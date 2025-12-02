#!/usr/bin/env python3
"""
Create Slide Images from Markdown (No Deckset Required)

Generates slide images directly from Deckset-format markdown,
without requiring Deckset export. Supports multiple visual themes.

Features:
- Multiple themes: romantic, professional, minimal
- Gradient backgrounds
- Korean font support (handwriting or gothic)
- EXIF orientation fix for images
- 1920x1080 resolution

Limitations:
- Emoji rendering NOT supported (PIL limitation)
- Simple layouts only (no complex Deckset positioning)

Usage:
    python create_slides_from_markdown.py "slides.md" --output-dir "./slides"
    python create_slides_from_markdown.py "slides.md" --theme professional
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps
import urllib.parse

# Theme color palettes
THEMES = {
    'romantic': {
        'gradient_start': (45, 13, 75),       # Deep purple
        'gradient_end': (139, 69, 102),        # Dusty rose
        'title': (255, 182, 193),              # Light pink
        'body': (255, 248, 245),               # Cream white
        'quote': (221, 160, 221),              # Plum/lavender
        'accent': (255, 215, 0),               # Gold
        'shadow': (20, 10, 30),                # Dark purple shadow
        'handwriting': True,
    },
    'professional': {
        'gradient_start': (30, 40, 60),        # Dark navy
        'gradient_end': (50, 70, 100),         # Lighter navy
        'title': (255, 255, 255),              # White
        'body': (220, 220, 230),               # Light gray
        'quote': (150, 180, 220),              # Light blue
        'accent': (100, 150, 255),             # Blue accent
        'shadow': (10, 15, 25),                # Dark shadow
        'handwriting': False,
    },
    'minimal': {
        'gradient_start': (250, 250, 250),     # Off-white
        'gradient_end': (235, 235, 240),       # Light gray
        'title': (30, 30, 35),                 # Near black
        'body': (60, 60, 70),                  # Dark gray
        'quote': (80, 80, 90),                 # Medium gray
        'accent': (0, 120, 200),               # Blue accent
        'shadow': (200, 200, 205),             # Light shadow
        'handwriting': False,
    },
}

# Resolution
WIDTH = 1920
HEIGHT = 1080

# Current theme (set at runtime)
COLORS = THEMES['romantic']


def create_gradient_background(width: int, height: int) -> Image.Image:
    """Create a gradient background based on current theme"""
    img = Image.new('RGB', (width, height))

    start_color = COLORS['gradient_start']
    end_color = COLORS['gradient_end']

    for y in range(height):
        ratio = y / height
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)

        for x in range(width):
            img.putpixel((x, y), (r, g, b))

    return img


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get Korean-compatible font based on theme settings"""
    font_paths = []

    if COLORS.get('handwriting', False):
        # Handwriting fonts (for romantic style)
        font_paths.extend([
            str(Path.home() / 'Library/Fonts/NanumPen.ttf'),
            '/Library/Fonts/NanumPen.ttf',
            '/System/Library/Fonts/NanumPen.ttf',
        ])

    # Gothic/sans-serif fonts (fallback or for professional/minimal themes)
    font_paths.extend([
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    ])

    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def draw_text_with_shadow(draw: ImageDraw.Draw, pos: Tuple[int, int], text: str,
                          font: ImageFont.FreeTypeFont, fill: Tuple[int, int, int],
                          shadow_offset: int = 2):
    """Draw text with shadow for better readability"""
    x, y = pos
    # Shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=COLORS['shadow'])
    # Main text
    draw.text((x, y), text, font=font, fill=fill)


def load_and_resize_image(image_path: Path, max_width: int, max_height: int) -> Optional[Image.Image]:
    """Load and resize image with EXIF orientation fix"""
    try:
        img = Image.open(image_path)
        # Apply EXIF orientation transpose to fix rotation
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"    Warning: Could not load image: {image_path} ({e})")
        return None


def add_rounded_corners(img: Image.Image, radius: int = 20) -> Image.Image:
    """Add rounded corners to image"""
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)

    output = Image.new('RGBA', img.size, (0, 0, 0, 0))
    output.paste(img, mask=mask)
    return output


def parse_markdown_slides(md_file: Path, base_dir: Path) -> List[Dict]:
    """Parse markdown and extract slide information"""
    content = md_file.read_text(encoding='utf-8')
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

        # Extract images
        images = []
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, display_content):
            alt_text = match.group(1)
            img_path = match.group(2)
            img_path = urllib.parse.unquote(img_path)
            if not img_path.startswith('/'):
                img_path = base_dir / img_path
            else:
                img_path = Path(img_path)
            images.append({'alt': alt_text, 'path': img_path})

        # Remove images from display content
        display_content = re.sub(image_pattern, '', display_content).strip()

        # Remove title from display content
        display_content = re.sub(r'^#+\s*.+?$', '', display_content, flags=re.MULTILINE).strip()

        # Extract blockquotes
        quotes = []
        quote_pattern = r'^>\s*["""]?(.+?)["""]?$'
        for match in re.finditer(quote_pattern, display_content, re.MULTILINE):
            quotes.append(match.group(1).strip())

        # Remove quotes from body
        body = re.sub(r'^>.*$', '', display_content, flags=re.MULTILINE).strip()
        body = re.sub(r'\*\*([^*]+)\*\*', r'\1', body)  # Remove bold markers
        body = re.sub(r'\n+', '\n', body).strip()

        slides.append({
            'num': output_num,
            'title': title,
            'body': body,
            'quotes': quotes,
            'images': images,
            'speaker_notes': speaker_notes,
        })
        output_num += 1

    return slides


