#!/bin/bash
# Daily Content Pipeline - Unified script for EC2 cron deployment
#
# Runs the full pipeline: generate screenshots -> stitch video -> upload to all platforms
#
# Usage:
#   ./run-daily-pipeline.sh              # Auto-calculates day number from start date
#   ./run-daily-pipeline.sh --day 42     # Override day number
#   ./run-daily-pipeline.sh --dry-run    # Generate content but skip upload
#
# Environment (loaded from .env):
#   INFRASKETCH_URL, CLERK_SECRET_KEY, CLERK_USER_ID,
#   UPLOAD_POST_API_KEY, UPLOAD_POST_PROFILE, OPENAI_API_KEY

set -euo pipefail

# Ensure cron has access to all required binaries
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Timestamp for logging
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Send failure alert via SNS (same topic as Lambda alarms)
send_failure_alert() {
  local msg="$1"
  local log_file="$LOG_DIR/pipeline-$(date '+%Y-%m-%d').log"
  local tail_log=$(tail -20 "$log_file" 2>/dev/null || echo "No log available")
  aws sns publish \
    --topic-arn "arn:aws:sns:us-east-1:059409992371:infrasketch-alerts" \
    --subject "Content Pipeline FAILED - Day ${DAY_NUMBER:-unknown}" \
    --message "Pipeline failed: $msg

Last 20 lines of log:
$tail_log" \
    --region us-east-1 2>/dev/null || true
}

# Load .env
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
DAY_NUMBER=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --day) DAY_NUMBER="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Calculate day number if not provided
# Day 1 = April 7, 2026
# ---------------------------------------------------------------------------
if [ -z "$DAY_NUMBER" ]; then
  START_DATE="2026-04-07"
  TODAY=$(date '+%Y-%m-%d')

  # Calculate days difference (works on both macOS and Linux)
  if date --version >/dev/null 2>&1; then
    # GNU date (Linux)
    START_EPOCH=$(date -d "$START_DATE" +%s)
    TODAY_EPOCH=$(date -d "$TODAY" +%s)
  else
    # BSD date (macOS)
    START_EPOCH=$(date -j -f "%Y-%m-%d" "$START_DATE" +%s)
    TODAY_EPOCH=$(date -j -f "%Y-%m-%d" "$TODAY" +%s)
  fi

  DAY_NUMBER=$(( (TODAY_EPOCH - START_EPOCH) / 86400 + 1 ))
fi

if [ "$DAY_NUMBER" -lt 1 ] || [ "$DAY_NUMBER" -gt 365 ]; then
  log "ERROR: Day $DAY_NUMBER is outside the 1-365 range"
  exit 1
fi

log "=== Daily Content Pipeline - Day $DAY_NUMBER ==="
log "Dry run: $DRY_RUN"

# ---------------------------------------------------------------------------
# Step 1: Generate screenshots with Puppeteer
# ---------------------------------------------------------------------------
log "Step 1: Generating content (Puppeteer)..."

GENERATE_OUTPUT=$(cd "$SCRIPT_DIR" && node generate-content.js --from-calendar "$DAY_NUMBER" 2>&1) || {
  log "ERROR: Content generation failed"
  echo "$GENERATE_OUTPUT"
  send_failure_alert "Content generation failed"
  exit 1
}
echo "$GENERATE_OUTPUT"

# Extract output directory from the log
OUTPUT_DIR=$(echo "$GENERATE_OUTPUT" | grep "^Output:" | head -1 | sed 's/Output: //')
if [ -z "$OUTPUT_DIR" ]; then
  log "ERROR: Could not determine output directory"
  exit 1
fi
log "Output directory: $OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Step 2: Stitch video with voiceover
# ---------------------------------------------------------------------------
log "Step 2: Stitching video..."

bash "$SCRIPT_DIR/stitch-video.sh" "$OUTPUT_DIR" "$DAY_NUMBER" || {
  log "ERROR: Video stitching failed"
  send_failure_alert "Video stitching failed"
  exit 1
}

