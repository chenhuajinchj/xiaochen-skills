#!/usr/bin/env python3
"""将聚类后的话题 JSON 写入 Obsidian 选题库 — 分层总览 + 话题索引追踪"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from paths import get_topic_dir

TOPIC_DIR = get_topic_dir()
INDEX_PATH = TOPIC_DIR / "话题索引.json"
CREATOR_PATH = TOPIC_DIR / "创作者索引.json"

# 状态判断阈值
RISING_MIN_APPEARANCES = 2
SATURATED_MIN_APPEARANCES = 4
SATURATED_MIN_VIDEOS = 10
STALE_DAYS = 5

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


def build_topic_ref(topic_entry: dict) -> str:
    """构建已知话题的引用块（首发信息）"""
    first = topic_entry.get("first_video", {})
    first_title = first.get("title", "未知")
    first_url = first.get("url", "")
    first_channel = first.get("channel", "未知")
    first_seen = topic_entry.get("first_seen", "未知")
    total = topic_entry.get("total_videos", 0)
    status = topic_entry.get("status", "未知")

    link = f"[{first_title}]({first_url})" if first_url else first_title
    return f"> 首发：{first_seen} · {first_channel} · {link}\n> 累计 {total} 个视频 · 状态：{status}"


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

    topics = json.loads(raw)
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

    # 将已知话题按状态细分
    rising_topics = [(g, e) for g, e in known_topics if e["status"] == "升温中"]
    saturated_topics = [(g, e) for g, e in known_topics if e["status"] in ("饱和", "已沉寂")]

    # ── 构建 Markdown ──

    # 收集所有话题名用于 frontmatter
    all_topic_names = [g["topic"] for g in topics]
    topics_yaml = "\n".join(f"  - {name}" for name in all_topic_names)

    frontmatter = f"""---
source: ai-discovery
created: {timestamp}
status: 未处理
new_topics: {new_count}
known_topics: {known_count}
topics:
{topics_yaml}
---"""

    # 概览区
    overview = f"""## 本次抓取概览
- 共 {total_videos} 个新视频
- **{new_count} 个新话题** · {known_count} 个已知话题有更新
- 抓取时间：{timestamp}"""

    # 分层内容
    sections = []

    # 第一层：新发现的话题
    if new_topics:
        sections.append("---\n\n## 🆕 新发现的话题")
        for g, entry in new_topics:
            name = g["topic"]
            video_lines = [build_video_line(v, quality_channels) for v in g["videos"]]
            section = f"### {name}\n" + "\n".join(video_lines)
            sections.append(section)

    # 第二层：升温中的话题
    if rising_topics:
        sections.append("---\n\n## 📈 升温中的话题")
        for g, entry in rising_topics:
            name = g["topic"]
            ref_block = build_topic_ref(entry)
            video_lines = [build_video_line(v, quality_channels) for v in g["videos"]]
            section = f"### {name}\n{ref_block}\n\n" + "\n".join(video_lines)
            sections.append(section)

    # 第三层：饱和/仅记录
    if saturated_topics:
        sections.append("---\n\n## 📋 仅记录（饱和话题）")
        for g, entry in saturated_topics:
            name = g["topic"]
            ref_block = build_topic_ref(entry)
            video_lines = [build_video_line(v, quality_channels) for v in g["videos"]]
            section = f"### {name}\n{ref_block}\n\n" + "\n".join(video_lines)
            sections.append(section)

    # 组装完整文件
    content = frontmatter + "\n\n" + overview + "\n\n" + "\n\n".join(sections) + "\n"

    # 写入每日总览
    file_path = TOPIC_DIR / f"{filename_time} YouTube选题总览.md"
    file_path.write_text(content, encoding="utf-8")

    # 保存更新后的话题索引和创作者索引
    index["topics"] = list(index_map.values())
    save_index(index)
    creator_data["creators"] = creators
    save_creators(creator_data)

    # 输出结果
    print(f"已创建：{file_path.name}（{new_count} 个新话题，{known_count} 个已知话题更新，共 {total_videos} 个视频）")


if __name__ == "__main__":
    main()
