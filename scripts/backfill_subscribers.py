#!/usr/bin/env python3
"""
Backfill existing users from Clerk into the subscribers table.

This script:
1. Fetches all users from Clerk Admin API
2. Creates subscriber records for each user (auto opt-in)
3. Logs progress and results

Usage:
    python scripts/backfill_subscribers.py

Requirements:
    - CLERK_SECRET_KEY environment variable must be set
    - AWS credentials configured for DynamoDB access
"""

import os
import sys
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.subscription.storage import SubscriberStorage


def get_clerk_users():
    """
    Fetch all users from Clerk Admin API.

    Returns:
        List of user dicts with user_id and email
    """
    clerk_secret_key = os.getenv('CLERK_SECRET_KEY')
    if not clerk_secret_key:
        raise ValueError("CLERK_SECRET_KEY environment variable is required")

    users = []
    offset = 0
    limit = 100  # Clerk's default page size

    while True:
        response = requests.get(
            'https://api.clerk.com/v1/users',
            headers={
                'Authorization': f'Bearer {clerk_secret_key}',
                'Content-Type': 'application/json'
            },
            params={
                'limit': limit,
                'offset': offset
            }
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        for user in data:
            user_id = user.get('id')

            # Get primary email address
            email_addresses = user.get('email_addresses', [])
            primary_email = None

            for email in email_addresses:
                if email.get('id') == user.get('primary_email_address_id'):
                    primary_email = email.get('email_address')
                    break

            # Fallback to first email if no primary
            if not primary_email and email_addresses:
                primary_email = email_addresses[0].get('email_address')

            if user_id and primary_email:
                users.append({
                    'user_id': user_id,
                    'email': primary_email,
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'created_at': user.get('created_at')
                })

        # Check if there are more pages
        if len(data) < limit:
            break

        offset += limit

    return users


def backfill_subscribers():
    """
    Main backfill function.
    """
    print("=" * 60)
    print("InfraSketch Subscriber Backfill")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Fetch users from Clerk
    print("\n1. Fetching users from Clerk...")
    try:
        users = get_clerk_users()
        print(f"   Found {len(users)} users in Clerk")
    except Exception as e:
        print(f"   ERROR: Failed to fetch users from Clerk: {e}")
        return

    if not users:
        print("   No users found. Exiting.")
        return

    # Initialize subscriber storage
    print("\n2. Connecting to DynamoDB...")
    try:
        storage = SubscriberStorage()
        print("   Connected to infrasketch-subscribers table")
    except Exception as e:
        print(f"   ERROR: Failed to connect to DynamoDB: {e}")
        return

    # Create subscriber records
    print("\n3. Creating subscriber records...")
    created = 0
    already_exists = 0
    errors = 0

    for user in users:
        try:
            # Check if already exists
            existing = storage.get_subscriber(user['user_id'])
            if existing:
                print(f"   - {user['email']}: Already exists (subscribed={existing.subscribed})")
                already_exists += 1
            else:
                subscriber = storage.create_subscriber(user['user_id'], user['email'])
                print(f"   + {user['email']}: Created (subscribed=True)")
                created += 1
        except Exception as e:
            print(f"   ! {user['email']}: ERROR - {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total users in Clerk:     {len(users)}")
    print(f"New subscribers created:  {created}")
    print(f"Already existed:          {already_exists}")
    print(f"Errors:                   {errors}")

    # Show current counts
    counts = storage.get_subscriber_count()
    print(f"\nCurrent subscriber status:")
    print(f"  Total:        {counts['total']}")
    print(f"  Subscribed:   {counts['subscribed']}")
    print(f"  Unsubscribed: {counts['unsubscribed']}")

    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == '__main__':
    backfill_subscribers()