# Verify video files exist
if [ ! -f "$OUTPUT_DIR/reel.mp4" ]; then
  log "ERROR: reel.mp4 not found in $OUTPUT_DIR"
  exit 1
fi
log "Video files ready: reel.mp4, post.mp4"

# ---------------------------------------------------------------------------
# Step 3: Read metadata for captions
# ---------------------------------------------------------------------------
METADATA_FILE="$OUTPUT_DIR/metadata.json"
if [ ! -f "$METADATA_FILE" ]; then
  log "ERROR: metadata.json not found"
  exit 1
fi

# Extract fields from metadata using node (avoids jq dependency)
CAPTIONS=$(node -e "
const meta = require('$METADATA_FILE');
const cal = meta.calendar || {};
const title = cal.title || 'Day $DAY_NUMBER';
const hashtags = cal.hashtags || '#systemdesign #infrasketch';

const ytTitle = ('Day $DAY_NUMBER: ' + title + ' - AI System Design in Seconds #Shorts').substring(0, 100);
const ytDesc = 'Day $DAY_NUMBER/365: ' + title + '\\n\\nAI-generated system architecture in seconds. Watch as InfraSketch designs a complete ' + title.toLowerCase() + ' architecture, then generates a full design document.\\n\\nTry InfraSketch free: https://infrasketch.net\\n\\n' + hashtags + ' #Shorts #systemdesign #softwarearchitecture #programming #developer #tech #coding #software #engineering';
const tiktokCaption = cal.tiktokCaption || ('Day $DAY_NUMBER/365: ' + title + ' - AI designs your architecture in seconds. Try it free at infrasketch.net ' + hashtags);
const igCaption = cal.instagramCaption || ('Day $DAY_NUMBER/365: ' + title + '\\n\\nAI-powered system design in seconds. Try it free at infrasketch.net\\n\\n' + hashtags);

console.log(JSON.stringify({ ytTitle, ytDesc, tiktokCaption, igCaption, title, hashtags }));
")

YT_TITLE=$(echo "$CAPTIONS" | node -e "process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).ytTitle)")
YT_DESC=$(echo "$CAPTIONS" | node -e "process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).ytDesc)")
TIKTOK_CAPTION=$(echo "$CAPTIONS" | node -e "process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).tiktokCaption)")
IG_CAPTION=$(echo "$CAPTIONS" | node -e "process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).igCaption)")

log "Title: $YT_TITLE"

# ---------------------------------------------------------------------------
# Step 4: Upload to all platforms via Upload-Post API
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = true ]; then
  log "DRY RUN: Skipping upload. Video ready at: $OUTPUT_DIR/reel.mp4"
  log "Would post to: YouTube, TikTok, Instagram, Facebook, X, Threads, LinkedIn"
  exit 0
fi

log "Step 3: Uploading to all platforms via Upload-Post..."

UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.upload-post.com/api/upload" \
  -H "Authorization: Apikey $UPLOAD_POST_API_KEY" \
  -F "video=@$OUTPUT_DIR/reel.mp4" \
  -F "user=${UPLOAD_POST_PROFILE:-InfraSketch}" \
  -F "platform[]=youtube" \
  -F "platform[]=tiktok" \
  -F "platform[]=instagram" \
  -F "platform[]=facebook" \
  -F "platform[]=x" \
  -F "platform[]=threads" \
  -F "platform[]=linkedin" \
  -F "target_linkedin_page_id=110574199" \
  -F "title=$YT_TITLE" \
  -F "youtube_title=$YT_TITLE" \
  -F "youtube_description=$YT_DESC" \
  -F "categoryId=28" \
  -F "containsSyntheticMedia=true" \
  -F "tiktok_title=$TIKTOK_CAPTION" \
  -F "is_aigc=true" \
  -F "instagram_title=$IG_CAPTION" \
  -F "threads_title=$IG_CAPTION" \
)

