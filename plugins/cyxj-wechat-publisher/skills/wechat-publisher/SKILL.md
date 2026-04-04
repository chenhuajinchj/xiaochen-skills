---
name: 公众号排版
description: >
  将 Obsidian Markdown 文章转换为 TATALAB 风格的高质量公众号排版。
  支持内容审查、打磨、IP 配图生成、预览确认，输出可直接粘贴到微信后台。
  触发词：发布到公众号、公众号排版、微信发布、排版文章、XCYJ 排版。
version: 1.0.0
---

# XCYJ WeChat Publisher - 陈与小金公众号排版发布 Skill

## Files

- `${CLAUDE_PLUGIN_ROOT}/theme-tatalab.css` - TATALAB 风格 CSS 主题
- `${CLAUDE_PLUGIN_ROOT}/preview-template.html` - 预览 HTML 模板
- `${CLAUDE_PLUGIN_ROOT}/package.json` - npm 依赖（仅 juice）

## Workflow

```
Obsidian .md
  -> Phase 0: 内容审查（判定是否需要扩写/去AI味/结构调整）
  -> Phase 1: 内容打磨（如需要，扩写/改写/Humanize）
  -> Phase 2: 结构分析 + 生成 HTML
  -> Phase 3: IP 配图生成 + 上传公网
  -> Phase 4: CSS 内联 + 预览确认（用户自行复制粘贴到微信后台）
```

### Phase 0: 内容审查（核心步骤）

读取 Obsidian MD 文件后，先做内容质量判定，不急着排版。

**判定维度**：
1. **完整度** — 是大纲/要点还是完整文章？如果只是几个要点，需要扩写
2. **AI 痕迹** — 是否有明显的 AI 生成特征？（夸大修辞、三段式、"值得注意的是"等）
3. **结构** — 章节划分是否合理？是否需要重组？
4. **篇幅** — 公众号文章通常 1500-3000 字，太短或太长都需要调整

**判定结果（向用户报告）**：
- **A. 内容就绪** -> 直接进入 Phase 2 排版
- **B. 需要扩写** -> 进入 Phase 1，Claude 基于要点扩写
- **C. 需要去 AI 味** -> 进入 Phase 1，调用 Humanizer-zh skill 处理
- **D. 需要扩写 + 去 AI 味** -> Phase 1 先扩写再 Humanize
- **E. 需要结构调整** -> 向用户建议章节重组方案，确认后进入 Phase 1

**关键**：判定结果必须告知用户，由用户决定是否处理，不自动执行。

### Phase 1: 内容打磨（按需执行）

根据 Phase 0 的判定结果：
- **扩写**：基于用户的要点/大纲，扩展为完整段落。保留用户原始表达，补充论据和过渡
- **去 AI 味**：调用 Humanizer-zh skill 处理，或手动调整措辞
- **结构调整**：按用户确认的方案重组

打磨完成后，输出完整 Markdown 文本给用户确认，确认后再进入排版。

### Phase 2: 结构分析 + 生成 HTML

1. 分析内容结构，按 **Auto-Recognition Rules** 匹配组件
2. 生成带 class 的 HTML（使用 `<section>` 标签，非 `<div>`）
3. 列表使用 `<p class="list-item">` 而非 `<ul><li>`（微信兼容）
4. 整体包裹在 `<section class="article">...</section>` 中

**Important**: You (Claude) are responsible for generating the HTML with correct class names. The converter only handles CSS inlining.

### Phase 3: IP 配图生成 + 上传

#### 3.1 题材识别与视觉方案匹配

先判断文章题材，自动匹配对应的视觉方案。这决定了插图和封面的场景、配色和构图方向：

