#!/usr/bin/env python3
"""
Batch process WeChat chat screenshots: auto-detect and mosaic sensitive regions.

Detects and masks:
1. Left-side avatars (other person's)
2. Navigation bar nickname
3. Person names and company names in left-side chat text (via OCR + NER)

Does NOT mask:
- Right-side (user's own) messages and avatar
- Numbers, amounts, salary figures

Usage:
    python3 process.py [image_dir] [--output-dir OUTPUT]

Defaults: image_dir = current directory, output = ./output/
"""

import sys
import os
import json
import glob
import time
import re

from PIL import Image

# Import detection functions from detect.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from detect import find_title_region, find_left_avatars
from mosaic import apply_mosaic


COMPANY_SUFFIXES = (
    "餐饮管理有限公司",
    "管理有限公司",
    "有限责任公司",
    "有限公司",
    "工作室",
    "商贸",
    "科技",
    "餐饮",
)

COMPANY_FULL_RE = re.compile(
    rf"[（(]?([A-Za-z0-9\u4e00-\u9fff·]{{2,40}}?(?:{'|'.join(map(re.escape, COMPANY_SUFFIXES))}))[）)]?"
)

CONTEXTUAL_COMPANY_PATTERNS = (
    re.compile(r"(?:过了|通过了|入职了|入职|进了|去了|拿到|收到了|发了)(?P<name>[A-Za-z\u4e00-\u9fff]{2,8})"),
    re.compile(r"(?P<name>[A-Za-z\u4e00-\u9fff]{2,6})(?:无责底薪|有责底薪|底薪)"),
)
PARENTHETICAL_COMPANY_RE = re.compile(r"我司[（(](?P<name>[A-Za-z0-9\u4e00-\u9fff·]{2,30})")

EXEMPT_ENTITY_SUFFIXES = ("老师",)
ALIAS_NOISE_PREFIXES = ("这个是昨晚", "这个是", "是昨晚", "昨晚", "今天", "刚刚", "刚")
GENERIC_ENTITY_FRAGMENTS = ("岗位", "薪资", "工资", "底薪", "无责", "offer", "入职")


def init_ocr():
    """Initialize CnOcr (lazy, so models load once)."""
    from cnocr import CnOcr
    return CnOcr()


def init_ner():
    """Initialize jieba POS tagger for NER."""
    import jieba.posseg as pseg
    # Warm up
    list(pseg.cut("测试"))
    return pseg


def ocr_image(ocr, img_path):
    """Run OCR on an image, return list of {text, x1, y1, x2, y2}."""
    results = ocr.ocr(img_path)
    texts = []
    for r in results:
        text = r["text"].strip()
        if not text:
            continue
        pos = r["position"]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        x1 = int(pos[0][0])
        y1 = int(pos[0][1])
        x2 = int(pos[2][0])
        y2 = int(pos[2][1])
        texts.append({
            "text": text,
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
            "score": float(r["score"]),
        })
    return texts


def find_sensitive_entities(pseg, text):
    """Use jieba POS tagging to find person names (nr) and org names (nt, nz).
    Returns list of (entity_text, start_char_index, end_char_index, tag)."""
    # Common words jieba misclassifies as names/orgs
    SKIP_WORDS = {
        # Generic titles/honorifics
        "老师", "师傅", "老板", "老大", "同学", "朋友", "同事", "领导",
        "大哥", "大姐", "小姐", "先生", "美女", "帅哥", "宝贝", "亲爱的",
        # Common nouns jieba misclassifies
        "沙龙", "晋升", "哈哈", "啊啊啊", "嘻嘻", "呵呵",
        "offer", "OK", "ok",
    }

    words = list(pseg.cut(text))
    entities = []
    pos = 0
    for w in words:
        word_len = len(w.word)
        # nr = person name, nt = org/institution
        # Skip nz (other proper noun) — too many false positives
        if w.flag in ("nr", "nt"):
            # Skip single-char entities (almost always false positives)
            if word_len < 2:
                pos += word_len
                continue
            # Skip known non-name words
            if w.word in SKIP_WORDS:
                pos += word_len
                continue
            # Skip if text is all repeated chars (e.g. "啊啊啊", "哈哈哈")
            if len(set(w.word)) == 1:
                pos += word_len
                continue
            if looks_like_generic_context_phrase(w.word):
                pos += word_len
                continue
            if is_exempt_entity(w.word):
                pos += word_len
                continue
            entities.append((w.word, pos, pos + word_len, w.flag))
        pos += word_len

    entities.extend(find_rule_based_entities(text))
    return dedupe_entities(entities)


