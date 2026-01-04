#!/usr/bin/env python3
"""
Generate Audio from Markdown Slides

Simple script to generate TTS audio files from Deckset-format markdown speaker notes.
Focuses on one task: Markdown → Audio files (no HTML generation).

Usage:
    # Basic usage - generates audio in ./audio directory
    python generate_audio.py "slides.md"

    # Specify output directory
    python generate_audio.py "slides.md" --output-dir "my_audio"

    # Use different voice
    python generate_audio.py "slides.md" --voice alloy

    # Dry run - show what would be generated
    python generate_audio.py "slides.md" --dry-run

    # Force regenerate all (ignore cache)
    python generate_audio.py "slides.md" --force

Features:
    - Parses Deckset markdown (slides separated by ---)
    - Extracts speaker notes from each slide
    - Generates Korean TTS using OpenAI API
    - Creates slide_0.mp3, slide_1.mp3, etc.
    - Delta updates: only regenerates changed slides (uses .audio_cache.json)
    - Progress tracking and error handling
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
import requests


def compute_hash(text: str) -> str:
    """Compute MD5 hash of text for change detection"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


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


class ProgressBar:
    """Simple progress bar for terminal"""

    def __init__(self, total: int, prefix: str = ''):
        self.total = total
        self.current = 0
        self.prefix = prefix

    def update(self, n: int = 1):
        """Update progress by n steps"""
        self.current += n
        self._print()

    def _print(self):
        """Print progress bar"""
        percent = 100 * (self.current / self.total)
        bar_length = 40
        filled = int(bar_length * self.current / self.total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f'\r{self.prefix} |{bar}| {self.current}/{self.total} ({percent:.1f}%)', end='', flush=True)

    def finish(self):
        """Complete the progress bar"""
        self.current = self.total
        self._print()
        print()


def parse_deckset_markdown(md_file: Path) -> List[Dict]:
    """
    Parse Deckset markdown and extract slides with speaker notes.

    Returns:
        List of dicts with:
        - slide_num: Sequential number (0, 1, 2, ...) for slides with notes only
        - markdown_index: Index in markdown file (for reference)
        - content: Slide content
        - speaker_notes: Speaker notes text (empty if no notes)
    """
    content = md_file.read_text(encoding='utf-8')

    # Split by slide separator
    raw_slides = content.split('---')

    all_slides = []
    slide_num = 0  # Sequential counter for slides with notes

    for markdown_index, slide_content in enumerate(raw_slides):
        slide_content = slide_content.strip()

        if not slide_content:
            continue

        # Extract speaker notes (marked with ^ or ^: or Notes:)
        speaker_notes = ""

        # Pattern 1: ^ speaker notes (Deckset format)
        notes_match = re.search(r'^\^\s*(.*?)$', slide_content, re.MULTILINE)
        if notes_match:
            speaker_notes = notes_match.group(1).strip()
        else:
            # Pattern 2: ^: speaker notes
            notes_match = re.search(r'\^:\s*(.*?)(?=\n\n|\Z)', slide_content, re.DOTALL)
            if notes_match:
                speaker_notes = notes_match.group(1).strip()
            else:
                # Pattern 3: Notes: speaker notes
                notes_match = re.search(r'Notes?:\s*(.*?)(?=\n\n|\Z)', slide_content, re.DOTALL | re.IGNORECASE)
                if notes_match:
                    speaker_notes = notes_match.group(1).strip()

        # Clean up speaker notes
        if speaker_notes:
            # Remove extra whitespace and line breaks
            speaker_notes = re.sub(r'\s+', ' ', speaker_notes)
            speaker_notes = speaker_notes.strip()

        # Store all slides, but only assign slide_num to those with notes
        all_slides.append({
            'slide_num': slide_num if speaker_notes else None,  # Sequential for slides with notes
            'markdown_index': markdown_index,  # Original markdown position
            'content': slide_content,
            'speaker_notes': speaker_notes
        })

        # Increment sequential counter only for slides with notes
        if speaker_notes:
            slide_num += 1

    return all_slides


