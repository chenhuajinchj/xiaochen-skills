# 达芬奇字幕修正工具

[English](README.md)

一个 Claude Code Skill，用于修正达芬奇 DaVinci Resolve 导出 SRT 字幕中的语音识别（ASR）错误。采用 **Gemini + Opus 混合架构**，以极低成本实现高质量修正。

## 解决什么问题

达芬奇的中文语音转文字准确度有限，导出的字幕经常出现：
- **同音字替换**：专业术语被识别成同音常见词（如 "Claude Code" → "Color Code"，"上下文" → "善夏文"）
- **口吃重复**："我说的我说的我说的" 应该是 "我说的"
- **填充词**："嗯""啊""那个""就是说" 等口头禅
- **重复条目**：达芬奇有时会生成时间重叠的字幕片段

## 架构

```
Phase 1: Python 结构处理 (srt_cleaner.py)
  HTML 清理 → 去重 → 标点替换 → 合并短条目 → 拆分长条目 → 重新编号

Phase 2a: Gemini Flash Lite 自动初修 (srt_corrector.py)
  分批 API 调用（词典 + 主题上下文）→ _gemini_fixed.srt + _changes.json

Phase 2b: Opus 审查（在 Claude Code 对话中）
  审查 Gemini 的修改清单 → 纠正错误 → 补充遗漏 → 保存 _fixed.srt

Phase 3: 导出纯文本（供 IntelliScript 使用）
```

### 为什么用混合架构？

| 方案 | 400 条字幕成本 | 准确度 |
|------|--------------|--------|
| 纯 Opus (v3) | ~$2-4 | 高 |
| Gemini Flash Lite + Opus 审查 (v4) | ~$0.35-0.55 | 高 |

Gemini 以 1/50 的成本完成 95%+ 的修正，Opus 只需审查修改清单（diff），不处理全文。

## 环境要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+
- 环境变量 `GEMINI_API_KEY`

```bash
pip install google-genai pysrt
```

## 安装

### 作为 Claude Code Skill 安装（推荐）

```bash
/plugin marketplace add chenhuajinchj/xiaochen-skills
```

在 Claude Code 中使用：
```
/字幕修正 ~/Desktop/Timeline1.srt --topic "视频主题"
```

### 独立使用

```bash
# Phase 1: 结构清理
python3 srt_cleaner.py "input.srt" --stats

# Phase 2a: Gemini 自动修正
python3 srt_corrector.py "input_cleaned.srt" --topic "视频主题"

# 使用高端模型（更准但稍贵）
python3 srt_corrector.py "input_cleaned.srt" --topic "视频主题" --premium
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `srt_cleaner.py` | Phase 1：结构处理（HTML 清理、去重、合并/拆分、编号） |
| `srt_corrector.py` | Phase 2a：Gemini API 分批修正，支持词典 |
| `dictionary.json` | 已知 ASR 错误映射（正确词 → 错误变体列表） |
| `SKILL.md` | Claude Code Skill 定义和工作流程 |

## 词典

词典将正确术语映射到已知的 ASR 错误变体：

```json
{
  "corrections": {
    "Claude Code": ["Color Code", "Closet Code", "Colortico", "clotco"],
    "上下文": ["善夏文", "善效文"],
    "worktree": ["工作数", "工夫"]
  }
}
```

通过 Claude Code 添加新条目：
```
/字幕修正 --add "错误词" "正确词"
```

`feedback.gemini_missed` 字段记录 Gemini 漏掉但 Opus 发现的错误，实现持续改进。

## Gemini 模型选择

| 模型 | 用途 | 输入/输出价格 |
|------|------|-------------|
| `gemini-3.1-flash-lite-preview` | 默认，最便宜 | $0.25 / $1.50 每百万 token |
| `gemini-3-flash-preview` | 高端，更智能 | $0.50 / $3.00 每百万 token |

> 注意：图片生成模型（`gemini-3.1-flash-image-preview`、`gemini-3-pro-image-preview`）不适用于文本修正。

## 显示规则

针对 16:9 横屏视频字幕优化：
- 软上限：18 显示字符（中文=1，ASCII=0.5）
- 硬上限：25 字符（自动拆分并标记需人工校验）
- 标点：逗号句号 → 空格，保留？！

## 许可证

MIT
