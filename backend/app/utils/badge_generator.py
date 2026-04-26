"""
Badge Generator Utility

Generates SVG badges for displaying visitor statistics.
Parses CloudFront logs from S3 and caches results in DynamoDB.
"""

import boto3
import gzip
import io
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional, Set
from urllib.parse import unquote

# S3 bucket containing CloudFront logs
CLOUDFRONT_LOGS_BUCKET = "infrasketch-cloudfront-logs-059409992371"
CLOUDFRONT_LOGS_PREFIX = "cloudfront/"

# Bot detection patterns (case-insensitive)
BOT_PATTERNS = [
    r"bot",
    r"crawler",
    r"spider",
    r"scraper",
    r"facebook",
    r"facebookexternalhit",
    r"googlebot",
    r"bingbot",
    r"yandex",
    r"baidu",
    r"duckduckbot",
    r"slurp",  # Yahoo
    r"semrush",
    r"ahrefs",
    r"mj12bot",
    r"dotbot",
    r"petalbot",
    r"bytespider",
    r"gptbot",
    r"claudebot",
    r"anthropic",
    r"ccbot",
    r"dataforseo",
    r"headless",
    r"phantomjs",
    r"selenium",
    r"puppeteer",
    r"playwright",
    r"curl",
    r"wget",
    r"python-requests",
    r"python-urllib",
    r"go-http-client",
    r"java/",
    r"libwww",
    r"apache-httpclient",
    r"okhttp",
    r"axios",
    r"node-fetch",
    r"undici",
]

# Compile regex pattern for efficiency
BOT_REGEX = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)

# Asset file extensions to exclude
ASSET_EXTENSIONS = {
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".webp", ".avif"
}

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


def is_bot(user_agent: str) -> bool:
    """Check if user agent string indicates a bot/crawler."""
    if not user_agent or user_agent == "-":
        return True  # No user agent is suspicious
    # URL decode the user agent (CloudFront logs are URL-encoded)
    decoded_ua = unquote(user_agent)
    return bool(BOT_REGEX.search(decoded_ua))


def is_asset_request(uri_stem: str) -> bool:
    """Check if the request is for a static asset (not a page view)."""
    if not uri_stem:
        return True
    # Check if it ends with an asset extension
    uri_lower = uri_stem.lower()
    for ext in ASSET_EXTENSIONS:
        if uri_lower.endswith(ext):
            return True
    # Also exclude /assets/ directory
    if "/assets/" in uri_lower:
        return True
    return False


def read_cached_visitor_count_any_age() -> Optional[int]:
    """
    Read the cached visitor count from DynamoDB regardless of TTL.
    Returns None only when no cache row exists at all.

    The serving endpoint uses this so it never parses S3 logs in the request
    path (would exceed API Gateway's 30s timeout). The cache is refreshed
    asynchronously by the infrasketch-visitor-count-refresh Lambda.
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
        return int(item.get("visitor_count", {}).get("N", 0))
    except Exception as e:
        print(f"Error reading cached visitor count: {e}")
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


def _list_log_keys_in_window(s3, start_date: datetime, end_date: datetime) -> list:
    """List CloudFront log keys whose filename date falls within [start_date, end_date]."""
    keys: list = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=CLOUDFRONT_LOGS_BUCKET,
        Prefix=CLOUDFRONT_LOGS_PREFIX,
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Filename format: E2YM028NUBX2QN.YYYY-MM-DD-HH.xxxxx.gz
            try:
                filename = key.split("/")[-1]
                parts = filename.split(".")
                if len(parts) < 2:
                    continue
                date_str = parts[1][:10]
                log_date = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, IndexError):
                continue
            if start_date <= log_date <= end_date:
                keys.append(key)
    return keys


def _parse_log_file_unique_ips(s3, key: str) -> Set[str]:
    """Download, decompress, and parse one CloudFront log file. Returns unique human IPs."""
    ips: Set[str] = set()
    try:
        response = s3.get_object(Bucket=CLOUDFRONT_LOGS_BUCKET, Key=key)
        if key.endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(response["Body"].read())) as f:
                content = f.read().decode("utf-8")
        else:
            content = response["Body"].read().decode("utf-8")

        # CloudFront log fields (tab-separated):
        # 0: date, 1: time, 2: x-edge-location, 3: sc-bytes, 4: c-ip,
        # 5: cs-method, 6: cs(Host), 7: cs-uri-stem, 8: sc-status,
        # 9: cs(Referer), 10: cs(User-Agent), ...
        for line in content.split("\n"):
            if line.startswith("#") or not line.strip():
                continue
            fields = line.split("\t")
            if len(fields) < 11:
                continue
            ip = fields[4]
            uri_stem = fields[7]
            user_agent = fields[10]
            if is_asset_request(uri_stem):
                continue
            if is_bot(user_agent):
                continue
            ips.add(ip)
    except Exception as e:
        print(f"Error parsing log file {key}: {e}")
    return ips


def parse_cloudfront_logs_for_unique_ips(days: int = 30, max_workers: int = 32) -> int:
    """
    Parse CloudFront logs from S3 and count unique human visitor IPs.

    Filters out:
    - Bots and crawlers (based on User-Agent)
    - Asset requests (JS, CSS, images, etc.)

    Downloads in parallel because the bucket holds tens of thousands of small
    gzipped logs and a sequential pass exceeds Lambda's max timeout.

    Args:
        days: Number of days to look back (default 30)
        max_workers: Concurrent S3 GETs (boto3 clients are thread-safe)

    Returns:
        Count of unique human IP addresses
    """
    s3 = get_s3_client()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    try:
        keys = _list_log_keys_in_window(s3, start_date, end_date)
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return 0

    print(f"Parsing {len(keys)} CloudFront log files (lookback={days}d, workers={max_workers})")

    unique_ips: Set[str] = set()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_parse_log_file_unique_ips, s3, k) for k in keys]
        for fut in as_completed(futures):
            unique_ips.update(fut.result())

    return len(unique_ips)


def format_visitor_count(count: int) -> str:
    """
    Format visitor count for display with commas (e.g., 1996 -> "1,996").
    No rounding - display the full number.
    """
    return f"{count:,}"


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
    Build the monthly-visitors SVG badge from the DynamoDB cache only.

    Must stay fast (well under API Gateway's 30s timeout). The cache is
    populated by the infrasketch-visitor-count-refresh scheduled Lambda;
    this function never parses CloudFront logs itself.
    """
    try:
        count = read_cached_visitor_count_any_age()

        if not count:
            return generate_badge_svg("New!")

        return generate_badge_svg(format_visitor_count(count))

    except Exception as e:
        print(f"Error generating badge: {e}")
        return generate_badge_svg("N/A")
