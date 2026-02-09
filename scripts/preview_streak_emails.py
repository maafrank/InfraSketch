"""Generate streak reminder email previews as HTML files.

Run: python scripts/preview_streak_emails.py
Opens HTML files in your browser for each variant:
  - warning (grace available, mid-level user)
  - last-chance (grace used, mid-level user)
  - new-user-warning (low level, few achievements)
  - max-level (Chief Architect, high stats)
"""

import os
import sys
import webbrowser
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from lambda_streak_reminder import build_email_html

PREVIEW_DIR = tempfile.mkdtemp(prefix="streak-preview-")

# Use local logo path so preview works without network
LOGO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "InfraSketchLogoTransparent_03_256.png")
)
LOCAL_LOGO_URL = f"file://{LOGO_PATH}"

variants = [
    {
        "name": "warning",
        "streak": 7,
        "grace_used": False,
        "desc": "Warning (grace day still available)",
        "level": 5,
        "level_name": "Architect",
        "xp_total": 780,
        "longest_streak": 14,
        "achievements_count": 18,
    },
    {
        "name": "last-chance",
        "streak": 7,
        "grace_used": True,
        "desc": "Last chance (grace day already used)",
        "level": 5,
        "level_name": "Architect",
        "xp_total": 780,
        "longest_streak": 14,
        "achievements_count": 18,
    },
    {
        "name": "new-user-warning",
        "streak": 2,
        "grace_used": False,
        "desc": "New user warning (low level, few achievements)",
        "level": 1,
        "level_name": "Intern",
        "xp_total": 30,
        "longest_streak": 2,
        "achievements_count": 2,
    },
    {
        "name": "max-level",
        "streak": 45,
        "grace_used": False,
        "desc": "Max level user (Chief Architect)",
        "level": 10,
        "level_name": "Chief Architect",
        "xp_total": 7500,
        "longest_streak": 100,
        "achievements_count": 28,
    },
]

for v in variants:
    html = build_email_html(
        v["streak"],
        v["grace_used"],
        "sample-token-123",
        level=v["level"],
        level_name=v["level_name"],
        xp_total=v["xp_total"],
        longest_streak=v["longest_streak"],
        achievements_count=v["achievements_count"],
    )
    # Swap production URL for local file path in previews
    html = html.replace(
        "https://infrasketch.net/InfraSketchLogoTransparent_03_256.png",
        LOCAL_LOGO_URL,
    )
    path = os.path.join(PREVIEW_DIR, f"streak-{v['name']}.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"  {v['desc']}: {path}")
    webbrowser.open(f"file://{path}")

print(f"\nPreview files saved to: {PREVIEW_DIR}")
