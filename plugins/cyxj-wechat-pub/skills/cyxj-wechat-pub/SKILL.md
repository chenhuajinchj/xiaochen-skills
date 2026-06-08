---
name: cyxj-wechat-pub
description: >
  将 Obsidian Markdown 文章转换为高质量公众号排版，内置 3 套 CSS 主题可选：
  TATALAB 蓝（默认）、炭黑暖金（深度/商务）、暖橙编辑（编辑/海报风）。
  支持内容审查、打磨、IP 配图生成、预览确认，输出可直接粘贴到微信后台。
  触发词：发布到公众号、公众号排版、微信发布、排版文章、XCYJ 排版。
version: 1.0.0
---

# XCYJ WeChat Publisher - 陈与小金公众号排版发布 Skill

## Files

- `${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub/theme-tatalab.css` - TATALAB 蓝色风格 CSS 主题（默认）
- `${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub/theme-noir-gold.css` - 炭黑 + 暖金风格 CSS 主题（深度内容/商务调性）
- `${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub/theme-orange-editorial.css` - 暖橙 × 米黄编辑/海报风 CSS 主题（杂志感长稿）
- `${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub/preview-template.html` - 预览 HTML 模板
- `${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub/package.json` - npm 依赖（仅 juice）

## Theme 选择

排版前先决定用哪个主题（默认 tatalab）：

| 主题文件 | 风格 | 适用题材 |
|---------|------|---------|
| `theme-tatalab.css` | 蓝色商务感（Material Blue 系：#1565C0 / #1976D2 / #BBDEFB） | AI 编程 / 运营干货 / 教程效率类，活泼亲和 |
| `theme-noir-gold.css` | 炭黑 + 暖金沉稳感（#26262A 炭灰 Hero + #8A6D1A 金棕强调 + #FAF6EC 米黄引用块） | AI 行业观察 / 深度分析 / 长稿，沉稳权威 |
| `theme-orange-editorial.css` | 暖橙 × 米黄编辑/海报风（#E8763C 橙 + #F2E6CC 米黄 + #2A1F18 深棕 + Bebas Neue + 2px 描边 + 6px 实心阴影 + 网点底纹） | AI 行业观察 / 大事件解读 / 海报式长稿，杂志/印刷感强 |

调用 juice 时把 `theme-tatalab.css` 替换成想要的主题文件名即可，其他流程不变。Phase 0 内容审查时顺便判定主题：技术/教程类默认 tatalab；行业观察/深度分析/商业评论类问用户是 noir-gold 还是 orange-editorial（orange-editorial 适合需要强视觉冲击、有数据 + 时间线 + 关键词 + 结论金句的长稿；noir-gold 适合更克制的深度评论）。

**orange-editorial 主题的强制结构约束**（见下方 Phase 2 章节，必须遵守，否则公众号会出白色断层）：
- 整篇文章（含 hero）必须包在**一个** `<section class="article">` 内
- 章节之间用 `<section class="spacer"></section>` 占位，不要用 margin
- 禁止用 `position: absolute`、`writing-mode: vertical-rl`、`transform: rotate(...)`

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

将匹配到的场景、配色、构图描述融入图片生成 prompt，让每篇文章的配图氛围与内容匹配，而不是千篇一律的白底 3D 渲染。

#### 3.2 渲染风格选择

- **默认风格：3D Stylized Toon** — 保持 XCYJ 品牌 IP 一致性，适用于大多数文章
- **备选风格：水彩绘本风** — 适用于读书笔记、生活感悟、情感类文章。将小金 IP 画成柔和水彩/水墨插画风格，保留核心辨识特征（光头、蓝色卫衣、金链耳饰），但呈现为手绘绘本质感

选择哪种风格由文章气质决定：技术/教程/商业类用 3D Toon，文艺/读书/情感类可用水彩风。如果不确定，询问用户。

#### 3.3 图片生成引擎（GPTIMG2 / gpt-image-2）

所有 IP 配图（插图 + 封面）统一走 **gpt-image-2 @ GPTIMG2 中转站**（OpenAI 兼容协议）。

**凭据来源**：
> `GPTIMG2_BASE_URL`（= `https://api.chatgpt-code.com`，**末尾没有 `/v1`**）和 `GPTIMG2_API_KEY` 从环境变量读取。
> 如果环境变量未设置，先 `set -a; source ~/项目/自己的应用/密钥存储/.env; set +a` 加载，再继续。
> 如果文件里没这两个 key，提示用户加。

