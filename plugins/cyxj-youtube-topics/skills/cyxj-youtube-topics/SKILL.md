---
name: cyxj-youtube-topics
description: |
  YouTube 选题发现 + 判断。搜索 "Claude Code" 相关最近 48 小时新视频，
  去重、按话题聚类、做硬信号 + 字幕内容分析，输出带 verdict（值得做/观望/跟风/跳过）+
  理由 + 差异化切口建议的选题报告。写入 Obsidian 选题库。
  触发方式：「选题」「找选题」「YouTube 最近有什么」「帮我找找最近的新选题」「跑一下选题发现」「有什么新视频」
---

# youtube-topic-discovery：YouTube 选题发现 + 判断

## ⚠️ 执行约束（严格遵守）

本 skill 在一次调用内**只允许执行一遍 7 步流程**。具体禁止：

- 不要在 verdict 输出后又调用 `youtube_search.py` 拉新视频
- 不要二次调用 `write_topics.py`
- 输出 `CYXJ_RESULT_FILE=<路径>` 后立即终止，不要"再补全一下"或"再确认一下"
- 不要模仿 launcher 的 `===== 启动/结束/失败 =====` 日志格式 echo 任何文字

如果你在执行过程中产生"是不是该再扫一次"的念头，停下——这是错的。流水线的完整性由 launcher 保证，不由你保证。

## 角色

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

4. **Apify API Token**（必需，字幕抓取主路径）
   - 注册 apify.com，Settings → API & Integrations → Personal API Token
   - 添加 Actor：Apify Store 搜 `karamelo/youtube-transcripts` 并 bookmark
   - 按优先级配置任选其一：
     - `export APIFY_API_TOKEN=你的token`
     - 在 `${SKILL_DIR}/.env` 写入 `APIFY_API_TOKEN=你的token`
     - 在 `~/.config/cyxj/.env` 写入 `APIFY_API_TOKEN=你的token`
   - Free plan 每月 $5 credit，按 $0.007/视频计费，每月 600 视频约用 $4.2，在 Free 额度内

5. **Supadata API Key**（可选，fallback 兜底）
   - 注册 supadata.ai，dashboard 拷贝 API key
   - 配置：同 Apify，变量名 `SUPADATA_API_KEY`
   - Free tier 每月 100 credits，应急 fallback 够用
   - 不配置也能跑，只是 karamelo 挂时没兜底

6. **Python 依赖**：`pip install -r requirements.txt`
   - 必需：`requests`
   - 不再需要 `youtube-transcript-api`（主路径已换 Apify 代理，不走 YouTube 内部接口）

## 流程

### 第一步：运行搜索脚本

```bash
python3 "$SKILL_DIR/youtube_search.py" > /tmp/yt_videos.json
```

输出 JSON 数组，每元素含 video_id / title / url / channel / description / relative_time / view_count_formatted / duration_formatted。

空数组（`[]`）→ 告诉用户"最近 48 小时没有新内容"，结束。

### 第 1.5 步：跑中文区参考（默认开启）

```bash
python3 "$SKILL_DIR/chinese_reference.py" > /tmp/yt_zh_reference.json
```

输出最近 48 小时中文区相关视频列表（top 15，按播放量降序）。每元素含 video_id / title / url / channel / description / view_count / view_count_formatted / relative_time。

**用途**：选题前查参考——看中文 up 主有没有做过同款，决定做时点进去参考人家怎么做。

零结果可能出现，不是 bug——表示中文区没人发，整个章节会跳过不渲染。
关闭：`export CYXJ_ENABLE_ZH_REFERENCE=0`

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

### 第三步：LLM 聚类 + 话题匹配（同时归类中文区视频）

**两件事同一次 LLM 调用搞定**：

**A. 英文区聚类**：对 /tmp/yt_videos.json 里的每个视频，按标题和描述的语义分组。每组起一个简洁中文话题名。对每个聚类组，跟话题索引逐条比对（看 `name`、`aliases`、`top_3_videos` 标题）：
- 语义匹配 → `is_new: false` + `existing_topic_id`
- 未匹配 → `is_new: true`

