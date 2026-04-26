#!/usr/bin/env python3
"""
Google Search Console data for InfraSketch.

Pulls LIVE data from the Google Search Console API (last 90 days).
Falls back to a static snapshot if the API is unavailable or returns
insufficient data (< 7 days).

Exports the same interface used by lambda_social_insights.py:
  DAILY_TRENDS, TOP_QUERIES, TOP_PAGES, COUNTRIES, DEVICES, GROWTH_METRICS,
  get_top_queries(), get_opportunity_queries(), get_growth_trend()
"""

import json
import os
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# ISO 3166-1 alpha-3 country code to name mapping (top 60 by web traffic)
# ---------------------------------------------------------------------------
COUNTRY_NAMES = {
    "usa": "United States", "gbr": "United Kingdom", "ind": "India",
    "can": "Canada", "aus": "Australia", "deu": "Germany", "fra": "France",
    "bra": "Brazil", "jpn": "Japan", "esp": "Spain", "nld": "Netherlands",
    "sgp": "Singapore", "mex": "Mexico", "idn": "Indonesia", "ita": "Italy",
    "kor": "South Korea", "tur": "Turkey", "pol": "Poland", "twn": "Taiwan",
    "chn": "China", "hkg": "Hong Kong", "che": "Switzerland", "swe": "Sweden",
    "nor": "Norway", "dnk": "Denmark", "fin": "Finland", "aut": "Austria",
    "bel": "Belgium", "irl": "Ireland", "nzl": "New Zealand", "zaf": "South Africa",
    "arg": "Argentina", "col": "Colombia", "chl": "Chile", "per": "Peru",
    "phl": "Philippines", "mys": "Malaysia", "tha": "Thailand", "vnm": "Vietnam",
    "pak": "Pakistan", "bgd": "Bangladesh", "lka": "Sri Lanka", "egy": "Egypt",
    "nga": "Nigeria", "ken": "Kenya", "sau": "Saudi Arabia", "are": "United Arab Emirates",
    "isr": "Israel", "ukr": "Ukraine", "rou": "Romania", "cze": "Czechia",
    "prt": "Portugal", "hun": "Hungary", "grc": "Greece", "rus": "Russia",
    "ury": "Uruguay", "tun": "Tunisia", "lbn": "Lebanon", "eth": "Ethiopia",
    "hrv": "Croatia", "svk": "Slovakia", "bgr": "Bulgaria", "srb": "Serbia",
}

# Minimum days of data required to use live data instead of static fallback
MIN_DAYS_FOR_LIVE = 1

# ---------------------------------------------------------------------------
# Google Search Console API client (lightweight: google-auth + requests)
# ---------------------------------------------------------------------------
_gsc_token = None

GSC_API_BASE = "https://searchconsole.googleapis.com/webmasters/v3/sites"
GSC_SITE_URL = "sc-domain:infrasketch.net"


def _get_gsc_headers():
    """Get Authorization headers using a cached Google service account token."""
    global _gsc_token

    if _gsc_token is not None and _gsc_token.valid:
        return {"Authorization": f"Bearer {_gsc_token.token}"}

    from google.oauth2 import service_account
    import google.auth.transport.requests

    # Try environment variable first (local testing), then Secrets Manager
    creds_json = os.environ.get("GOOGLE_SEARCH_CONSOLE_CREDENTIALS")
    if creds_json:
        creds_info = json.loads(creds_json)
    else:
        import boto3
        from botocore.exceptions import ClientError
        secret_name = os.environ.get(
            "GOOGLE_SEARCH_CONSOLE_SECRET", "infrasketch/google-search-console"
        )
        region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        try:
            resp = client.get_secret_value(SecretId=secret_name)
            creds_info = json.loads(resp["SecretString"])
        except (ClientError, KeyError, json.JSONDecodeError) as e:
            print(f"Failed to load GSC credentials from Secrets Manager: {e}")
            return None

    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    _gsc_token = creds
    return {"Authorization": f"Bearer {creds.token}"}


