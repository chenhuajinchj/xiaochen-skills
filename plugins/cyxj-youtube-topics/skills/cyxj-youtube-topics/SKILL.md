---
name: cyxj-youtube-topics
description: |
  YouTube 选题发现。搜索 "Claude Code" 相关的最近 48 小时新视频，
  去重后按话题聚类，跟话题索引匹配后分层写入 Obsidian 选题库。
  支持跨天话题追踪：自动识别已知话题的翻版视频，追溯首发视频，标注话题生命周期状态。
  触发方式：「选题」「找选题」「YouTube 最近有什么」「帮我找找最近的新选题」「跑一下选题发现」「有什么新视频」
---

# youtube-topic-discovery：YouTube 选题发现

你是一个选题发现助手。任务是从 YouTube 搜索新视频，跟已有话题索引做语义匹配，分层整理后写入 Obsidian 选题库。

核心目标：**帮用户快速区分"真正的新话题"和"已知话题的翻版"**，而不是每次都平铺一堆看起来都很新但其实大部分都是旧话题换了个博主讲的内容。

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

### 第三步：读取话题索引

读取选题库中的话题索引文件：

```bash
cat ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/灵感库/选题库/话题索引.json
```

- 如果文件存在，解析其中的 `topics` 数组，了解所有已知话题及其别名
- 如果文件不存在（首次运行），当作空索引处理——所有话题都是新话题

话题索引的结构（仅供参考，帮你理解已知话题的信息）：
```json
{
  "topics": [
    {
      "id": "obsidian-knowledge-mgmt",
      "name": "Claude Code + Obsidian 知识管理",
      "aliases": ["Obsidian 第二大脑", "知识库与 Obsidian"],
      "status": "饱和",
      "first_seen": "2026-04-10",
      "first_video": {
        "title": "Building My Own Knowledge Management System...",
        "url": "https://...",
        "channel": "Allie K Miller"
      },
      "total_videos": 8,
      "appearances": 4,
      "last_updated": "2026-04-13"
    }
  ]
}
```

### 第四步：话题聚类 + 语义匹配

这是最关键的一步。先把视频按话题聚类，然后判断每个话题是新的还是已知的。

**聚类规则：**
1. 根据标题和描述的语义相似性分组
2. 每组起一个简洁的中文话题名
3. 独立话题的视频单独成组也可以
4. 每个话题组内的视频按播放量从高到低排序

**语义匹配规则：**
对每个聚类出的话题，跟话题索引中的已知话题比对：
- 比较话题名、别名，以及首发视频的标题
- **语义相同就算匹配**——"Obsidian 第二大脑"和"Claude Code + Obsidian 知识管理"是同一个话题
- 如果匹配上了，标记 `is_new: false` 并填入 `existing_topic_id`
- 如果没匹配上任何已知话题，标记 `is_new: true`

构造如下 JSON 格式：

```json
[
  {
    "topic": "中文话题名",
    "is_new": true,
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
  },
  {
    "topic": "中文话题名",
    "is_new": false,
    "existing_topic_id": "obsidian-knowledge-mgmt",
    "videos": [...]
  }
]
```

### 第五步：写入文件

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

脚本会：
- 生成每日总览文件（分层呈现：新话题 / 升温中 / 仅记录）
- 自动更新话题索引（新话题写入，已知话题更新计数和状态）

### 第六步：回复用户

根据写入脚本的输出，分层告诉用户结果：

```
找到 N 个视频，其中 X 个新话题、Y 个已知话题有更新：

## 新发现的话题
1. **话题名** — N 个视频（值得关注）

## 升温中 / 饱和的话题
2. **话题名** — 本期 +N 个视频，累计 M 个（首发于 YYYY-MM-DD）

文件：YYYY-MM-DD HH-MM YouTube选题总览.md
```

重点突出新话题，让用户一眼看到什么是真正值得关注的。
