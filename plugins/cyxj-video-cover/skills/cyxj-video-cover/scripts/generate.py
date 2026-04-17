#!/usr/bin/env python3
"""
视频封面生成脚本

使用 Gemini API + IP 参考图 + 风格参考图，生成 3D 渲染风格的视频封面。
默认输出 4:3 横版 + 3:4 竖版两张。

用法：
  python3 generate.py --title "封面标题"
  python3 generate.py --title "封面标题" --scene "角色坐在电脑前编程"
  python3 generate.py --title "封面标题" --ratios 4:3 --output ./covers/
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

# 路径常量
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STYLE_REF = SKILL_DIR / "style-reference" / "reference.png"


def get_ip_ref_dir() -> Path:
    """从环境变量 CYXJ_IP_REF_DIR 读取 IP 参考图目录。

    目录约定：
      - 任意数量的 .png 参考图（建议至少 1 张正面图 + 1 张多视角设定图）
      - ip-description.txt — IP 形象的英文描述段落，用于注入 Gemini prompt
    """
    env_path = os.environ.get("CYXJ_IP_REF_DIR")
    if not env_path:
        print(
            "❌ 未设置 CYXJ_IP_REF_DIR 环境变量。\n"
            "请准备 IP 形象资料目录后设置：\n"
            "  export CYXJ_IP_REF_DIR=/path/to/your/ip-reference/\n"
            "目录里需要：\n"
            "  - 至少 1 张 .png 参考图（建议正面图 + 多视角设定图）\n"
            "  - ip-description.txt（一段英文，描述 IP 外形特征）\n"
            "示例 ip-description.txt 内容：\n"
            '  A 3D rendered character with a bald head, large blue eyes,\n'
            '  wearing an oversized blue hoodie. Smooth vinyl toy finish,\n'
            '  friendly and confident expression.',
            file=sys.stderr,
        )
        sys.exit(1)
    return Path(env_path).expanduser()


def load_ip_description(ip_ref_dir: Path) -> str:
    """从 ${CYXJ_IP_REF_DIR}/ip-description.txt 读取 IP 角色描述。"""
    desc_file = ip_ref_dir / "ip-description.txt"
    if not desc_file.exists():
        print(
            f"❌ 缺少 IP 角色描述文件：{desc_file}\n"
            "请创建该文件，写入一段英文描述你 IP 形象的外形特征（颜色、服饰、表情、风格等）。\n"
            "这段描述会注入到 Gemini prompt 里，让生成的封面保持 IP 一致性。",
            file=sys.stderr,
        )
        sys.exit(1)
    return desc_file.read_text(encoding="utf-8").strip()


# 默认模型
DEFAULT_MODEL = "gemini-3-pro-image-preview"

# 比例 → 文件名映射
RATIO_FILENAME = {
    "4:3": "cover_4x3.png",
    "3:4": "cover_3x4.png",
    "16:9": "cover_16x9.png",
    "9:16": "cover_9x16.png",
    "1:1": "cover_1x1.png",
}

# Prompt 模板
PROMPT_TEMPLATE = """Generate a video cover/thumbnail image in EXACTLY the same visual style as the style reference image provided.

CRITICAL STYLE REQUIREMENTS (match the style reference exactly):
- 3D rendered character in the SAME art style as the reference images
- The character MUST be: {ip_description}
- Clean white/very light gray background with subtle grid pattern
- Holographic/translucent tech UI panels floating around the character
- Modern, professional, clean tech tutorial cover aesthetic
- Soft lighting, slight depth of field

SCENE:
{scene_description}

TEXT LAYOUT:
- Large bold text on the left side of the image (black + one accent color):
{title_lines}
- Text should be prominent but NOT fill the entire image — professional cover design feel
- Similar text size and positioning as the style reference

DO NOT use: flat 2D illustration, poster/print aesthetic, dark backgrounds, pixel art style, Mondo screen print. Must be 3D rendered, clean, modern.