**模型**：`gpt-image-2`（中文标题渲染准确率高，适合封面直接出字）。

**两个端点（按是否带 IP 参考图选）**：
- **带 IP 参考图（保小金形象一致）→ `{base}/v1/images/edits`**（multipart 表单，`image` 字段传 `ip-reference/xiaojin-spec-sheet.png`）。IP 配图默认走这个端点。
- **纯文生图（不需要小金形象，如纯场景图）→ `{base}/v1/images/generations`**（JSON body）。

**出图方式**：请求带 `response_format=url`，拿到返回 JSON 里的图片 url 后**先 `curl` 下载落地到本地临时文件**，再走下方「图床上传流程」上传公网。不要直接把中转站 url 写进 HTML（可能过期）。

**分辨率：默认 2K 出图**（公众号配图清晰度需要）。按构图比例选 `size`：
| 比例 | 用途 | `size` |
|------|------|--------|
| 16:9 | 横图配图（默认） | `2560x1440` |
| 4:3 | 横图配图（偏方） | `2048x1536` |
| 9:16 | 竖图配图 | `1440x2560` |

封面是 21:9 特殊规格，见 3.4。

**curl 示例 A — 带 IP 参考图（`/v1/images/edits`，IP 配图走这个）**：

```bash
set -a; source ~/项目/自己的应用/密钥存储/.env; set +a   # 没设环境变量时先加载
SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub"

curl -s -X POST "${GPTIMG2_BASE_URL}/v1/images/edits" \
  -H "Authorization: Bearer ${GPTIMG2_API_KEY}" \
  -F "model=gpt-image-2" \
  -F "image=@${SKILL_DIR}/ip-reference/xiaojin-spec-sheet.png" \
  -F "prompt=小金（光头、蓝色卫衣写着\"陈与小金\"、金链耳饰、蓝眼睛）站在全息工作站前，深蓝+霓虹青赛博朋克配色，居中对称构图，3D Stylized Toon 风格" \
  -F "size=2560x1440" \
  -F "n=1" \
  -F "response_format=url"
# 返回: {"data":[{"url":"https://.../xxxx.png"}]}
```

**curl 示例 B — 纯文生图（`/v1/images/generations`，无需小金形象时）**：

```bash
set -a; source ~/项目/自己的应用/密钥存储/.env; set +a

curl -s -X POST "${GPTIMG2_BASE_URL}/v1/images/generations" \
  -H "Authorization: Bearer ${GPTIMG2_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "暖琥珀金+奶油色的文艺暖调咖啡馆窗边场景，三层景深，柔和光线，水彩绘本风",
    "size": "2560x1440",
    "n": 1,
    "response_format": "url"
  }'
# 返回: {"data":[{"url":"https://.../xxxx.png"}]}
```

**拿到 url 后下载落地**：

```bash
IMG_URL=$(curl -s ... | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['url'])")
curl -s -o /tmp/wechat-illust-1.png "$IMG_URL"
# 然后把 /tmp/wechat-illust-1.png 走下方图床上传流程
```

**插图生成步骤**：

1. 根据每个章节主题 + 上面匹配到的视觉方案，撰写 gpt-image-2 图片生成 prompt
2. 调用 `{base}/v1/images/edits` 端点，传入 IP 参考图（`ip-reference/xiaojin-spec-sheet.png`），用上面的 curl 示例 A；prompt 中包含题材对应的场景、配色、构图描述
3. 从返回 JSON 取 `data[0].url`，`curl` 下载到本地临时文件
4. 上传到 Lsky Pro 图床（见下方上传流程）
5. 在 HTML 中插入 `.img-card` 组件，使用图床返回的公网 URL

**IP 配图数量策略**：
- 短文章（<1500 字）且已有截图配图时，IP 配图只补无图章节，不要每章都插
- 先询问用户需要几张 IP 配图，不要自作主张

**IP 形象核心特征（每次生成必须强调）**：光头、蓝色卫衣写着"陈与小金"、金链耳饰、蓝眼睛。

**图床上传流程**（Lsky Pro - img.xiaochens.com）：

