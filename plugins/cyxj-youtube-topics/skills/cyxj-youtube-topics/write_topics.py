#!/usr/bin/env python3
"""将聚类后的话题 JSON 写入 Obsidian 选题库 — 分层总览 + 话题索引追踪"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from paths import get_topic_dir

VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)"
    r"([0-9A-Za-z_-]{11})"
)

TOPIC_DIR = get_topic_dir()
INDEX_PATH = TOPIC_DIR / "话题索引.json"
ARCHIVE_INDEX_PATH = TOPIC_DIR / "话题索引-归档.json"
CREATOR_PATH = TOPIC_DIR / "创作者索引.json"
SEEN_IDS_PATH = TOPIC_DIR / ".seen_video_ids.json"

# 状态判断阈值
RISING_MIN_APPEARANCES = 2
SATURATED_MIN_APPEARANCES = 4
SATURATED_MIN_VIDEOS = 10
STALE_DAYS = 5
ARCHIVE_AFTER_DAYS = 30  # 已沉寂 + 超过 N 天没更新 → 归档

# 创作者优质判断阈值
QUALITY_AVG_VIEWS = 5000
QUALITY_MAX_VIEWS = 20000


def load_creators() -> dict:
    """加载创作者索引"""
    if CREATOR_PATH.exists():
        try:
            return json.loads(CREATOR_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"creators": {}}


def save_creators(data: dict):
    """保存创作者索引"""
    CREATOR_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_view_count(formatted: str) -> int:
    """解析格式化播放量回数字：1.4万→14000, 7.0千→7000, 662→662"""
    formatted = formatted.strip()
    if formatted.endswith("万"):
        return int(float(formatted[:-1]) * 10000)
    elif formatted.endswith("千"):
        return int(float(formatted[:-1]) * 1000)
    else:
        try:
            return int(formatted.replace(",", ""))
        except ValueError:
            return 0


def extract_video_id(url: str) -> str:
    """从 YouTube URL 中提取 11 位 video_id，失败返回空字符串"""
    m = VIDEO_ID_PATTERN.search(url or "")
    return m.group(1) if m else ""


def merge_top_3_videos(entry: dict, new_videos: list, today: str) -> list:
    """把本期视频合入历史 top_3，按播放量重排后保留前 3。
    top_3_videos 是话题指纹，给 LLM 做聚类匹配和判断用。"""
    existing = list(entry.get("top_3_videos", []))
    seen_ids = {v.get("video_id") for v in existing if v.get("video_id")}

    for v in new_videos:
        vid = extract_video_id(v.get("url", ""))
        if not vid or vid in seen_ids:
            continue
        seen_ids.add(vid)
        existing.append({
            "title": v.get("title", ""),
            "channel": v.get("channel", ""),
            "url": v.get("url", ""),
            "video_id": vid,
            "view_count": parse_view_count(v.get("view_count_formatted", "0")),
            "seen_at": today,
        })
    existing.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    return existing[:3]


def compute_signals(entry: dict, today: str, this_run_count: int) -> dict:
    """算硬信号：饱和度 / 话题年龄 / 热度趋势 / 头部集中度。
    判断层的脚本级输入，无 LLM 成本。"""
    total = entry.get("total_videos", 0)
    if total >= 10:
        saturation = "高"
    elif total >= 3:
        saturation = "中"
    else:
        saturation = "低"

    try:
        first_dt = datetime.strptime(entry.get("first_seen", today), "%Y-%m-%d")
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        age_days = (today_dt - first_dt).days
    except Exception:
        age_days = 0

    appearances = entry.get("appearances", 0)
    if this_run_count >= 3 and appearances > 1:
        momentum = "升温"
    elif this_run_count == 0:
        momentum = "降温"
    else:
        momentum = "平稳"

    top_3 = entry.get("top_3_videos", [])
    if top_3:
        top1 = top_3[0].get("view_count", 0)
        total_views = sum(v.get("view_count", 0) for v in top_3)
        head_concentration = round(top1 / total_views, 2) if total_views > 0 else 0
    else:
        head_concentration = 0

    return {
        "saturation": saturation,
        "age_days": age_days,
        "momentum": momentum,
        "this_run_count": this_run_count,
        "head_concentration": head_concentration,
    }


def update_creator(creators: dict, channel: str, views: int, today: str):
    """更新单个创作者的统计数据"""
    if channel not in creators:
        creators[channel] = {
            "total_videos": 0,
            "total_views": 0,
            "avg_views": 0,
            "max_views": 0,
            "first_seen": today,
            "appearances": 0,
            "first_discoveries": 0,
            "is_quality": False,
            "quality_source": "auto",
            "tags": [],
        }
    c = creators[channel]
    c["total_videos"] += 1
    c["total_views"] += views
    c["max_views"] = max(c.get("max_views", 0), views)
    c["avg_views"] = c["total_views"] // max(c["total_videos"], 1)


def refresh_creator_quality(creators: dict):
    """刷新所有非手动标记创作者的优质状态"""
    for channel, c in creators.items():
        if c.get("quality_source") == "manual":
            continue  # 手动标记的不覆盖
        tags = []
        if c.get("avg_views", 0) >= QUALITY_AVG_VIEWS:
            tags.append("高均播放")
        if c.get("max_views", 0) >= QUALITY_MAX_VIEWS:
            tags.append("爆款视频")
        if c.get("first_discoveries", 0) >= 1:
            tags.append("话题首发者")
        if c.get("appearances", 0) >= 3:
            tags.append("高频创作")
        c["is_quality"] = len(tags) > 0
        c["tags"] = tags


def append_seen_video_ids(new_ids: set):
    """总览写入成功后，才把视频 ID 追加到 .seen_video_ids.json。
    先读已有集合 → 合并 → 写回。避免覆盖其他流程写入的 ID。"""
    existing = set()
    if SEEN_IDS_PATH.exists():
        try:
            existing = set(json.loads(SEEN_IDS_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    all_ids = existing | new_ids
    SEEN_IDS_PATH.write_text(
        json.dumps(sorted(all_ids), ensure_ascii=False),
        encoding="utf-8",
    )


def load_index() -> dict:
    """加载话题索引，不存在则返回空结构"""
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"topics": []}


def save_index(index: dict):
    """保存话题索引"""
    TOPIC_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def archive_stale_topics(index: dict, today: str) -> int:
    """把已沉寂 + 超过 ARCHIVE_AFTER_DAYS 天没更新的话题挪到归档文件。返回归档数量。"""
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    active, to_archive = [], []
    for entry in index.get("topics", []):
        if entry.get("status") != "已沉寂":
            active.append(entry)
            continue
        try:
            last_dt = datetime.strptime(entry.get("last_updated", today), "%Y-%m-%d")
            if (today_dt - last_dt).days >= ARCHIVE_AFTER_DAYS:
                to_archive.append(entry)
            else:
                active.append(entry)
        except ValueError:
            active.append(entry)

    if to_archive:
        archive = {"topics": []}
        if ARCHIVE_INDEX_PATH.exists():
            try:
                archive = json.loads(ARCHIVE_INDEX_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        # 加归档时间戳
        for t in to_archive:
            t["archived_at"] = today
        archive.setdefault("topics", []).extend(to_archive)
        ARCHIVE_INDEX_PATH.write_text(
            json.dumps(archive, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        index["topics"] = active
    return len(to_archive)


def make_topic_id(name: str) -> str:
    """从中文话题名生成简短 ID（用拼音首字母或关键词）"""
    # 简单方案：去掉空格和特殊字符，用小写连字符
    clean = name.replace("Claude Code", "cc").replace("+", "").replace("（", "").replace("）", "")
    parts = clean.split()
    slug = "-".join(parts).lower().strip("-")
    return slug or f"topic-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def determine_status(topic_entry: dict, today: str) -> str:
    """根据出现次数和最近更新时间判断话题状态"""
    appearances = topic_entry.get("appearances", 1)
    total_videos = topic_entry.get("total_videos", 0)
    last_updated = topic_entry.get("last_updated", today)

    # 已沉寂：超过 STALE_DAYS 天没有新视频
    try:
        last_dt = datetime.strptime(last_updated, "%Y-%m-%d")
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        if (today_dt - last_dt).days > STALE_DAYS:
            return "已沉寂"
    except ValueError:
        pass

    # 饱和：出现 4+ 期 或 累计 10+ 个视频
    if appearances >= SATURATED_MIN_APPEARANCES or total_videos >= SATURATED_MIN_VIDEOS:
        return "饱和"

    # 升温中：出现 2-3 期
    if appearances >= RISING_MIN_APPEARANCES:
        return "升温中"

    return "新话题"


def build_video_line(video: dict, quality_channels: set = None) -> str:
    """构建单条视频的 markdown 行（带复选框，优质创作者加 ⭐）"""
    title = video["title"]
    url = video["url"]
    channel = video["channel"]
    relative_time = video["relative_time"]
    views = video["view_count_formatted"]
    duration = video.get("duration_formatted", "")
    duration_part = f" · {duration}" if duration else ""
    star = " ⭐" if quality_channels and channel in quality_channels else ""
    return f"- [ ] [{title}]({url}) — {channel}{star} · {relative_time} · {views}播放{duration_part}"


def build_topic_ref(topic_entry: dict, *, nested: bool = False) -> str:
    """构建已知话题的「首发追溯」callout 块。

    nested=True 时返回嵌套语法（每行 `> > ` 前缀），用于挂在主 verdict callout 内部。
    nested=False 时返回顶层 callout 语法（每行 `> ` 前缀）。"""
    first = topic_entry.get("first_video", {})
    first_title = first.get("title", "未知")
    first_url = first.get("url", "")
    first_channel = first.get("channel", "未知")
    first_seen = topic_entry.get("first_seen", "未知")
    total = topic_entry.get("total_videos", 0)
    status = topic_entry.get("status", "未知")

    link = f"[{first_title}]({first_url})" if first_url else first_title
    prefix = "> > " if nested else "> "
    lines = [
        f"{prefix}[!quote] 首发追溯",
        f"{prefix}**首发视频**：{link}",
        f"{prefix}**频道**：{first_channel}",
        f"{prefix}**发布时间**：{first_seen}",
        f"{prefix}**累计**：{total} 个视频",
        f"{prefix}**状态**：{status}",
    ]
    return "\n".join(lines)


def effective_verdict(cluster: dict) -> dict:
    """取一个话题的最终 verdict。优先用 LLM 的 last_judgment，
    否则退到 triage（粗筛砍的标"跳过"），再退到"观望"。"""
    j = cluster.get("last_judgment") or {}
    if j.get("label"):
        return {
            "label": j["label"],
            "reason": j.get("reason", ""),
            "angle": j.get("angle", ""),
            "signals_used": j.get("signals_used", []),
            "source": "llm",
        }
    triage = cluster.get("triage") or {}
    if triage.get("status") == "skip":
        return {
            "label": "跳过",
            "reason": f"粗筛：{triage.get('reason', '')}",
            "angle": "",
            "signals_used": [],
            "source": "triage",
        }
    return {
        "label": "观望",
        "reason": "未做 LLM 判断（默认）",
        "angle": "",
        "signals_used": [],
        "source": "default",
    }


def format_signals_line(signals: dict) -> str:
    """把 signals 渲染成一行紧凑展示"""
    if not signals:
        return ""
    parts = []
    if signals.get("saturation"):
        parts.append(f"饱和={signals['saturation']}")
    if "age_days" in signals:
        parts.append(f"年龄={signals['age_days']}天")
    if signals.get("momentum"):
        parts.append(f"趋势={signals['momentum']}")
    if "head_concentration" in signals:
        parts.append(f"头部={signals['head_concentration']}")
    if "this_run_count" in signals:
        parts.append(f"本期+{signals['this_run_count']}")
    if "total_videos" in signals:
        parts.append(f"累计{signals['total_videos']}")
    return " · ".join(parts)


# verdict → callout 类型 + 折叠符 映射
VERDICT_CALLOUT = {
    "值得做": ("success", "+"),
    "观望":   ("info",    "+"),
    "跟风":   ("warning", "-"),
    "跳过":   ("failure", "-"),
}


def build_verdict_block(cluster: dict, entry: dict) -> str:
    """构建话题的顶层 callout 块（仅含判断字段，不含视频列表）。

    格式：
        > [!success]+ 话题名 `[状态]`
        > **理由**：...
        > **切口**：...     （跳过省略）
        > **信号**：...
        > **依据**：...
    """
    v = effective_verdict(cluster)
    label = v["label"]
    callout_type, fold = VERDICT_CALLOUT.get(label, ("info", "+"))
    name = cluster.get("topic", "未知")
    status_tag = f"`[{entry.get('status', '未知')}]`"
    signals_line = format_signals_line(cluster.get("signals") or {})

    lines = [f"> [!{callout_type}]{fold} {name} {status_tag}"]
    if v["reason"]:
        lines.append(f"> **理由**：{v['reason']}")
    # 跳过省略「切口」字段
    if v["angle"] and label != "跳过":
        lines.append(f"> **切口**：{v['angle']}")
    if signals_line:
        lines.append(f"> **信号**：{signals_line}")
    if v["signals_used"]:
        lines.append(f"> **依据**：{'、'.join(v['signals_used'])}")
    return "\n".join(lines)


def build_nested_video_list(videos: list, quality_channels: set = None) -> str:
    """构建嵌套在主 callout 内的「相关视频」折叠 callout（`> > [!example]-`）。

    每条视频：- [title](url) · channel⭐ · 时间 · 播放 · 时长
    返回的字符串本身已包含前导空 `>` 行（嵌套必需）。
    """
    if not videos:
        return ""
    header = f"> > [!example]- 相关视频（{len(videos)} 条）"
    item_lines = []
    for v in videos:
        title = v.get("title", "")
        url = v.get("url", "")
        channel = v.get("channel", "")
        relative_time = v.get("relative_time", "")
        views = v.get("view_count_formatted", "")
        duration = v.get("duration_formatted", "")
        star = " ⭐" if quality_channels and channel in quality_channels else ""
        parts = [f"[{title}]({url})", f"{channel}{star}", relative_time, f"{views}播放"]
        if duration:
            parts.append(duration)
        item_lines.append("> > - " + " · ".join(parts))
    # 前导空 `>` 让 Obsidian 识别嵌套 callout
    return ">\n" + header + "\n" + "\n".join(item_lines)


def build_oneliner(cluster: dict, entry: dict, quality_channels: set = None) -> str:
    """跟风 / 跳过 的 callout 块 + 嵌套视频列表（折叠）。

    用 verdict 对应的 warning/failure callout 包裹判断字段，再嵌套一个 [!example]- 折叠
    视频列表，让用户点开就能看到链接。
    """
    verdict_block = build_verdict_block(cluster, entry)
    videos = cluster.get("videos", []) or []
    nested = build_nested_video_list(videos, quality_channels)
    if not nested:
        return verdict_block
    return verdict_block + "\n" + nested


def main():
    # 读取输入
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        raw = input_path.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("错误：未收到输入数据", file=sys.stderr)
        sys.exit(1)

    data = json.loads(raw)
    if isinstance(data, list):
        # 兼容旧结构：裸数组等同于 clusters
        topics = data
        zh_topics = []
    else:
        topics = data.get("clusters", [])
        zh_topics = data.get("zh_topics", [])

    TOPIC_DIR.mkdir(parents=True, exist_ok=True)

    # 加载话题索引和创作者索引
    index = load_index()
    index_map = {t["id"]: t for t in index["topics"]}
    creator_data = load_creators()
    creators = creator_data.get("creators", {})

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    filename_time = now.strftime("%Y-%m-%d %H-%M")

    # 分类话题
    new_topics = []       # is_new == True
    known_topics = []     # is_new == False

    for g in topics:
        is_new = g.get("is_new", True)
        videos = g["videos"]
        video_count = len(videos)

        if is_new:
            # 新话题：创建索引条目
            topic_id = make_topic_id(g["topic"])
            # 确保 ID 唯一
            base_id = topic_id
            counter = 2
            while topic_id in index_map:
                topic_id = f"{base_id}-{counter}"
                counter += 1

            first_video = videos[0] if videos else {}
            entry = {
                "id": topic_id,
                "name": g["topic"],
                "aliases": [],
                "status": "新话题",
                "first_seen": today,
                "first_video": {
                    "title": first_video.get("title", ""),
                    "url": first_video.get("url", ""),
                    "channel": first_video.get("channel", ""),
                },
                "total_videos": video_count,
                "appearances": 1,
                "last_updated": today,
            }
            index_map[topic_id] = entry
            new_topics.append((g, entry))
        else:
            # 已知话题：更新索引
            existing_id = g.get("existing_topic_id", "")
            entry = index_map.get(existing_id)
            if entry:
                entry["total_videos"] = entry.get("total_videos", 0) + video_count
                entry["appearances"] = entry.get("appearances", 0) + 1
                entry["last_updated"] = today
                # 把本次话题名加入别名（如果不同）
                if g["topic"] != entry["name"] and g["topic"] not in entry.get("aliases", []):
                    entry.setdefault("aliases", []).append(g["topic"])
                entry["status"] = determine_status(entry, today)
                known_topics.append((g, entry))
            else:
                # existing_topic_id 找不到，当新话题处理
                topic_id = make_topic_id(g["topic"])
                base_id = topic_id
                counter = 2
                while topic_id in index_map:
                    topic_id = f"{base_id}-{counter}"
                    counter += 1
                first_video = videos[0] if videos else {}
                entry = {
                    "id": topic_id,
                    "name": g["topic"],
                    "aliases": [],
                    "status": "新话题",
                    "first_seen": today,
                    "first_video": {
                        "title": first_video.get("title", ""),
                        "url": first_video.get("url", ""),
                        "channel": first_video.get("channel", ""),
                    },
                    "total_videos": video_count,
                    "appearances": 1,
                    "last_updated": today,
                }
                index_map[topic_id] = entry
                new_topics.append((g, entry))

    # 更新所有已沉寂话题的状态
    for entry in index_map.values():
        entry["status"] = determine_status(entry, today)

    # 扩展字段：top_3_videos（本期视频合入历史 top_3）+ signals（硬信号）
    # topic_judge.py 读取 signals 做粗筛；top_3_videos 作为话题指纹供 LLM 匹配。
    run_counts = {}  # entry_id -> 本次新增视频数
    for g, entry in new_topics + known_topics:
        entry["top_3_videos"] = merge_top_3_videos(entry, g["videos"], today)
        run_counts[entry["id"]] = run_counts.get(entry["id"], 0) + len(g["videos"])
    # 所有索引条目都算 signals（包括本次没新增的沉寂话题）
    for entry in index_map.values():
        this_run_count = run_counts.get(entry["id"], 0)
        entry["signals"] = compute_signals(entry, today, this_run_count)
        # last_judgment 占位——由 topic_judge.py 填充
        entry.setdefault("last_judgment", {})

    # 更新创作者索引
    seen_channels_today = set()
    for g in topics:
        for v in g["videos"]:
            channel = v["channel"]
            views = parse_view_count(v.get("view_count_formatted", "0"))
            update_creator(creators, channel, views, today)
            seen_channels_today.add(channel)
    # 更新出现期数（每个频道每天只算一次）
    for ch in seen_channels_today:
        creators[ch]["appearances"] = creators[ch].get("appearances", 0) + 1
    # 更新首发者计数
    for g, entry in new_topics:
        first_ch = entry.get("first_video", {}).get("channel", "")
        if first_ch and first_ch in creators:
            creators[first_ch]["first_discoveries"] = creators[first_ch].get("first_discoveries", 0) + 1
    # 刷新优质状态
    refresh_creator_quality(creators)
    # 构建优质频道集合
    quality_channels = {ch for ch, c in creators.items() if c.get("is_quality")}

    # 统计
    total_videos = sum(len(g["videos"]) for g in topics)
    new_count = len(new_topics)
    known_count = len(known_topics)

    # 按 verdict 分组（值得做/观望 详细展示，跟风/跳过 一行）
    all_pairs = new_topics + known_topics
    buckets = {"值得做": [], "观望": [], "跟风": [], "跳过": []}
    for g, entry in all_pairs:
        label = effective_verdict(g)["label"]
        if label in buckets:
            buckets[label].append((g, entry))
        else:
            buckets["观望"].append((g, entry))

    worth_count = len(buckets["值得做"])
    watch_count = len(buckets["观望"])
    follow_count = len(buckets["跟风"])
    skip_count = len(buckets["跳过"])

    # ── 中文区参考统计 ──
    zh_videos_count = sum(len(t.get("videos", [])) for t in zh_topics)
    zh_topics_count = sum(1 for t in zh_topics if t.get("videos"))

    # ── 构建 Markdown ──

    all_topic_names = [g["topic"] for g in topics]
    # topics 列表项含中文/特殊字符，必须加引号（PROPERTIES 规范第 5 节）
    topics_yaml = "\n".join(f'  - "{name}"' for name in all_topic_names)

    frontmatter = f"""---
