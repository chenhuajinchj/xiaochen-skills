#!/usr/bin/env python3
"""SRT 字幕语义修正工具 - 达芬奇字幕修正 Skill v4

用 Gemini Flash Lite 做初修，输出修正后的 SRT 和修改清单。
依赖：google-genai, pysrt
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import pysrt
from google import genai
from google.genai import types

# ── 配置 ──────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
PREMIUM_MODEL = "gemini-3-flash-preview"
BATCH_SIZE = 40  # 每批字幕条数
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

SKILL_DIR = Path(__file__).parent
DICTIONARY_PATH = SKILL_DIR / "dictionary.json"

# ── 词典加载 ──────────────────────────────────────────────────────────────

def load_dictionary() -> dict:
    """加载词典，构建 错误词→正确词 的映射。"""
    if not DICTIONARY_PATH.exists():
        return {}

    with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 反转词典：corrections 格式是 正确词→[错误变体列表]
    error_to_correct = {}
    for correct, variants in data.get("corrections", {}).items():
        for variant in variants:
            error_to_correct[variant] = correct

    # user_additions 同理
    for correct, variants in data.get("user_additions", {}).items():
        for variant in variants:
            error_to_correct[variant] = correct

    return error_to_correct


def format_dictionary_for_prompt(error_map: dict) -> str:
    """将词典格式化为 prompt 中的参考列表。"""
    if not error_map:
        return "（无已知词典映射）"

    # 按正确词分组
    correct_to_errors = {}
    for error, correct in error_map.items():
        correct_to_errors.setdefault(correct, []).append(error)

    lines = []
    for correct, errors in sorted(correct_to_errors.items()):
        errors_str = "、".join(errors)
        lines.append(f"  {errors_str} → {correct}")

    return "\n".join(lines)


# ── Gemini API 调用 ───────────────────────────────────────────────────────

def build_system_prompt(topic: str, dict_text: str) -> str:
    """构建系统提示词。"""
    return f"""你是一个专业的中文字幕校对员。你的任务是修正语音识别（ASR）产生的错误。

## 视频主题
{topic}

## 已知错误词典（ASR 常见错误 → 正确写法）
{dict_text}

## 修正规则
1. **同音字/近音字修正**：ASR 经常把专业术语识别成同音的常见词，结合主题语境判断并修正
2. **去口吃重复**：如"我说的我说的我说的"→"我说的"
3. **去填充词**：删除"嗯""啊""那个""就是说"等口头禅（如果整条都是填充词，文字留空）
4. **保持口语化**：不要书面化改写，保留说话人的自然表达风格
5. **不确定就不改**：如果不确定某个词是否有误，保持原样

## 输出格式
只返回一个 JSON 数组，包含你修改过的条目。未修改的条目不要包含。
每个元素格式：
{{"index": 条目编号, "original": "原文", "fixed": "修正后", "reason": "修正原因"}}

如果这批字幕没有需要修正的内容，返回空数组 []

