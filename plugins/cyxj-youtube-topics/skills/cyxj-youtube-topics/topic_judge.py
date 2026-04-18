#!/usr/bin/env python3
"""选题判断层：聚类后做硬信号 + 粗筛 + 字幕抓取。

输入（从 stdin 或 argv[1]）：聚类后的 topics JSON，同 write_topics.py 的格式：
    [{"topic": "...", "is_new": true|false, "existing_topic_id": "...",
      "videos": [{...}]}]

输出（到 stdout）：加了 signals、triage、subtitles 三个字段的 JSON。
verdict 本身（值得做/观望/跟风/跳过 + reason + angle）不在这里生成——
由 Claude 主流程读 signals + 字幕 + 用户画像后用 LLM 生成，再合并回数据。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from paths import get_topic_dir
from subtitle_fetcher import fetch_subtitle

TOPIC_DIR = get_topic_dir()
INDEX_PATH = TOPIC_DIR / "话题索引.json"

DEAD_AGE_DAYS = 14
DEAD_NO_NEW_THRESHOLD = 1
SATURATED_LOW_VIEW_THRESHOLD = 300

TOP_N_FOR_SUBTITLES = 3  # 已知话题：抓本期播放量 top 3
# 全新话题无历史数据，扩大字幕采样弥补"信息量不足"——视频数通常 1-5，全抓成本可控

# 字幕精筛阈值：对比实验（/tmp/compare_report.md）证明饱和+头部低类
# 话题字幕带不来增量，只对"可能升值得做"的候选抓字幕
HEATING_TOP_VIEW_THRESHOLD = 10000   # 升温中：头部 ≥1 万播放才抓
SATURATED_RESCUE_THRESHOLD = 1000    # 饱和：头部 ≥1 千播放才救援抓字幕

VIDEO_ID_PATTERN = re.compile(r"([0-9A-Za-z_-]{11})")


def load_index() -> dict:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"topics": []}


def parse_views(formatted: str) -> int:
    formatted = (formatted or "").strip()
    try:
        if formatted.endswith("万"):
            return int(float(formatted[:-1]) * 10000)
        if formatted.endswith("千"):
            return int(float(formatted[:-1]) * 1000)
        return int(formatted.replace(",", ""))
    except (ValueError, IndexError):
        return 0


def extract_video_id(url: str) -> str:
    m = VIDEO_ID_PATTERN.search(url or "")
    return m.group(1) if m else ""


def compute_signals(cluster: dict, historic: dict, today: str) -> dict:
    """算硬信号，融合本期 + 历史数据。historic 是话题索引条目或 None。"""
    this_run = len(cluster.get("videos", []))
    if historic:
        total = historic.get("total_videos", 0) + this_run
        first_seen = historic.get("first_seen", today)
        appearances = historic.get("appearances", 0) + 1
    else:
        total = this_run
        first_seen = today
        appearances = 1

    saturation = "高" if total >= 10 else ("中" if total >= 3 else "低")

    try:
        first_dt = datetime.strptime(first_seen, "%Y-%m-%d")
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        age_days = (today_dt - first_dt).days
    except Exception:
        age_days = 0

    if this_run >= 3 and appearances > 1:
        momentum = "升温"
    elif this_run == 0:
        momentum = "降温"
    else:
        momentum = "平稳"

    views = [parse_views(v.get("view_count_formatted", "0")) for v in cluster.get("videos", [])]
    top_view = max(views) if views else 0
    total_views = sum(views) if views else 0
    head_concentration = round(top_view / total_views, 2) if total_views > 0 else 0

    return {
        "saturation": saturation,
        "age_days": age_days,
        "momentum": momentum,
        "this_run_count": this_run,
        "total_videos": total,
        "head_concentration": head_concentration,
        "top_view_count": top_view,
    }


def triage(signals: dict) -> dict:
    """粗筛：砍掉明显沉寂/过期/饱和无热度的话题。"""
    if signals["age_days"] >= DEAD_AGE_DAYS and signals["this_run_count"] <= DEAD_NO_NEW_THRESHOLD:
        return {
            "status": "skip",
            "reason": f"话题 {signals['age_days']} 天前首发，本期仅 {signals['this_run_count']} 新增",
        }
    if signals["saturation"] == "高" and signals["top_view_count"] < SATURATED_LOW_VIEW_THRESHOLD:
        return {
            "status": "skip",
            "reason": f"话题已饱和（累计 {signals['total_videos']}），本期头部仅 {signals['top_view_count']} 播放",
        }
    return {"status": "pass", "reason": ""}


def should_fetch_subtitles(signals: dict, is_new: bool) -> tuple[bool, str]:
    """字幕精筛：只对可能升到"值得做"的候选抓字幕。

    返回 (是否抓, 精筛原因)。原因用于日志展示。
    """
    top_view = signals.get("top_view_count", 0)
    if is_new:
        return True, "全新话题抓全部"
    if signals.get("momentum") == "升温" and top_view >= HEATING_TOP_VIEW_THRESHOLD:
        return True, f"升温+头部 {top_view / 10000:.1f}w"
    if signals.get("saturation") == "高" and top_view >= SATURATED_RESCUE_THRESHOLD:
        return True, f"饱和+头部 {top_view / 1000:.1f}k 救援"
    if signals.get("saturation") == "高":
        return False, f"饱和+头部仅 {top_view} 跳过"
    if signals.get("momentum") == "升温":
        return False, f"升温但头部仅 {top_view}，字幕无增量"
    return False, f"非升温+头部 {top_view}，字幕无增量"


def fetch_subtitles_for_cluster(cluster: dict, top_n: int) -> dict:
    """拉 top N 视频的字幕。失败的视频返回 None，调用方降级到标题+描述。"""
    out = {}
    for v in cluster.get("videos", [])[:top_n]:
        url = v.get("url", "")
        vid = extract_video_id(url)
        if not vid:
            continue
        out[vid] = fetch_subtitle(url)
    return out


def main():
    raw = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else sys.stdin.read()
    if not raw.strip():
        print("错误：未收到聚类后的 topics JSON", file=sys.stderr)
        sys.exit(1)
    clusters = json.loads(raw)

    index = load_index()
    index_map = {t["id"]: t for t in index.get("topics", [])}
    today = datetime.now().strftime("%Y-%m-%d")

    enriched = []
    fetch_count = 0
    skip_subtitle_count = 0
    triage_skip_count = 0
    for c in clusters:
        is_new = c.get("is_new", True)
        existing_id = c.get("existing_topic_id", "")
        historic = index_map.get(existing_id) if not is_new else None

        c["signals"] = compute_signals(c, historic, today)
        c["triage"] = triage(c["signals"])

        if c["triage"]["status"] == "pass":
            fetch, reason = should_fetch_subtitles(c["signals"], is_new)
            if fetch:
                fetch_count += 1
                top_n = len(c.get("videos", [])) if is_new else TOP_N_FOR_SUBTITLES
                scope = f"全部 {top_n}" if is_new else f"top {top_n}"
                tag = "🆕 全新" if is_new else "已知"
                print(f"精筛 → {c['topic']}（{tag}，{reason}，拉 {scope} 字幕）", file=sys.stderr)
                c["subtitles"] = fetch_subtitles_for_cluster(c, top_n)
                missing = sum(1 for v in c["subtitles"].values() if not v)
                if missing:
                    print(f"  其中 {missing}/{len(c['subtitles'])} 视频字幕抓取失败", file=sys.stderr)
            else:
                skip_subtitle_count += 1
                print(f"精筛跳过字幕 → {c['topic']}（{reason}）", file=sys.stderr)
                c["subtitles"] = {}
        else:
            triage_skip_count += 1
            print(f"粗筛砍 → {c['topic']}（{c['triage']['reason']}）", file=sys.stderr)
            c["subtitles"] = {}

        enriched.append(c)

    print(
        f"判断层：{fetch_count} 进精筛抓字幕，"
        f"{skip_subtitle_count} 精筛跳过字幕，"
        f"{triage_skip_count} 粗筛砍",
        file=sys.stderr,
    )
    print(json.dumps(enriched, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
