---
name: cyxj-video-cover
description: |
  视频封面生成。一句话生成 IP 形象 3D 渲染风格的视频封面，默认输出 4:3 横版 + 3:4 竖版。
  触发方式：/封面、/video-cover、「生成封面」「做个视频封面」「帮我做封面」
  Video cover generator with 3D rendered IP character. Generates 4:3 + 3:4 covers.
  Trigger: /封面, /video-cover, "generate cover", "make a cover"
---

# cyxj-video-cover：视频封面生成

一句话生成带 IP 形象的视频封面。默认输出 4:3 横版 + 3:4 竖版两张。

## 工作流

### Step 1：确认标题

用户可能给出：
- **明确标题**：直接使用
- **一段话/主题描述**：提炼为 10-20 字的封面标题
- **什么都没说**：从当前对话上下文（刚写完的文章、逐字稿、大纲等）推断主题，提炼标题

标题确认后继续。

### Step 2：场景推断

根据标题自动推断 IP 角色的场景和动作，**不需要问用户**。推断原则：

- 角色的动作/姿态必须与标题语义相关（如「计划模式」→ 看规划面板，「省钱」→ 手持钱袋）
- 场景中要有与主题匹配的全息 UI / 科技道具
- 如果用户主动指定了场景描述，用 `--scene` 参数传入

### Step 3：调用脚本生成

```bash
python3 $SKILL_DIR/scripts/generate.py \
  --title "封面标题" \
  --output <当前工作目录或用户指定目录>
```

可选参数：
- `--scene "场景描述"` — 手动指定场景（通常不需要）
- `--ratios "4:3,3:4"` — 自定义比例（默认已是 4:3,3:4）
- `--model <model>` — 换模型（默认 gemini-3-pro-image-preview）

### Step 4：展示结果

用 Read 工具打开生成的两张图片展示给用户。

如果用户不满意：
- 调整 `--scene` 描述角色动作/场景
- 调整 `--title` 措辞
- 重新生成

## 输出规格

| 版本 | 比例 | 文件名 |
|------|------|--------|
| 横版 | 4:3 | cover_4x3.png |
| 竖版 | 3:4 | cover_3x4.png |

## 视觉风格（内置，无需用户指定）

- 3D 渲染 IP 角色（光头、蓝眼、金耳坠、蓝色「陈与小金」卫衣）
- 白色/浅灰背景 + 微网格
- 全息/半透明科技 UI 面板
- 左侧大号加粗标题文字（黑色 + 一个强调色）
- 柔光、轻微景深

## 依赖

- Python 3.11+
- google-genai, pillow
- 环境变量：`GEMINI_API_KEY` 或 `GOOGLE_API_KEY`
