"""
AWS Lambda function for weekly conversion-customer analysis.

Runs analyze_conversions.run_analysis() against production DynamoDB and CloudWatch,
then emails the rendered Markdown report (plus a small text summary) via SES.

Triggered by EventBridge on a weekly schedule (Mondays 9 AM PST by default).
Manual invoke is safe: read-only against production data, only side effect is the email.
"""

import json
import logging
from datetime import datetime, timezone

import boto3

from analyze_conversions import render_report, run_analysis

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client("ses", region_name="us-east-1")

SENDER_EMAIL = "reports@infrasketch.net"
RECIPIENT_EMAIL = "mattafrank2439@gmail.com"


def _markdown_to_html(md: str) -> str:
    """
    Minimal Markdown → HTML conversion sufficient for the email.

    We keep this in-Lambda to avoid pulling a markdown dep into the package.
    Handles: # headers, **bold**, _italic_, `code`, > quotes, lists, tables,
    paragraphs, horizontal rules.
    """
    import re

    lines = md.splitlines()
    out = []
    in_list = False
    in_table = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    def inline(text: str) -> str:
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", text)
        return text

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            close_list()
            close_table()
            out.append("")
            continue

        if stripped.startswith("---"):
            close_list()
            close_table()
            out.append("<hr/>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            close_table()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            if not in_table:
                close_list()
                in_table = True
                out.append('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;border-color:#ddd"><tbody>')
            row_html = "".join(f"<td>{inline(c)}</td>" for c in cells)
            out.append(f"<tr>{row_html}</tr>")
            continue
        else:
            close_table()

        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            close_table()
            if not in_list:
                in_list = True
                out.append("<ul>")
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue
        else:
            close_list()

        if stripped.startswith(">"):
            out.append(f"<blockquote>{inline(stripped[1:].strip())}</blockquote>")
            continue

        out.append(f"<p>{inline(stripped)}</p>")

    close_list()
    close_table()
    return "\n".join(out)


def _build_text_summary(agg: dict, generated_at: datetime) -> str:
    if agg["n"] == 0:
        return "No paying customers found this week."
    ttc = agg.get("time_to_convert_hours", {})
    median_h = ttc.get("median")
    median_str = f"{median_h:.1f}h" if median_h is not None else "n/a"
    plans = agg.get("plan_distribution", {})
    plan_str = ", ".join(f"{p}: {c}" for p, c in plans.items())
    return (
        f"InfraSketch conversion report — {generated_at.strftime('%Y-%m-%d')}\n"
        f"Paying customers: {agg['n']}\n"
        f"Plan mix: {plan_str}\n"
        f"Estimated MRR: ${agg.get('estimated_mrr_usd', 0):.2f}\n"
        f"Median time to convert: {median_str}\n"
        f"% who hit free limit before paying: {agg.get('pct_hit_free_limit_before_paying', 0):.0f}%\n"
        f"% who tried design doc preview before paying: {agg.get('pct_tried_design_doc_preview', 0):.0f}%\n"
        f"% who used a promo code: {agg.get('pct_used_promo_code', 0):.0f}%\n"
    )


def _send_email(subject: str, text_body: str, html_body: str) -> None:
    response = ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [RECIPIENT_EMAIL]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    )
    logger.info(f"Email sent: MessageId={response['MessageId']}")


def lambda_handler(event, context):
    logger.info("Starting conversion analysis...")
    try:
        signals, agg, generated_at = run_analysis(log_fn=logger.info)

        report_md = render_report(signals, agg, generated_at)
        text_summary = _build_text_summary(agg, generated_at)
        html_body = (
            "<html><body style=\"font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#333\">"
            + _markdown_to_html(report_md)
            + "</body></html>"
        )

        date_str = generated_at.strftime("%Y-%m-%d")
        subject = f"InfraSketch conversion report — {date_str} (cohort: {agg['n']})"

        _send_email(subject=subject, text_body=text_summary, html_body=html_body)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Conversion report sent",
                    "cohort_size": agg["n"],
                    "plan_distribution": agg.get("plan_distribution", {}),
                    "estimated_mrr_usd": agg.get("estimated_mrr_usd", 0),
                }
            ),
        }
    except Exception as e:
        logger.exception("Conversion report failed")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    print(json.dumps(lambda_handler({}, None), indent=2))
