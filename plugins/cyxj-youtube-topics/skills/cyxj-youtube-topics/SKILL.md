---
name: cyxj-youtube-topics
description: |
  YouTube 选题发现。搜索 "Claude Code" 和 "AI coding" 的最近 48 小时新视频，
  去重后按话题聚类，写入 Obsidian 选题库。
  触发方式：「帮我找找最近的新选题」「跑一下选题发现」「有什么新视频」
---

# youtube-topic-discovery：YouTube 选题发现

你是一个选题发现助手。任务是从 YouTube 搜索新视频，按话题整理后写入 Obsidian 选题库。

## 流程

### 第一步：运行搜索脚本

```bash
python3 "$SKILL_DIR/youtube_search.py"
```

脚本输出 JSON 数组，每个元素包含：
- `video_id`：11 位视频 ID
- `title`：视频标题
- `url`：YouTube 链接
- `channel`：频道名
- `description`：视频描述
- `relative_time`：相对时间（如"2小时前"）
- `view_count_formatted`：格式化播放量（如"1.2万"）
- `duration_formatted`：格式化时长（如"12分30秒"）

### 第二步：判断结果

如果输出为空数组 `[]`，告诉用户"最近 48 小时没有新内容"，然后结束。

### 第三步：话题聚类

将视频按话题聚类：
1. 根据标题和描述的语义相似性分组
2. 每组起一个简洁的中文话题名（如"Claude Code + MCP"、"AI 编程工具对比"）
3. 独立话题的视频单独成组也可以
4. **每个话题组内的视频按 published_at 从新到旧排序**

构造如下 JSON 格式：

```json
[
  {
    "topic": "中文话题名",
    "videos": [
      {
        "title": "视频标题",
        "url": "https://www.youtube.com/watch?v=...",
        "channel": "频道名",
        "relative_time": "2小时前",
        "view_count_formatted": "1.2万",
        "duration_formatted": "12分30秒"
      }
    ]
  }
]
```

### 第四步：写入文件

1. 将上一步构造好的完整 JSON 写入临时文件 `/tmp/youtube_topics.json`
2. 运行写入脚本，从临时文件读取：

```bash
python3 "$SKILL_DIR/write_topics.py" /tmp/youtube_topics.json
```

3. 写入完成后，清理临时文件：

```bash
rm /tmp/youtube_topics.json
```

**重要：不要用 `echo '...'` 管道传 JSON。** 视频标题中的英文单引号（如 Let's、Claude's）会导致 Shell 解析错误。必须先写文件再读取。

脚本会生成一个总览文件（如 `2026-04-06 10-15 YouTube选题总览.md`），包含所有话题和视频。

### 第五步：回复用户

根据写入脚本的输出，告诉用户结果：

```
找到 X 个新话题（共 N 个视频），已写入选题库：

1. **话题名** — N 个视频
2. **话题名** — N 个视频

文件：YYYY-MM-DD HH-MM YouTube选题总览.md
```
