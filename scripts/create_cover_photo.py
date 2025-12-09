#!/usr/bin/env python3
"""
Create LinkedIn cover photo for InfraSketch.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOGO_PATH = os.path.join(PROJECT_ROOT, "assets/logos/InfraSketchLogo_01.png")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "assets/logos/CoverPhoto.png")

# LinkedIn cover photo dimensions (high-res)
WIDTH = 1584
HEIGHT = 396

# Colors
BACKGROUND_COLOR = (10, 10, 10)  # #0a0a0a - matches logo background
TEXT_COLOR = (255, 255, 255)  # White
TAGLINE_COLOR = (180, 180, 180)  # Light gray for tagline

def create_cover_photo():
    # Create dark background
    img = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # Load and resize logo
    logo = Image.open(LOGO_PATH)
    logo_height = int(HEIGHT * 0.75)  # 75% of banner height
    logo_ratio = logo.width / logo.height
    logo_width = int(logo_height * logo_ratio)
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

    # Calculate positions - center everything as a group
    padding = 60

    # Try to load a nice font, fall back to default
    try:
        # Try macOS system fonts
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        tagline_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    except:
        try:
            # Try Arial
            title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 72)
            tagline_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 32)
        except:
            # Fall back to default
            title_font = ImageFont.load_default()
            tagline_font = ImageFont.load_default()

    # Text content
    title_text = "InfraSketch"
    tagline_text = "AI-powered system design"

    # Get text dimensions
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    tagline_bbox = draw.textbbox((0, 0), tagline_text, font=tagline_font)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    tagline_height = tagline_bbox[3] - tagline_bbox[1]

    # Calculate total width of logo + text group
    gap_between = 40  # Gap between logo and text
    text_block_width = max(title_width, tagline_width)
    total_width = logo_width + gap_between + text_block_width

    # Center the entire group
    start_x = (WIDTH - total_width) // 2

    # Position logo
    logo_x = start_x
    logo_y = (HEIGHT - logo_height) // 2

    # Position text (to the right of logo)
    text_x = logo_x + logo_width + gap_between

    # Vertically center the text block (title + tagline)
    text_spacing = 15  # Space between title and tagline
    text_block_height = title_height + text_spacing + tagline_height
    text_start_y = (HEIGHT - text_block_height) // 2

    # Paste logo (handle transparency)
    if logo.mode == 'RGBA':
        img.paste(logo, (logo_x, logo_y), logo)
    else:
        img.paste(logo, (logo_x, logo_y))

    # Draw title
    draw.text((text_x, text_start_y), title_text, font=title_font, fill=TEXT_COLOR)

    # Draw tagline
    tagline_y = text_start_y + title_height + text_spacing
    draw.text((text_x, tagline_y), tagline_text, font=tagline_font, fill=TAGLINE_COLOR)

    # Save
    img.save(OUTPUT_PATH, 'PNG')
    print(f"Cover photo saved to: {OUTPUT_PATH}")
    print(f"Dimensions: {WIDTH}x{HEIGHT}")

if __name__ == "__main__":
    create_cover_photo()