重要：只返回 JSON 数组，不要有任何其他文字。"""


def build_batch_prompt(subs_batch: list[tuple[int, str]]) -> str:
    """构建单批字幕的用户提示词。"""
    lines = []
    for idx, text in subs_batch:
        lines.append(f"[{idx}] {text}")
    return "请检查以下字幕并修正错误：\n\n" + "\n".join(lines)


def parse_gemini_response(response_text: str) -> list[dict]:
    """解析 Gemini 返回的 JSON 修改清单。"""
    text = response_text.strip()

    # 去掉可能的 markdown 代码块标记
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    text = text.strip()
    if not text:
        return []

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        # 尝试提取 JSON 数组
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        print(f"  ⚠ 无法解析 Gemini 响应，跳过此批", file=sys.stderr)
        return []


def call_gemini_batch(client, model: str, system_prompt: str,
                      batch: list[tuple[int, str]]) -> list[dict]:
    """调用 Gemini API 处理一批字幕。"""
    user_prompt = build_batch_prompt(batch)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,  # 低温度，追求准确
                    max_output_tokens=4096,
                )
            )

            if response.text:
                return parse_gemini_response(response.text)
            return []

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠ API 错误 (重试 {attempt + 1}/{MAX_RETRIES}): {e}",
                      file=sys.stderr)
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"  ✗ API 失败，跳过此批: {e}", file=sys.stderr)
                return []


# ── 主处理流程 ────────────────────────────────────────────────────────────

def process_srt(input_path: str, topic: str, model: str = DEFAULT_MODEL,
                batch_size: int = BATCH_SIZE) -> tuple[str, str]:
    """处理 SRT 文件，返回 (输出SRT路径, 修改清单路径)。"""

    # 初始化 Gemini 客户端
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("✗ 未找到 GEMINI_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 加载文件和词典
    subs = pysrt.open(input_path, encoding="utf-8")
    error_map = load_dictionary()
    dict_text = format_dictionary_for_prompt(error_map)
    system_prompt = build_system_prompt(topic, dict_text)

    print(f"📝 输入: {input_path} ({len(subs)} 条字幕)")
    print(f"🤖 模型: {model}")
    print(f"📖 词典: {len(error_map)} 个已知错误映射")
    print(f"📦 批次大小: {batch_size}")
    print()

    # 准备批次
    all_items = [(sub.index, sub.text.strip()) for sub in subs]
    batches = []
    for i in range(0, len(all_items), batch_size):
        batches.append(all_items[i:i + batch_size])

    # 逐批处理
    all_changes = []
    total_fixed = 0

    for batch_idx, batch in enumerate(batches):
        start_idx = batch[0][0]
        end_idx = batch[-1][0]
        print(f"  处理批次 {batch_idx + 1}/{len(batches)} "
              f"(#{start_idx}-#{end_idx})...", end=" ", flush=True)

        changes = call_gemini_batch(client, model, system_prompt, batch)

        if changes:
            all_changes.extend(changes)
            total_fixed += len(changes)
            print(f"✓ {len(changes)} 处修正")
        else:
            print("✓ 无需修正")

        # 避免 API 限流
        if batch_idx < len(batches) - 1:
            time.sleep(0.5)

    print()
    print(f"📊 总计: {total_fixed} 处修正 / {len(subs)} 条字幕")

    # 应用修正到 SRT
    changes_map = {}
    for change in all_changes:
        idx = change.get("index")
        if idx is not None:
            changes_map[idx] = change

    for sub in subs:
        if sub.index in changes_map:
            sub.text = changes_map[sub.index]["fixed"]

    # 输出文件
    p = Path(input_path)
    output_srt = str(p.parent / (p.stem.replace("_cleaned", "") + "_gemini_fixed" + p.suffix))
    output_json = str(p.parent / (p.stem.replace("_cleaned", "") + "_changes.json"))

    subs.save(output_srt, encoding="utf-8")

    changes_output = {
        "model": model,
        "topic": topic,
        "total_subtitles": len(subs),
        "total_changes": len(all_changes),
        "changes": all_changes,
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(changes_output, f, ensure_ascii=False, indent=2)

    print(f"✅ 修正后字幕: {output_srt}")
    print(f"📋 修改清单: {output_json}")

    return output_srt, output_json


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SRT 字幕语义修正工具 (Gemini Flash)")
    parser.add_argument("input", help="输入 SRT 文件路径（通常是 _cleaned.srt）")
    parser.add_argument("--topic", required=True,
                        help="视频主题（用于语境判断，如 'Claude Code教程'）")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Gemini 模型 ID（默认: {DEFAULT_MODEL}）")
    parser.add_argument("--premium", action="store_true",
                        help=f"使用高端模型 ({PREMIUM_MODEL})")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"每批处理条数（默认: {BATCH_SIZE}）")

    args = parser.parse_args()

    model = PREMIUM_MODEL if args.premium else args.model
    process_srt(args.input, args.topic, model, args.batch_size)


if __name__ == "__main__":
    main()
