"""
Badge Generator Utility

Generates SVG badges for displaying visitor statistics.
Parses CloudFront logs from S3 and caches results in DynamoDB.
"""

import boto3
import gzip
import io
import time
from datetime import datetime, timedelta
from typing import Optional
import os

# S3 bucket containing CloudFront logs
CLOUDFRONT_LOGS_BUCKET = "infrasketch-cloudfront-logs-059409992371"
CLOUDFRONT_LOGS_PREFIX = "cloudfront/"

# DynamoDB cache settings
CACHE_TABLE = "infrasketch-sessions"
CACHE_KEY = "CACHE#monthly-visitors"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def get_dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client("dynamodb", region_name="us-east-1")


def get_s3_client():
    """Get S3 client."""
    return boto3.client("s3", region_name="us-east-1")


def get_cached_visitor_count() -> Optional[int]:
    """
    Get cached visitor count from DynamoDB.
    Returns None if cache is expired or doesn't exist.
    """
    try:
        dynamodb = get_dynamodb_client()
        response = dynamodb.get_item(
            TableName=CACHE_TABLE,
            Key={"session_id": {"S": CACHE_KEY}}
        )

        if "Item" not in response:
            return None

        item = response["Item"]

        # Check if cache is expired
        cached_at = float(item.get("cached_at", {}).get("N", 0))
        if time.time() - cached_at > CACHE_TTL_SECONDS:
            return None

        return int(item.get("visitor_count", {}).get("N", 0))
    except Exception as e:
        print(f"Error getting cached visitor count: {e}")
        return None


def set_cached_visitor_count(count: int) -> None:
    """Cache visitor count in DynamoDB with TTL."""
    try:
        dynamodb = get_dynamodb_client()
        ttl = int(time.time()) + CACHE_TTL_SECONDS

        dynamodb.put_item(
            TableName=CACHE_TABLE,
            Item={
                "session_id": {"S": CACHE_KEY},
                "visitor_count": {"N": str(count)},
                "cached_at": {"N": str(time.time())},
                "ttl": {"N": str(ttl)}
            }
        )
    except Exception as e:
        print(f"Error caching visitor count: {e}")


def parse_cloudfront_logs_for_unique_ips(days: int = 30) -> int:
    """
    Parse CloudFront logs from S3 and count unique visitor IPs.

    Args:
        days: Number of days to look back (default 30)

    Returns:
        Count of unique IP addresses
    """
    s3 = get_s3_client()
    unique_ips = set()

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    try:
        # List all log files
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(
            Bucket=CLOUDFRONT_LOGS_BUCKET,
            Prefix=CLOUDFRONT_LOGS_PREFIX
        ):
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Extract date from filename (format: E2YM028NUBX2QN.2026-01-12-14.xxxxx.gz)
                try:
                    # Get the date part from the filename
                    filename = key.split("/")[-1]
                    parts = filename.split(".")
                    if len(parts) >= 2:
                        date_str = parts[1][:10]  # "2026-01-12"
                        log_date = datetime.strptime(date_str, "%Y-%m-%d")

                        # Skip if outside our date range
                        if log_date < start_date or log_date > end_date:
                            continue
                except (ValueError, IndexError):
                    continue

                # Download and parse the log file
                try:
                    response = s3.get_object(Bucket=CLOUDFRONT_LOGS_BUCKET, Key=key)

                    # Decompress gzip content
                    if key.endswith(".gz"):
                        with gzip.GzipFile(fileobj=io.BytesIO(response["Body"].read())) as f:
                            content = f.read().decode("utf-8")
                    else:
                        content = response["Body"].read().decode("utf-8")

                    # Parse each line and extract IP (5th field in CloudFront logs)
                    for line in content.split("\n"):
                        if line.startswith("#") or not line.strip():
                            continue

                        fields = line.split("\t")
                        if len(fields) >= 5:
                            ip = fields[4]  # c-ip field
                            unique_ips.add(ip)

                except Exception as e:
                    print(f"Error parsing log file {key}: {e}")
                    continue

    except Exception as e:
        print(f"Error listing S3 objects: {e}")

    return len(unique_ips)


def get_monthly_visitor_count() -> int:
    """
    Get monthly visitor count, using cache if available.
    """
    # Check cache first
    cached_count = get_cached_visitor_count()
    if cached_count is not None:
        print(f"Using cached visitor count: {cached_count}")
        return cached_count

    # Parse logs and cache result
    print("Cache miss - parsing CloudFront logs...")
    count = parse_cloudfront_logs_for_unique_ips(days=30)

    if count > 0:
        set_cached_visitor_count(count)
        print(f"Cached new visitor count: {count}")

    return count


def format_visitor_count(count: int) -> str:
    """
    Format visitor count for display (e.g., 6158 -> "6.2K").
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def generate_badge_svg(count: str) -> str:
    """
    Generate a minimal flat SVG badge displaying monthly visitors.

    Style matches the TryLaunch styled badge pattern.
    Scaled 2x for better readability.
    """
    line1 = f"{count} monthly visitors"
    line2 = "Powered by CloudFront"

    # Calculate width based on longer text line (approximate) - scaled 2x
    line1_width = len(line1) * 13 + 60
    line2_width = len(line2) * 11 + 60
    badge_width = max(line1_width, line2_width, 320)
    badge_height = 84  # Taller for two lines, scaled 2x

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{badge_width}" height="{badge_height}" viewBox="0 0 {badge_width} {badge_height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2d2d2d"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
  </defs>
  <rect width="{badge_width}" height="{badge_height}" rx="12" ry="12" fill="url(#bg)"/>
  <rect x="1" y="1" width="{badge_width - 2}" height="{badge_height - 2}" rx="11" ry="11" fill="none" stroke="#444" stroke-width="2"/>
  <text x="24" y="34" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="22" fill="#fff">
    <tspan fill="#aaa">&#x1F465;</tspan>
    <tspan dx="12" fill="#fff">{line1}</tspan>
  </text>
  <text x="24" y="66" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" fill="#888">
    {line2}
  </text>
</svg>'''

    return svg


def get_monthly_visitors_badge_svg() -> str:
    """
    Main function to get the complete badge SVG.
    Handles caching, log parsing, and SVG generation.
    """
    try:
        count = get_monthly_visitor_count()

        if count == 0:
            # If no data, show "New!" instead
            return generate_badge_svg("New!")

        formatted_count = format_visitor_count(count)
        return generate_badge_svg(formatted_count)

    except Exception as e:
        print(f"Error generating badge: {e}")
        # Return a fallback badge on error
        return generate_badge_svg("N/A")
