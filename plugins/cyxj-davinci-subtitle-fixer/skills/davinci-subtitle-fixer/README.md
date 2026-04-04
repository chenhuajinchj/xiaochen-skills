# DaVinci Subtitle Fixer

[中文版](README_zh.md)

A Claude Code skill for correcting ASR (Automatic Speech Recognition) errors in SRT subtitle files exported from DaVinci Resolve. Uses a **Gemini + Opus hybrid architecture** to achieve high accuracy at minimal cost.

## The Problem

When you export subtitles from DaVinci Resolve's built-in speech-to-text, Chinese transcription is riddled with errors:
- **Homophone substitutions**: Technical terms get replaced by common words with similar pronunciation (e.g., "Claude Code" → "Color Code", "上下文" → "善夏文")
- **Stutter/repetition**: "我说的我说的我说的" should be "我说的"
- **Filler words**: "嗯", "啊", "那个", "就是说" cluttering the text
- **Duplicate entries**: DaVinci sometimes generates overlapping subtitle segments

## Architecture

```
Phase 1: Python structural processing (srt_cleaner.py)
  HTML cleanup → dedup → punctuation → merge short → split long → renumber

Phase 2a: Gemini Flash Lite auto-correction (srt_corrector.py)
  Batch API calls with dictionary + topic context → _gemini_fixed.srt + _changes.json

Phase 2b: Opus review (in Claude Code conversation)
  Review Gemini's change list → fix errors → catch misses → save _fixed.srt

Phase 3: Export plain text for IntelliScript
```

### Why Hybrid?

| Approach | Cost per 400 subtitles | Accuracy |
|----------|----------------------|----------|
| Opus only (v3) | ~$2-4 | High |
| Gemini Flash Lite + Opus review (v4) | ~$0.35-0.55 | High |

Gemini handles 95%+ of corrections at 1/50th the cost. Opus only reviews the diff, not the full text.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- Python 3.10+
- `GEMINI_API_KEY` environment variable set

```bash
pip install google-genai pysrt
```

## Installation

### As a Claude Code Skill (Recommended)

```bash
# Clone to Claude Code skills directory
git clone https://github.com/chenhuajinchj/davinci-subtitle-fixer.git \
  ~/.claude/skills/davinci-subtitle-fixer
```

Then use it in Claude Code:
```
/字幕修正 ~/Desktop/Timeline1.srt --topic "Your video topic"
```

### Standalone Usage

```bash
# Phase 1: Structural cleanup
python3 srt_cleaner.py "input.srt" --stats

# Phase 2a: Gemini auto-correction
python3 srt_corrector.py "input_cleaned.srt" --topic "Video topic"

# Use --premium for harder corrections
python3 srt_corrector.py "input_cleaned.srt" --topic "Video topic" --premium
```

## Files

| File | Purpose |
|------|---------|
| `srt_cleaner.py` | Phase 1: Structural processing (HTML strip, dedup, merge/split, renumber) |
| `srt_corrector.py` | Phase 2a: Gemini API batch correction with dictionary support |
| `dictionary.json` | Known ASR error mappings (correct term → error variants) |
| `SKILL.md` | Claude Code skill definition and workflow |

## Dictionary

The dictionary maps correct terms to known ASR error variants:

```json
{
  "corrections": {
    "Claude Code": ["Color Code", "Closet Code", "Colortico", "clotco"],
    "上下文": ["善夏文", "善效文"],
    "worktree": ["工作数", "工夫"]
  }
}
```

Add new entries via Claude Code:
```
/字幕修正 --add "error_word" "correct_word"
```

The `feedback.gemini_missed` field tracks errors Gemini missed but Opus caught, enabling continuous improvement.

## Gemini Models

| Model | Use Case | Input/Output Price |
|-------|----------|-------------------|
| `gemini-3.1-flash-lite-preview` | Default, cheapest | $0.25 / $1.50 per M tokens |
| `gemini-3-flash-preview` | Premium, smarter | $0.50 / $3.00 per M tokens |

> Note: Image generation models (`gemini-3.1-flash-image-preview`, `gemini-3-pro-image-preview`) are NOT suitable for text correction.

## Display Rules

Optimized for 16:9 landscape video subtitles:
- Soft limit: 18 display characters (Chinese = 1, ASCII = 0.5)
- Hard limit: 25 characters (auto-split with review flag)
- Punctuation: commas/periods → spaces, keep ？！

## License

MIT
