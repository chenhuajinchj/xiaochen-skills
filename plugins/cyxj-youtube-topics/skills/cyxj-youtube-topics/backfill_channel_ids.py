#!/usr/bin/env python3
"""一次性 backfill：给创作者索引里 is_quality=True 但 channel_id 为空的创作者补 channelId。

两种模式：
  1. 手工字典模式（默认，零 YouTube quota）：内置 KNOWN_CHANNEL_IDS 映射，遇到匹配的名字就补
  2. API 查询模式（--api）：对剩余无映射的创作者调 search.list?type=channel 自动查找
     成本：每个查询 100 quota

用法：
  python3 backfill_channel_ids.py             # 手工字典模式 + 报告
  python3 backfill_channel_ids.py --dry-run   # 只看会改什么，不真写入
  python3 backfill_channel_ids.py --api       # 手工字典 + 剩余的走 API 兜底
"""

import argparse
import json
import sys
from pathlib import Path

import requests

from paths import get_topic_dir, load_youtube_api_key

CREATOR_INDEX_PATH = get_topic_dir() / "创作者索引.json"
API_BASE = "https://www.googleapis.com/youtube/v3"

# 手工查证的 channelId 映射（避免烧 YouTube quota）
KNOWN_CHANNEL_IDS = {
    "Chase AI": "UCoy6cTJ7Tg0dqS-DI-_REsA",
    "Nate Herk | AI Automation": "UC2ojq-nuP8ceeHqiroeKhBA",
    "John Kim": "UCiZotp9tZ4uXgXEjHDUYzBQ",
    "IndyDevDan": "UC_x36zCEGilGpB1m-V4gmjg",
    "Brian Casel": "UCSxPE9PHHxQUEt6ajGmQyMA",
    "Jack Roberts": "UCxVxcTULO9cFU6SB9qVaisQ",
    "Build Great Products": "UCZRp6-Xvzo_dBFvt9L7y3Qw",
    "Chris Raroque": "UC4x3CR25WSlvMJUtSPPzwwg",
    "ThePrimeagenHighlights": "UChk6TQce1EJMn6_liKdHDog",
    "Theo - t3.gg": "UCbRP3c757lWg9M-U7TyEkXA",
    "Alex Ziskind": "UCajiMK_CY9icRhLepS8_3ug",
    "Greg Isenberg": "UCPjNBjflYl0-HQtUvOx0Ibw",
    "David Ondrej": "UCPGrgwfbkjTIgPoOh2q1BAg",
    "Ishan Sharma": "UCY6N8zZhs2V7gNTUxPuKWoQ",
    "Vaibhav Sisinty": "UClXAalunTPaX1YV185DWUeg",
    "Malewicz": "UC6dx8XTw7cjBsRLgSFTJT1g",
}


def resolve_via_api(api_key: str, channel_name: str) -> str:
    """调 search.list 用频道名查 channelId。失败返回空字符串。每次 100 quota。"""
    try:
        resp = requests.get(f"{API_BASE}/search", params={
            "key": api_key,
            "q": channel_name,
            "type": "channel",
            "part": "snippet",
            "maxResults": 1,
        }, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return ""
        return items[0].get("snippet", {}).get("channelId", "") or items[0].get("id", {}).get("channelId", "")
    except Exception as e:
        print(f"  API 查询失败 ({e})", file=sys.stderr)
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写入")
    ap.add_argument("--api", action="store_true", help="手工字典之外的走 API 兜底（烧 quota）")
    args = ap.parse_args()

    if not CREATOR_INDEX_PATH.exists():
        print(f"错误：创作者索引不存在 {CREATOR_INDEX_PATH}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(CREATOR_INDEX_PATH.read_text(encoding="utf-8"))
    creators = data.get("creators", {})

    needs_backfill = [
        name for name, c in creators.items()
        if c.get("is_quality") and not c.get("channel_id")
    ]
    print(f"待 backfill 创作者（is_quality=True 且 channel_id 为空）：{len(needs_backfill)} 个")

    filled_manual = 0
    filled_api = 0
    failed = []
    api_key = ""

    for name in needs_backfill:
        if name in KNOWN_CHANNEL_IDS:
            cid = KNOWN_CHANNEL_IDS[name]
            avg = creators[name].get("avg_views", 0)
            print(f"  [手工] {name}  ({cid})  avg={avg}")
            if not args.dry_run:
                creators[name]["channel_id"] = cid
            filled_manual += 1
        elif args.api:
            if not api_key:
                api_key = load_youtube_api_key()
            cid = resolve_via_api(api_key, name)
            if cid:
                avg = creators[name].get("avg_views", 0)
                print(f"  [API]  {name}  ({cid})  avg={avg}")
                if not args.dry_run:
                    creators[name]["channel_id"] = cid
                filled_api += 1
            else:
                print(f"  [失败] {name}  API 查询无结果")
                failed.append(name)
        else:
            failed.append(name)

    if not args.dry_run and (filled_manual or filled_api):
        data["creators"] = creators
        CREATOR_INDEX_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n已写入 {CREATOR_INDEX_PATH}")
    elif args.dry_run:
        print("\n[--dry-run] 没有真写入")

    print(f"\n统计：手工填充 {filled_manual} / API 填充 {filled_api} / 未匹配 {len(failed)}")
    if failed:
        print("未填充的（KNOWN_CHANNEL_IDS 没有，且未启用 --api 或 API 查不到）：")
        for n in failed[:20]:
            avg = creators[n].get("avg_views", 0)
            print(f"  - {n}  (avg={avg})")
        if len(failed) > 20:
            print(f"  ... 还有 {len(failed) - 20} 个")


if __name__ == "__main__":
    main()
