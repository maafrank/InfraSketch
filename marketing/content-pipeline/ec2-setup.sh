#!/bin/bash
# EC2 Instance Setup for InfraSketch Content Pipeline
#
# Run this on a fresh Amazon Linux 2023 (ARM/t4g) or Ubuntu 22.04 instance.
# Sets up: Node.js, Chromium, ffmpeg, and the daily cron job.
#
# Usage:
#   ssh ec2-user@<ip> 'bash -s' < ec2-setup.sh
#   OR
#   scp ec2-setup.sh ec2-user@<ip>:~ && ssh ec2-user@<ip> './ec2-setup.sh'

set -euo pipefail

echo "=== InfraSketch Content Pipeline - EC2 Setup ==="

# Detect OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$ID
else
  OS="unknown"
fi

echo "Detected OS: $OS"

# ---------------------------------------------------------------------------
# Install system dependencies
# ---------------------------------------------------------------------------
if [ "$OS" = "amzn" ]; then
  echo "Installing dependencies (Amazon Linux)..."
  sudo dnf update -y
  sudo dnf install -y \
    nodejs npm \
    chromium \
    ffmpeg \
    git \
    curl

elif [ "$OS" = "ubuntu" ]; then
  echo "Installing dependencies (Ubuntu)..."
  sudo apt-get update
  sudo apt-get install -y \
    nodejs npm \
    chromium-browser \
    ffmpeg \
    git \
    curl

  # Ubuntu may have older Node.js, install v20 via nodesource if needed
  NODE_VER=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
  if [ "${NODE_VER:-0}" -lt 18 ]; then
    echo "Upgrading Node.js to v20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
else
  echo "Unsupported OS: $OS. Install Node.js 18+, Chromium, and ffmpeg manually."
  exit 1
fi

# Verify installations
echo ""
echo "Versions:"
echo "  Node.js: $(node -v)"
echo "  npm: $(npm -v)"
echo "  Chromium: $(chromium --version 2>/dev/null || chromium-browser --version 2>/dev/null || echo 'not found')"
echo "  ffmpeg: $(ffmpeg -version 2>/dev/null | head -1)"

# ---------------------------------------------------------------------------
# Set up pipeline directory
# ---------------------------------------------------------------------------
PIPELINE_DIR="$HOME/content-pipeline"

if [ -d "$PIPELINE_DIR" ]; then
  echo ""
  echo "Pipeline directory already exists at $PIPELINE_DIR"
  echo "Pulling latest changes..."
  cd "$PIPELINE_DIR" && git pull || true
else
  echo ""
  echo "NOTE: You need to copy the content-pipeline/ directory to $PIPELINE_DIR"
  echo "Options:"
  echo "  1. ./deploy-pipeline.sh ec2-user@<ip>"
  echo "  2. Clone your repo and symlink"
  mkdir -p "$PIPELINE_DIR"
fi

# ---------------------------------------------------------------------------
# Install npm dependencies
# ---------------------------------------------------------------------------
if [ -f "$PIPELINE_DIR/package.json" ]; then
  echo ""
  echo "Installing npm dependencies..."
  cd "$PIPELINE_DIR" && npm ci --production 2>/dev/null || npm install --production
fi

# ---------------------------------------------------------------------------
# Set Puppeteer to use system Chromium (not download its own)
# ---------------------------------------------------------------------------
echo ""
echo "Configuring Puppeteer to use system Chromium..."

# Find system chromium path
CHROMIUM_PATH=$(which chromium 2>/dev/null || which chromium-browser 2>/dev/null || echo "")
if [ -z "$CHROMIUM_PATH" ]; then
  echo "WARNING: Could not find system Chromium. Puppeteer may download its own."
else
  echo "System Chromium at: $CHROMIUM_PATH"
  # Set env var so Puppeteer uses system Chrome
  export PUPPETEER_EXECUTABLE_PATH="$CHROMIUM_PATH"
fi

# ---------------------------------------------------------------------------
# Create .env reminder
# ---------------------------------------------------------------------------
if [ ! -f "$PIPELINE_DIR/.env" ]; then
  echo ""
  echo "IMPORTANT: Create $PIPELINE_DIR/.env with these required variables:"
  echo "  INFRASKETCH_URL=https://infrasketch.net"
  echo "  CLERK_SECRET_KEY=sk_live_..."
  echo "  CLERK_USER_ID=user_..."
  echo "  UPLOAD_POST_API_KEY=..."
  echo "  UPLOAD_POST_PROFILE=InfraSketch"
  echo "  ANTHROPIC_API_KEY=sk-ant-...  (for Dev.to article generation)"
  echo "  DEVTO_API_KEY=...  (for Dev.to publishing)"
  echo "  OPENAI_API_KEY=sk-proj-...  (only if regenerating voiceovers)"
fi

# ---------------------------------------------------------------------------
# Set up cron job (daily at 6:00 AM PST = 13:00 UTC during PDT)
# ---------------------------------------------------------------------------
echo ""
echo "Setting up daily cron job (6:00 AM PST / 13:00 UTC)..."

CRON_LINE="0 13 * * * cd $PIPELINE_DIR && PUPPETEER_EXECUTABLE_PATH=${CHROMIUM_PATH:-/usr/bin/chromium} ./run-daily-pipeline.sh >> $PIPELINE_DIR/logs/pipeline-\$(date +\%Y-\%m-\%d).log 2>&1"

# Add cron job if not already present
(crontab -l 2>/dev/null | grep -v "run-daily-pipeline" ; echo "$CRON_LINE") | crontab -
echo "Cron job installed:"
crontab -l | grep "run-daily-pipeline"

# ---------------------------------------------------------------------------
# Create log rotation
# ---------------------------------------------------------------------------
echo ""
echo "Setting up log rotation..."
cat <<'LOGROTATE' | sudo tee /etc/logrotate.d/content-pipeline > /dev/null
/home/*/content-pipeline/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGROTATE

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Deploy files: ./deploy-pipeline.sh ec2-user@<ip> (if not already done)"
echo "  2. Create/verify $PIPELINE_DIR/.env"
echo "  3. Test: cd $PIPELINE_DIR && ./run-daily-pipeline.sh --day 1 --dry-run"
echo "  4. Full test: ./run-daily-pipeline.sh --day 1"
echo "  5. The cron job will run daily at 6:00 AM PST"
echo ""
echo "Logs: $PIPELINE_DIR/logs/"
echo "Manual run: cd $PIPELINE_DIR && ./run-daily-pipeline.sh"
