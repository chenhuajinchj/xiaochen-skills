# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是一个 Claude Code 插件仓库（Plugin Marketplace），包含 8 个独立的 skill，通过 `/plugin marketplace add chenhuajinchj/xiaochen-skills` 安装到 Claude Code。

## 架构

```
.claude-plugin/marketplace.json   ← 插件市场注册表（所有插件入口）
plugins/
  cyxj-{plugin-name}/
    skills/
      {skill-name}/
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

## 新增 Skill 的流程

1. 创建 `plugins/cyxj-{name}/skills/{skill-name}/SKILL.md`（含 frontmatter）
2. 添加辅助脚本和资源到同级目录
3. 在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中注册
4. 更新 `README.md` 的 Skills 表格
5. push 到 GitHub 后生效（本地修改不会自动同步到已安装的用户）

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