| 文章题材 | 场景类型 | 配色倾向 | 构图 |
|---------|---------|---------|------|
| AI/科技 | 全息工作站、数据空间、未来城市 | 深蓝+霓虹青+品红边缘光（赛博朋克） | 居中对称，几何光环框架 |
| 读书/生活 | 咖啡馆、书房、窗边、秋日场景 | 暖琥珀金+奶油色+焦橙+深红（文艺暖调） | 三层景深（前景虚化→中景人物→背景环境） |
| 教程/干货 | 黑板、工具台、实验室、工作桌面 | 深色底+亮色重点标注（专业感） | 尺度对比，功能性构图 |
| 感悟/情感 | 自然场景、星空、海边、山顶 | 柔和渐变、淡彩（诗意感） | 负空间留白叙事 |
| 运营/商业 | 会议室、数据仪表盘、增长曲线 | 商务蓝+白+金色点缀（专业信任感） | 居中对称或黄金比例 |

将匹配到的场景、配色、构图描述融入 Gemini prompt，让每篇文章的配图氛围与内容匹配，而不是千篇一律的白底 3D 渲染。

#### 3.2 渲染风格选择

- **默认风格：3D Stylized Toon** — 保持 XCYJ 品牌 IP 一致性，适用于大多数文章
- **备选风格：水彩绘本风** — 适用于读书笔记、生活感悟、情感类文章。将小金 IP 画成柔和水彩/水墨插画风格，保留核心辨识特征（光头、蓝色卫衣、金链耳饰），但呈现为手绘绘本质感

选择哪种风格由文章气质决定：技术/教程/商业类用 3D Toon，文艺/读书/情感类可用水彩风。如果不确定，询问用户。

#### 3.3 插图生成

1. 根据每个章节主题 + 上面匹配到的视觉方案，撰写 Gemini 图片生成 prompt
2. 调用 Gemini 图片生成 API，传入 IP 参考图（`ip-reference/xiaojin-spec-sheet.png`）
3. 生成场景图（prompt 中包含题材对应的场景、配色、构图描述）
4. 上传到 Lsky Pro 图床（见下方上传流程）
5. 在 HTML 中插入 `.img-card` 组件，使用公网 URL

**IP 配图数量策略**：
- 短文章（<1500 字）且已有截图配图时，IP 配图只补无图章节，不要每章都插
- 先询问用户需要几张 IP 配图，不要自作主张

**IP 形象核心特征（每次生成必须强调）**：光头、蓝色卫衣写着"陈与小金"、金链耳饰、蓝眼睛。

**图床上传流程**（Lsky Pro - img.xiaochens.com）：
```bash
# 1. 获取 token
curl -s -X POST "https://img.xiaochens.com/api/v1/tokens" \
  -H "Content-Type: application/json" \
  -d '{"email":"chenyuxiaojin@gmail.com","password":"xxx"}'
# 返回: {"data":{"token":"1|xxxxx"}}

# 2. 上传图片
curl -s -X POST "https://img.xiaochens.com/api/v1/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@image.png"
# 返回: {"data":{"links":{"url":"https://img.xiaochens.com/i/2026/04/02/xxxxx.png"}}}
```

#### 3.4 封面生成

封面是文章的门面，必须同时包含 **IP 形象 + 文章标题文字**。

生成封面时，在 Gemini prompt 中明确要求：
- IP 形象（小金）处于画面中，场景和配色按题材视觉方案
- **文章标题文字直接渲染在封面图上**，作为设计的一部分（不是后期叠加）
- 标题文字要清晰可读，字体风格与画面氛围匹配
- 分辨率 1800x766（21:9 微信公众号封面规格）

也可使用统一封面工具：
```bash
npx -y bun ~/.agents/skills/pw-image-generation/scripts/cover-generator.ts --platform wechat --topic "文章主题" /tmp/covers
```

**API Key**：从环境变量 `GEMINI_API_KEY` 读取
**模型**：推荐 `gemini-3.1-flash-image-preview`（快且便宜），高质量需求用 `gemini-3-pro-image-preview`

### Phase 4: CSS 内联 + 预览确认

1. Run juice to inline all CSS styles:

```bash
cd ${CLAUDE_PLUGIN_ROOT} && node -e "
const juice = require('juice');
const fs = require('fs');
const css = fs.readFileSync('theme-tatalab.css', 'utf8');
const html = fs.readFileSync('/tmp/wechat-input.html', 'utf8');
fs.writeFileSync('/tmp/wechat-output.html', juice.inlineContent(html, css));
"
```