def create_slide_image(slide: Dict, base_dir: Path) -> Image.Image:
    """Create a single slide image"""
    img = create_gradient_background(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(img)

    # Font sizes
    title_font = get_font(72, bold=True)
    body_font = get_font(48)
    quote_font = get_font(42)

    y_pos = 80
    margin = 100
    content_width = WIDTH - 2 * margin

    has_images = len(slide['images']) > 0

    # Handle images
    if has_images:
        if len(slide['images']) == 1:
            max_img_width = WIDTH - 200
            max_img_height = HEIGHT - 300 if slide['title'] else HEIGHT - 150

            photo = load_and_resize_image(slide['images'][0]['path'], max_img_width, max_img_height)
            if photo:
                photo = add_rounded_corners(photo.convert('RGBA'), radius=30)
                img_x = (WIDTH - photo.width) // 2
                img_y = (HEIGHT - photo.height) // 2

                if slide['title']:
                    img_y = 180

                img.paste(photo, (img_x, img_y), photo)
                y_pos = img_y + photo.height + 30
        else:
            num_images = min(len(slide['images']), 2)
            img_width = (WIDTH - 300) // num_images
            img_height = HEIGHT - 350

            for i, img_info in enumerate(slide['images'][:2]):
                photo = load_and_resize_image(img_info['path'], img_width - 40, img_height)
                if photo:
                    photo = add_rounded_corners(photo.convert('RGBA'), radius=20)
                    img_x = margin + i * (img_width + 50)
                    img_y = 180
                    img.paste(photo, (img_x, img_y), photo)

    # Draw title
    if slide['title']:
        title_y = 60 if has_images else 150

        title_lines = wrap_text(slide['title'], title_font, content_width, draw)
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = (WIDTH - text_width) // 2
            draw_text_with_shadow(draw, (x, title_y), line, title_font, COLORS['title'], shadow_offset=3)
            title_y += 90

    # Draw body text and quotes (only if no images)
    if not has_images:
        center_y = HEIGHT // 2 - 100

        if slide['quotes']:
            for quote in slide['quotes']:
                quote_text = f'"{quote}"'
                lines = wrap_text(quote_text, quote_font, content_width - 100, draw)

                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=quote_font)
                    text_width = bbox[2] - bbox[0]
                    x = (WIDTH - text_width) // 2
                    draw_text_with_shadow(draw, (x, center_y), line, quote_font, COLORS['quote'], shadow_offset=2)
                    center_y += 60
                center_y += 30

        if slide['body']:
            body_lines = slide['body'].split('\n')
            for body_line in body_lines:
                if not body_line.strip():
                    center_y += 30
                    continue
                lines = wrap_text(body_line, body_font, content_width, draw)
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=body_font)
                    text_width = bbox[2] - bbox[0]
                    x = (WIDTH - text_width) // 2
                    draw_text_with_shadow(draw, (x, center_y), line, body_font, COLORS['body'], shadow_offset=2)
                    center_y += 65

    return img


def main():
    global COLORS

    parser = argparse.ArgumentParser(
        description='Create slide images from Deckset-format markdown (no Deckset required)',
        epilog='NOTE: Emoji rendering is NOT supported. Remove emojis from titles for clean output.'
    )
    parser.add_argument('markdown_file', type=Path, help='Deckset markdown file with speaker notes')
    parser.add_argument('--output-dir', type=Path, default=Path('slides'), help='Output directory')
    parser.add_argument('--theme', choices=['romantic', 'professional', 'minimal'],
                        default='romantic', help='Visual theme (default: romantic)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created')

    args = parser.parse_args()

    # Set theme
    COLORS = THEMES[args.theme]

    if not args.markdown_file.exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)

    theme_emoji = {'romantic': '', 'professional': '', 'minimal': ''}
    print(f"Create Slide Images [{args.theme}]")
    print("=" * 60)
    print(f"Input:  {args.markdown_file}")
    print(f"Output: {args.output_dir}")
    print(f"Theme:  {args.theme}")
    print()

    # Parse markdown
    base_dir = args.markdown_file.parent
    print("Parsing markdown...")
    slides = parse_markdown_slides(args.markdown_file, base_dir)
    print(f"Found {len(slides)} slides with speaker notes")
    print()

    if args.dry_run:
        print("Dry run - would create:")
        for slide in slides:
            images_str = f" + {len(slide['images'])} image(s)" if slide['images'] else ""
            title_preview = slide['title'][:50] if slide['title'] else "(no title)"
            print(f"  {slide['num']}.jpeg: {title_preview}...{images_str}")
        return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate slides
    print(f"Creating {len(slides)} slide images...")
    for slide in slides:
        output_path = args.output_dir / f"{slide['num']}.jpeg"
        img = create_slide_image(slide, base_dir)
        img.save(output_path, 'JPEG', quality=95)
        title_preview = slide['title'][:40] if slide['title'] else "(no title)"
        print(f"  {output_path.name}: {title_preview}...")

    print()
    print("=" * 60)
    print(f"Done! Created {len(slides)} slide images in {args.output_dir}")
    print(f"Files: 1.jpeg, 2.jpeg, ..., {len(slides)}.jpeg")


if __name__ == '__main__':
    main()