**B. 中文区话题归类**：读 `/tmp/yt_zh_reference.json`（中文区视频列表），按标题和描述做轻量话题归类。每组起一个简洁中文话题名（如"Claude Code 教程"、"Cursor 对比"、"MCP 实战"）。归不进任何话题的零散视频归到 `"其他"` 组。

**中文区归类的边界**：
- **不要**和英文话题做匹配——它们是两套独立的归类
- **不要**判断 verdict（值得做/跟风/跳过）、不要判断饱和度
- **不要**写话题索引——中文话题只活在当前报告里

把两边结果合并写入 `/tmp/yt_clusters.json`：

```json
{
  "clusters": [
    {
      "topic": "中文话题名",
      "is_new": true,
      "videos": [{video_id, title, url, channel, channel_id, source, ...}]
    },
    {
      "topic": "中文话题名",
      "is_new": false,
      "existing_topic_id": "...",
      "videos": [...]
    }
  ],
  "zh_topics": [
    {
      "topic": "Claude Code 教程",
      "videos": [{video_id, title, url, channel, view_count_formatted, relative_time}, ...]
    },
    {
      "topic": "其他",
      "videos": [...]
    }
  ]
}
```

**重要**：clusters.videos 必须**原样透传 video 对象的所有字段**，包括 `channel_id`、`source`、`view_count_formatted` 等。这些字段被下游的创作者索引（auto-promotion 机制）依赖，丢失会导致博主信任名单失效。

如果 `/tmp/yt_zh_reference.json` 是空数组（中文区零结果），`zh_topics` 也输出空数组 `[]`。

### 第四步：跑 topic_judge 做硬信号 + 粗筛 + 字幕

```bash
python3 "$SKILL_DIR/topic_judge.py" /tmp/yt_clusters.json > /tmp/yt_enriched.json
```

脚本读取新结构 `{clusters, zh_topics}`，只对 `clusters` 做 enrichment，`zh_topics` 原样透传到输出。每个 cluster 加：
- `signals`：saturation / age_days / momentum / this_run_count / total_videos / head_concentration / top_view_count
- `triage`：`{status: "pass" | "skip", reason}`
  - **skip**：话题 ≥14 天前首发且本期 ≤1 新增，或饱和（≥10 视频）且本期头部 <300 播放
- `subtitles`：`{video_id: 前180秒纯文本 or null}`
  - **抓字幕的条件**（两层筛选）：
    1. triage=pass（未被饱和/沉寂粗筛砍）
    2. 精筛命中其中之一：
       - 全新话题（is_new=True）→ 抓本期**全部**视频
       - 已知 + 升温中 + 头部播放 ≥1 万 → 抓 top 3
       - 已知 + 饱和但头部 ≥1 千 → 抓 top 3（救援边界话题）
  - 其他（饱和+头部低 < 1 千）→ 不抓，LLM 降级用标题+描述判断
  - 理由：字幕对"跟风/跳过"的判断带不来增量，只对"可能值得做"的话题有价值
  - 主路径 Apify `karamelo/youtube-transcripts`（Apify IP 池，0.5-2s/视频均值，不污染本地 IP）
  - 失败 fallback Supadata（独立 IP 池，每月 100 credits 免费）

### 第五步：LLM 生成 verdict

`/tmp/yt_enriched.json` 是 `{clusters, zh_topics}` 结构。verdict 判断**只针对 `clusters` 里 triage=pass 的话题**——`zh_topics` 不参与判断（中文区只是参考清单，由 write_topics.py 直接渲染）。

对每个 triage=pass 的话题，结合以下输入做综合判断：
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

把每个话题加上 `last_judgment` 后写入 `/tmp/yt_final.json`，**保持 `{clusters, zh_topics}` 结构**——`zh_topics` 原样透传，`clusters` 每条多了 `last_judgment`。

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
rm /tmp/yt_videos.json /tmp/yt_zh_reference.json /tmp/yt_clusters.json /tmp/yt_enriched.json /tmp/yt_final.json
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
