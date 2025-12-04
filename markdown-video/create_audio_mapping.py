#!/usr/bin/env python3
"""
Create Audio Mapping for Deckset Images

Maps Deckset-exported images to TTS audio files when slides have inconsistent
speaker notes. This solves the problem where some slides have speaker notes
(and thus audio) while others don't.

Problem:
    - Deckset exports ALL slides as images (1.jpeg, 2.jpeg, 3.jpeg, ...)
    - generate_audio.py creates audio only for slides WITH notes (slide_0.mp3, slide_1.mp3, ...)
    - slides_to_video.py expects simple N:N-1 mapping (image N → audio N-1)
    - This breaks when some slides lack speaker notes

Solution:
    This script creates a proper mapping by:
    1. Parsing markdown to identify which slides have speaker notes
    2. Matching Deckset image numbers to correct audio file numbers
    3. Creating either:
       - A mapped audio folder (copies/symlinks audio to correct names)
       - A JSON mapping file for manual use

Usage:
    # Create mapped audio folder (recommended)
    python create_audio_mapping.py "slides.md" \\
        --audio-dir "audio" \\
        --output-dir "audio-mapped"

    # Generate JSON mapping only
    python create_audio_mapping.py "slides.md" \\
        --audio-dir "audio" \\
        --json-only

    # Dry run - show mapping without creating files
    python create_audio_mapping.py "slides.md" --dry-run

Example Output:
    Deckset image 1.jpeg  → slide_0.mp3 (PKM 가이드라인)
    Deckset image 2.jpeg  → silent (no audio - section header)
    Deckset image 3.jpeg  → slide_1.mp3 (정의)
    ...
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def parse_deckset_markdown(md_file: Path) -> List[Dict]:
    """
    Parse Deckset markdown and extract all slides with their metadata.

    Returns:
        List of dicts with:
        - deckset_num: Image number when exported from Deckset (1-indexed)
        - audio_num: Audio file number if has speaker notes (0-indexed), else None
        - title: First line of slide (for identification)
        - has_notes: Boolean indicating if slide has speaker notes
        - notes: Speaker notes text (empty string if none)
    """
    content = md_file.read_text(encoding='utf-8')

    # Split by slide separator
    raw_slides = content.split('---')

    slides = []
    deckset_num = 0  # 1-indexed for Deckset export
    audio_num = 0    # 0-indexed for audio files

    for slide_content in raw_slides:
        slide_content = slide_content.strip()

        if not slide_content:
            continue

        # Skip frontmatter/metadata slides (slidenumbers, theme, etc.)
        if is_metadata_slide(slide_content):
            continue

        deckset_num += 1

        # Extract title (first non-empty line, stripped of markdown)
        title = extract_title(slide_content)

        # Extract speaker notes (marked with ^ prefix)
        notes = extract_speaker_notes(slide_content)
        has_notes = bool(notes)

        slides.append({
            'deckset_num': deckset_num,
            'audio_num': audio_num if has_notes else None,
            'title': title,
            'has_notes': has_notes,
            'notes': notes
        })

        # Increment audio counter only for slides with notes
        if has_notes:
            audio_num += 1

    return slides


def is_metadata_slide(content: str) -> bool:
    """Check if slide is metadata/frontmatter (not a real slide)."""
    # Common metadata patterns
    metadata_patterns = [
        r'^slidenumbers:\s*(true|false)',
        r'^autoscale:\s*(true|false)',
        r'^theme:\s*\w+',
        r'^footer:',
        r'^build-lists:\s*(true|false)',
    ]

    first_line = content.split('\n')[0].strip()

    for pattern in metadata_patterns:
        if re.match(pattern, first_line, re.IGNORECASE):
            return True

    return False


def extract_title(content: str) -> str:
    """Extract slide title from content."""
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip speaker notes
        if line.startswith('^'):
            continue
        # Skip image references
        if line.startswith('!['):
            continue
        # Skip horizontal rules
        if re.match(r'^[-*_]{3,}$', line):
            continue

        # Remove markdown headers
        title = re.sub(r'^#+\s*', '', line)
        # Remove bold/italic
        title = re.sub(r'\*+([^*]+)\*+', r'\1', title)
        # Truncate if too long
        if len(title) > 60:
            title = title[:60] + "..."

        return title

    return "(empty slide)"


def extract_speaker_notes(content: str) -> str:
    """Extract speaker notes from slide content."""
    notes_lines = []

    for line in content.split('\n'):
        line = line.strip()
        # Pattern 1: ^ speaker notes (Deckset format)
        if line.startswith('^'):
            note_text = line[1:].strip()
            if note_text:
                notes_lines.append(note_text)

    if notes_lines:
        return ' '.join(notes_lines)

    # Pattern 2: ^: speaker notes
    notes_match = re.search(r'\^:\s*(.*?)(?=\n\n|\Z)', content, re.DOTALL)
    if notes_match:
        return notes_match.group(1).strip()

    return ""


def create_mapped_audio_folder(
    slides: List[Dict],
    audio_dir: Path,
    output_dir: Path,
    use_symlinks: bool = False
) -> Tuple[int, int]:
    """
    Create audio folder with files mapped to Deckset image numbers.

    Args:
        slides: Parsed slide data
        audio_dir: Directory containing original audio files
        output_dir: Directory for mapped audio files
        use_symlinks: Use symlinks instead of copying (default: False)

    Returns:
        Tuple of (success_count, failed_count)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    for slide in slides:
        if not slide['has_notes']:
            continue

        # Source audio file (0-indexed)
        audio_num = slide['audio_num']
        source_file = None

        # Try different extensions
        for ext in ['.mp3', '.wav', '.m4a', '.aac']:
            candidate = audio_dir / f"slide_{audio_num}{ext}"
            if candidate.exists():
                source_file = candidate
                break

        if not source_file:
            print(f"  ⚠️  Audio not found: slide_{audio_num}.mp3 for Deckset {slide['deckset_num']}.jpeg")
            failed += 1
            continue

        # Target audio file (0-indexed based on Deckset image number)
        target_file = output_dir / f"slide_{slide['deckset_num'] - 1}{source_file.suffix}"

        try:
            if use_symlinks:
                if target_file.exists():
                    target_file.unlink()
                target_file.symlink_to(source_file.resolve())
            else:
                shutil.copy2(source_file, target_file)
            success += 1
        except Exception as e:
            print(f"  ⚠️  Failed to {'link' if use_symlinks else 'copy'}: {e}")
            failed += 1

    return success, failed


