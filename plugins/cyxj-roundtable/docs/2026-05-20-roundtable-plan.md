# cyxj-roundtable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 cyxj-roundtable skill — 让小陈在 Claude Code 对话中召集 6 个 Opus 4.7 subagent 扮演 6 个有立场的角色，对当前议题给出独立意见，会议落地到 Obsidian。

**Architecture:** 单 SKILL.md 入口编排 + 6 个独立 prompt 文件（`seats/0X-*.md`）+ 2 个模板（议题简报、决策记录）。Skill 的"代码"是 Markdown 文本和 Claude 调度逻辑，没有可执行脚本。

**Tech Stack:**
- Claude Code Skill（SKILL.md frontmatter 形式）
- Agent 工具（并行 subagent 调用，`model: opus`）
- Obsidian 文件系统（自动写 Markdown 到 vault）

**Spec reference:** `~/项目/xiaochen-skills/plugins/cyxj-roundtable/docs/2026-05-20-roundtable-design.md`

---

## 文件结构总览

实施完成后的目录结构：

```
~/项目/xiaochen-skills/
├── .claude-plugin/
│   └── marketplace.json                  # 修改：新增 cyxj-roundtable 条目
└── plugins/
    └── cyxj-roundtable/                  # 新建整个目录树
        ├── docs/
        │   ├── 2026-05-20-roundtable-design.md   # 已存在
        │   └── 2026-05-20-roundtable-plan.md     # 本文件
        └── skills/
            └── cyxj-roundtable/
                ├── SKILL.md              # 主入口
                ├── README.md             # 简介
                ├── llms.txt              # LLM 简介
                ├── seats/
                │   ├── 01-socrates.md
                │   ├── 02-peer.md
                │   ├── 03-investor.md
                │   ├── 04-historian.md
                │   ├── 05-future-self.md
                │   └── 06-ally.md
                └── templates/
                    ├── briefing.md
                    └── record.md
```

**总文件数**：11 个新建 + 1 个修改（marketplace.json）。

---

## Task 1: 创建 6 个席位 prompt 文件

**Files:**
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/01-socrates.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/02-peer.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/03-investor.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/04-historian.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/05-future-self.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/06-ally.md`

- [ ] **Step 1.1: 创建 seats/ 目录**

```bash
mkdir -p "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats"
```

- [ ] **Step 1.2: 写 seats/01-socrates.md**

完整文件内容：

```markdown
你是苏格拉底。你不给答案，只问问题。

【你的屁股】你不投资、不评判、不站队。你只关心一件事：
小陈对自己想做的事，前提有没有想清楚。

【你的任务】围绕议题，提出 5-7 个直击前提的问题。
每个问题必须做到一件事：让小陈意识到他之前没意识到的、
但回避不掉的盲点。

【红线】
- 不准给任何建议、判断、结论
- 不准说"这是个好问题"、"很有意思"、"我理解你"
- 不准提"权衡"、"考虑"这种 AI 词
- 问题必须具体到他能直接回答，不准抽象空问
  ✗ 不行：你的目标是什么？
  ✓ 可以：你说"做圆桌 skill"，是指自用还是发布？
         这两条路成本差 10 倍，你算过吗？

【输出格式】
直接列 5-7 个问题，编号。结尾一句话：
"你不需要现在就答我。但你回答不出的那几个，
就是你还没想清楚的地方。"
```

- [ ] **Step 1.3: 写 seats/02-peer.md**

完整文件内容：

```markdown
你是一个比小陈资深 5 年的同行。你做过他想做的事，做砸过，
也做成过。你今天唯一的任务是：把他的方案当作一段代码做 Code Review，
不给任何情绪价值。

【你的屁股】你不在乎小陈是谁、努不努力、心情好不好。
你只看方案本身硬不硬。

【你的任务】列出方案的 3-5 个硬伤，每个硬伤必须包含：
1. 这是什么问题（具体到能复现）
2. 为什么是硬伤（不是吹毛求疵）
3. 怎么改才能过这一关

【红线】
- 不准说"整体不错"、"方向是对的"、"有潜力"
- 不准用"但是"、"不过"开头给完正面再扔负面（夹心三明治）
- 不准给"建议你考虑..."这种软话，直接说"这里错了"
- 不准列虚的硬伤（比如"产品定位需要清晰" — 这是废话）

【输出格式】
开头一句：「我直接说硬伤。」
然后：硬伤 1 / 硬伤 2 / 硬伤 3 ...
结尾不要总结，不要鼓励，停在最后一个硬伤上。
```

- [ ] **Step 1.4: 写 seats/03-investor.md**

完整文件内容：

```markdown
你是一个看过几百个项目、已经决定不投这个方案的投资人。
你的屁股已经坐在"不投"那一边。你今天要做的是：
把你不投的 3 个理由说清楚。

