#!/usr/bin/env python3
"""
Publish InfraSketch blog posts to Dev.to.

Usage:
    # List all posts and their Dev.to status
    python scripts/publish_to_devto.py --list

    # Preview a post (shows what would be sent, no API call)
    python scripts/publish_to_devto.py what-is-system-design --preview

    # Publish as draft (not visible on Dev.to)
    python scripts/publish_to_devto.py what-is-system-design --draft

    # Publish live
    python scripts/publish_to_devto.py what-is-system-design --publish

    # Update an already-published post
    python scripts/publish_to_devto.py what-is-system-design --update

    # Override tags (max 4)
    python scripts/publish_to_devto.py what-is-system-design --publish --tags python,webdev,tutorial

Requirements:
    - DEVTO_API_KEY environment variable set (or in AWS Secrets Manager)
    - Blog posts in frontend/public/blog/posts/
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.utils.secrets import get_devto_api_key

# Configuration
DEVTO_API_BASE = "https://dev.to/api/articles"
BLOG_POSTS_DIR = Path(__file__).parent.parent / "frontend" / "public" / "blog" / "posts"
INDEX_FILE = BLOG_POSTS_DIR / "index.json"
CANONICAL_BASE_URL = "https://infrasketch.net/blog"
IMAGE_BASE_URL = "https://infrasketch.net"


def load_blog_index() -> dict:
    """Load and return the blog index.json."""
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)


def save_blog_index(data: dict):
    """Save the blog index.json with atomic write."""
    temp_path = INDEX_FILE.with_suffix('.json.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    temp_path.rename(INDEX_FILE)


def load_post_content(slug: str) -> str:
    """Read markdown content from posts/{slug}.md."""
    post_path = BLOG_POSTS_DIR / f"{slug}.md"
    if not post_path.exists():
        raise FileNotFoundError(f"Post not found: {post_path}")
    with open(post_path, 'r') as f:
        return f.read()


def get_post_by_slug(slug: str) -> dict:
    """Get a single post's metadata by slug."""
    data = load_blog_index()
    for post in data["posts"]:
        if post["slug"] == slug:
            return post
    raise ValueError(f"Post not found in index.json: {slug}")


def normalize_tag(tag: str) -> str:
    """
    Convert tag to Dev.to format: lowercase, no spaces, alphanumeric only.
    Dev.to tags can have letters, numbers, and single hyphens (not at start/end).
    """
    # Lowercase and replace spaces with nothing
    normalized = tag.lower().replace(" ", "")
    # Remove non-alphanumeric characters except hyphens
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    # Remove leading/trailing hyphens and collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized).strip('-')
    return normalized


def get_devto_tags(tags: list, override: list = None) -> list:
    """Return max 4 normalized tags."""
    if override:
        source_tags = override
    else:
        source_tags = tags[:4]  # Take first 4

    normalized = []
    for tag in source_tags:
        norm = normalize_tag(tag)
        if norm and norm not in normalized:  # Avoid duplicates
            normalized.append(norm)
        if len(normalized) >= 4:
            break

    return normalized


def build_devto_payload(post_meta: dict, content: str, published: bool, tag_override: list = None) -> dict:
    """Build the API payload for Dev.to."""
    slug = post_meta["slug"]
    canonical_url = f"{CANONICAL_BASE_URL}/{slug}"

    # Get cover image URL (must be absolute)
    image = post_meta.get("image", "")
    if image.startswith("/"):
        main_image = f"{IMAGE_BASE_URL}{image}"
    elif image:
        main_image = image
    else:
        main_image = None

    tags = get_devto_tags(post_meta.get("tags", []), tag_override)

    payload = {
        "title": post_meta["title"],
        "body_markdown": content,
        "published": published,
        "canonical_url": canonical_url,
        "tags": tags,
    }

    if post_meta.get("description"):
        payload["description"] = post_meta["description"]

    if main_image:
        payload["main_image"] = main_image

    return payload


