# 达芬奇字幕修正 Skill v4

<command-name>字幕修正</command-name>

<trigger>
Use when user mentions:
- `/字幕修正`
- "修正字幕", "字幕错别字", "SRT 修正"
- "达芬奇字幕", "DaVinci subtitle"
- Provides an SRT file path for correction
</trigger>

## 路径约定

`$SKILL_DIR` 指本 SKILL.md 所在目录的绝对路径。运行脚本前先确定：
```bash
SKILL_DIR="$(dirname "$(readlink -f "$0")")"  # 或直接用 SKILL.md 所在目录的绝对路径
```

## 架构原则

**三层分离**：Python 做结构处理，Gemini 做语义初修，Opus 审查把关。

- Python（srt_cleaner.py）：HTML 清理、去重、标点替换、合并、拆分、编号、导出纯文本 — 所有时间码操作
- Gemini（srt_corrector.py）：同音字修正 + 去口吃 + 去填充词 — API 自动处理，几乎免费
- Opus（对话内）：审查 Gemini 的修改清单，纠正错误修正，发现遗漏 — 只看 diff，token 极少

**词典定位**：词典是"已知陷阱"参考，不是主力。同一个词的错误变体太多，词典永远无法穷举。真正的修正靠 Gemini 的语义理解 + 视频主题上下文。Opus 审查后发现的遗漏会反馈到词典，让系统越来越准。

## 使用方法

```
/字幕修正 ~/Desktop/Timeline1.srt                          # 完整流程
/字幕修正 ~/Desktop/Timeline1.srt --topic "Claude Code教程" # 指定主题提高修正准确度
/字幕修正 ~/Desktop/Timeline1.srt --no-regroup             # 跳过合并拆分
/字幕修正 ~/Desktop/Timeline1.srt --premium                # Phase 2a 用高端 Gemini 模型
/字幕修正 --add "错误词" "正确词"                            # 添加词典条目
```

## 显示规则

- 场景：横屏 16:9
- 软上限：18 字符（正常通过）
- 警告区：18-25 字符（输出时标注提醒）
- 硬上限：25 字符（Python 强制拆分，标记需人工校验）
- 字符计算：中文/中文标点=1, ASCII=0.5, 向上取整
- 标点规则：字幕中不用逗号句号（替换为空格），保留？！

## 执行步骤

<steps>

### Phase 1: Python 结构处理

1. **备份**：创建 `.bak` 备份文件
2. **运行 srt_cleaner.py**：
   ```bash
   python3 "$SKILL_DIR/srt_cleaner.py" "<input.srt>" --stats
   ```
   如果用户指定 `--no-regroup`，追加该参数跳过合并拆分。
3. **报告结果**：向用户汇报去重、合并、拆分、超限条目数量

### Phase 2a: Gemini 自动初修

1. **确认主题**：如果用户提供了 `--topic`，以此为语境参考；否则从字幕内容推断主题，向用户确认
2. **运行 srt_corrector.py**：
   ```bash
   python3 "$SKILL_DIR/srt_corrector.py" "<_cleaned.srt>" --topic "主题"
   ```
   如果用户指定 `--premium`，追加该参数使用高端模型。
3. **输出**：
   - `_gemini_fixed.srt`：Gemini 修正后的完整 SRT
   - `_changes.json`：修改清单（原文→修正，带原因）

### Phase 2b: Opus 审查（在对话中）

1. **读取 `_changes.json`**（只看修改清单，不读全文 SRT）
2. **审查 Gemini 的修正**：
   - 检查每项修正是否合理
   - 标记错误的修正（Gemini 改错了的）
   - 发现遗漏的错误（浏览 _gemini_fixed.srt 中 Gemini 未修改的部分，抽查是否有遗漏）
3. **应用最终修正**：
   - 撤销错误的修正
   - 补充遗漏的修正
   - 保存为 `_fixed.srt`
4. **反馈到词典**：
   - 把 Gemini 漏掉的重要错误写入 `dictionary.json` 的 `feedback.gemini_missed` 字段
   - 如果遗漏的错误有通用性（不是偶发的），同时添加到 `corrections` 中

### Phase 3: 导出 IntelliScript 纯文本

Phase 2b 完成后，运行：
```bash
python3 "$SKILL_DIR/srt_cleaner.py" "<_fixed.srt>" --export-txt
```

生成 `_script.txt`（UTF-8 纯文本），供 DaVinci Resolve IntelliScript 使用。

### Phase 4: 输出汇总

向用户说明最终输出文件：
- `_fixed.srt` — 最终修正后的字幕文件
- `_script.txt` — 纯文本逐字稿（给 IntelliScript 用）

中间文件留在同目录供排查：
- `原文件.bak` — 原始备份
- `_cleaned.srt` + `_cleaned_stats.json` — Phase 1 中间产物
- `_gemini_fixed.srt` + `_changes.json` — Phase 2a 中间产物

提醒检查 `splits_needing_review` 和 `over_soft_limit` 条目。

</steps>

## Opus 审查时的权限边界

**可以做：**
- 审查并修正 Gemini 的错误修改
- 补充 Gemini 遗漏的同音字、口吃、填充词修正
- 将遗漏反馈到词典
- 审查合并结果，标记语义问题
- 建议用户添加新词典条目

**绝不可以做：**
- 修改任何时间码
- 合并或拆分条目
- 调整条目顺序
- 删除整条字幕（即使是填充词，也只清空文字保留时间码结构）
- 书面化改写口语表达

## 模型选择

| 用途 | 模型 ID | 价格 | 说明 |
|------|---------|------|------|
| 日常初修 | `gemini-3.1-flash-lite-preview` | $0.25/$1.50 per M | 默认，最便宜 |
| 高端初修 | `gemini-3-flash-preview` | $0.50/$3 per M | flash-lite 效果不够时加 `--premium` |
| 审查 | Opus 4.6（对话内） | $15/$75 per M | 只审查 diff |

**注意**：`gemini-3.1-flash-image-preview` 和 `gemini-3-pro-image-preview` 是图片生成专用模型，不用于文本修正。

## 词典管理

添加新的错误映射：
```
/字幕修正 --add "错误词" "正确词"
```

词典结构为"正确词 → 已知错误变体列表"，添加时会自动归类到对应的正确词下。

词典路径：`$SKILL_DIR/dictionary.json`

### 反馈机制

`dictionary.json` 的 `feedback.gemini_missed` 字段记录 Gemini 漏掉但 Opus 审查时发现的错误：
```json
{"original": "错误文字", "correct": "正确文字", "context": "错误类型描述", "date": "2026-03-21"}
```

这些记录用于：
1. 优化 Gemini 的 prompt（如果某类错误反复出现）
2. 扩充 corrections 词典（如果错误有通用性）