> 图床凭证从 `~/项目/自己的应用/密钥存储/.env` 读取（变量名 `LSKY_EMAIL` / `LSKY_PASSWORD`）。
> 如果环境变量未设置，先 `set -a; source ~/项目/自己的应用/密钥存储/.env; set +a` 加载，再继续。
> 如果文件里没这两个 key，提示用户加。

```bash
# 1. 获取 token
curl -s -X POST "https://img.xiaochens.com/api/v1/tokens" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$LSKY_EMAIL\",\"password\":\"$LSKY_PASSWORD\"}"
# 返回: {"data":{"token":"1|xxxxx"}}

# 2. 上传图片
curl -s -X POST "https://img.xiaochens.com/api/v1/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@image.png"
# 返回: {"data":{"links":{"url":"https://img.xiaochens.com/i/2026/04/02/xxxxx.png"}}}
```

#### 3.4 封面生成

封面是文章的门面，必须同时包含 **IP 形象 + 文章标题文字**。

封面同样走 3.3 的 GPTIMG2 引擎和凭据。因为封面必须含小金形象，**用 `{base}/v1/images/edits` 端点**（带 IP 参考图，curl 示例 A），在 prompt 中明确要求：
- IP 形象（小金）处于画面中，场景和配色按题材视觉方案
- **文章标题文字直接渲染在封面图上**，作为设计的一部分（不是后期叠加）。gpt-image-2 中文渲染准确率高，适合直接出标题字
- 标题文字要清晰可读，字体风格与画面氛围匹配
- 封面是 21:9 微信公众号规格，目标 1800x766。但 GPTIMG2 的 `size` 取离散档位，21:9 没有原生档——请求时用最接近的 16:9 `2560x1440`（2K，比例略宽），拿到图后再裁成 1800x766；或直接在 prompt 里要求 21:9 超宽构图。**不要回退到低分辨率出图**

**引擎 / 凭据 / 模型**：见 3.3（`gpt-image-2` @ `${GPTIMG2_BASE_URL}` = `https://api.chatgpt-code.com`，鉴权 `Authorization: Bearer ${GPTIMG2_API_KEY}`，`response_format=url` → 下载落地 → 图床上传）。

### Phase 4: CSS 内联 + 预览确认

1. Run juice to inline all CSS styles:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub && { [ -d node_modules ] || npm install; }
```

```bash
cd ${CLAUDE_PLUGIN_ROOT}/skills/cyxj-wechat-pub && node -e "
const juice = require('juice');
const fs = require('fs');
// 改这一行切换主题：theme-tatalab.css / theme-noir-gold.css / theme-orange-editorial.css
const css = fs.readFileSync('theme-tatalab.css', 'utf8');
const html = fs.readFileSync('/tmp/wechat-input.html', 'utf8');
fs.writeFileSync('/tmp/wechat-output.html', juice.inlineContent(html, css));
"
```

2. Read `preview-template.html`
3. Replace `{{CONTENT}}` with the juice-inlined HTML
4. Write to `/tmp/wechat-preview.html`
5. **打开预览给用户看**：`open /tmp/wechat-preview.html`（系统浏览器，用户可在底部点「复制到剪贴板」）
6. **可选：Claude 自验证排版**——Playwright MCP 不支持 file:// 协议，必须先起本地 http server：
   ```bash
   cd /tmp && python3 -m http.server 8765 &
   ```
   然后让 Playwright `navigate` 到 `http://localhost:8765/wechat-preview.html`，`browser_take_screenshot` 后用 `pkill -f "http.server 8765"` 关闭 server。
   - **截图 filename 必须用相对路径**，比如 `.playwright-mcp/skill-test.png` 或工作目录下的 `xxx.png`；写 `/tmp/xxx.png` 等绝对路径会被 MCP 以 `outside allowed roots` 拒绝。
   - 截图看完后 `rm -rf .playwright-mcp` 清理，避免污染工作区。
7. Ask: "排版满意吗？需要调整什么？"
8. If user wants changes, go back to Phase 2


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

## Orange Editorial Theme — 专属规则与组件

选了 `theme-orange-editorial.css` 时，按这一节走。其他主题忽略本节。

### 结构铁律（违反就出白色断层）

公众号编辑器会在所有相邻的 `<section>` 兄弟元素之间强行插入白色间隙，所以这个主题的 HTML 必须长这样：