def generate_tts_audio(text: str, output_file: Path, voice: str = "nova", model: str = "tts-1", instructions: Optional[str] = None) -> bool:
    """
    Generate TTS audio using OpenAI API.

    Args:
        text: Text to convert to speech
        output_file: Path to save MP3 file
        voice: Voice to use (nova, alloy, echo, fable, onyx, shimmer, ballad, etc.)
        model: TTS model to use (tts-1, tts-1-hd, or gpt-4o-mini-tts)
        instructions: Tone/emotion instructions (only for gpt-4o-mini-tts)

    Returns:
        True if successful, False otherwise
    """
    # Get API key from environment
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ Error: OPENAI_API_KEY environment variable not set")
        return False

    # OpenAI TTS endpoint
    url = "https://api.openai.com/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "mp3"
    }

    # Add instructions parameter for gpt-4o-mini-tts model
    if model == "gpt-4o-mini-tts" and instructions:
        data["instructions"] = instructions

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        # Save audio file
        output_file.write_bytes(response.content)
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n⚠️  Warning: TTS generation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate TTS audio from Deckset markdown speaker notes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'markdown_file',
        type=Path,
        help='Deckset markdown file with speaker notes'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('audio'),
        help='Output directory for audio files (default: ./audio)'
    )

    parser.add_argument(
        '--voice',
        default='nova',
        choices=['nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer', 'ballad'],
        help='OpenAI TTS voice (default: nova)'
    )

    parser.add_argument(
        '--model',
        default='tts-1',
        choices=['tts-1', 'tts-1-hd', 'gpt-4o-mini-tts'],
        help='TTS model (default: tts-1, gpt-4o-mini-tts supports instructions)'
    )

    parser.add_argument(
        '--instructions',
        type=str,
        default=None,
        help='Tone/emotion instructions (only for gpt-4o-mini-tts model)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without generating'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Limit to first N slides with speaker notes (default: 0 = all)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regenerate all audio files (ignore cache)'
    )

    args = parser.parse_args()

    # Validate input file
    if not args.markdown_file.exists():
        print(f"❌ Error: Markdown file not found: {args.markdown_file}")
        sys.exit(1)

    print("🎤 Generate Audio from Markdown")
    print("=" * 60)
    print(f"Input file:  {args.markdown_file}")
    print(f"Output dir:  {args.output_dir}")
    print(f"Voice:       {args.voice}")
    print(f"Model:       {args.model}")
    if args.instructions:
        print(f"Instructions: {args.instructions[:60]}{'...' if len(args.instructions) > 60 else ''}")
    print()

    # Parse markdown
    print("📝 Parsing markdown slides...")
    slides = parse_deckset_markdown(args.markdown_file)

    if not slides:
        print("❌ Error: No slides found in markdown file")
        sys.exit(1)

    print(f"✅ Found {len(slides)} slides")

    # Count slides with speaker notes
    slides_with_notes = [s for s in slides if s['speaker_notes']]
    slides_without_notes = [s for s in slides if not s['speaker_notes']]

    print(f"   {len(slides_with_notes)} slides with speaker notes")
    print(f"   {len(slides_without_notes)} slides without speaker notes")

    # Apply limit if specified
    if args.limit > 0 and args.limit < len(slides_with_notes):
        slides_with_notes = slides_with_notes[:args.limit]
        print(f"📌 Limited to first {args.limit} slides")

    if slides_without_notes:
        print("\n⚠️  Slides without speaker notes (no audio will be generated):")
        for slide in slides_without_notes:
            # Get slide title (first line)
            first_line = slide['content'].split('\n')[0].strip('#').strip()
            if len(first_line) > 50:
                first_line = first_line[:50] + "..."
            print(f"   Slide {slide['markdown_index']}: {first_line}")

    if args.dry_run:
        print("\n🔍 Dry run - no audio generated")
        print("\nWould generate:")
        for slide in slides_with_notes:
            output_file = args.output_dir / f"slide_{slide['slide_num']}.mp3"
            notes_preview = slide['speaker_notes'][:80] + "..." if len(slide['speaker_notes']) > 80 else slide['speaker_notes']
            print(f"   {output_file.name}: {notes_preview}")
        return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load cache for delta updates
    cache_file = args.output_dir / '.audio_cache.json'
    cache = {} if args.force else load_cache(cache_file)

    # Determine which slides need regeneration
    slides_to_generate = []
    slides_unchanged = []

    for slide in slides_with_notes:
        content_hash = compute_hash(slide['speaker_notes'])
        slide_key = f"slide_{slide['slide_num']}"
        output_file = args.output_dir / f"{slide_key}.mp3"

        # Check if regeneration needed
        cached_hash = cache.get(slide_key, {}).get('hash')
        if cached_hash == content_hash and output_file.exists():
            slides_unchanged.append(slide)
        else:
            slide['content_hash'] = content_hash
            slides_to_generate.append(slide)

    # Report delta status
    if slides_unchanged and not args.force:
        print(f"\n✨ Delta update: {len(slides_unchanged)} slides unchanged, {len(slides_to_generate)} to regenerate")

    if not slides_to_generate:
        print("\n✅ All audio files are up to date!")
        print(f"\n📂 Output directory: {args.output_dir}")
        total_size = sum(f.stat().st_size for f in args.output_dir.glob('slide_*.mp3'))
        print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
        return

    # Generate audio files
    print(f"\n🎵 Generating {len(slides_to_generate)} audio files...")
    progress = ProgressBar(len(slides_to_generate), prefix='Progress')

    success_count = 0
    failed_slides = []

    for slide in slides_to_generate:
        output_file = args.output_dir / f"slide_{slide['slide_num']}.mp3"

        success = generate_tts_audio(
            slide['speaker_notes'],
            output_file,
            args.voice,
            args.model,
            args.instructions
        )

        if success:
            success_count += 1
            # Update cache
            cache[f"slide_{slide['slide_num']}"] = {
                'hash': slide['content_hash'],
                'voice': args.voice,
                'model': args.model
            }
        else:
            failed_slides.append(slide['slide_num'])

        progress.update()

    progress.finish()

    # Save updated cache
    save_cache(cache_file, cache)

    # Summary
    print()
    print("=" * 60)
    print(f"✅ Audio generation complete!")
    print(f"   Generated: {success_count}/{len(slides_to_generate)} files")
    if slides_unchanged:
        print(f"   Unchanged: {len(slides_unchanged)} files (skipped)")

    if failed_slides:
        print(f"   Failed:     {len(failed_slides)} files (slides: {', '.join(map(str, failed_slides))})")

    print(f"\n📂 Output directory: {args.output_dir}")
    print(f"   Files: slide_0.mp3, slide_1.mp3, ..., slide_{len(slides_with_notes)-1}.mp3")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in args.output_dir.glob('slide_*.mp3'))
    print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
