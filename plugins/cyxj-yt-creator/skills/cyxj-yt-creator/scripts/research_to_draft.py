#!/usr/bin/env python3
"""Apify YouTube creator research -> Obsidian draft."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

SEARCH_ACTOR = "streamers~youtube-scraper"
TRANSCRIPT_ACTOR = "karamelo~youtube-transcripts"

DEFAULT_DRAFT_DIR = Path(
    "/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感库/待发布"
)
DEFAULT_PROFILE = Path(
    "/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/个人档案.md"
)


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env_value(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value.strip()

    for env_path in (skill_dir() / ".env", Path.home() / ".config" / "cyxj" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            if key.strip() == name:
                return raw.strip().strip("\"'")
    return ""


def apify_post(actor_id: str, token: str, payload: dict[str, Any], timeout: int = 240) -> list[dict[str, Any]]:
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    response = requests.post(url, params={"token": token, "timeout": str(timeout)}, json=payload, timeout=timeout + 30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Apify actor {actor_id} returned non-list payload")
    return data


def default_queries(topic: str) -> list[str]:
    words = [topic]
    if " " in topic:
        words.append(f'"{topic}"')
    words.extend(
        [
            f"{topic} tutorial",
            f"{topic} review",
            f"{topic} workflow",
            f"{topic} 教程",
            f"{topic} 实测",
        ]
    )
    return dedupe_strings(words)


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def canonical_url(url: str) -> str:
    if not url:
        return ""
    return url.split("&")[0]


def dedupe_videos(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        url = canonical_url(str(item.get("url") or item.get("videoUrl") or ""))
        if not url or url in seen:
            continue
        item["url"] = url
        seen.add(url)
        out.append(item)
    return out


def sort_by_date_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item.get("date") or item.get("publishedAt") or ""), reverse=True)


def parse_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def format_views(value: Any) -> str:
    count = parse_int(value)
    if count >= 10000:
        return f"{count / 10000:.1f}万"
    if count >= 1000:
        return f"{count / 1000:.1f}千"
    return str(count)


def date_only(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else text


def slugify(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:80] or "creator-research"


def plain_transcript(item: dict[str, Any], limit_chars: int) -> str:
    captions = item.get("captions") or []
    if not isinstance(captions, list):
        return ""
    text = " ".join(str(c) for c in captions if c).strip()
    return html.unescape(text[:limit_chars])


def choose_subtitle_targets(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda item: parse_int(item.get("viewCount")), reverse=True)
    return ranked[: max(0, count)]


def read_profile(path: Path) -> str:
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def infer_positioning(profile: str) -> str:
    if "非程序员，用 Claude Code 做一切" in profile:
        return "非程序员，用 Claude Code 做一切"
    return "陈与小金的 Claude Code / Codex 工作流"


def build_markdown(
    *,
    topic: str,
    output_title: str,
    videos: list[dict[str, Any]],
    subtitles: dict[str, str],
    profile: str,
    search_queries: list[str],
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    positioning = infer_positioning(profile)
    top_videos = choose_subtitle_targets(videos, min(8, len(videos)))

    lines: list[str] = []
    add = lines.append
    add("---")
    add(f"title: {output_title}")
    add(f"date: {today}")
    add("source: Apify YouTube Scraper + Apify transcript")
    add("status: 待发布")
    add("tags: [YouTube选题, 博主研究, Apify, Claude Code, Codex]")
    add("---\n")
    add(f"# {output_title}\n")
    add("## 结论\n")
    add(
        f"本轮围绕 **{topic}** 用 Apify 搜到 {len(videos)} 条 YouTube 结果。"
        f"这篇稿子的目标不是复述工具介绍，而是判断外部博主已经怎么讲，以及如何把选题转回 **{positioning}**。"
    )
    add("\n建议优先寻找“工具进入真实工作流”的角度，避免做成普通安装教程或标题党平替介绍。\n")

    add("## 推荐标题\n")
    add(f"> {topic}：我把它接进 {positioning} 的真实工作流\n")
    add("备用标题：\n")
    add(f"- {topic} 不只是工具介绍：它在创作者工作流里怎么用")
    add(f"- 我研究了 YouTube 博主怎么讲 {topic}，发现真正的机会不是安装教程")
    add(f"- {topic} 实战：从博主套路到我的 Claude Code 工作流\n")

    add("## 为什么现在值得做\n")
    add(f"- **外部信号**：本轮搜索拿到 {len(videos)} 条相关视频，说明话题已有内容供参考。")
    add("- **差异化空间**：大多数博主容易停在安装、体验、平替、免费这些浅层卖点。")
    add(f"- **账号匹配**：你的定位是 {positioning}，更适合讲工具如何进入可复用流程，而不是泛泛介绍。")
    add("- **内容资产**：字幕观察可以反推外部视频结构，帮助避开重复表达。\n")

    add("## 建议视频结构\n")
    add("1. 先展示最终效果或最终工作流，不要从安装开始。")
    add("2. 快速交代外部博主都在讲什么：安装、平替、免费、多模型、效率。")
    add("3. 转到你的差异化：非程序员如何把它接进 Claude Code / Codex。")
    add("4. 做一段可复现演示：输入、工具链、输出文件、下一步怎么复用。")
    add("5. 结尾给判断：这个工具适合谁，不适合谁，下一期可以继续做什么。\n")

    add("## 搜索关键词\n")
    for query in search_queries:
        add(f"- `{query}`")
    add("")

    add("## 重点视频与字幕观察\n")
    for item in top_videos:
        url = canonical_url(str(item.get("url") or ""))
        title = item.get("title") or "Untitled"
        transcript = subtitles.get(url, "")
        add(f"### {date_only(item.get('date') or item.get('publishedAt'))} · {title}")
        add(f"- 频道：{item.get('channelName') or item.get('channelTitle') or ''}")
        add(f"- 播放：{format_views(item.get('viewCount'))}")
        duration = item.get("duration") or item.get("durationFormatted") or ""
        if duration:
            add(f"- 时长：{duration}")
        add(f"- 链接：{url}")
        if transcript:
            clean = re.sub(r"\s+", " ", transcript).strip()
            add("- 字幕观察：这条视频可用于拆解博主开场痛点、核心卖点和演示顺序；正式写稿时优先看它的前 3-5 分钟。")
            add(f"- 字幕片段：{clean[:320]}...")
        else:
            add("- 字幕观察：Apify 本轮未抓到字幕，降级用标题、频道和播放数据判断。")
        add("")

    add("## 全部 YouTube 结果（按发布日期倒序）\n")
    for index, item in enumerate(videos, start=1):
        title = item.get("title") or "Untitled"
        url = canonical_url(str(item.get("url") or ""))
        add(f"{index}. **{date_only(item.get('date') or item.get('publishedAt'))}** · [{title}]({url})")
        add(f"   - 频道：{item.get('channelName') or item.get('channelTitle') or ''}")
        add(f"   - 播放：{format_views(item.get('viewCount'))}")
        duration = item.get("duration") or item.get("durationFormatted") or ""
        if duration:
            add(f"   - 时长：{duration}")
        add("")

    add("## 拍摄判断\n")
    add(
        f"**建议做，但要避开普通教程。** 这期应该把 {topic} 放进 {positioning} 的工作流里讲："
        "先给结果，再讲外部博主的共识，最后展示你的本地流程和可复用资产。"
    )
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> Path:
    token = load_env_value("APIFY_API_TOKEN")
    if not token:
        raise SystemExit("未找到 APIFY_API_TOKEN。请设置环境变量、skill .env，或 ~/.config/cyxj/.env。")

    queries = dedupe_strings(args.query or default_queries(args.topic))
    search_payload = {
        "searchQueries": queries,
        "maxResults": args.max_results,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
        "sortingOrder": "relevance",
        "dateFilter": args.date_filter,
        "videoType": "video",
        "downloadSubtitles": False,
    }
    raw_videos = apify_post(SEARCH_ACTOR, token, search_payload, timeout=args.timeout)
    videos = sort_by_date_desc(dedupe_videos(raw_videos))

    subtitle_targets = choose_subtitle_targets(videos, args.subtitle_count)
    subtitle_payload = {"urls": [canonical_url(str(item.get("url") or "")) for item in subtitle_targets]}
    subtitles: dict[str, str] = {}
    if subtitle_payload["urls"]:
        try:
            subtitle_items = apify_post(TRANSCRIPT_ACTOR, token, subtitle_payload, timeout=args.timeout)
            for video, subtitle_item in zip(subtitle_targets, subtitle_items):
                url = canonical_url(str(video.get("url") or ""))
                subtitles[url] = plain_transcript(subtitle_item, args.subtitle_chars)
        except Exception as exc:
            print(f"warn: subtitle actor failed: {exc}", file=sys.stderr)

    profile = read_profile(Path(args.profile).expanduser())
    title = args.output_title or f"{args.topic} 选题研究"
    markdown = build_markdown(
        topic=args.topic,
        output_title=title,
        videos=videos,
        subtitles=subtitles,
        profile=profile,
        search_queries=queries,
    )

    if args.output:
        output = Path(args.output).expanduser()
    elif args.dry_run:
        output = Path("/tmp") / f"{datetime.now().strftime('%Y-%m-%d')} {slugify(args.topic)} 选题研究.md"
    else:
        output_dir = Path(args.out_dir).expanduser()
        output = output_dir / f"{datetime.now().strftime('%Y-%m-%d')} {slugify(args.topic)} 选题研究.md"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(output)
    print(f"videos={len(videos)} subtitles={sum(1 for value in subtitles.values() if value)}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Research YouTube creator usage through Apify and write an Obsidian draft.")
    parser.add_argument("--topic", required=True, help="Research topic, e.g. 'Open Design + HyperFrames'.")
    parser.add_argument("--query", action="append", help="Search query. Repeat for multiple queries. Defaults are derived from topic.")
    parser.add_argument("--max-results", type=int, default=60, help="Max results per search query passed to Apify.")
    parser.add_argument("--subtitle-count", type=int, default=8, help="How many top-view videos to fetch subtitles for.")
    parser.add_argument("--subtitle-chars", type=int, default=5000, help="Max transcript chars kept per video.")
    parser.add_argument("--output-title", help="Markdown title. Defaults to '<topic> 选题研究'.")
    parser.add_argument("--out-dir", default=str(DEFAULT_DRAFT_DIR), help="Output directory for live writes.")
    parser.add_argument("--output", help="Exact output file path.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE), help="Creator profile markdown path.")
    parser.add_argument("--date-filter", default="year", help="Apify YouTube date filter, e.g. day/week/month/year.")
    parser.add_argument("--timeout", type=int, default=240, help="Apify request timeout seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Write to /tmp unless --output is set.")
    args = parser.parse_args()
    try:
        run(args)
    except requests.RequestException as exc:
        print(f"Apify 请求失败：{exc}", file=sys.stderr)
        print("如果是网络/TLS 问题，可重试：HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897 python3 scripts/research_to_draft.py ...", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
