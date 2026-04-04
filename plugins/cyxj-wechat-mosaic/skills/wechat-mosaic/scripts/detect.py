#!/usr/bin/env python3
"""
Auto-detect mosaic regions in WeChat chat screenshots.

Detects:
1. Left-side avatars (other person's avatars)
2. Navigation bar title/nickname

Outputs JSON array of regions to stdout.

Usage:
    python detect.py <image_path>
"""

import sys
import json
from PIL import Image


def find_title_region(img):
    """Find the navigation bar title region to mask.

    Scans the top portion of the image for text groups. The title is
    the last text group before the chat content begins. This handles
    both dark and light status bar styles.
    """
    w, h = img.size
    scan_top = int(h * 0.12)  # scan top 12% of image

    search_left = int(w * 0.10)
    search_right = int(w * 0.80)

    # Find all rows with dark text in the top portion
    text_rows = []
    for y in range(0, scan_top):
        dark_count = 0
        for x in range(search_left, search_right):
            r, g, b = img.getpixel((x, y))[:3]
            if r < 180 and g < 180 and b < 180:
                dark_count += 1
        if dark_count >= 3:
            text_rows.append(y)

    if not text_rows:
        return None

    # Group contiguous text rows (gap > 5px = new group)
    groups = []
    current_group = [text_rows[0]]
    for i in range(1, len(text_rows)):
        if text_rows[i] - text_rows[i - 1] > 5:
            groups.append(current_group)
            current_group = [text_rows[i]]
        else:
            current_group.append(text_rows[i])
    groups.append(current_group)

    # Filter out groups near the bottom of the scan area — those are likely
    # chat content bleeding into the scan zone, not the title.
    cutoff = int(scan_top * 0.85)
    candidate_groups = [g for g in groups if g[0] < cutoff]
    if not candidate_groups:
        candidate_groups = groups

    # The title is the LAST candidate group (below status bar text)
    title_group = candidate_groups[-1]
    title_top = title_group[0]
    title_bottom = title_group[-1]

    padding_x = 5
    padding_y = 5
    return {
        "x": max(0, search_left - padding_x),
        "y": max(0, title_top - padding_y),
        "w": (search_right - search_left) + padding_x * 2,
        "h": (title_bottom - title_top) + padding_y * 2,
        "block_size": 12,
        "label": "nav_title"
    }


def _is_background(r, g, b):
    """Check if a pixel is a WeChat background color (light gray or white)."""
    # WeChat uses rgb(237,237,237) for chat bg and rgb(255,255,255) for message bubbles
    return r > 220 and g > 220 and b > 220 and abs(r - g) < 10 and abs(g - b) < 10


def find_left_avatars(img, content_start):
    """Find left-side avatar regions by scanning for non-background pixels."""
    w, h = img.size

    # Scan multiple x positions to handle different screenshot widths
    # WeChat avatars sit in the left ~12% of the image
    scan_positions = [20, 30, 40, 50]
    all_regions = []

    for scan_x in scan_positions:
        if scan_x >= w:
            continue
        in_region = False
        region_start = 0

        for y in range(content_start, h - 10):
            r, g, b = img.getpixel((scan_x, y))[:3]
            is_bg = _is_background(r, g, b)

            if not is_bg and not in_region:
                in_region = True
                region_start = y
            elif is_bg and in_region:
                in_region = False
                region_height = y - region_start
                if 15 < region_height < 120:
                    all_regions.append((region_start, y))

    # Deduplicate overlapping regions (merge if they overlap vertically)
    all_regions.sort()
    merged = []
    for start, end in all_regions:
        if merged and start <= merged[-1][1] + 5:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Find X boundaries of avatars
    results = []
    for start_y, end_y in merged:
        mid_y = (start_y + end_y) // 2

        # Find rightmost non-bg pixel in this row within left portion
        x_end = 0
        for x in range(min(130, w // 4), -1, -1):
            r, g, b = img.getpixel((x, mid_y))[:3]
            if not _is_background(r, g, b):
                x_end = x
                break

        if x_end > 0:
            padding = 3
            results.append({
                "x": 0,
                "y": max(0, start_y - padding),
                "w": x_end + padding + 1,
                "h": (end_y - start_y) + padding * 2,
                "block_size": 20,
                "label": "left_avatar"
            })

    return results


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <image_path>", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    regions = []

    # Step 1: Find title region in nav bar
    title = find_title_region(img)
    if title:
        regions.append(title)

    # Step 2: Determine where chat content starts (below title)
    content_start = (title["y"] + title["h"] + 20) if title else int(h * 0.1)

    # Step 3: Find left-side avatars
    avatars = find_left_avatars(img, content_start)
    regions.extend(avatars)

    # Output
    output = {
        "image": image_path,
        "size": {"w": w, "h": h},
        "regions": regions,
        "auto_detected": True
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
