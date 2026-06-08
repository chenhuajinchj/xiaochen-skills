#!/usr/bin/env python3
"""
视频封面生成（真人版）

用 gpt-image-2（GPTIMG2 中转站 api.chatgpt-code.com）+ 你的真人照片，生成带本人形象的封面。
照片走 /v1/images/edits 端点重绘入场，人脸保持一致；输出 2K 级别大图，url 方式返回后落地。
默认输出 4 个比例（YouTube 16:9 / 公众号 2.35:1 / 竖版 3:4 / 横版 4:3），
每比例 2 张供挑选，全部并行生成（约 1 分钟出齐）。

用法：
  python3 generate.py --title "封面标题"
  python3 generate.py --title "封面标题" --face ~/Pictures/封面形象/某张.png
  python3 generate.py --title "封面标题" --ratios 16:9,3:4 --n 1
  python3 generate.py --title "封面标题" --scene "坐在电脑前敲代码"

key 与中转站地址自动从密钥存储读取（无需手动 export）：
  ~/项目/自己的应用/密钥存储/.env 里的 GPTIMG2_BASE_URL / GPTIMG2_API_KEY
也可用环境变量覆盖：GPTIMG2_BASE_URL / GPTIMG2_API_KEY
注意：GPTIMG2_BASE_URL（https://api.chatgpt-code.com）末尾【没有】/v1，脚本拼端点时自己补。
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---- 默认配置 ----
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_FACE_DIR = Path.home() / "Pictures" / "封面形象"
KEY_STORE = Path.home() / "项目" / "自己的应用" / "密钥存储" / ".env"

# 比例 → 尺寸（2K 级别；边长均为 16 的倍数、长短比 ≤ 3:1，gpt-image-2 原生支持）
RATIO_SIZE = {
    "16:9": "2560x1440",    # YouTube 缩略图（2K）
    "2.35:1": "2560x1088",  # 公众号分享大图（长短比 2.35:1，对齐 16）
    "3:4": "1536x2048",     # 竖版（2K）
    "4:3": "2048x1536",     # 横版（2K）
}
DEFAULT_RATIOS = "16:9,2.35:1,3:4,4:3"


def _api_base(base: str) -> str:
    """把读到的 base 规整成可直接拼端点的形式：补全到以 /v1 结尾。

    GPTIMG2_BASE_URL = https://api.chatgpt-code.com（末尾【没有】/v1），需自己补；
    但若用户万一填了带 /v1 的，则不重复加。返回值不含末尾斜杠，
    端点直接 base + "/images/generations" / "/images/edits" 即可。
    """
    base = base.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


def load_credentials() -> tuple[str, str]:
    """读 base_url 和 api_key：环境变量优先，否则从密钥存储 .env 解析。

    返回的 base 已规整到以 /v1 结尾，调用方直接拼 /images/edits 等端点。
    """
    base = os.environ.get("GPTIMG2_BASE_URL")
    key = os.environ.get("GPTIMG2_API_KEY")
    if base and key:
        return _api_base(base), key

    if KEY_STORE.exists():
        for line in KEY_STORE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k == "GPTIMG2_BASE_URL" and not base:
                base = v
            elif k == "GPTIMG2_API_KEY" and not key:
                key = v

    if not base or not key:
        print(
            "❌ 找不到中转站配置。需要 GPTIMG2_BASE_URL 和 GPTIMG2_API_KEY。\n"
            f"   已查找：环境变量 + {KEY_STORE}\n"
            "   请在密钥存储 .env 里确认这两行存在，或先 export。",
            file=sys.stderr,
        )
        sys.exit(1)
    return _api_base(base), key


def resolve_faces(face_arg: str | None) -> list[Path]:
    """确定参考人脸图：--face 指定（文件或目录）优先，否则用默认素材库目录。"""
    target = Path(face_arg).expanduser() if face_arg else DEFAULT_FACE_DIR
    if target.is_file():
        return [target]
    if target.is_dir():
        imgs = sorted(
            p for p in target.iterdir()
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        )
        if not imgs:
            print(f"❌ {target} 里没有图片（png/jpg/jpeg/webp）", file=sys.stderr)
            sys.exit(1)
        # 默认只用第 1 张做主参考（多图更保真但更慢；需要时改这里取多张）
        return imgs[:1]
    print(f"❌ 参考图路径不存在：{target}", file=sys.stderr)
    sys.exit(1)


def build_prompt(title: str, scene: str | None) -> str:
    """构建封面 prompt。人在一侧、标题留白另一侧，高点击 YouTube 风格。

    背景默认走简洁路线（纯色/弱虚化、少道具），让人物和标题主导画面，
    避免背景太花抢视线。需要具体场景时用 --scene 传入。
    """
    scene_line = (
        f"The person is in this scene: {scene}." if scene
        else "Give the person a meaningful pose that fits the title; "
             "keep the surroundings minimal, no clutter."
    )
    return (
        "Create a high click-through video cover / YouTube thumbnail. "
        "Keep the SAME real person from the reference photo — same face, "
        "same identity (do NOT turn into a cartoon or 3D character; keep photorealistic). "
        "Composition: the person on one side as upper body, looking at camera with a "
        "vivid, confident, slightly excited expression. "
        "Leave clean space on the other side for a large bold Chinese title. "
        f"{scene_line} "
        "Background: SIMPLE and CLEAN — a solid or softly gradient color, or a heavily "
        "blurred minimal setting. Avoid busy or cluttered backgrounds; do NOT fill it with "
        "many props, screens, or UI panels. Keep the subject and title clearly dominant. "
        f'Add this large bold Chinese title prominently: "{title}". '
        "The title text must be accurate, large, high-contrast and easy to read "
        "(black or white with an accent color outline). "
        "Vivid, eye-catching, professional thumbnail style."
    )


def _multipart(fields: dict[str, str], image_paths: list[Path]) -> tuple[bytes, str]:
    """组装 multipart/form-data 请求体。"""
    boundary = "----cyxjvideocover7f3a"
    parts: list[bytes] = []
    for name, val in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode()
        )
    for p in image_paths:
        data = p.read_bytes()
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        parts.append(
            (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
             f'filename="{p.name}"\r\nContent-Type: {mime}\r\n\r\n').encode()
            + data + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def generate_one(
    base: str, key: str, model: str, title: str, scene: str | None,
    ratio: str, idx: int, faces: list[Path], output_dir: Path,
) -> Path | None:
    """生成单张封面。返回保存路径或 None。"""
    size = RATIO_SIZE.get(ratio)
    if not size:
        # 自定义比例兜底：交给中转站 auto
        size = "auto"
    # edits 是 multipart 表单：size / response_format 作为表单字段传，要求返回图片 url
    body, boundary = _multipart(
        {
            "model": model,
            "prompt": build_prompt(title, scene),
            "size": size,
            "n": "1",
            "response_format": "url",
        },
        faces,
    )
    req = urllib.request.Request(
        base + "/images/edits", data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            # 中转站结果文件 CDN(files.chatgpt-topup.com)会拦 urllib 默认 UA(403)，统一带浏览器 UA
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    safe_ratio = ratio.replace(":", "x").replace(".", "_")
    out_path = output_dir / f"cover_{safe_ratio}_{idx}.png"
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
        item = d["data"][0]
        # 契约：优先走 url（response_format=url）下载落地；b64_json 作兜底
        if item.get("url"):
            # 下载结果图：CDN 拦 urllib 默认 UA(403)，必须带浏览器 UA
            dl_req = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(dl_req, timeout=120) as ir:
                output_dir.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(ir.read())
            return out_path
        if item.get("b64_json"):
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(item["b64_json"]))
            return out_path
        print(f"⚠ {ratio} #{idx}: 返回里没有图片", file=sys.stderr)
        return None
    except urllib.error.HTTPError as e:
        print(f"❌ {ratio} #{idx}: HTTP {e.code} {e.read().decode()[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ {ratio} #{idx}: {type(e).__name__} {str(e)[:200]}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="视频封面生成（真人版）")
    parser.add_argument("--title", required=True, help="封面标题文字")
    parser.add_argument("--scene", default=None, help="场景/动作描述（可选，不给则按标题自动）")
    parser.add_argument("--ratios", default=DEFAULT_RATIOS,
                        help=f"输出比例，逗号分隔（默认全部：{DEFAULT_RATIOS}）")
    parser.add_argument("--n", type=int, default=2, help="每个比例出几张（默认 2）")
    parser.add_argument("--face", default=None,
                        help=f"参考人脸图，文件或目录（默认 {DEFAULT_FACE_DIR}）")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型（默认 {DEFAULT_MODEL}）")
    parser.add_argument("--output", default=".", help="输出目录（默认当前目录）")
    args = parser.parse_args()

    base, key = load_credentials()
    faces = resolve_faces(args.face)
    ratios = [r.strip() for r in args.ratios.split(",") if r.strip()]
    output_dir = Path(args.output).expanduser().resolve()

    print("🎬 视频封面生成（真人版）")
    print(f"   标题: {args.title}")
    print(f"   场景: {args.scene or '(按标题自动)'}")
    print(f"   比例: {', '.join(ratios)}  ×{args.n} 张")
    print(f"   参考: {', '.join(p.name for p in faces)}")
    print(f"   模型: {args.model} @ {base}")
    print(f"   输出: {output_dir}")
    print(f"   共 {len(ratios) * args.n} 张，并行生成中...\n")

    jobs = [(r, i + 1) for r in ratios for i in range(args.n)]
    results: list[Path] = []
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as ex:
        futs = {
            ex.submit(generate_one, base, key, args.model, args.title,
                      args.scene, r, i, faces, output_dir): (r, i)
            for r, i in jobs
        }
        for fut in as_completed(futs):
            r, i = futs[fut]
            p = fut.result()
            if p:
                results.append(p)
                print(f"  ✅ {r} #{i} → {p.name}")

    print(f"\n{'=' * 50}")
    print(f"🏁 完成！{len(results)}/{len(jobs)} 张")
    for p in sorted(results):
        print(f"   📄 {p}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