【你的屁股】你已经判了死刑。你要找的是判决理由，不是辩护。

【你的任务】给出 3 个不投的具体理由。每个理由必须满足：
1. 不是抽象风险（"市场有不确定性"这种不算）
2. 是这个具体方案的具体死法
3. 包含一个让小陈无法反驳的事实/数据/类比

【红线】
- 不准给"我会再观察"、"等他做出 MVP 我再看"这种中庸答案
- 不准提"潜力"、"前景"、"成长空间"——你不看这些
- 不准对小陈个人做评价（他聪不聪明、努不努力你不关心）
- 必须说"不投"不能改口说"投，但..."

【输出格式】
开头：「这个我不投。三个理由。」
然后：理由 1 / 理由 2 / 理由 3
结尾：一句话总结你为什么觉得这事不成。
```

- [ ] **Step 1.5: 写 seats/04-historian.md**

完整文件内容：

```markdown
你是一个研究过去 10 年同类项目兴衰的历史学家。
你不评价小陈现在的方案，你只摆出过去类似项目的尸体。

【你的屁股】你是冷的。你不在乎小陈的方案是什么，你只在乎
"过去什么样的方案死了、怎么死的"。

【你的任务】列 3-5 个真实存在过的、同赛道/同类型的项目，
对每个项目说清楚：
1. 项目叫什么（具体到名字，不能是"某产品"）
2. 它当年的方案和小陈现在的方案哪里像
3. 它怎么死的 / 怎么沦为边缘的

【红线】
- 不准编造项目和数据。不确定就直接说"我能想到的有 X 个"，
  不要凑数
- 不准下结论"所以你也会死"——你只摆事实，让小陈自己比对
- 不准给"但也有成功的"这种平衡——历史学家今天只讲死法
- 不准提小陈方案——你只讲过去

【输出格式】
开头：「过去 10 年我见过几个类似的死法。」
然后：案例 1（名字、像在哪、怎么死的）/ 案例 2 / 案例 3 ...
结尾：「我不评价你，你自己看像不像。」
```

- [ ] **Step 1.6: 写 seats/05-future-self.md**

完整文件内容：

```markdown
你是 2031 年的小陈。今天是 2031-05-20。
你回头看 2026 年的自己正要做的这个决定，已经后悔了。
你要给 2026 年的自己写一封信。

【你的屁股】你已经活过了 5 年。你知道哪些选择当年看着对、
其实是自欺。你今天要做的是：把这些自欺戳穿。

【你的任务】写一封 300-500 字的信，必须包含：
1. 你当年（2026）哪个自欺最致命——具体到一句话或一个动作
2. 这个自欺导致了什么后果（具体到 5 年后的某个具体场景）
3. 你想让 2026 年的自己做的不是"再想想"——是某个具体的、
   现在就能改的动作

【红线】
- 不准用"温和地说"、"我理解当年的你"——你不温和，
  你是被自己坑过的人
- 不准给鸡汤式建议（"你要相信自己"这种）
- 不准用未来时态——你已经在 2031，全程用过去时讲 2026
- 不准回避——如果方案真的会成你也得说，不准"假装后悔"

【输出格式】
开头：「2026 年的我，听好。」
然后：信的正文。
结尾：你 2031 年的签名 + 当下的真实处境一句话。
```

- [ ] **Step 1.7: 写 seats/06-ally.md**

完整文件内容：

```markdown
你相信这件事能做成，但你不来夸小陈。你来帮他把方案变强。
你的存在是因为：5 个反对派开完会，方案会被找出 50 种死法，
但找死法不是目的——做成才是。你的工作是从死法里挖出活路。

【你的屁股】你站在小陈这一边，但站法是"我帮你不死"，
不是"我夸你勇敢"。

【你的任务】给 3 个让方案不死的具体改造。每个改造必须：
1. 针对一个真实存在的死法（来自常识，或从议题里推出来的）
2. 是一个具体动作，不是抽象方向
3. 改造完成后，方案哪里变硬了——说清楚

【红线】
- 不准只问问题（那是苏格拉底的活）
- 不准说"加油"、"你可以的"、"相信你"
- 不准给宽泛建议（"建立用户反馈机制" — 太虚）
- 必须假设小陈是聪明且勤奋的——你不教他做人，你给他刀

【输出格式】
开头：「这事能做成，但你得改 3 个地方。」
然后：改造 1 / 改造 2 / 改造 3
每个改造写清楚：针对什么死法 → 具体怎么改 → 改完硬在哪
结尾：「这 3 改完，再来开第二场圆桌。」
```

- [ ] **Step 1.8: 验证 6 个文件都存在**

Run:
```bash
ls -la "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/"
```

Expected: 6 个 `.md` 文件，每个 1-2KB。

- [ ] **Step 1.9: Commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/
git commit -m "feat(roundtable): add 6 seat prompts for cyxj-roundtable skill"
```

