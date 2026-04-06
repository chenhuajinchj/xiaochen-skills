#!/usr/bin/env python3
"""将聚类后的话题 JSON 写入 Obsidian 选题库 — 单文件总览模式"""

import json
import sys
from datetime import datetime
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


def main():
    # 支持两种输入方式：文件参数 或 stdin
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        raw = input_path.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("错误：未收到输入数据", file=sys.stderr)
        sys.exit(1)

    topics = json.loads(raw)

    # 确保目录存在
    TOPIC_DIR.mkdir(parents=True, exist_ok=True)

    # 统计
    now = datetime.now()
    total_videos = sum(len(g["videos"]) for g in topics)
    total_topics = len(topics)
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    filename_time = now.strftime("%Y-%m-%d %H-%M")

    # 收集话题名
    topic_names = [g["topic"] for g in topics]

    # 构建 frontmatter
    topics_yaml = "\n".join(f"  - {name}" for name in topic_names)
    frontmatter = f"""---
source: ai-discovery
created: {timestamp}
status: 未处理
topics:
{topics_yaml}
---"""

    # 构建概览区
    overview = f"""## 本次抓取概览
- 共 {total_videos} 个新视频 · {total_topics} 个话题
- 抓取时间：{timestamp}

### 话题导航"""

    nav_lines = []
    for g in topics:
        name = g["topic"]
        count = len(g["videos"])
        nav_lines.append(f"- [[#{name}]]（{count} 个视频）")
    overview += "\n" + "\n".join(nav_lines)

    # 构建各话题分组
    sections = []
    for g in topics:
        name = g["topic"]
        videos = g["videos"]
        video_lines = [build_video_line(v) for v in videos]
        section = f"## {name}\n" + "\n".join(video_lines)
        sections.append(section)

    # 组装完整文件
    content = frontmatter + "\n\n" + overview + "\n\n---\n\n" + "\n\n".join(sections) + "\n"

    # 写入文件
    file_path = TOPIC_DIR / f"{filename_time} YouTube选题总览.md"
    file_path.write_text(content, encoding="utf-8")

    print(f"已创建：{file_path.name}（{total_topics} 个话题，{total_videos} 个视频）")


if __name__ == "__main__":
    main()
