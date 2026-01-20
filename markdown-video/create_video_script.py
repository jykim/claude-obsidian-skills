#!/usr/bin/env python3
"""
Create a video script document from markdown slides for review.

This script generates a markdown document that shows:
- Section images (embedded)
- Speaker notes for each slide
- Easy-to-review format for narration editing

Usage:
    python create_video_script.py "slides.md" --output "video_script.md"
    python create_video_script.py "slides.md" --image-dir "slides-section"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def parse_markdown_sections(markdown_path: Path) -> List[Dict]:
    """
    Parse a Deckset markdown file into sections with slides and speaker notes.
    """
    content = markdown_path.read_text(encoding='utf-8')
    slides = re.split(r'\n---+\n', content)

    sections = []
    current_section = None
    current_section_title = None
    section_slides = []
    section_id = 0

    for slide_idx, slide in enumerate(slides):
        slide = slide.strip()
        if not slide:
            continue

        # Extract speaker notes (lines starting with ^)
        lines = slide.split('\n')
        content_lines = []
        speaker_notes = []

        for line in lines:
            if line.startswith('^'):
                speaker_notes.append(line[1:].strip())
            else:
                content_lines.append(line)

        slide_content = '\n'.join(content_lines).strip()
        speaker_note = ' '.join(speaker_notes)

        # Check for H1 header (section start)
        h1_match = re.match(r'^#\s+(.+?)(?:\n|$)', slide_content)

        # Extract slide title (first H1, H2, or H3)
        title_match = re.search(r'^#{1,3}\s+(.+?)$', slide_content, re.MULTILINE)
        slide_title = title_match.group(1).strip() if title_match else f"Slide {slide_idx}"

        if h1_match:
            # Save previous section
            if current_section is not None and section_slides:
                sections.append({
                    "id": section_id,
                    "name": slugify(current_section_title),
                    "title": current_section_title,
                    "slides": section_slides.copy(),
                })
                section_id += 1

            current_section_title = h1_match.group(1).strip()
            current_section = section_id
            section_slides = []

        if current_section is None:
            current_section_title = "Introduction"
            current_section = 0

        section_slides.append({
            "index": slide_idx,
            "title": slide_title,
            "content": slide_content,
            "speaker_note": speaker_note,
            "has_note": bool(speaker_note),
        })

    # Don't forget the last section
    if current_section_title and section_slides:
        sections.append({
            "id": section_id,
            "name": slugify(current_section_title),
            "title": current_section_title,
            "slides": section_slides.copy(),
        })

    return sections


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '_', text.strip())
    return text[:30]


def generate_video_script(
    sections: List[Dict],
    image_dir: Optional[Path],
    source_file: str
) -> str:
    """Generate markdown video script document."""
    lines = []

    # Header
    lines.append("---")
    lines.append(f"title: Video Script - {source_file}")
    lines.append(f"created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("tags:")
    lines.append("  - video-script")
    lines.append("  - narration-review")
    lines.append("---")
    lines.append("")
    lines.append(f"# Video Script: {source_file}")
    lines.append("")
    lines.append("> This document is for reviewing and editing narration before video generation.")
    lines.append("> Edit the narration text in blockquotes, then regenerate audio for changed slides.")
    lines.append("")

    # Summary
    total_slides = sum(len(s["slides"]) for s in sections)
    slides_with_notes = sum(1 for s in sections for sl in s["slides"] if sl["has_note"])
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Sections**: {len(sections)}")
    lines.append(f"- **Total Slides**: {total_slides}")
    lines.append(f"- **Slides with Narration**: {slides_with_notes}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    for section in sections:
        lines.append(f"## Section {section['id']}: {section['title']}")
        lines.append("")

        # Embed section image if available
        if image_dir:
            image_path = image_dir / f"section_{section['id']}_{section['name']}.png"
            if image_path.exists():
                lines.append(f"![[{image_path.name}]]")
                lines.append("")

        # Slides in this section
        for slide in section["slides"]:
            lines.append(f"### Slide #{slide['index']}: {slide['title']}")
            lines.append("")

            if slide["has_note"]:
                lines.append("**Narration**:")
                lines.append(f"> {slide['speaker_note']}")
            else:
                lines.append("*No narration (silent slide)*")

            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("## Editing Instructions")
    lines.append("")
    lines.append("1. Review each narration in the blockquotes above")
    lines.append("2. Edit the text directly in the blockquotes")
    lines.append("3. Run `generate_audio.py` to regenerate audio for changed slides")
    lines.append("4. Run `create_section_video.py` to create the final video")
    lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Create video script document from markdown slides"
    )
    parser.add_argument("markdown_file", help="Path to Deckset markdown file")
    parser.add_argument("--output", "-o", help="Output markdown file path")
    parser.add_argument("--image-dir", "-i", default=None,
                        help="Directory containing section images (for embedding)")

    args = parser.parse_args()

    markdown_path = Path(args.markdown_file)
    if not markdown_path.exists():
        print(f"❌ File not found: {markdown_path}")
        sys.exit(1)

    # Default output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = markdown_path.parent / f"{markdown_path.stem}_video_script.md"

    image_dir = Path(args.image_dir) if args.image_dir else None

    print(f"📄 Parsing: {markdown_path.name}")
    sections = parse_markdown_sections(markdown_path)

    if not sections:
        print("❌ No sections found in markdown file")
        sys.exit(1)

    print(f"📊 Found {len(sections)} sections")

    # Generate script
    script_content = generate_video_script(sections, image_dir, markdown_path.name)

    # Write output
    output_path.write_text(script_content, encoding='utf-8')
    print(f"✅ Video script created: {output_path}")

    # Summary
    total_slides = sum(len(s["slides"]) for s in sections)
    slides_with_notes = sum(1 for s in sections for sl in s["slides"] if sl["has_note"])
    print(f"   Sections: {len(sections)}")
    print(f"   Total slides: {total_slides}")
    print(f"   Slides with narration: {slides_with_notes}")


if __name__ == "__main__":
    main()
