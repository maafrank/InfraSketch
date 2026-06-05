#!/usr/bin/env python3
"""
Sync a single user's DynamoDB plan from Clerk.

Use this when a billing webhook missed and a user is stuck on the wrong plan.
Accepts either a Clerk user_id (user_xxx) or an email address.

Usage:
    python scripts/sync_user_plan.py user_35kXiiZNx1eveuE7FN4dncjP7hA
    python scripts/sync_user_plan.py mattafrank2439@gmail.com

Requires:
    - CLERK_SECRET_KEY in .env (or AWS Secrets Manager infrasketch/clerk-secret-key)
    - AWS credentials with read/write on infrasketch-user-credits
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.billing.clerk_client import ClerkAPIError, get_clerk_client
from app.billing.storage import get_user_credits_storage
from app.billing.sync import sync_user_from_clerk


def _resolve_user_id(identifier: str) -> str:
    if "@" not in identifier:
        return identifier
    try:
        user_id = get_clerk_client().lookup_user_id_by_email(identifier)
    except ClerkAPIError as e:
        print(f"ERROR: Clerk lookup failed for {identifier}: {e}", file=sys.stderr)
        sys.exit(2)
    if not user_id:
        print(f"ERROR: No Clerk user found for {identifier}", file=sys.stderr)
        sys.exit(2)
    return user_id


def _snapshot(user_id: str) -> dict:
    credits = get_user_credits_storage().get_credits(user_id)
    if credits is None:
        return {"exists": False}
    return {
        "exists": True,
        "plan": credits.plan,
        "subscription_status": credits.subscription_status,
        "clerk_subscription_id": credits.clerk_subscription_id,
        "credits_balance": credits.credits_balance,
        "credits_monthly_allowance": credits.credits_monthly_allowance,
        "last_clerk_sync_at": credits.last_clerk_sync_at.isoformat() if credits.last_clerk_sync_at else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync a user's plan from Clerk to DynamoDB.")
    parser.add_argument("identifier", help="Clerk user_id (user_xxx) or email address")
    args = parser.parse_args()

    user_id = _resolve_user_id(args.identifier)
    print(f"User: {user_id}")

    before = _snapshot(user_id)
    print("\nBefore:")
    print(json.dumps(before, indent=2))

    try:
        sync_user_from_clerk(user_id, force=True)
    except Exception as e:
        print(f"\nERROR: Clerk sync failed for {user_id}: {e}", file=sys.stderr)
        print("DynamoDB was NOT modified. Fix the Clerk credentials / connectivity and re-run.", file=sys.stderr)
        return 3

    after = _snapshot(user_id)
    print("\nAfter:")
    print(json.dumps(after, indent=2))

    if before.get("plan") != after.get("plan"):
        print(f"\nUpdated plan: {before.get('plan')} -> {after.get('plan')}")
    else:
        print(f"\nNo plan change. Stored plan = {after.get('plan')}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
