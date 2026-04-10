#!/bin/bash
# Stitch screenshots into a social-media-ready video
#
# Usage: ./stitch-video.sh ./output/2026-04-03-video-streaming
#
# Creates:
#   - carousel/  (individual slides resized for Instagram 1080x1080)
#   - reel.mp4   (vertical 1080x1920, 3s per slide, for Reels/TikTok/Shorts)
#   - post.mp4   (square 1080x1080, 3s per slide, for feed posts)

set -euo pipefail

INPUT_DIR="${1:?Usage: ./stitch-video.sh <screenshot-dir> [day-number]}"
DAY_NUMBER="${2:-}"
CAROUSEL_DIR="${INPUT_DIR}/carousel"
SECONDS_PER_SLIDE=1.5
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VOICEOVER_DIR="$SCRIPT_DIR/voiceovers"

if ! command -v ffmpeg &>/dev/null; then
  echo "Error: ffmpeg not found. Install with: brew install ffmpeg"
  exit 1
fi

mkdir -p "$CAROUSEL_DIR"

echo "Creating carousel images (1080x1080)..."
for img in "$INPUT_DIR"/0*.png; do
  basename=$(basename "$img")
  ffmpeg -y -i "$img" \
    -vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e" \
    "$CAROUSEL_DIR/$basename" 2>/dev/null
  echo "  $basename"
done

# Resolve voiceover file if day number provided
VOICEOVER_FILE=""
if [ -n "$DAY_NUMBER" ]; then
  DAY_OF_MONTH=$(( ((DAY_NUMBER - 1) % 31) + 1 ))
  PADDED=$(printf "%02d" "$DAY_OF_MONTH")
  VOICEOVER_FILE=$(find "$VOICEOVER_DIR" -name "${PADDED}-*.mp3" | head -1)
  if [ -n "$VOICEOVER_FILE" ]; then
    echo ""
    echo "Using voiceover: $(basename "$VOICEOVER_FILE")"
  else
    echo ""
    echo "  Warning: No voiceover found for day $DAY_OF_MONTH, videos will be silent"
  fi
else
  echo ""
  echo "  No day number provided, videos will be silent"
fi

echo ""
echo "Creating vertical reel (1080x1920, ${SECONDS_PER_SLIDE}s per slide)..."
ffmpeg -y -framerate "1/${SECONDS_PER_SLIDE}" \
  -pattern_type glob -i "${INPUT_DIR}/0*.png" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e" \
  -c:v libx264 -r 30 -pix_fmt yuv420p \
  "${INPUT_DIR}/reel.mp4" 2>/dev/null
echo "  Created: reel.mp4"

echo ""
echo "Creating square post (1080x1080, ${SECONDS_PER_SLIDE}s per slide)..."
ffmpeg -y -framerate "1/${SECONDS_PER_SLIDE}" \
  -pattern_type glob -i "${INPUT_DIR}/0*.png" \
  -vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e" \
  -c:v libx264 -r 30 -pix_fmt yuv420p \
  "${INPUT_DIR}/post.mp4" 2>/dev/null
echo "  Created: post.mp4"

# Add voiceover to both videos
if [ -n "$VOICEOVER_FILE" ]; then
  for video in reel.mp4 post.mp4; do
    echo "  Adding voiceover to $video..."
    mv "${INPUT_DIR}/${video}" "${INPUT_DIR}/${video%.mp4}-silent.mp4"
    # Get video duration to avoid apad infinite hang
    VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "${INPUT_DIR}/${video%.mp4}-silent.mp4" 2>/dev/null | cut -d. -f1)
    VIDEO_DUR=${VIDEO_DUR:-15}
    ffmpeg -y -i "${INPUT_DIR}/${video%.mp4}-silent.mp4" -i "$VOICEOVER_FILE" \
      -filter_complex "[1:a]adelay=500|500,volume=1.0[vo]" \
      -map 0:v -map "[vo]" \
      -c:v copy -c:a aac -t "${VIDEO_DUR}" \
      "${INPUT_DIR}/${video}" 2>/dev/null
    rm "${INPUT_DIR}/${video%.mp4}-silent.mp4"
  done
  echo "  Voiceover added to both videos"
fi

echo ""
echo "Done! Output:"
echo "  Carousel: ${CAROUSEL_DIR}/"
echo "  Reel:     ${INPUT_DIR}/reel.mp4"
echo "  Post:     ${INPUT_DIR}/post.mp4"