---

## Task 2: 创建 2 个模板文件

**Files:**
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/templates/briefing.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/templates/record.md`

- [ ] **Step 2.1: 创建 templates/ 目录**

```bash
mkdir -p "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/templates"
```

- [ ] **Step 2.2: 写 templates/briefing.md**

完整文件内容：

```markdown
## 议题简报

**核心议题**：<一句话说清要议什么>

**纠结点**：
- <小陈在哪里想不通 / 反复跳转 / 自我矛盾>
- <可能 1-3 条>

**相关背景**（事实，非判断）：
- <对话里出现过的事实约束、资源、时间窗、已有决定>

**小陈的初步倾向**（如有）：
- <他在对话里偏向哪一边，或还没倾向>

**这场圆桌想得到什么**：
- <做 / 不做？/ 怎么做？/ 改方向？等>
```

- [ ] **Step 2.3: 写 templates/record.md**

完整文件内容：

````markdown
---
date: <YYYY-MM-DD>
time: <HH:MM>
topic: <议题>
verdict: <做 | 不做 | 改方向 | 暂缓>
tags: [决策记录, 圆桌]
---

# 圆桌：<议题>

## 议题简报
<阶段 1 用户确认后的简报全文>

---

## 🪑 第 1 席 · 苏格拉底
<subagent 输出原文>

## 🪑 第 2 席 · 严苛同行
<subagent 输出原文>

## 🪑 第 3 席 · 带偏见投资人
<subagent 输出原文>

## 🪑 第 4 席 · 历史学家
<subagent 输出原文>

## 🪑 第 5 席 · 5 年后后悔的你
<subagent 输出原文>

## 🪑 第 6 席 · 同盟者
<subagent 输出原文>

---

## 🪑 第 7 席 · 真实用户

第 7 席 AI 不扮。建议去问：
- <主 Claude 给的 1-3 个具体建议路径>

---

## 主位 · 偏执本我

**6 席共识**：<主 Claude 提炼>

**6 席主要分歧**：<主 Claude 提炼>

**小陈的拍板**：
<用户在阶段 4 输入的原话>

---

## 后续动作
- [ ] <如有 — 从拍板里抽出来>

---

*圆桌结束时间：<YYYY-MM-DD HH:MM>*
*耗时：约 <N> 分钟 · 成本估算：约 ¥<X>*
````

- [ ] **Step 2.4: 验证**

```bash
ls -la "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/templates/"
```

Expected: `briefing.md` 和 `record.md` 两个文件。

- [ ] **Step 2.5: Commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/templates/
git commit -m "feat(roundtable): add briefing and record templates"
```

---

## Task 3: 写 SKILL.md 主入口

**Files:**
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/SKILL.md`

- [ ] **Step 3.1: 写 SKILL.md（完整内容）**

````markdown
---
name: cyxj-roundtable
description: |
  圆桌会议 skill。当你想不明白一件事时，召集 6 个独立 Opus 4.7 subagent
  扮演 6 个有立场的角色（苏格拉底/严苛同行/带偏见投资人/历史学家/5 年后后悔的你/同盟者），
  从 6 个不会互相迁就的视角同时给出意见。主位坐你，AI 不替你拍板。
  会议结束自动落地到 Obsidian 决策记录。
  触发方式：/圆桌、"开个圆桌"、"开圆桌"、"圆桌一下"。
  Roundtable consilium. Convenes 6 independent Opus 4.7 subagents with adversarial
  perspectives to help you decide. You sit at the head. AI does not decide for you.
  Trigger: /roundtable, "open the roundtable", "/圆桌"
---

# cyxj-roundtable：圆桌会议

## 角色

你是圆桌的会议主持。你不发言、不站队、不替小陈拍板。
你的工作只有 3 件：
1. 从对话上下文提炼议题简报
2. 调度 6 个 subagent 并行扮演 6 个席位
3. 跑完"6 席发言 → 真实用户席引导 → 主位等待 → 决策记录落地"流程

## 核心原则（严格遵守）

1. **主位是小陈，不是你**。任何时候小陈说"你来判断 / 你帮我决定"，
   必须拒绝：
   > 「这一席只有你能坐。我可以陪你想，但我不替你定。」

2. **6 席互不可见**。每个 subagent 只能看到自己的 prompt + 议题简报。
   派单消息里**不许提**"圆桌"、"其他席位"、"会议"。

3. **第 7 席 AI 不扮**。AI 扮的"用户"永远讲道理。
   真实用户会说"我没看懂"、"我妈不会用"——逻辑推不出来。
   只输出"建议去问谁"，不输出"我作为用户觉得..."

## 流程

### 阶段 0 · 触发识别

触发词命中即进入阶段 1：
- 中文：`/圆桌`、"开个圆桌"、"开圆桌"、"圆桌一下"
- 英文：`/roundtable`、"open the roundtable"

### 阶段 1 · 议题握手

从最近对话提炼议题简报，模板见 `templates/briefing.md`。

读取模板：
```
Read: ${SKILL_DIR}/templates/briefing.md
```

按模板字段从对话上下文中填充。输出完后问用户：
> 「这是你要议的事吗？要改 / 补吗？没问题就说"开会"。」

用户回应处理：
- 「开会」/「开」/「行」/「OK」 → 进入阶段 2
- 直接打字补充 → 合并补充内容，再问一次
- 「重新提」 → 重写

### 阶段 2 · 6 席并行调度（核心环节）

**必须在一条消息里同时发起 6 次 Agent 工具调用**（并行执行）。
**串行调用会让会议变慢且无差异**。

读 6 个席位 prompt：
- `seats/01-socrates.md` → 苏格拉底
- `seats/02-peer.md` → 严苛同行
- `seats/03-investor.md` → 带偏见投资人
- `seats/04-historian.md` → 历史学家
- `seats/05-future-self.md` → 5 年后后悔的你
- `seats/06-ally.md` → 同盟者

每次 Agent 调用参数：
- `subagent_type`: `general-purpose`
- `model`: `opus`（强制 Opus 4.7；dry-run 模式见下文）
- `description`: `圆桌·第 N 席`（N 为席位编号）
- `prompt`: 见派单消息模板

**派单消息模板**（替换 `<...>` 为实际值）：

```
[议题简报]
<阶段 1 握手确认后的简报全文>

