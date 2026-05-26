---
name: cyxj-ai-weekly-news
description: |
  每周 AI 热点视频制作流程。承接陈宇小金 "每周 AI 热点汇总" 栏目第二期开始的端到端制作。
  按 9 步 SOP 走完：AI 出新闻候选 → 用户拍板 → 用户手抓截图 → AI 填 NEWS → AI 写旁白稿 →
  用户达芬奇录音+导字幕 SRT → 用户填 subtitleRange → AI 跑脚本生成时间码 → AI 跑素材核对 → 渲染 4K。
  每个决策点停下等用户确认，不一把梭。
  触发方式：/AI每周热点、/做下一期、/每周AI视频、「做这周的 AI 视频」「做下一期 AI 热点」
---

# cyxj-ai-weekly-news：每周 AI 热点视频制作

陈宇小金每周 AI 热点视频栏目的固化制作流程。

## 项目路径

固定项目位置：

```text
~/项目/试验区/ai-weekly-flash-video
```

后续所有命令默认在此目录下执行。

## 节目档案（先核对一遍，避免飘）

| 项目 | 当前定值 |
|------|---------|
| 视频标题/封面 | 每周 AI 热点汇总 |
| 主 IP | 陈宇小金 |
| 时长目标 | 约 3 分钟（180s ± 30s） |
| 画幅 | 1440×1080 编辑，导出升 4K 2880×2160 |
| 帧率 | 30 fps |
| 入选条数 | 8-12 条（第一期 21 条偏密，下期硬切）|
| 主 Composition | `AIWeeklyFlash43` |

如果用户在对话里说出别的栏目名（"AI 每周资讯"、"每周 AI 快讯"等），**指出名字漂移并提醒以"每周 AI 热点汇总"为准**，不要静默接受。

## 执行原则

1. **每一步执行完停下等用户确认**，不要连续跑完。
2. **决策权归用户**：选哪几条新闻、删/留哪条、旁白稿怎么改、什么时候渲染都是用户拍板。
3. **不要绕过红线**：见项目 `CLAUDE.md` 的"视觉模板设计禁区"和"流程禁区"。
4. **历史 v0 的旧文档不要照抄**：`docs/声音克隆与AI周报视频制作流程.md` 已废弃，只参考 `docs/制作SOP.md`。

## 9 步流程

> 每步标 **AI 做** 或 **用户做**。AI 在 **用户做** 的步骤上只能等、不能代办。

### Step 1 — 收集本周 AI 新闻候选（AI 做）

抓本周（周一-周日）AI 圈热点候选 ≥ 20 条，整理成一份候选清单，每条带：

- 日期（MM.DD）
- 公司 / 主体
- 标题
- 一句判断（这件事为什么重要）
- 信源链接
- 截图源 URL（首选官方页 / 推文 / 发布会截屏链接）
- region：GLOBAL / CHINA / TREND

抓取时优先用：grok-search 的 web_search（带 extra_sources=2） + Tavily web_fetch 钉事实。**关键事实需要两源交叉验证**。详见用户全局 CLAUDE.md 的"证据协议"。

候选清单输出给用户后**停**，等用户从中选 8-12 条 + 排顺序。

### Step 2 — 用户提供截图（用户做，AI 等）

用户会：

1. 从 Step 1 候选里选 8-12 条
2. **手动抓截图**（已弃用 capture-news-screenshots.mjs，AI 抓的经常不对）
3. 把截图按 `<slug>.png` 命名后放到 `public/screenshots/`

**AI 在这一步只能等**。可以提醒用户截图命名要跟 Step 3 NEWS 数组的 `image` 字段一致（小写连字符）。

### Step 3 — 填 NEWS 数组（AI 做）

按用户给的入选清单 + 截图文件名，覆盖 `src/Composition.tsx` 第 30 行起的 `NEWS` 数组。

每条结构（参考 `references/news-template.md`）：

```ts
{
  day: "05.18",
  company: "OpenAI x Dell",
  title: "Codex 进入企业混合和本地环境",
  line: "Codex 不再只是写代码工具，而是企业内部的自动化执行层。",
  source: "OpenAI",
  region: "GLOBAL",
  image: "openai-dell.png",
  subtitleRange: null as [number, number] | null,  // Step 7 填
  // 可选：video: "01_io.mp4" / tweet: "anthropic-stainless"
}
```

`subtitleRange` 先全部留 `null`，等 Step 7 用户拿到 SRT 后再填。

### Step 4 — 写旁白稿（AI 写初稿 + 用户改）

