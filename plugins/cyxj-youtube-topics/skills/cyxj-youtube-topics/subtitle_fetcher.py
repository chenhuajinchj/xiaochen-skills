#!/usr/bin/env python3
"""拉 YouTube 视频字幕前 N 秒的纯文本。

主路径：youtube-transcript-api（直连 YouTube 网页内部接口，0.5-2s/次，
不消耗 Data API 配额，不需要 cookies）。
Fallback：yt-dlp（慢但能扛某些 IP 限流）。失败返回 None。

设计约束：
- 入口签名 fetch_subtitle(video_url_or_id, max_seconds=180) 不变
- 失败返回 None 不抛异常
- 默认前 180 秒纯文本（足够判断角度）
- stderr 打印耗时和失败原因
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_MAX_SECONDS = 180
YT_DLP_TIMEOUT = 60
YT_DLP_SLEEP_SECONDS = 5

VIDEO_ID_PATTERN = re.compile(r"([0-9A-Za-z_-]{11})")
PREFERRED_LANGS = ["en", "en-US", "en-GB"]


def _normalize(video_url_or_id: str):
    """归一化为 (video_id, url)。无法解析返回 (None, None)。"""
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", video_url_or_id):
        return video_url_or_id, f"https://www.youtube.com/watch?v={video_url_or_id}"
    m = VIDEO_ID_PATTERN.search(video_url_or_id)
    if not m:
        return None, None
    return m.group(1), video_url_or_id


def _snippets_to_text(snippets, max_seconds: int) -> str:
    """从 snippet 列表里取 start < max_seconds 的拼成纯文本。"""
    parts = []
    for s in snippets:
        if s.start >= max_seconds:
            break
        text = (s.text or "").strip()
        if text:
            parts.append(text)
    if not parts:
        return ""
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _fetch_via_transcript_api(vid: str, max_seconds: int):
    """主路径：youtube-transcript-api。
    返回 (text|None, fatal: bool)。fatal=True 表示视频本身没字幕，不要 fallback。"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
    except ImportError:
        return None, False

    api = YouTubeTranscriptApi()

    try:
        fetched = api.fetch(vid, languages=PREFERRED_LANGS)
        text = _snippets_to_text(fetched, max_seconds)
        return (text or None), False
    except (TranscriptsDisabled, VideoUnavailable):
        return None, True
    except NoTranscriptFound:
        pass
    except Exception as e:
        print(f"warn subtitle {vid}: transcript-api 异常 {type(e).__name__}: {str(e)[:120]}",
              file=sys.stderr)
        return None, False

    try:
        transcript_list = api.list(vid)
        for t in transcript_list:
            try:
                fetched = t.fetch()
                text = _snippets_to_text(fetched, max_seconds)
                if text:
                    return text, False
            except Exception:
                continue
    except (TranscriptsDisabled, VideoUnavailable):
        return None, True
    except Exception as e:
        print(f"warn subtitle {vid}: transcript-api list 失败 {type(e).__name__}",
              file=sys.stderr)
        return None, False

    return None, False


def _ytdlp_cookies_args() -> list:
    """yt-dlp cookies 参数。优先文件，其次浏览器，最后裸跑。"""
    path = os.environ.get("YT_DLP_COOKIES_PATH")
    if path and Path(path).expanduser().exists():
        return ["--cookies", str(Path(path).expanduser())]
    browser = os.environ.get("YT_DLP_COOKIES_BROWSER")
    if browser:
        return ["--cookies-from-browser", browser]
    return []


def _fetch_via_ytdlp(url: str, vid: str, max_seconds: int):
    """Fallback：yt-dlp。慢但能扛 IP 限流。返回 text|None。"""
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = str(Path(tmp) / f"sub_{vid}")
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "en.*",
            "--sub-format", "json3",
            "--sleep-subtitles", str(YT_DLP_SLEEP_SECONDS),
            "--no-warnings",
            *_ytdlp_cookies_args(),
            "-o", out_tpl,
            url,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=YT_DLP_TIMEOUT)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", "replace")[:200]
            print(f"warn subtitle {vid}: yt-dlp 失败 {stderr}", file=sys.stderr)
            return None
        except subprocess.TimeoutExpired:
            print(f"warn subtitle {vid}: yt-dlp 超时", file=sys.stderr)
            return None
        except FileNotFoundError:
            print(f"warn subtitle {vid}: yt-dlp 未安装", file=sys.stderr)
            return None

        files = list(Path(tmp).glob(f"sub_{vid}*.json3"))
        if not files:
            print(f"warn subtitle {vid}: yt-dlp 无字幕文件", file=sys.stderr)
            return None

        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
        except Exception as e:
            print(f"warn subtitle {vid}: yt-dlp 解析失败 {e}", file=sys.stderr)
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


def fetch_subtitle(video_url_or_id: str, max_seconds: int = DEFAULT_MAX_SECONDS):
    """拉前 max_seconds 秒字幕纯文本。失败返回 None。
    主路径 youtube-transcript-api，失败 fallback 到 yt-dlp。"""
    vid, url = _normalize(video_url_or_id)
    if not vid:
        return None

    t0 = time.monotonic()
    text, fatal = _fetch_via_transcript_api(vid, max_seconds)
    dt = (time.monotonic() - t0) * 1000
    if text:
        print(f"info subtitle {vid}: transcript-api 成功（{dt:.0f}ms）", file=sys.stderr)
        return text

    if fatal:
        print(f"info subtitle {vid}: 视频无字幕，跳过 fallback（{dt:.0f}ms）", file=sys.stderr)
        return None

    print(f"info subtitle {vid}: transcript-api 未取到（{dt:.0f}ms），fallback yt-dlp",
          file=sys.stderr)
    t1 = time.monotonic()
    text = _fetch_via_ytdlp(url, vid, max_seconds)
    dt2 = (time.monotonic() - t1) * 1000
    if text:
        print(f"info subtitle {vid}: yt-dlp 成功（{dt2:.0f}ms）", file=sys.stderr)
    else:
        print(f"info subtitle {vid}: yt-dlp 也失败（{dt2:.0f}ms）", file=sys.stderr)
    return text


def main():
    if len(sys.argv) < 2:
        print("用法: python3 subtitle_fetcher.py <video_url_or_id> [max_seconds]",
              file=sys.stderr)
        sys.exit(1)
    max_s = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_SECONDS
    text = fetch_subtitle(sys.argv[1], max_s)
    if text is None:
        sys.exit(2)
    print(text)


if __name__ == "__main__":
    main()
