#!/usr/bin/env python3
"""SRT 字幕结构清理工具 - 达芬奇字幕修正 Skill v3

处理流程：strip_html → deduplicate → replace_punctuation → merge_short → split_long → renumber
导出功能：--export-txt 从 SRT 提取纯文本供 IntelliScript 使用
所有时间码操作基于精确计算，不做语义判断。
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import pysrt


# ── 辅助函数 ──────────────────────────────────────────────────────────────

def count_display_chars(text: str) -> int:
    """计算字幕显示宽度。中文/中文标点=1, ASCII=0.5, 向上取整。"""
    width = 0.0
    for ch in text:
        if ord(ch) > 0x7F:
            width += 1.0
        else:
            width += 0.5
    return math.ceil(width)


def time_gap_seconds(current_end, next_start) -> float:
    """计算两条字幕之间的间隔（秒）。"""
    end_ms = current_end.ordinal
    start_ms = next_start.ordinal
    return (start_ms - end_ms) / 1000.0


def lcs_length(a: str, b: str) -> int:
    """最长公共子序列长度。"""
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0
    # 空间优化的 DP
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def text_overlap_ratio(a: str, b: str) -> float:
    """LCS / min(len_a, len_b)，衡量文本重叠度。"""
    if not a or not b:
        return 0.0
    return lcs_length(a, b) / min(len(a), len(b))


def sub_duration_seconds(sub) -> float:
    """字幕条目时长（秒）。"""
    return (sub.end.ordinal - sub.start.ordinal) / 1000.0


def interpolate_time(start, end, ratio):
    """按比例在 start 和 end 之间插值，返回 SubRipTime。"""
    start_ms = start.ordinal
    end_ms = end.ordinal
    target_ms = int(start_ms + (end_ms - start_ms) * ratio)
    return pysrt.SubRipTime(milliseconds=target_ms)


# ── Stage 1: 清除 HTML 标签 ──────────────────────────────────────────────

def strip_html_tags(subs):
    """移除所有 HTML 标签。"""
    html_re = re.compile(r'<[^>]+>')
    count = 0
    for sub in subs:
        cleaned = html_re.sub('', sub.text)
        if cleaned != sub.text:
            count += 1
            sub.text = cleaned
    return count


# ── Stage 2: 去重 ────────────────────────────────────────────────────────

def deduplicate(subs, overlap_threshold=0.6, ghost_duration=0.3):
    """去除重复和幽灵条目。返回 (cleaned_list, removed_count)。"""
    if not subs:
        return [], 0

    to_remove = set()
    items = list(subs)

    for i in range(len(items)):
        if i in to_remove:
            continue
        for j in range(i + 1, min(i + 5, len(items))):  # 只看相邻几条
            if j in to_remove:
                continue

            text_i = items[i].text.strip()
            text_j = items[j].text.strip()
            gap = time_gap_seconds(items[i].end, items[j].start)

            # 完全重复
            if text_i == text_j:
                # 保留时长更长的
                if sub_duration_seconds(items[i]) >= sub_duration_seconds(items[j]):
                    to_remove.add(j)
                else:
                    to_remove.add(i)
                continue

            # 时间重叠（gap < 0）：达芬奇导出的桥接片段
            if gap < 0:
                # 时间重叠的条目，保留更长文本，时间取并集
                if len(text_i) >= len(text_j):
                    items[i].start = min(items[i].start, items[j].start)
                    items[i].end = max(items[i].end, items[j].end)
                    to_remove.add(j)
                else:
                    items[j].start = min(items[i].start, items[j].start)
                    items[j].end = max(items[i].end, items[j].end)
                    to_remove.add(i)
                continue

            # 高度重叠且间隔很小
            if gap < 0.5:
                ratio = text_overlap_ratio(text_i, text_j)
                if ratio > overlap_threshold:
                    # 保留更长的文本，时间取并集
                    if len(text_i) >= len(text_j):
                        items[i].start = min(items[i].start, items[j].start)
                        items[i].end = max(items[i].end, items[j].end)
                        to_remove.add(j)
                    else:
                        items[j].start = min(items[i].start, items[j].start)
                        items[j].end = max(items[i].end, items[j].end)
                        to_remove.add(i)
                    continue

            # 超短幽灵条目：< 0.3s 且文本被相邻条目包含
            if sub_duration_seconds(items[j]) < ghost_duration and text_j in text_i:
                to_remove.add(j)
            elif sub_duration_seconds(items[i]) < ghost_duration and text_i in text_j:
                to_remove.add(i)

    cleaned = [items[i] for i in range(len(items)) if i not in to_remove]

    # 后处理：消除合并操作导致的级联时间重叠
    changed = True
    while changed:
        changed = False
        new_cleaned = []
        i = 0
        while i < len(cleaned):
            if i + 1 < len(cleaned):
                gap = time_gap_seconds(cleaned[i].end, cleaned[i + 1].start)
                if gap < 0:
                    # 时间重叠，保留更长文本，时间取并集
                    a, b = cleaned[i], cleaned[i + 1]
                    if len(a.text.strip()) >= len(b.text.strip()):
                        a.start = min(a.start, b.start)
                        a.end = max(a.end, b.end)
                        new_cleaned.append(a)
                    else:
                        b.start = min(a.start, b.start)
                        b.end = max(a.end, b.end)
                        new_cleaned.append(b)
                    i += 2
                    changed = True
                    continue
            new_cleaned.append(cleaned[i])
            i += 1
        cleaned = new_cleaned

    removed_total = len(subs) - len(cleaned)
    return cleaned, removed_total


# ── Stage 3: 替换标点 ────────────────────────────────────────────────────

def replace_punctuation(subs):
    """逗号句号 → 空格，保留？！，合并连续空格。"""
    punct_re = re.compile(r'[,，.。、]')
    multi_space = re.compile(r' {2,}')

    for sub in subs:
        text = punct_re.sub(' ', sub.text)
        text = multi_space.sub(' ', text)
        text = text.strip()
        sub.text = text


# ── Stage 4: 保守合并 ────────────────────────────────────────────────────

def merge_short(subs, gap_limit=0.5, soft_limit=18):
    """保守合并短字幕。返回 (merged_list, merge_ops)。"""
    if not subs:
        return [], []

    merged = []
    merge_ops = []
    i = 0

    while i < len(subs):
        current = subs[i]
        group = [i]

        # 贪心向后尝试合并
        while i + 1 < len(subs):
            next_sub = subs[i + 1]
            gap = time_gap_seconds(current.end, next_sub.start)

            if gap > gap_limit:
                break

            combined_text = current.text + ' ' + next_sub.text
            if count_display_chars(combined_text) > soft_limit:
                break

            # 执行合并
            current_text = combined_text
            new_sub = pysrt.SubRipItem(
                start=subs[group[0]].start,
                end=next_sub.end,
                text=current_text
            )
            current = new_sub
            i += 1
            group.append(i)

        if len(group) > 1:
            merge_ops.append({
                'source': [g + 1 for g in group],  # 1-based
                'op': 'merge'
            })
        merged.append(current)
        i += 1

    return merged, merge_ops


# ── Stage 5: 强制拆分 ────────────────────────────────────────────────────

def find_split_point(text: str) -> int:
    """找最佳拆分点。优先级：？！ > 空格 > 中点强拆。"""
    mid = len(text) // 2
    best = -1

    # 优先级 1：？！
    for i, ch in enumerate(text):
        if ch in '？！?!':
            if best == -1 or abs(i - mid) < abs(best - mid):
                best = i
    if best != -1:
        return best + 1  # 在标点后拆

    # 优先级 2：空格
    for i, ch in enumerate(text):
        if ch == ' ':
            if best == -1 or abs(i - mid) < abs(best - mid):
                best = i
    if best != -1:
        return best + 1  # 在空格后拆

    # 优先级 3：中点强拆
    return mid


def split_long(subs, hard_limit=25):
    """拆分超长字幕。返回 (split_list, split_ops, needing_review)。"""
    result = []
    split_ops = []
    needing_review = []

    for idx, sub in enumerate(subs):
        if count_display_chars(sub.text) <= hard_limit:
            result.append(sub)
            continue

        # 需要拆分
        text = sub.text
        split_pos = find_split_point(text)
        part1 = text[:split_pos].strip()
        part2 = text[split_pos:].strip()

        if not part1:
            part1, part2 = part2[:len(part2) // 2], part2[len(part2) // 2:]
        if not part2:
            result.append(sub)
            continue

        # 按字符比例分配时间
        total_chars = len(part1) + len(part2)
        ratio = len(part1) / total_chars if total_chars > 0 else 0.5
        split_time = interpolate_time(sub.start, sub.end, ratio)

        sub1 = pysrt.SubRipItem(start=sub.start, end=split_time, text=part1)
        sub2 = pysrt.SubRipItem(start=split_time, end=sub.end, text=part2)

        output_idx = len(result) + 1  # 1-based
        result.append(sub1)
        result.append(sub2)
        split_ops.append({
            'source_idx': idx + 1,
            'output_indices': [output_idx, output_idx + 1],
            'op': 'split'
        })
        needing_review.append(output_idx)
        needing_review.append(output_idx + 1)

    return result, split_ops, needing_review


# ── Stage 6: 重新编号 ────────────────────────────────────────────────────

def renumber(subs):
    """重新编号。"""
    for i, sub in enumerate(subs):
        sub.index = i + 1


# ── 主流程 ────────────────────────────────────────────────────────────────

def export_intelliscript_txt(srt_path, output_path=None):
    """从 SRT 提取纯文本，供 DaVinci Resolve IntelliScript 使用。

    去掉时间码和编号，所有字幕文字用空格连接为一段连续文本。
    """
    subs = pysrt.open(srt_path, encoding='utf-8')
    texts = [sub.text.strip() for sub in subs if sub.text.strip()]
    script = ' '.join(texts)

    if output_path is None:
        p = Path(srt_path)
        output_path = str(p.parent / (p.stem.replace('_fixed', '') + '_script.txt'))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"IntelliScript 纯文本: {output_path} ({len(texts)} 条, {len(script)} 字符)")
    return output_path


def build_operation_map(original_count, merge_ops, split_ops, dedup_removed):
    """构建操作映射表（简化版，记录关键操作）。"""
    ops = []
    for m in merge_ops:
        ops.append({'source': m['source'], 'op': 'merge'})
    for s in split_ops:
        ops.append({
            'source': [s['source_idx']],
            'op': f"split_into_{len(s['output_indices'])}"
        })
    return ops


def process(input_path, output_path=None, soft_limit=18, hard_limit=25,
            gap=0.5, no_regroup=False, show_stats=False):
    """主处理流程。"""
    subs = pysrt.open(input_path, encoding='utf-8')
    input_count = len(subs)
    stats = {'input_count': input_count}

    # Stage 1: Strip HTML
    html_count = strip_html_tags(subs)
    stats['html_stripped'] = html_count

    # Stage 2: Deduplicate
    items, dedup_count = deduplicate(list(subs))
    stats['duplicates_removed'] = dedup_count

    # Stage 3: Replace punctuation
    replace_punctuation(items)

    if no_regroup:
        # 跳过合并和拆分
        renumber_list = items
        merge_ops = []
        split_ops = []
        needing_review = []
        stats['merges'] = 0
        stats['splits_forced'] = 0
    else:
        # Stage 4: Merge short
        merged, merge_ops = merge_short(items, gap_limit=gap, soft_limit=soft_limit)
        stats['merges'] = len(merge_ops)

        # Stage 5: Split long
        final, split_ops, needing_review = split_long(merged, hard_limit=hard_limit)
        stats['splits_forced'] = len(split_ops)
        renumber_list = final

    # Stage 6: Renumber
    renumber(renumber_list)

    stats['output_count'] = len(renumber_list)
    stats['splits_needing_review'] = needing_review

    # 找出超软上限但未超硬上限的条目
    over_soft = []
    for sub in renumber_list:
        chars = count_display_chars(sub.text)
        if soft_limit < chars <= hard_limit:
            over_soft.append(sub.index)
    stats['over_soft_limit'] = over_soft

    # 操作映射
    stats['operation_map'] = build_operation_map(
        input_count, merge_ops, split_ops, dedup_count
    )

    # 输出文件
    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / (p.stem + '_cleaned' + p.suffix))

    # 写入 SRT
    out_srt = pysrt.SubRipFile(items=renumber_list)
    out_srt.save(output_path, encoding='utf-8')

    # 写入 stats
    stats_path = Path(output_path).parent / (Path(output_path).stem + '_stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    if show_stats:
        print(f"输入: {stats['input_count']} 条")
        print(f"输出: {stats['output_count']} 条")
        print(f"HTML 清理: {stats['html_stripped']} 条")
        print(f"去重: {stats['duplicates_removed']} 条")
        print(f"合并: {stats['merges']} 组")
        print(f"强制拆分: {stats['splits_forced']} 条")
        print(f"超软上限: {len(stats['over_soft_limit'])} 条 {stats['over_soft_limit']}")
        print(f"需人工校验: {stats['splits_needing_review']}")
        print(f"输出文件: {output_path}")
        print(f"统计文件: {stats_path}")

    return output_path, stats


def main():
    parser = argparse.ArgumentParser(description='SRT 字幕结构清理工具')
    parser.add_argument('input', help='输入 SRT 文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认: *_cleaned.srt）')
    parser.add_argument('--soft-limit', type=int, default=18, help='软上限字符数（默认: 18）')
    parser.add_argument('--hard-limit', type=int, default=25, help='硬上限字符数（默认: 25）')
    parser.add_argument('--gap', type=float, default=0.5, help='合并间隔阈值秒（默认: 0.5）')
    parser.add_argument('--no-regroup', action='store_true', help='跳过合并和拆分')
    parser.add_argument('--stats', action='store_true', help='打印统计信息')
    parser.add_argument('--export-txt', action='store_true',
                        help='从 SRT 导出纯文本（供 IntelliScript 使用）')

    args = parser.parse_args()

    if args.export_txt:
        export_intelliscript_txt(args.input, args.output)
    else:
        process(args.input, args.output, args.soft_limit, args.hard_limit,
                args.gap, args.no_regroup, args.stats)


if __name__ == '__main__':
    main()