```html
<section class="article">
  <section class="hero">
    <!-- ticker / corner / title / subtitle / author 全部塞在 hero 内部 -->
    <section class="hero-bleed"></section>
    <section class="hero-bleed-cream"></section>
  </section>
  <section class="body">
    <!-- 所有正文段落 + 章节 + 配图 + 后记 + footer 都在 body 这一个 section 内 -->
    <p>段落...</p>
    <section class="spacer"></section>
    <section class="chapter">...</section>
    <p>段落...</p>
    <!-- ... -->
    <section class="footer-card">...</section>
  </section>
</section>
```

**不要做的事**：
- 不要把 hero 之后的章节 / 后记拆成 `.article` 的多个兄弟 `<section>`
- 不要用 `margin-top` 给章节之间留白——用 `<section class="spacer"></section>` 占位（内部填充米色背景，避免兄弟间隙）
- 不要把 `.body` 嵌套到 `.hero` 里面（嵌套之后 hero 橙色背景会被 WeChat 剥掉）
- 不要用 `position: absolute` / `writing-mode: vertical-rl` / `transform: rotate(180deg)`，公众号统统不支持

### Orange Editorial 专属组件模板

下面列的组件除了基础的 `.quote / .card / .img-card / .callout` 已在前面 HTML Component Templates 里定义过，其他都是这个主题专属，仅在 `theme-orange-editorial.css` 里有定义。

#### Hero（杂志封面式）

```html
<section class="hero">

  <section class="hero-ticker">WRAPPER · MODEL · PRODUCT · WRAPPER · MODEL · PRODUCT</section>

  <section class="hero-corner">
    <section class="hero-issue">
      <span class="hero-issue-dash"></span>
      ISSUE 03 / 2026.05
    </section>
    <section class="hero-cat">{TAG}</section>
  </section>

  <section class="hero-title">
    <h1>{标题第一行}<br>{标题第二行}<span class="hero-title-arrow">→</span></h1>
  </section>

  <section class="hero-subtitle">
    <section class="hero-eyebrow">STUCK BETWEEN<br>MODEL & WRAPPER</section>
    <section class="hero-deck">{中文副标，1-2 句话讲清楚文章在说什么}</section>
  </section>

  <section class="hero-author">
    <section class="hero-ip"><img src="{头像 CDN}" alt="陈与小金"></section>
    <section class="hero-byline">
      <section class="hero-byline-label">BYLINE / 作者</section>
      <section class="hero-author-name">陈与小金</section>
    </section>
    <section class="hero-author-tags">AI 编程<br>运营干货<br>效率提升</section>
  </section>

  <section class="hero-bleed"></section>
  <section class="hero-bleed-cream"></section>
</section>
```

每篇文章只换 `TAG`、ISSUE 号、ticker 内容、标题、eyebrow（英文小标）、deck（中文副标），其他保持不变。

#### Chapter（章节大头）

```html
<section class="chapter">
  <section class="chapter-num">01</section>
  <section class="chapter-right">
    <section class="chapter-tag">CHAPTER ONE</section>
    <section class="chapter-title">{中文小标题}</section>
  </section>
</section>
```

反色变体（用于结论 / 总结章节，黑底橙数字）：

```html
<section class="chapter chapter-dark">...</section>
```

#### Spacer（章节之间的米色占位）

```html
<section class="spacer"></section>
```

每个 chapter 之前都加一个 spacer，撑出 36px 米色呼吸区。

#### Pull Quote（金句 / 引言）

```html
<section class="quote">
  <section class="quote-mark">"</section>
  <section class="quote-text">{金句正文}</section>
</section>
```

注意这里跟其他主题的 `.quote` 不一样：橙色编辑风用 flex 两列布局，左列大引号，右列引文。

#### Stat Callout（双栏数据对比）

```html
<section class="stat-callout">
  <section class="stat-row">
    <section class="stat-cell">
      <section class="stat-label">ANTHROPIC</section>
      <section class="stat-value">34.44%</section>
    </section>
    <section class="stat-cell">
      <section class="stat-label">OPENAI</section>
      <section class="stat-value">32.30%</section>
    </section>
  </section>
  <section class="stat-footnote">{数据来源 / 时间 / 样本说明}</section>
</section>
```

#### List Card（票据风 dashed 分隔的编号列表）

