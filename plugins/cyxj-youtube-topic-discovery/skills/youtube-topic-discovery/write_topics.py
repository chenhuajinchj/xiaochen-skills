#!/usr/bin/env python3
"""将聚类后的话题 JSON 写入 Obsidian 选题库"""

import json
import sys
from datetime import date
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
    """构建单条视频的 markdown 行"""
    title = video["title"]
    url = video["url"]
    channel = video["channel"]
    relative_time = video["relative_time"]
    views = video["view_count_formatted"]
    duration = video.get("duration_formatted", "")
    duration_part = f" · {duration}" if duration else ""
    return f"- [{title}]({url}) — {channel} · {relative_time} · {views}播放{duration_part}"


def write_topic_file(topic_name: str, videos: list[dict]) -> str:
    """写入或追加一个话题文件，返回操作说明"""
    # 文件名中不能有 / 等非法字符
    safe_name = topic_name.replace("/", "·").replace("\\", "·")
    file_path = TOPIC_DIR / f"{safe_name}.md"

    video_lines = [build_video_line(v) for v in videos]
    video_block = "\n".join(video_lines)

    if file_path.exists():
        # 追加到已有文件
        existing = file_path.read_text(encoding="utf-8")
        # 在文件末尾追加新视频
        updated = existing.rstrip() + "\n" + video_block + "\n"
        file_path.write_text(updated, encoding="utf-8")
        return f"追加 {len(videos)} 个视频到 {safe_name}.md"
    else:
        # 创建新文件
        today = date.today().isoformat()
        content = f"""---
source: ai-discovery
created: {today}
status: 未处理
---

## 相关视频

{video_block}
"""
        file_path.write_text(content, encoding="utf-8")
        return f"创建 {safe_name}.md（{len(videos)} 个视频）"


def main():
    # 支持两种输入方式：文件参数 或 stdin
    if len(sys.argv) > 1:
        # 从文件读取（推荐，避免 Shell 引号冲突）
        input_path = Path(sys.argv[1])
        raw = input_path.read_text(encoding="utf-8")
    else:
        # 从 stdin 读取
        raw = sys.stdin.read()

    if not raw.strip():
        print("错误：未收到输入数据", file=sys.stderr)
        sys.exit(1)

    topics = json.loads(raw)

    # 确保目录存在
    TOPIC_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for group in topics:
        topic_name = group["topic"]
        videos = group["videos"]
        result = write_topic_file(topic_name, videos)
        results.append(result)

    # 输出摘要
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