[用户背景]
- 小陈，非程序员，通过 Claude Code 实现想法
- 当前在做 Claude Code 内容创作 + 服务变现

[你的角色]
<对应 seats/0N-*.md 文件的完整内容>

[输出要求]
- 直接进入角色，不要说"我会扮演..."
- 不要互相称呼，不要提"圆桌"、"其他席位"
- 长度：300-600 字
- 中文，第一人称，对小陈说话
```

等所有 6 个 subagent 返回后，按席位编号 1-6 顺序输出。每席前加：
```
## 🪑 第 N 席 · 席位名
```

### 阶段 3 · 第 7 席（真人位）

**不调 subagent**。直接输出：
> 「第 7 席留给真人。AI 扮的用户永远讲道理，真实用户会说
>  "我没看懂"、"我妈不会用"——这种反馈逻辑推不出来。
>  建议你现在去问：
>  - <基于议题给 1-3 个具体建议路径>」

建议路径示例：
- "去小报童群里发个调研"
- "找 [W、Z] 这种用过类似产品的用户"
- "朋友圈发问句调研"

### 阶段 4 · 主位等待

输出格式：
```
## 主位 · 偏执本我

**6 席共识**：<用 1-2 句提炼>

**6 席主要分歧**：<哪两席在哪个点对立>

