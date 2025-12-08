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


def find_logo_bounds(img, threshold=240):
    """
    Find the bounding box of the logo (non-white pixels).
    Returns (left, top, right, bottom) of the logo area.
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


def smart_crop_256(img, padding=3):
    """
    Create a 256x256 crop centered on the logo with padding.
    Scales down if logo + padding > 256px.
    """
    left, top, right, bottom = find_logo_bounds(img)

    # Add padding
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)

    logo_width = right - left
    logo_height = bottom - top

    # Calculate the size needed
    max_dim = max(logo_width, logo_height)

    if max_dim > 256:
        # Need to scale down - crop the logo area first, then resize
        cropped = img.crop((left, top, right, bottom))
        # Calculate scale to fit in 256x256
        scale = 256 / max_dim
        new_width = int(logo_width * scale)
        new_height = int(logo_height * scale)
        scaled = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create 256x256 canvas with white background
        result = Image.new("RGB", (256, 256), (255, 255, 255))
        # Center the scaled logo
        paste_x = (256 - new_width) // 2
        paste_y = (256 - new_height) // 2
        result.paste(scaled, (paste_x, paste_y))
        return result
    else:
        # Logo fits in 256x256, just need to center it
        # Calculate center of logo
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        # Calculate crop bounds for 256x256 centered on logo
        crop_left = center_x - 128
        crop_top = center_y - 128
        crop_right = center_x + 128
        crop_bottom = center_y + 128

        # Adjust if out of bounds
        if crop_left < 0:
            crop_right -= crop_left
            crop_left = 0
        if crop_top < 0:
            crop_bottom -= crop_top
            crop_top = 0
        if crop_right > img.width:
            crop_left -= (crop_right - img.width)
            crop_right = img.width
        if crop_bottom > img.height:
            crop_top -= (crop_bottom - img.height)
            crop_bottom = img.height

        # If still out of bounds, create a padded canvas
        if crop_left < 0 or crop_top < 0 or crop_right > img.width or crop_bottom > img.height:
            # Create white canvas and paste centered logo
            result = Image.new("RGB", (256, 256), (255, 255, 255))
            logo_crop = img.crop((left, top, right, bottom))
            paste_x = (256 - logo_width) // 2
            paste_y = (256 - logo_height) // 2
            result.paste(logo_crop, (paste_x, paste_y))
            return result

        return img.crop((crop_left, crop_top, crop_right, crop_bottom))


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


def main():
    print(f"Loading source image: {SOURCE_IMAGE}")
    img = Image.open(SOURCE_IMAGE)
    print(f"Source image size: {img.width}x{img.height}")

    # Find logo bounds for info
    left, top, right, bottom = find_logo_bounds(img)
    print(f"Logo bounds: ({left}, {top}) to ({right}, {bottom})")
    print(f"Logo size: {right - left}x{bottom - top}")

    # 1. Original (full size, white background)
    original = img.convert("RGB")
    original_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_01.png")
    original.save(original_path)
    print(f"Saved: {original_path}")

    # 2. Original 256x256 cropped
    original_256 = smart_crop_256(img)
    original_256_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_01_256.png")
    original_256.save(original_256_path)
    print(f"Saved: {original_256_path}")

    # 3. Inverted (full size, black background)
    inverted = invert_colors(original)
    inverted_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_02.png")
    inverted.save(inverted_path)
    print(f"Saved: {inverted_path}")

    # 4. Inverted 256x256 cropped
    inverted_256 = invert_colors(original_256)
    inverted_256_path = os.path.join(OUTPUT_DIR, "InfraSketchLogo_02_256.png")
    inverted_256.save(inverted_256_path)
    print(f"Saved: {inverted_256_path}")

    # 5. Original transparent (full size)
    original_transparent = remove_background(original)
    original_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_01.png")
    original_transparent.save(original_transparent_path)
    print(f"Saved: {original_transparent_path}")

    # 6. Original 256x256 transparent
    original_256_transparent = remove_background(original_256)
    original_256_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_01_256.png")
    original_256_transparent.save(original_256_transparent_path)
    print(f"Saved: {original_256_transparent_path}")

    # 7. Inverted transparent (full size)
    inverted_transparent = remove_background_inverted(inverted)
    inverted_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_02.png")
    inverted_transparent.save(inverted_transparent_path)
    print(f"Saved: {inverted_transparent_path}")

    # 8. Inverted 256x256 transparent
    inverted_256_transparent = remove_background_inverted(inverted_256)
    inverted_256_transparent_path = os.path.join(OUTPUT_DIR, "InfraSketchLogoTransparent_02_256.png")
    inverted_256_transparent.save(inverted_256_transparent_path)
    print(f"Saved: {inverted_256_transparent_path}")

    print("\nAll 8 logo variants generated successfully!")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
