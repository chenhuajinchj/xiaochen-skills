#!/usr/bin/env python3
"""
XCYJ Poster Design Generator
Generates Mondo-style and photorealistic prompts, creates images via Google Gemini API.
"""

import os
import sys
import argparse
from datetime import datetime
from google import genai
from google.genai import types

# API Configuration
DEFAULT_IMAGE_MODEL = 'gemini-3.1-flash-image-preview'

# Photography styles (realistic, not poster art)
PHOTO_STYLES = {
    "ccd-flash", "kodak-portra", "tyndall-forest", "studio-afternoon",
    "cyberpunk-neon", "snow-cabin", "vintage-library", "cherry-blossom",
    "desert-sunset", "classical-garden"
}

PHOTO_STYLE_DESCRIPTIONS = {
    "ccd-flash": "early 2000s CCD smartphone aesthetic, strong built-in flash, close-up face shot, candid raw snapshot energy, slight amateur framing charm, digital noise in mid-shadows",
    "kodak-portra": "Kodak Portra 400 film emulation, warm golden-orange highlights, deep cyan shadows, rich sunset side lighting, vintage analog grain, golden hour warmth",
    "tyndall-forest": "dramatic Tyndall effect volumetric light beams through dense forest canopy, dappled moving shadows, floating dust and pollen particles, cold emerald green dominant with warm golden beam contrast",
    "studio-afternoon": "luxury high-ceiling photography studio, floor-to-ceiling sheer white curtains diffusing soft afternoon natural daylight, warm-neutral beige color temperature 3200-4500K, creamy film emulation, dewy skin glow",
    "cyberpunk-neon": "urban loft with floor-to-ceiling windows, neon sign reflections bleeding into scene, metallic silver-blue palette, cool cyberpunk elegance, moody mixed lighting",
    "snow-cabin": "minimalist high-key exposure, pristine ice-white pure tones, pearl-like luminous glow, snow cabin window soft diffused light, extreme clean aesthetic",
    "vintage-library": "warm tungsten filament lamp lighting, amber-gold color cast, dark wood bookshelves background, literary vintage atmosphere, rich shadow depth",
    "cherry-blossom": "Japanese sweet spring aesthetic, pink soft-focus bokeh, dreamy scattered cherry blossom petals, pastel pink diffused light, gentle ethereal glow",
    "desert-sunset": "strong side-backlight on desert sand dunes, emerald-green and gold color contrast, exotic tropical elegance, dramatic rim lighting, warm golden contour",
    "classical-garden": "morning mist permeating classical garden, lace-pattern shadows, romantic classical atmosphere, soft diffused misty glow, delicate floral elements"
}


