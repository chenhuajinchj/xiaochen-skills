# NEWS 数组结构参考

每周新闻数据放在 `src/Composition.tsx` 第 30 行起的 `NEWS = [...] as const;` 数组里。

## 字段说明

```ts
{
  day: "05.18",                        // 必填。日期 MM.DD，左侧裁纸条显示
  company: "OpenAI x Dell",            // 必填。公司或主体名，新闻卡 lower-third 左侧
  title: "Codex 进入企业混合和本地环境", // 必填。主标题，新闻卡正中
  line: "Codex 不再只是写代码工具，...", // 必填。一句判断，底部黑条字幕
  source: "OpenAI",                    // 必填。信源简称，新闻卡角落显示
  region: "GLOBAL",                    // 必填。GLOBAL | CHINA | TREND
  image: "openai-dell.png",            // 必填。public/screenshots/ 下文件名
  subtitleRange: [5, 9] as [number, number] | null,  // 必填。Step 7 填，未入画则 null

  // 以下可选
  video: "01_io.mp4",                  // 可选。public/videos/ 下短视频片段（替代静图）
  tweet: "anthropic-stainless",        // 可选。public/tweets/{slug}.json 嵌入推文
}
```

## 字段写作约定

- **day**：用 `MM.DD` 格式，不要 `2026-05-18`、不要 `5/18`
- **company**：
  - 一家公司：`"OpenAI"` / `"Anthropic"`
  - 合作：`"OpenAI x Dell"`（中间用空格 + x + 空格）
  - 产品线：`"Gemini 3.5"` / `"Codex"`
  - 无明确公司：`"中国模型"` / `"国产算力"` / `"本周结论"` / `"风险提醒"`
- **title**：8-15 字最佳。陈述句，不要标点结尾。强调动作 + 对象（"收购 Stainless" / "Goal mode 全面 GA"）
- **line**：15-35 字。"发生了什么 + 为什么重要"。带判断、不只是描述
- **region**：`GLOBAL`（美/全球）、`CHINA`（中）、`TREND`（趋势分析/总结条）
- **image**：小写、连字符分隔。`<company-or-topic>.png`。例：
  - `openai-dell.png`、`anthropic-stainless.png`、`gemini-spark.png`
  - 避免：`OpenAI_Dell.png`、`openai dell.png`、`截图1.png`

## 关于 subtitleRange

`subtitleRange: [start, end]` 表示这条新闻对应 SRT 文件里第几句到第几句（1-indexed）。

例：SRT 第 5 句是"那么第一件事"、第 9 句是"它正在变成企业内部的自动化执行层"，第 1 条新闻就填 `[5, 9]`。

- 整个 NEWS 数组里所有 `subtitleRange` 区间应该是**连续不重叠**的
- 入选但出于某种原因不入画的新闻（罕见），保持 `subtitleRange: null`
- intro 和 outro 不需要在 NEWS 里标，由 `build-schedule.mjs` 自动从"第一条入画 NEWS 之前的句子"和"最后一条入画 NEWS 之后的句子"推断

## 一条完整示例（第一期数据）

```ts
{
  day: "05.18",
  company: "OpenAI x Dell",
  title: "Codex 进入企业混合和本地环境",
  line: "Codex 不再只是写代码工具，而是企业内部的自动化执行层。",
  source: "OpenAI",
  region: "GLOBAL",
  image: "openai-dell.png",
  subtitleRange: [5, 9] as [number, number] | null,
},
```

## 排序建议

数组顺序 = 视频里的播报顺序。一般按时间先后排（周一到周日），最后两条留给"本周结论"和"风险提醒/趋势观察"。

如果一天有多条相关新闻（例如 Google I/O 当天发布了 5 个产品），按"重要度从高到低"排，相当于把当天再细分。
