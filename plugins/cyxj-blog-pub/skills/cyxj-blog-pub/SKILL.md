---
name: cyxj-blog-pub
description: >
  把文章发布到 Astro 博客。生成符合规范的 post（frontmatter 必填项校验、
  kebab-case 文件名、正文图片全部换成图床公网 URL），放进
  src/content/posts/，再 build 并部署。产出物在博客仓库，不在内容创作工作区。
  触发词：发布到博客、发博客、博客发文、上博客、Astro 发布、blog 发布。
version: 1.0.0
---

# cyxj-blog-pub — Astro 博客发布

把一篇成稿文章发到博客站点。**只做博客这一个平台**，不要顺手发别处。

## 何时用

- 用户说「发到博客」「发个博客」并指明（或已存在）一篇文章
- 文章源通常是 Obsidian `灵感库/待发布/` 的成稿，或刚由 `cyxj-transcript` 产出的草稿

**前置**：文章已成文。还是逐字稿先走 `/cyxj-transcript`。

## 项目坐标（来自内容创作 CLAUDE.md）

| 项 | 值 |
|----|----|
| 博客项目 | `~/项目/服务器/server-config/blog/` |
| 文章目录 | `src/content/posts/`（文件名 **kebab-case**） |
| 图片 | **全部用图床公网 URL**，禁止本地路径进正文 |
| 部署 | 在 `server-config` 根目录：`pnpm build` → `cp -r dist/* landing/` → `bash deploy.sh blog` |

## frontmatter 规范

```yaml
---
title: <文章标题>          # 必填
description: <一句话摘要>   # 必填
pubDate: <YYYY-MM-DD>      # 必填
tags: [<可选>]            # 可选
image: <封面图床 URL>      # 可选
draft: false              # 可选；true 则不发布
---
```

发布前**校验三个必填项齐全**，缺了就问用户或据稿补。

## 工作流

1. **取稿**：Read 文章源（路径不明就在 `灵感库/待发布/` 搜或问用户）。
2. **定文件名**：英文 kebab-case，如 `claude-code-for-non-coders.md`。
3. **处理图片（关键红线）**：正文里所有图片必须是图床 URL。
   - 本地图 → 先传图床（`img.xiaochens.com`，Lsky Pro，见内容创作 CLAUDE.md「图床操作参考」），拿到公网 URL 再写进正文。
   - **绝不把本地图片路径写进博客正文。**
4. **写 post**：组装 frontmatter + 正文，写到 `~/项目/服务器/server-config/blog/src/content/posts/<kebab>.md`。
5. **构建 + 部署**（动手前向用户确认要不要立即上线）：
   ```bash
   cd ~/项目/服务器/server-config
   pnpm build
   cp -r dist/* landing/
   bash deploy.sh blog
   ```
6. **报告**：给出文章路径 + 部署结果；失败就贴报错原文，别说「成功了」。

## 红线

- 只发博客这一个平台，不默认走多平台。
- 正文图片只用图床 URL。
- 不臆造 frontmatter；必填项缺失先确认。
- 部署是对外动作——`pnpm build` 之后、推上线之前，先跟用户确认一次。
