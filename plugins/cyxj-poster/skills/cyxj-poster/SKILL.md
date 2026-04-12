---
name: cyxj-poster
description: 一句话生成大师级海报/封面设计。33+设计师风格+10种摄影风格，支持多平台比例、AI提示词优化、风格对比、图生图。
---

# Poster Design Generator

一句话生成大师级海报、书籍封面、专辑封面等设计作品。基于 Mondo 丝网印刷美学，支持 33+ 传奇设计师风格和 10 种写实摄影风格。

## 脚本调用

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "subject" "type" [options]
```

### 必填参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `subject` | 设计主题 | `"Blade Runner"`, `"Jazz Festival"` |
| `type` | 设计类型 | `movie`, `book`, `album`, `event` |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--style` | 艺术家风格（见 `--list-styles`） | 自动选择 |
| `--ai-enhance` | AI 优化 prompt（保留用户原始意图） | 关闭 |
| `--compare` | 生成 3 种风格对比图 | 无 |
| `--input` | 输入图片路径（图生图转换） | 无 |
| `--ip-ref` | IP 角色参考图目录 | 无 |
| `--title` | 直接渲染在海报上的标题文字 | 无 |
| `--colors` | 配色偏好 | AI 建议 |
| `--aspect-ratio` | 画幅比例 | `9:16` |
| `--output` | 自定义输出路径 | `outputs/` |
| `--no-generate` | 只输出 prompt，不生成图片 | 关闭 |
| `--list-styles` | 列出所有可用风格 | — |

### 常用画幅比例

| 比例 | 用途 |
|------|------|
| `9:16` | 电影海报、书籍封面、手机竖屏（默认） |
| `16:9` | 文章配图、横屏封面 |
| `21:9` | 公众号封面 |
| `3:4` | 小红书配图 |
| `1:1` | 专辑封面、头像 |
| `4:3` | 通用横版 |

## 调用示例

基础生成：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "Blade Runner" movie
```

AI 优化 prompt：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "Blade Runner" movie --ai-enhance
```

3 种风格对比：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "Akira" movie --compare kilian-eng,saul-bass,jock
```

图生图转换：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "cyberpunk noir" movie --input poster.jpg --style saul-bass
```

指定配色：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "Jazz Night" event --style milton-glaser --colors "psychedelic orange, purple, yellow"
```

摄影风格：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "portrait" event --style ccd-flash
```

IP 角色海报（带标题）：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "cyberpunk tech news" event --ip-ref ./ip-reference/ --title "A社新规：禁止第三方调用" --aspect-ratio 4:3 --colors "deep navy blue, neon cyan, magenta"
```

IP 角色海报（无标题）：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "cozy reading scene" event --ip-ref ./ip-reference/ --style rixi --aspect-ratio 3:4
```

只输出 prompt：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py "Dune sci-fi epic" movie --no-generate
```

列出所有风格：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_mondo_enhanced.py --list-styles
```

## 摄影风格速查

| Key | 名称 | 特点 |
|-----|------|------|
| `ccd-flash` | CCD 闪光写真 | 2000s CCD 手机，强闪光，近距离 |
| `kodak-portra` | Kodak 胶片黄昏 | Portra 400 胶片，暖金高光，青色阴影 |
| `tyndall-forest` | 丁达尔森林 | 体积光束，斑驳阴影，浮尘 |
| `studio-afternoon` | 影楼午后光 | 白纱窗帘，暖中性色，奶油质感 |
| `cyberpunk-neon` | 赛博霓虹 | 城市阁楼，霓虹反射，金属银蓝 |
| `snow-cabin` | 雪景高调 | 极简高调，冰白，珍珠光泽 |
| `vintage-library` | 复古图书馆 | 钨丝暖灯，琥珀金，文学感 |
| `cherry-blossom` | 樱花春日 | 日系甜美，粉色散景，梦幻花瓣 |
| `desert-sunset` | 沙漠日落 | 强侧逆光，翡翠金对比 |
| `classical-garden` | 古典花园晨雾 | 晨雾，蕾丝光影，古典浪漫 |

摄影风格使用写实基底（`ultra photorealistic, cinematic photograph, 8K resolution`），生成写实照片而非丝网印刷风格。

## 交互式工作流

当用户通过 Claude Code 使用本 skill 时，按以下流程引导：

1. **确认主题** — 用户想设计什么？（电影/书籍/专辑/活动）
2. **推荐风格** — 展示 3-4 个适合的风格选项
3. **配色偏好** — 用户有想法就用，没有就让 AI 建议
4. **确认参数** — 画幅比例、是否需要标题文字等
5. **生成并展示** — 调用脚本生成，展示结果
6. **迭代调整** — 不满意可以换风格/配色重新生成

如果用户想看风格对比，用 `--compare` 生成 3 种风格并排对比图。

## 风格参考资料

详细的风格说明和设计模板在 `references/` 目录：

- [artist-styles.md](references/artist-styles.md) — 所有艺术家风格详细说明
- [genre-templates.md](references/genre-templates.md) — 按类型分类的设计模板（恐怖、科幻、西部等）
- [composition-patterns.md](references/composition-patterns.md) — 构图策略和视觉层次
- [book-covers.md](references/book-covers.md) — 书籍封面设计模式
- [prompt-examples.md](references/prompt-examples.md) — Prompt 示例和高级技巧

需要构建 prompt 或了解特定风格时，读取对应参考文件。