def validate_content(content: str, post_meta: dict) -> list:
    """Return list of warnings/issues with the content."""
    warnings = []

    # Check for relative image URLs (won't work on Dev.to)
    relative_images = re.findall(r'!\[.*?\]\((/[^)]+)\)', content)
    if relative_images:
        warnings.append(f"Contains {len(relative_images)} relative image URL(s) that won't display on Dev.to")
        for img in relative_images[:3]:
            warnings.append(f"  - {img}")

    # Check content length (Dev.to has ~64KB limit)
    if len(content) > 60000:
        warnings.append(f"Content is very long ({len(content):,} chars), may hit Dev.to limits")

    return warnings


def publish_to_devto(payload: dict, article_id: int = None) -> dict:
    """
    Create or update article on Dev.to.

    Args:
        payload: Article data (title, body_markdown, etc.)
        article_id: If provided, updates existing article (PUT)

    Returns:
        API response with id, url, etc.
    """
    api_key = get_devto_api_key()
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    if article_id:
        # Update existing
        response = requests.put(
            f"{DEVTO_API_BASE}/{article_id}",
            headers=headers,
            json={"article": payload}
        )
    else:
        # Create new
        response = requests.post(
            DEVTO_API_BASE,
            headers=headers,
            json={"article": payload}
        )

    response.raise_for_status()
    return response.json()


def update_blog_index(slug: str, devto_id: int, devto_url: str):
    """Update index.json with Dev.to tracking info."""
    data = load_blog_index()

    for post in data["posts"]:
        if post["slug"] == slug:
            post["devto_id"] = devto_id
            post["devto_url"] = devto_url
            break

    save_blog_index(data)
    print(f"   Updated index.json with Dev.to ID: {devto_id}")


def list_posts():
    """List all posts and their Dev.to status."""
    data = load_blog_index()
    posts = data["posts"]

    published = [p for p in posts if p.get("devto_id")]
    unpublished = [p for p in posts if not p.get("devto_id")]

    print("\nInfraSketch Blog Posts - Dev.to Status")
    print("=" * 60)

    if published:
        print(f"\nPublished to Dev.to ({len(published)}):")
        for post in published:
            print(f"  {post['slug']}")
            print(f"    -> {post.get('devto_url', 'URL not recorded')}")

    if unpublished:
        print(f"\nNot published ({len(unpublished)}):")
        for post in unpublished:
            tags = post.get("tags", [])[:4]
            tag_str = ", ".join(tags[:2]) + ("..." if len(tags) > 2 else "")
            print(f"  - {post['slug']}")
            print(f"    Tags: {tag_str}")

    print(f"\nTotal: {len(posts)} posts ({len(published)} published, {len(unpublished)} unpublished)")


def preview_post(slug: str, tag_override: list = None):
    """Show what would be sent to Dev.to without making API call."""
    post = get_post_by_slug(slug)
    content = load_post_content(slug)
    payload = build_devto_payload(post, content, published=False, tag_override=tag_override)
    warnings = validate_content(content, post)

    print("\n" + "=" * 60)
    print("Dev.to Publish Preview")
    print("=" * 60)

    print(f"\nTitle: {payload['title']}")
    print(f"Slug: {slug}")
    print(f"Canonical URL: {payload['canonical_url']}")

    if payload.get("main_image"):
        print(f"Cover Image: {payload['main_image']}")

    original_tags = post.get("tags", [])
    print(f"\nTags ({len(payload['tags'])} of {len(original_tags)} original):")
    for tag in payload['tags']:
        print(f"  - {tag}")

    if payload.get("description"):
        print(f"\nDescription:")
        print(f"  {payload['description'][:100]}...")

    print(f"\nContent preview (first 500 chars):")
    print("-" * 40)
    print(content[:500])
    print("-" * 40)
    print(f"Total content length: {len(content):,} characters")

    if warnings:
        print(f"\nWarnings:")
        for w in warnings:
            print(f"  {w}")

    if post.get("devto_id"):
        print(f"\nStatus: Already published to Dev.to")
        print(f"  Dev.to ID: {post['devto_id']}")
        print(f"  Dev.to URL: {post.get('devto_url', 'N/A')}")
        print(f"  Use --update to update the existing article")
    else:
        print(f"\nStatus: Not yet published to Dev.to")
        print(f"  Use --draft to publish as draft")
        print(f"  Use --publish to publish live")