def find_rule_based_entities(text):
    """Find company-like entities that jieba often misses in hiring chat screenshots."""
    entities = []

    for match in COMPANY_FULL_RE.finditer(text):
        word = match.group(1)
        if len(word) >= 2 and not is_exempt_entity(word):
            entities.append((word, match.start(1), match.end(1), "nt"))

    for match in PARENTHETICAL_COMPANY_RE.finditer(text):
        word = match.group("name").strip("：:，,。.!！？?）)")
        if len(word) >= 2 and not is_exempt_entity(word):
            entities.append((word, match.start("name"), match.start("name") + len(word), "nt"))

    for pattern in CONTEXTUAL_COMPANY_PATTERNS:
        for match in pattern.finditer(text):
            raw_word = match.group("name").strip("：:，,。.!！？?）)")
            word = strip_alias_noise(raw_word)
            if len(word) < 2 or "的" in word or is_exempt_entity(word):
                continue
            start = match.start("name") + (len(raw_word) - len(word))
            end = start + len(word)
            entities.append((word, start, end, "nt"))

    return entities


def is_exempt_entity(word):
    return any(word.endswith(suffix) for suffix in EXEMPT_ENTITY_SUFFIXES)


def strip_alias_noise(word):
    cleaned = word
    changed = True
    while changed:
        changed = False
        for prefix in ALIAS_NOISE_PREFIXES:
            if cleaned.startswith(prefix) and len(cleaned) - len(prefix) >= 2:
                cleaned = cleaned[len(prefix):]
                changed = True
    return cleaned


def looks_like_generic_context_phrase(word):
    return any(fragment in word for fragment in GENERIC_ENTITY_FRAGMENTS)


def dedupe_entities(entities):
    seen = set()
    deduped = []
    for entity in sorted(entities, key=lambda item: (item[1], item[2], item[0], item[3])):
        key = (entity[0], entity[1], entity[2])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped


def is_amount_or_number(text):
    """Check if text is primarily a number/amount (should NOT be masked)."""
    # Remove common number-related chars and check if mostly digits
    cleaned = re.sub(r'[,，.。元万千百十块钱k￥¥$%号月日年时分秒:：\-/]', '', text)
    if not cleaned:
        return True
    digit_ratio = sum(1 for c in cleaned if c.isdigit()) / len(cleaned)
    return digit_ratio > 0.5


def entity_to_region(ocr_item, entity_text, char_start, char_end):
    """Map a character-level entity back to pixel coordinates within an OCR bounding box."""
    text = ocr_item["text"]
    text_len = len(text)
    if text_len == 0:
        return None

    x1, y1 = ocr_item["x1"], ocr_item["y1"]
    x2, y2 = ocr_item["x2"], ocr_item["y2"]
    text_width = x2 - x1
    text_height = y2 - y1

    # Estimate entity pixel range based on character position ratio
    ratio_start = char_start / text_len
    ratio_end = char_end / text_len

    ex1 = int(x1 + ratio_start * text_width)
    ex2 = int(x1 + ratio_end * text_width)

    padding_x = 4
    padding_y = 4

    return {
        "x": max(0, ex1 - padding_x),
        "y": max(0, y1 - padding_y),
        "w": (ex2 - ex1) + padding_x * 2,
        "h": text_height + padding_y * 2,
        "block_size": 15,
        "label": f"text:{entity_text}"
    }


def find_text_regions(ocr, pseg, img_path, img_width, content_start):
    """OCR the image, run NER, return regions for sensitive text on the LEFT side.

    Returns (regions, ocr_texts) where ocr_texts is a list of
    {"text": str, "side": "left"|"right", "y": int} for all chat-area text.
    """
    ocr_results = ocr_image(ocr, img_path)
    return find_text_regions_from_results(pseg, ocr_results, img_width, content_start)


def find_text_regions_from_results(pseg, ocr_results, img_width, content_start):
    """Run NER on pre-computed OCR results, return regions and text lines."""
    regions = []
    ocr_texts = []

    # Threshold: text whose center-x is in left 55% is considered left-side message
    left_threshold = img_width * 0.55

    for item in ocr_results:
        # Skip low-confidence OCR results
        if item["score"] < 0.3:
            continue

        # Skip text above chat content area (title/status bar handled by detect.py)
        if item["y1"] < content_start:
            continue

        center_x = (item["x1"] + item["x2"]) / 2
        side = "left" if center_x <= left_threshold else "right"

        # Collect all chat text for 文案 generation
        ocr_texts.append({"text": item["text"], "side": side, "y": item["y1"]})

        # Only run NER on left-side (other person's) messages
        if side == "right":
            continue

        text = item["text"]

        # Skip pure numbers/amounts
        if is_amount_or_number(text):
            continue

        # Run NER on this text line
        entities = find_sensitive_entities(pseg, text)
        for entity_text, char_start, char_end, tag in entities:
            # Skip if the entity itself is a number/amount
            if is_amount_or_number(entity_text):
                continue
            region = entity_to_region(item, entity_text, char_start, char_end)
            if region:
                regions.append(region)

    return regions, ocr_texts


