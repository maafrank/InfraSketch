"""
AWS Lambda function for sending daily streak reminder emails.
Triggered by EventBridge at 6 PM UTC (noon EST) daily.

Flow:
1. Scan gamification table for at-risk users (active streak, not active today)
2. Cross-reference subscriber table for email addresses
3. Send personalized reminder emails via Resend API

Environment variables:
    RESEND_API_KEY_SECRET - Secrets Manager name for Resend API key
    AWS_REGION - AWS region (default: us-east-1)
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


# --- Secrets Manager helper ---

_secrets_cache = {}


def _get_secret(secret_name, key_name=None):
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


def get_resend_api_key():
    key = os.environ.get("RESEND_API_KEY")
    if key:
        return key
    secret_name = os.environ.get(
        "RESEND_API_KEY_SECRET", "infrasketch/resend-api-key"
    )
    return _get_secret(secret_name, "RESEND_API_KEY")


# --- Configuration ---

GAMIFICATION_TABLE = "infrasketch-user-gamification"
SUBSCRIBER_TABLE = "infrasketch-subscribers"
REGION = os.getenv("AWS_REGION", "us-east-1")
SENDER_EMAIL = "contact@infrasketch.net"
SENDER_NAME = "InfraSketch"
RESEND_API_URL = "https://api.resend.com/emails"
API_BASE_URL = "https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api"

# --- XP Level definitions (inlined from backend/app/gamification/xp.py) ---

LEVELS = [
    (0, "Intern"),
    (50, "Junior Designer"),
    (150, "Designer"),
    (350, "Senior Designer"),
    (600, "Architect"),
    (1000, "Senior Architect"),
    (1600, "Lead Architect"),
    (2500, "Principal Architect"),
    (4000, "Distinguished Architect"),
    (6000, "Chief Architect"),
]
TOTAL_ACHIEVEMENTS = 32


def _compute_xp_progress(xp_total, level_num):
    """Compute XP progress to next level. Returns (xp_in_level, xp_needed, pct, xp_to_next)."""
    level_idx = max(0, min(level_num - 1, len(LEVELS) - 1))
    current_threshold = LEVELS[level_idx][0]

    if level_idx < len(LEVELS) - 1:
        next_threshold = LEVELS[level_idx + 1][0]
        xp_in_level = xp_total - current_threshold
        xp_needed = next_threshold - current_threshold
        pct = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100
        xp_to_next = next_threshold - xp_total
    else:
        xp_in_level = 0
        xp_needed = 0
        pct = 100
        xp_to_next = 0

    return xp_in_level, xp_needed, pct, max(xp_to_next, 0)


# --- DynamoDB helpers ---


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def scan_at_risk_users(dynamodb, today_str):
    """Scan gamification table for users at risk of losing their streak."""
    table = dynamodb.Table(GAMIFICATION_TABLE)

    filter_expr = (
        "current_streak > :zero "
        "AND last_active_date < :today "
        "AND (attribute_not_exists(streak_reminders_enabled) "
        "OR streak_reminders_enabled = :enabled)"
    )
    expr_values = {
        ":zero": 0,
        ":today": today_str,
        ":enabled": True,
    }

    results = []
    response = table.scan(
        FilterExpression=filter_expr,
        ExpressionAttributeValues=expr_values,
    )
    results.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=filter_expr,
            ExpressionAttributeValues=expr_values,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        results.extend(response.get("Items", []))

    return results


def get_subscriber_email(dynamodb, user_id):
    """Look up a user's email from the subscriber table."""
    table = dynamodb.Table(SUBSCRIBER_TABLE)
    try:
        response = table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if item and item.get("subscribed", False):
            return item.get("email"), item.get("unsubscribe_token")
    except Exception as e:
        print(f"Error looking up subscriber {user_id}: {e}")
    return None, None


# --- Email generation ---


