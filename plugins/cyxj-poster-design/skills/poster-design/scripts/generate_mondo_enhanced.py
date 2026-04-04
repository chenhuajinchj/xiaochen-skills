#!/usr/bin/env python3
"""
XCYJ Poster Design Generator - Enhanced Version
Features: AI prompt optimization, 3-column comparison, image-to-image, 33+ artist styles, 10 photography styles
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from google import genai
from google.genai import types

# API Configuration
DEFAULT_IMAGE_MODEL = 'gemini-3.1-flash-image-preview'
DEFAULT_TEXT_MODEL = 'gemini-3.1-flash-lite-preview'

# Photography styles that use photorealistic base instead of Mondo poster base
PHOTO_STYLES = {
    "ccd-flash", "kodak-portra", "tyndall-forest", "studio-afternoon",
    "cyberpunk-neon", "snow-cabin", "vintage-library", "cherry-blossom",
    "desert-sunset", "classical-garden"
}

# 33+ Design Styles: Poster Artists + Book Cover + Album Cover + Social Media + Photography
ARTIST_STYLES = {
    "auto": "let AI choose best style",
    # === Poster Artists (20) ===
    "saul-bass": "Saul Bass minimalist geometric abstraction, 2-3 colors, visual metaphor",
    "olly-moss": "Olly Moss ultra-minimal negative space, clever hidden imagery, 2 colors",
    "tyler-stout": "Tyler Stout maximalist character collage, intricate line work, organized chaos",
    "martin-ansin": "Martin Ansin Art Deco elegance, refined vintage palette, sophisticated",
    "toulouse-lautrec": "Toulouse-Lautrec flat color blocks, Japanese influence, bold silhouettes",
    "alphonse-mucha": "Alphonse Mucha Art Nouveau flowing curves, ornate floral, decorative borders",
    "jules-cheret": "Jules Chéret Belle Époque bright joyful colors, dynamic feminine figures",
    "cassandre": "Cassandre modernist geometry, Cubist planes, dramatic perspective, Art Deco",
    "milton-glaser": "Milton Glaser psychedelic pop art, innovative typography, vibrant colors",
    "drew-struzan": "Drew Struzan painted realism, epic cinematic, warm nostalgic glow",
    "kilian-eng": "Kilian Eng geometric futurism, precise technical lines, cool sci-fi palette",
    "laurent-durieux": "Laurent Durieux visual puns, hidden imagery, mysterious atmospheric",
    "jay-ryan": "Jay Ryan folksy handmade, single focal image, warm textured simple",
    "dan-mccarthy": "Dan McCarthy ultra-flat geometric abstraction, 2-3 solid colors, no gradients",
    "jock": "Jock gritty expressive brushwork, dynamic action, high contrast, raw energy",
    "shepard-fairey": "Shepard Fairey propaganda style, red black cream, halftone, political",
    "steinlen": "Steinlen social realist, expressive lines, cat motifs, high contrast",
    "josef-muller-brockmann": "Josef Müller-Brockmann Swiss grid, Helvetica, mathematical precision",
    "paul-rand": "Paul Rand playful geometry, clever visual puns, witty intelligent",
    "paula-scher": "Paula Scher typographic maximalism, layered text, vibrant expressive letters",
    # === Book Cover Designers (6) ===
    "chip-kidd": "Chip Kidd conceptual book cover, single symbolic object, bold typography, photographic metaphor, witty visual pun, Random House literary aesthetic",
    "peter-mendelsund": "Peter Mendelsund abstract literary cover, deconstructed typography, minimal symbolic elements, intellectual negative space, Knopf literary elegance",
    "coralie-bickford-smith": "Coralie Bickford-Smith Penguin Clothbound Classics, repeating decorative patterns, Art Nouveau foil stamping, jewel-tone palette, ornamental borders, fabric texture",
    "david-pearson": "David Pearson Penguin Great Ideas, bold typographic-only cover, text as visual element, minimal color, intellectual and clean, type-driven design",
    "wang-zhi-hong": "Wang Zhi-Hong East Asian book design, restrained elegant typography, confident negative space, subtle texture, balanced asymmetry, literary sophistication",
    "jan-tschichold": "Jan Tschichold modernist Penguin typography, Swiss precision grid, clean serif fonts, understated elegance, timeless typographic hierarchy",
    # === Album Cover Designers (3) ===
    "reid-miles": "Reid Miles Blue Note Records, bold asymmetric typography, high contrast black and single accent color, jazz photography silhouette, dramatic negative space, vintage vinyl",
    "david-stone-martin": "David Stone Martin Verve Records, single gestural ink brushstroke, minimalist line drawing on cream, fluid calligraphic lines, maximum negative space, improvisational energy",
    "peter-saville": "Peter Saville Factory Records extreme minimalism, single abstract form in vast empty space, monochromatic, no text on cover, conceptual and mysterious, intellectual restraint",
    # === Social Media / Chinese Aesthetic Styles (4) ===
    "wenyi": "文艺风 literary artistic style, soft muted tones, generous white space, delicate serif typography, watercolor texture, poetic atmosphere, refined and contemplative, editorial book review aesthetic",
    "guochao": "国潮风 Chinese contemporary trend, traditional Chinese motifs reimagined modern, bold red and gold palette, ink wash meets graphic design, cultural symbols with street art energy, 新中式",
    "rixi": "日系 Japanese aesthetic, warm film grain, soft natural light, pastel muted palette, clean minimal layout, hand-drawn accents, cozy atmosphere, wabi-sabi imperfection, zakka lifestyle",
    "hanxi": "韩系 Korean aesthetic, clean bright pastel, soft gradient backgrounds, modern sans-serif typography, dreamy ethereal quality, sophisticated minimal, Instagram-worthy composition",
    # === Photography / Realistic Styles (10) ===
    "ccd-flash": "CCD 闪光写真 — early 2000s CCD smartphone aesthetic, strong built-in flash, close-up face shot, candid raw snapshot energy, slight amateur framing charm, digital noise in mid-shadows",
    "kodak-portra": "Kodak 胶片黄昏 — Kodak Portra 400 film emulation, warm golden-orange highlights, deep cyan shadows, rich sunset side lighting, vintage analog grain, golden hour warmth",
    "tyndall-forest": "丁达尔森林 — dramatic Tyndall effect volumetric light beams through dense forest canopy, dappled moving shadows, floating dust and pollen particles, cold emerald green dominant with warm golden beam contrast",
    "studio-afternoon": "影楼午后光 — luxury high-ceiling photography studio, floor-to-ceiling sheer white curtains diffusing soft afternoon daylight, warm-neutral beige 3200-4500K, creamy film emulation, dewy skin glow",
    "cyberpunk-neon": "赛博霓虹 — urban loft floor-to-ceiling windows, neon sign reflections bleeding into scene, metallic silver-blue palette, cool cyberpunk elegance, moody mixed lighting",
    "snow-cabin": "雪景高调 — minimalist high-key exposure, pristine ice-white pure tones, pearl-like luminous glow, snow cabin window soft diffused light, extreme clean aesthetic",
    "vintage-library": "复古图书馆 — warm tungsten filament lamp lighting, amber-gold color cast, dark wood bookshelves background, literary vintage atmosphere, rich shadow depth",
    "cherry-blossom": "樱花春日 — Japanese sweet spring aesthetic, pink soft-focus bokeh, dreamy scattered cherry blossom petals, pastel pink diffused light, gentle ethereal glow",
    "desert-sunset": "沙漠日落 — strong side-backlight on desert sand dunes, emerald-green and gold color contrast, exotic tropical elegance, dramatic rim lighting, warm golden contour",
    "classical-garden": "古典花园晨雾 — morning mist permeating classical garden, lace-pattern shadows, romantic classical atmosphere, soft diffused misty glow, delicate floral elements",
    # === Generic Styles ===
    "minimal": "minimalist, centered single focal point, 2-3 color palette, clean simple",
    "atmospheric": "single strong focal element with atmospheric background, 3-4 colors",
    "negative-space": "figure-ground inversion, negative space reveals hidden element, 2 colors"
}


def get_client():
    """Get Google Gemini API client"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is required.")
        print("Please set it with your Google Gemini API key.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def ai_enhance_prompt(original_subject, design_type, user_preferences=""):
    """
    Use AI to enhance and optimize the prompt while respecting user's original intent

    Args:
        original_subject: User's original subject/idea
        design_type: Type of design (movie/book/album/event)
        user_preferences: Optional user specifications (colors, style, elements)

    Returns:
        Enhanced prompt string
    """
    client = get_client()

    enhancement_request = f"""Enhance this Mondo poster prompt while STRICTLY respecting the user's original intent:

Original Subject: {original_subject}
Design Type: {design_type}
User Preferences: {user_preferences if user_preferences else "None specified - AI can suggest"}

Create an optimized Mondo-style prompt that:
1. KEEPS the core idea from user's original subject
2. Adds ONE perfect symbolic visual element (not multiple)
3. Suggests 2-3 complementary colors (user can override)
4. Uses negative space or visual puns when possible
5. Maintains Mondo screen print aesthetic
6. Stays clean and minimal (not cluttered)

Return ONLY the enhanced prompt text, no explanations."""

    try:
        response = client.models.generate_content(
            model=DEFAULT_TEXT_MODEL,
            contents=[enhancement_request],
            config=types.GenerateContentConfig(
                responseModalities=["TEXT"],
                maxOutputTokens=300,
            ),
        )

        if (response.candidates and
                response.candidates[0].content and
                response.candidates[0].content.parts):
            enhanced = response.candidates[0].content.parts[0].text.strip()
            return enhanced
        else:
            print("⚠ AI enhancement failed, using standard template")
            return None

    except Exception as e:
        print(f"⚠ AI enhancement error: {e}, using standard template")
        return None


def get_format_description(aspect_ratio):
    """Get format description text matching the aspect ratio"""
    ratio_descriptions = {
        "9:16": "vertical 9:16 portrait format",
        "16:9": "horizontal 16:9 landscape format, wide cinematic composition",
        "21:9": "ultra-wide 21:9 panoramic banner format, horizontal landscape",
        "3:4": "vertical 3:4 portrait format",
        "4:3": "horizontal 4:3 landscape format",
        "1:1": "square 1:1 format",
    }
    return ratio_descriptions.get(aspect_ratio, f"{aspect_ratio} format")


def generate_prompt(subject, design_type, style="auto", ai_enhance=False, color_hint="", aspect_ratio="9:16", ip_ref=False, title=""):
    """
    Generate prompt with optional AI enhancement

    Args:
        subject: The subject matter
        design_type: Type of design ("movie", "book", "album", "event")
        style: Visual style (artist name, photo style, or preset)
        ai_enhance: Whether to use AI enhancement
        color_hint: Optional color preferences from user
        aspect_ratio: Aspect ratio for the image
        ip_ref: Whether IP reference images are being used
        title: Optional title text to render on the poster

    Returns:
        Generated prompt string
    """
    format_desc = get_format_description(aspect_ratio)

    # Photography style path — photorealistic base
    if style in PHOTO_STYLES:
        style_desc = ARTIST_STYLES.get(style, "")
        # Strip the Chinese name prefix for the prompt (everything after " — ")
        if " — " in style_desc:
            style_desc = style_desc.split(" — ", 1)[1]
        base = "ultra photorealistic, cinematic photograph, 8K resolution"

        if design_type == "movie":
            prompt = f"{subject}, {base}, {style_desc}, {format_desc}, cinematic still frame"
        elif design_type == "book":
            prompt = f"{subject} book cover photograph, {base}, {style_desc}, {format_desc}"
        elif design_type == "album":
            prompt = f"{subject} album cover photograph, {base}, {style_desc}, square 1:1 format"
        elif design_type == "event":
            prompt = f"{subject} event photograph, {base}, {style_desc}, {format_desc}"
        else:
            prompt = f"{subject}, {base}, {style_desc}"

        if color_hint:
            prompt += f", color palette: {color_hint}"
        return prompt

    # AI Enhancement path (respects user intent)
    if ai_enhance:
        user_prefs = f"Style: {style}, Colors: {color_hint}" if color_hint else f"Style: {style}"
        enhanced = ai_enhance_prompt(subject, design_type, user_prefs)
        if enhanced:
            return enhanced + f", Mondo poster style, screen print aesthetic, {format_desc}"

    # Standard Mondo poster template path
    base_elements = "Mondo poster style, screen print aesthetic, limited edition poster art"

    # Get style modifier
    style_desc = ARTIST_STYLES.get(style, ARTIST_STYLES['minimal'])

    # Build prompt based on type
    if design_type == "movie":
        prompt = f"{subject} in {base_elements}, {style_desc}, {format_desc}, clean focused composition, vintage poster aesthetic"
    elif design_type == "book":
        prompt = f"{subject} book cover in {base_elements}, {style_desc}, {format_desc}, clean typography, literary design"
    elif design_type == "album":
        prompt = f"{subject} album cover in {base_elements}, {style_desc}, square 1:1 format, vintage vinyl aesthetic"
    elif design_type == "event":
        prompt = f"{subject} event poster in {base_elements}, {style_desc}, {format_desc}, bold memorable design"
    else:
        prompt = f"{subject} in {base_elements}, {style_desc}, vintage print aesthetic"

    # Add color hint if provided
    if color_hint:
        prompt += f", color palette: {color_hint}"

    # Add IP character instructions
    if ip_ref:
        prompt += """

IP CHARACTER (CRITICAL — must match the attached reference images exactly):
Recreate the character from the reference images precisely. Maintain the character's exact appearance, outfit, accessories, and art style. The character should be a prominent part of the composition, naturally integrated into the scene described above."""

    # Add title text rendering
    if title:
        prompt += f"""

TEXT ON IMAGE:
Render the following title text directly on the image as part of the design:
"{title}"
- The text should be clearly readable, bold, and integrated into the visual style
- Position it prominently but without covering the main visual elements
- Font style should match the overall aesthetic of the poster"""

    return prompt


def load_ip_references(ip_ref_dir):
    """
    Load IP reference images from a directory.

    Args:
        ip_ref_dir: Path to directory containing reference images (.png/.jpg)

    Returns:
        List of PIL Image objects
    """
    ip_dir = Path(ip_ref_dir)
    if not ip_dir.is_dir():
        print(f"⚠ IP reference directory not found: {ip_ref_dir}")
        return []

    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for img_path in sorted(ip_dir.glob(ext)):
            try:
                images.append(Image.open(img_path))
                print(f"📷 Loaded IP reference: {img_path.name}")
            except Exception as e:
                print(f"⚠ Could not load {img_path.name}: {e}")
    return images


def generate_image(prompt, output_path=None, model=DEFAULT_IMAGE_MODEL, aspect_ratio="9:16", input_image=None, ip_refs=None):
    """
    Generate image using Google Gemini API with optional image-to-image

    Args:
        prompt: The text prompt
        output_path: Path to save the image
        model: Model to use
        aspect_ratio: Aspect ratio
        input_image: Optional input image path for image-to-image
        ip_refs: Optional list of PIL Image objects as IP character references

    Returns:
        Path to saved image or None if failed
    """
    client = get_client()

    contents = [prompt]

    # Add IP reference images
    if ip_refs:
        contents.extend(ip_refs)

    # Add image-to-image support
    if input_image and os.path.exists(input_image):
        try:
            img = Image.open(input_image)
            contents.append(img)
            print(f"📷 Using input image: {input_image}")
        except Exception as e:
            print(f"⚠ Could not load input image: {e}")

    print(f"🎨 Generating with {model}")
    print(f"📐 Aspect ratio: {aspect_ratio}")
    print(f"✍️  Prompt: {prompt[:80]}..." if len(prompt) > 80 else f"✍️  Prompt: {prompt}")
    print("⏳ Please wait...\n")

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                responseModalities=["IMAGE"],
                imageConfig=types.ImageConfig(
                    aspectRatio=aspect_ratio,
                ),
            ),
        )

        # Extract image from response
        if (response.candidates and
                response.candidates[0].content and
                response.candidates[0].content.parts):
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image = part.as_image()

                    if not output_path:
                        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                        output_path = f"outputs/mondo-{timestamp}.png"

                    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

                    image.save(output_path)
                    print(f"✅ Saved to {output_path}")
                    return output_path

        print("❌ No image data in response")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def generate_comparison(subject, design_type, styles, aspect_ratio="9:16", colors=""):
    """
    Generate 3-column comparison of different styles

    Args:
        subject: Subject matter
        design_type: Type of design
        styles: List of 3 style names
        aspect_ratio: Aspect ratio
        colors: Optional color hint

    Returns:
        Path to comparison image
    """
    print(f"\n{'='*80}")
    print(f"🎨 GENERATING 3-STYLE COMPARISON")
    print(f"{'='*80}\n")

    images = []
    labels = []

    for i, style in enumerate(styles, 1):
        print(f"\n[{i}/3] Generating {style} style...")
        prompt = generate_prompt(subject, design_type, style, color_hint=colors, aspect_ratio=aspect_ratio)

        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        temp_path = f"outputs/temp-{style}-{timestamp}.png"

        result = generate_image(prompt, temp_path, aspect_ratio=aspect_ratio)
        if result:
            images.append(result)
            labels.append(style)
        else:
            print(f"⚠ Failed to generate {style}, skipping")

    if len(images) < 2:
        print("❌ Not enough images generated for comparison")
        return None

    # Create side-by-side comparison
    try:
        pil_images = [Image.open(img) for img in images]

        # Resize to same height
        target_height = min(img.height for img in pil_images)
        pil_images = [img.resize((int(img.width * target_height / img.height), target_height))
                     for img in pil_images]

        # Create comparison canvas
        total_width = sum(img.width for img in pil_images) + (len(pil_images) - 1) * 20
        comparison = Image.new('RGB', (total_width, target_height + 50), 'white')
        draw = ImageDraw.Draw(comparison)

        # Paste images side by side
        x_offset = 0
        for i, (img, label) in enumerate(zip(pil_images, labels)):
            comparison.paste(img, (x_offset, 0))

            # Add label
            label_text = label.upper().replace('-', ' ')
            bbox = draw.textbbox((0, 0), label_text)
            text_width = bbox[2] - bbox[0]
            text_x = x_offset + (img.width - text_width) // 2
            draw.text((text_x, target_height + 15), label_text, fill='black')

            x_offset += img.width + 20

        # Save comparison
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        comparison_path = f"outputs/comparison-{timestamp}.png"
        comparison.save(comparison_path)

        # Clean up temp files
        for img_path in images:
            try:
                os.remove(img_path)
            except:
                pass

        print(f"\n✅ Comparison saved to {comparison_path}")
        return comparison_path

    except Exception as e:
        print(f"❌ Error creating comparison: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Poster Design Generator — 33+ artist styles, 10 photography styles, AI optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎨 33+ Artist Styles + 10 Photography Styles Available

  Poster Artists: saul-bass, olly-moss, tyler-stout, martin-ansin, kilian-eng...
  Book Covers: chip-kidd, coralie-bickford-smith, wang-zhi-hong...
  Album Covers: reid-miles, peter-saville, david-stone-martin
  Photography: ccd-flash, kodak-portra, tyndall-forest, studio-afternoon,
               cyberpunk-neon, snow-cabin, vintage-library, cherry-blossom,
               desert-sunset, classical-garden

Examples:
  # AI-enhanced prompt
  python3 generate_mondo_enhanced.py "Blade Runner" movie --ai-enhance

  # Photography style (photorealistic)
  python3 generate_mondo_enhanced.py "portrait" event --style ccd-flash

  # 3-style comparison
  python3 generate_mondo_enhanced.py "Dune" movie --compare saul-bass,olly-moss,kilian-eng

  # Image-to-image transformation
  python3 generate_mondo_enhanced.py "noir thriller" movie --input poster.jpg --style saul-bass

  # With color preferences
  python3 generate_mondo_enhanced.py "Jazz Festival" event --style jules-cheret --colors "yellow, blue, red"

  # With IP character reference (poster with your own character)
  python3 generate_mondo_enhanced.py "AI news announcement" event --ip-ref ./ip-reference/ --title "Breaking News"

  # IP character poster without text
  python3 generate_mondo_enhanced.py "cyberpunk city scene" event --ip-ref ./ip-reference/
        """
    )

    parser.add_argument('subject', nargs='?', default=None, help='Subject matter (e.g., "Blade Runner", "1984 novel")')
    parser.add_argument('type', nargs='?', choices=['movie', 'book', 'album', 'event'], default='movie',
                       help='Type of design to create')
    parser.add_argument('--style', choices=list(ARTIST_STYLES.keys()), default='auto',
                       help='Artist or photography style (default: auto)')
    parser.add_argument('--ai-enhance', action='store_true',
                       help='Use AI to optimize prompt (respects your original intent)')
    parser.add_argument('--compare', type=str,
                       help='Generate 3-style comparison (comma-separated, e.g., "saul-bass,olly-moss,jock")')
    parser.add_argument('--input', type=str,
                       help='Input image for image-to-image transformation')
    parser.add_argument('--colors', type=str, default='',
                       help='Color preferences (e.g., "orange, teal, black")')
    parser.add_argument('--aspect-ratio', '--ratio', dest='aspect_ratio', default='9:16',
                       help='Aspect ratio (default: 9:16)')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--model', default=DEFAULT_IMAGE_MODEL, help='Model to use')
    parser.add_argument('--ip-ref', type=str,
                       help='Directory containing IP character reference images (e.g., ./ip-reference/)')
    parser.add_argument('--title', type=str, default='',
                       help='Title text to render on the poster (e.g., "A社新规：禁止第三方调用")')
    parser.add_argument('--no-generate', action='store_true',
                       help='Only show prompt without generating')
    parser.add_argument('--list-styles', action='store_true',
                       help='List all available styles')

    args = parser.parse_args()

    # List styles
    if args.list_styles:
        print("\n🎨 Available Styles:\n")
        print("--- Poster Artists (20) ---")
        for style, desc in list(ARTIST_STYLES.items())[1:21]:
            print(f"  {style:25} → {desc}")
        print("\n--- Book Cover Designers (6) ---")
        for style, desc in list(ARTIST_STYLES.items())[21:27]:
            print(f"  {style:25} → {desc}")
        print("\n--- Album Cover Designers (3) ---")
        for style, desc in list(ARTIST_STYLES.items())[27:30]:
            print(f"  {style:25} → {desc}")
        print("\n--- Social Media / Chinese Aesthetic (4) ---")
        for style, desc in list(ARTIST_STYLES.items())[30:34]:
            print(f"  {style:25} → {desc}")
        print("\n--- Photography / Realistic Styles (10) ---")
        for style in PHOTO_STYLES:
            desc = ARTIST_STYLES.get(style, "")
            print(f"  {style:25} → {desc}")
        print("\n--- Generic Styles (3) ---")
        for style in ["minimal", "atmospheric", "negative-space"]:
            print(f"  {style:25} → {ARTIST_STYLES[style]}")
        print()
        return

    if not args.subject:
        parser.print_help()
        sys.exit(1)

    # Comparison mode
    if args.compare:
        styles = [s.strip() for s in args.compare.split(',')]
        if len(styles) != 3:
            print("❌ Comparison requires exactly 3 styles (e.g., --compare saul-bass,olly-moss,jock)")
            sys.exit(1)

        generate_comparison(args.subject, args.type, styles, args.aspect_ratio, args.colors)
        return

    # Load IP references if provided
    ip_refs = None
    if args.ip_ref:
        ip_refs = load_ip_references(args.ip_ref)
        if not ip_refs:
            print("⚠ No reference images found, proceeding without IP character")

    # Single generation mode
    prompt = generate_prompt(args.subject, args.type, args.style, args.ai_enhance, args.colors, args.aspect_ratio,
                            ip_ref=bool(ip_refs), title=args.title)

    print(f"\n{'='*80}")
    print("🎨 POSTER DESIGN PROMPT")
    print(f"{'='*80}")
    print(f"{prompt}")
    print(f"{'='*80}\n")

    if not args.no_generate:
        output_path = generate_image(prompt, args.output, args.model, args.aspect_ratio, args.input, ip_refs=ip_refs)
        if not output_path:
            sys.exit(1)
    else:
        print("✓ Prompt generated. Use without --no-generate to create image.")

if __name__ == '__main__':
    main()
