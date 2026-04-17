#!/usr/bin/env python3
"""YouTube 选题发现 — 三段式：召回 → 硬过滤 → 排序输出"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from paths import get_topic_dir, load_youtube_api_key

# ── 常量 ──────────────────────────────────────────────

# 第一段：召回关键词（大词 + 受众词 + 功能词 + 内容类型词）
KEYWORDS = [
    "Claude Code",              # 兜底大词
    "Claude Code tutorial",     # 教程类
    "Claude Code beginner",     # 新手向
    "Claude Code plan",         # 功能更新
    "Claude Code skills",       # 功能特性
    "Claude Code agent",        # 热点话题
    "Claude Code MCP",          # 生态热点
    "Claude Code build",        # 实战展示
    "Claude Code update",       # 资讯更新
    "Anthropic Academy",        # A 社官方课程/教育
    "Claude Desktop",           # 桌面版动态
]
HOURS_WINDOW = 48
MAX_RESULTS_PER_KEYWORD = 50  # 拉满上限，search.list 无论取多少条都扣 100 点
API_BASE = "https://www.googleapis.com/youtube/v3"

# 第二段：硬过滤阈值
MIN_VIEW_COUNT = 100
MIN_DURATION_SECONDS = 300  # 5 分钟

# 噪音标题关键词（大小写不敏感）
NOISE_TITLE_WORDS = re.compile(
    r"\b(shorts?|clip|highlights?|teaser|trailer|livestream|live\s*stream|"
    r"live\s*coding\s*stream|replay|stream\s*archive)\b",
    re.IGNORECASE,
)

# 非英文字符集
NON_ENGLISH_PATTERN = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff"
    r"\u0600-\u06ff\u0e00-\u0e7f\u0900-\u097f]"
)

TOPIC_DIR = get_topic_dir()
SEEN_IDS_PATH = TOPIC_DIR / ".seen_video_ids.json"

# 匹配 YouTube URL 中的 11 位 Video ID
VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)"
    r"([0-9A-Za-z_-]{11})"
)


# ── 工具函数 ──────────────────────────────────────────

def parse_duration(duration_str: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    return int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + int(match.group(3) or 0)


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


# ── 第一段：召回 ──────────────────────────────────────

def recall(api_key: str, published_after: str) -> list[dict]:
    """多关键词搜索，尽量多拿候选，按 Video ID 去重"""
    all_videos = []
    seen_ids = set()

    for keyword in KEYWORDS:
        try:
            resp = requests.get(f"{API_BASE}/search", params={
                "key": api_key,
                "q": keyword,
                "part": "snippet",
                "type": "video",
                "order": "date",
                "publishedAfter": published_after,
                "relevanceLanguage": "en",
                "maxResults": MAX_RESULTS_PER_KEYWORD,
            }, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"警告：关键词 '{keyword}' 搜索失败 ({e})", file=sys.stderr)
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

    print(f"召回：{len(all_videos)} 个候选", file=sys.stderr)
    return all_videos


# ── 第二段：硬过滤 ──────────────────────────────────────

def enrich_and_filter(api_key: str, videos: list[dict]) -> list[dict]:
    """获取详情 + 硬过滤：语言、时长、播放量、噪音标题"""
    if not videos:
        return []

    # 批量获取详情（videos.list 每次最多 50 个）
    video_ids = [v["video_id"] for v in videos]
    stats_map = {}
    duration_map = {}
    lang_map = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = requests.get(f"{API_BASE}/videos", params={
            "key": api_key,
            "part": "statistics,contentDetails,snippet",
            "id": ",".join(batch),
        }, timeout=30)
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            vid = item["id"]
            stats_map[vid] = int(item["statistics"].get("viewCount", 0))
            duration_map[vid] = parse_duration(item["contentDetails"].get("duration", "PT0S"))
            # 语言：优先 defaultAudioLanguage，其次 defaultLanguage
            snippet = item.get("snippet", {})
            lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or ""
            lang_map[vid] = lang.lower()

    for video in videos:
        video["view_count"] = stats_map.get(video["video_id"], 0)
        video["duration_seconds"] = duration_map.get(video["video_id"], 0)
        video["language"] = lang_map.get(video["video_id"], "")

    # 硬过滤
    filtered = []
    for v in videos:
        title = v["title"]

        # 相关性过滤：标题或描述必须包含相关关键词（不区分大小写）
        text = (title + " " + v.get("description", "")).lower()
        if not any(kw in text for kw in ("claude code", "anthropic", "claude desktop")):
            continue

        # 语言过滤：只保留英语（en, en-US, en-GB 等）或未标注语言的视频
        lang = v.get("language", "")
        if lang and not lang.startswith("en"):
            continue

        # 非英文字符集（兜底：拦截 CJK、俄文等未标注语言的非英文视频）
        if NON_ENGLISH_PATTERN.search(title):
            continue

        # 噪音标题
        if NOISE_TITLE_WORDS.search(title):
            continue

        # 时长 < 5 分钟
        if v["duration_seconds"] < MIN_DURATION_SECONDS:
            continue

        # 播放量 < 100
        if v["view_count"] < MIN_VIEW_COUNT:
            continue

        filtered.append(v)

    print(f"硬过滤后：{len(filtered)} 个", file=sys.stderr)
    return filtered


# ── 去重 ──────────────────────────────────────────────

def load_seen_ids() -> set[str]:
    """从独立索引文件加载已见过的 Video ID，md 扫描作为兜底"""
    seen = set()

    # 主索引：seen_video_ids.json
    if SEEN_IDS_PATH.exists():
        try:
            seen.update(json.loads(SEEN_IDS_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass

    # 兜底：扫描选题库 markdown
    if TOPIC_DIR.exists():
        for md_file in TOPIC_DIR.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                seen.update(VIDEO_ID_PATTERN.findall(content))
            except Exception as e:
                print(f"警告：无法读取 {md_file.name}（{e}）", file=sys.stderr)

    return seen


# ── 第三段：排序 + 输出 ──────────────────────────────────

def sort_and_output(videos: list[dict]) -> list[dict]:
    """按播放量降序排列，添加格式化字段"""
    videos.sort(key=lambda v: v["view_count"], reverse=True)

    for v in videos:
        v["relative_time"] = format_relative_time(v["published_at"])
        v["view_count_formatted"] = format_view_count(v["view_count"])
        mins, secs = divmod(v["duration_seconds"], 60)
        v["duration_formatted"] = f"{mins}分{secs}秒" if secs else f"{mins}分钟"

    return videos


# ── 入口 ──────────────────────────────────────────────

def main():
    api_key = load_youtube_api_key()
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 召回
    candidates = recall(api_key, published_after)

    # 2. 硬过滤
    clean = enrich_and_filter(api_key, candidates)

    # 3. 去重
    seen_ids = load_seen_ids()
    new_videos = [v for v in clean if v["video_id"] not in seen_ids]
    print(f"去重后：{len(new_videos)} 个新视频", file=sys.stderr)

    # 4. 排序 + 输出
    #    注意：.seen_video_ids.json 不在这里更新——必须等 write_topics.py 成功写入
    #    总览文件后才能标记"已处理"，否则中途失败会丢视频。
    result = sort_and_output(new_videos)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