```html
<section class="list-card">
  <p class="list-item"><span class="list-num">01</span>OpenAI 创始成员</p>
  <p class="list-item"><span class="list-num">02</span>特斯拉前 AI 总监</p>
  <p class="list-item"><span class="list-num">03</span>斯坦福读博时的导师是李飞飞</p>
</section>
```

#### Timeline（时间线表格，最新行高亮）

```html
<section class="timeline">
  <section class="timeline-head">
    <section class="timeline-head-year">YEAR</section>
    <section class="timeline-head-event">EVENT / 事件</section>
  </section>
  <section class="timeline-row">
    <section class="timeline-year">2015</section>
    <section class="timeline-event">OpenAI 成立，他是联合创始人之一</section>
  </section>
  <section class="timeline-row">
    <section class="timeline-year">2017.06</section>
    <section class="timeline-event">被挖到特斯拉，直接向马斯克汇报</section>
  </section>
  <section class="timeline-row timeline-row-current">
    <section class="timeline-year">2026.05.19</section>
    <section class="timeline-event">加入 Anthropic 预训练团队 →</section>
  </section>
</section>
```

最新 / 当前事件加 `.timeline-row-current`，会变橙底反白。

#### Keyword Card（黑底橙阴影的概念锚点）

```html
<section class="keyword-card">
  <section class="keyword-label">KEYWORD 01 →</section>
  <section class="keyword-text">VIBE CODING</section>
</section>
```

如果要带中英对照（如 LLM WIKI / 大模型 WIKI）：

```html
<section class="keyword-card">
  <section class="keyword-label">KEYWORD 02 →</section>
  <section class="keyword-text">LLM WIKI<br><span class="keyword-sub">大模型 WIKI</span></section>
</section>
```

#### Layer List（洋葱式 L1-L4 分层）

```html
<section class="layer-list">
  <section class="layer">
    <section class="layer-num">L1</section>
    <section class="layer-body">
      <section class="layer-eyebrow">FIRST LAYER</section>
      <section class="layer-title">命令行工具，比如 Claude Code</section>
    </section>
  </section>
  <section class="layer">
    <section class="layer-num">L2</section>
    <section class="layer-body">
      <section class="layer-eyebrow">SECOND LAYER</section>
      <section class="layer-title">Skills、子智能体、Agent Teams</section>
    </section>
  </section>
  <section class="layer layer-outer">
    <section class="layer-num">L4</section>
    <section class="layer-body">
      <section class="layer-eyebrow">OUTER LAYER →</section>
      <section class="layer-title">记忆 + CLAUDE.md 文件——给模型的上下文</section>
    </section>
  </section>
</section>
```

最外层加 `.layer-outer` 变成橙底反白，强调"最重要的一层"。

#### Growth（增长可视化，简易横条形）

```html
<section class="growth">
  <section class="growth-head">
    <section class="growth-head-date">DATE</section>
    <section class="growth-head-share">ANTHROPIC SHARE / 采纳率</section>
  </section>
  <section class="growth-row">
    <section class="growth-date">2023.06</section>
    <section class="growth-bar-cell">
      <section class="growth-bar" style="width:2px;"></section>
      <section class="growth-value">0.003%</section>
    </section>
  </section>
  <section class="growth-row">
    <section class="growth-date">2025.04</section>
    <section class="growth-bar-cell">
      <section class="growth-bar" style="width:46px;"></section>
      <section class="growth-value">7.94%</section>
    </section>
  </section>
  <section class="growth-row growth-row-current">
    <section class="growth-date">2026.04</section>
    <section class="growth-bar-cell">
      <section class="growth-bar" style="width:200px;max-width:60%;"></section>
      <section class="growth-value">34.44%</section>
    </section>
  </section>
</section>
```

横条宽度按数据比例手工算（行内 style 写 width），最新一行加 `.growth-row-current`。

#### Poster（海报式中央大字块）

```html
<section class="poster">
  <section class="poster-eyebrow">→ THE NAME IS</section>
  <section class="poster-text">WRAPPER</section>
  <section class="poster-cn">套　壳</section>
</section>
```

结论 / verdict 强力变体（中文大字，英文做补充）：

```html
<section class="poster poster-verdict">
  <section class="poster-eyebrow">→ THE VERDICT</section>
  <section class="poster-text">套壳<br>才是产品</section>
  <section class="poster-cn">WRAPPER IS THE PRODUCT</section>
</section>
```

#### Callout（黑底 takeaway）