source: ai-discovery
created: {timestamp}
status: 未处理
new_topics: {new_count}
known_topics: {known_count}
verdict_worth_doing: {worth_count}
verdict_watching: {watch_count}
verdict_follow: {follow_count}
verdict_skip: {skip_count}
zh_topics_count: {zh_topics_count}
zh_videos_count: {zh_videos_count}
topics:
{topics_yaml}
cssclasses:
  - youtube-topics-report
---"""

    overview = f"""## 本次抓取概览
- 共 {total_videos} 个新视频 · {new_count} 个新话题 · {known_count} 个已知话题更新
- **判断**：💎 {worth_count} 值得做 · 👀 {watch_count} 观望 · 🔁 {follow_count} 跟风 · 📋 {skip_count} 跳过
- 抓取时间：{timestamp}"""

    sections = []

    def detail_section(g, entry):
        """值得做 / 观望 的详细块：
        主 callout（success/info）+ （非新话题时）嵌套首发追溯 + 嵌套视频列表。
        统一用嵌套 callout，跟跟风/跳过保持一致。
        """
        verdict_block = build_verdict_block(g, entry)
        parts = [verdict_block]
        if not g.get("is_new", True):
            # 嵌套在主 callout 内，前导一行空 `>` 让 Obsidian 识别
            parts.append(">\n" + build_topic_ref(entry, nested=True))
        nested_videos = build_nested_video_list(g["videos"], quality_channels)
        if nested_videos:
            parts.append(nested_videos)
        return "\n".join(parts)

    # 值得做
    if buckets["值得做"]:
        sections.append(f"## 💎 值得做（{worth_count} 个）")
        for g, entry in buckets["值得做"]:
            sections.append(detail_section(g, entry))

    # 观望
    if buckets["观望"]:
        sections.append(f"## 👀 观望（{watch_count} 个）")
        for g, entry in buckets["观望"]:
            sections.append(detail_section(g, entry))

    # 跟风（callout + 嵌套折叠视频列表）
    if buckets["跟风"]:
        sections.append(f"## 🔁 跟风（{follow_count} 个）")
        for g, entry in buckets["跟风"]:
            sections.append(build_oneliner(g, entry, quality_channels))

    # 跳过（callout + 嵌套折叠视频列表）
    if buckets["跳过"]:
        sections.append(f"## 📋 跳过（{skip_count} 个）")
        for g, entry in buckets["跳过"]:
            sections.append(build_oneliner(g, entry, quality_channels))

    # 中文区参考（按话题分组，零结果整段跳过）
    if zh_topics and zh_videos_count > 0:
        zh_lines = [
            f"## 🪞 中文区参考（{zh_topics_count} 个话题 · {zh_videos_count} 个视频）",
            "> 中文区最近 48 小时已发布的相关视频。决定做某个选题前可以扫一眼，"
            "看中文 up 主有没有做过同款，点进去参考人家怎么做的。",
            "",
        ]
        for t in zh_topics:
            videos = t.get("videos", [])
            if not videos:
                continue
            topic_name = t.get("topic", "其他")
            zh_lines.append(f"### {topic_name}（{len(videos)} 个）")
            for v in videos:
                # 防 markdown 链接破坏：标题里的 [ ] 替换成 ( )
                title = (v.get("title", "") or "").replace("[", "(").replace("]", ")")
                channel = v.get("channel", "")
                rel_time = v.get("relative_time", "")
                vc = v.get("view_count_formatted", "")
                url = v.get("url", "")
                zh_lines.append(f"- [{title}]({url}) — {channel} · {rel_time} · {vc}")
            zh_lines.append("")
        sections.append("\n".join(zh_lines))

    content = frontmatter + "\n\n" + overview + "\n\n" + "\n\n".join(sections) + "\n"

    # 写入每日总览
    file_path = TOPIC_DIR / f"{filename_time} YouTube选题总览.md"
    file_path.write_text(content, encoding="utf-8")

    # 把 verdict 写入话题索引的 last_judgment 字段（下次跑时 LLM 可见）
    for g, entry in all_pairs:
        v = effective_verdict(g)
        entry["last_judgment"] = {
            "label": v["label"],
            "reason": v["reason"],
            "angle": v["angle"],
            "signals_used": v["signals_used"],
            "source": v["source"],
            "timestamp": timestamp,
        }

    # 保存更新后的话题索引和创作者索引
    index["topics"] = list(index_map.values())
    archived_count = archive_stale_topics(index, today)
    if archived_count:
        print(f"归档 {archived_count} 个长期沉寂话题", file=sys.stderr)
    save_index(index)
    creator_data["creators"] = creators
    save_creators(creator_data)

    # 追加判断日志（每行一条，事后回看"准不准"用）
    log_path = TOPIC_DIR / "判断日志.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        for g, entry in all_pairs:
            log_entry = {
                "timestamp": timestamp,
                "topic": g.get("topic", ""),
                "topic_id": entry.get("id", ""),
                "is_new": g.get("is_new", True),
                "verdict": effective_verdict(g),
                "signals": g.get("signals", {}),
                "triage": g.get("triage", {}),
                "videos_count": len(g.get("videos", [])),
                "top_video_url": g.get("videos", [{}])[0].get("url", "") if g.get("videos") else "",
            }
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    # 最后一步：总览 + 索引 + 日志都写完了，标记视频为"已见"是安全的。
    # 如果上面任何一步失败，这里不会执行，下次跑仍能重新捞到。
    video_ids = set()
    for g in topics:
        for v in g["videos"]:
            m = VIDEO_ID_PATTERN.search(v.get("url", ""))
            if m:
                video_ids.add(m.group(1))
    if video_ids:
        append_seen_video_ids(video_ids)

    # 输出结果
    print(
        f"已创建：{file_path.name}（💎 {worth_count} 值得做 · 👀 {watch_count} 观望 · "
        f"🔁 {follow_count} 跟风 · 📋 {skip_count} 跳过，共 {total_videos} 个视频）"
    )


if __name__ == "__main__":
    main()
