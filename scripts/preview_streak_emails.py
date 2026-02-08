"""Generate streak reminder email previews as HTML files.

Run: python scripts/preview_streak_emails.py
Opens two HTML files in your browser: warning (amber) and last-chance (red).
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
    },
    {
        "name": "last-chance",
        "streak": 7,
        "grace_used": True,
        "desc": "Last chance (grace day already used)",
    },
]

for v in variants:
    html = build_email_html(v["streak"], v["grace_used"], "sample-token-123")
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
