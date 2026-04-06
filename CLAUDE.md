# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是一个 Claude Code 插件仓库（Plugin Marketplace），包含 8 个独立的 skill，通过 `/plugin marketplace add chenhuajinchj/xiaochen-skills` 安装到 Claude Code。

## 架构

```
.claude-plugin/marketplace.json   ← 插件市场注册表（所有插件入口）
plugins/
  cyxj-{name}/
    skills/
      cyxj-{name}/               ← 技能文件夹名 = 插件名 = SKILL.md name
        SKILL.md              ← Skill 定义文件（frontmatter + 指令），Claude Code 运行时读取
        *.py                  ← 辅助脚本（Python 3.11+）
        *.css / *.html        ← 静态资源
        references/           ← 参考素材（部分 skill 有）
```

**关键约定**：
- 每个插件目录名以 `cyxj-` 为前缀
- `SKILL.md` 是 skill 的核心，frontmatter 中的 `name`、`description` 定义触发条件和名称
- `marketplace.json` 中的 `source` 字段指向插件目录，新增插件必须在此注册
- Python 脚本通过 `$SKILL_DIR` 或 `${CLAUDE_PLUGIN_ROOT}` 引用本地路径

## 命名规则

插件名、技能文件夹名、SKILL.md 的 `name` 字段，三处必须完全一致，格式为 `cyxj-{短名}`。

```
plugins/cyxj-foo/skills/cyxj-foo/SKILL.md   ← name: cyxj-foo
marketplace.json                             ← "name": "cyxj-foo"
```

## 修改 Skill 后的检查清单

任何对 skill 的修改（新增、重命名、删除、改内容），完成后必须逐项检查：

1. **SKILL.md frontmatter** — `name` 字段是否与文件夹名一致
2. **marketplace.json** — `name` 和 `source` 路径是否同步更新
3. **README.md** — Skills 表格是否同步更新（名称 + 链接路径）
4. **CLAUDE.md** — 技术栈速查表是否同步更新
5. **push 到 GitHub** — 本地修改不会自动同步到已安装的用户，必须 push 后才生效

## 新增 Skill 的流程

1. 创建 `plugins/cyxj-{name}/skills/cyxj-{name}/SKILL.md`（含 frontmatter，`name` 与文件夹名一致）
2. 添加辅助脚本和资源到同级目录
3. 在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中注册
4. 更新 `README.md` 的 Skills 表格
5. 更新 `CLAUDE.md` 的技术栈速查表
6. push 到 GitHub 后生效

## 常用命令

```bash
# 验证 marketplace.json 格式
python3 -m json.tool .claude-plugin/marketplace.json

# 查看当前所有已注册插件
cat .claude-plugin/marketplace.json | python3 -c "import sys,json; [print(p['name']) for p in json.load(sys.stdin)['plugins']]"
```

## 各 Skill 技术栈速查

| Skill | 核心技术 | 外部依赖 |
|-------|---------|---------|
| cyxj-subfix | Python + Gemini API + Opus 审查 | google-generativeai |
| cyxj-wechat-pub | CSS + HTML 模板 + juice（npm） | juice (npm) |
| cyxj-wechat-mask | Python (OpenCV/Pillow) | opencv-python, pillow |
| cyxj-cc-price | 纯 SKILL.md 指令 | 无 |
| cyxj-obsidian-build | 纯 SKILL.md 指令 | Obsidian 库访问 |
| cyxj-poster | Python + Gemini API | google-genai, pillow |
| cyxj-youtube-topics | Python + YouTube Data API | google-api-python-client |
| cyxj-notebook-research | Python + Notebook LM | playwright（浏览器自动化） |