def save_mapping_json(slides: List[Dict], output_file: Path):
    """Save slide-audio mapping as JSON file."""
    mapping = []

    for slide in slides:
        mapping.append({
            'deckset_num': slide['deckset_num'],
            'deckset_image': f"{slide['deckset_num']}.jpeg",
            'has_audio': slide['has_notes'],
            'audio_source': f"slide_{slide['audio_num']}.mp3" if slide['has_notes'] else None,
            'mapped_audio': f"slide_{slide['deckset_num'] - 1}.mp3" if slide['has_notes'] else None,
            'title': slide['title']
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Create audio mapping for Deckset images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'markdown_file',
        type=Path,
        help='Deckset markdown file with speaker notes'
    )

    parser.add_argument(
        '--audio-dir',
        type=Path,
        default=Path('audio'),
        help='Directory containing original audio files (default: ./audio)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('audio-mapped'),
        help='Output directory for mapped audio files (default: ./audio-mapped)'
    )

    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Only generate JSON mapping file, do not copy audio files'
    )

    parser.add_argument(
        '--symlink',
        action='store_true',
        help='Use symlinks instead of copying audio files'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show mapping without creating files'
    )

    args = parser.parse_args()

    # Validate input file
    if not args.markdown_file.exists():
        print(f"❌ Error: Markdown file not found: {args.markdown_file}")
        sys.exit(1)

    print("🔗 Audio Mapping Creator")
    print("=" * 60)
    print(f"Markdown file: {args.markdown_file}")
    print(f"Audio dir:     {args.audio_dir}")
    print(f"Output dir:    {args.output_dir}")
    print()

    # Parse markdown
    print("📝 Parsing markdown slides...")
    slides = parse_deckset_markdown(args.markdown_file)

    if not slides:
        print("❌ Error: No slides found in markdown file")
        sys.exit(1)

    # Count statistics
    total_slides = len(slides)
    slides_with_notes = sum(1 for s in slides if s['has_notes'])
    slides_without_notes = total_slides - slides_with_notes

    print(f"✅ Found {total_slides} slides")
    print(f"   {slides_with_notes} with speaker notes (will have audio)")
    print(f"   {slides_without_notes} without notes (silent)")
    print()

    # Display mapping
    print("📊 Slide-Audio Mapping:")
    print("-" * 60)

    for slide in slides:
        deckset_img = f"{slide['deckset_num']}.jpeg"
        if slide['has_notes']:
            audio_src = f"slide_{slide['audio_num']}.mp3"
            mapped_audio = f"slide_{slide['deckset_num'] - 1}.mp3"
            status = f"✅ {deckset_img:12} ← {audio_src:15} → {mapped_audio}"
        else:
            status = f"⚪ {deckset_img:12} ← (no audio - silent)"

        title_preview = slide['title'][:35] + "..." if len(slide['title']) > 35 else slide['title']
        print(f"  {status:45} | {title_preview}")

    print("-" * 60)
    print()

    if args.dry_run:
        print("🔍 Dry run - no files created")
        return

    # Save JSON mapping
    json_file = args.output_dir.parent / f"{args.output_dir.stem}_mapping.json"
    if args.json_only:
        json_file = args.markdown_file.parent / "audio_mapping.json"

    print(f"💾 Saving mapping to {json_file}")
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    save_mapping_json(slides, json_file)

    if args.json_only:
        print("\n✅ JSON mapping created successfully!")
        print(f"📂 {json_file}")
        return

    # Create mapped audio folder
    print(f"\n📁 Creating mapped audio folder: {args.output_dir}")

    if not args.audio_dir.exists():
        print(f"❌ Error: Audio directory not found: {args.audio_dir}")
        sys.exit(1)

    success, failed = create_mapped_audio_folder(
        slides,
        args.audio_dir,
        args.output_dir,
        args.symlink
    )

    print()
    print("=" * 60)
    print("✅ Audio mapping complete!")
    print(f"   Processed: {success} files")
    if failed:
        print(f"   Failed:    {failed} files")
    print(f"\n📂 Mapped audio: {args.output_dir}")
    print(f"📄 Mapping JSON: {json_file}")

    print("\n💡 Usage:")
    print(f"   python slides_to_video.py \\")
    print(f"     --slides-dir \"path/to/deckset/images\" \\")
    print(f"     --audio-dir \"{args.output_dir}\" \\")
    print(f"     --output \"presentation.mp4\"")


if __name__ == '__main__':
    main()
