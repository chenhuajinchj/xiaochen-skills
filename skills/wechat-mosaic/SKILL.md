---
name: wechat-mosaic
description: "Batch mosaic/blur sensitive regions in WeChat chat screenshots, then auto-generate 朋友圈 promotional posts. Use this skill when the user wants to censor, mask, blur, or mosaic WeChat chat screenshots, or when they mention '打码', '马赛克', '模糊处理', '朋友圈文案', '隐私保护', '截图处理', '发朋友圈' for chat screenshots. Also trigger when the user has a folder of WeChat screenshots and wants to redact personal information like avatars, nicknames, names, or company names before sharing."
version: 1.0.0
---

# WeChat Chat Screenshot Batch Mosaic

Fully automated batch processing of WeChat chat screenshots. Masks left-side avatars, navigation bar nicknames, and person/company names in chat text via OCR + NER. Then generates a ready-to-post 朋友圈 promotional text.

## Workflow

### Step 1: Determine image directory

Use the current working directory, or the directory the user specifies. Confirm the path with:

```bash
ls *.png *.jpg *.jpeg 2>/dev/null | head -20
```

If no images are found, ask the user where the screenshots are.

### Step 2: Check and install dependencies

```bash
python3 -c "from PIL import Image; from cnocr import CnOcr; import jieba; print('All dependencies OK')" 2>/dev/null || {
  echo "Installing dependencies..."
  pip3 install Pillow cnocr onnxruntime jieba
}
```

### Step 3: Run the batch processor

Run the fully automated processing script. It handles everything: avatar detection, title detection, OCR, NER, and mosaic application.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/process.py "<image_directory>" --output-dir "<image_directory>/output"
```

The script:
- Scans for all PNG/JPG images in the directory
- For each image, auto-detects:
  - Left-side avatars (other person's) → mosaic
  - Navigation bar nickname → mosaic
  - Person names and company names in left-side chat text (via cnocr OCR + jieba NER) → mosaic
- Skips right-side (user's own) messages entirely
- Skips numbers, amounts, and salary figures
- Outputs processed images to the output directory
- Generates `_summary.json` with processing details, OCR text, and conversation grouping

Typical speed: ~0.3 seconds per image.

If the script fails, check that all dependencies are installed (Step 2) and that the image directory contains valid PNG/JPG files. Corrupt or non-image files will be skipped with a warning.

### Step 4: Report results and read summary

Read the summary JSON:

```bash
cat "<image_directory>/output/_summary.json"
```

Tell the user:
- How many images were processed
- What was masked in each (avatars, title, text entities)
- Output file locations
- Any images that may need manual review (e.g., unusual layouts)

### Step 5 (optional): Manual review

If the user wants to verify results, read one or two output images with the Read tool to spot-check. If any regions were missed or incorrectly masked, the user can re-run with adjustments.

### Step 6: Generate 朋友圈文案

Using the summary JSON already read in Step 4, automatically generate a WeChat Moments promotional post based on the chat content extracted by OCR.

Each image in the summary has:
- `conversation`: title bar text identifying which student this chat belongs to (e.g., "07-12西瓜"). Use this to **group images by student** — multiple screenshots from the same conversation should be merged into ONE bullet point.
- `ocr_text`: list of `{"text", "side", "y"}` entries. `side` is `"left"` (student) or `"right"` (teacher).

**Compose a post with 4 modules:**

1. **开头金句/hook** — Attention-grabbing opening. Reference the most impressive data point (highest salary, fastest placement, number of offers). Tone: casual, confident, slightly playful. Example: "又是offer收到手软的一天～"

2. **学员案例列表** — Bullet points prefixed with `▫️`. **One bullet per student** (NOT per screenshot). Group all screenshots with the same `conversation` value, consolidate their info into one bullet. Include: salary figure, job outcome, speed, company type/scale (NOT company name). Keep each bullet ≤ 40 chars. Example: `▫️0基础手握3个offer，底薪9k-12k`

3. **课程推广信息** — 1-2 sentences about 且曼IP助理 course. Mention the graduation-to-employment pipeline.

4. **hashtag/结尾** — Close with `#IP助理` `#且曼IP助理` and any relevant topic hashtags.

**Extraction rules:**
- Extract salary numbers from OCR text (patterns: `Nk`, `N万`, `底薪N`, `薪资N`, plain numbers near salary context)
- Extract job outcomes: 面试通过, 入职, 拿到offer, 约满, 过了
- Extract time context: N天, 单周, 一周内
- Extract company descriptors by type/scale (粉丝量级, 头部博主, 轻奢品牌 etc.) but **NEVER** use actual company names — they are masked for privacy
- **NEVER** include student real names
- If OCR data is sparse, generate fewer bullets rather than fabricating details
- Right-side text (teacher's messages) provides context but should not be quoted verbatim

Output the 文案 as a ready-to-copy text block.

## Key Rules

- LEFT side = other person's messages and avatar → mask these
- RIGHT side = user's own messages → do NOT mask
- Navigation bar shows contact/group name → always mask
- Numbers, amounts, salary → do NOT mask
- If an image is not a WeChat chat, skip it

## Known Limitations

- **Non-standard nicknames**: Nicknames like "鳄鱼", "西瓜" that are common nouns won't be detected as person names by jieba. Standard Chinese names (张三, 赵诚和) are reliably detected. The navigation bar mosaic covers these nicknames regardless.
- **Mixed layouts**: Screenshots from different phones may have slightly different avatar positions, but the multi-position scanning handles most variations.