```html
<section class="callout callout-dark">
  <section class="callout-title">→ TAKEAWAY</section>
  <p>{重要结论 / 一句话总结}</p>
</section>
```

普通米色 callout 用 `<section class="callout">...</section>`；橙色编辑风默认就有 6px 实心阴影。

#### Prediction（橙表头预测卡）

```html
<section class="prediction">
  <section class="prediction-head">
    <section class="prediction-label">PREDICTION 01</section>
    <section class="prediction-title">{预测主题}</section>
  </section>
  <section class="prediction-body">
    <p>{核心论点}</p>
    <p class="prediction-note">{补充说明，灰色小字}</p>
  </section>
</section>
```

#### Divider Eyebrow（横线 + 小标 + 横线，用于段落分隔）

```html
<section class="divider-eyebrow">
  <section class="divider-eyebrow-line"></section>
  <section class="divider-eyebrow-label">P.S. / 后记</section>
  <section class="divider-eyebrow-line"></section>
</section>
```

#### Center Quote（结尾感言 + 箭头）

```html
<section class="center-quote">
  <section class="center-quote-arrows">→ → →</section>
  <section class="center-quote-text">本期就到这里。<br>如果对你有帮助，欢迎评论转发。</section>
</section>
```

#### Footer Card（黑底 sign-off）

```html
<section class="footer-card">
  <section class="footer-head">— SIGN OFF —</section>
  <section class="footer-body">
    <section class="footer-label">SIGNED</section>
    <section class="footer-author">陈与小金</section>
    <section class="footer-desc">祝你身体健康，永远平安。<br>祝你 Token 无限，永远自由。</section>
    <section class="footer-sign-row">
      <section class="footer-sign-line"></section>
      <section class="footer-sign">{2026 · 05 · 23}</section>
      <section class="footer-sign-line"></section>
    </section>
    <section class="footer-thanks">THANKS FOR READING →</section>
  </section>
</section>
```

#### End Ticker（最后一条跑马灯字条）

```html
<section class="ticker-end">
  WRAPPER · MODEL · PRODUCT · WRAPPER · MODEL · PRODUCT · END
</section>
```

放在 footer-card 之后，作为整篇文章的视觉收束。

### Orange Editorial 专属 Auto-Recognition（补充）

在通用 Auto-Recognition Rules 基础上，遇到下列模式优先选橙色编辑风专属组件：

| 内容模式 | 选哪个组件 |
|---------|----------|
| 两个对比数字（如 X% vs Y%）| `.stat-callout` |
| 一个"概念单词 + 中文释义"作为本章关键词 | `.keyword-card` |
| 多个时间点 + 事件描述（含最新事件）| `.timeline` + 最新行加 `.timeline-row-current` |
| 同一指标在多个时间点的数值变化 | `.growth` |
| 分层 / 嵌套结构（L1/L2/L3 等）| `.layer-list` |
| 三条左右的预测 / 推断 | `.prediction` 每条一卡 |
| 单独成段、需要"大字"视觉冲击的概念词或结论 | `.poster`（中段）/ `.poster poster-verdict`（结论） |
| 一段"重点结论 / 一句话总结" | `.callout callout-dark` 加 `→ TAKEAWAY` 标签 |
| 后记 / P.S. 分隔 | `.divider-eyebrow` |
| 文章首尾的"杂志感"字条 | `.hero-ticker`（首）+ `.ticker-end`（尾） |

### Orange Editorial 校验清单

排完版准备调 juice 之前，对照下面这张清单检查一遍：

- [ ] 整篇 HTML 是 `<section class="article">` 一个根节点，hero 和 body 都在它内部
- [ ] body 内所有章节都是同一个 `<section class="body">` 的子元素，没有把章节拆成 `.article` 的兄弟
- [ ] 章节之间是 `<section class="spacer"></section>`，不是 margin
- [ ] grep 一遍 HTML，确认没有 `position: absolute`、`writing-mode`、`transform: rotate`
- [ ] hero 末尾有 `.hero-bleed` + `.hero-bleed-cream` 两块米色压底（缓冲 WeChat 间隙）
- [ ] body 开头有 `border-top: 30px solid #F2E6CC`（CSS 里已写好，HTML 别覆盖）
- [ ] 文章开头确认有橙底网点的 hero，结尾确认有 footer-card + ticker-end