2. Read `preview-template.html`
3. Replace `{{CONTENT}}` with the juice-inlined HTML
4. Write to `/tmp/wechat-preview.html`
5. Open with Playwright, take a screenshot, show to user
6. Ask: "排版满意吗？需要调整什么？"
7. If user wants changes, go back to Phase 2


## Auto-Recognition Rules

When reading the Markdown, apply these rules to determine component mapping:

| Content Pattern | Component | Class |
|----------------|-----------|-------|
| Frontmatter has `title` and optional `subtitle` | Hero Banner | `.hero` |
| `## N. Title` or sequential `## Title` headings | Chapter Section | `.chapter` + `.chapter-num` + `.chapter-title` |
| `### Title` | Sub-heading with pill style | `h3` + `.pill` |
| Single short bold/italic sentence (<50 chars) standing alone | Quote | `.quote` |
| Multiple `**Keyword**: description` items in sequence | Knowledge Card | `.card` + `.card-item` |
| Bullet list where each item has `**Title**: description` | List Card | `.list-card` |
| Sequential `Name: "dialogue content"` patterns | Chat Bubbles | `.chat` + `.chat-item` |
| Final short emotional/inspirational sentence | Center Quote | `.center-quote` |
| `![alt](url)` image | Image Card | `.img-card` |
| Multiple consecutive images of the same category (2-4 images) | Scroll Gallery | `.img-scroll` |
| `---` horizontal rule | Divider | `hr` |
| Regular paragraph text | Body text | `p` |
| Paragraph with warning/danger/trap context, or preceded by ⚠️/💡 emoji | Callout | `.callout` + variant |
| Multiple sequential key points about rules/laws/tips in code/terminal context | Dark Card | `.card-dark` |
| Ordered steps where each has **bold title**: description | Steps List | `.steps` |
| 3-4 parallel short concepts/subcategories needing side-by-side display | Grid Cards | `.grid-cards` |
| Ordered/unordered lists (without special formatting) | List items | `p.list-item` |
| Code blocks | Code block | `pre` > `code` |
| Tables | Styled table | `table` |

## HTML Component Templates

### Hero Banner
```html
<section class="hero">
  <section class="hero-top">
    <section class="hero-tag">{TAG}</section>
    <h1>{title}</h1>
    <section class="hero-line"></section>
    <p class="hero-subtitle">{subtitle}</p>
    <section class="hero-author">
      <section class="hero-ip"><img src="https://img.xiaochens.com/i/2026/03/21/69be46623a45d.png" alt="陈与小金"></section>
      <section>
        <section class="hero-author-name">陈与小金</section>
        <section class="hero-author-tags">
          <section class="hero-author-tag">AI 编程</section>
          <section class="hero-author-tag">运营干货</section>
          <section class="hero-author-tag">效率提升</section>
        </section>
      </section>
    </section>
  </section>
</section>
```

**Hero 作者区是固定 IP 标志**，每篇文章不变。只替换 `{TAG}`、`{title}`、`{subtitle}`。

### Chapter Section
```html
<section class="chapter">
  <section class="chapter-num">01</section>
  <section class="chapter-tag">CHAPTER ONE</section>
  <section class="chapter-title">{title}</section>
</section>
```

Chapter tag English mapping (use these or similar):
- 01: CHAPTER ONE
- 02: CHAPTER TWO
- 03: CHAPTER THREE
- 04: CHAPTER FOUR
- 05: CHAPTER FIVE
- 06+: CHAPTER {N}

### Sub-heading with Pill
```html
<h3><span class="pill">{title}</span></h3>
```

### Quote (Golden Sentence)
```html
<section class="quote">
  <p>{content}</p>
</section>
```

### Knowledge Card
```html
<section class="card">
  <section class="card-title">{optional title}</section>
  <section class="card-item"><strong>{key}</strong>: {description}</section>
  <section class="card-item"><strong>{key}</strong>: {description}</section>
</section>
```

