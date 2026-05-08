#!/usr/bin/env python3
"""中文区视频召回 — 选题前查参考用，独立于英文主流程。

用法：python3 chinese_reference.py > /tmp/yt_zh_reference.json
关闭：export CYXJ_ENABLE_ZH_REFERENCE=0
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

from paths import load_youtube_api_key

# ── 常量 ──────────────────────────────────────────────

KEYWORDS_ZH = [
    "Claude Code",          # 中文 up 主常直接用英文词
    "Claude 编程",
    "Claude 写代码",
    "AI 编程",
    "AI 编程助手",
    "AI 写代码",
    "Cursor vs Claude",     # 对比类
    "Claude Code 教程",     # 中文标题高频词
    "Claude Code 实战",
]

HOURS_WINDOW = max(1, min(168, int(os.environ.get("CYXJ_LOOKBACK_HOURS", "48"))))
MAX_RESULTS_PER_KEYWORD = 25  # 召回阶段，附录用不需要拉满 50
MAX_ZH_REFERENCE = 15         # 输出阶段截断
API_BASE = "https://www.googleapis.com/youtube/v3"

# CJK Unified Ideographs U+4E00–U+9FFF（仅汉字，不含日文假名/韩文）
CJK_PATTERN = re.compile("[一-鿿]")

# 明确非中文的语言标签（用于反向硬过滤）
DEFINITELY_NON_ZH = {"en", "ja", "ko", "es", "fr", "de", "pt", "ru", "it", "ar", "hi", "th", "vi"}


# ── 工具函数 ──────────────────────────────────────────

def format_relative_time(published_at: str) -> str:
    pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    diff = datetime.now(timezone.utc) - pub_time
    hours = int(diff.total_seconds() / 3600)
    if hours < 1:
        return "刚刚"
    if hours < 24:
        return f"{hours}小时前"
    return f"{hours // 24}天前"


def format_view_count(count: int) -> str:
    if count >= 10000:
        return f"{count / 10000:.1f}万"
    if count >= 1000:
        return f"{count / 1000:.1f}千"
    return str(count)


def is_chinese_video(title: str, channel: str, lang: str) -> bool:
    """三层判定，命中任意一层即认定中文"""
    if CJK_PATTERN.search(title):
        return True
    if lang.startswith("zh"):
        return True
    if CJK_PATTERN.search(channel):
        return True
    return False


def is_definitely_non_chinese(title: str, lang: str) -> bool:
    """反向硬过滤：纯 ASCII 标题 + 明确非中文语言标签 → 丢"""
    if CJK_PATTERN.search(title):
        return False
    if lang and not lang.startswith("zh"):
        primary = lang.split("-")[0].lower()
        if primary in DEFINITELY_NON_ZH:
            return True
    return False


# ── 召回 ──────────────────────────────────────────────

def recall(api_key: str, published_after: str) -> list[dict]:
    """多关键词搜索，按 video_id 去重"""
    all_videos = []
    seen_ids = set()
    failed = []

    for keyword in KEYWORDS_ZH:
        try:
            resp = requests.get(f"{API_BASE}/search", params={
                "key": api_key,
                "q": keyword,
                "part": "snippet",
                "type": "video",
                "order": "date",
                "publishedAfter": published_after,
                "relevanceLanguage": "zh",  # ISO-639-1 标准；不传 regionCode（CN 无效）
                "maxResults": MAX_RESULTS_PER_KEYWORD,
            }, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"警告：中文关键词 '{keyword}' 搜索失败 ({e})", file=sys.stderr)
            failed.append(keyword)
            continue

        for item in resp.json().get("items", []):
            video_id = item["id"]["videoId"]
            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)
            snippet = item["snippet"]
            all_videos.append({
                "video_id": video_id,
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "description": snippet.get("description", ""),
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    if len(failed) == len(KEYWORDS_ZH):
        print("警告：所有中文关键词搜索全部失败，返回空列表（不影响主流程）", file=sys.stderr)
        return []

    print(f"中文区召回：{len(all_videos)} 个候选", file=sys.stderr)
    return all_videos


# ── 详情 + 中文判定过滤 ────────────────────────────────

def filter_chinese(api_key: str, videos: list[dict]) -> list[dict]:
    """批量拿 statistics + snippet，做中文双向判定"""
    if not videos:
        return []

    video_ids = [v["video_id"] for v in videos]
    stats_map = {}
    lang_map = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            resp = requests.get(f"{API_BASE}/videos", params={
                "key": api_key,
                "part": "statistics,snippet",
                "id": ",".join(batch),
            }, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"警告：中文区 videos.list 批次失败 ({e})", file=sys.stderr)
            continue

        for item in resp.json().get("items", []):
            vid = item["id"]
            stats_map[vid] = int(item["statistics"].get("viewCount", 0))
            snippet = item.get("snippet", {})
            lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or ""
            lang_map[vid] = lang.lower()

    chinese_passed = 0
    final = []
    for v in videos:
        vid = v["video_id"]
        v["view_count"] = stats_map.get(vid, 0)
        v["language"] = lang_map.get(vid, "")
        title = v["title"]
        channel = v["channel"]
        lang = v["language"]

        if not is_chinese_video(title, channel, lang):
            continue
        chinese_passed += 1
        if is_definitely_non_chinese(title, lang):
            continue
        final.append(v)

    print(f"中文判定通过：{chinese_passed} → 反向过滤后：{len(final)}", file=sys.stderr)
    return final


# ── 输出 ──────────────────────────────────────────────

def finalize(videos: list[dict]) -> list[dict]:
    """按播放量降序，截断 top 15，添加格式化字段"""
    videos.sort(key=lambda v: v["view_count"], reverse=True)
    videos = videos[:MAX_ZH_REFERENCE]

    for v in videos:
        v["relative_time"] = format_relative_time(v["published_at"])
        v["view_count_formatted"] = format_view_count(v["view_count"])

    return videos


def main():
    enabled = os.environ.get("CYXJ_ENABLE_ZH_REFERENCE", "1").lower()
    if enabled not in ("1", "true", "yes", "on"):
        print("[]")
        print("中文区参考已关闭（CYXJ_ENABLE_ZH_REFERENCE=0）", file=sys.stderr)
        return

    api_key = load_youtube_api_key()
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    candidates = recall(api_key, published_after)
    chinese = filter_chinese(api_key, candidates)
    result = finalize(chinese)

    print(f"中文区最终输出：top {len(result)}", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
