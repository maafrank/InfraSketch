#!/usr/bin/env python3
"""
Send feature announcement emails to InfraSketch subscribers.

Usage:
    # Preview in browser (sends nothing)
    python scripts/send_announcement.py announcements/my-feature.html --preview

    # Test mode (default) - sends to mattafrank2439@gmail.com only
    python scripts/send_announcement.py announcements/my-feature.html

    # Send to a specific subscriber email
    python scripts/send_announcement.py announcements/my-feature.html --to user@example.com

    # Production - sends to ALL subscribed users
    python scripts/send_announcement.py announcements/my-feature.html --production

Requirements:
    - RESEND_API_KEY environment variable set
    - AWS credentials configured for DynamoDB access (subscriber storage)
    - HTML file must exist and contain valid email HTML
    - HTML file should have a <title> tag (used as email subject)
"""

import os
import sys
import re
import argparse
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path

import resend
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Initialize Resend API key early
resend.api_key = os.environ.get("RESEND_API_KEY")

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.subscription.storage import SubscriberStorage

# Configuration
SENDER_EMAIL = "contact@infrasketch.net"
SENDER_NAME = "InfraSketch"
TEST_RECIPIENT = "mattafrank2439@gmail.com"
UNSUBSCRIBE_BASE_URL = "https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api/unsubscribe"


def extract_subject_from_html(html_content: str) -> str:
    """Extract the title from HTML to use as email subject."""
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return "New Updates from InfraSketch"


def inject_unsubscribe_link(html_content: str, token: str) -> str:
    """
    Inject the unsubscribe link into the HTML content.
    Replaces {{UNSUBSCRIBE_URL}} placeholder with actual URL.
    """
    unsubscribe_url = f"{UNSUBSCRIBE_BASE_URL}/{token}"
    return html_content.replace("{{UNSUBSCRIBE_URL}}", unsubscribe_url)


