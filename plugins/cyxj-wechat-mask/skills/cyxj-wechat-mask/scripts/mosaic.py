#!/usr/bin/env python3
"""
Apply mosaic (pixelation) to specified rectangular regions in an image.

Usage:
    python mosaic.py <input_path> <output_path> '<regions_json>'

regions_json is a JSON array of objects with keys: x, y, w, h (in pixels)
Example:
    python mosaic.py input.png output.png '[{"x":10,"y":50,"w":45,"h":45}]'

Optional --block-size flag controls mosaic granularity (default: 10).
"""

import sys
import json
import os
from PIL import Image


def apply_mosaic(image: Image.Image, x: int, y: int, w: int, h: int, block_size: int = 10) -> Image.Image:
    """Apply mosaic (pixelation) effect to a rectangular region."""
    img_w, img_h = image.size

    # Clamp region to image bounds
    x = max(0, x)
    y = max(0, y)
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    if w <= 0 or h <= 0:
        return image

    # Crop the region
    region = image.crop((x, y, x + w, y + h))

    # Downscale then upscale to create pixelation
    small_w = max(1, w // block_size)
    small_h = max(1, h // block_size)
    region = region.resize((small_w, small_h), Image.NEAREST)
    region = region.resize((w, h), Image.NEAREST)

    # Paste back
    image.paste(region, (x, y))
    return image


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <input_path> <output_path> '<regions_json>'")
        print(f"Optional: --block-size <int> (default: 10)")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    regions_json = sys.argv[3]

    # Parse optional block size
    block_size = 10
    if "--block-size" in sys.argv:
        idx = sys.argv.index("--block-size")
        if idx + 1 < len(sys.argv):
            block_size = int(sys.argv[idx + 1])

    # Parse regions
    regions = json.loads(regions_json)

    # Load image
    image = Image.open(input_path).convert("RGB")

    # Apply mosaic to each region
    for region in regions:
        x = int(region["x"])
        y = int(region["y"])
        w = int(region["w"])
        h = int(region["h"])
        bs = int(region.get("block_size", block_size))
        image = apply_mosaic(image, x, y, w, h, bs)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Save
    image.save(output_path, quality=95)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