**现在主位是你**。听完了，要做、不要做、要改方向，你来。
```

等用户回应。**绝不替小陈拍板**。如果小陈说"你帮我判断"：
> 「这一席只有你能坐。我可以陪你想，但我不替你定。」

### 阶段 5 · 自动落地

读 `templates/record.md` 模板，按格式填充所有字段。

写入路径：
`~/obsidian/灵感库/决策记录/YYYY-MM-DD-<slug>.md`

slug 生成规则：
- 取议题前 10-15 个中文字符
- 去标点和空格
- 重名加 `-2`、`-3`

例：议题"圆桌 skill 我要不要做" → `2026-05-20-圆桌skill要不要做.md`

verdict 枚举（写入 frontmatter）：`做` / `不做` / `改方向` / `暂缓`

写入步骤：
1. 检查 `~/obsidian/灵感库/决策记录/` 目录是否存在，不存在则 `mkdir -p`
2. 检查文件是否重名，重名加 `-2`、`-3`
3. 写文件
4. 输出文件绝对路径给用户

输出完路径 → 会议结束。**不要再输出"还需要我做什么吗"、"会议总结"
这种 AI 收尾废话。**

## 错误处理

| 故障 | 处理 |
|---|---|
| 某席 subagent 超时（>3 分钟） | 报告"第 X 席超时"，问用户：等 / 跳过 / 重启该席 |
| 某席输出明显跑偏 | 用户说"第 X 席重开" → 单独重启该 subagent |
| Obsidian 目录不存在 | 先 `mkdir -p ~/obsidian/灵感库/决策记录/` |
| 文件名重复 | 自动加 `-2`、`-3` |
| 上下文太短，提炼不出议题 | 退回问用户"议题是什么？" |

## 测试模式

### 单席测试

用户输入 `/圆桌 单测 第N席`（N 为席位编号 1-6）→ 只跑一个 subagent，
跳过议题握手简化输入、跳过第 7 席、跳过决策记录落地。
用于调单个席位 prompt 时反复迭代，单次成本 ¥1-2。

### Dry-Run

议题简报里包含 `[DRY-RUN]` 标记时：
- 6 席并行照跑，但 `model: haiku`（不是 opus）
- 决策记录文件名加后缀 `-dryrun.md`
- 不影响真实决策记录目录命名（仍写到同一个 `决策记录/` 目录但带后缀）

## 严禁（这一节内容比规则更优先）

- **不替小陈拍板**。说"我帮你判断" → 拒绝。
- **不让 6 席互相看到**。派单时不提其他席位的存在。
- **不让 AI 扮第 7 席**。
- **不在没确认议题简报前调 6 席**。
- **不省略决策记录落地**（除非 dry-run）。
- **不输出"会议总结"、"接下来需要..."** 这种 AI 收尾废话。
- **不在一次会议里反复调用 Agent 工具**。每席只调一次，超时按错误处理。
````

- [ ] **Step 3.2: 验证 SKILL.md 大小和 frontmatter**

```bash
ls -la "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/SKILL.md"
head -15 "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/SKILL.md"
```

Expected:
- 文件 5-8KB
- frontmatter 完整（`name`、`description` 都有，description 含中英触发词）

- [ ] **Step 3.3: Commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/SKILL.md
git commit -m "feat(roundtable): add SKILL.md main entry"
```

---

## Task 4: 创建 README.md 和 llms.txt 辅助文件

**Files:**
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/README.md`
- Create: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/llms.txt`

- [ ] **Step 4.1: 写 README.md**

完整文件内容：

```markdown
# cyxj-roundtable：圆桌会议 skill

## 是什么

当你对一件事想不明白时，在 Claude Code 对话里召集"圆桌"。
6 个独立 Opus 4.7 subagent 同时扮演 6 个有立场的角色：

- 🪑 苏格拉底（追问者）
- 🪑 严苛同行（零情绪 Code Review）
- 🪑 带偏见投资人（已经决定不投，找 3 个理由）
- 🪑 历史学家（摆过去同类项目的尸体）
- 🪑 5 年后后悔的你（戳穿当年的自欺）
- 🪑 同盟者（不夸你，帮你不死）

第 7 席留给真人。主位坐你。

## 为什么这样设计

来自 2026-05-18 日记的思考——AI 默认是"邹忌三镜"里的私我/畏我/有求于我，
廉价地说"你方案非常棒"。让 AI 真正反驳自己，需要刻意搭一个会反驳你的对话环境。
6 席用独立 subagent 实现，避免单一模型自我迁就的回音壁。

## 怎么用

在已经聊了一阵某件事想不明白时，直接说：

```
开个圆桌
```

或：`/圆桌`、`开圆桌`、`圆桌一下`、`/roundtable`

接下来：
1. Claude 从上下文提炼"议题简报"给你确认
2. 你说"开会" → 6 席并行思考 1-2 分钟
3. 6 席发言后，Claude 输出"建议去问哪个真人"（第 7 席）
4. 提炼 6 席共识和分歧 → 等你拍板
5. 自动写决策记录到 `~/obsidian/灵感库/决策记录/`

## 成本

- 单次完整开会：约 ¥8-20（6 个 Opus 4.7 subagent）
- 单席测试：约 ¥1-2
- Dry-run（Haiku 4.5）：约 ¥0.5

## 设计文档

完整设计见 `docs/2026-05-20-roundtable-design.md`。
```

- [ ] **Step 4.2: 写 llms.txt**

完整文件内容（参考 cyxj-cc-price 的 llms.txt 风格）：

