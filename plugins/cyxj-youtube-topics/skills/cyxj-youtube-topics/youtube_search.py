#!/usr/bin/env python3
"""YouTube 选题发现 — 三段式：召回 → 硬过滤 → 排序输出"""

import json
import os
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
HOURS_WINDOW = max(1, min(168, int(os.environ.get("CYXJ_LOOKBACK_HOURS", "48"))))
MAX_RESULTS_PER_KEYWORD = 50  # 拉满上限，search.list 无论取多少条都扣 100 点
API_BASE = "https://www.googleapis.com/youtube/v3"

# 第二段：硬过滤阈值
MIN_VIEW_COUNT = 100
MIN_DURATION_SECONDS = 300  # 5 分钟

# 信任频道：召回阶段单独查询（绕开关键词竞争），过滤阶段豁免时长门槛。
# 种子列表保证 Day-1 即生效；之外的创作者由 load_promoted_channels() 从创作者索引自动晋升。
SEED_TRUSTED_CHANNELS = [
    ("UCoy6cTJ7Tg0dqS-DI-_REsA", "Chase AI"),
    ("UC2ojq-nuP8ceeHqiroeKhBA", "Nate Herk"),
    ("UCiZotp9tZ4uXgXEjHDUYzBQ", "John Kim"),
    ("UC_x36zCEGilGpB1m-V4gmjg", "IndyDevDan"),
    ("UCSxPE9PHHxQUEt6ajGmQyMA", "Brian Casel"),
    ("UCxVxcTULO9cFU6SB9qVaisQ", "Jack Roberts"),
    ("UCZRp6-Xvzo_dBFvt9L7y3Qw", "Build Great Products"),
    ("UC4x3CR25WSlvMJUtSPPzwwg", "Chris Raroque"),
]

# 自动晋升阈值
PROMOTION_MIN_VIDEOS = 1     # 至少召回过 1 条
PROMOTION_MAX_CHANNELS = 50  # 上限防失控