参考 `references/voiceover-template.md` 的写作规则：

- 开头：1-2 句钩子 + 本周关键词
- 主体：用 `那么第一件事 / 第二件事 / 接下来 / 同天 / 同时` 把新闻串起来
- 结尾固定句式：`OK，我是陈宇小金。每周 AI 热点，每周一期，我们下周再见`
- 字数目标：3 分钟左右 ≈ 600-660 字

写好后保存到 `docs/voiceover-script-zh.md`，让用户审阅修改。

### Step 5 — 录旁白（用户做，AI 等）

用户在达芬奇里录制旁白（或导入预录音频）。AI 等待用户确认录制完成。

### Step 6 — 达芬奇加字幕 + 导出 SRT 和 wav（用户做，AI 等）

用户在达芬奇里：

1. 字幕生成 → 校对错字（AI 转录的错字必须在这一步改掉，否则会进入最终成品）
2. 导出 SRT 到 `docs/transcripts/voiceover.fixed.srt`
3. 单独导出音频到 `public/audio/voiceover.wav`（48000Hz 双声道）

详见 `references/davinci-srt-export.md`。

AI 等用户告知"已导出"再继续。

### Step 7 — 用户填 subtitleRange + AI 跑生成脚本

用户操作：打开 `docs/transcripts/voiceover.fixed.srt`，数一下每条新闻对应第几句到第几句，回到 `src/Composition.tsx` 把每条 NEWS 的 `subtitleRange` 从 `null` 改成 `[start, end]`（1-indexed）。

不入画的新闻保留 `null`。

AI 操作：

```bash
node scripts/build-schedule.mjs
```

会生成 `src/schedule.generated.ts`，包含：

- `AUDIO_DURATION_SEC`
- `OUTRO_43_START_SEC`
- `SCHEDULE_43_RAW`
- `SUBTITLES_43_RAW`

⚠️ **第二期切换提示**：第一期 `Composition.tsx` 里这 4 个常量是手工硬编码的。第二期开始前需要把 Composition.tsx 改成 import 这 4 个值。让用户确认后再改 Composition.tsx，**不要静默替换**。

### Step 8 — 素材核对 + 起 Studio 预览（AI 做 → 用户做）

```bash
node scripts/check-assets.mjs
```

核对截图齐不齐、命名对不对、音频/SRT 在不在。失败立刻停下，回到对应步骤补。

核对通过：

```bash
npm run dev
```

让用户在浏览器里看 1-2 遍 `AIWeeklyFlash43`，重点核对：

- 画面切换是否跟旁白对得上
- 字幕是否跟声音同步
- 截图位置/内容是否对得上当前讲的新闻
- intro 和 outro 节奏

不要让用户口头确认"应该没问题"——必须真看一遍预览。

### Step 9 — 渲染 4K（AI 做）

用户预览点头后：

```bash
npx remotion render AIWeeklyFlash43 out/aiweekly-v$(date +%Y%m%d)-4k.mp4
```

文件名带日期方便归档。渲染 5-10 分钟，输出约 200MB。

渲染完简单核验：

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,nb_frames,duration \
  -of default=noprint_wrappers=1 \
  out/aiweekly-v<日期>-4k.mp4
```

期望：width=2880 / height=2160 / duration ≈ 180s ± 30s。

## 完成后的复盘动作（AI 提醒）

每期渲染完后提醒用户：

1. 这一期踩到的新坑 → 是否需要补进 `CLAUDE.md` 的"视觉模板设计禁区"或"流程禁区"
2. 是否还有第一期"遗留问题"（条数收到 8-12 没？栏目名旁白统一没？）
3. 这一期成品是否需要在 `docs/制作SOP.md` 里更新 SOP

不要主动改，**提醒就好**。改不改用户决定。

## 引用

- 详细 SOP：`~/项目/试验区/ai-weekly-flash-video/docs/制作SOP.md`
- 视觉禁区：`~/项目/试验区/ai-weekly-flash-video/CLAUDE.md`
- 第一期复盘：`~/项目/试验区/ai-weekly-flash-video/docs/每周AI资讯栏目制作记录-2026-05-24.md`（5/24 v0 验证版反思）

## 文件清单

```
${CLAUDE_PLUGIN_ROOT}/skills/cyxj-ai-weekly-news/
├── SKILL.md
└── references/
    ├── news-template.md       # NEWS 数组结构 + 字段说明
    ├── voiceover-template.md  # 旁白稿写作风格指南
    └── davinci-srt-export.md  # 达芬奇导字幕导出 SRT 的具体步骤
```
