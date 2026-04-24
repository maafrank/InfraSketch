#!/usr/bin/env python3
"""
AWS Lambda function for automated daily social media posts with search insights.

Triggered by EventBridge on a daily schedule:
1. Determine today's insight category (rotates through 7 categories)
2. Extract relevant data from search console snapshot
3. Generate branded chart image with matplotlib
4. Convert chart to short MP4 video
5. Generate platform-specific captions with Claude
6. Upload video to all platforms via Upload-Post API
7. Record post in DynamoDB for deduplication

Usage (local testing):
    python scripts/lambda_social_insights.py

Environment variables:
    ANTHROPIC_API_KEY - Claude API key (or ANTHROPIC_API_KEY_SECRET for Secrets Manager)
    UPLOAD_POST_API_KEY - Upload-Post API key (or UPLOAD_POST_API_KEY_SECRET)
    AWS_REGION - AWS region (default: us-east-1)
"""

import io
import os
import sys
import json
import struct
import time
import zlib
import tempfile
from datetime import datetime
from decimal import Decimal

import boto3
import requests
from botocore.exceptions import ClientError

# Add parent directory for imports when running locally
sys.path.insert(0, os.path.dirname(__file__))

from search_console_data import (
    DAILY_TRENDS,
    TOP_QUERIES,
    TOP_PAGES,
    COUNTRIES,
    DEVICES,
    GROWTH_METRICS,
    get_top_queries,
    get_opportunity_queries,
    get_growth_trend,
)

# ---------------------------------------------------------------------------
# Secrets management (same pattern as lambda_blog_publisher.py)
# ---------------------------------------------------------------------------
try:
    from app.utils.secrets import get_anthropic_api_key