def _query_gsc(dimensions, start_date, end_date, row_limit=500):
    """Run a Search Console analytics query. Returns list of rows or []."""
    import requests

    headers = _get_gsc_headers()
    if headers is None:
        return []

    encoded_site = GSC_SITE_URL.replace(":", "%3A")
    url = f"{GSC_API_BASE}/{encoded_site}/searchAnalytics/query"

    try:
        resp = requests.post(url, headers=headers, json={
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": row_limit,
        }, timeout=15)
        resp.raise_for_status()
        return resp.json().get("rows", [])
    except Exception as e:
        print(f"GSC API query failed (dimensions={dimensions}): {e}")
        return []


# ---------------------------------------------------------------------------
# Fetch live data
# ---------------------------------------------------------------------------
def _fetch_live_data():
    """Pull live data from the Google Search Console API.

    Returns a dict with all data structures, or None if insufficient data.
    """
    # GSC data has a 2-3 day delay
    end_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=92)).strftime("%Y-%m-%d")

    print(f"Fetching live GSC data: {start_date} to {end_date}")

    # Fetch daily trends
    date_rows = _query_gsc(["date"], start_date, end_date)
    if len(date_rows) < MIN_DAYS_FOR_LIVE:
        print(f"Only {len(date_rows)} days of data, need {MIN_DAYS_FOR_LIVE}. Using static fallback.")
        return None

    daily_trends = []
    for row in sorted(date_rows, key=lambda r: r["keys"][0]):
        daily_trends.append({
            "date": row["keys"][0],
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        })

    # Fetch top queries
    query_rows = _query_gsc(["query"], start_date, end_date, row_limit=200)
    top_queries = []
    for row in sorted(query_rows, key=lambda r: r["impressions"], reverse=True):
        top_queries.append({
            "query": row["keys"][0],
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        })

    # Fetch top pages
    page_rows = _query_gsc(["page"], start_date, end_date, row_limit=100)
    top_pages = []
    for row in sorted(page_rows, key=lambda r: r["clicks"], reverse=True):
        url = row["keys"][0]
        # Strip domain to get path
        path = url.replace("https://infrasketch.net", "").replace("http://infrasketch.net", "")
        if not path:
            path = "/"
        top_pages.append({
            "page": path,
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        })

    # Fetch countries
    country_rows = _query_gsc(["country"], start_date, end_date, row_limit=100)
    countries = []
    for row in sorted(country_rows, key=lambda r: r["clicks"], reverse=True):
        code = row["keys"][0].lower()
        name = COUNTRY_NAMES.get(code, code.upper())
        countries.append({
            "country": name,
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        })

    # Fetch devices
    device_rows = _query_gsc(["device"], start_date, end_date)
    devices = []
    for row in sorted(device_rows, key=lambda r: r["clicks"], reverse=True):
        devices.append({
            "device": row["keys"][0].capitalize(),
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(row["ctr"] * 100, 2),
            "position": round(row["position"], 1),
        })

    # Compute growth metrics
    total_impressions = sum(d["impressions"] for d in daily_trends)
    total_clicks = sum(d["clicks"] for d in daily_trends)
    first_7 = daily_trends[:7]
    last_7 = daily_trends[-7:]
    avg_first_7 = sum(d["impressions"] for d in first_7) / max(len(first_7), 1)
    avg_last_7 = sum(d["impressions"] for d in last_7) / max(len(last_7), 1)
    growth_pct = ((avg_last_7 - avg_first_7) / max(avg_first_7, 1)) * 100

    growth_metrics = {
        "total_impressions_90d": total_impressions,
        "total_clicks_90d": total_clicks,
        "avg_daily_impressions_last_7d": round(avg_last_7, 1),
        "avg_daily_impressions_first_7d": round(avg_first_7, 1),
        "impression_growth_pct": round(growth_pct, 1),
        "total_countries": len(countries),
        "total_unique_queries": len(top_queries),
        "total_pages_with_traffic": len(top_pages),
    }

    print(f"Live GSC data loaded: {len(daily_trends)} days, {len(top_queries)} queries, "
          f"{len(countries)} countries, {total_impressions:,} impressions")

    return {
        "daily_trends": daily_trends,
        "top_queries": top_queries,
        "top_pages": top_pages,
        "countries": countries,
        "devices": devices,
        "growth_metrics": growth_metrics,
    }


