---
name: cyxj-video-cover
description: |
  视频封面生成（真人版）。用你的真人照片 + gpt-image-2 重绘入场，一句话生成带本人形象的高点击封面。
  默认输出 4 个比例：YouTube 16:9、公众号 2.35:1、竖版 3:4、横版 4:3，每比例 2 张供挑选，并行生成。
  中文标题由模型直接渲染（gpt-image-2 中文渲染准确率高）。
  触发方式：/封面、/video-cover、「生成封面」「做个视频封面」「帮我做封面」「做个 YouTube 封面」
  Real-person video cover generator. Uses your photo + gpt-image-2 to redraw you into a
  high-CTR cover. Outputs 16:9 / 2.35:1 / 3:4 / 4:3, 2 picks each, in parallel.
  Trigger: /封面, /video-cover, "generate cover", "make a YouTube thumbnail"
---

# cyxj-video-cover：视频封面生成（真人版）

用你的真人照片做参考，gpt-image-2 把你重绘进新封面场景（人脸保持一致），一句话出封面。
默认 4 个比例各 2 张，并行生成，约 1 分钟出齐。

## 前置准备（首次）

1. **中转站 key**（已配好则跳过）——脚本自动从密钥存储读，无需手动 export：
   - `~/项目/自己的应用/密钥存储/.env` 里的 `GPTIMG2_BASE_URL` 和 `GPTIMG2_API_KEY`
   - `GPTIMG2_BASE_URL` = `https://api.chatgpt-code.com`（末尾**没有** `/v1`，脚本拼端点时自己补）
   - 也可用同名环境变量覆盖

2. **真人照片**——默认读 `~/Pictures/封面形象/`（放几张本人正脸清晰的照片即可），
   也可每次用 `--face` 临时指定某张或某目录。

3. **Python 依赖**：仅标准库（urllib），无需 pip 安装。生成结果用系统自带能力查看即可。

## 工作流

### Step 1：确认标题

- **明确标题**：直接用
- **一段话/主题**：提炼为 10-20 字的封面标题
- **什么都没说**：从当前对话上下文（刚写的文章、逐字稿、选题、大纲）推断主题并提炼标题

### Step 2：场景（通常自动）

脚本会根据标题自动安排人物动作和场景（科技工位虚化背景 + 与主题相关的道具），
**不需要问用户**。用户主动指定时用 `--scene` 传入（如「坐在电脑前敲代码」「手指向屏幕」）。

### Step 3：调用脚本生成

```bash
python3 $SKILL_DIR/scripts/generate.py \
  --title "封面标题" \
  --output <当前工作目录或用户指定目录>
```

常用参数：
- `--ratios "16:9,3:4"` — 只出指定比例（默认全四个：`16:9,2.35:1,3:4,4:3`）
- `--n 1` — 每比例只出 1 张（默认 2 张挑）
- `--face ~/Pictures/封面形象/某张.png` — 临时指定参考照片（默认读 `~/Pictures/封面形象/`）
- `--scene "场景描述"` — 手动指定人物动作/场景
- `--model <model>` — 换模型（默认 gpt-image-2）

### Step 4：展示结果，让用户挑

用 Read 工具打开生成的封面展示给用户。每比例多张时，并列展示让用户挑。

不满意时：
- 调 `--scene` 改人物动作/场景
- 调 `--title` 措辞
- 换 `--face` 参考照片
- 重新生成（多出几张挑）

### Step 5：选定的封面过 cyxj-psjpg 转上传用 JPG

生成的封面是 PNG。**用户挑定要用的封面后**，把这些选中的图过一遍
[`cyxj-psjpg`](../../cyxj-psjpg) skill，转成统一规格的 JPG 并清理元数据痕迹
（真 PS 导出，去掉来源痕迹，适合上传各平台）。

为什么挑完再过：psjpg 走真 Photoshop，慢且占用 PS——只处理用户最终要用的几张，
不浪费在没选中的图上。

做法：
1. 把用户选定的封面**复制到一个单独目录**（如 `<输出目录>/选定/`），避免把没选的也转了。
2. **调用 `cyxj-psjpg` skill**，对这个目录跑它的转换脚本（psjpg 会输出到 `<目录>_psjpg/`）。
   psjpg 是独立插件，用 Skill 工具调起它即可，由它用自己的 `${CLAUDE_PLUGIN_ROOT}` 定位脚本——
   **不要**在本 skill 里写死 psjpg 的路径（两个插件装在不同缓存目录，路径不固定）。
3. 把最终 JPG 位置告诉用户。

前提：用户本机已装 `cyxj-psjpg`（及其依赖 Photoshop + exiftool）。没装就提示用户先装，
或这一步可跳过（PNG 也能直接用）。

## 输出规格

| 用途 | 比例 | 实际尺寸 | 文件名 |
|------|------|---------|--------|
| YouTube | 16:9 | 2560×1440 | cover_16x9_N.png |
| 公众号 | 2.35:1 | 2560×1088 | cover_2_35x1_N.png |
| 竖版 | 3:4 | 1536×2048 | cover_3x4_N.png |
| 横版 | 4:3 | 2048×1536 | cover_4x3_N.png |

> ℹ️ **尺寸说明**：GPTIMG2（`api.chatgpt-code.com`）的 gpt-image-2 出 **2K 级别**大图，
> 边长均对齐 16 的倍数、长短比 ≤ 3:1。图片走 `response_format=url` 返回，脚本拿到 url 后下载落地为 PNG。
> 想改尺寸/比例改脚本里的 `RATIO_SIZE` 即可。

## 视觉风格（内置，无需用户指定）

- **真人**：你的照片重绘入场，保持本人长相（写实，不卡通/不 3D 化）
- 人物在一侧（半身、看镜头、表情生动自信）+ 另一侧大标题留白
- 背景：**简洁为主**——纯色/弱渐变或重度虚化的极简环境，不堆道具/屏幕/UI，
  让人物和标题主导画面（需要具体场景时用 `--scene` 临时加）
- 大号加粗中文标题（高对比、描边），由 gpt-image-2 直接渲染
- 高点击 YouTube 缩略图调性

## 技术说明

- 模型 **gpt-image-2** @ GPTIMG2 中转站 `api.chatgpt-code.com`（OpenAI 兼容）
- 走 `{base}/v1/images/edits` 端点：传真人照片做参考图重绘，保人脸一致
  （`GPTIMG2_BASE_URL` 末尾无 `/v1`，脚本读到 base 后自动补全到 `/v1`）
- 出 **2K** 大图，`response_format=url` 返回 url，脚本下载后落地为 PNG
- 中文文字渲染准确率高（实测大标题基本不错字），靠每比例多出几张进一步兜底
- 并行生成（ThreadPoolExecutor），4 比例×2 张约 1 分钟出齐
- key 从密钥存储自动读取，不写进代码

## 依赖

- Python 3.11+（仅标准库）
- 真人照片目录（默认 `~/Pictures/封面形象/`）
- 密钥存储 `.env` 里的 `GPTIMG2_BASE_URL` / `GPTIMG2_API_KEY`
- **可选**：`cyxj-psjpg` skill（Step 5 把选定封面转上传用 JPG；它本身需 Photoshop + exiftool）
