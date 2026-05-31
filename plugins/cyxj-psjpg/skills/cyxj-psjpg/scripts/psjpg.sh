#!/bin/bash
# psjpg.sh —— 一条命令跑完「真 PS 批量导出 JPG + 清理转换痕迹」
# 1) 用本机 Photoshop 把源目录里所有 png/jpg/jpeg 导出为同名 JPG（质量可配 / Progressive / 嵌 sRGB）
# 2) 清理这些 JPG 的 XMP History，抹掉 PNG->JPG 转换痕迹，让产物看起来像 PS 原生导出
# 原文件保留不动；JPG 输出到单独目录（默认 <源目录>_psjpg）。
#
# 用法:
#   psjpg.sh <源目录> [输出目录] [质量 1-12]
# 默认:
#   输出目录 = <源目录>_psjpg；质量 = 12（PS 最高档）
#
# 依赖: 本机 Adobe Photoshop + exiftool + osascript(macOS)
# 兼容 macOS 自带 bash 3.2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSX="$SCRIPT_DIR/ps_export.jsx"
CLEAN="$SCRIPT_DIR/clean_metadata.sh"

SRC="${1:-}"
if [ -z "$SRC" ]; then
    echo "用法: psjpg.sh <源目录> [输出目录] [质量 1-12]"
    echo ""
    echo "示例:"
    echo "  psjpg.sh /Users/chenhuajin/Pictures/AI生成"
    echo "  psjpg.sh ~/Pictures/foo ~/Desktop/foo_out 11"
    exit 1
fi

# 展开 ~ 和相对路径
SRC=$(cd "$SRC" 2>/dev/null && pwd) || { echo "源目录不存在: $1" >&2; exit 1; }

OUT="${2:-${SRC}_psjpg}"
QUALITY="${3:-12}"

# 校验质量范围
if ! [[ "$QUALITY" =~ ^([1-9]|1[0-2])$ ]]; then
    echo "质量必须是 1-12，当前: $QUALITY" >&2
    exit 1
fi

# 找 PS 应用名（兼容多版本：Adobe Photoshop 2026 / 2025 / CC ...）
PS_APP=$(ls /Applications/ 2>/dev/null | grep -i "^Adobe Photoshop" | head -1)
if [ -z "$PS_APP" ]; then
    echo "未找到 Adobe Photoshop。请确认已安装在 /Applications/。" >&2
    exit 1
fi

# 校验 exiftool（第 2 步要用，提前失败比跑完一半再炸好）
if ! command -v exiftool >/dev/null 2>&1; then
    echo "未找到 exiftool（brew install exiftool）。导出能跑，但无法清理痕迹。" >&2
    exit 1
fi

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)

# 统计源文件数
TOTAL=$(find "$SRC" -maxdepth 1 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l | xargs)

echo "===== cyxj-psjpg：PS 导出 + 去痕迹 ====="
echo "PS 版本:  $PS_APP"
echo "源目录:   $SRC"
echo "输出:     $OUT"
echo "质量:     $QUALITY (Save As, Progressive 3 Scans, sRGB)"
echo "待处理:   $TOTAL 张"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "源目录里没有图片（png/jpg/jpeg），结束。"
    exit 0
fi

# 把参数写给 JSX 读取（UTF-8，支持中文路径），三行：源目录 / 输出目录 / 质量
printf '%s\n%s\n%s\n' "$SRC" "$OUT" "$QUALITY" > /tmp/cyxj_psjpg_cfg.txt

echo "===== 1/2 Photoshop 导出 JPG ====="
echo "Photoshop 启动中（会占用 PS 界面，每张约 2-4 秒）..."
START=$(date +%s)
osascript -e "tell application \"$PS_APP\" to do javascript file \"$JSX\"" >/dev/null

# ExtendScript 在 Mac 上写日志用的是老式 \r 换行，整个日志会挤成一行，
# 让下面所有 grep '^\[OK' 锚定行首匹配不到。先把 \r 统一成 \n 再处理。
LOG=/tmp/cyxj_psjpg_export.log
if [ -f "$LOG" ]; then
    tr '\r' '\n' < "$LOG" > "$LOG.norm" && mv "$LOG.norm" "$LOG"
    grep -E '^\[(OK|FAIL)' "$LOG" || true
fi

echo ""
echo "===== 2/2 清理元数据痕迹 ====="
# 输出目录是全新的，里面的 jpg 全是本次产物，直接整目录清理
"$CLEAN" "$OUT"

END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "===== 完成（耗时 ${ELAPSED} 秒）====="
SUCCESS=$(grep -c '^\[OK' /tmp/cyxj_psjpg_export.log 2>/dev/null; true)
FAIL=$(grep -c '^\[FAIL' /tmp/cyxj_psjpg_export.log 2>/dev/null; true)
SUCCESS=${SUCCESS:-0}
FAIL=${FAIL:-0}
OUT_COUNT=$(ls "$OUT"/*.jpg 2>/dev/null | wc -l | xargs)
SIZE=$(du -sh "$OUT" 2>/dev/null | awk '{print $1}')
echo "处理:     成功 $SUCCESS · 失败 $FAIL"
echo "实际输出: $OUT_COUNT 张 JPG · 总大小 $SIZE"
echo "输出位置: $OUT"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "===== 失败清单 ====="
    grep '^\[FAIL' /tmp/cyxj_psjpg_export.log || true
fi

if [ "$OUT_COUNT" -lt "$SUCCESS" ]; then
    DIFF=$((SUCCESS - OUT_COUNT))
    echo ""
    echo "提示: 处理了 $SUCCESS 张但实际只有 $OUT_COUNT 张输出——"
    echo "      源目录里可能有同名 PNG 和 JPEG 对（如 foo.png + foo.jpeg），输出会互相覆盖，差 $DIFF 张。"
fi