ASPECT RATIO: {aspect_label}"""


def build_title_lines(title: str) -> str:
    """将标题拆成多行用于 prompt。"""
    # 如果标题较短，直接一行
    if len(title) <= 12:
        return f'  "{title}"'

    # 尝试在标点或空格处拆行
    mid = len(title) // 2
    for offset in range(min(8, mid)):
        for i in (mid + offset, mid - offset):
            if 0 < i < len(title) and title[i] in " ，,、：:——":
                line1 = title[:i].strip("，, ")
                line2 = title[i:].strip("，, ")
                return f'  Line 1: "{line1}"\n  Line 2: "{line2}"'

    # 没有合适断点，强制从中间拆
    return f'  Line 1: "{title[:mid]}"\n  Line 2: "{title[mid:]}"'


def build_scene_description(title: str, scene: str | None) -> str:
    """构建场景描述。用户不传 scene 时根据 title 自动推断。"""
    if scene:
        return (
            f"- The IP character is in the following scene: {scene}\n"
            f"- The scene should visually represent the topic: \"{title}\"\n"
            "- Character should have a semantic action/pose matching the scene"
        )
    return (
        f"- The IP character should be in a scene that visually represents: \"{title}\"\n"
        "- Character should have a meaningful action/pose related to the topic\n"
        "- Include relevant holographic UI elements, tech panels, or visual props that match the topic\n"
        "- Expression: confident, slightly smirking, like sharing a clever insight"
    )


def load_references(ip_ref_dir: Path) -> list[Image.Image]:
    """加载 IP 参考图（目录里所有 .png）和内置风格参考图。"""
    ip_pngs = sorted(ip_ref_dir.glob("*.png"))
    if not ip_pngs:
        print(f"❌ {ip_ref_dir} 里没有任何 .png 参考图", file=sys.stderr)
        sys.exit(1)

    refs: list[Image.Image] = []
    for path in ip_pngs:
        refs.append(Image.open(path))
        print(f"  📷 IP ref: {path.name}")

    if STYLE_REF.exists():
        refs.append(Image.open(STYLE_REF))
        print(f"  🎨 Style ref: {STYLE_REF.name}")
    else:
        print(f"  ⚠ Style reference not found: {STYLE_REF}")

    return refs


def generate_cover(
    title: str,
    scene: str | None,
    ratio: str,
    model: str,
    output_dir: Path,
    refs: list[Image.Image],
    ip_description: str,
) -> Path | None:
    """生成单张封面。"""
    aspect_label = {
        "4:3": "horizontal 4:3 landscape format",
        "3:4": "vertical 3:4 portrait format",
        "16:9": "horizontal 16:9 widescreen format",
        "9:16": "vertical 9:16 portrait format",
        "1:1": "square 1:1 format",
    }.get(ratio, f"{ratio} format")

    prompt = PROMPT_TEMPLATE.format(
        ip_description=ip_description,
        scene_description=build_scene_description(title, scene),
        title_lines=build_title_lines(title),
        aspect_label=aspect_label,
    )

    filename = RATIO_FILENAME.get(ratio, f"cover_{ratio.replace(':', 'x')}.png")
    output_path = output_dir / filename

    print(f"\n{'=' * 50}")
    print(f"📐 {ratio} ({aspect_label})")
    print(f"🎨 Model: {model}")
    print(f"⏳ Generating...")

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )

    contents = [prompt] + refs

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                responseModalities=["IMAGE"],
                imageConfig=types.ImageConfig(aspectRatio=ratio),
            ),
        )

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image = part.as_image()
                    output_dir.mkdir(parents=True, exist_ok=True)
                    image.save(output_path)
                    print(f"✅ Saved: {output_path}")
                    return output_path

        print("❌ No image in response")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="视频封面生成")
    parser.add_argument("--title", required=True, help="封面标题文字")
    parser.add_argument("--scene", default=None, help="场景/动作描述（可选）")
    parser.add_argument("--ratios", default="4:3,3:4", help="输出比例，逗号分隔（默认 4:3,3:4）")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型（默认 {DEFAULT_MODEL}）")
    parser.add_argument("--output", default=".", help="输出目录（默认当前目录）")
    args = parser.parse_args()

    # 检查 API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 未设置 GEMINI_API_KEY 或 GOOGLE_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    # 提前校验 IP 资料目录和描述文件（错误立即退出）
    ip_ref_dir = get_ip_ref_dir()
    ip_description = load_ip_description(ip_ref_dir)

    ratios = [r.strip() for r in args.ratios.split(",")]
    output_dir = Path(args.output).resolve()

    print(f"🎬 视频封面生成")
    print(f"   标题: {args.title}")
    print(f"   场景: {args.scene or '(自动推断)'}")
    print(f"   比例: {', '.join(ratios)}")
    print(f"   模型: {args.model}")
    print(f"   输出: {output_dir}")
    print(f"\n📦 加载参考图...")

    refs = load_references(ip_ref_dir)

    results = []
    for ratio in ratios:
        result = generate_cover(
            args.title, args.scene, ratio, args.model, output_dir, refs, ip_description
        )
        if result:
            results.append(result)

    print(f"\n{'=' * 50}")
    print(f"🏁 完成！生成 {len(results)}/{len(ratios)} 张封面")
    for r in results:
        print(f"   📄 {r}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