### List Card
```html
<section class="list-card">
  <p class="list-item"><strong>{title}</strong>: {description}</p>
  <p class="list-item"><strong>{title}</strong>: {description}</p>
</section>
```

### Image Card
```html
<section class="img-card">
  <img src="{url}" alt="{alt}">
  <section class="img-caption">{alt text as caption}</section>
</section>
```

### Scroll Gallery (横向滑动图片组)
```html
<section class="img-scroll">
  <section class="img-scroll-track">
    <section class="img-scroll-item">
      <img src="{url1}" alt="{alt1}">
      <section class="img-caption">{caption1}</section>
    </section>
    <section class="img-scroll-item">
      <img src="{url2}" alt="{alt2}">
      <section class="img-caption">{caption2}</section>
    </section>
    <section class="img-scroll-item">
      <img src="{url3}" alt="{alt3}">
      <section class="img-caption">{caption3}</section>
    </section>
  </section>
  <p class="img-scroll-hint">← 左右滑动查看 →</p>
</section>
```

适用场景：多张同类截图（如 Notion 截图、对比图等），避免竖排堆叠占据过多篇幅。

### Chat Bubbles (Table-based for WeChat compatibility)
```html
<table class="chat-table" cellpadding="0" cellspacing="0">
  <tr>
    <td class="avatar-cell">
      <section class="avatar">{first letter}</section>
    </td>
    <td>
      <section class="chat-name">{name}</section>
      <section class="chat-bubble">{content}</section>
    </td>
  </tr>
  <tr>
    <td class="avatar-cell">
      <section class="avatar">{first letter}</section>
    </td>
    <td>
      <section class="chat-name">{name}</section>
      <section class="chat-bubble">{content}</section>
    </td>
  </tr>
</table>
```

### Center Quote (Ending)
```html
<section class="center-quote">{content}</section>
```

### Footer Card (固定 IP 标志)
```html
<section class="footer-card">
  <section class="footer-author">我是<strong>陈与小金</strong></section>
  <section class="footer-desc">祝你身体健康，永远平安。<br>祝你 Token 无限，永远自由。</section>
  <section class="footer-sign">— {日期} —</section>
  <section class="footer-thanks">THANKS FOR READING</section>
</section>
```

**Footer 是固定 IP 标志**，祝福语不变，只替换 `{日期}`（格式：`2026.03.21`）。

### Callout (Functional Tip / Warning)
```html
<section class="callout callout-warn">
  <section class="callout-title">⚠️ 危险陷阱：均值回归</section>
  <p>内容文字...</p>
</section>
```

Variants:
- Default (`.callout`): 蓝色左边框 + 浅蓝底，一般提示
- Warning (`.callout-warn`): 琥珀色左边框 + 浅黄底，陷阱/危险
- Tip (`.callout-tip`): 绿色左边框 + 浅绿底，最佳实践

与 `.quote` 的区别：quote 是金句/引用（偏文学感），callout 是功能性提示（偏信息感），callout 带标题行。

### Dark Card (Terminal / Core Rules)
```html
<section class="card-dark">
  <section class="card-dark-title">Skills 避坑与高阶法则</section>
  <p class="card-dark-item">➜ 不要安装太多。选项越多越难触发。</p>
  <p class="card-dark-item">➜ 用斜杠手动触发最可靠。</p>
</section>
```

### Steps List (Numbered Steps)
```html
<table class="steps" cellpadding="0" cellspacing="0">
  <tr>
    <td class="step-num-cell"><section class="step-num">1</section></td>
    <td><p class="step-text"><strong>学会写清晰具体的提示词。</strong> 围绕目标去写具体功能。</p></td>
  </tr>
  <tr>
    <td class="step-num-cell"><section class="step-num">2</section></td>
    <td><p class="step-text"><strong>学会评估输出。</strong> 你得知道好的长什么样。</p></td>
  </tr>
</table>
```

