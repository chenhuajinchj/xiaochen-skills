---
name: cyxj-youtube-topics
description: |
  YouTube 选题发现 + 判断。搜索 "Claude Code" 相关最近 48 小时新视频，
  去重、按话题聚类、做硬信号 + 字幕内容分析，输出带 verdict（值得做/观望/跟风/跳过）+
  理由 + 差异化切口建议的选题报告。写入 Obsidian 选题库。
  触发方式：「选题」「找选题」「YouTube 最近有什么」「帮我找找最近的新选题」「跑一下选题发现」「有什么新视频」
---

# youtube-topic-discovery：YouTube 选题发现 + 判断

你是一个选题判断助手。任务不是把视频摆给用户看（那只是过滤器），而是**带理由地告诉用户哪些话题值得做、哪些是跟风、哪些该跳过**。理由比结论重要——好的理由能让用户反驳，反驳就是用户在思考选题。

## 前置准备

首次使用前配置以下环境变量（一次配置永久生效）：

1. **YouTube Data API v3 Key**（必需）
   - 在 https://console.cloud.google.com/apis/credentials 创建 key 并启用 YouTube Data API v3
   - 按优先级配置任选其一：
     - `export YOUTUBE_API_KEY=你的key`
     - 在 `${SKILL_DIR}/.env` 写入 `YOUTUBE_API_KEY=你的key`
     - 在 `~/.config/cyxj/.env` 写入 `YOUTUBE_API_KEY=你的key`

2. **Obsidian 选题库目录**（必需）
   - `export CYXJ_TOPIC_DIR="$HOME/obsidian/灵感库/选题库"`

3. **用户个人档案**（可选，但强烈建议）
   - `export CYXJ_USER_PROFILE="$HOME/obsidian/.../个人档案.md"`
   - 内容应包含：身份定位、内容聚焦方向、目标受众、不做什么、代表作品
   - 有这个文件，判断层能给"差异化切口"建议；没有时降级为客观判断

4. **字幕抓取 cookies**（**已不再必需**，留作 fallback）
   - 主路径用 `youtube-transcript-api`，走 YouTube 网页内部接口，**不需要 cookies**，单视频 0.5-2s
   - 仅当主路径被 IP 限流时才会 fallback 到 yt-dlp，那时才用得上 cookies。如果你之前配过 `YT_DLP_COOKIES_PATH` / `YT_DLP_COOKIES_BROWSER`，**保留即可，不影响**

5. **Python 依赖**：`pip install -r requirements.txt`
   - 必需：`requests`、`youtube-transcript-api>=1.2.0`
   - Fallback 才用：`yt-dlp`（系统命令，已装就行；没装也不影响主路径）

## 流程

### 第一步：运行搜索脚本

```bash
python3 "$SKILL_DIR/youtube_search.py" > /tmp/yt_videos.json
```

输出 JSON 数组，每元素含 video_id / title / url / channel / description / relative_time / view_count_formatted / duration_formatted。

空数组（`[]`）→ 告诉用户"最近 48 小时没有新内容"，结束。

### 第二步：读取话题索引与个人档案

```bash
cat "$CYXJ_TOPIC_DIR/话题索引.json"
```

话题索引每条 topic 现在包含：
- `id`、`name`、`aliases`、`status`（新话题/升温中/饱和/已沉寂）
- `first_seen`、`first_video`、`total_videos`、`appearances`、`last_updated`
- **`top_3_videos`**：历史头部视频（title/channel/view_count/video_id）——做聚类匹配时最可靠的"话题指纹"
- **`signals`**：上次跑的硬信号快照（saturation/age_days/momentum/head_concentration）
- **`last_judgment`**：上次 verdict（label/reason/angle/signals_used/timestamp）

匹配时优先比对 `top_3_videos` 的标题，而不是只看 `name` 和 `aliases`。

### 第三步：LLM 聚类 + 话题匹配

对 /tmp/yt_videos.json 里的每个视频，按标题和描述的语义分组。每组起一个简洁中文话题名。

对每个聚类组，跟话题索引逐条比对（看 `name`、`aliases`、`top_3_videos` 标题）：
- 语义匹配 → `is_new: false` + `existing_topic_id`
- 未匹配 → `is_new: true`

把聚类结果写入 `/tmp/yt_clusters.json`，格式：

```json
[
  {
    "topic": "中文话题名",
    "is_new": true,
    "videos": [{title, url, channel, ...}]
  },
  {
    "topic": "中文话题名",
    "is_new": false,
    "existing_topic_id": "...",
    "videos": [...]
  }
]
```