def extract_title_text(ocr_results, title_region):
    """Extract conversation name from full-image OCR results that fall within the title region."""
    if not title_region:
        return ""
    ty = title_region["y"]
    tb = ty + title_region["h"]
    # Find OCR lines that overlap vertically with the title region (with tolerance)
    candidates = []
    for item in ocr_results:
        # Check vertical overlap: OCR line must overlap with title region
        if item["y2"] < ty - 10 or item["y1"] > tb + 10:
            continue
        candidates.append(item)
    if not candidates:
        return ""
    # Pick the candidate that looks most like a conversation name:
    # prefer longer text that contains Chinese chars, skip single digits/symbols
    best = ""
    for c in candidates:
        text = c["text"].strip()
        if len(text) > len(best) and any('\u4e00' <= ch <= '\u9fff' for ch in text):
            best = text
    return best


def process_image(img_path, output_path, ocr, pseg):
    """Process a single WeChat screenshot: detect all regions and apply mosaic."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    regions = []

    # 1. Title region (nav bar nickname)
    title = find_title_region(img)
    if title:
        regions.append(title)

    # 2. Content start position
    content_start = (title["y"] + title["h"] + 20) if title else int(h * 0.1)

    # 3. Left-side avatars
    avatars = find_left_avatars(img, content_start)
    regions.extend(avatars)

    # 4. OCR full image, then extract title text and sensitive text regions
    all_ocr_results = ocr_image(ocr, img_path)
    conversation = extract_title_text(all_ocr_results, title)
    text_regions, ocr_texts = find_text_regions_from_results(
        pseg, all_ocr_results, w, content_start
    )
    regions.extend(text_regions)

    # Apply mosaic to all regions
    for region in regions:
        img = apply_mosaic(
            img,
            region["x"], region["y"],
            region["w"], region["h"],
            region.get("block_size", 10)
        )

    # Save output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, quality=95)

    return regions, ocr_texts, conversation


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch mosaic WeChat chat screenshots")
    parser.add_argument("image_dir", nargs="?", default=".",
                        help="Directory containing screenshots (default: current dir)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory (default: <image_dir>/output/)")
    args = parser.parse_args()

    image_dir = os.path.abspath(args.image_dir)
    output_dir = args.output_dir or os.path.join(image_dir, "output")

    # Find all images
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    image_files = []
    for pat in patterns:
        image_files.extend(glob.glob(os.path.join(image_dir, pat)))
    image_files = sorted(set(image_files))

    if not image_files:
        print(f"No images found in {image_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(image_files)} images in {image_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Initialize OCR and NER (once)
    print("Loading OCR model...", end=" ", flush=True)
    ocr = init_ocr()
    print("done")

    print("Loading NER model...", end=" ", flush=True)
    pseg = init_ner()
    print("done")

    print()

    # Process each image
    results = []
    total_start = time.time()

    for i, img_path in enumerate(image_files, 1):
        filename = os.path.basename(img_path)
        output_path = os.path.join(output_dir, filename)

        t0 = time.time()
        regions, ocr_texts, conversation = process_image(img_path, output_path, ocr, pseg)
        elapsed = time.time() - t0

        # Summarize
        avatar_count = sum(1 for r in regions if r.get("label") == "left_avatar")
        title_count = sum(1 for r in regions if r.get("label") == "nav_title")
        text_labels = [r["label"] for r in regions if r.get("label", "").startswith("text:")]

        print(f"[{i}/{len(image_files)}] {filename}")
        if conversation:
            print(f"  Conversation: {conversation}")
        print(f"  Avatars: {avatar_count}, Title: {'yes' if title_count else 'no'}, "
              f"Text entities: {len(text_labels)}")
        if text_labels:
            names = [l.replace("text:", "") for l in text_labels]
            print(f"  Masked text: {', '.join(names)}")
        print(f"  Time: {elapsed:.2f}s → {output_path}")
        print()

        results.append({
            "file": filename,
            "conversation": conversation,
            "regions": len(regions),
            "avatars": avatar_count,
            "title": title_count > 0,
            "text_entities": text_labels,
            "ocr_text": ocr_texts,
            "time": round(elapsed, 2),
        })

    total_elapsed = time.time() - total_start

    # Summary
    print("=" * 60)
    print(f"Processed {len(results)} images in {total_elapsed:.1f}s "
          f"({total_elapsed/len(results):.1f}s/image avg)")
    print(f"Output: {output_dir}/")

    # Output JSON summary for programmatic use
    summary = {
        "total": len(results),
        "output_dir": output_dir,
        "elapsed": round(total_elapsed, 1),
        "images": results,
    }
    summary_path = os.path.join(output_dir, "_summary.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