### Grid Cards (Parallel Concepts)
```html
<table class="grid-cards" cellpadding="0" cellspacing="0">
  <tr>
    <td class="grid-card">
      <section class="grid-card-tag">01</section>
      <section class="grid-card-title">多终端同项目</section>
      <p class="grid-card-desc">开两到十个终端同时干活。</p>
    </td>
    <td class="grid-card">
      <section class="grid-card-tag">02</section>
      <section class="grid-card-title">Worktree</section>
      <p class="grid-card-desc">不同分支各自干活再合并。</p>
    </td>
  </tr>
  <tr>
    <td class="grid-card">
      <section class="grid-card-tag">03</section>
      <section class="grid-card-title">Agent + Worktree</section>
      <p class="grid-card-desc">主窗口生成 sub-agent。</p>
    </td>
    <td class="grid-card">
      <section class="grid-card-tag">04</section>
      <section class="grid-card-title">Agent Team</section>
      <p class="grid-card-desc">终极形态，自动协调。</p>
    </td>
  </tr>
</table>
```

奇数项处理：如果只有 3 个卡片，最后一行只放 1 个 `<td class="grid-card">`，另一个 `<td>` 留空。

### Divider
```html
<hr>
```

## Editorial Mindset

你是杂志排版编辑，不是 Markdown 转 HTML 的翻译器。每篇文章结构不同，组件选择靠编辑判断，不靠固定规则。

**核心思考流程（逐章扫一遍）**：
1. **读者此刻的情绪是什么？** 刚读完三段密集论述？需要视觉喘息点
2. **这段内容的最佳呈现形式是什么？** 同样是三个要点，知识卡片（`.card`）强调学习感，列表卡片（`.list-card`）强调并列感——选哪个取决于上下文语气
3. **这句话值不值得单独拎出来？** 引用卡片（`.quote`）要挑有画面感、有冲击力的金句，不要挑总结性的废话。读者扫到引用卡片时会停下来——你要对得起这个停顿
4. **长章节是否需要内部分隔？** 超过 4 段的章节考虑用药丸标签（`.pill`）切分子主题，打破视觉单调
5. **加粗用在哪？** 只点关键词（2-4 个字），不要加粗整句话。加粗是手指点一下的力度，不是一拳打过去

**节奏公式**：密集文字（2-3 段）→ 视觉组件喘气 → 密集文字 → 视觉组件 → ...
- 避免连续 4+ 段纯文字
- 避免连续 2 个视觉组件紧挨（会显得碎）

**铁律**：
- 文字一字不动——只改 HTML 标签结构，原文整段搬运，不能缩写、改词、调顺序
- 排版是为内容服务的，不是为了好看而好看

## WeChat Compatibility Notes

- All styles MUST be inlined via juice (WeChat strips `<style>` tags)
- Use `<table>` for chat bubbles instead of flex layout
- Avoid CSS pseudo-elements (::before, ::after) - use real HTML elements
- `box-shadow` and `border-radius` work in modern WeChat
- External images in `<img src>` will be auto-fetched by WeChat CDN when pasted
- `linear-gradient` works in WeChat for backgrounds
- Do NOT use `position: absolute/fixed` - WeChat may strip these
- Keep all widths relative (%, auto) - avoid fixed px widths except for small elements
- Use `<section>` instead of `<div>` - better semantic structure
- Use `<p class="list-item">` instead of `<ul><li>` for lists - more reliable rendering in WeChat
- Do NOT use `<thead>`, `<tbody>`, `<caption>` in tables - WeChat renders each as a separate empty table. Only use `<table><tr><th/td>` three-level structure
- 上传图片到 Lsky Pro 图床 `img.xiaochens.com`，通过 API 获取公网 URL
- 预览 HTML 用 `open` 命令打开系统浏览器，Playwright MCP 不支持 `file://` 协议
- 封面分辨率已更新为 1800x766（cover-spec.json），不要改回低分辨率
- 最终产出是预览 HTML + 复制按钮，用户自行复制粘贴到微信后台发布

