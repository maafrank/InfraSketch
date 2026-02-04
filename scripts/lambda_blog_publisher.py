#!/usr/bin/env python3
"""
AWS Lambda function for automated daily blog publishing to Dev.to.

Triggered by EventBridge on a daily schedule:
1. Query DynamoDB for next pending blog idea
2. Generate article content using Claude API
3. Source cover image from Unsplash
4. Publish to Dev.to
5. Update DynamoDB with published status

Usage (local testing):
    python scripts/lambda_blog_publisher.py

Environment variables:
    ANTHROPIC_API_KEY - Claude API key
    DEVTO_API_KEY - Dev.to API key
    UNSPLASH_ACCESS_KEY - Unsplash API key (optional, uses fallback image)
    AWS_REGION - AWS region (default: us-east-1)
"""

import os
import sys
import json
import time
from datetime import datetime
from decimal import Decimal

import boto3
import requests
from botocore.exceptions import ClientError

# Add parent directory for imports when running locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.utils.secrets import get_anthropic_api_key, get_devto_api_key
except ImportError:
    # Fallback for Lambda where backend isn't available
    def get_anthropic_api_key():
        return os.environ.get("ANTHROPIC_API_KEY")
    def get_devto_api_key():
        return os.environ.get("DEVTO_API_KEY")

# Configuration
TABLE_NAME = "infrasketch-blog-ideas"
REGION = os.getenv("AWS_REGION", "us-east-1")
DEVTO_API_BASE = "https://dev.to/api/articles"
UNSPLASH_API_BASE = "https://api.unsplash.com"
FALLBACK_IMAGE = "https://infrasketch.net/full-app-with-design-doc.png"
MAX_RETRIES = 3

# Category rotation order
CATEGORIES = [
    "system-design",
    "architecture",
    "interviews",
    "devops",
    "cloud",
    "ai-ml",
    "career",
]

# Article generation prompt
ARTICLE_PROMPT = """You are a senior software engineer and technical writer creating educational content for developers.

Write a comprehensive blog article about: {title}

Context/Outline:
{outline}

Target audience: Software engineers learning about {category}
Tone: Professional but approachable, like a senior engineer mentoring a colleague
Length: 2000-3000 words
Difficulty level: {difficulty}

Article Structure:
1. Introduction (compelling hook explaining why this topic matters)
2. Core Concepts (explain fundamentals clearly with examples)
3. Practical Implementation (code snippets, step-by-step guidance)
4. Common Pitfalls (mistakes to avoid, best practices)
5. Real-World Applications (how this is used at scale)
6. Key Takeaways (summary of most important points)

Writing Guidelines:
- Use markdown headers (## and ###) to organize content
- Include code examples in appropriate languages (Python, JavaScript, Go, SQL, YAML)
- Add bullet points for lists and key points
- Keep paragraphs concise (3-4 sentences max)
- Use specific technologies and real-world examples
- Include a natural mention of InfraSketch for visualizing architectures where relevant
- NO em-dashes (—), use commas or separate sentences instead
- End with a brief call-to-action encouraging readers to try designing their own systems

Keywords to incorporate naturally: {keywords}

Write the article now in markdown format:"""


def get_dynamodb_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def get_next_pending_idea():
    """
    Get the next pending blog idea using round-robin category selection.

    Rotates through categories based on day of year to ensure balanced coverage.
    Skips ideas that have failed too many times.
    """
    table = get_dynamodb_table()

    # Determine today's starting category
    day_of_year = datetime.utcnow().timetuple().tm_yday
    start_idx = day_of_year % len(CATEGORIES)

    # Try each category in rotation
    for i in range(len(CATEGORIES)):
        category = CATEGORIES[(start_idx + i) % len(CATEGORIES)]

        try:
            response = table.query(
                IndexName="category-status-index",
                KeyConditionExpression="category = :cat AND #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cat": category,
                    ":status": "pending",
                },
                Limit=10,  # Get a few to filter
            )

            items = response.get("Items", [])

            # Filter out items with too many attempts
            for item in items:
                attempts = int(item.get("generation_attempts", 0))
                if attempts < MAX_RETRIES:
                    print(f"Selected idea from category '{category}': {item['title']}")
                    return item

        except ClientError as e:
            print(f"Error querying category {category}: {e}")
            continue

    print("No pending ideas found in any category")
    return None


