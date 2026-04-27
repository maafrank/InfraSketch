"""
Conversion customer analysis.

Identifies all paying customers (plan != "free") from infrasketch-user-credits and
pulls their pre-conversion behavior across DynamoDB and CloudWatch Logs Insights.
Writes a Markdown report with per-customer journeys, aggregate patterns, and
prioritized recommendations.

Usage:
    python scripts/analyze_conversions.py [--dry-run] [--output PATH]

Read-only. No production data is modified.
"""

import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

REGION = "us-east-1"
LOG_GROUP = "/aws/lambda/infrasketch-backend"
CW_LOG_LOOKBACK_DAYS = 30
PLAN_PRICES = {"starter": 1.0, "pro": 4.99, "enterprise": 0.0}

PROMPT_TOPIC_KEYWORDS = {
    "kubernetes": ["kubernetes", "k8s", "kube", "helm"],
    "auth": ["auth", "oauth", "jwt", "sso", "login", "signup"],
    "microservices": ["microservice", "service mesh", "grpc", "rpc"],
    "ecommerce": ["ecommerce", "e-commerce", "checkout", "cart", "shopify", "stripe"],
    "ai_ml": ["ai", "ml ", "machine learning", "llm", "rag", "vector", "embedding"],
    "data_pipeline": ["etl", "kafka", "airflow", "spark", "warehouse", "data pipeline"],
    "saas": ["saas", "multi-tenant", "tenant"],
    "social": ["social", "feed", "follower", "twitter", "instagram"],
    "video": ["video", "streaming", "live stream"],
    "messaging": ["chat app", "messaging", "whatsapp", "slack"],
    "mobile": ["mobile app", "ios", "android", "react native", "flutter"],
    "iot": ["iot", "sensor", "device fleet"],
    "gaming": ["game", "leaderboard", "matchmaking"],
    "finance": ["fintech", "payment", "trading", "ledger", "banking"],
    "url_shortener": ["url shortener", "tinyurl", "bitly"],
    "rate_limiter": ["rate limit"],
    "cdn_cache": ["cdn", "cache layer"],
    "search": ["search engine", "elasticsearch", "full-text"],
}


# DynamoDB serialization helpers (mirror what the backend does).

def _decimal_default(o):
    if isinstance(o, Decimal):
        i = int(o)
        return i if i == o else float(o)
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Not JSON serializable: {type(o)}")


def _to_iso(v) -> Optional[str]:
    if v is None or v == "":
        return None
    return str(v)


