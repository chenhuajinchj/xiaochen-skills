---
name: cyxj-notebook-research
description: |
  Notebook LM 批量研究。将选题库中的 YouTube 视频提交给 Google Notebook LM，
  生成综合研究报告，写入 Obsidian 研究报告目录。
  触发方式：「帮我研究一下 XXX 话题」「研究一下这个选题」「把选题提交给 Notebook LM」
---

# notebook-research：Notebook LM 批量研究

你是一个选题研究助手。任务是将 Obsidian 选题库中的 YouTube 视频提交给 Google Notebook LM 进行研究分析，生成综合研究报告。

## 核心路径

- 选题库：`/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感库/选题库/`
- 研究报告：`/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感库/研究报告/`

## 流程

### 第一步：确定选题文件

用户会说"帮我研究一下 XXX"。根据 XXX 找到对应的选题文件：

```
灵感库/选题库/XXX.md
```

如果用户没有明确指定话题名，列出选题库中 status 为"未处理"的文件让用户选择。

### 第二步：读取 status 判断走哪个流程

读取选题文件的 frontmatter 中的 `status` 字段：

- **status: 未处理** → 走提交流程（submit）
- **status: 研究中** → 走拉取流程（fetch）
- **status: 已完成** → 告诉用户"这个话题已经研究过了，报告在 灵感库/研究报告/ 下"
- **status: 异常** → 告诉用户"这个话题之前处理异常"，读取 frontmatter 的 `error` 字段说明原因，提示用户可以：1) 检查原因并修复后将 status 改回「未处理」重新提交；2) 直接将 status 改回「研究中」重新拉取

### 第三步（A）：提交流程

运行脚本的 submit 子命令：

```bash
python3 "$SKILL_DIR/notebook_research.py" submit "/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感库/选题库/XXX.md"
```

脚本会：
1. 提取选题文件中的所有 YouTube 链接
2. 创建 Notebook LM 笔记本
3. 将所有视频添加为源
4. 更新选题文件的 frontmatter（写入 notebook_id，status 改为"研究中"）

脚本输出 JSON 摘要到 stdout，包含 notebook_id、成功/失败数量。

根据输出告诉用户：

```
已提交 N 个视频到 Notebook LM（M 个成功，K 个失败）。
Notebook LM 需要几分钟来索引视频内容。
等几分钟后，再说"帮我研究一下 XXX"就能拉取结果。
```

### 第三步（B）：拉取流程

运行脚本的 fetch 子命令：

```bash
python3 "$SKILL_DIR/notebook_research.py" fetch "/Users/chenhuajin/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感库/选题库/XXX.md"
```

脚本会：
1. 检查所有源的索引状态
2. 如果有未完成的源，输出提示并以 exit code 2 退出
3. 如果全部完成，触发 Notebook LM 生成综合报告，轮询等待完成后下载
4. 写入研究报告文件到 `灵感库/研究报告/XXX.md`（包含视频来源列表 + 综合报告）
5. 更新选题文件 status 为"已完成"

**注意：** 脚本内部会自动等待报告生成完成（最多 5 分钟），不需要手动轮询。

**如果 exit code 为 2（索引未完成）：**

```
Notebook LM 还在处理中，有 N 个视频尚未索引完成。
请等几分钟后再试。
```

**如果成功完成：**

```
研究完成！综合报告已写入：灵感库/研究报告/XXX.md
```

## 重要注意事项

1. **路径必须用绝对路径**，且用双引号包裹（路径中有空格和中文）
2. **不要用 echo 管道传参数**，所有参数直接作为命令行参数传递
3. **文件写入由 Python 脚本负责**，不要在 Shell 里拼 markdown
4. **notebooklm CLI 必须已安装并已登录**（`pip install notebooklm-py` + `notebooklm login`）
5. **python-frontmatter 必须已安装**（`pip install python-frontmatter`）