# Split response body and HTTP status code
HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -1)
RESPONSE_BODY=$(echo "$UPLOAD_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  log "Upload successful (HTTP $HTTP_CODE)"
  log "Response: $RESPONSE_BODY"
  # Save upload response for the video article pipeline
  echo "$RESPONSE_BODY" > "$OUTPUT_DIR/upload-result.json"
  log "Saved upload result to $OUTPUT_DIR/upload-result.json"
else
  log "ERROR: Upload failed (HTTP $HTTP_CODE)"
  log "Response: $RESPONSE_BODY"
  send_failure_alert "Upload failed (HTTP $HTTP_CODE): $RESPONSE_BODY"
  exit 1
fi

# ---------------------------------------------------------------------------
# Step 5: Wait for Upload-Post processing, then publish Dev.to article
# ---------------------------------------------------------------------------
log "Step 5: Waiting for Upload-Post to finish processing..."

REQUEST_ID=$(node -e "process.stdout.write(JSON.parse(require('fs').readFileSync('$OUTPUT_DIR/upload-result.json','utf8')).request_id || '')")

if [ -z "$REQUEST_ID" ]; then
  log "ERROR: No request_id found in upload-result.json"
  send_failure_alert "No request_id in upload-result.json, skipping Dev.to article"
else
  MAX_POLLS=30
  POLL_INTERVAL=60
  POLL_COUNT=0
  UPLOAD_STATUS="pending"

  while [ "$UPLOAD_STATUS" != "completed" ] && [ "$POLL_COUNT" -lt "$MAX_POLLS" ]; do
    POLL_COUNT=$((POLL_COUNT + 1))
    log "  Polling Upload-Post status ($POLL_COUNT/$MAX_POLLS)..."

    STATUS_BODY=$(curl -s "https://api.upload-post.com/api/uploadposts/status?request_id=$REQUEST_ID" \
      -H "Authorization: Apikey $UPLOAD_POST_API_KEY") || true

    UPLOAD_STATUS=$(echo "$STATUS_BODY" | node -e "
      try { process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).status || 'unknown'); }
      catch(e) { process.stdout.write('error'); }
    " 2>/dev/null) || UPLOAD_STATUS="error"

    if [ "$UPLOAD_STATUS" = "completed" ]; then
      log "  Upload-Post processing complete"
      # Log per-platform results for debugging
      echo "$STATUS_BODY" | node -e "
        const data = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
        for (const r of data.results || []) {
          const status = r.success ? 'OK' : 'FAILED';
          console.log('  ' + status + ': ' + (r.platform || 'unknown') + (r.url ? ' -> ' + r.url : '') + (r.error ? ' (' + r.error + ')' : ''));
        }
      " 2>/dev/null || true
      break
    elif [ "$UPLOAD_STATUS" = "failed" ]; then
      log "ERROR: Upload-Post processing failed"
      send_failure_alert "Upload-Post processing failed, skipping Dev.to article"
      break
    fi

    log "  Status: $UPLOAD_STATUS - waiting ${POLL_INTERVAL}s..."
    sleep "$POLL_INTERVAL"
  done

  if [ "$UPLOAD_STATUS" = "completed" ]; then
    log "Publishing Dev.to article..."
    ARTICLE_OUTPUT=$(cd "$SCRIPT_DIR" && node publish-video-article.js --day "$DAY_NUMBER" 2>&1) || {
      log "ERROR: Dev.to article publishing failed"
      echo "$ARTICLE_OUTPUT"
      send_failure_alert "Dev.to article publishing failed for Day $DAY_NUMBER"
    }
    echo "$ARTICLE_OUTPUT"
  elif [ "$UPLOAD_STATUS" != "failed" ]; then
    log "ERROR: Upload-Post timed out after $((MAX_POLLS * POLL_INTERVAL))s (status: $UPLOAD_STATUS)"
    send_failure_alert "Upload-Post timed out, skipping Dev.to article for Day $DAY_NUMBER"
  fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log "=== Pipeline complete for Day $DAY_NUMBER ==="
log "Output: $OUTPUT_DIR"
