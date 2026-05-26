# 达芬奇导出 SRT 和旁白音频步骤

每周制作流程 Step 6 用。AI 不能代办，引导用户完成。

## 前置

在达芬奇里：

1. 新建工程或打开本期工程
2. 把录好的旁白音频导入媒体池
3. 拖到 Audio Track 1

## 步骤 1 — 自动生成字幕

1. 选中旁白音轨片段
2. 顶部菜单 `时间线 (Timeline)` → `创建字幕` → `从音频转录`
3. 弹窗选项：
   - **语言**：中文（普通话）
   - **字幕轨道**：新建轨道
   - **每行最多字数**：18-20 字（视频底部黑条单行能装下）
4. 点击 "创建"，等待转录完成（约 1-3 分钟）

## 步骤 2 — 校对错字（**这一步非常重要**）

达芬奇 ASR 会有错字，**不校对会直接进成品**。常见错处：

- 公司名错听：`Gemini 3.5 Flash` → `Gemini3.5Face`、`Antigravity` → `安体格拉维`
- 同音错字：`层` → `呈`、`产商` → `厂商`
- 重复或漏字：句子前半段重复说了

校对方法：

1. 在 Edit 页面双击字幕条，逐句听 + 看 + 改
2. 重点检查公司名、产品名、专有词
3. 重复的字幕条直接合并或删除

如果懒得逐句看，至少跑一遍 Inspector 的字幕搜索，找以下高频错词：

```
Gemini / Codex / Claude / DeepSeek / Anthropic / Antigravity / MiniMax / Hailuo
```

## 步骤 3 — 导出 SRT

1. 顶部菜单 `文件` → `导出字幕` (或选中字幕轨道右键 → `导出字幕`)
2. 格式选 **SRT**
3. 保存路径：

```
~/项目/试验区/ai-weekly-flash-video/docs/transcripts/voiceover.fixed.srt
```

⚠️ 文件名必须是 `voiceover.fixed.srt`，build-schedule.mjs 写死读这个路径。

## 步骤 4 — 单独导出旁白音频

1. 进入 Deliver 页面
2. 自定义预设：
   - **格式**：QuickTime
   - **视频编解码器**：不导出视频（或 None）
   - **音频编解码器**：Linear PCM
   - **采样率**：48000 Hz
   - **声道**：立体声（双声道）
   - **文件扩展名**：wav（必要时手动改）
3. 输出文件名：`voiceover.wav`
4. 保存路径：

```
~/项目/试验区/ai-weekly-flash-video/public/audio/voiceover.wav
```

⚠️ 文件名必须是 `voiceover.wav`，Remotion 写死读这个路径。

## 验证

导出后跑：

```bash
cd ~/项目/试验区/ai-weekly-flash-video
ffprobe -v error \
  -show_entries format=duration:stream=codec_name,sample_rate,channels \
  -of default=noprint_wrappers=1 \
  public/audio/voiceover.wav
```

期望：

```text
codec_name=pcm_s16le (或 pcm_s24le)
sample_rate=48000
channels=2
duration=180-210 之间
```

```bash
wc -l docs/transcripts/voiceover.fixed.srt
head -10 docs/transcripts/voiceover.fixed.srt
```

期望：行数 = 句数 × 4（每段 4 行）+ 末尾空行。头几行能看到时间码格式 `00:00:00,000 --> 00:00:02,280`。

通过验证后回到 SKILL.md Step 7 继续。
