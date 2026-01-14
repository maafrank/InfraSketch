#!/usr/bin/env python3
"""
Generate all logo variants from source image.
Creates 8 variants: original, 256x256 cropped, inverted, and transparent versions of each.
"""

from PIL import Image
import numpy as np
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE_IMAGE = os.path.join(PROJECT_ROOT, "assets", "image.png")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "assets", "logos")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def find_logo_bounds(img, threshold=230):
    """
    Find the bounding box of the logo (non-white pixels).
    Returns (left, top, right, bottom) of the logo area.

    Note: Uses threshold=230 to avoid detecting textured/off-white backgrounds
    (which can have pixel values around 248-252).
    """
    # Convert to numpy array
    arr = np.array(img.convert("RGB"))

    # Find pixels that are NOT white (any channel below threshold)
    is_logo = np.any(arr < threshold, axis=2)

    # Find bounds
    rows = np.any(is_logo, axis=1)
    cols = np.any(is_logo, axis=0)

    if not rows.any() or not cols.any():
        # No logo found, return full image
        return 0, 0, img.width, img.height

    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    return int(left), int(top), int(right), int(bottom)


def smart_crop_256(img, padding=10):
    """
    Create a 256x256 image with the logo cropped tightly and scaled to fill.
    Crops to a square around the logo, then resizes to 256x256.
    """
    left, top, right, bottom = find_logo_bounds(img)

    # Add padding
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)

    logo_width = right - left
    logo_height = bottom - top

    # Make square by expanding to the larger dimension
    max_dim = max(logo_width, logo_height)

    # Calculate center of logo area
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2

    # Calculate square bounds centered on logo
    half_size = max_dim // 2
    sq_left = center_x - half_size
    sq_top = center_y - half_size
    sq_right = center_x + half_size + (max_dim % 2)  # Handle odd sizes
    sq_bottom = center_y + half_size + (max_dim % 2)

    # Check if square is within image bounds
    if sq_left >= 0 and sq_top >= 0 and sq_right <= img.width and sq_bottom <= img.height:
        # Can crop directly from image
        cropped = img.crop((sq_left, sq_top, sq_right, sq_bottom))
    else:
        # Need to create a canvas and paste the logo area
        # First crop the padded logo area
        logo_crop = img.crop((left, top, right, bottom))

        # Create square canvas with white background
        result = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))

        # Center the logo crop on the canvas
        paste_x = (max_dim - logo_width) // 2
        paste_y = (max_dim - logo_height) // 2
        result.paste(logo_crop, (paste_x, paste_y))
        cropped = result

    # Resize to 256x256
    return cropped.resize((256, 256), Image.Resampling.LANCZOS)


def invert_colors(img):
    """
    Invert all colors in the image (white becomes black, black becomes white).
    """
    arr = np.array(img.convert("RGB"))
    inverted_arr = 255 - arr
    return Image.fromarray(inverted_arr)


def remove_background(img, threshold=230):
    """
    Remove white/near-white background by making it transparent.
    Uses threshold of 230 to catch off-white textured backgrounds with noise.
    """
    # Convert to RGBA
    rgba = img.convert("RGBA")
    arr = np.array(rgba)

    # Find white/near-white pixels (all channels above threshold)
    is_background = np.all(arr[:, :, :3] >= threshold, axis=2)

    # Set alpha to 0 for background pixels
    arr[is_background, 3] = 0

    return Image.fromarray(arr)


def remove_background_inverted(img, threshold=25):
    """
    Remove black/near-black background by making it transparent.
    For inverted images where background is black.
    Uses threshold of 25 (255-230=25) to match the original background detection.
    """
    # Convert to RGBA
    rgba = img.convert("RGBA")
    arr = np.array(rgba)

    # Find black/near-black pixels (all channels below threshold)
    is_background = np.all(arr[:, :, :3] <= threshold, axis=2)

    # Set alpha to 0 for background pixels
    arr[is_background, 3] = 0

    return Image.fromarray(arr)


def colorize_green(img, threshold=230):
    """
    Create a green (#009926) version of the logo.
    Takes original image (dark logo on light background) and makes
    the logo green while keeping background transparent.
    """
    # Convert to RGBA
    rgba = img.convert("RGBA")
    arr = np.array(rgba)

    # Find logo pixels (non-white/non-background)
    is_logo = np.any(arr[:, :, :3] < threshold, axis=2)

    # Find background pixels
    is_background = ~is_logo

    # Set logo pixels to green (#009926 = RGB(0, 153, 38))
    arr[is_logo, 0] = 0    # R
    arr[is_logo, 1] = 153  # G
    arr[is_logo, 2] = 38   # B
    arr[is_logo, 3] = 255  # A (fully opaque)

    # Set background to transparent
    arr[is_background, 3] = 0

    return Image.fromarray(arr)