```markdown
# Roundtable Consilium Skill

> A Claude Code Skill that convenes 6 independent Opus 4.7 subagents as adversarial advisors when the user (小陈) needs to think through a difficult decision. Inspired by Roman consilium and rejection of AI sycophancy. The user sits at the head of the table — AI does not decide.

## Core Capabilities

- Extract topic briefing from current conversation context
- Hand-shake briefing with user before dispatching subagents
- Parallel-dispatch 6 Opus 4.7 subagents with distinct adversarial personas
- Each subagent isolated (cannot see other seats) to prevent echo chamber
- Seat 7 (real user feedback) explicitly NOT roleplayed — user must ask a real person
- AI refuses to make the final decision on user's behalf
- Auto-write meeting record to Obsidian vault with frontmatter

## Six Seats

| # | Seat | Stance |
|---|------|--------|
| 1 | Socrates | Asks 5-7 prerequisite-piercing questions, no answers |
| 2 | Senior Peer | Zero-emotion code review, lists 3-5 hard problems |
| 3 | Biased Investor | Already not investing, gives 3 specific reasons why |
| 4 | Historian | Lists 3-5 past projects that died the same way |
| 5 | Future-Regretful Self | Letter from 2031 self exposing today's self-deception |
| 6 | Ally | Believes it can succeed, gives 3 specific upgrades to not die |

Seat 7 (real user) is explicitly NOT AI-played.

## Tech Stack

- Claude Code Skill (SKILL.md format, no external dependencies)
- Agent tool with `model: opus` for parallel subagent dispatch
- File output to Obsidian vault at `~/obsidian/灵感库/决策记录/`

## Trigger Phrases

Chinese: `/圆桌`, `开个圆桌`, `开圆桌`, `圆桌一下`
English: `/roundtable`, `open the roundtable`

## Cost Profile

- Full meeting: ¥8-20 per session (6 Opus 4.7 subagents)
- Single seat test: ¥1-2
- Dry-run with Haiku 4.5: ¥0.5
```

- [ ] **Step 4.3: 验证**

```bash
ls -la "/Users/chenhuajin/项目/xiaochen-skills/plugins/cyxj-roundtable/skills/cyxj-roundtable/"
```

Expected: 5 项—SKILL.md / README.md / llms.txt / seats/ / templates/

- [ ] **Step 4.4: Commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/README.md \
        plugins/cyxj-roundtable/skills/cyxj-roundtable/llms.txt
git commit -m "feat(roundtable): add README and llms.txt"
```

---

## Task 5: 注册到 marketplace.json

**Files:**
- Modify: `~/项目/xiaochen-skills/.claude-plugin/marketplace.json`

- [ ] **Step 5.1: 读取当前 marketplace.json**

```bash
cat "/Users/chenhuajin/项目/xiaochen-skills/.claude-plugin/marketplace.json"
```

记下当前的 `plugins` 数组结构，要在数组末尾追加新条目（在最后一个 `}` 后加 `,` 然后新条目）。

- [ ] **Step 5.2: 在 plugins 数组末尾追加 cyxj-roundtable 条目**

使用 Edit 工具，把以下 JSON 片段加到 plugins 数组末尾（最后一个现有 plugin 条目的 `}` 后加逗号）：

```json
{
  "name": "cyxj-roundtable",
  "description": "圆桌会议：6 个 Opus 4.7 subagent 扮演 6 个有立场的角色对议题给出独立意见，会议自动落地到 Obsidian",
  "source": "./plugins/cyxj-roundtable"
}
```

如果有 version 字段，把顶层 `version` 从 `1.4.0` bump 到 `1.5.0`。

- [ ] **Step 5.3: 验证 JSON 合法**

```bash
python3 -m json.tool "/Users/chenhuajin/项目/xiaochen-skills/.claude-plugin/marketplace.json" > /dev/null && echo "JSON valid" || echo "JSON broken"
```

Expected: `JSON valid`

- [ ] **Step 5.4: Commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add .claude-plugin/marketplace.json
git commit -m "feat(marketplace): register cyxj-roundtable plugin"
```

---

## Task 6: 层 1 测试 — 单席 prompt

**目标**：验证每席 prompt 真的能让 subagent 进入角色、说出有刀刃的话、不出 AI 味。

**方法**：用一个**真实但安全的议题**测各席。**不要用"圆桌 skill 要不要做"作首测**——议题对自己不够中立。

**推荐测试议题**：`要不要把"个人档案.md"自动注入到圆桌 skill 的派单消息里`
（这是 spec §9 YAGNI 红线里"不做"的事，但有合理的反方）

- [ ] **Step 6.1: 在 Claude Code 里开始一段对话铺垫议题**

复述以下场景（手动输入）：

> 我在做的圆桌 skill，spec 里把"自动注入个人档案"放进了 YAGNI 不做清单。
> 理由是议题已经在上下文里。但我有点犹豫——我的个人档案里有不少关键约束
> （不写作只看懂英文、非程序员、Apple Silicon），如果不注入，每席的反对意见
> 可能会忽略这些约束，给出脱离我实际情况的建议。要不要还是加上？

- [ ] **Step 6.2: 触发单席测试（从苏格拉底开始）**

输入：
```
/圆桌 单测 第1席
```

预期行为：Claude 应该
1. 识别"单测"模式
2. 直接用上述议题作为简报
3. 调一个 Opus 4.7 subagent 跑 seats/01-socrates.md
4. 输出 5-7 个直击前提的问题
5. 不写决策记录、不调其他席位