def build_email_html(
    streak_count,
    grace_used,
    unsubscribe_token,
    level=1,
    level_name="Intern",
    xp_total=0,
    longest_streak=0,
    achievements_count=0,
):
    """Build the streak reminder email HTML with gamification stats."""
    # Compute XP progress
    _xp_in, _xp_needed, xp_pct, xp_to_next = _compute_xp_progress(xp_total, level)
    is_max_level = level >= len(LEVELS)

    # Variant-specific colors and text
    if grace_used:
        urgency_text = "This is your last chance. Your grace day has already been used."
        accent_color = "#00b830"
        headline = "Your streak is about to end"
    else:
        urgency_text = "You still have a grace day available, but why risk it?"
        accent_color = "#00b830"
        headline = "Keep your streak alive"

    unsubscribe_url = (
        f"{API_BASE_URL}/unsubscribe/{unsubscribe_token}"
        if unsubscribe_token
        else "#"
    )

    # XP progress subtitle
    xp_subtitle = "Max level reached" if is_max_level else f"{xp_to_next} XP to next level"

    # XP progress bar width (clamp to 100)
    bar_pct = min(xp_pct, 100)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline} - InfraSketch</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0a0a0a;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #1a3a1a;">

                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0d1117; padding: 30px 40px; text-align: center; border-bottom: 1px solid #1a3a1a;">
                            <img src="https://infrasketch.net/InfraSketchLogoTransparent_03_256.png"
                                 alt="InfraSketch"
                                 width="48"
                                 height="48"
                                 style="display: inline-block; vertical-align: middle; margin-right: 12px;"
                            />
                            <span style="color: #00b830; font-size: 28px; font-weight: 600; vertical-align: middle;">
                                InfraSketch
                            </span>
                            <p style="color: #00b830; margin: 10px 0 0 0; font-size: 14px; letter-spacing: 1px;">
                                Streak Reminder
                            </p>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="color: #e6edf3; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                                {headline}
                            </h2>

                            <!-- Streak counter -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center" style="padding: 20px 0 30px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="background-color: #0d1117; border-radius: 12px; border: 2px solid {accent_color};">
                                            <tr>
                                                <td style="padding: 20px 40px; text-align: center;">
                                                    <div style="font-size: 48px; font-weight: 700; color: {accent_color};">
                                                        {streak_count}
                                                    </div>
                                                    <div style="font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">
                                                        day streak
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Gamification Stats Grid -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                                <!-- Row 1: Level + XP -->
                                <tr>
                                    <td width="50%" style="padding: 0 6px 12px 0; vertical-align: top;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0d1117; border: 1px solid #1a3a1a; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 14px 16px;">
                                                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                                                        Level
                                                    </div>
                                                    <div style="font-size: 22px; font-weight: 700; color: #00b830;">
                                                        Level {level}
                                                    </div>
                                                    <div style="font-size: 13px; color: #c9d1d9; margin-top: 2px;">
                                                        {level_name}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td width="50%" style="padding: 0 0 12px 6px; vertical-align: top;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0d1117; border: 1px solid #1a3a1a; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 14px 16px;">
                                                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                                                        Experience
                                                    </div>
                                                    <div style="font-size: 22px; font-weight: 700; color: #00b830;">
                                                        {xp_total} XP
                                                    </div>
                                                    <div style="font-size: 13px; color: #c9d1d9; margin-top: 2px;">
                                                        {xp_subtitle}
                                                    </div>
                                                    <!-- XP Progress Bar -->
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 8px;">
                                                        <tr>
                                                            <td style="background-color: #2d333b; border-radius: 3px; height: 6px; font-size: 0; line-height: 0;">
                                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="{bar_pct}%">
                                                                    <tr>
                                                                        <td style="background-color: #00b830; border-radius: 3px; height: 6px; font-size: 0; line-height: 0;">
                                                                            &nbsp;
                                                                        </td>
                                                                    </tr>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Row 2: Best Streak + Achievements -->
                                <tr>
                                    <td width="50%" style="padding: 0 6px 0 0; vertical-align: top;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0d1117; border: 1px solid #1a3a1a; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 14px 16px;">
                                                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                                                        Best Streak
                                                    </div>
                                                    <div style="font-size: 22px; font-weight: 700; color: #00b830;">
                                                        {longest_streak}
                                                    </div>
                                                    <div style="font-size: 13px; color: #c9d1d9; margin-top: 2px;">
                                                        days
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td width="50%" style="padding: 0 0 0 6px; vertical-align: top;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0d1117; border: 1px solid #1a3a1a; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 14px 16px;">
                                                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                                                        Achievements
                                                    </div>
                                                    <div style="font-size: 22px; font-weight: 700; color: #00b830;">
                                                        {achievements_count} / {TOTAL_ACHIEVEMENTS}
                                                    </div>
                                                    <div style="font-size: 13px; color: #c9d1d9; margin-top: 2px;">
                                                        unlocked
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="color: #c9d1d9; font-size: 16px; line-height: 1.6; margin: 0 0 10px 0;">
                                You have not used InfraSketch today, and your <strong style="color: #e6edf3;">{streak_count}-day streak</strong> is at risk.
                            </p>

                            <p style="color: {accent_color}; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0; font-weight: 500;">
                                {urgency_text}
                            </p>

                            <p style="color: #c9d1d9; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                Just open InfraSketch and do anything: create a diagram, send a chat message, or make a quick edit. It only takes a moment to keep your progress going.
                            </p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center" style="padding: 20px 0 10px 0;">
                                        <a href="https://infrasketch.net"
                                           style="display: inline-block; background: linear-gradient(135deg, #00b830 0%, #009926 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-size: 16px; font-weight: 600;">
                                            Open InfraSketch
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #0d1117; padding: 30px 40px; border-top: 1px solid #1a3a1a;">
                            <p style="color: #8b949e; font-size: 12px; margin: 0; text-align: center; line-height: 1.6;">
                                You are receiving this because you have an active streak on InfraSketch.<br>
                                <a href="{unsubscribe_url}" style="color: #00b830; text-decoration: underline;">Unsubscribe from all emails</a>
                                &nbsp;|&nbsp;
                                <a href="https://infrasketch.net/settings" style="color: #00b830; text-decoration: underline;">Manage streak reminders</a>
                            </p>
                            <p style="color: #6e7681; font-size: 12px; margin: 15px 0 0 0; text-align: center;">
                                2026 InfraSketch. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    return html