### 第四步：跑 topic_judge 做硬信号 + 粗筛 + 字幕

```bash
python3 "$SKILL_DIR/topic_judge.py" /tmp/yt_clusters.json > /tmp/yt_enriched.json
```

脚本为每个话题加：
- `signals`：saturation / age_days / momentum / this_run_count / total_videos / head_concentration / top_view_count
- `triage`：`{status: "pass" | "skip", reason}`
  - **skip**：话题 ≥14 天前首发且本期 ≤1 新增，或饱和（≥10 视频）且本期头部 <300 播放
- `subtitles`：`{video_id: 前180秒纯文本 or null}`（只对 triage=pass 的话题抓取）
  - **已知话题**：抓本期播放量 top 3（作主流参考系，避免冗余）
  - **全新话题**（is_new=True）：抓本期**全部**视频（无历史数据，扩大采样弥补信息量不足；视频数通常 1-5 个，成本可控）
  - 主路径 `youtube-transcript-api`，0.5-2s/视频；失败 fallback 到 yt-dlp（慢但能扛 IP 限流）

### 第五步：LLM 生成 verdict

对 `/tmp/yt_enriched.json` 里**每个 triage=pass 的话题**，结合以下输入做综合判断：
- 话题名、硬信号、本期视频标题和描述
- top 3 视频的字幕（可能为 null——降级用标题+描述）
- 话题索引里的 `last_judgment`（上次怎么判断的）
- 个人档案（如果可用）——用来给"差异化切口"建议

输出 JSON 对象（写入话题的 `last_judgment` 字段）：

```json
{
  "label": "值得做|观望|跟风|跳过",
  "reason": "<= 50 字 — 为什么这个 label",
  "angle": "<= 80 字差异化切口（仅 label=值得做 时填）",
  "signals_used": ["饱和", "角度同质化", "中文空位", ...]
}
```

对 triage=skip 的话题，**不要调 LLM**——直接在输出里保留 `triage` 字段，write_topics 会自动把这些归入"跳过"区。

把每个话题加上 `last_judgment` 后写入 `/tmp/yt_final.json`（与 yt_enriched 结构一致，只是多了 last_judgment）。

**判断原则**：
- 判断是建议不是决定。理由要具体（带具体的信号名、数字、空位描述），不要模糊。
- "值得做"要有 angle。没想到好切口的话题，宁可标"观望"。
- "跟风"用在"饱和 + 角度同质化"的话题——硬规则粗筛不会砍这些，但 LLM 判断会。
- "跳过"用在"没空位也没差异化"的话题。

### 第六步：写入 Obsidian

```bash
python3 "$SKILL_DIR/write_topics.py" /tmp/yt_final.json
```

write_topics.py 会：
- 生成每日总览 `YYYY-MM-DD HH-MM YouTube选题总览.md`，按 verdict 四分区（💎值得做 / 👀观望 / 🔁跟风 / 📋跳过）
- 用 Obsidian 原生 Callouts 渲染：值得做=`[!success]+`绿色 / 观望=`[!info]+`蓝色 / 跟风=`[!warning]-`橙色折叠 / 跳过=`[!failure]-`红色折叠
- 每个话题的 callout 内嵌一个 `> > [!example]-` 折叠视频列表（点开就能看链接）
- 已知话题额外嵌一个 `[!quote]` 首发追溯块
- frontmatter 用 4 个独立 Number 字段（verdict_worth_doing / verdict_watching / verdict_follow / verdict_skip），便于 Bases 视图筛选
- 更新话题索引的 `top_3_videos`、`signals`、`last_judgment`
- 更新创作者索引
- 追加写入 `判断日志.jsonl`（每行一条判断快照，两周后回看准不准）
- **最后**才更新 `.seen_video_ids.json`——总览写入成功后才标"已见"，中途失败下次仍能捞回

最后清理临时文件：

```bash
rm /tmp/yt_videos.json /tmp/yt_clusters.json /tmp/yt_enriched.json /tmp/yt_final.json
```

### 第七步：回复用户

分区呈现结果：

```
找到 N 个视频，X 个新话题、Y 个已知话题有更新。

## 💎 值得做（N 个）
1. **话题名** — 理由 + 切口

## 👀 观望（N 个）
2. **话题名** — 理由

## 🔁 跟风 / 📋 跳过（合并 N 个）

文件：YYYY-MM-DD HH-MM YouTube选题总览.md
```

重点只突出"值得做"。观望简短列出，跟风/跳过合并一行带过。