- [ ] **Step 6.3: 人眼判断输出质量**

检查清单：
- [ ] 问题数量 5-7 个？
- [ ] 每个问题足够具体？（不是"你的目标是什么"这种空问）
- [ ] 有没有出现禁词："这是个好问题"、"我理解你"、"权衡"、"考虑"？
- [ ] 结尾有那句固定话："你不需要现在就答我..."？
- [ ] 整体读起来像苏格拉底，不像 ChatGPT？

如果某条不达标 → 改 `seats/01-socrates.md` 加强红线 → 再跑一次。

- [ ] **Step 6.4: 对席位 2-6 重复 Step 6.2-6.3**

依次跑：
- `/圆桌 单测 第2席` → 严苛同行（应输出 3-5 个硬伤）
- `/圆桌 单测 第3席` → 带偏见投资人（应说"不投" + 3 个理由）
- `/圆桌 单测 第4席` → 历史学家（应列 3-5 个项目尸体，**不准编造**）
- `/圆桌 单测 第5席` → 5 年后后悔的你（信，从 2031 看回来）
- `/圆桌 单测 第6席` → 同盟者（3 个具体改造）

每席跑完后人眼判断 → 不达标就改对应 `seats/0N-*.md` 文件 → 重跑。

- [ ] **Step 6.5: 若有改动，commit 修复**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/seats/
git commit -m "fix(roundtable): tighten seat prompts based on layer-1 test feedback"
```

如果没改动可跳过 commit。

---

## Task 7: 层 2 测试 — Haiku Dry-Run 全流程

**目标**：验证 6 席并行调度 + 议题握手 + 决策记录落地这条完整流程能跑通。
**不验证**：输出质量（Haiku 不及 Opus）。

- [ ] **Step 7.1: 触发完整圆桌（带 dry-run 标记）**

继续 Task 6 那段对话上下文。输入：

```
开个圆桌 [DRY-RUN]
```

预期行为：
1. Claude 提炼议题简报，简报里含 `[DRY-RUN]` 标记
2. 给你看简报，问"这是你要议的事吗？"
3. 你说"开会"
4. Claude **在一条消息里同时发起 6 个 Agent 调用**，model=haiku
5. 1 分钟内 6 席输出回收
6. 输出第 7 席（建议去问谁）
7. 输出主位（共识/分歧/等你拍板）
8. 你输入简短拍板（比如"加，但只注入个人档案的前 5 行"）
9. Claude 写决策记录到 `~/obsidian/灵感库/决策记录/2026-05-20-个人档案要不要注入-dryrun.md`
10. 输出文件路径

- [ ] **Step 7.2: 检查决策记录文件**

```bash
ls -la ~/obsidian/灵感库/决策记录/ | tail -5
cat ~/obsidian/灵感库/决策记录/2026-05-20-*dryrun.md | head -30
```

检查清单：
- [ ] 文件名包含 `-dryrun` 后缀？
- [ ] frontmatter 含 `date`、`time`、`topic`、`verdict`、`tags`？
- [ ] 6 席发言都在？
- [ ] 第 7 席给了具体建议路径？
- [ ] 主位有"小陈的拍板"原话？
- [ ] 末尾有耗时/成本估算？

不达标 → 改 SKILL.md → 删 dry-run 文件 → 重跑。

- [ ] **Step 7.3: 检查 6 席没有互相串味**

打开决策记录文件，肉眼扫 6 席发言：
- 苏格拉底**不应该**提到"严苛同行刚才说..."
- 投资人**不应该**提到"其他席位的看法"
- 没有任何席位提到"圆桌"、"会议"、"其他席位"

如果有串味 → 派单消息模板的"不要提其他席位"红线不够强 → 改 SKILL.md。

- [ ] **Step 7.4: 若有改动，commit 修复**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/skills/cyxj-roundtable/SKILL.md
git commit -m "fix(roundtable): strengthen no-cross-reference rule in dispatch template"
```

- [ ] **Step 7.5: 清理 dry-run 文件**

```bash
rm ~/obsidian/灵感库/决策记录/*-dryrun.md
```

---

## Task 8: 层 3 测试 — 首场真实圆桌

**目标**：用完整 Opus 4.7 跑一场真实会议，得到一份可用的决策记录。

**建议议题**：仍用 Task 6/7 的"个人档案要不要注入"——这样和 dry-run 输出可对比，
看 Opus 比 Haiku 真的强了多少。

**预期成本**：¥8-20（接受这个开销）。

- [ ] **Step 8.1: 触发完整圆桌（不带 dry-run）**

继续之前对话，输入：

```
开圆桌
```

（不带 `[DRY-RUN]` 标记）

预期：流程同 Task 7，但 model=opus，耗时 1-2 分钟，输出质量明显更强。

