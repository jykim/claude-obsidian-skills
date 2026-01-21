#!/usr/bin/env python3
"""
Generate infographic-style section images from markdown slides using Gemini.

This script parses a Deckset-format markdown file into logical sections,
then generates one infographic image per section using Gemini 3.0 Pro.

Usage:
    python generate_section_images.py "slides.md" --output-dir "slides-section"
    python generate_section_images.py "slides.md" --style "professional"
    python generate_section_images.py "slides.md" --start-from 3
    python generate_section_images.py "slides.md" --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai package not installed")
    print("Install with: pip install google-genai")
    sys.exit(1)


# Visual style presets
STYLE_PRESETS = {
    "infographic": {
        "description": "Clean professional infographic with icons and visual metaphors",
        "colors": "Blue (#3498db), Purple (#9b59b6), Teal (#1abc9c), Orange (#f39c12)",
        "style": "Modern flat design with subtle shadows and gradients",
    },
    "professional": {
        "description": "Minimalist corporate design with geometric shapes",
        "colors": "Navy (#2c3e50), White, Gray (#95a5a6), Blue accent (#3498db)",
        "style": "Clean lines, minimal icons, professional typography",
    },
    "vibrant": {
        "description": "Bright gradients and flat design for marketing",
        "colors": "Pink (#ff6b9d), Purple (#c44569), Yellow (#f8b500), Teal (#00b894)",
        "style": "Bold colors, rounded shapes, playful icons",
    },
    "technical": {
        "description": "Technical diagram style with flowcharts and connections",
        "colors": "Blue (#3498db), Gray (#7f8c8d), Dark (#2c3e50), Green (#27ae60)",
        "style": "Clean lines, technical icons, flowchart elements, connection arrows",
    },
}

STYLE_PROMPT_TEMPLATE = """
Create an infographic-style presentation slide image for a technology/strategy presentation.

CONTENT TO VISUALIZE:
{content}

VISUAL STYLE REQUIREMENTS:
- {style_description}
- Color scheme: {style_colors}
- Design style: {style_style}
- Clear visual hierarchy with numbered sections
- Include non-English text as shown in content (IMPORTANT: must be readable)
- 16:9 aspect ratio, high resolution (1920x1080)
- White or light gradient background
- Use connecting lines, arrows, or flow diagrams to show relationships
- Make it look like a polished keynote/presentation slide
- Use relevant emojis as visual accents

TITLE: {title}
"""


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '_', text.strip())
    return text[:30]


def compute_hash(content: str) -> str:
    """Generate MD5 hash for content."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_cache(cache_file: Path) -> Dict:
    """Load generation cache."""
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache_file: Path, cache: Dict):
    """Save generation cache."""
    cache_file.write_text(json.dumps(cache, indent=2))


def parse_markdown_sections(markdown_path: Path) -> List[Dict]:
    """
    Parse a Deckset markdown file into logical sections.

    Sections are detected by H1 headers (# Title).
    Slides within a section are separated by ---.
    """
    content = markdown_path.read_text(encoding='utf-8')
    slides = re.split(r'\n---+\n', content)

    sections = []
    current_section = None
    current_slides = []
    section_id = 0

    for slide in slides:
        slide = slide.strip()
        if not slide:
            continue

        h1_match = re.match(r'^#\s+(.+?)(?:\n|$)', slide)

        if h1_match:
            if current_section and current_slides:
                sections.append({
                    "id": section_id,
                    "name": slugify(current_section),
                    "title": current_section,
                    "slides": current_slides.copy(),
                    "content": "\n\n".join(current_slides),
                })
                section_id += 1

            current_section = h1_match.group(1).strip()
            current_slides = [slide]
        else:
            if current_section is None:
                current_section = "Introduction"
            current_slides.append(slide)

    if current_section and current_slides:
        sections.append({
            "id": section_id,
            "name": slugify(current_section),
            "title": current_section,
            "slides": current_slides.copy(),
            "content": "\n\n".join(current_slides),
        })

    return sections


def generate_section_image(
    section: Dict,
    client,
    output_dir: Path,
    style: str,
    dry_run: bool = False
) -> Optional[str]:
    """Generate infographic image for a section using Gemini."""
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["infographic"])

    prompt = STYLE_PROMPT_TEMPLATE.format(
        content=section["content"],
        title=section["title"],
        style_description=style_config["description"],
        style_colors=style_config["colors"],
        style_style=style_config["style"],
    )

    print(f"\n🎨 Section {section['id']}: {section['name']}")
    print(f"   Title: {section['title']}")
    print(f"   Slides: {len(section['slides'])}")

    if dry_run:
        print(f"   [DRY RUN] Would generate image with {len(prompt)} char prompt")
        return None

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_path = output_dir / f"section_{section['id']}_{section['name']}.png"
                with open(image_path, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"   ✅ Saved: {image_path.name}")
                return str(image_path)

        print("   ❌ No image in response")
        return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate section infographic images from markdown slides"
    )
    parser.add_argument("markdown_file", help="Path to Deckset markdown file")
    parser.add_argument("--output-dir", "-o", default="slides-section",
                        help="Output directory for images (default: slides-section)")
    parser.add_argument("--style", "-s", default="infographic",
                        choices=list(STYLE_PRESETS.keys()),
                        help="Visual style preset (default: infographic)")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Start from section N (0-indexed)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Regenerate all images (ignore cache)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and show sections without generating images")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between API calls in seconds (default: 2.0)")

    args = parser.parse_args()

    markdown_path = Path(args.markdown_file)
    if not markdown_path.exists():
        print(f"❌ File not found: {markdown_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📄 Parsing: {markdown_path.name}")
    sections = parse_markdown_sections(markdown_path)
    print(f"📊 Found {len(sections)} sections")

    if not sections:
        print("❌ No sections found in markdown file")
        sys.exit(1)

    print("\n📋 Sections:")
    for s in sections:
        print(f"   {s['id']}: {s['title']} ({len(s['slides'])} slides)")

    if args.dry_run:
        print("\n[DRY RUN MODE - No images will be generated]")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    client = genai.Client(api_key=api_key) if api_key else None

    cache_file = output_dir / ".section_cache.json"
    cache = {} if args.force else load_cache(cache_file)

    to_generate = []
    for section in sections:
        if section["id"] < args.start_from:
            continue

        content_hash = compute_hash(section["content"])
        image_path = output_dir / f"section_{section['id']}_{section['name']}.png"

        if not args.force and section["name"] in cache:
            if cache[section["name"]].get("hash") == content_hash and image_path.exists():
                print(f"   ⏭️  Section {section['id']} unchanged (cached)")
                continue

        to_generate.append(section)

    if not to_generate:
        print("\n✅ All sections up to date (no changes)")
        return

    print(f"\n🎬 Generating {len(to_generate)} section images...")

    results = []
    for i, section in enumerate(to_generate):
        result = generate_section_image(section, client, output_dir, args.style, args.dry_run)
        results.append(result)

        if result and not args.dry_run:
            cache[section["name"]] = {
                "hash": compute_hash(section["content"]),
                "path": result,
            }
            save_cache(cache_file, cache)

        if i < len(to_generate) - 1 and not args.dry_run:
            print(f"   ⏳ Waiting {args.delay}s...")
            time.sleep(args.delay)

    success = len([r for r in results if r])
    print(f"\n{'='*50}")
    print(f"✅ Generation complete!")
    print(f"   Generated: {success}/{len(to_generate)}")
    print(f"   Output: {output_dir}")


if __name__ == "__main__":
    main()
