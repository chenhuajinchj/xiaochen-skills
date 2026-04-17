#!/usr/bin/env python3
"""拉 YouTube 视频字幕前 N 秒的纯文本，用 yt-dlp。失败返回 None。

设计约束：
- 只拉自动字幕（绝大多数英文视频都有）
- 默认前 180 秒（足够判断角度，省 LLM token）
- 加 --sleep-subtitles 防 IP 封
- 失败返回 None 不抛异常，调用方好 fallback
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_MAX_SECONDS = 180
YT_DLP_TIMEOUT = 60
SLEEP_SECONDS = 5

VIDEO_ID_PATTERN = re.compile(r"([0-9A-Za-z_-]{11})")


def _cookies_args() -> list:
    """返回 yt-dlp 的 cookies 参数。按优先级：
    1. YT_DLP_COOKIES_PATH 指向的 Netscape 格式 cookies 文件
    2. YT_DLP_COOKIES_BROWSER （如 "safari"、"chrome"）
    3. 无——直接裸请求，会被 YouTube 拦截
    """
    path = os.environ.get("YT_DLP_COOKIES_PATH")
    if path and Path(path).expanduser().exists():
        return ["--cookies", str(Path(path).expanduser())]
    browser = os.environ.get("YT_DLP_COOKIES_BROWSER")
    if browser:
        return ["--cookies-from-browser", browser]
    return []


def _normalize(video_url_or_id: str):
    """把入参归一化为 (video_id, url)。无法解析返回 (None, None)。"""
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", video_url_or_id):
        return video_url_or_id, f"https://www.youtube.com/watch?v={video_url_or_id}"
    m = VIDEO_ID_PATTERN.search(video_url_or_id)
    if not m:
        return None, None
    return m.group(1), video_url_or_id


def fetch_subtitle(video_url_or_id: str, max_seconds: int = DEFAULT_MAX_SECONDS):
    """拉前 max_seconds 秒的字幕纯文本，失败返回 None。"""
    vid, url = _normalize(video_url_or_id)
    if not vid:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = str(Path(tmp) / f"sub_{vid}")
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "en.*",
            "--sub-format", "json3",
            "--sleep-subtitles", str(SLEEP_SECONDS),
            "--no-warnings",
            *_cookies_args(),
            "-o", out_tpl,
            url,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=YT_DLP_TIMEOUT)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", "replace")[:200]
            print(f"warn subtitle_fetch {vid}: yt-dlp 失败 {stderr}", file=sys.stderr)
            return None
        except subprocess.TimeoutExpired:
            print(f"warn subtitle_fetch {vid}: 超时", file=sys.stderr)
            return None

        files = list(Path(tmp).glob(f"sub_{vid}*.json3"))
        if not files:
            print(f"warn subtitle_fetch {vid}: 无字幕文件", file=sys.stderr)
            return None

        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
        except Exception as e:
            print(f"warn subtitle_fetch {vid}: 解析失败 {e}", file=sys.stderr)
            return None

        max_ms = max_seconds * 1000
        parts = []
        for event in data.get("events", []):
            if event.get("tStartMs", 0) >= max_ms:
                break
            for seg in event.get("segs", []):
                text = seg.get("utf8", "")
                if text and text.strip():
                    parts.append(text)
        if not parts:
            return None
        return re.sub(r"\s+", " ", " ".join(parts)).strip()


def main():
    if len(sys.argv) < 2:
        print("用法: python3 subtitle_fetcher.py <video_url_or_id> [max_seconds]", file=sys.stderr)
        sys.exit(1)
    max_s = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_SECONDS
    text = fetch_subtitle(sys.argv[1], max_s)
    if text is None:
        sys.exit(2)
    print(text)


if __name__ == "__main__":
    main()