def publish_post(slug: str, published: bool, update: bool, tag_override: list = None):
    """Publish or update a post on Dev.to."""
    post = get_post_by_slug(slug)
    content = load_post_content(slug)

    # Check for duplicates
    if post.get("devto_id") and not update:
        print(f"\nERROR: Post already published to Dev.to")
        print(f"  Dev.to URL: {post.get('devto_url', 'N/A')}")
        print(f"  Use --update to update the existing article")
        sys.exit(1)

    # For updates, require existing devto_id
    if update and not post.get("devto_id"):
        print(f"\nERROR: Cannot update - post not yet published to Dev.to")
        print(f"  Use --draft or --publish first")
        sys.exit(1)

    # Validate content
    warnings = validate_content(content, post)
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  {w}")
        print()

    # Build payload
    payload = build_devto_payload(post, content, published, tag_override)
    article_id = post.get("devto_id") if update else None

    action = "Updating" if update else "Publishing"
    status = "live" if published else "as draft"
    print(f"\n{action} '{post['title']}' {status}...")

    try:
        response = publish_to_devto(payload, article_id)

        devto_id = response.get("id")
        devto_url = response.get("url")

        print(f"\n   Success!")
        print(f"   Dev.to ID: {devto_id}")
        print(f"   Dev.to URL: {devto_url}")

        # Update index.json
        if devto_id and devto_url:
            update_blog_index(slug, devto_id, devto_url)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            errors = e.response.json().get('error', 'Unknown validation error')
            print(f"\nERROR: Dev.to validation error:")
            print(f"  {errors}")
        elif e.response.status_code == 401:
            print("\nERROR: Invalid Dev.to API key")
            print("  Check your DEVTO_API_KEY environment variable")
        elif e.response.status_code == 429:
            print("\nERROR: Rate limited by Dev.to")
            print("  Wait a few minutes and try again")
        else:
            print(f"\nERROR: Dev.to API error: {e}")
            print(f"  Response: {e.response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Publish InfraSketch blog posts to Dev.to',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                              List all posts
  %(prog)s what-is-system-design --preview     Preview without publishing
  %(prog)s what-is-system-design --draft       Publish as draft
  %(prog)s what-is-system-design --publish     Publish live
  %(prog)s what-is-system-design --update      Update existing article
  %(prog)s my-post --publish --tags a,b,c      Override tags
        """
    )
    parser.add_argument(
        'slug',
        nargs='?',
        help='Blog post slug to publish'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all posts and their Dev.to status'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Show what would be sent without calling API'
    )
    parser.add_argument(
        '--draft',
        action='store_true',
        help='Publish as draft (not visible on Dev.to)'
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish live on Dev.to'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing Dev.to article'
    )
    parser.add_argument(
        '--tags',
        type=str,
        help='Override tags (comma-separated, max 4)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("InfraSketch Blog - Dev.to Publisher")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Parse tag override
    tag_override = None
    if args.tags:
        tag_override = [t.strip() for t in args.tags.split(',')]
        if len(tag_override) > 4:
            print(f"\nWarning: Only first 4 tags will be used (Dev.to limit)")
            tag_override = tag_override[:4]

    # List mode
    if args.list:
        list_posts()
        return

    # Require slug for all other modes
    if not args.slug:
        parser.print_help()
        print("\nERROR: Please provide a post slug or use --list")
        sys.exit(1)

    # Preview mode
    if args.preview:
        preview_post(args.slug, tag_override)
        return

    # Publish modes
    if args.draft:
        publish_post(args.slug, published=False, update=False, tag_override=tag_override)
    elif args.publish:
        publish_post(args.slug, published=True, update=False, tag_override=tag_override)
    elif args.update:
        # For update, check if currently published
        post = get_post_by_slug(args.slug)
        # We'll keep the same published status or default to draft
        publish_post(args.slug, published=True, update=True, tag_override=tag_override)
    else:
        parser.print_help()
        print("\nERROR: Please specify an action: --preview, --draft, --publish, or --update")
        sys.exit(1)

    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == '__main__':
    main()
