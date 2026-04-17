#!/usr/bin/env python3
"""共享路径与密钥配置 — 全部从环境变量读取，缺失时给出清晰引导。"""

import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent


def load_youtube_api_key() -> str:
    """按优先级查找 YOUTUBE_API_KEY。

    1. 环境变量 YOUTUBE_API_KEY
    2. ${SKILL_DIR}/.env
    3. ~/.config/cyxj/.env
    """
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key.strip()

    for env_path in (SKILL_DIR / ".env", Path.home() / ".config" / "cyxj" / ".env"):
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("YOUTUBE_API_KEY="):
                    return line.split("=", 1)[1].strip(' "\'\n\r')

    print(
        "错误：未找到 YOUTUBE_API_KEY。请按以下任一方式配置：\n"
        "  1. 环境变量：export YOUTUBE_API_KEY=你的key\n"
        f"  2. 在 {SKILL_DIR}/.env 写入：YOUTUBE_API_KEY=你的key\n"
        "  3. 在 ~/.config/cyxj/.env 写入：YOUTUBE_API_KEY=你的key\n"
        "获取 API key：https://console.cloud.google.com/apis/credentials",
        file=sys.stderr,
    )
    sys.exit(1)


def get_topic_dir() -> Path:
    """返回 Obsidian 选题库目录路径。从环境变量 CYXJ_TOPIC_DIR 读取。"""
    env_path = os.environ.get("CYXJ_TOPIC_DIR")
    if not env_path:
        print(
            "错误：未设置 CYXJ_TOPIC_DIR 环境变量。\n"
            "请指向你 Obsidian 库中存放 YouTube 选题的目录，例如：\n"
            "  export CYXJ_TOPIC_DIR=\"$HOME/obsidian/灵感库/选题库\"\n"
            "建议把这一行加到 ~/.zshrc 或 ~/.bashrc。",
            file=sys.stderr,
        )
        sys.exit(1)
    return Path(env_path).expanduser()