except ImportError:
    _secrets_cache = {}

    def _get_secret(secret_name: str, key_name: str = None) -> str:
        cache_key = f"{secret_name}:{key_name}" if key_name else secret_name
        if cache_key in _secrets_cache:
            return _secrets_cache[cache_key]

        client = boto3.client(
            "secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        try:
            response = client.get_secret_value(SecretId=secret_name)
            secret = response["SecretString"]
            if key_name:
                try:
                    secret_dict = json.loads(secret)
                    secret = secret_dict.get(key_name, secret)
                except json.JSONDecodeError:
                    pass
            _secrets_cache[cache_key] = secret
            return secret
        except ClientError as e:
            print(f"Error fetching secret {secret_name}: {e}")
            return None

    def get_anthropic_api_key():
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return key
        secret_name = os.environ.get(
            "ANTHROPIC_API_KEY_SECRET", "infrasketch/anthropic-api-key"
        )
        return _get_secret(secret_name, "ANTHROPIC_API_KEY")


def get_upload_post_api_key():
    key = os.environ.get("UPLOAD_POST_API_KEY")
    if key:
        return key
    secret_name = os.environ.get(
        "UPLOAD_POST_API_KEY_SECRET", "infrasketch/upload-post-api-key"
    )
    return _get_secret(secret_name, "UPLOAD_POST_API_KEY")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TABLE_NAME = "infrasketch-social-insights"
REGION = os.getenv("AWS_REGION", "us-east-1")
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"
UPLOAD_POST_STATUS_URL = "https://api.upload-post.com/api/uploadposts/status"
UPLOAD_POST_PROFILE = "InfraSketch"
LINKEDIN_PAGE_ID = "110574199"

# InfraSketch brand colors
BRAND_GREEN = "#00b830"
BRAND_DARK = "#0d1117"
BRAND_TEXT = "#e6edf3"
BRAND_MUTED = "#8b949e"

INSIGHT_CATEGORIES = [
    "growth_milestone",
    "top_queries",
    "geographic_reach",
    "top_content",
    "opportunity_queries",
    "device_breakdown",
    "weekly_summary",
]

# All available chart types for multi-chart videos (pick 5 randomly per video)
ALL_CHART_TYPES = [
    "growth_impressions",       # Line: impressions over 90 days
    "growth_clicks",            # Line: clicks over 90 days
    "ctr_trend",                # Line: CTR over 90 days
    "position_trend",           # Line: avg search position over 90 days (inverted)
    "top_queries_impressions",  # H-bar: top 10 queries by impressions
    "top_queries_clicks",       # H-bar: top queries by clicks
    "top_countries_clicks",     # H-bar: top 10 countries by clicks
    "top_countries_impressions",# H-bar: top 10 countries by impressions
    "top_content",              # H-bar: top 5 pages by clicks
    "blog_impressions",         # H-bar: top blog posts by impressions
    "opportunity_queries",      # H-bar: high impression, low CTR queries
    "device_breakdown",         # Pie: desktop vs mobile vs tablet
    "branded_vs_unbranded",     # Pie: branded (infrasketch) vs unbranded queries
    "weekly_impressions",       # Vertical bar: impressions grouped by week
    "weekly_summary",           # Stats infographic: 4 big numbers
]
CHARTS_PER_VIDEO = 5

# Caption generation prompt
CAPTION_PROMPT = """You are a social media manager for InfraSketch (https://infrasketch.net), an AI-powered system design tool that generates architecture diagrams from natural language.

Generate social media captions for a post about this search performance insight:

Category: {category}
Insight data: {insight_summary}

Write captions for these platforms (each as a separate section):

1. **YouTube Title** (max 100 chars): Short, engaging title for a YouTube Short
2. **YouTube Description** (max 500 chars): Brief description with the insight, CTA to infrasketch.net, and relevant hashtags
3. **TikTok Caption** (max 300 chars): Casual, engaging caption with hashtags
4. **Instagram Caption** (max 500 chars): Visual-focused caption with hashtags and CTA

Guidelines:
- Lead with the most impressive data point
- Include specific numbers (percentages, counts)
- Always mention infrasketch.net as the CTA
- Use hashtags: #systemdesign #infrasketch #softwarearchitecture #programming #tech
- Do NOT use em-dashes
- Keep it authentic and data-driven, not salesy
- Mark as AI-generated content where appropriate

Return ONLY a JSON object with keys: youtube_title, youtube_desc, tiktok, instagram"""


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------
def get_dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def reserve_post(today: str, category: str):
    """Reserve today's post slot in DynamoDB BEFORE uploading.

    Uses a conditional put so that only the first invocation wins.
    Returns True if the reservation was acquired, False if another
    invocation already claimed this date.
    """
    table = get_dynamodb_table()
    try:
        table.put_item(
            Item={
                "post_date": today,
                "category": category,
                "status": "reserved",
                "created_at": datetime.utcnow().isoformat(),
            },
            ConditionExpression="attribute_not_exists(post_date)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def record_post(today: str, category: str, captions: dict, upload_result: dict):
    """Update the reserved post record with upload results."""
    table = get_dynamodb_table()
    table.update_item(
        Key={"post_date": today},
        UpdateExpression="SET #s = :status, captions = :captions, upload_request_id = :rid, uploaded_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "posted",
            ":captions": json.dumps(captions),
            ":rid": upload_result.get("request_id", ""),
            ":now": datetime.utcnow().isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Insight data extraction
# ---------------------------------------------------------------------------
def get_insight_data(category: str) -> dict:
    """Extract relevant data for the given insight category."""
    if category == "growth_milestone":
        trend = get_growth_trend()
        return {
            "type": "growth",
            "summary": (
                f"InfraSketch search impressions grew {trend['growth_pct']:.0f}% "
                f"in 90 days. From {trend['early_avg']:.0f} daily impressions "
                f"to {trend['recent_avg']:.0f}. "
                f"Total: {GROWTH_METRICS['total_impressions_90d']:,} impressions, "
                f"{GROWTH_METRICS['total_clicks_90d']} clicks."
            ),
            "chart_data": DAILY_TRENDS,
        }
    elif category == "top_queries":
        top = get_top_queries(10)
        query_list = ", ".join(f'"{q["query"]}" ({q["impressions"]} impr)' for q in top[:5])
        return {
            "type": "queries",
            "summary": (
                f"Top search queries finding InfraSketch: {query_list}. "
                f"Engineers are searching for system design and architecture tools."
            ),
            "chart_data": top,
        }
    elif category == "geographic_reach":
        top_countries = COUNTRIES[:10]
        country_list = ", ".join(f'{c["country"]} ({c["clicks"]} clicks)' for c in top_countries[:5])
        return {
            "type": "countries",
            "summary": (
                f"InfraSketch is being discovered by engineers in {GROWTH_METRICS['total_countries']}+ countries. "
                f"Top: {country_list}."
            ),
            "chart_data": top_countries,
        }
    elif category == "top_content":
        top_pages = sorted(TOP_PAGES, key=lambda p: p["clicks"], reverse=True)[:5]
        page_list = ", ".join(
            f'{p["page"].split("/")[-1]} ({p["clicks"]} clicks)' for p in top_pages
        )
        return {
            "type": "pages",
            "summary": (
                f"Top performing content on InfraSketch: {page_list}. "
                f"Blog posts about system design are driving organic traffic."
            ),
            "chart_data": top_pages,
        }
    elif category == "opportunity_queries":
        opportunities = get_opportunity_queries()[:10]
        opp_list = ", ".join(f'"{o["query"]}" ({o["impressions"]} impr)' for o in opportunities[:5])
        return {
            "type": "opportunities",
            "summary": (
                f"High-potential search queries: {opp_list}. "
                f"Engineers are searching for these terms and finding InfraSketch, "
                f"but not clicking yet. {len(opportunities)} opportunity queries identified."
            ),
            "chart_data": opportunities,
        }
    elif category == "device_breakdown":
        total_impr = sum(d["impressions"] for d in DEVICES)
        device_pcts = [
            f'{d["device"]} {d["impressions"] / max(total_impr, 1) * 100:.0f}%'
            for d in DEVICES
        ]
        return {
            "type": "devices",
            "summary": (
                f"Device breakdown for InfraSketch search traffic: {', '.join(device_pcts)}. "
                f"Engineers primarily discover InfraSketch from desktop, designing at their workstations."
            ),
            "chart_data": DEVICES,
        }
    else:  # weekly_summary
        trend = get_growth_trend()
        top_query = get_top_queries(1)[0]
        top_country = COUNTRIES[0]
        return {
            "type": "summary",
            "summary": (
                f"Weekly InfraSketch search stats: "
                f"{GROWTH_METRICS['total_impressions_90d']:,} total impressions, "
                f"{GROWTH_METRICS['total_clicks_90d']} clicks, "
                f"{GROWTH_METRICS['total_countries']}+ countries, "
                f"top query: \"{top_query['query']}\" ({top_query['impressions']} impr), "
                f"top country: {top_country['country']}. "
                f"Growth: {trend['growth_pct']:.0f}% over 90 days."
            ),
            "chart_data": {
                "trends": DAILY_TRENDS[-14:],
                "top_queries": get_top_queries(5),
                "top_countries": COUNTRIES[:5],
            },
        }


# ---------------------------------------------------------------------------
# Chart generation (matplotlib) - 15 chart types
# ---------------------------------------------------------------------------
def _setup_chart():
    """Common chart setup: returns (fig, ax) with brand styling."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(BRAND_DARK)
    ax.set_facecolor(BRAND_DARK)
    ax.tick_params(colors=BRAND_TEXT, labelsize=11)
    for spine in ax.spines.values():
        spine.set_color(BRAND_MUTED)
    return fig, ax


def _finalize_chart(fig, ax) -> bytes:
    """Add branding, logo overlay, return PNG bytes."""
    from PIL import Image

    fig.text(
        0.5, 0.02, "infrasketch.net",
        ha="center", fontsize=14, color=BRAND_GREEN, fontweight="bold",
    )
    import matplotlib.pyplot as plt
    plt.tight_layout(rect=[0, 0.05, 1, 1])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BRAND_DARK, bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)

    chart_img = Image.open(buf).convert("RGBA")
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo_size = int(chart_img.width * 0.08)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        padding = 20
        x = chart_img.width - logo_size - padding
        y = padding
        chart_img.paste(logo, (x, y), logo)

    out = io.BytesIO()
    chart_img.convert("RGB").save(out, format="PNG")
    out.seek(0)
    return out.read()


def _draw_line_chart(ax, dates, values, title, ylabel, color=None, annotation=None):
    """Helper for line charts with fill."""
    from matplotlib.ticker import MaxNLocator
    c = color or BRAND_GREEN
    ax.fill_between(range(len(dates)), values, alpha=0.3, color=c)
    ax.plot(range(len(dates)), values, color=c, linewidth=2.5)
    ax.set_title(title, color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("Date", color=BRAND_TEXT, fontsize=13)
    ax.set_ylabel(ylabel, color=BRAND_TEXT, fontsize=13)
    tick_positions = list(range(0, len(dates), 15))
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([dates[i] for i in tick_positions], rotation=45)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    if annotation:
        ax.annotate(
            annotation, xy=(len(dates) - 1, values[-1]),
            fontsize=24, fontweight="bold", color=c, ha="right", va="bottom",
        )


def _draw_hbar_chart(ax, labels, values, title, xlabel, color=None):
    """Helper for horizontal bar charts with value labels."""
    c = color or BRAND_GREEN
    labels_r = list(reversed(labels))
    values_r = list(reversed(values))
    bars = ax.barh(labels_r, values_r, color=c, height=0.6)
    ax.set_title(title, color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel(xlabel, color=BRAND_TEXT, fontsize=13)
    max_val = max(values_r) if values_r else 1
    offset = max_val * 0.01 + 0.3
    for bar, val in zip(bars, values_r):
        ax.text(
            val + offset, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", color=BRAND_TEXT, fontsize=11,
        )


def generate_single_chart(chart_type: str) -> bytes:
    """Generate a branded 1080x1080 chart image as PNG bytes for a specific chart type."""
    fig, ax = _setup_chart()

    if chart_type == "growth_impressions":
        dates = [d["date"][5:] for d in DAILY_TRENDS]
        values = [d["impressions"] for d in DAILY_TRENDS]
        trend = get_growth_trend()
        _draw_line_chart(ax, dates, values,
                         "InfraSketch Search Impressions (90 Days)",
                         "Daily Impressions",
                         annotation=f"+{trend['growth_pct']:,.0f}%")

    elif chart_type == "growth_clicks":
        dates = [d["date"][5:] for d in DAILY_TRENDS]
        values = [d["clicks"] for d in DAILY_TRENDS]
        total = sum(values)
        _draw_line_chart(ax, dates, values,
                         "InfraSketch Search Clicks (90 Days)",
                         "Daily Clicks", color="#1f6feb",
                         annotation=f"{total} total")

    elif chart_type == "ctr_trend":
        dates = [d["date"][5:] for d in DAILY_TRENDS]
        values = [d["ctr"] for d in DAILY_TRENDS]
        _draw_line_chart(ax, dates, values,
                         "Click-Through Rate Over 90 Days",
                         "CTR (%)", color="#f0883e")

    elif chart_type == "position_trend":
        dates = [d["date"][5:] for d in DAILY_TRENDS]
        values = [d["position"] for d in DAILY_TRENDS]
        c = "#a371f7"
        ax.fill_between(range(len(dates)), values, alpha=0.3, color=c)
        ax.plot(range(len(dates)), values, color=c, linewidth=2.5)
        ax.set_title("Average Search Position (Lower = Better)",
                      color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)
        ax.set_xlabel("Date", color=BRAND_TEXT, fontsize=13)
        ax.set_ylabel("Avg Position", color=BRAND_TEXT, fontsize=13)
        ax.invert_yaxis()
        tick_positions = list(range(0, len(dates), 15))
        ax.set_xticks(tick_positions)
        ax.set_xticklabels([dates[i] for i in tick_positions], rotation=45)
        recent_pos = sum(d["position"] for d in DAILY_TRENDS[-7:]) / 7
        ax.annotate(f"Avg: {recent_pos:.1f}",
                     xy=(len(dates) - 1, values[-1]),
                     fontsize=24, fontweight="bold", color=c, ha="right", va="top")

    elif chart_type == "top_queries_impressions":
        top = get_top_queries(10)
        labels = [q["query"][:30] for q in top]
        values = [q["impressions"] for q in top]
        _draw_hbar_chart(ax, labels, values,
                         "Top Search Queries by Impressions", "Impressions")

    elif chart_type == "top_queries_clicks":
        top = sorted(TOP_QUERIES, key=lambda q: q["clicks"], reverse=True)[:10]
        top = [q for q in top if q["clicks"] > 0]
        labels = [q["query"][:30] for q in top]
        values = [q["clicks"] for q in top]
        _draw_hbar_chart(ax, labels, values,
                         "Top Search Queries by Clicks", "Clicks", color="#1f6feb")

    elif chart_type == "top_countries_clicks":
        top = COUNTRIES[:10]
        labels = [c["country"] for c in top]
        values = [c["clicks"] for c in top]
        _draw_hbar_chart(ax, labels, values,
                         "Top Countries Discovering InfraSketch", "Clicks")

    elif chart_type == "top_countries_impressions":
        top = sorted(COUNTRIES, key=lambda c: c["impressions"], reverse=True)[:10]
        labels = [c["country"] for c in top]
        values = [c["impressions"] for c in top]
        _draw_hbar_chart(ax, labels, values,
                         "Top Countries by Search Impressions", "Impressions",
                         color="#1f6feb")

    elif chart_type == "top_content":
        top_pages = sorted(TOP_PAGES, key=lambda p: p["clicks"], reverse=True)[:5]
        labels = []
        for p in top_pages:
            name = p["page"].replace("/blog/", "").replace("-", " ").title()
            if len(name) > 25:
                name = name[:22] + "..."
            labels.append(name)
        values = [p["clicks"] for p in top_pages]
        _draw_hbar_chart(ax, labels, values, "Top Performing Content", "Clicks")

    elif chart_type == "blog_impressions":
        blog_pages = sorted(
            [p for p in TOP_PAGES if "/blog/" in p["page"]],
            key=lambda p: p["impressions"], reverse=True,
        )[:8]
        labels = []
        for p in blog_pages:
            name = p["page"].replace("/blog/", "").replace("-", " ").title()
            if len(name) > 30:
                name = name[:27] + "..."
            labels.append(name)
        values = [p["impressions"] for p in blog_pages]
        _draw_hbar_chart(ax, labels, values,
                         "Blog Posts by Search Impressions", "Impressions",
                         color="#f0883e")

    elif chart_type == "opportunity_queries":
        opportunities = get_opportunity_queries()[:10]
        labels = [q["query"][:30] for q in opportunities]
        values = [q["impressions"] for q in opportunities]
        _draw_hbar_chart(ax, labels, values,
                         "Untapped Search Opportunities",
                         "Impressions (Low CTR)", color="#ff6b35")

    elif chart_type == "device_breakdown":
        labels = [d["device"].capitalize() for d in DEVICES]
        sizes = [d["impressions"] for d in DEVICES]
        colors = [BRAND_GREEN, "#1f6feb", "#f0883e"]
        explode = [0.05] * len(labels)
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.0f%%", colors=colors,
            explode=explode, textprops={"color": BRAND_TEXT, "fontsize": 14},
            pctdistance=0.75,
        )
        for autotext in autotexts:
            autotext.set_fontsize(16)
            autotext.set_fontweight("bold")
        ax.set_title("Search Traffic by Device",
                      color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)

    elif chart_type == "branded_vs_unbranded":
        branded = sum(q["impressions"] for q in TOP_QUERIES
                      if "infrasketch" in q["query"].lower())
        total = sum(q["impressions"] for q in TOP_QUERIES)
        unbranded = total - branded
        labels = ["Branded\n(infrasketch)", "Unbranded\n(organic)"]
        sizes = [branded, unbranded]
        colors = [BRAND_GREEN, "#1f6feb"]
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.0f%%", colors=colors,
            explode=[0.05, 0.05],
            textprops={"color": BRAND_TEXT, "fontsize": 14},
            pctdistance=0.75,
        )
        for autotext in autotexts:
            autotext.set_fontsize(16)
            autotext.set_fontweight("bold")
        ax.set_title("Branded vs Organic Search Queries",
                      color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)

    elif chart_type == "weekly_impressions":
        # Group daily data into weeks
        week_data = {}
        for d in DAILY_TRENDS:
            # Use ISO week
            from datetime import datetime as dt
            date = dt.strptime(d["date"], "%Y-%m-%d")
            week_key = date.strftime("%m/%d")
            week_num = date.isocalendar()[1]
            if week_num not in week_data:
                week_data[week_num] = {"label": week_key, "impressions": 0}
            week_data[week_num]["impressions"] += d["impressions"]
        weeks = sorted(week_data.keys())
        labels = [week_data[w]["label"] for w in weeks]
        values = [week_data[w]["impressions"] for w in weeks]
        bars = ax.bar(labels, values, color=BRAND_GREEN, width=0.7)
        ax.set_title("Weekly Search Impressions",
                      color=BRAND_TEXT, fontsize=18, fontweight="bold", pad=20)
        ax.set_xlabel("Week Starting", color=BRAND_TEXT, fontsize=13)
        ax.set_ylabel("Impressions", color=BRAND_TEXT, fontsize=13)
        ax.tick_params(axis="x", rotation=45)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                    f"{val:,}", ha="center", va="bottom",
                    color=BRAND_TEXT, fontsize=9)

    elif chart_type == "weekly_summary":
        ax.axis("off")
        ax.set_title("InfraSketch Search Stats (90 Days)",
                      color=BRAND_TEXT, fontsize=22, fontweight="bold", pad=20)
        stats = [
            (f"{GROWTH_METRICS['total_impressions_90d']:,}", "Total Impressions"),
            (f"{GROWTH_METRICS['total_clicks_90d']}", "Total Clicks"),
            (f"{GROWTH_METRICS['total_countries']}+", "Countries"),
            (f"{GROWTH_METRICS['total_unique_queries']:,}", "Unique Queries"),
        ]
        for i, (value, label) in enumerate(stats):
            row = i // 2
            col = i % 2
            x = 0.25 + col * 0.5
            y = 0.65 - row * 0.35
            ax.text(x, y, value, fontsize=42, fontweight="bold",
                    color=BRAND_GREEN, ha="center", va="center",
                    transform=ax.transAxes)
            ax.text(x, y - 0.08, label, fontsize=16,
                    color=BRAND_MUTED, ha="center", va="center",
                    transform=ax.transAxes)

    return _finalize_chart(fig, ax)


def generate_chart(category: str, data: dict) -> bytes:
    """Legacy wrapper: generate a chart for an insight category."""
    type_map = {
        "growth_milestone": "growth_impressions",
        "top_queries": "top_queries_impressions",
        "geographic_reach": "top_countries_clicks",
        "top_content": "top_content",
        "opportunity_queries": "opportunity_queries",
        "device_breakdown": "device_breakdown",
        "weekly_summary": "weekly_summary",
    }
    chart_type = type_map.get(category, "weekly_summary")
    return generate_single_chart(chart_type)


def select_charts_for_today(seed_date: str = None) -> list:
    """Pick CHARTS_PER_VIDEO chart types using a date-based seed for reproducibility."""
    import random
    if seed_date is None:
        seed_date = datetime.utcnow().strftime("%Y-%m-%d")
    rng = random.Random(seed_date)
    return rng.sample(ALL_CHART_TYPES, CHARTS_PER_VIDEO)


def generate_chart_set(chart_types: list) -> list:
    """Generate PNG bytes for each chart type. Returns list of (chart_type, png_bytes)."""
    results = []
    for ct in chart_types:
        png = generate_single_chart(ct)
        results.append((ct, png))
        print(f"  Chart {ct}: {len(png)} bytes")
    return results


# ---------------------------------------------------------------------------
# Voiceover generation (Amazon Polly)
# ---------------------------------------------------------------------------
def generate_voiceover_text(category: str, data: dict) -> str:
    """Create a short voiceover script from insight data."""
    summary = data["summary"]

    if category == "growth_milestone":
        return (
            f"InfraSketch search growth update. {summary} "
            "Design your system architecture in seconds at infrasketch.net."
        )
    elif category == "top_queries":
        return (
            f"What developers are searching for. {summary} "
            "Try InfraSketch free at infrasketch.net."
        )
    elif category == "geographic_reach":
        return (
            f"InfraSketch is going global. {summary} "
            "Join developers worldwide at infrasketch.net."
        )
    elif category == "top_content":
        return (
            f"Our top performing content this week. {summary} "
            "Explore more at infrasketch.net."
        )
    elif category == "opportunity_queries":
        return (
            f"Search opportunities we're targeting. {summary} "
            "See what InfraSketch can do at infrasketch.net."
        )
    elif category == "device_breakdown":
        return (
            f"How developers find InfraSketch. {summary} "
            "Try it yourself at infrasketch.net."
        )
    else:  # weekly_summary
        return (
            f"InfraSketch weekly search stats. {summary} "
            "Start designing at infrasketch.net."
        )


def generate_voiceover(text: str) -> bytes:
    """
    Generate voiceover audio using Amazon Polly.

    Returns raw PCM audio bytes (16-bit signed, mono, 16000 Hz).
    """
    polly = boto3.client("polly", region_name=REGION)

    # Keep text under Polly's 3000 char limit
    if len(text) > 2900:
        text = text[:2900]

    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="pcm",
        SampleRate="16000",
        VoiceId="Matthew",
        Engine="neural",
    )

    audio_bytes = response["AudioStream"].read()
    print(f"Voiceover generated: {len(audio_bytes)} bytes ({len(audio_bytes) / 32000:.1f}s)")
    return audio_bytes


# ---------------------------------------------------------------------------
# Video creation from chart images (supports multi-chart slideshows)
# ---------------------------------------------------------------------------
def create_video_from_charts(chart_png_list: list, output_path: str, duration: int = 10,
                             audio_pcm: bytes = None, audio_sample_rate: int = 16000):
    """
    Create a video from one or more chart PNG images.

    chart_png_list: list of PNG bytes (each shown for equal time)
    If audio_pcm is provided, video duration extends to match audio length.
    Falls back to AVI if PyAV is not available (Lambda environment).
    """
    return _create_avi_multi(chart_png_list, output_path, duration,
                             audio_pcm, audio_sample_rate)


def create_video_from_chart(chart_png_bytes: bytes, output_path: str, duration: int = 10,
                            audio_pcm: bytes = None, audio_sample_rate: int = 16000):
    """Legacy wrapper for single-chart video."""
    return create_video_from_charts([chart_png_bytes], output_path, duration,
                                    audio_pcm, audio_sample_rate)


def _create_avi_multi(chart_png_list: list, output_path: str, duration: int = 10,
                      audio_pcm: bytes = None, audio_sample_rate: int = 16000):
    """
    Create an AVI video slideshow from multiple chart images using pure Python.
    Each chart is shown for an equal portion of the total duration.
    Supports optional PCM audio stream (16-bit signed mono).
    """
    from PIL import Image

    # Prepare JPEG frames for each chart
    jpeg_frames = []
    for png_bytes in chart_png_list:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        img = img.resize((1080, 1080), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        jpeg_frames.append(buf.getvalue())

    width, height = 1080, 1080
    fps = 1
    num_charts = len(jpeg_frames)

    # If audio is provided, extend video duration to match audio length
    if audio_pcm:
        bytes_per_sample = 2  # 16-bit
        audio_duration = len(audio_pcm) / (audio_sample_rate * bytes_per_sample)
        duration = max(duration, int(audio_duration) + 1)

    total_frames = duration * fps

    # Calculate how long each chart shows (in frames)
    frames_per_chart = max(1, total_frames // num_charts)

    # Build frame sequence: which JPEG to show at each second
    frame_sequence = []
    for i in range(total_frames):
        chart_idx = min(i // frames_per_chart, num_charts - 1)
        frame_sequence.append(chart_idx)

    # Find the largest frame for the suggested buffer size
    max_frame_size = max(len(f) for f in jpeg_frames)

    has_audio = audio_pcm is not None and len(audio_pcm) > 0
    num_streams = 2 if has_audio else 1
    block_align = 2  # 16-bit mono
    avg_bytes_per_sec = audio_sample_rate * block_align if has_audio else 0

    # Audio: split PCM into per-frame chunks (1 second each at 1fps)
    audio_chunks = []
    if has_audio:
        chunk_size = audio_sample_rate * block_align
        padded_audio = audio_pcm + b"\x00" * max(0, chunk_size * total_frames - len(audio_pcm))
        for i in range(total_frames):
            start = i * chunk_size
            audio_chunks.append(padded_audio[start:start + chunk_size])

    def write_chunk(fid, chunk_id, data):
        fid.write(chunk_id)
        fid.write(struct.pack("<I", len(data)))
        fid.write(data)
        if len(data) % 2:
            fid.write(b"\x00")

    # Build movi data (interleaved video + audio)
    movi_data = io.BytesIO()
    for i in range(total_frames):
        jpeg_bytes = jpeg_frames[frame_sequence[i]]
        frame_size = len(jpeg_bytes)
        # Video chunk (stream 0)
        movi_data.write(b"00dc")
        movi_data.write(struct.pack("<I", frame_size))
        movi_data.write(jpeg_bytes)
        if frame_size % 2:
            movi_data.write(b"\x00")
        # Audio chunk (stream 1)
        if has_audio:
            aud = audio_chunks[i]
            movi_data.write(b"01wb")
            movi_data.write(struct.pack("<I", len(aud)))
            movi_data.write(aud)
            if len(aud) % 2:
                movi_data.write(b"\x00")
    movi_bytes = movi_data.getvalue()

    # --- Build hdrl ---
    avih_data = struct.pack(
        "<14I",
        int(1000000 / fps),  # microseconds per frame
        0, 0,
        0x10,  # flags (AVIF_HASINDEX)
        total_frames, 0,
        num_streams,
        max_frame_size,
        width, height,
        0, 0, 0, 0,
    )

    # Video stream header
    vid_strh_data = (
        b"vids" + b"MJPG"
        + struct.pack("<I", 0)  # flags
        + struct.pack("<HH", 0, 0)  # priority, language
        + struct.pack("<I", 0)  # initial frames
        + struct.pack("<II", 1, fps)  # scale, rate
        + struct.pack("<I", 0)  # start
        + struct.pack("<I", total_frames)  # length
        + struct.pack("<I", max_frame_size)  # suggested buffer
        + struct.pack("<II", 0, 0)  # quality, sample size
        + struct.pack("<4H", 0, 0, width, height)
    )

    vid_strf_data = struct.pack(
        "<IiiHH4sIiiII",
        40, width, height, 1, 24, b"MJPG",
        width * height * 3, 0, 0, 0, 0,
    )

    vid_strl = io.BytesIO()
    write_chunk(vid_strl, b"strh", vid_strh_data)
    write_chunk(vid_strl, b"strf", vid_strf_data)
    vid_strl_bytes = vid_strl.getvalue()

    hdrl_content = io.BytesIO()
    write_chunk(hdrl_content, b"avih", avih_data)
    hdrl_content.write(b"LIST")
    hdrl_content.write(struct.pack("<I", len(vid_strl_bytes) + 4))
    hdrl_content.write(b"strl")
    hdrl_content.write(vid_strl_bytes)

    if has_audio:
        total_audio_samples = audio_sample_rate * duration
        aud_strh_data = (
            b"auds" + b"\x01\x00\x00\x00"
            + struct.pack("<I", 0)
            + struct.pack("<HH", 0, 0)
            + struct.pack("<I", 0)
            + struct.pack("<II", 1, audio_sample_rate)
            + struct.pack("<I", 0)
            + struct.pack("<I", total_audio_samples)
            + struct.pack("<I", audio_sample_rate * block_align)
            + struct.pack("<II", 0, block_align)
            + struct.pack("<4H", 0, 0, 0, 0)
        )
        aud_strf_data = struct.pack(
            "<HHIIHHH",
            1, 1, audio_sample_rate, avg_bytes_per_sec, block_align, 16, 0,
        )
        aud_strl = io.BytesIO()
        write_chunk(aud_strl, b"strh", aud_strh_data)
        write_chunk(aud_strl, b"strf", aud_strf_data)
        aud_strl_bytes = aud_strl.getvalue()
        hdrl_content.write(b"LIST")
        hdrl_content.write(struct.pack("<I", len(aud_strl_bytes) + 4))
        hdrl_content.write(b"strl")
        hdrl_content.write(aud_strl_bytes)

    hdrl_bytes = hdrl_content.getvalue()

    riff_content = io.BytesIO()
    riff_content.write(b"LIST")
    riff_content.write(struct.pack("<I", len(hdrl_bytes) + 4))
    riff_content.write(b"hdrl")
    riff_content.write(hdrl_bytes)
    riff_content.write(b"LIST")
    riff_content.write(struct.pack("<I", len(movi_bytes) + 4))
    riff_content.write(b"movi")
    riff_content.write(movi_bytes)
    riff_bytes = riff_content.getvalue()

    avi_path = output_path.replace(".mp4", ".avi")
    with open(avi_path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", len(riff_bytes) + 4))
        f.write(b"AVI ")
        f.write(riff_bytes)

    audio_info = f", audio={len(audio_pcm)} bytes" if has_audio else ", no audio"
    print(f"Created AVI slideshow: {avi_path} ({duration}s, {fps}fps, "
          f"{num_charts} charts, ~{frames_per_chart}s each{audio_info})")
    return avi_path


# ---------------------------------------------------------------------------
# Caption generation (Claude API)
# ---------------------------------------------------------------------------
def generate_captions(category: str, insight_data: dict) -> dict:
    """Generate platform-specific captions using Claude."""
    import anthropic

    api_key = get_anthropic_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = CAPTION_PROMPT.format(
        category=category.replace("_", " ").title(),
        insight_summary=insight_data["summary"],
    )

    print(f"Generating captions for category: {category}")
    start_time = time.time()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed = time.time() - start_time
    print(f"Captions generated in {elapsed:.1f}s")

    # Parse JSON response
    text = response.content[0].text
    # Extract JSON from response (handle markdown code blocks)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        captions = json.loads(text.strip())
    except json.JSONDecodeError:
        print(f"Failed to parse captions JSON, using fallback. Raw: {text[:200]}")
        captions = {
            "youtube_title": f"InfraSketch Search Insights: {category.replace('_', ' ').title()}",
            "youtube_desc": insight_data["summary"][:500],
            "tiktok": insight_data["summary"][:300],
            "instagram": insight_data["summary"][:500],
        }

    return captions


# ---------------------------------------------------------------------------
# Upload-Post API integration
# ---------------------------------------------------------------------------
def upload_to_platforms(video_path: str, captions: dict) -> dict:
    """Upload video to all platforms via Upload-Post API."""
    api_key = get_upload_post_api_key()
    if not api_key:
        raise ValueError("UPLOAD_POST_API_KEY not configured")

    yt_title = captions.get("youtube_title", "InfraSketch Search Insights")[:100]
    yt_desc = captions.get("youtube_desc", "")[:5000]
    tiktok_caption = captions.get("tiktok", "")[:300]
    ig_caption = captions.get("instagram", "")[:2200]

    print(f"Uploading to all platforms: {yt_title}")

    with open(video_path, "rb") as video_file:
        response = requests.post(
            UPLOAD_POST_API_URL,
            headers={"Authorization": f"Apikey {api_key}"},
            files={"video": video_file},
            data={
                "user": UPLOAD_POST_PROFILE,
                "platform[]": [
                    "youtube", "tiktok", "instagram",
                    "facebook", "x", "threads", "linkedin",
                ],
                "target_linkedin_page_id": LINKEDIN_PAGE_ID,
                "title": yt_title,
                "youtube_title": yt_title,
                "youtube_description": yt_desc,
                "categoryId": "28",
                "containsSyntheticMedia": "true",
                "tiktok_title": tiktok_caption,
                "is_aigc": "true",
                "instagram_title": ig_caption,
                "threads_title": ig_caption,
            },
            timeout=60,
        )

    if response.status_code >= 400:
        raise Exception(
            f"Upload-Post API error (HTTP {response.status_code}): {response.text[:500]}"
        )

    result = response.json()
    print(f"Upload response: {json.dumps(result)[:200]}")
    return result


def poll_upload_status(request_id: str, max_polls: int = 10, interval: int = 30) -> dict:
    """Poll Upload-Post for processing completion."""
    api_key = get_upload_post_api_key()

    for i in range(max_polls):
        time.sleep(interval)
        print(f"Polling upload status ({i + 1}/{max_polls})...")

        try:
            response = requests.get(
                UPLOAD_POST_STATUS_URL,
                params={"request_id": request_id},
                headers={"Authorization": f"Apikey {api_key}"},
                timeout=15,
            )
            if response.ok:
                data = response.json()
                status = data.get("status", "unknown")
                print(f"Status: {status}")
                if status == "completed":
                    return data
                if status == "failed":
                    print(f"Upload processing failed: {data}")
                    return data
        except Exception as e:
            print(f"Poll error: {e}")

    print(f"Upload polling timed out after {max_polls * interval}s")
    return {"status": "timeout"}


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """
    Main Lambda handler for daily social media insights posting.

    Triggered by EventBridge schedule or manual invocation.
    """
    print(f"Starting social insights: {datetime.utcnow().isoformat()}")
    print(f"Event: {json.dumps(event)}")

    start_time = time.time()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # 1. Determine today's insight category (for captions/voiceover theme)
        day_of_year = datetime.utcnow().timetuple().tm_yday
        category_idx = day_of_year % len(INSIGHT_CATEGORIES)
        category = INSIGHT_CATEGORIES[category_idx]
        print(f"Today's category: {category} (day {day_of_year}, idx {category_idx})")

        # 2. Select 5 random charts for today's video
        selected_charts = select_charts_for_today(today)
        print(f"Selected charts: {selected_charts}")

        # 3. Generate all chart images
        print("Generating charts...")
        chart_set = generate_chart_set(selected_charts)
        chart_pngs = [png for _, png in chart_set]
        print(f"Generated {len(chart_pngs)} charts")

        # 4. Extract insight data (for captions and voiceover)
        insight_data = get_insight_data(category)
        print(f"Insight summary: {insight_data['summary'][:100]}...")

        # 5. Generate voiceover audio
        print("Generating voiceover...")
        vo_text = generate_voiceover_text(category, insight_data)
        try:
            audio_pcm = generate_voiceover(vo_text)
        except Exception as e:
            print(f"Voiceover generation failed, continuing without audio: {e}")
            audio_pcm = None

        # 6. Create multi-chart slideshow video (with audio if available)
        video_path = "/tmp/insight_video.mp4"
        video_path = create_video_from_charts(chart_pngs, video_path, duration=15,
                                               audio_pcm=audio_pcm)
        video_size = os.path.getsize(video_path)
        print(f"Video created: {video_size} bytes")

        # 7. Generate captions with Claude
        captions = generate_captions(category, insight_data)
        print(f"Captions: {json.dumps(captions)[:200]}...")

        # 8. Upload to all platforms
        upload_result = upload_to_platforms(video_path, captions)
        request_id = upload_result.get("request_id", "")

        # 9. Skip polling - Upload-Post processes asynchronously and the Lambda
        # timeout is too short to wait. The upload was accepted successfully.
        print(f"Upload accepted with request_id: {request_id}")

        # 10. Record in DynamoDB
        record_post(today, category, captions, upload_result)

        elapsed = time.time() - start_time
        print(f"Successfully posted in {elapsed:.1f}s")

        # Clean up /tmp
        for path in [video_path] + [f"/tmp/chart_{i}.png" for i in range(len(chart_pngs))]:
            if os.path.exists(path):
                os.remove(path)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Social insight posted successfully",
                "date": today,
                "category": category,
                "charts": selected_charts,
                "youtube_title": captions.get("youtube_title", ""),
                "duration_seconds": round(elapsed, 1),
            }),
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise


# ---------------------------------------------------------------------------
# Local testing
# ---------------------------------------------------------------------------
def main():
    """Run locally for testing."""
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    # Also try content pipeline .env
    load_dotenv(
        os.path.join(os.path.dirname(__file__), "..", "content-pipeline", ".env"),
        override=False,
    )

    print("=" * 60)
    print("Social Insights - Local Test")
    print("=" * 60)

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--category", "-c", help="Specific category to test")
    parser.add_argument("--dry-run", action="store_true", help="Skip upload")
    parser.add_argument("--all-charts", action="store_true", help="Generate all 15 chart types")
    parser.add_argument("--video", action="store_true", help="Generate multi-chart slideshow video")
    args = parser.parse_args()

    if args.all_charts:
        print(f"\nGenerating all {len(ALL_CHART_TYPES)} chart types...")
        for ct in ALL_CHART_TYPES:
            png = generate_single_chart(ct)
            out_path = f"/tmp/chart_{ct}.png"
            with open(out_path, "wb") as f:
                f.write(png)
            print(f"  {ct}: {len(png)} bytes -> {out_path}")
        print(f"\nAll {len(ALL_CHART_TYPES)} charts saved to /tmp/chart_*.png")
        return

    if args.video or args.dry_run:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        day_of_year = datetime.utcnow().timetuple().tm_yday
        category = INSIGHT_CATEGORIES[day_of_year % len(INSIGHT_CATEGORIES)]

        # Pick 5 random charts
        selected = select_charts_for_today(today)
        print(f"\nCategory: {category}")
        print(f"Selected charts: {selected}")

        # Generate charts
        print("\nGenerating charts...")
        chart_set = generate_chart_set(selected)
        chart_pngs = [png for _, png in chart_set]

        # Save individual charts
        for ct, png in chart_set:
            with open(f"/tmp/chart_{ct}.png", "wb") as f:
                f.write(png)

        # Generate voiceover
        data = get_insight_data(category)
        vo_text = generate_voiceover_text(category, data)
        print(f"\nVoiceover: {vo_text[:150]}...")

        try:
            audio_pcm = generate_voiceover(vo_text)
        except Exception as e:
            print(f"Polly not available locally, skipping audio: {e}")
            audio_pcm = None

        # Create multi-chart video
        video_path = "/tmp/insight_slideshow.mp4"
        video_path = create_video_from_charts(chart_pngs, video_path, duration=15,
                                               audio_pcm=audio_pcm)
        print(f"\nVideo: {video_path} ({os.path.getsize(video_path)} bytes)")

        if not args.dry_run:
            captions = generate_captions(category, data)
            print(f"\nCaptions:\n{json.dumps(captions, indent=2)}")
        else:
            print("\nDry run complete (upload skipped)")
        return

    if args.category:
        data = get_insight_data(args.category)
        chart_png = generate_chart(args.category, data)
        chart_path = f"/tmp/chart_{args.category}.png"
        with open(chart_path, "wb") as f:
            f.write(chart_png)
        print(f"Chart saved to: {chart_path}")
        return

    # Full run
    result = lambda_handler({}, None)
    print("\nResult:")
    print(json.dumps(json.loads(result["body"]), indent=2))


if __name__ == "__main__":
    main()