def get_client():
    """Get Google Gemini API client"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is required.")
        print("Please set it with your Google Gemini API key.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def generate_prompt(subject, design_type, style="auto"):
    """
    Generate prompt based on subject, type, and style

    Args:
        subject: The subject matter
        design_type: Type of design ("movie", "book", "album", "event")
        style: Visual style

    Returns:
        Generated prompt string
    """

    # Check if it's a photography style
    if style in PHOTO_STYLES:
        photo_desc = PHOTO_STYLE_DESCRIPTIONS[style]
        base = "ultra photorealistic, cinematic photograph, 8K resolution"

        if design_type == "movie":
            prompt = f"{subject}, {base}, {photo_desc}, vertical 9:16 portrait format, cinematic still frame"
        elif design_type == "book":
            prompt = f"{subject} book cover photograph, {base}, {photo_desc}, vertical 9:16 portrait format"
        elif design_type == "album":
            prompt = f"{subject} album cover photograph, {base}, {photo_desc}, square 1:1 format"
        elif design_type == "event":
            prompt = f"{subject} event photograph, {base}, {photo_desc}, vertical 9:16 format"
        else:
            prompt = f"{subject}, {base}, {photo_desc}"
        return prompt

    # Mondo poster styles
    base_elements = "Mondo poster style, screen print aesthetic, limited edition poster art"

    style_modifiers = {
        "olly-moss": "ultra-minimal, 2-3 color screen print, single symbolic element, Olly Moss negative space approach",
        "tyler-stout": "intricate detailed composition, Tyler Stout style, character-focused",
        "minimal": "minimalist, centered single focal point, 2-3 color palette, clean simple composition",
        "atmospheric": "single strong focal element with atmospheric background, 3-4 color screen print, clean layered composition",
        "negative-space": "figure-ground inversion where negative space WITHIN silhouette reveals hidden element, clever dual imagery, Olly Moss style visual pun, 2-color duotone, what's missing tells the story"
    }

    if design_type == "movie":
        if style == "auto" or style == "minimal":
            prompt = f"{subject} in {base_elements}, vertical 9:16 portrait format, centered single focal element, 3-color screen print, clean minimalist composition, symbolic not literal, halftone texture, vintage 1970s-80s aesthetic, simple and iconic"
        else:
            prompt = f"{subject} in {base_elements}, vertical 9:16 portrait format, {style_modifiers.get(style, style_modifiers['atmospheric'])}, vintage poster aesthetic, clean focused design"

    elif design_type == "book":
        if style == "auto" or style == "minimal":
            prompt = f"{subject} book cover in {base_elements}, vertical 9:16 portrait format, single symbolic centerpiece, 2-3 color palette, clean typography, minimalist literary design, simple focused composition, vintage book aesthetic"
        else:
            prompt = f"{subject} book cover in {base_elements}, vertical 9:16 format, {style_modifiers.get(style, style_modifiers['minimal'])}, clean focused design, vintage book aesthetic"

    elif design_type == "album":
        if style == "auto" or style == "minimal":
            prompt = f"{subject} album cover in {base_elements}, square 1:1 format, single bold central image, 3 color screen print, clean minimalist design, vintage vinyl aesthetic, simple iconic imagery"
        else:
            prompt = f"{subject} album cover in {base_elements}, square 1:1 format, {style_modifiers.get(style, style_modifiers['minimal'])}, vintage vinyl aesthetic, clean design"

    elif design_type == "event":
        if style == "auto":
            prompt = f"{subject} event poster in {base_elements}, vertical 9:16 format, single focal point, 3 color high contrast, clean bold design, vintage concert poster aesthetic, simple memorable composition"
        else:
            prompt = f"{subject} event poster in {base_elements}, vertical 9:16 format, {style_modifiers.get(style, style_modifiers['minimal'])}, clean vintage poster design"

    else:
        prompt = f"{subject} in {base_elements}, {style_modifiers.get(style, style_modifiers['minimal'])}, vintage limited edition print aesthetic"

    return prompt


def generate_image(prompt, output_path=None, model=DEFAULT_IMAGE_MODEL, aspect_ratio="9:16"):
    """
    Generate image using Google Gemini API

    Args:
        prompt: The text prompt for image generation
        output_path: Path to save the generated image
        model: Model to use for generation
        aspect_ratio: Aspect ratio (default: 9:16)

    Returns:
        Path to saved image or None if failed
    """
    client = get_client()

    print(f"Generating image with model: {model}")
    print(f"Aspect ratio: {aspect_ratio}")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print("Please wait...\n")

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
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

                    # Determine output path
                    if not output_path:
                        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                        output_path = f"outputs/mondo-{timestamp}.png"

                    # Ensure directory exists
                    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

                    # Save image
                    image.save(output_path)
                    print(f"✓ Image saved successfully to {output_path}")
                    return output_path

        print("Error: No image data in response")
        return None

    except Exception as e:
        print(f"Error generating image: {e}")
        return None


def main():
    all_styles = ['auto', 'olly-moss', 'tyler-stout', 'minimal', 'atmospheric', 'negative-space'] + list(PHOTO_STYLES)

    parser = argparse.ArgumentParser(
        description='Generate Mondo-style and photorealistic designs for posters, book covers, and album art',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a movie poster (default 9:16 vertical)
  python3 generate_mondo.py "Akira cyberpunk anime" movie

  # Generate with minimal style
  python3 generate_mondo.py "1984 dystopian novel" book --style minimal

  # Generate with CCD flash photography style
  python3 generate_mondo.py "portrait" event --style ccd-flash

  # Generate album art with square ratio
  python3 generate_mondo.py "Pink Floyd The Wall" album --aspect-ratio 1:1

  # Only generate prompt without creating image
  python3 generate_mondo.py "Dune sci-fi epic" movie --no-generate

Photography Styles:
  ccd-flash, kodak-portra, tyndall-forest, studio-afternoon,
  cyberpunk-neon, snow-cabin, vintage-library, cherry-blossom,
  desert-sunset, classical-garden
        """
    )

    parser.add_argument('subject', help='Subject matter (e.g., "Blade Runner cyberpunk film")')
    parser.add_argument('type', choices=['movie', 'book', 'album', 'event'],
                       help='Type of design to create')
    parser.add_argument('--style', choices=all_styles,
                       default='auto', help='Visual style approach (default: auto)')
    parser.add_argument('--aspect-ratio', '--ratio', dest='aspect_ratio', default='9:16',
                       help='Aspect ratio for the image (default: 9:16). Examples: 9:16, 16:9, 1:1, 2:3, 3:4')
    parser.add_argument('--output', help='Output file path (default: outputs/mondo-TIMESTAMP.png)')
    parser.add_argument('--model', default=DEFAULT_IMAGE_MODEL,
                       help=f'Model to use for generation (default: {DEFAULT_IMAGE_MODEL})')
    parser.add_argument('--no-generate', action='store_true',
                       help='Only generate prompt without creating image')

    args = parser.parse_args()

    # Generate prompt
    prompt = generate_prompt(args.subject, args.type, args.style)

    print("=" * 80)
    print("GENERATED PROMPT")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print()

    # Generate image if requested
    if not args.no_generate:
        output_path = generate_image(prompt, args.output, args.model, args.aspect_ratio)
        if output_path:
            print(f"\n✓ Success! Design saved to: {output_path}")
        else:
            print("\n✗ Failed to generate image")
            sys.exit(1)
    else:
        print("Prompt generation complete. Use without --no-generate to create the image.")

if __name__ == '__main__':
    main()
