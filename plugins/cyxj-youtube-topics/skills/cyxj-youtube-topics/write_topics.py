#!/usr/bin/env python3
"""将聚类后的话题 JSON 写入 Obsidian 选题库 — 分层总览 + 话题索引追踪"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

TOPIC_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
    / "灵感库"
    / "选题库"
)
INDEX_PATH = TOPIC_DIR / "话题索引.json"

# 状态判断阈值
RISING_MIN_APPEARANCES = 2
SATURATED_MIN_APPEARANCES = 4
SATURATED_MIN_VIDEOS = 10
STALE_DAYS = 5


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


def build_video_line(video: dict) -> str:
    """构建单条视频的 markdown 行（带复选框）"""
    title = video["title"]
    url = video["url"]
    channel = video["channel"]
    relative_time = video["relative_time"]
    views = video["view_count_formatted"]
    duration = video.get("duration_formatted", "")
    duration_part = f" · {duration}" if duration else ""
    return f"- [ ] [{title}]({url}) — {channel} · {relative_time} · {views}播放{duration_part}"


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

    # 加载话题索引
    index = load_index()
    index_map = {t["id"]: t for t in index["topics"]}

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
            video_lines = [build_video_line(v) for v in g["videos"]]
            section = f"### {name}\n" + "\n".join(video_lines)
            sections.append(section)

    # 第二层：升温中的话题
    if rising_topics:
        sections.append("---\n\n## 📈 升温中的话题")
        for g, entry in rising_topics:
            name = g["topic"]
            ref_block = build_topic_ref(entry)
            video_lines = [build_video_line(v) for v in g["videos"]]
            section = f"### {name}\n{ref_block}\n\n" + "\n".join(video_lines)
            sections.append(section)

    # 第三层：饱和/仅记录
    if saturated_topics:
        sections.append("---\n\n## 📋 仅记录（饱和话题）")
        for g, entry in saturated_topics:
            name = g["topic"]
            ref_block = build_topic_ref(entry)
            video_lines = [build_video_line(v) for v in g["videos"]]
            section = f"### {name}\n{ref_block}\n\n" + "\n".join(video_lines)
            sections.append(section)

    # 组装完整文件
    content = frontmatter + "\n\n" + overview + "\n\n" + "\n\n".join(sections) + "\n"

    # 写入每日总览
    file_path = TOPIC_DIR / f"{filename_time} YouTube选题总览.md"
    file_path.write_text(content, encoding="utf-8")

    # 保存更新后的话题索引
    index["topics"] = list(index_map.values())
    save_index(index)

    # 输出结果
    print(f"已创建：{file_path.name}（{new_count} 个新话题，{known_count} 个已知话题更新，共 {total_videos} 个视频）")


if __name__ == "__main__":
    main()
