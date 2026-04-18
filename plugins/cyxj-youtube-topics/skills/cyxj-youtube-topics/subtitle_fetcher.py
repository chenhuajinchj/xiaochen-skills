#!/usr/bin/env python3
"""拉 YouTube 视频字幕前 N 秒的纯文本。

主路径：Apify Actor `karamelo/youtube-transcripts`（第三方代理，走 Apify IP 池，
不会把创作者本地 IP 与抓字幕行为关联，避免 YouTube 风控）。
Fallback：Supadata（独立服务商，独立 IP 池）。

设计约束：
- 入口签名 fetch_subtitle(video_url_or_id, max_seconds=180) 不变
- 失败返回 None 不抛异常
- 默认前 180 秒纯文本（足够判断角度）
- stderr 打印耗时和失败原因
"""

import html
import json
import re
import sys
import time
import urllib.request

from paths import load_apify_token, load_supadata_key

DEFAULT_MAX_SECONDS = 180

VIDEO_ID_PATTERN = re.compile(r"([0-9A-Za-z_-]{11})")


def _normalize(video_url_or_id: str):
    """归一化为 (video_id, url)。无法解析返回 (None, None)。"""
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", video_url_or_id):
        return video_url_or_id, f"https://www.youtube.com/watch?v={video_url_or_id}"
    m = VIDEO_ID_PATTERN.search(video_url_or_id)
    if not m:
        return None, None
    return m.group(1), video_url_or_id


def _fetch_via_karamelo(vid: str, max_seconds: int):
    """主路径：Apify karamelo/youtube-transcripts Actor。失败返回 None。"""
    token = load_apify_token()
    api_url = (
        "https://api.apify.com/v2/acts/karamelo~youtube-transcripts"
        "/run-sync-get-dataset-items"
    )
    body = json.dumps({"urls": [f"https://www.youtube.com/watch?v={vid}"]}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.4.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status != 201:
                print(f"warn karamelo {vid}: HTTP {r.status}", file=sys.stderr)
                return None
            items = json.loads(r.read())
    except Exception as e:
        print(
            f"warn karamelo {vid}: {type(e).__name__} {str(e)[:120]}",
            file=sys.stderr,
        )
        return None

    if not items:
        return None
    item = items[0] or {}

    caps = item.get("captions") or []
    if caps:
        joined = " ".join(c for c in caps if c).strip()
        if joined:
            approx_chars = max_seconds * 60
            return html.unescape(joined[:approx_chars])
    return None


def _fetch_via_supadata(vid: str, max_seconds: int):
    """Fallback：Supadata。文本模式无时间戳，按字符数粗估截断。失败返回 None。"""
    key = load_supadata_key()
    if not key:
        return None
    api_url = (
        f"https://api.supadata.ai/v1/youtube/transcript?videoId={vid}&text=true"
    )
    req = urllib.request.Request(
        api_url,
        headers={
            "x-api-key": key,
            "User-Agent": "curl/8.4.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                print(f"warn supadata {vid}: HTTP {r.status}", file=sys.stderr)
                return None
            d = json.loads(r.read())
    except Exception as e:
        print(
            f"warn supadata {vid}: {type(e).__name__} {str(e)[:120]}",
            file=sys.stderr,
        )
        return None

    text = d.get("content", "")
    if not text:
        return None
    approx_chars = max_seconds * 60
    return text[:approx_chars]


def fetch_subtitle(video_url_or_id: str, max_seconds: int = DEFAULT_MAX_SECONDS):
    """拉前 max_seconds 秒字幕纯文本。失败返回 None。
    主路径 Apify karamelo，失败 fallback 到 Supadata。"""
    vid, _ = _normalize(video_url_or_id)
    if not vid:
        return None

    t0 = time.monotonic()
    text = _fetch_via_karamelo(vid, max_seconds)
    dt = (time.monotonic() - t0) * 1000
    if text:
        print(f"info subtitle {vid}: karamelo 成功（{dt:.0f}ms）", file=sys.stderr)
        return text

    print(
        f"info subtitle {vid}: karamelo 未取到（{dt:.0f}ms），fallback supadata",
        file=sys.stderr,
    )
    t1 = time.monotonic()
    text = _fetch_via_supadata(vid, max_seconds)
    dt2 = (time.monotonic() - t1) * 1000
    if text:
        print(f"info subtitle {vid}: supadata 成功（{dt2:.0f}ms）", file=sys.stderr)
    else:
        print(f"info subtitle {vid}: supadata 也失败（{dt2:.0f}ms）", file=sys.stderr)
    return text


def main():
    if len(sys.argv) < 2:
        print(
            "用法: python3 subtitle_fetcher.py <video_url_or_id> [max_seconds]",
            file=sys.stderr,
        )
        sys.exit(1)
    max_s = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_SECONDS
    text = fetch_subtitle(sys.argv[1], max_s)
    if text is None:
        sys.exit(2)
    print(text)


if __name__ == "__main__":
    main()