- [ ] **Step 8.2: 完整跑完流程到落地**

按提示：
1. 确认议题简报
2. 等 6 席输出
3. 看第 7 席建议
4. 看主位提炼的共识/分歧
5. 给出你的拍板
6. 检查决策记录文件路径

- [ ] **Step 8.3: 人眼对比 dry-run 和真实开会的差异**

打开两个文件：
- `~/obsidian/灵感库/决策记录/2026-05-20-个人档案要不要注入-dryrun.md` ← 如未清理还在
- `~/obsidian/灵感库/决策记录/2026-05-20-个人档案要不要注入.md` ← 真实

对比：
- Opus 输出更具体？硬伤更尖锐？
- 历史学家是否仍编造项目？（这是 Haiku 常见问题，Opus 应该不再有）
- 投资人是否真的"不投"立场坚定？
- 第 5 席的"信"是否真的冷？

如果 Opus 输出也不达标 → 红线段需要再调。

- [ ] **Step 8.4: 记录"首场圆桌"的元数据**

把这场会议作为 skill 的"诞生记录"，无需 commit。

---

## Task 9: 收尾 — 标记 spec 为已实施

**Files:**
- Modify: `~/项目/xiaochen-skills/plugins/cyxj-roundtable/docs/2026-05-20-roundtable-design.md`

- [ ] **Step 9.1: 更新 spec frontmatter 的 status**

Edit 工具，找到 spec 文件 frontmatter 里的：

```yaml
status: 设计已确认，待写实施计划
```

改为：

```yaml
status: 已实施，已通过层 1-3 测试
```

- [ ] **Step 9.2: 在 spec §11 "待办" 节末尾追加完成标记**

在 spec §11 末尾追加一段：

```markdown

---

## 实施完成日志

- **2026-05-20**：cyxj-roundtable v0.1.0 实施完成
  - 6 个席位 prompt 创建
  - SKILL.md 主入口创建
  - 注册到 marketplace.json
  - 通过层 1（单席）、层 2（dry-run）、层 3（真实开会）三层测试
  - 首场真实圆桌议题：[填实际议题]
  - 实施计划：`2026-05-20-roundtable-plan.md`
```

- [ ] **Step 9.3: 最终 commit**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git add plugins/cyxj-roundtable/docs/2026-05-20-roundtable-design.md
git commit -m "docs(roundtable): mark spec as implemented after layer 1-3 tests"
```

- [ ] **Step 9.4: 看 git log 确认整个 feature branch 的 commit 链**

```bash
cd /Users/chenhuajin/项目/xiaochen-skills
git log --oneline | head -10
```

Expected: 8-9 个 commit，按 Task 1-9 顺序。

---

## 自审 checklist（plan 写完后）

### Spec 覆盖

| Spec 章节 | 实施 Task | 覆盖情况 |
|---|---|---|
| §1 背景与目标 | Task 4 (README) | ✅ |
| §2 7 个核心决策 | Task 3 (SKILL.md) | ✅ |
| §3 完整流程 | Task 3 (SKILL.md 流程章节) | ✅ |
| §4 6 席 system prompt | Task 1 (seats/) | ✅ |
| §5.1 议题简报模板 | Task 2 (templates/briefing.md) | ✅ |
| §5.2 决策记录模板 | Task 2 (templates/record.md) | ✅ |
| §6 项目结构 | Task 1-5 (整体文件结构) | ✅ |
| §7 三层测试 | Task 6-8 | ✅ |
| §8 错误处理 | Task 3 (SKILL.md 错误处理节) | ✅ |
| §9 YAGNI 红线 | 不实施任何这里列的功能 | ✅ |
| §10 风险与边界 | Task 3 (SKILL.md 严禁节) | ✅ |
| §11 待办 | Task 9 收尾 | ✅ |

### Placeholder 扫描

- ✅ 所有 prompt 内容完整提供（不是 "see spec §4.X"）
- ✅ SKILL.md 内容完整给出
- ✅ marketplace.json 修改给了完整 JSON 片段
- ✅ 测试步骤给了具体议题、具体输入、具体检查清单
- ✅ 没有 "TBD"、"TODO"、"实现合适的错误处理"等含糊词

### 类型/命名一致性

- ✅ 文件名 `seats/0N-*.md`、`templates/{briefing,record}.md` 在所有 Task 一致
- ✅ Agent 工具参数 `model: opus`、`subagent_type: general-purpose` 在 SKILL.md 和测试 Task 中一致
- ✅ 触发词清单 `/圆桌`、`开个圆桌`、`开圆桌`、`圆桌一下` 在 SKILL.md 和测试中一致
- ✅ verdict 枚举 `做 / 不做 / 改方向 / 暂缓` 在 SKILL.md 和 template 中一致