# 信任频道直查每个频道拉视频上限
TRUSTED_MAX_RESULTS_PER_CHANNEL = 20
APIFY_SEARCH_ACTOR = "streamers~youtube-scraper"

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
    failed_keywords = []

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
            failed_keywords.append(keyword)
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
                "channel_id": snippet.get("channelId", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    if len(failed_keywords) == len(KEYWORDS):
        print(f"错误：所有 {len(KEYWORDS)} 个关键词搜索全部失败，疑似 API key 失效或网络问题", file=sys.stderr)
        sys.exit(1)

    print(f"召回：{len(all_videos)} 个候选", file=sys.stderr)
    return all_videos


# ── 第二段：硬过滤 ──────────────────────────────────────

def enrich_and_filter(api_key: str, videos: list[dict]) -> list[dict]:
    """获取详情 + 硬过滤：语言、时长、播放量、噪音标题。
    已带 duration_seconds + view_count 的视频（如 Apify backend 召回的）跳过 videos.list。"""
    if not videos:
        return []

    # 只对缺少 stats/duration 的视频调 videos.list（节省 quota）
    need_enrich = [
        v for v in videos
        if "duration_seconds" not in v or "view_count" not in v
    ]
    stats_map = {}
    duration_map = {}
    lang_map = {}

    if need_enrich and api_key:
        video_ids = [v["video_id"] for v in need_enrich]
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
                snippet = item.get("snippet", {})
                lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or ""
                lang_map[vid] = lang.lower()

    for video in videos:
        # 已带字段就保留，否则用 videos.list 拿到的值；都没有就 0/空
        video["view_count"] = video.get("view_count", stats_map.get(video["video_id"], 0))
        video["duration_seconds"] = video.get("duration_seconds", duration_map.get(video["video_id"], 0))
        video["language"] = video.get("language", lang_map.get(video["video_id"], ""))

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

        # 时长 < 5 分钟（信任频道豁免：通过 source 字段判断，避免重复维护 channelId set）
        if v["duration_seconds"] < MIN_DURATION_SECONDS and v.get("source") != "trusted_channel":
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


# ── 信任频道直查 ──────────────────────────────────────

def _load_creator_index() -> dict:
    """从 Obsidian 选题库读创作者索引，找不到返回空字典。"""
    p = TOPIC_DIR / "创作者索引.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("creators", {})
    except Exception as e:
        print(f"警告：读创作者索引失败（{e}），跳过自动晋升", file=sys.stderr)
        return {}


def load_promoted_channels() -> list[tuple[str, str]]:
    """自动晋升：从创作者索引筛 is_quality=True AND total_videos≥N AND channel_id 非空，
    按 avg_views 降序取前 PROMOTION_MAX_CHANNELS 个。"""
    creators = _load_creator_index()
    candidates = []
    for name, c in creators.items():
        if not c.get("is_quality"):
            continue
        if c.get("total_videos", 0) < PROMOTION_MIN_VIDEOS:
            continue
        cid = c.get("channel_id", "")
        if not cid:
            continue
        candidates.append((cid, name, c.get("avg_views", 0)))
    candidates.sort(key=lambda x: -x[2])
    return [(cid, name) for cid, name, _ in candidates[:PROMOTION_MAX_CHANNELS]]


def get_trusted_channels() -> list[tuple[str, str]]:
    """合并种子 + 自动晋升，按 channel_id 去重（种子优先保留名字）。"""
    seen = set()
    out = []
    for cid, name in SEED_TRUSTED_CHANNELS:
        if cid in seen:
            continue
        seen.add(cid)
        out.append((cid, name))
    for cid, name in load_promoted_channels():
        if cid in seen:
            continue
        seen.add(cid)
        out.append((cid, name))
    return out


def _parse_apify_duration(value) -> int:
    """Apify 的 duration 可能是 'mm:ss' / 'hh:mm:ss' 字符串或 lengthSeconds 数字。"""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        parts = value.strip().split(":")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            return 0
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
        if len(nums) == 1:
            return nums[0]
    return 0


def _trusted_recall_youtube_api(
    api_key: str, published_after: str, channels: list[tuple[str, str]]
) -> list[dict]:
    """生产 backend：每个频道单独调一次 search.list?channelId=X。每个频道 100 配额。"""
    out = []
    failed = 0
    for cid, name in channels:
        try:
            resp = requests.get(f"{API_BASE}/search", params={
                "key": api_key,
                "channelId": cid,
                "part": "snippet",
                "type": "video",
                "order": "date",
                "publishedAfter": published_after,
                "maxResults": TRUSTED_MAX_RESULTS_PER_CHANNEL,
            }, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"警告：信任频道 '{name}' ({cid}) 拉取失败 ({e})", file=sys.stderr)
            failed += 1
            continue
        for item in resp.json().get("items", []):
            try:
                vid = item["id"]["videoId"]
            except (KeyError, TypeError):
                continue
            snippet = item["snippet"]
            out.append({
                "video_id": vid,
                "title": snippet["title"],
                "channel": snippet.get("channelTitle") or name,
                "channel_id": snippet.get("channelId") or cid,
                "description": snippet.get("description", ""),
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={vid}",
                "source": "trusted_channel",
            })
    print(
        f"信任频道直查（YouTube API）：{len(channels)} 频道，{failed} 失败，召回 {len(out)} 条",
        file=sys.stderr,
    )
    return out


APIFY_BATCH_SIZE = 4  # Apify sync 单次 5 分钟超时，4 频道 × ~60s = 安全


def _apify_recall_batch(
    token: str, batch: list[tuple[str, str]], published_after: str,
    cid_to_name: dict[str, str],
) -> list[dict]:
    """单批 Apify 调用：≤APIFY_BATCH_SIZE 个频道 URL 一次性提交。"""
    apify_url = f"https://api.apify.com/v2/acts/{APIFY_SEARCH_ACTOR}/run-sync-get-dataset-items"
    payload = {
        "startUrls": [
            {"url": f"https://www.youtube.com/channel/{cid}/videos"}
            for cid, _ in batch
        ],
        "maxResults": TRUSTED_MAX_RESULTS_PER_CHANNEL,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
        "dateFilter": "week",
        "videoType": "video",
        "downloadSubtitles": False,
    }
    try:
        resp = requests.post(
            apify_url,
            params={"token": token, "timeout": "300"},
            json=payload,
            timeout=360,
        )
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            raise RuntimeError(f"Apify 返回非列表: {type(items)}")
    except Exception as e:
        print(f"警告：Apify 批 {[n for _, n in batch]} 失败 ({e})", file=sys.stderr)
        return []

    out = []
    for item in items:
        video_url = item.get("url") or item.get("videoUrl") or ""
        m = VIDEO_ID_PATTERN.search(video_url)
        vid = m.group(1) if m else (item.get("id") or "")
        if not vid or len(vid) != 11:
            continue
        channel_url = item.get("channelUrl") or ""
        cid_match = re.search(r"/channel/(UC[A-Za-z0-9_-]{22})", channel_url)
        cid = cid_match.group(1) if cid_match else (item.get("channelId") or "")
        if cid not in cid_to_name:
            continue  # 跳过非本批信任频道的视频
        duration_s = _parse_apify_duration(item.get("lengthSeconds") or item.get("duration"))
        view_count = int(item.get("viewCount") or 0)
        pub_raw = item.get("date") or item.get("publishedAt") or ""
        if pub_raw and pub_raw < published_after:
            continue
        out.append({
            "video_id": vid,
            "title": item.get("title", ""),
            "channel": item.get("channelName") or cid_to_name.get(cid, ""),
            "channel_id": cid,
            "description": item.get("text") or item.get("description") or "",
            "published_at": pub_raw,
            "url": video_url or f"https://www.youtube.com/watch?v={vid}",
            "duration_seconds": duration_s,
            "view_count": view_count,
            "language": "",
            "source": "trusted_channel",
        })
    return out


def _trusted_recall_apify(
    published_after: str, channels: list[tuple[str, str]]
) -> list[dict]:
    """测试 backend：不烧 YouTube quota，用 Apify streamers/youtube-scraper。
    分批调用（每批 APIFY_BATCH_SIZE 个频道）避免 Apify sync 5 分钟超时。
    返回 dict 已包含 duration/views，后续 enrich_and_filter 会跳过 videos.list。"""
    from paths import load_apify_token
    token = load_apify_token()
    cid_to_name = {cid: name for cid, name in channels}

    out = []
    failed_batches = 0
    for i in range(0, len(channels), APIFY_BATCH_SIZE):
        batch = channels[i:i + APIFY_BATCH_SIZE]
        print(f"  Apify 批 {i // APIFY_BATCH_SIZE + 1}：{[n for _, n in batch]}", file=sys.stderr)
        batch_out = _apify_recall_batch(token, batch, published_after, cid_to_name)
        if not batch_out:
            failed_batches += 1
        out.extend(batch_out)

    print(
        f"信任频道直查（Apify 分批）：{len(channels)} 频道分 "
        f"{(len(channels) + APIFY_BATCH_SIZE - 1) // APIFY_BATCH_SIZE} 批，"
        f"{failed_batches} 批失败，召回 {len(out)} 条",
        file=sys.stderr,
    )
    return out


def recall_from_trusted_channels(api_key: str, published_after: str) -> list[dict]:
    """信任频道直查。env CYXJ_TRUSTED_BACKEND 切换：youtube_api（默认）/ apify（测试）。"""
    channels = get_trusted_channels()
    if not channels:
        return []
    backend = os.environ.get("CYXJ_TRUSTED_BACKEND", "youtube_api")
    promoted_count = len(channels) - len(SEED_TRUSTED_CHANNELS)
    print(
        f"信任频道：{len(channels)} 个（种子 {len(SEED_TRUSTED_CHANNELS)} + 晋升 {promoted_count}），backend={backend}",
        file=sys.stderr,
    )
    if backend == "apify":
        return _trusted_recall_apify(published_after, channels)
    return _trusted_recall_youtube_api(api_key, published_after, channels)


# ── 入口 ──────────────────────────────────────────────

def main():
    api_key_required = os.environ.get("CYXJ_TRUSTED_BACKEND", "youtube_api") != "apify"
    api_key = load_youtube_api_key() if api_key_required else ""
    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1a. 关键词召回（Apify 模式下不跑——避免烧 YouTube quota）
    if api_key:
        keyword_candidates = recall(api_key, published_after)
        for v in keyword_candidates:
            v["source"] = "keyword"
    else:
        print("信号：Apify 模式跳过关键词召回（避免烧 YouTube quota）", file=sys.stderr)
        keyword_candidates = []

    # 1b. 信任频道直查
    trusted_candidates = recall_from_trusted_channels(api_key, published_after)

    # 1c. 合并：video_id 去重，trusted 覆盖 keyword（保留 trusted source）
    by_id: dict[str, dict] = {}
    for v in keyword_candidates + trusted_candidates:
        existing = by_id.get(v["video_id"])
        if existing is None or v.get("source") == "trusted_channel":
            by_id[v["video_id"]] = v
    candidates = list(by_id.values())
    print(f"召回合并：{len(candidates)} 个候选（去重后）", file=sys.stderr)

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