def inject_test_banner(html_content: str, original_email: str) -> str:
    """
    Inject a test mode banner at the top of the email.
    """
    test_banner = f'''
    <div style="background-color: #fef3c7; border: 2px solid #f59e0b; padding: 15px; margin-bottom: 20px; text-align: center; font-family: sans-serif;">
        <strong style="color: #92400e;">[TEST MODE]</strong>
        <br>
        <span style="color: #78350f;">This email would have been sent to: <strong>{original_email}</strong></span>
    </div>
    '''
    # Insert after <body> tag
    if '<body>' in html_content.lower():
        html_content = re.sub(
            r'(<body[^>]*>)',
            r'\1' + test_banner,
            html_content,
            flags=re.IGNORECASE
        )
    else:
        html_content = test_banner + html_content

    return html_content


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via Resend API."""
    try:
        response = resend.Emails.send({
            "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "reply_to": SENDER_EMAIL
        })
        return True
    except Exception as e:
        print(f"   ERROR sending to {to_email}: {e}")
        return False


def preview_email(html_content: str, subject: str):
    """Open the email in a browser for preview."""
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        # Add subject as visible header for preview
        preview_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Preview: {subject}</title>
            <style>
                .preview-header {{
                    background: #1f2937;
                    color: white;
                    padding: 20px;
                    font-family: sans-serif;
                    position: sticky;
                    top: 0;
                }}
                .preview-header h2 {{ margin: 0 0 10px 0; }}
                .preview-header p {{ margin: 0; opacity: 0.8; }}
                .preview-content {{
                    max-width: 600px;
                    margin: 20px auto;
                    border: 1px solid #e5e7eb;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body style="margin: 0; background: #f3f4f6;">
            <div class="preview-header">
                <h2>Email Preview</h2>
                <p><strong>Subject:</strong> {subject}</p>
                <p><strong>From:</strong> {SENDER_NAME} &lt;{SENDER_EMAIL}&gt;</p>
            </div>
            <div class="preview-content">
                {html_content}
            </div>
        </body>
        </html>
        '''
        f.write(preview_html)
        temp_path = f.name

    print(f"\nOpening preview in browser...")
    webbrowser.open(f'file://{temp_path}')
    print(f"Preview file: {temp_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Send feature announcement emails to InfraSketch subscribers.'
    )
    parser.add_argument(
        'html_file',
        type=str,
        help='Path to the HTML email file'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Open email in browser instead of sending'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Send to ALL subscribed users (requires explicit flag for safety)'
    )
    parser.add_argument(
        '--to',
        type=str,
        metavar='EMAIL',
        help='Send to a specific subscriber email address (must be in subscriber list)'
    )

    args = parser.parse_args()

    # Validate HTML file exists
    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"ERROR: HTML file not found: {html_path}")
        sys.exit(1)

    # Read HTML content
    with open(html_path, 'r') as f:
        html_content = f.read()

    # Extract subject from HTML title
    subject = extract_subject_from_html(html_content)

    print("=" * 60)
    print("InfraSketch Feature Announcement")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    print(f"\nHTML File: {html_path}")
    print(f"Subject: {subject}")

    # Preview mode
    if args.preview:
        print("\nMode: PREVIEW (opening in browser)")
        # Use a sample unsubscribe URL for preview
        preview_content = inject_unsubscribe_link(html_content, "sample-token-12345")
        preview_email(preview_content, subject)
        print("\nDone! No emails sent.")
        return

    # Get subscribers
    print("\nConnecting to subscriber database...")
    storage = SubscriberStorage()
    subscribers = storage.get_all_subscribed()
    counts = storage.get_subscriber_count()

    print(f"Total subscribers: {counts['total']}")
    print(f"Subscribed (opted-in): {counts['subscribed']}")
    print(f"Unsubscribed: {counts['unsubscribed']}")

    if not subscribers:
        print("\nNo subscribed users found. Exiting.")
        return

    # Determine mode
    if args.to:
        # Send to a specific subscriber
        mode = "TARGETED"
        target_email = args.to.lower().strip()
        matching = [s for s in subscribers if s.email.lower() == target_email]
        if not matching:
            print(f"\nERROR: Email '{args.to}' not found in subscriber list.")
            print("Make sure the email is subscribed before sending.")
            sys.exit(1)
        recipients = matching
        print(f"\nMode: {mode}")
        print(f"Will send to: {recipients[0].email}")
    elif args.production:
        mode = "PRODUCTION"
        recipients = subscribers
        print(f"\nMode: {mode}")
        print(f"Will send to: {len(recipients)} subscribers")
        print("\n⚠️  WARNING: This will send real emails to all subscribers!")
        confirm = input("Type 'SEND' to confirm: ")
        if confirm != 'SEND':
            print("Aborted.")
            return
    else:
        mode = "TEST"
        recipients = subscribers  # We still iterate to show who would receive
        print(f"\nMode: {mode}")
        print(f"All emails will be sent to: {TEST_RECIPIENT}")
        print(f"Would send to {len(recipients)} subscribers in production")

    # Verify Resend API key is set
    if not resend.api_key:
        print("\nERROR: RESEND_API_KEY environment variable not set.")
        print("Set it in your .env file or export it: export RESEND_API_KEY=re_...")
        sys.exit(1)

    # Send emails
    print("\nSending emails...")
    sent = 0
    failed = 0

    for subscriber in recipients:
        # Inject unsubscribe link for this subscriber
        personalized_html = inject_unsubscribe_link(html_content, subscriber.unsubscribe_token)

        if mode == "TEST":
            # In test mode, send to test recipient with banner showing original
            personalized_html = inject_test_banner(personalized_html, subscriber.email)
            to_email = TEST_RECIPIENT
            final_subject = f"[TEST] {subject}"
        elif mode == "TARGETED":
            # Targeted mode: send directly to the specified subscriber
            to_email = subscriber.email
            final_subject = subject
        else:
            # Production mode
            to_email = subscriber.email
            final_subject = subject

        success = send_email(to_email, final_subject, personalized_html)

        if success:
            print(f"   ✓ Sent to {to_email}" + (f" (originally for {subscriber.email})" if mode == "TEST" else ""))
            sent += 1
        else:
            failed += 1

        # In test mode, only send once (to yourself)
        if mode == "TEST":
            print(f"\n   (Test mode: stopping after first email)")
            print(f"   In production, would send to {len(recipients)} subscribers")
            break

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Emails sent: {sent}")
    print(f"Emails failed: {failed}")
    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == '__main__':
    main()
