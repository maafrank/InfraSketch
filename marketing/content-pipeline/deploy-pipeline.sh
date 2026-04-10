#!/bin/bash
# Deploy the content pipeline to EC2
#
# Usage:
#   ./deploy-pipeline.sh <ec2-host>
#   ./deploy-pipeline.sh ec2-user@54.123.45.67
#   ./deploy-pipeline.sh ubuntu@my-instance.compute.amazonaws.com
#
# First-time setup:
#   ./deploy-pipeline.sh <ec2-host> --setup

set -euo pipefail

EC2_HOST="${1:?Usage: ./deploy-pipeline.sh <ec2-host> [--setup]}"
SETUP="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="content-pipeline"

echo "=== Deploying Content Pipeline to $EC2_HOST ==="

# Files to deploy
FILES=(
  generate-content.js
  stitch-video.sh
  run-daily-pipeline.sh
  ec2-setup.sh
  content-calendar.csv
  package.json
  package-lock.json
  .env
)

# Create remote directory
ssh "$EC2_HOST" "mkdir -p ~/$REMOTE_DIR/voiceovers ~/$REMOTE_DIR/output ~/$REMOTE_DIR/logs"

# Copy pipeline files
echo "Copying pipeline files..."
for f in "${FILES[@]}"; do
  if [ -f "$SCRIPT_DIR/$f" ]; then
    scp "$SCRIPT_DIR/$f" "$EC2_HOST:~/$REMOTE_DIR/$f"
    echo "  $f"
  else
    echo "  SKIP: $f (not found)"
  fi
done

# Copy logo for branding slide
LOGO_SRC="$SCRIPT_DIR/../../assets/logos/InfraSketchLogoTransparent_03_256.png"
if [ -f "$LOGO_SRC" ]; then
  scp "$LOGO_SRC" "$EC2_HOST:~/$REMOTE_DIR/InfraSketchLogoTransparent_03_256.png"
  echo "  Logo copied"
fi

# Copy voiceovers
echo "Copying voiceover files..."
scp "$SCRIPT_DIR/voiceovers/"*.mp3 "$EC2_HOST:~/$REMOTE_DIR/voiceovers/" 2>/dev/null && \
  echo "  31 voiceover clips" || echo "  No voiceovers found"

# Make scripts executable, lock down .env
ssh "$EC2_HOST" "chmod +x ~/$REMOTE_DIR/*.sh && chmod 600 ~/$REMOTE_DIR/.env"

# Run setup if requested
if [ "$SETUP" = "--setup" ]; then
  echo ""
  echo "Running EC2 setup..."
  ssh "$EC2_HOST" "cd ~/$REMOTE_DIR && bash ec2-setup.sh"
else
  echo ""
  echo "Installing npm dependencies..."
  ssh "$EC2_HOST" "cd ~/$REMOTE_DIR && npm ci --production 2>/dev/null || npm install --production"
fi

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Test with:"
echo "  ssh $EC2_HOST 'cd ~/$REMOTE_DIR && ./run-daily-pipeline.sh --day 1 --dry-run'"
echo ""
echo "First-time? Run with --setup flag:"
echo "  ./deploy-pipeline.sh $EC2_HOST --setup"