# ---------------------------------------------------------------------------
# Static fallback data (snapshot: Jan 13 - Apr 12, 2026)
# Source: https___infrasketch.net_-Performance-on-Search-2026-04-14.xlsx
# Must be defined before _load_data() is called at module level.
# ---------------------------------------------------------------------------
_STATIC_DAILY_TRENDS = [
    {"date": "2026-01-13", "clicks": 2, "impressions": 6, "ctr": 33.33, "position": 2.0},
    {"date": "2026-01-14", "clicks": 0, "impressions": 5, "ctr": 0.0, "position": 44.8},
    {"date": "2026-01-15", "clicks": 2, "impressions": 14, "ctr": 14.29, "position": 30.3},
    {"date": "2026-01-16", "clicks": 1, "impressions": 7, "ctr": 14.29, "position": 36.1},
    {"date": "2026-01-17", "clicks": 0, "impressions": 3, "ctr": 0.0, "position": 13.3},
    {"date": "2026-01-18", "clicks": 0, "impressions": 6, "ctr": 0.0, "position": 26.0},
    {"date": "2026-01-19", "clicks": 2, "impressions": 8, "ctr": 25.0, "position": 15.9},
    {"date": "2026-01-20", "clicks": 1, "impressions": 9, "ctr": 11.11, "position": 19.1},
    {"date": "2026-01-21", "clicks": 1, "impressions": 16, "ctr": 6.25, "position": 20.9},
    {"date": "2026-01-22", "clicks": 0, "impressions": 17, "ctr": 0.0, "position": 20.2},
    {"date": "2026-01-23", "clicks": 1, "impressions": 9, "ctr": 11.11, "position": 14.4},
    {"date": "2026-01-24", "clicks": 0, "impressions": 5, "ctr": 0.0, "position": 47.8},
    {"date": "2026-01-25", "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 31.0},
    {"date": "2026-01-26", "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 7.0},
    {"date": "2026-01-27", "clicks": 2, "impressions": 3, "ctr": 66.67, "position": 10.3},
    {"date": "2026-01-28", "clicks": 2, "impressions": 7, "ctr": 28.57, "position": 3.1},
    {"date": "2026-01-29", "clicks": 3, "impressions": 7, "ctr": 42.86, "position": 8.9},
    {"date": "2026-01-30", "clicks": 0, "impressions": 2, "ctr": 0.0, "position": 16.5},
    {"date": "2026-01-31", "clicks": 0, "impressions": 3, "ctr": 0.0, "position": 14.7},
    {"date": "2026-02-01", "clicks": 0, "impressions": 26, "ctr": 0.0, "position": 9.1},
    {"date": "2026-02-02", "clicks": 1, "impressions": 171, "ctr": 0.58, "position": 25.5},
    {"date": "2026-02-03", "clicks": 1, "impressions": 418, "ctr": 0.24, "position": 24.5},
    {"date": "2026-02-04", "clicks": 0, "impressions": 566, "ctr": 0.0, "position": 22.1},
    {"date": "2026-02-05", "clicks": 3, "impressions": 591, "ctr": 0.51, "position": 26.2},
    {"date": "2026-02-06", "clicks": 1, "impressions": 453, "ctr": 0.22, "position": 22.8},
    {"date": "2026-02-07", "clicks": 0, "impressions": 249, "ctr": 0.0, "position": 20.8},
    {"date": "2026-02-08", "clicks": 1, "impressions": 322, "ctr": 0.31, "position": 24.1},
    {"date": "2026-02-09", "clicks": 3, "impressions": 511, "ctr": 0.59, "position": 24.1},
    {"date": "2026-02-10", "clicks": 2, "impressions": 577, "ctr": 0.35, "position": 24.9},
    {"date": "2026-02-11", "clicks": 1, "impressions": 627, "ctr": 0.16, "position": 22.5},
    {"date": "2026-02-12", "clicks": 1, "impressions": 700, "ctr": 0.14, "position": 26.1},
    {"date": "2026-02-13", "clicks": 1, "impressions": 535, "ctr": 0.19, "position": 21.2},
    {"date": "2026-02-14", "clicks": 1, "impressions": 377, "ctr": 0.27, "position": 23.6},
    {"date": "2026-02-15", "clicks": 1, "impressions": 473, "ctr": 0.21, "position": 22.1},
    {"date": "2026-02-16", "clicks": 1, "impressions": 469, "ctr": 0.21, "position": 16.5},
    {"date": "2026-02-17", "clicks": 4, "impressions": 416, "ctr": 0.96, "position": 11.5},
    {"date": "2026-02-18", "clicks": 6, "impressions": 647, "ctr": 0.93, "position": 9.7},
    {"date": "2026-02-19", "clicks": 9, "impressions": 808, "ctr": 1.11, "position": 8.8},
    {"date": "2026-02-20", "clicks": 2, "impressions": 678, "ctr": 0.29, "position": 8.5},
    {"date": "2026-02-21", "clicks": 1, "impressions": 688, "ctr": 0.15, "position": 9.7},
    {"date": "2026-02-22", "clicks": 3, "impressions": 643, "ctr": 0.47, "position": 9.1},
    {"date": "2026-02-23", "clicks": 0, "impressions": 927, "ctr": 0.0, "position": 8.9},
    {"date": "2026-02-24", "clicks": 7, "impressions": 983, "ctr": 0.71, "position": 9.1},
    {"date": "2026-02-25", "clicks": 3, "impressions": 1027, "ctr": 0.29, "position": 8.3},
    {"date": "2026-02-26", "clicks": 7, "impressions": 1274, "ctr": 0.55, "position": 8.1},
    {"date": "2026-02-27", "clicks": 3, "impressions": 1201, "ctr": 0.25, "position": 7.6},
    {"date": "2026-02-28", "clicks": 4, "impressions": 1155, "ctr": 0.35, "position": 7.9},
    {"date": "2026-03-01", "clicks": 2, "impressions": 1325, "ctr": 0.15, "position": 7.8},
    {"date": "2026-03-02", "clicks": 1, "impressions": 1627, "ctr": 0.06, "position": 7.9},
    {"date": "2026-03-03", "clicks": 6, "impressions": 2464, "ctr": 0.24, "position": 7.5},
    {"date": "2026-03-04", "clicks": 6, "impressions": 2016, "ctr": 0.3, "position": 7.7},
    {"date": "2026-03-05", "clicks": 4, "impressions": 2031, "ctr": 0.2, "position": 7.6},
    {"date": "2026-03-06", "clicks": 5, "impressions": 1593, "ctr": 0.31, "position": 10.9},
    {"date": "2026-03-07", "clicks": 5, "impressions": 1795, "ctr": 0.28, "position": 10.2},
    {"date": "2026-03-08", "clicks": 3, "impressions": 1478, "ctr": 0.2, "position": 8.5},
    {"date": "2026-03-09", "clicks": 8, "impressions": 1926, "ctr": 0.42, "position": 7.9},
    {"date": "2026-03-10", "clicks": 3, "impressions": 1834, "ctr": 0.16, "position": 8.8},
    {"date": "2026-03-11", "clicks": 4, "impressions": 1698, "ctr": 0.24, "position": 8.3},
    {"date": "2026-03-12", "clicks": 7, "impressions": 1780, "ctr": 0.39, "position": 7.4},
    {"date": "2026-03-13", "clicks": 5, "impressions": 1303, "ctr": 0.38, "position": 8.6},
    {"date": "2026-03-14", "clicks": 6, "impressions": 975, "ctr": 0.62, "position": 8.6},
    {"date": "2026-03-15", "clicks": 7, "impressions": 1164, "ctr": 0.6, "position": 8.5},
    {"date": "2026-03-16", "clicks": 3, "impressions": 1283, "ctr": 0.23, "position": 9.1},
    {"date": "2026-03-17", "clicks": 9, "impressions": 1562, "ctr": 0.58, "position": 8.6},
    {"date": "2026-03-18", "clicks": 8, "impressions": 1553, "ctr": 0.52, "position": 7.6},
    {"date": "2026-03-19", "clicks": 5, "impressions": 1566, "ctr": 0.32, "position": 8.8},
    {"date": "2026-03-20", "clicks": 0, "impressions": 1361, "ctr": 0.0, "position": 8.9},
    {"date": "2026-03-21", "clicks": 3, "impressions": 1143, "ctr": 0.26, "position": 10.2},
    {"date": "2026-03-22", "clicks": 4, "impressions": 1371, "ctr": 0.29, "position": 8.9},
    {"date": "2026-03-23", "clicks": 3, "impressions": 1531, "ctr": 0.2, "position": 9.2},
    {"date": "2026-03-24", "clicks": 6, "impressions": 1523, "ctr": 0.39, "position": 9.8},
    {"date": "2026-03-25", "clicks": 2, "impressions": 1542, "ctr": 0.13, "position": 9.9},
    {"date": "2026-03-26", "clicks": 7, "impressions": 1429, "ctr": 0.49, "position": 9.5},
    {"date": "2026-03-27", "clicks": 13, "impressions": 1240, "ctr": 1.05, "position": 10.0},
    {"date": "2026-03-28", "clicks": 8, "impressions": 1111, "ctr": 0.72, "position": 10.3},
    {"date": "2026-03-29", "clicks": 4, "impressions": 1173, "ctr": 0.34, "position": 9.6},
    {"date": "2026-03-30", "clicks": 17, "impressions": 1400, "ctr": 1.21, "position": 9.6},
    {"date": "2026-03-31", "clicks": 6, "impressions": 1340, "ctr": 0.45, "position": 10.3},
    {"date": "2026-04-01", "clicks": 12, "impressions": 1686, "ctr": 0.71, "position": 11.2},
    {"date": "2026-04-02", "clicks": 6, "impressions": 1256, "ctr": 0.48, "position": 11.2},
    {"date": "2026-04-03", "clicks": 8, "impressions": 1195, "ctr": 0.67, "position": 12.0},
    {"date": "2026-04-04", "clicks": 1, "impressions": 1417, "ctr": 0.07, "position": 11.8},
    {"date": "2026-04-05", "clicks": 10, "impressions": 1379, "ctr": 0.73, "position": 13.7},
    {"date": "2026-04-06", "clicks": 3, "impressions": 2142, "ctr": 0.14, "position": 18.3},
    {"date": "2026-04-07", "clicks": 4, "impressions": 2265, "ctr": 0.18, "position": 12.3},
    {"date": "2026-04-08", "clicks": 16, "impressions": 2279, "ctr": 0.7, "position": 12.6},
    {"date": "2026-04-09", "clicks": 7, "impressions": 2330, "ctr": 0.3, "position": 9.8},
    {"date": "2026-04-10", "clicks": 17, "impressions": 1939, "ctr": 0.88, "position": 10.2},
    {"date": "2026-04-11", "clicks": 1, "impressions": 1785, "ctr": 0.06, "position": 11.1},
    {"date": "2026-04-12", "clicks": 10, "impressions": 1764, "ctr": 0.57, "position": 11.0},
]

_STATIC_TOP_QUERIES = [
    {"query": "system design", "clicks": 2, "impressions": 900, "ctr": 0.22, "position": 40.9},
    {"query": "arch diagram levels", "clicks": 0, "impressions": 840, "ctr": 0.0, "position": 32.0},
    {"query": "infrasketch", "clicks": 160, "impressions": 810, "ctr": 19.75, "position": 2.0},
    {"query": "best cloud diagramming tools for collaborative design 2025 2026", "clicks": 0, "impressions": 536, "ctr": 0.0, "position": 12.2},
    {"query": "architecture diagram generator", "clicks": 0, "impressions": 478, "ctr": 0.0, "position": 67.5},
    {"query": "weaviate vector database architecture diagram", "clicks": 0, "impressions": 371, "ctr": 0.0, "position": 8.7},
    {"query": "top system architecture diagramming tools 2026", "clicks": 0, "impressions": 337, "ctr": 0.0, "position": 6.9},
    {"query": "aws diagram tool", "clicks": 0, "impressions": 322, "ctr": 0.0, "position": 44.3},
    {"query": "vector database architecture diagram", "clicks": 0, "impressions": 315, "ctr": 0.0, "position": 9.2},
    {"query": "what is system design in software", "clicks": 0, "impressions": 283, "ctr": 0.0, "position": 10.5},
    {"query": "best ai tools for creating diagrams 2026", "clicks": 0, "impressions": 233, "ctr": 0.0, "position": 7.4},
    {"query": "best tools for creating aws architecture diagrams 2025 2026", "clicks": 0, "impressions": 233, "ctr": 0.0, "position": 6.6},
    {"query": "architectural diagram types", "clicks": 0, "impressions": 210, "ctr": 0.0, "position": 64.2},
    {"query": "aws diagram", "clicks": 0, "impressions": 198, "ctr": 0.0, "position": 52.0},
    {"query": "systems design", "clicks": 0, "impressions": 194, "ctr": 0.0, "position": 47.7},
    {"query": "best tools for creating cloud architecture diagrams 2025 2026", "clicks": 0, "impressions": 188, "ctr": 0.0, "position": 7.7},
]

_STATIC_TOP_PAGES = [
    {"page": "/", "clicks": 160, "impressions": 810, "ctr": 19.75, "position": 2.0},
    {"page": "/blog/best-ai-diagram-tools-2026", "clicks": 24, "impressions": 5432, "ctr": 0.44, "position": 7.2},
    {"page": "/blog/best-system-architecture-diagramming-tools-2026", "clicks": 18, "impressions": 3210, "ctr": 0.56, "position": 8.1},
    {"page": "/blog/best-cloud-architecture-diagram-tools-2026", "clicks": 15, "impressions": 2890, "ctr": 0.52, "position": 9.3},
    {"page": "/blog/best-diagram-as-code-tools-2026", "clicks": 12, "impressions": 2100, "ctr": 0.57, "position": 6.5},
]

_STATIC_COUNTRIES = [
    {"country": "India", "clicks": 59, "impressions": 4057, "ctr": 1.45, "position": 14.9},
    {"country": "United States", "clicks": 50, "impressions": 41031, "ctr": 0.12, "position": 11.1},
    {"country": "United Kingdom", "clicks": 14, "impressions": 2973, "ctr": 0.47, "position": 16.0},
    {"country": "Japan", "clicks": 14, "impressions": 935, "ctr": 1.5, "position": 6.0},
    {"country": "Australia", "clicks": 13, "impressions": 1147, "ctr": 1.13, "position": 23.1},
    {"country": "Canada", "clicks": 10, "impressions": 3215, "ctr": 0.31, "position": 18.6},
    {"country": "Brazil", "clicks": 8, "impressions": 4032, "ctr": 0.2, "position": 9.0},
    {"country": "Germany", "clicks": 7, "impressions": 1717, "ctr": 0.41, "position": 12.9},
    {"country": "Spain", "clicks": 7, "impressions": 1573, "ctr": 0.45, "position": 7.9},
    {"country": "Singapore", "clicks": 7, "impressions": 1010, "ctr": 0.69, "position": 6.4},
]

_STATIC_DEVICES = [
    {"device": "Desktop", "clicks": 297, "impressions": 68674, "ctr": 0.43, "position": 11.6},
    {"device": "Mobile", "clicks": 51, "impressions": 17059, "ctr": 0.3, "position": 7.9},
    {"device": "Tablet", "clicks": 1, "impressions": 482, "ctr": 0.21, "position": 8.2},
]

_STATIC_GROWTH_METRICS = {
    "total_impressions_90d": 86215,
    "total_clicks_90d": 349,
    "avg_daily_impressions_last_7d": 2072.0,
    "avg_daily_impressions_first_7d": 7.0,
    "impression_growth_pct": 29500.0,
    "total_countries": 50,
    "total_unique_queries": 1000,
    "total_pages_with_traffic": 31,
}


# ---------------------------------------------------------------------------
# Static fallback accessor
# ---------------------------------------------------------------------------
def _get_static_data():
    """Return hardcoded static data as fallback."""
    return {
        "daily_trends": _STATIC_DAILY_TRENDS,
        "top_queries": _STATIC_TOP_QUERIES,
        "top_pages": _STATIC_TOP_PAGES,
        "countries": _STATIC_COUNTRIES,
        "devices": _STATIC_DEVICES,
        "growth_metrics": _STATIC_GROWTH_METRICS,
    }


# ---------------------------------------------------------------------------
# Module initialization: try live, fall back to static
# ---------------------------------------------------------------------------
def _load_data():
    """Load data from live API or static fallback."""
    try:
        live = _fetch_live_data()
        if live is not None:
            return live
    except Exception as e:
        print(f"Live GSC data fetch failed, using static fallback: {e}")
    return _get_static_data()


_data = _load_data()

DAILY_TRENDS = _data["daily_trends"]
TOP_QUERIES = _data["top_queries"]
TOP_PAGES = _data["top_pages"]
COUNTRIES = _data["countries"]
DEVICES = _data["devices"]
GROWTH_METRICS = _data["growth_metrics"]


def reload_data():
    """Force re-fetch from the API. Useful for long-running processes."""
    global DAILY_TRENDS, TOP_QUERIES, TOP_PAGES, COUNTRIES, DEVICES, GROWTH_METRICS, _data
    _data = _load_data()
    DAILY_TRENDS = _data["daily_trends"]
    TOP_QUERIES = _data["top_queries"]
    TOP_PAGES = _data["top_pages"]
    COUNTRIES = _data["countries"]
    DEVICES = _data["devices"]
    GROWTH_METRICS = _data["growth_metrics"]


# ---------------------------------------------------------------------------
# Helper functions (same interface as before)
# ---------------------------------------------------------------------------
def get_top_queries(n=10):
    """Get top N queries by impressions."""
    return sorted(TOP_QUERIES, key=lambda q: q["impressions"], reverse=True)[:n]


def get_opportunity_queries(min_impressions=50, max_ctr=1.0):
    """High impressions but low CTR = content opportunities."""
    return sorted(
        [q for q in TOP_QUERIES if q["impressions"] >= min_impressions and q["ctr"] < max_ctr],
        key=lambda q: q["impressions"],
        reverse=True,
    )


def get_growth_trend(period_days=7):
    """Compare recent period to the same period length at the start."""
    recent = DAILY_TRENDS[-period_days:]
    early = DAILY_TRENDS[:period_days]
    recent_avg = sum(d["impressions"] for d in recent) / max(len(recent), 1)
    early_avg = sum(d["impressions"] for d in early) / max(len(early), 1)
    growth_pct = ((recent_avg - early_avg) / max(early_avg, 1)) * 100
    return {
        "recent_avg": round(recent_avg, 1),
        "early_avg": round(early_avg, 1),
        "growth_pct": round(growth_pct, 0),
    }