def colorize_green_with_background(img, threshold=230):
    """
    Create a green (#009926) version of the logo with dark background (#0a0a0a).
    Takes original image (dark logo on light background) and makes
    the logo green on a dark background.
    """
    # Convert to RGB
    rgb = img.convert("RGB")
    arr = np.array(rgb)

    # Find logo pixels (non-white/non-background)
    is_logo = np.any(arr < threshold, axis=2)

    # Find background pixels
    is_background = ~is_logo

    # Set logo pixels to green (#009926 = RGB(0, 153, 38))
    arr[is_logo, 0] = 0    # R
    arr[is_logo, 1] = 153  # G
    arr[is_logo, 2] = 38   # B

    # Set background to dark (#0a0a0a = RGB(10, 10, 10))
    arr[is_background, 0] = 10  # R
    arr[is_background, 1] = 10  # G
    arr[is_background, 2] = 10  # B

    return Image.fromarray(arr)


def main():
    print(f"Loading source image: {SOURCE_IMAGE}")
    img = Image.open(SOURCE_IMAGE)
    print(f"Source image size: {img.width}x{img.height}")

    # Find logo bounds for info
    left, top, right, bottom = find_logo_bounds(img)
    print(f"Logo bounds: ({left}, {top}) to ({right}, {bottom})")
    print(f"Logo size: {right - left}x{bottom - top}")

    # 1. Original (full size, white background) -> _02
    original = img.convert("RGB")
    original_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_02.png")
    original.save(original_path)
    print(f"Saved: {original_path}")

    # 2. Original 256x256 cropped -> _02
    original_256 = smart_crop_256(img)
    original_256_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_02_256.png")
    original_256.save(original_256_path)
    print(f"Saved: {original_256_path}")

    # 3. Inverted (full size, black background) -> _01
    inverted = invert_colors(original)
    inverted_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_01.png")
    inverted.save(inverted_path)
    print(f"Saved: {inverted_path}")

    # 4. Inverted 256x256 cropped -> _01
    inverted_256 = invert_colors(original_256)
    inverted_256_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_01_256.png")
    inverted_256.save(inverted_256_path)
    print(f"Saved: {inverted_256_path}")

    # 5. Original transparent (full size) -> _02
    original_transparent = remove_background(original)
    original_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_02.png")
    original_transparent.save(original_transparent_path)
    print(f"Saved: {original_transparent_path}")

    # 6. Original 256x256 transparent -> _02
    original_256_transparent = remove_background(original_256)
    original_256_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_02_256.png")
    original_256_transparent.save(original_256_transparent_path)
    print(f"Saved: {original_256_transparent_path}")

    # 7. Inverted transparent (full size) -> _01
    inverted_transparent = remove_background_inverted(inverted)
    inverted_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_01.png")
    inverted_transparent.save(inverted_transparent_path)
    print(f"Saved: {inverted_transparent_path}")

    # 8. Inverted 256x256 transparent -> _01
    inverted_256_transparent = remove_background_inverted(inverted_256)
    inverted_256_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_01_256.png")
    inverted_256_transparent.save(inverted_256_transparent_path)
    print(f"Saved: {inverted_256_transparent_path}")

    # 9. Green with dark background (full size) -> _03
    green = colorize_green_with_background(original)
    green_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_03.png")
    green.save(green_path)
    print(f"Saved: {green_path}")

    # 10. Green with dark background 256x256 -> _03
    green_256 = colorize_green_with_background(original_256)
    green_256_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_03_256.png")
    green_256.save(green_256_path)
    print(f"Saved: {green_256_path}")

    # 11. Green transparent (full size) -> _03
    green_transparent = colorize_green(original)
    green_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_03.png")
    green_transparent.save(green_transparent_path)
    print(f"Saved: {green_transparent_path}")

    # 12. Green 256x256 transparent -> _03
    green_256_transparent = colorize_green(original_256)
    green_256_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_03_256.png")
    green_256_transparent.save(green_256_transparent_path)
    print(f"Saved: {green_256_transparent_path}")

    print("\nAll 12 logo variants generated successfully!")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