def _parse_dt(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v)
    if not s:
        return None
    try:
        # datetime.fromisoformat accepts "2025-12-31T15:00:00.123456" and offsets.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _to_int(v, default=0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def fetch_paying_users(credits_table) -> list[dict]:
    """Scan user-credits for plan != 'free'. Returns raw DynamoDB items."""
    items = []
    last_key = None
    while True:
        kwargs = {
            "FilterExpression": Attr("plan").is_in(["starter", "pro", "enterprise"]),
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = credits_table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
    return items


def fetch_user_dynamo_signals(
    user_id: str,
    sessions_table,
    transactions_table,
    gamification_table,
    preferences_table,
) -> dict:
    """Pull all DynamoDB-side data for one user. Returns dict of raw items/lists."""
    out = {
        "sessions": [],
        "transactions": [],
        "gamification": None,
        "preferences": None,
    }

    # Sessions via GSI
    try:
        last_key = None
        while True:
            kwargs = {
                "IndexName": "user_id-index",
                "KeyConditionExpression": Key("user_id").eq(user_id),
            }
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            resp = sessions_table.query(**kwargs)
            out["sessions"].extend(resp.get("Items", []))
            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
    except Exception as e:
        print(f"  sessions query failed for {user_id}: {e}", file=sys.stderr)

    # Transactions via GSI
    try:
        last_key = None
        while True:
            kwargs = {
                "IndexName": "user_id-index",
                "KeyConditionExpression": Key("user_id").eq(user_id),
            }
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            resp = transactions_table.query(**kwargs)
            out["transactions"].extend(resp.get("Items", []))
            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
    except Exception as e:
        print(f"  transactions query failed for {user_id}: {e}", file=sys.stderr)

    # Gamification (single get)
    try:
        resp = gamification_table.get_item(Key={"user_id": user_id})
        out["gamification"] = resp.get("Item")
    except Exception as e:
        print(f"  gamification get failed for {user_id}: {e}", file=sys.stderr)

    # Preferences (single get)
    try:
        resp = preferences_table.get_item(Key={"user_id": user_id})
        out["preferences"] = resp.get("Item")
    except Exception as e:
        print(f"  preferences get failed for {user_id}: {e}", file=sys.stderr)

    return out


def run_cw_query(logs_client, query_string: str, start_time: datetime, end_time: datetime, max_wait: int = 90) -> list:
    """Run a CloudWatch Logs Insights query and wait for completion."""
    start = logs_client.start_query(
        logGroupName=LOG_GROUP,
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query_string,
    )
    qid = start["queryId"]
    waited = 0
    while waited < max_wait:
        time.sleep(2)
        waited += 2
        result = logs_client.get_query_results(queryId=qid)
        status = result["status"]
        if status == "Complete":
            return result.get("results", [])
        if status in ("Failed", "Cancelled"):
            print(f"  CW query {status}: {query_string[:120]}", file=sys.stderr)
            return []
    print(f"  CW query timeout after {max_wait}s", file=sys.stderr)
    return []


def cw_row_to_dict(row: list) -> dict:
    return {item["field"]: item["value"] for item in row if "field" in item}


def fetch_cloudwatch_signals(logs_client, all_session_ids: list[str]) -> dict:
    """
    Run CW Logs Insights queries scoped to the given session_ids.
    Returns dict mapping session_id -> {"diagram_events": [...], "chat_events": [...], etc.}
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=CW_LOG_LOOKBACK_DAYS)

    by_session: dict[str, dict] = defaultdict(lambda: {
        "diagram_events": [],
        "chat_events": [],
        "preview_events": [],
        "insufficient_credit_errors": 0,
    })

    if not all_session_ids:
        return {"by_session": dict(by_session), "window": (start_time, end_time)}

    # CW Insights `in` filter expects bracketed list of quoted strings.
    # Chunk to keep queries reasonable.
    def chunked(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i : i + n]

    queries = {
        "diagram": (
            'fields @timestamp, session_id, metadata.prompt, metadata.prompt_length, '
            'metadata.node_count, metadata.edge_count, metadata.duration_ms '
            '| filter event_type = "diagram_generated" and session_id in {ids} '
            '| sort @timestamp asc | limit 5000'
        ),
        "chat": (
            'fields @timestamp, session_id, metadata.message, metadata.message_length, '
            'metadata.diagram_updated '
            '| filter event_type = "chat_message" and session_id in {ids} '
            '| sort @timestamp asc | limit 5000'
        ),
        "preview": (
            'fields @timestamp, session_id, metadata.action '
            '| filter event_type = "export_design_doc" and metadata.action = "preview_generated" '
            'and session_id in {ids} | sort @timestamp asc | limit 1000'
        ),
        "errors": (
            'fields @timestamp, session_id, error, metadata.error_type '
            '| filter event_type = "api_error" and session_id in {ids} '
            'and (metadata.error_type = "insufficient_credits" or error like /insufficient/) '
            '| sort @timestamp asc | limit 1000'
        ),
    }

    for chunk in chunked(all_session_ids, 100):
        ids_literal = "[" + ",".join(f'"{sid}"' for sid in chunk) + "]"

        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {
                ex.submit(run_cw_query, logs_client, q.format(ids=ids_literal), start_time, end_time): name
                for name, q in queries.items()
            }
            for fut in as_completed(futures):
                name = futures[fut]
                rows = fut.result()
                for row in rows:
                    d = cw_row_to_dict(row)
                    sid = d.get("session_id")
                    if not sid:
                        continue
                    if name == "diagram":
                        by_session[sid]["diagram_events"].append(d)
                    elif name == "chat":
                        by_session[sid]["chat_events"].append(d)
                    elif name == "preview":
                        by_session[sid]["preview_events"].append(d)
                    elif name == "errors":
                        by_session[sid]["insufficient_credit_errors"] += 1

    return {"by_session": dict(by_session), "window": (start_time, end_time)}


def classify_prompt_topic(prompt: str) -> Optional[str]:
    if not prompt:
        return None
    p = prompt.lower()
    for topic, keywords in PROMPT_TOPIC_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            return topic
    return None


def compute_signals(user_item: dict, dynamo: dict, cw_by_session: dict, cw_window) -> dict:
    """Reduce raw fetched data into a per-user signal dict for the report."""
    user_id = user_item["user_id"]
    plan = str(user_item.get("plan"))
    sub_status = str(user_item.get("subscription_status"))
    signup_at = _parse_dt(user_item.get("created_at"))
    plan_started_at = _parse_dt(user_item.get("plan_started_at"))
    redeemed_promos = list(user_item.get("redeemed_promo_codes") or [])

    sessions = dynamo["sessions"]
    txns = dynamo["transactions"]
    gam = dynamo["gamification"]
    prefs = dynamo["preferences"]

    # Sort sessions and transactions by created_at
    def session_dt(s):
        return _parse_dt(s.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)

    def txn_dt(t):
        return _parse_dt(t.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)

    sessions_sorted = sorted(sessions, key=session_dt)
    txns_sorted = sorted(txns, key=txn_dt)

    sessions_before = [s for s in sessions_sorted if plan_started_at and session_dt(s) < plan_started_at]
    txns_before = [t for t in txns_sorted if plan_started_at and txn_dt(t) < plan_started_at]

    # Action distribution from transactions (deductions only).
    action_counts_before = Counter()
    action_counts_lifetime = Counter()
    for t in txns_sorted:
        if str(t.get("type")) == "deduction":
            action = str(t.get("action") or "unknown")
            action_counts_lifetime[action] += 1
    for t in txns_before:
        if str(t.get("type")) == "deduction":
            action = str(t.get("action") or "unknown")
            action_counts_before[action] += 1

    # First session signals.
    first_session = sessions_sorted[0] if sessions_sorted else None
    first_session_at = session_dt(first_session) if first_session else None
    first_prompt = ""
    first_session_messages = 0
    first_session_node_count = 0
    first_session_edge_count = 0
    first_session_repo_url = None
    first_session_model = None
    first_session_has_doc = False
    if first_session:
        first_prompt = str(first_session.get("generation_prompt") or "")
        first_session_repo_url = first_session.get("repo_url")
        first_session_model = first_session.get("model")
        msgs = first_session.get("messages") or []
        first_session_messages = len([m for m in msgs if str(m.get("role")) == "user"])
        diagram = first_session.get("diagram") or {}
        first_session_node_count = len(diagram.get("nodes") or [])
        first_session_edge_count = len(diagram.get("edges") or [])
        first_session_has_doc = bool(first_session.get("design_doc"))

    # Time deltas. The user-credits record's `created_at` is set when the row is first
    # created (signup webhook OR first credit interaction). If a session predates it,
    # use the earlier of the two as the effective signup.
    def hours(td: timedelta) -> float:
        return td.total_seconds() / 3600.0

    effective_signup = signup_at
    credits_record_postdates_activity = False
    if signup_at and first_session_at and first_session_at < signup_at:
        effective_signup = first_session_at
        credits_record_postdates_activity = True

    time_to_first_session_h = (
        hours(first_session_at - effective_signup) if first_session_at and effective_signup else None
    )
    time_to_convert_h = (
        hours(plan_started_at - effective_signup) if plan_started_at and effective_signup else None
    )
    same_day_signup_to_first_action = (
        time_to_first_session_h is not None and time_to_first_session_h < 24
    )
    same_day_signup_to_paid = (
        time_to_convert_h is not None and time_to_convert_h < 24
    )

    # CloudWatch-derived signals (scoped to sessions before conversion).
    session_ids_before = [str(s.get("session_id")) for s in sessions_before if s.get("session_id")]
    session_ids_all = [str(s.get("session_id")) for s in sessions_sorted if s.get("session_id")]

    cw_diagram_events_before = []
    cw_chat_events_before = []
    cw_preview_events_before = []
    cw_402_errors_before = 0
    cw_diagram_events_lifetime = []

    for sid in session_ids_all:
        ev = cw_by_session.get(sid, {})
        cw_diagram_events_lifetime.extend(ev.get("diagram_events", []))
    for sid in session_ids_before:
        ev = cw_by_session.get(sid, {})
        cw_diagram_events_before.extend(ev.get("diagram_events", []))
        cw_chat_events_before.extend(ev.get("chat_events", []))
        cw_preview_events_before.extend(ev.get("preview_events", []))
        cw_402_errors_before += ev.get("insufficient_credit_errors", 0)

    # CloudWatch retention check: signup older than the lookback window means CW data is incomplete.
    cw_start, cw_end = cw_window
    cw_data_complete = signup_at is not None and signup_at >= cw_start

    # Gamification.
    counters = (gam or {}).get("counters") or {}
    longest_streak = _to_int((gam or {}).get("longest_streak"))
    current_streak = _to_int((gam or {}).get("current_streak"))
    last_active_date = (gam or {}).get("last_active_date")
    xp_total = _to_int((gam or {}).get("xp_total"))
    level = _to_int((gam or {}).get("level"), default=1)
    achievements = (gam or {}).get("achievements") or []
    achievements_before = []
    if plan_started_at:
        for a in achievements:
            ad = _parse_dt(a.get("unlocked_at"))
            if ad and ad < plan_started_at:
                achievements_before.append(str(a.get("id")))

    # Preferences.
    tutorial_completed = bool((prefs or {}).get("tutorial_completed"))
    tutorial_at = _parse_dt((prefs or {}).get("tutorial_completed_at"))
    tutorial_completed_before_paying = (
        tutorial_completed and tutorial_at and plan_started_at and tutorial_at < plan_started_at
    )

    # First-prompt topic (best-effort: first DynamoDB session's generation_prompt; fallback to CW).
    first_prompt_text = first_prompt
    if not first_prompt_text and cw_diagram_events_lifetime:
        first_prompt_text = str(cw_diagram_events_lifetime[0].get("metadata.prompt") or "")
    first_prompt_topic = classify_prompt_topic(first_prompt_text)
    first_prompt_word_count = len(first_prompt_text.split()) if first_prompt_text else 0

    # Try design doc preview before paying? (signal includes both DynamoDB session.design_doc_preview_used and CW events)
    tried_preview = (
        any(bool(s.get("design_doc_preview_used")) for s in sessions_before)
        or len(cw_preview_events_before) > 0
    )

    # Hit free limit before paying? (insufficient_credit_errors in CW)
    hit_free_limit = cw_402_errors_before > 0

    # Models tried before paying (from sessions).
    models_before = sorted({str(s.get("model")) for s in sessions_before if s.get("model")})
    repos_analyzed_total = _to_int(counters.get("repos_analyzed"))
    used_repo_analysis = repos_analyzed_total > 0

    return {
        "user_id": user_id,
        "plan": plan,
        "subscription_status": sub_status,
        "signup_at": signup_at,
        "effective_signup_at": effective_signup,
        "credits_record_postdates_activity": credits_record_postdates_activity,
        "plan_started_at": plan_started_at,
        "time_to_convert_hours": time_to_convert_h,
        "time_to_first_session_hours": time_to_first_session_h,
        "same_day_signup_to_first_action": same_day_signup_to_first_action,
        "same_day_signup_to_paid": same_day_signup_to_paid,
        "first_session_at": first_session_at,
        "first_prompt_text": first_prompt_text,
        "first_prompt_word_count": first_prompt_word_count,
        "first_prompt_topic": first_prompt_topic,
        "first_session_node_count": first_session_node_count,
        "first_session_edge_count": first_session_edge_count,
        "first_session_messages": first_session_messages,
        "first_session_repo_url": first_session_repo_url,
        "first_session_model": first_session_model,
        "first_session_has_doc": first_session_has_doc,
        "sessions_before_count": len(sessions_before),
        "sessions_lifetime_count": len(sessions_sorted),
        "diagrams_before_count": action_counts_before.get("diagram_generation", 0),
        "chats_before_count": action_counts_before.get("chat_message", 0),
        "design_doc_actions_before": (
            action_counts_before.get("design_doc_generation", 0)
            + action_counts_before.get("design_doc_export", 0)
        ),
        "repo_analysis_actions_before": action_counts_before.get("repo_analysis", 0),
        "action_counts_before": dict(action_counts_before),
        "action_counts_lifetime": dict(action_counts_lifetime),
        "hit_free_limit_before_paying": hit_free_limit,
        "tried_design_doc_preview_before_paying": tried_preview,
        "used_promo_code": len(redeemed_promos) > 0,
        "redeemed_promo_codes": redeemed_promos,
        "tutorial_completed_before_paying": bool(tutorial_completed_before_paying),
        "longest_streak": longest_streak,
        "current_streak": current_streak,
        "last_active_date": last_active_date,
        "xp_total": xp_total,
        "level": level,
        "achievements_before_paying": achievements_before,
        "models_used_before": models_before,
        "used_repo_analysis_lifetime": used_repo_analysis,
        "cw_data_complete": cw_data_complete,
        "cw_chat_events_before": len(cw_chat_events_before),
        "cw_402_errors_before": cw_402_errors_before,
    }


def aggregate(signals: list[dict]) -> dict:
    n = len(signals)
    if n == 0:
        return {"n": 0}

    def collect(field):
        return [s[field] for s in signals if s.get(field) is not None]

    def pct(predicate) -> float:
        if n == 0:
            return 0.0
        return 100.0 * sum(1 for s in signals if predicate(s)) / n

    def median(values):
        return statistics.median(values) if values else None

    def quartiles(values):
        if not values:
            return (None, None, None)
        sv = sorted(values)
        if len(sv) == 1:
            return (sv[0], sv[0], sv[0])
        q = statistics.quantiles(sv, n=4, method="inclusive")
        return (q[0], q[1], q[2])

    plan_dist = Counter(s["plan"] for s in signals)
    mrr = sum(PLAN_PRICES.get(s["plan"], 0.0) for s in signals)

    ttc_hours = collect("time_to_convert_hours")
    ttc_q = quartiles(ttc_hours)

    sessions_before = collect("sessions_before_count")
    diagrams_before = collect("diagrams_before_count")
    chats_before = collect("chats_before_count")

    topics = Counter(s["first_prompt_topic"] for s in signals if s.get("first_prompt_topic"))
    achievements = Counter()
    for s in signals:
        for a in s.get("achievements_before_paying", []):
            achievements[a] += 1
    promo_codes = Counter()
    for s in signals:
        for p in s.get("redeemed_promo_codes", []):
            promo_codes[p] += 1
    models = Counter()
    for s in signals:
        for m in s.get("models_used_before", []):
            models[m] += 1

    return {
        "n": n,
        "plan_distribution": dict(plan_dist),
        "estimated_mrr_usd": round(mrr, 2),
        "time_to_convert_hours": {
            "p25": ttc_q[0],
            "median": ttc_q[1],
            "p75": ttc_q[2],
            "mean": statistics.fmean(ttc_hours) if ttc_hours else None,
        },
        "sessions_before_paying": {
            "median": median(sessions_before),
            "max": max(sessions_before) if sessions_before else None,
        },
        "diagrams_before_paying": {
            "median": median(diagrams_before),
            "max": max(diagrams_before) if diagrams_before else None,
        },
        "chats_before_paying": {
            "median": median(chats_before),
            "max": max(chats_before) if chats_before else None,
        },
        "pct_hit_free_limit_before_paying": pct(lambda s: s["hit_free_limit_before_paying"]),
        "pct_tried_design_doc_preview": pct(lambda s: s["tried_design_doc_preview_before_paying"]),
        "pct_used_promo_code": pct(lambda s: s["used_promo_code"]),
        "pct_tutorial_completed_before_paying": pct(lambda s: s["tutorial_completed_before_paying"]),
        "pct_same_day_first_action": pct(lambda s: s["same_day_signup_to_first_action"]),
        "pct_same_day_paid": pct(lambda s: s["same_day_signup_to_paid"]),
        "pct_used_repo_analysis": pct(lambda s: s["used_repo_analysis_lifetime"]),
        "pct_cw_data_complete": pct(lambda s: s["cw_data_complete"]),
        "first_prompt_topics": dict(topics.most_common()),
        "achievements_before_paying_top": dict(achievements.most_common(10)),
        "promo_codes_used": dict(promo_codes.most_common()),
        "models_used_before_top": dict(models.most_common()),
    }


def fmt_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "—"


def fmt_hours(h: Optional[float]) -> str:
    if h is None:
        return "—"
    if h < 0:
        return "n/a (negative — see note)"
    if h < 1:
        return f"{h * 60:.0f} min"
    if h < 48:
        return f"{h:.1f} h"
    return f"{h / 24:.1f} d"


def fmt_pct(p: Optional[float]) -> str:
    return f"{p:.0f}%" if p is not None else "—"


def fmt_num(n) -> str:
    if n is None:
        return "—"
    if isinstance(n, float):
        return f"{n:.1f}"
    return str(n)


def render_report(signals: list[dict], agg: dict, generated_at: datetime) -> str:
    lines = []
    lines.append(f"# InfraSketch Conversion Customer Analysis")
    lines.append("")
    lines.append(f"_Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}_")
    lines.append("")
    lines.append(
        "Cohort: all users with `plan` in (starter, pro, enterprise) in `infrasketch-user-credits`. "
        f"CloudWatch lookback window: {CW_LOG_LOOKBACK_DAYS} days. "
        "Customers who signed up before that window will have partial behavioral data (flagged per row)."
    )
    lines.append("")

    # 1. Summary
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(f"- Paying customers: **{agg['n']}**")
    lines.append(f"- Estimated MRR (starter $1, pro $4.99, enterprise excluded): **${agg.get('estimated_mrr_usd', 0):.2f}**")
    plan_dist = agg.get("plan_distribution", {})
    if plan_dist:
        parts = ", ".join(f"{p}: {c}" for p, c in plan_dist.items())
        lines.append(f"- Plan mix: {parts}")
    lines.append(f"- CloudWatch data complete for **{fmt_pct(agg.get('pct_cw_data_complete'))}** of cohort (rest signed up before {CW_LOG_LOOKBACK_DAYS}-day window).")
    lines.append("")

    # 2. Aggregate signals
    lines.append("## 2. Aggregate signals")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    ttc = agg.get("time_to_convert_hours", {})
    lines.append(f"| Time to convert (signup → paid), median | {fmt_hours(ttc.get('median'))} |")
    lines.append(f"| Time to convert, p25 / p75 | {fmt_hours(ttc.get('p25'))} / {fmt_hours(ttc.get('p75'))} |")
    lines.append(f"| Sessions before paying, median (max) | {fmt_num(agg.get('sessions_before_paying', {}).get('median'))} ({fmt_num(agg.get('sessions_before_paying', {}).get('max'))}) |")
    lines.append(f"| Diagrams generated before paying, median (max) | {fmt_num(agg.get('diagrams_before_paying', {}).get('median'))} ({fmt_num(agg.get('diagrams_before_paying', {}).get('max'))}) |")
    lines.append(f"| Chat messages before paying, median (max) | {fmt_num(agg.get('chats_before_paying', {}).get('median'))} ({fmt_num(agg.get('chats_before_paying', {}).get('max'))}) |")
    lines.append(f"| % who hit free credit limit (402) before paying | {fmt_pct(agg.get('pct_hit_free_limit_before_paying'))} |")
    lines.append(f"| % who tried design doc preview before paying | {fmt_pct(agg.get('pct_tried_design_doc_preview'))} |")
    lines.append(f"| % who redeemed a promo code | {fmt_pct(agg.get('pct_used_promo_code'))} |")
    lines.append(f"| % who completed tutorial before paying | {fmt_pct(agg.get('pct_tutorial_completed_before_paying'))} |")
    lines.append(f"| % who took first action same day as signup | {fmt_pct(agg.get('pct_same_day_first_action'))} |")
    lines.append(f"| % who paid same day as signup | {fmt_pct(agg.get('pct_same_day_paid'))} |")
    lines.append(f"| % who used repo analysis (lifetime) | {fmt_pct(agg.get('pct_used_repo_analysis'))} |")
    lines.append("")

    topics = agg.get("first_prompt_topics", {})
    if topics:
        lines.append("**First-prompt topics (heuristic keyword classifier):**")
        lines.append("")
        for t, c in topics.items():
            lines.append(f"- {t}: {c}")
        unclassified = agg["n"] - sum(topics.values())
        if unclassified > 0:
            lines.append(f"- _unclassified: {unclassified}_")
        lines.append("")

    achievements = agg.get("achievements_before_paying_top", {})
    if achievements:
        lines.append("**Achievements unlocked before paying (top 10):**")
        lines.append("")
        for a, c in achievements.items():
            lines.append(f"- `{a}`: {c}")
        lines.append("")

    promos = agg.get("promo_codes_used", {})
    if promos:
        lines.append("**Promo codes redeemed:**")
        lines.append("")
        for p, c in promos.items():
            lines.append(f"- `{p}`: {c}")
        lines.append("")

    models = agg.get("models_used_before_top", {})
    if models:
        lines.append("**Models used before paying:**")
        lines.append("")
        for m, c in models.items():
            lines.append(f"- `{m}`: {c}")
        lines.append("")

    # 3. Per-customer journeys
    lines.append("## 3. Per-customer journeys")
    lines.append("")
    signals_sorted = sorted(
        signals,
        key=lambda s: s.get("plan_started_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    for i, s in enumerate(signals_sorted, 1):
        flags_inline = []
        if not s["cw_data_complete"]:
            flags_inline.append("⚠️ CloudWatch data partial (signed up before lookback window)")
        if s.get("credits_record_postdates_activity"):
            flags_inline.append("ℹ️ credits record postdates first activity — using earliest activity as effective signup")
        if s["user_id"] in {"local-dev-user"} or str(s["user_id"]).startswith("test-") or str(s["user_id"]).startswith("dev-"):
            flags_inline.append("🧪 likely test/dev account — exclude from cohort interpretation")
        flag_suffix = "  \n_" + " · ".join(flags_inline) + "_" if flags_inline else ""
        lines.append(f"### {i}. `{s['user_id']}` — {s['plan']} ({s['subscription_status']}){flag_suffix}")
        lines.append("")
        lines.append(f"- **Signup (credits record):** {fmt_dt(s['signup_at'])}")
        lines.append(f"- **Converted:** {fmt_dt(s['plan_started_at'])} ({fmt_hours(s['time_to_convert_hours'])} after effective signup)")
        lines.append(f"- **First session:** {fmt_dt(s['first_session_at'])} ({fmt_hours(s['time_to_first_session_hours'])} after effective signup)")

        prompt_preview = (s["first_prompt_text"] or "").strip().replace("\n", " ")
        if len(prompt_preview) > 240:
            prompt_preview = prompt_preview[:237] + "..."
        topic_str = f" _(topic: {s['first_prompt_topic']})_" if s["first_prompt_topic"] else ""
        if prompt_preview:
            lines.append(f"- **First prompt** ({s['first_prompt_word_count']} words){topic_str}: > {prompt_preview}")
        else:
            lines.append(f"- **First prompt:** _(unavailable)_")

        if s["first_session_repo_url"]:
            lines.append(f"- **First session was repo analysis:** {s['first_session_repo_url']}")
        lines.append(
            f"- **First diagram complexity:** {s['first_session_node_count']} nodes / {s['first_session_edge_count']} edges, "
            f"{s['first_session_messages']} user follow-up messages"
        )

        lines.append("- **Pre-conversion behavior:**")
        lines.append(f"  - Sessions: {s['sessions_before_count']} (lifetime: {s['sessions_lifetime_count']})")
        lines.append(f"  - Diagram generations: {s['diagrams_before_count']}")
        lines.append(f"  - Chat messages: {s['chats_before_count']}")
        lines.append(f"  - Design doc actions: {s['design_doc_actions_before']}")
        lines.append(f"  - Repo analysis calls: {s['repo_analysis_actions_before']}")

        flags = []
        flags.append(f"Hit free limit: {'yes' if s['hit_free_limit_before_paying'] else 'no'}")
        flags.append(f"Tried design doc preview: {'yes' if s['tried_design_doc_preview_before_paying'] else 'no'}")
        flags.append(f"Promo code used: {'yes (' + ', '.join(s['redeemed_promo_codes']) + ')' if s['redeemed_promo_codes'] else 'no'}")
        flags.append(f"Tutorial done before paying: {'yes' if s['tutorial_completed_before_paying'] else 'no'}")
        lines.append("- **Flags:** " + " | ".join(flags))

        if s["models_used_before"]:
            lines.append(f"- **Models tried before paying:** {', '.join(s['models_used_before'])}")
        lines.append(
            f"- **Engagement:** XP {s['xp_total']} (level {s['level']}), longest streak {s['longest_streak']} days, last active {s['last_active_date'] or '—'}"
        )
        if s["achievements_before_paying"]:
            lines.append(f"- **Achievements before paying:** {', '.join(s['achievements_before_paying'])}")
        lines.append("")

    # 4. Patterns observed
    lines.append("## 4. Patterns observed")
    lines.append("")
    n = agg["n"]
    if n == 0:
        lines.append("_No paying customers found._")
    else:
        observations = []

        def frac(p):
            return f"{int(round(p / 100 * n))}/{n}"

        if agg.get("pct_hit_free_limit_before_paying", 0) >= 50:
            observations.append(
                f"**{frac(agg['pct_hit_free_limit_before_paying'])} ({fmt_pct(agg['pct_hit_free_limit_before_paying'])}) hit a free-credit limit (HTTP 402) before converting.** "
                "The 402 wall is a primary upgrade trigger — make sure the upgrade CTA at that moment is unmissable."
            )
        elif agg.get("pct_hit_free_limit_before_paying", 0) > 0:
            observations.append(
                f"Only {frac(agg['pct_hit_free_limit_before_paying'])} hit the 402 wall before paying. Most converted while still inside the free allowance — interest, not pain, is the dominant trigger."
            )

        if agg.get("pct_tried_design_doc_preview", 0) >= 40:
            observations.append(
                f"**{frac(agg['pct_tried_design_doc_preview'])} tried the design doc preview** before converting. The preview-then-paywall flow is doing real work; double down on it."
            )

        if agg.get("pct_same_day_paid", 0) >= 50:
            observations.append(
                f"**{frac(agg['pct_same_day_paid'])} paid on the same day they signed up** — the first session is decisive. There is no week-2 nurture window; it has to land in the first hour."
            )
        elif (ttc.get("median") or 0) > 24:
            observations.append(
                f"Median time to convert is {fmt_hours(ttc.get('median'))}, so multi-session consideration is real. There is value in lifecycle email/comeback nudges."
            )

        if agg.get("pct_used_promo_code", 0) >= 30:
            observations.append(
                f"**{frac(agg['pct_used_promo_code'])} redeemed a promo code.** Promo codes meaningfully drive conversion in this cohort."
            )

        if agg.get("pct_used_repo_analysis", 0) >= 40:
            observations.append(
                f"**{frac(agg['pct_used_repo_analysis'])} used repo analysis** at some point. This may be a feature converters seek out — surface it earlier in onboarding."
            )

        med_diagrams = agg.get("diagrams_before_paying", {}).get("median")
        if med_diagrams is not None and med_diagrams >= 1:
            observations.append(
                f"Median paying customer generated **{fmt_num(med_diagrams)} diagram(s)** before converting (max: {fmt_num(agg['diagrams_before_paying']['max'])}). The 'aha' is in the first one or two outputs."
            )

        if topics:
            top_topic, top_count = next(iter(topics.items()))
            observations.append(
                f"Top first-prompt topic: **{top_topic}** ({top_count}/{n}). Lean prompt examples and marketing copy toward this domain."
            )

        if not observations:
            observations.append("Cohort too small or signals too sparse to draw confident conclusions yet — re-run when more customers convert.")

        for obs in observations:
            lines.append(f"- {obs}")
    lines.append("")

    # 5. Recommendations
    lines.append("## 5. Recommendations")
    lines.append("")
    lines.append("Recommendations are tagged with the signal that motivates them. Re-evaluate after the cohort grows.")
    lines.append("")

    recs = []
    if agg.get("pct_hit_free_limit_before_paying", 0) >= 30:
        recs.append({
            "priority": "P0",
            "title": "Make the 402 upgrade moment a conversion-class UX, not an error message.",
            "why": f"{fmt_pct(agg.get('pct_hit_free_limit_before_paying'))} of converters hit the 402 wall first.",
            "action": "Replace the generic 'insufficient credits' message with a contextual upgrade modal that shows what they were trying to do, the price ($1 starter), and a one-click Clerk checkout. Pre-fill the plan choice based on what they ran out of credits doing.",
        })
    if agg.get("pct_tried_design_doc_preview", 0) >= 30:
        recs.append({
            "priority": "P0",
            "title": "Auto-suggest design doc generation after first diagram.",
            "why": f"{fmt_pct(agg.get('pct_tried_design_doc_preview'))} of converters tried the design doc preview before paying.",
            "action": "After the first successful diagram, surface a banner ('Want a full design doc for this? Free preview included'). Exposes the highest-converting paid feature without hunting.",
        })
    if agg.get("pct_same_day_paid", 0) >= 50:
        recs.append({
            "priority": "P0",
            "title": "Optimize the first 30 minutes ruthlessly.",
            "why": f"{fmt_pct(agg.get('pct_same_day_paid'))} of converters pay on day 1.",
            "action": "Shrink time-to-first-diagram. Pre-populate the prompt textarea with a strong, conversion-aligned example (current top topic: " + (next(iter(topics.keys())) if topics else "n/a") + "). Defer auth gates that aren't needed until export/save.",
        })
    if topics:
        top_topics_list = list(topics.keys())[:3]
        recs.append({
            "priority": "P1",
            "title": f"Re-skin landing page examples toward top converting topics: {', '.join(top_topics_list)}.",
            "why": "These topics dominate the first prompts of paying customers.",
            "action": "Replace the 3 hero example prompts on the landing page with one from each top topic. Add a section to the blog targeting the same keywords for SEO.",
        })
    if agg.get("pct_used_promo_code", 0) >= 20:
        recs.append({
            "priority": "P1",
            "title": "Treat promo codes as a real channel, not a leak.",
            "why": f"{fmt_pct(agg.get('pct_used_promo_code'))} of converters used a promo. Most-used: {next(iter(agg.get('promo_codes_used', {}).keys()), 'n/a')}.",
            "action": "Add a dedicated promo input field in the upgrade modal (not just on /pricing). Track each promo's revenue per redemption to decide which to retire.",
        })
    if agg.get("pct_used_repo_analysis", 0) >= 30:
        recs.append({
            "priority": "P1",
            "title": "Move repo analysis higher in the onboarding flow.",
            "why": f"{fmt_pct(agg.get('pct_used_repo_analysis'))} of converters use repo analysis.",
            "action": "Add a 'Generate from your GitHub repo' option alongside the prompt textarea on the landing page, not just inside the app. This is a high-intent acquisition wedge.",
        })
    med_sessions = agg.get("sessions_before_paying", {}).get("median")
    if med_sessions is not None and med_sessions >= 2:
        recs.append({
            "priority": "P1",
            "title": "Convert returning free users at session N+1.",
            "why": f"Median converter creates {fmt_num(med_sessions)} sessions before paying. Multi-session consideration is real.",
            "action": "On second session start, surface a one-time inline pitch tied to what they did in session 1 (e.g., 'You generated X. Pro lets you keep it auto-synced with the design doc').",
        })
    if agg.get("pct_tutorial_completed_before_paying", 0) < 30 and agg["n"] >= 5:
        recs.append({
            "priority": "P2",
            "title": "Tutorial may be skipped or under-driving conversion.",
            "why": f"Only {fmt_pct(agg.get('pct_tutorial_completed_before_paying'))} of converters completed the tutorial before paying.",
            "action": "Either make the tutorial more obviously a conversion driver (end it on the design doc preview) or accept it isn't on the path and de-prioritize it.",
        })

    if not recs:
        recs.append({
            "priority": "P2",
            "title": "Cohort is too small for confident product changes.",
            "why": f"Only {agg['n']} paying customer(s) found.",
            "action": "Re-run this analysis after each ~10 new conversions and watch for emerging patterns. In the meantime, instrument any new funnel events you suspect matter.",
        })

    for r in recs:
        lines.append(f"### [{r['priority']}] {r['title']}")
        lines.append("")
        lines.append(f"**Why:** {r['why']}")
        lines.append("")
        lines.append(f"**Action:** {r['action']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Source: scripts/analyze_conversions.py. Read-only against `infrasketch-user-credits`, `infrasketch-credit-transactions`, `infrasketch-sessions`, `infrasketch-user-gamification`, `infrasketch-user-preferences`, and CloudWatch log group `/aws/lambda/infrasketch-backend`._")

    return "\n".join(lines) + "\n"


def run_analysis(region: str = REGION, max_workers: int = 8, log_fn=print) -> tuple[list[dict], dict, datetime]:
    """
    Execute the full conversion analysis end-to-end.

    Returns (per_user_signals, aggregate_dict, generated_at_utc).
    `log_fn` is called with progress messages — pass `print` for CLI use,
    or a Lambda logger.
    """
    boto3.setup_default_session(region_name=region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    logs = boto3.client("logs", region_name=region)

    credits_table = dynamodb.Table("infrasketch-user-credits")
    sessions_table = dynamodb.Table("infrasketch-sessions")
    transactions_table = dynamodb.Table("infrasketch-credit-transactions")
    gamification_table = dynamodb.Table("infrasketch-user-gamification")
    preferences_table = dynamodb.Table("infrasketch-user-preferences")

    log_fn("Scanning infrasketch-user-credits for paying users...")
    paying_users = fetch_paying_users(credits_table)
    log_fn(f"Found {len(paying_users)} paying users (plan in starter/pro/enterprise).")

    if not paying_users:
        return ([], {"n": 0}, datetime.now(timezone.utc))

    log_fn(f"Fetching DynamoDB signals for {len(paying_users)} users...")
    dynamo_by_user: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(
                fetch_user_dynamo_signals,
                u["user_id"],
                sessions_table,
                transactions_table,
                gamification_table,
                preferences_table,
            ): u["user_id"]
            for u in paying_users
        }
        done = 0
        for fut in as_completed(futs):
            uid = futs[fut]
            try:
                dynamo_by_user[uid] = fut.result()
            except Exception as e:
                log_fn(f"  failed for {uid}: {e}")
                dynamo_by_user[uid] = {"sessions": [], "transactions": [], "gamification": None, "preferences": None}
            done += 1
            if done % 5 == 0 or done == len(paying_users):
                log_fn(f"  {done}/{len(paying_users)}")

    all_session_ids = []
    for d in dynamo_by_user.values():
        for s in d["sessions"]:
            sid = s.get("session_id")
            if sid:
                all_session_ids.append(str(sid))
    log_fn(f"Querying CloudWatch Logs Insights for {len(all_session_ids)} sessions across cohort (last {CW_LOG_LOOKBACK_DAYS} days)...")
    cw = fetch_cloudwatch_signals(logs, all_session_ids)
    log_fn(f"  CloudWatch returned data for {len(cw['by_session'])} sessions.")

    log_fn("Computing per-customer signals...")
    signals = []
    for u in paying_users:
        uid = u["user_id"]
        sig = compute_signals(u, dynamo_by_user[uid], cw["by_session"], cw["window"])
        signals.append(sig)

    log_fn("Aggregating...")
    agg = aggregate(signals)
    return signals, agg, datetime.now(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description="Analyze paying customer conversion patterns.")
    parser.add_argument("--dry-run", action="store_true", help="Print cohort summary without writing the report or running CloudWatch queries.")
    parser.add_argument("--output", default=None, help="Output Markdown path. Default: marketing/conversion-analysis-{YYYY-MM-DD}.md")
    parser.add_argument("--region", default=REGION, help="AWS region.")
    parser.add_argument("--max-workers", type=int, default=8, help="Parallel DynamoDB fetches.")
    args = parser.parse_args()

    if args.dry_run:
        boto3.setup_default_session(region_name=args.region)
        dynamodb = boto3.resource("dynamodb", region_name=args.region)
        credits_table = dynamodb.Table("infrasketch-user-credits")
        print(f"Scanning infrasketch-user-credits for paying users...")
        paying_users = fetch_paying_users(credits_table)
        print(f"Found {len(paying_users)} paying users (plan in starter/pro/enterprise).")
        print("\n=== Dry run cohort summary ===")
        plan_dist = Counter(str(u.get("plan")) for u in paying_users)
        status_dist = Counter(str(u.get("subscription_status")) for u in paying_users)
        print(f"  Plan distribution: {dict(plan_dist)}")
        print(f"  Subscription status: {dict(status_dist)}")
        for u in paying_users[:10]:
            print(
                f"  - user_id={u.get('user_id')} plan={u.get('plan')} "
                f"status={u.get('subscription_status')} "
                f"plan_started_at={u.get('plan_started_at')} "
                f"signup={u.get('created_at')}"
            )
        if len(paying_users) > 10:
            print(f"  ... and {len(paying_users) - 10} more")
        return 0

    signals, agg, generated_at = run_analysis(region=args.region, max_workers=args.max_workers)
    if agg["n"] == 0:
        print("No paying users to analyze. Exiting.")
        return 0

    output_path = args.output
    if not output_path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = f"marketing/conversion-analysis-{date_str}.md"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    report = render_report(signals, agg, generated_at)
    output_file.write_text(report)

    print(f"\nReport written: {output_file}")
    print(f"Cohort: {agg['n']} | Plans: {agg.get('plan_distribution')} | MRR estimate: ${agg.get('estimated_mrr_usd')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
