"""
AWS Lambda function for refreshing the InfraSketch monthly-visitors badge cache.

Triggered by EventBridge once a day. Parses 30 days of CloudFront logs from S3
and writes the unique-human-visitor count into the DynamoDB cache row that
GET /api/badges/monthly-visitors.svg reads from.

The serving endpoint is cache-only and never parses logs in the request path,
because the parse routinely exceeds API Gateway's 30s timeout.

`badge_generator.py` is bundled alongside this file by the deploy script so the
parsing/caching logic lives in one place.
"""

import json
import traceback

from badge_generator import (
    parse_cloudfront_logs_for_unique_ips,
    set_cached_visitor_count,
)


def lambda_handler(event, context):
    print("Starting monthly-visitors cache refresh...")

    try:
        count = parse_cloudfront_logs_for_unique_ips(days=30)
        print(f"Parsed CloudFront logs, unique human visitors (30d): {count}")

        if count > 0:
            set_cached_visitor_count(count)
            print(f"Cached new visitor count: {count}")
        else:
            print("Visitor count was 0; not overwriting cache")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Cache refreshed", "count": count}),
        }
    except Exception as e:
        print(f"Error refreshing visitor cache: {e}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