def update_idea_status(idea_id: str, status: str, **kwargs):
    """Update the status of an idea in DynamoDB."""
    table = get_dynamodb_table()

    update_expr = "SET #status = :status, updated_at = :now"
    expr_names = {"#status": "status"}
    expr_values = {
        ":status": status,
        ":now": datetime.utcnow().isoformat(),
    }

    for key, value in kwargs.items():
        update_expr += f", {key} = :{key}"
        if isinstance(value, float):
            value = Decimal(str(value))
        elif isinstance(value, int):
            value = Decimal(value)
        expr_values[f":{key}"] = value

    table.update_item(
        Key={"idea_id": idea_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def increment_attempts(idea_id: str, error: str):
    """Increment generation attempts and record error."""
    table = get_dynamodb_table()

    # Get current attempts
    response = table.get_item(Key={"idea_id": idea_id})
    item = response.get("Item", {})
    attempts = int(item.get("generation_attempts", 0)) + 1

    # Determine new status
    new_status = "pending" if attempts < MAX_RETRIES else "failed"

    table.update_item(
        Key={"idea_id": idea_id},
        UpdateExpression="SET #status = :status, generation_attempts = :attempts, last_error = :error, updated_at = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": new_status,
            ":attempts": attempts,
            ":error": error[:500],  # Truncate long errors
            ":now": datetime.utcnow().isoformat(),
        },
    )

    return attempts


def generate_article(idea: dict) -> str:
    """Generate article content using Claude API."""
    import anthropic

    api_key = get_anthropic_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = ARTICLE_PROMPT.format(
        title=idea["title"],
        outline=idea["outline"],
        category=idea["category"].replace("-", " "),
        difficulty=idea["difficulty"],
        keywords=", ".join(idea.get("keywords", [])),
    )

    print(f"Generating article for: {idea['title']}")
    start_time = time.time()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed = time.time() - start_time
    print(f"Article generated in {elapsed:.1f}s")

    return response.content[0].text


def get_cover_image(keywords: list) -> dict:
    """
    Get a relevant cover image from Unsplash.

    Returns dict with url, photographer, and photographer_url for attribution.
    Falls back to InfraSketch default image if Unsplash unavailable.
    """
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")

    if not access_key:
        print("No Unsplash API key, using fallback image")
        return {
            "url": FALLBACK_IMAGE,
            "photographer": "InfraSketch",
            "photographer_url": "https://infrasketch.net",
        }

    # Try keywords in order until we find a good match
    search_terms = keywords[:3] + ["technology", "code"]

    for term in search_terms:
        try:
            response = requests.get(
                f"{UNSPLASH_API_BASE}/search/photos",
                params={
                    "query": term,
                    "orientation": "landscape",
                    "per_page": 1,
                },
                headers={"Authorization": f"Client-ID {access_key}"},
                timeout=10,
            )

            if response.ok:
                data = response.json()
                results = data.get("results", [])
                if results:
                    photo = results[0]
                    print(f"Found Unsplash image for '{term}'")
                    return {
                        "url": photo["urls"]["regular"],
                        "photographer": photo["user"]["name"],
                        "photographer_url": photo["user"]["links"]["html"],
                    }
        except Exception as e:
            print(f"Unsplash search failed for '{term}': {e}")
            continue

    print("No Unsplash image found, using fallback")
    return {
        "url": FALLBACK_IMAGE,
        "photographer": "InfraSketch",
        "photographer_url": "https://infrasketch.net",
    }


def normalize_tag(tag: str) -> str:
    """Normalize tag for Dev.to (lowercase, alphanumeric, hyphens only)."""
    import re
    normalized = tag.lower().replace(" ", "")
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    normalized = re.sub(r'-+', '-', normalized).strip('-')
    return normalized


def publish_to_devto(idea: dict, article_content: str, cover_image: dict) -> dict:
    """
    Publish article to Dev.to.

    Returns the Dev.to API response with id and url.
    """
    api_key = get_devto_api_key()
    if not api_key:
        raise ValueError("DEVTO_API_KEY not configured")

    # Prepare tags (max 4, normalized)
    tags = []
    for keyword in idea.get("keywords", [])[:4]:
        normalized = normalize_tag(keyword)
        if normalized and normalized not in tags:
            tags.append(normalized)

    # Add attribution for cover image
    attribution = ""
    if cover_image["photographer"] != "InfraSketch":
        attribution = f"\n\n*Cover photo by [{cover_image['photographer']}]({cover_image['photographer_url']}) on [Unsplash](https://unsplash.com)*"

    # Build payload
    payload = {
        "article": {
            "title": idea["title"],
            "body_markdown": article_content + attribution,
            "published": True,
            "tags": tags,
            "main_image": cover_image["url"],
        }
    }

    # Add canonical URL if we want to link back to InfraSketch blog
    # payload["article"]["canonical_url"] = f"https://infrasketch.net/blog/{idea['slug']}"

    print(f"Publishing to Dev.to: {idea['title']}")

    response = requests.post(
        DEVTO_API_BASE,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code == 429:
        raise Exception("Dev.to rate limit exceeded")

    response.raise_for_status()

    result = response.json()
    print(f"Published successfully: {result.get('url')}")

    return result


def lambda_handler(event, context):
    """
    Main Lambda handler for daily blog publishing.

    Triggered by EventBridge schedule or manual invocation.
    """
    print(f"Starting blog publisher: {datetime.utcnow().isoformat()}")
    print(f"Event: {json.dumps(event)}")

    start_time = time.time()
    idea = None

    try:
        # 1. Get next pending idea
        idea = get_next_pending_idea()
        if not idea:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No pending ideas found"}),
            }

        idea_id = idea["idea_id"]

        # 2. Mark as generating
        update_idea_status(idea_id, "generating")

        # 3. Generate article with Claude
        article_content = generate_article(idea)

        # 4. Get cover image
        cover_image = get_cover_image(idea.get("keywords", []))

        # 5. Publish to Dev.to
        devto_response = publish_to_devto(idea, article_content, cover_image)

        # 6. Update DynamoDB with success
        update_idea_status(
            idea_id,
            "published",
            devto_id=devto_response.get("id"),
            devto_url=devto_response.get("url"),
            published_date=datetime.utcnow().isoformat(),
        )

        elapsed = time.time() - start_time
        print(f"Successfully published in {elapsed:.1f}s")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Article published successfully",
                "title": idea["title"],
                "devto_url": devto_response.get("url"),
                "duration_seconds": round(elapsed, 1),
            }),
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")

        # Record failure
        if idea:
            attempts = increment_attempts(idea["idea_id"], error_msg)
            print(f"Attempt {attempts}/{MAX_RETRIES} failed for: {idea['title']}")

        # Re-raise for Lambda to record the error
        raise


def main():
    """Run locally for testing."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

    print("=" * 60)
    print("Blog Publisher - Local Test")
    print("=" * 60)

    # Run the handler
    result = lambda_handler({}, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))


if __name__ == "__main__":
    main()
