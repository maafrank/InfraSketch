#!/usr/bin/env python3
"""
Seed the infrasketch-blog-ideas DynamoDB table with 365 unique blog post ideas.

Usage:
    # Preview what would be seeded (no database changes)
    python scripts/seed_blog_ideas.py --preview

    # Seed the database with all ideas
    python scripts/seed_blog_ideas.py --seed

    # Count current ideas in the database
    python scripts/seed_blog_ideas.py --count

    # Reset all ideas to pending status
    python scripts/seed_blog_ideas.py --reset

    # Delete all ideas (use with caution)
    python scripts/seed_blog_ideas.py --delete-all

Requirements:
    - AWS credentials configured
    - boto3 installed
"""

import os
import sys
import argparse
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from blog_ideas_data import BLOG_IDEAS, get_category_counts

# Configuration
TABLE_NAME = "infrasketch-blog-ideas"
REGION = os.getenv("AWS_REGION", "us-east-1")


def get_dynamodb_resource():
    """Get DynamoDB resource."""
    return boto3.resource("dynamodb", region_name=REGION)


def get_dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client("dynamodb", region_name=REGION)


def create_table_if_not_exists():
    """Create the DynamoDB table if it doesn't exist."""
    client = get_dynamodb_client()

    try:
        client.describe_table(TableName=TABLE_NAME)
        print(f"Table '{TABLE_NAME}' already exists")
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    print(f"Creating table '{TABLE_NAME}'...")

    client.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "idea_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "idea_id", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "category-status-index",
                "KeySchema": [
                    {"AttributeName": "category", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
        Tags=[
            {"Key": "Project", "Value": "InfraSketch"},
            {"Key": "Purpose", "Value": "Blog automation"},
        ],
    )

    # Wait for table to be active
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=TABLE_NAME)
    print(f"Table '{TABLE_NAME}' created successfully")
    return True


def seed_ideas(dry_run: bool = False):
    """Seed all blog ideas to DynamoDB."""
    if not dry_run:
        create_table_if_not_exists()

    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TABLE_NAME)

    now = datetime.utcnow().isoformat()
    seeded = 0
    skipped = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seeding {len(BLOG_IDEAS)} blog ideas...")

    for idea in BLOG_IDEAS:
        idea_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"infrasketch-blog-{idea['slug']}"))

        if not dry_run:
            # Check if already exists
            try:
                response = table.get_item(Key={"idea_id": idea_id})
                if "Item" in response:
                    skipped += 1
                    continue
            except ClientError:
                pass

        item = {
            "idea_id": idea_id,
            "slug": idea["slug"],
            "title": idea["title"],
            "category": idea["category"],
            "outline": idea["outline"],
            "keywords": idea["keywords"],
            "difficulty": idea["difficulty"],
            "status": "pending",
            "generation_attempts": 0,
            "created_at": now,
            "updated_at": now,
        }

        if dry_run:
            if seeded < 5:
                print(f"  Would seed: {idea['title'][:60]}...")
            elif seeded == 5:
                print("  ... (showing first 5 only)")
            seeded += 1
        else:
            table.put_item(Item=item)
            seeded += 1
            if seeded % 50 == 0:
                print(f"  Seeded {seeded} ideas...")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done!")
    print(f"  Seeded: {seeded}")
    if skipped > 0:
        print(f"  Skipped (already exist): {skipped}")


def count_ideas():
    """Count ideas in the database by status."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TABLE_NAME)

    print(f"\nCounting ideas in '{TABLE_NAME}'...")

    # Scan and count by status
    status_counts = {}
    category_counts = {}
    total = 0

    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    for item in items:
        total += 1
        status = item.get("status", "unknown")
        category = item.get("category", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

    print(f"\nTotal ideas: {total}")

    print("\nBy status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("\nBy category:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    return total, status_counts, category_counts


def reset_ideas():
    """Reset all ideas back to pending status."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TABLE_NAME)

    print(f"\nResetting all ideas to 'pending' status...")

    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    reset_count = 0
    now = datetime.utcnow().isoformat()

    for item in items:
        if item.get("status") != "pending":
            table.update_item(
                Key={"idea_id": item["idea_id"]},
                UpdateExpression="SET #status = :status, updated_at = :now, generation_attempts = :zero",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "pending",
                    ":now": now,
                    ":zero": 0,
                },
            )
            reset_count += 1

    print(f"Reset {reset_count} ideas to pending status")


def delete_all_ideas():
    """Delete all ideas from the table."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TABLE_NAME)

    print(f"\nDeleting all ideas from '{TABLE_NAME}'...")

    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    deleted = 0
    for item in items:
        table.delete_item(Key={"idea_id": item["idea_id"]})
        deleted += 1
        if deleted % 50 == 0:
            print(f"  Deleted {deleted} ideas...")

    print(f"Deleted {deleted} ideas")


def preview_ideas():
    """Show summary of ideas that would be seeded."""
    counts = get_category_counts()
    total = len(BLOG_IDEAS)

    print("\n" + "=" * 60)
    print("Blog Ideas Preview")
    print("=" * 60)

    print(f"\nTotal ideas: {total}")

    print("\nBy category:")
    for cat, count in sorted(counts.items()):
        print(f"  {cat}: {count}")

    print("\nSample ideas by category:")
    for cat in sorted(counts.keys()):
        ideas = [i for i in BLOG_IDEAS if i["category"] == cat][:2]
        print(f"\n  {cat.upper()}:")
        for idea in ideas:
            print(f"    - {idea['title'][:55]}...")

    print("\n" + "=" * 60)
    print("Run with --seed to add these to DynamoDB")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Seed blog ideas to DynamoDB for automated publishing."
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show what would be seeded without making changes",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed all ideas to DynamoDB",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Count current ideas in the database",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all ideas to pending status",
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all ideas from the table (use with caution)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("InfraSketch Blog Ideas Seeder")
    print(f"Table: {TABLE_NAME}")
    print(f"Region: {REGION}")
    print("=" * 60)

    if args.preview:
        preview_ideas()
    elif args.seed:
        seed_ideas(dry_run=False)
    elif args.count:
        count_ideas()
    elif args.reset:
        confirm = input("Are you sure you want to reset all ideas? (yes/no): ")
        if confirm.lower() == "yes":
            reset_ideas()
        else:
            print("Aborted.")
    elif args.delete_all:
        confirm = input("Are you sure you want to DELETE ALL ideas? This cannot be undone. (DELETE/no): ")
        if confirm == "DELETE":
            delete_all_ideas()
        else:
            print("Aborted.")
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python scripts/seed_blog_ideas.py --preview")
        print("  python scripts/seed_blog_ideas.py --seed")
        print("  python scripts/seed_blog_ideas.py --count")


if __name__ == "__main__":
    main()