def send_email(api_key, to_email, subject, html_content):
    """Send email via Resend API."""
    data = json.dumps({
        "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "reply_to": SENDER_EMAIL,
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "InfraSketch/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"Resend API error for {to_email}: {e.code} {body}")
        return False
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")
        return False


# --- Lambda handler ---


def lambda_handler(event, context):
    """Main Lambda entry point. Triggered daily by EventBridge."""
    print("Starting streak reminder check...")
    today_str = datetime.utcnow().date().isoformat()
    print(f"Today (UTC): {today_str}")

    # Get Resend API key
    resend_key = get_resend_api_key()
    if not resend_key:
        raise RuntimeError("STREAK_REMINDER_ERROR: Could not retrieve Resend API key from Secrets Manager")

    # Connect to DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    # Step 1: Scan for at-risk users
    at_risk_users = scan_at_risk_users(dynamodb, today_str)
    print(f"Found {len(at_risk_users)} at-risk users")

    if not at_risk_users:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No at-risk users found", "sent": 0}),
        }

    # Step 2: Cross-reference and send emails
    sent = 0
    skipped = 0
    failed = 0

    for user_data in at_risk_users:
        user_id = user_data.get("user_id", "")
        streak = int(user_data.get("current_streak", 0))
        grace_used = user_data.get("streak_grace_used", False)

        # Extract gamification data
        level = int(user_data.get("level", 1))
        level_name = user_data.get("level_name", "Intern")
        xp_total = int(user_data.get("xp_total", 0))
        longest_streak = int(user_data.get("longest_streak", 0))
        achievements = user_data.get("achievements", [])
        achievements_count = len(achievements) if isinstance(achievements, list) else 0

        # Look up email
        email, unsub_token = get_subscriber_email(dynamodb, user_id)
        if not email:
            skipped += 1
            continue

        # Build and send email
        if grace_used:
            subject = f"Your {streak}-day streak ends today"
        else:
            subject = f"Keep your {streak}-day streak alive"

        html = build_email_html(
            streak,
            grace_used,
            unsub_token,
            level=level,
            level_name=level_name,
            xp_total=xp_total,
            longest_streak=longest_streak,
            achievements_count=achievements_count,
        )
        success = send_email(resend_key, email, subject, html)

        if success:
            sent += 1
            print(f"  Sent to {user_id} (streak: {streak}, grace_used: {grace_used})")
        else:
            failed += 1

        # Rate limit: 1 second between requests to stay within Resend limits
        time.sleep(1.0)

    summary = {
        "at_risk_users": len(at_risk_users),
        "emails_sent": sent,
        "skipped_no_email": skipped,
        "failed": failed,
        "date": today_str,
    }
    print(f"Summary: {json.dumps(summary)}")

    # Fail loudly if ANY email sends failed
    if failed > 0:
        error_msg = (
            f"STREAK_REMINDER_ERROR: {failed} of {sent + failed} email(s) failed to send. "
            f"Sent: {sent}, Failed: {failed}, Skipped: {skipped}"
        )
        print(error_msg)

        # If ALL sends failed, raise so CloudWatch Lambda Errors metric fires
        # and the alarm triggers immediately
        if sent == 0:
            raise RuntimeError(error_msg)

        # Partial failure: return 500 so it's visible, but don't raise
        # (raising would retry and potentially duplicate the successful sends)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Streak reminders partially failed",
                **summary,
            }),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Streak reminders processed", **summary}),
    }


# Local testing
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    result = lambda_handler({}, None)
    print(json.dumps(json.loads(result["body"]), indent=2))
