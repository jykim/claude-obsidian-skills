#!/usr/bin/env python3
"""
Create Slide Images from Markdown using Gemini Image Generation

Generates high-quality slide images using Google Gemini API.
Each slide is converted to a prompt and rendered as an AI-generated illustration.

Features:
- Multiple visual styles (technical-diagram, professional, vibrant-cartoon, watercolor)
- Full Korean text and emoji support
- 16:9 aspect ratio for presentations
- No Deckset installation required
- Delta updates: only regenerates changed slides (uses .slides_cache.json)

Usage:
    python create_slides_gemini.py "slides.md" --output-dir "./slides-gemini"
    python create_slides_gemini.py "slides.md" --style technical-diagram --auto-approve
    python create_slides_gemini.py "slides.md" --force  # Regenerate all
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from io import BytesIO


def compute_slide_hash(slide: Dict, style: str) -> str:
    """Compute hash of slide content for change detection"""
    content = f"{slide['title']}|{slide['body']}|{slide.get('table', '')}|{slide.get('mermaid', '')}|{style}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_cache(cache_file: Path) -> Dict:
    """Load cache from JSON file"""
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_cache(cache_file: Path, cache: Dict):
    """Save cache to JSON file"""
    cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: Google GenAI SDK not installed. Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# Style configurations
STYLES = {
    "technical-diagram": {
        "description": "technical diagram illustration with clean lines, infographic icons, muted blue/gray palette, and clear visual hierarchy",
        "background": "dark navy gradient",
        "best_for": "Technical presentations, education, business"
    },
    "professional": {
        "description": "professional minimalist illustration with muted colors, geometric shapes, and clean typography",
        "background": "subtle gradient",
        "best_for": "Corporate presentations, formal meetings"
    },
    "vibrant-cartoon": {
        "description": "vibrant modern cartoon illustration with bright gradients, flat design, and playful icons",
        "background": "colorful gradient",
        "best_for": "Marketing, startups, casual presentations"
    },
    "watercolor": {
        "description": "artistic watercolor illustration with soft pastel colors, flowing organic shapes, and gentle textures",
        "background": "soft wash",
        "best_for": "Creative presentations, personal content"
    },
}

# Gemini model configuration
# gemini-3-pro-image-preview: highest quality, supports aspect ratios ($0.06/image)
# gemini-2.0-flash-exp: free but lower quality, no aspect ratio support
DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_ASPECT_RATIO = "16:9"


def parse_markdown_slides(md_file: Path, base_dir: Path) -> List[Dict]:
    """Parse markdown and extract slide information (slides with speaker notes only)"""
    content = md_file.read_text(encoding='utf-8')

    # Remove frontmatter (slidenumbers, theme, etc.)
    content = re.sub(r'^[a-z]+:\s*\S+\s*\n', '', content, flags=re.MULTILINE)

    raw_slides = content.split('---')

    slides = []
    output_num = 1

    for idx, slide_content in enumerate(raw_slides):
        slide_content = slide_content.strip()
        if not slide_content:
            continue

        # Check for speaker notes (required for video)
        notes_match = re.search(r'^\^\s*(.+?)$', slide_content, re.MULTILINE | re.DOTALL)
        if not notes_match:
            continue  # Skip slides without speaker notes

        speaker_notes = notes_match.group(1).strip()

        # Remove speaker notes from display content
        display_content = re.sub(r'^\^\s*.+?$', '', slide_content, flags=re.MULTILINE).strip()

        # Extract title (# or ##)
        title_match = re.search(r'^#+\s*(.+?)$', display_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ""

        # Remove title from display content for body extraction
        body_content = re.sub(r'^#+\s*.+?$', '', display_content, flags=re.MULTILINE).strip()

        # Extract mermaid diagrams
        mermaid_match = re.search(r'```mermaid\s*\n(.+?)\n```', body_content, re.DOTALL)
        mermaid = mermaid_match.group(1).strip() if mermaid_match else None

        # Remove mermaid from body
        body_content = re.sub(r'```mermaid\s*\n.+?\n```', '', body_content, flags=re.DOTALL).strip()

        # Extract tables
        table_match = re.search(r'(\|.+\|[\s\S]*?\|.+\|)', body_content)
        table = table_match.group(1).strip() if table_match else None

        # Extract images
        images = []
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, display_content):
            alt_text = match.group(1)
            images.append(alt_text if alt_text else "image")

        # Remove images from body content
        body_content = re.sub(image_pattern, '', body_content).strip()

        # Clean up body
        body_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', body_content)  # Remove bold markers
        body_content = re.sub(r'\n{3,}', '\n\n', body_content).strip()

        slides.append({
            'num': output_num,
            'original_idx': idx,
            'title': title,
            'body': body_content,
            'table': table,
            'mermaid': mermaid,
            'images': images,
            'speaker_notes': speaker_notes,
        })
        output_num += 1

    return slides


def convert_slide_to_prompt(slide: Dict, style: str) -> str:
    """Convert slide content to Gemini image generation prompt"""

    style_info = STYLES.get(style, STYLES["technical-diagram"])
    style_desc = style_info["description"]

    # Build content description
    content_parts = []

    if slide['body']:
        content_parts.append(f"Main content:\n{slide['body']}")

    if slide['table']:
        content_parts.append(f"Data table to visualize:\n{slide['table']}")

    if slide['mermaid']:
        content_parts.append(f"Diagram/flowchart concept:\n{slide['mermaid']}")

    if slide['images']:
        content_parts.append(f"Visual elements: {', '.join(slide['images'])}")

    content_text = '\n\n'.join(content_parts) if content_parts else ""

    # Simple, effective prompt (similar to generate_gemini_image.py)
    prompt = f"""A {style_desc} representing '{slide['title']}'.
{content_text}
The image should be visually appealing and relevant to the content.
Use clear visual hierarchy, meaningful icons, and professional composition.
Include Korean text labels where appropriate."""

    return prompt.strip()


def generate_slide_image(
    client: genai.Client,
    prompt: str,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
) -> bool:
    """Generate a single slide image using Gemini API"""

    try:
        # Build config with aspect ratio support
        # gemini-3-pro-image-preview and gemini-2.5-flash-image support imageConfig
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            imageConfig=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        )

        response = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=config
        )

        # Extract image from response
        image_data = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                image_data = part.inline_data.data
                break

        if not image_data:
            print(f"    Warning: No image data in response", file=sys.stderr)
            return False

        image = Image.open(BytesIO(image_data))

        # Convert RGBA to RGB for JPEG
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        image.save(output_path, 'JPEG', quality=95)
        return True

    except Exception as e:
        print(f"    Error generating image: {e}", file=sys.stderr)
        return False


def get_user_approval(slide: Dict, prompt: str, slide_num: int, total: int) -> tuple[bool, Optional[str]]:
    """Show prompt and get user approval for generation"""

    print(f"\n{'='*70}")
    print(f"Slide {slide_num}/{total}: {slide['title'][:50]}...")
    print(f"{'='*70}")
    print(f"\nPrompt preview (first 500 chars):")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print()

    while True:
        response = input(f"Generate this slide? [Y]es / [N]o / [E]dit / [A]ll / [Q]uit: ").strip().lower()

        if response in ['y', 'yes', '']:
            return True, None, False
        elif response in ['n', 'no']:
            return False, None, False
        elif response in ['a', 'all']:
            return True, None, True  # Auto-approve rest
        elif response in ['e', 'edit']:
            print("\nEnter edited prompt (or press Enter to keep original):")
            edited = input("> ").strip()
            if edited:
                return True, edited, False
            continue
        elif response in ['q', 'quit']:
            print("Quit requested.")
            sys.exit(0)
        else:
            print("Invalid response. Please enter Y/N/E/A/Q.")


def main():
    parser = argparse.ArgumentParser(
        description='Create slide images from markdown using Gemini AI',
        epilog='Generates high-quality AI illustrations for each slide'
    )
    parser.add_argument('markdown_file', type=Path, help='Deckset markdown file with speaker notes')
    parser.add_argument('--output-dir', type=Path, default=Path('slides-gemini'), help='Output directory')
    parser.add_argument('--style', choices=list(STYLES.keys()), default='technical-diagram',
                        help='Visual style (default: technical-diagram)')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        help=f'Gemini model (default: {DEFAULT_MODEL})')
    parser.add_argument('--aspect-ratio', default=DEFAULT_ASPECT_RATIO,
                        choices=['1:1', '16:9', '9:16', '4:3', '3:4'],
                        help=f'Aspect ratio (default: {DEFAULT_ASPECT_RATIO})')
    parser.add_argument('--auto-approve', action='store_true',
                        help='Skip approval prompts (use with caution)')
    parser.add_argument('--dry-run', action='store_true', help='Show prompts without generating')
    parser.add_argument('--start-from', type=int, default=1,
                        help='Start from slide number (for resuming)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of slides to generate (0 = all)')
    parser.add_argument('--force', action='store_true',
                        help='Force regenerate all slides (ignore cache)')

    args = parser.parse_args()

    # Check for API key (skip for dry-run)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not args.markdown_file.exists():
        print(f"Error: File not found: {args.markdown_file}", file=sys.stderr)
        sys.exit(1)

    print("Create Slide Images with Gemini AI")
    print("=" * 60)
    print(f"Input:  {args.markdown_file}")
    print(f"Output: {args.output_dir}")
    print(f"Style:  {args.style} - {STYLES[args.style]['best_for']}")
    print(f"Model:  {args.model}")
    print()

    # Parse markdown
    base_dir = args.markdown_file.parent
    print("Parsing markdown...")
    slides = parse_markdown_slides(args.markdown_file, base_dir)
    print(f"Found {len(slides)} slides with speaker notes")
    print()

    if args.dry_run:
        print("Dry run - prompts that would be generated:")
        print("-" * 60)
        for slide in slides:
            prompt = convert_slide_to_prompt(slide, args.style)
            print(f"\n[Slide {slide['num']}] {slide['title'][:50]}...")
            print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
            print()
        return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load cache for delta updates
    cache_file = args.output_dir / '.slides_cache.json'
    cache = {} if args.force else load_cache(cache_file)

    # Determine which slides need regeneration
    slides_to_generate = []
    slides_unchanged = []

    for slide in slides:
        if slide['num'] < args.start_from:
            continue
        if args.limit > 0 and slide['num'] > args.limit:
            continue

        content_hash = compute_slide_hash(slide, args.style)
        slide_key = f"{slide['num']}"
        output_path = args.output_dir / f"{slide['num']}.jpeg"

        # Check if regeneration needed
        cached_hash = cache.get(slide_key, {}).get('hash')
        if cached_hash == content_hash and output_path.exists():
            slides_unchanged.append(slide)
        else:
            slide['content_hash'] = content_hash
            slides_to_generate.append(slide)

    # Report delta status
    if slides_unchanged and not args.force:
        print(f"\n✨ Delta update: {len(slides_unchanged)} slides unchanged, {len(slides_to_generate)} to regenerate")

    if not slides_to_generate:
        print("\n✅ All slide images are up to date!")
        print(f"  Output: {args.output_dir}")
        return

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Generate slides
    print(f"Generating {len(slides_to_generate)} slide images...")
    auto_approve_all = args.auto_approve
    generated = 0
    skipped = 0
    failed = 0

    for slide in slides_to_generate:
        output_path = args.output_dir / f"{slide['num']}.jpeg"
        prompt = convert_slide_to_prompt(slide, args.style)

        # Get approval if not auto-approve
        if not auto_approve_all:
            approved, edited_prompt, approve_rest = get_user_approval(
                slide, prompt, slide['num'], len(slides)
            )
            if approve_rest:
                auto_approve_all = True
            if edited_prompt:
                prompt = edited_prompt
            if not approved:
                print(f"  Skipped: {slide['num']}.jpeg")
                skipped += 1
                continue

        print(f"  Generating {slide['num']}.jpeg: {slide['title'][:40]}...", end=" ", flush=True)

        success = generate_slide_image(
            client, prompt, output_path,
            model=args.model,
            aspect_ratio=args.aspect_ratio
        )

        if success:
            print("Done")
            generated += 1
            # Update cache
            cache[f"{slide['num']}"] = {
                'hash': slide['content_hash'],
                'style': args.style,
                'model': args.model
            }
        else:
            print("FAILED")
            failed += 1

        # Rate limiting - be gentle with the API
        time.sleep(1)

    # Save updated cache
    save_cache(cache_file, cache)

    # Summary
    print()
    print("=" * 60)
    print(f"Complete!")
    print(f"  Generated: {generated}")
    if slides_unchanged:
        print(f"  Unchanged: {len(slides_unchanged)} (skipped)")
    print(f"  Skipped:   {skipped}")
    print(f"  Failed:    {failed}")
    print(f"  Output:    {args.output_dir}")

    if generated > 0:
        # Estimate cost (approximate)
        cost_per_image = 0.039  # gemini-2.5-flash estimate
        print(f"  Est. cost: ~${generated * cost_per_image:.2f}")


if __name__ == '__main__':
    main()
