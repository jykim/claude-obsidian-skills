#!/usr/bin/env python3
"""
Create section-based video by merging audio and combining with section images.

This script:
1. Merges per-slide audio files into per-section audio
2. Combines section audio with section infographic images
3. Concatenates all sections into a final video

Usage:
    python create_section_video.py --config "sections.json" --output "presentation.mp4"
    python create_section_video.py --slides "slides.md" --audio-dir "audio" --image-dir "slides-section"

Config file format (sections.json):
{
    "sections": [
        {"id": 0, "name": "title", "audio_slides": [0]},
        {"id": 1, "name": "intro", "audio_slides": [1, 2, 3]},
        ...
    ]
}
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def check_dependencies():
    """Check if ffmpeg and ffprobe are available."""
    for cmd in ["ffmpeg", "ffprobe"]:
        try:
            subprocess.run([cmd, "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {cmd} not found. Install with: brew install ffmpeg")
            sys.exit(1)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '_', text.strip())
    return text[:30]


def parse_sections_from_markdown(markdown_path: Path) -> List[Dict]:
    """Auto-detect sections from markdown file."""
    content = markdown_path.read_text(encoding='utf-8')
    slides = re.split(r'\n---+\n', content)

    sections = []
    current_section = None
    current_title = None
    slide_indices = []
    section_id = 0
    slide_idx = 0

    for slide in slides:
        slide = slide.strip()
        if not slide:
            continue

        # Check for speaker notes (slides without notes are skipped in audio)
        has_note = bool(re.search(r'^\^', slide, re.MULTILINE))

        h1_match = re.match(r'^#\s+(.+?)(?:\n|$)', slide)

        if h1_match:
            if current_section is not None and slide_indices:
                sections.append({
                    "id": section_id,
                    "name": slugify(current_title),
                    "title": current_title,
                    "audio_slides": slide_indices.copy(),
                })
                section_id += 1

            current_title = h1_match.group(1).strip()
            current_section = section_id
            slide_indices = []

        if current_section is None:
            current_title = "Introduction"
            current_section = 0

        if has_note:
            slide_indices.append(slide_idx)
            slide_idx += 1

    if current_title and slide_indices:
        sections.append({
            "id": section_id,
            "name": slugify(current_title),
            "title": current_title,
            "audio_slides": slide_indices.copy(),
        })

    return sections


def merge_audio_files(
    section: Dict,
    audio_dir: Path,
    output_dir: Path
) -> Optional[Path]:
    """Merge multiple audio files into one for a section."""
    output_dir.mkdir(parents=True, exist_ok=True)

    section_name = section["name"]
    section_id = section["id"]
    audio_indices = section["audio_slides"]
    output_file = output_dir / f"section_{section_id}_{section_name}.mp3"

    if not audio_indices:
        print(f"   ⚠️  Section {section_id} has no audio slides")
        return None

    if len(audio_indices) == 1:
        src = audio_dir / f"slide_{audio_indices[0]}.mp3"
        if src.exists():
            subprocess.run(["cp", str(src), str(output_file)], check=True)
            print(f"   Copied: slide_{audio_indices[0]}.mp3 -> {output_file.name}")
            return output_file
        else:
            print(f"   ⚠️  Missing: {src.name}")
            return None

    # Create concat file for ffmpeg
    concat_file = output_dir / f"concat_{section_id}.txt"
    valid_files = []
    with open(concat_file, "w") as f:
        for idx in audio_indices:
            audio_path = audio_dir / f"slide_{idx}.mp3"
            if audio_path.exists():
                f.write(f"file '{audio_path}'\n")
                valid_files.append(idx)

    if not valid_files:
        print(f"   ⚠️  No valid audio files for section {section_id}")
        concat_file.unlink()
        return None

    # Merge using ffmpeg
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_file)
    ]
    result = subprocess.run(cmd, capture_output=True)

    concat_file.unlink()

    if result.returncode != 0:
        print(f"   ❌ Failed to merge audio for section {section_id}")
        return None

    print(f"   Merged {len(valid_files)} files -> {output_file.name}")
    return output_file


def get_audio_duration(audio_file: Path) -> float:
    """Get audio duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_file)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def create_section_video(
    section: Dict,
    audio_file: Path,
    image_file: Path,
    output_dir: Path
) -> Optional[Path]:
    """Create video for a section from image and audio."""
    output_dir.mkdir(parents=True, exist_ok=True)

    section_name = section["name"]
    section_id = section["id"]
    output_file = output_dir / f"section_{section_id}_{section_name}.mp4"

    duration = get_audio_duration(audio_file)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_file),
        "-i", str(audio_file),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-t", str(duration),
        "-shortest",
        str(output_file)
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"   ❌ Failed to create video for section {section_id}")
        return None

    print(f"   Created: {output_file.name} ({duration:.1f}s)")
    return output_file


def concatenate_videos(video_files: List[Path], output_file: Path, temp_dir: Path) -> bool:
    """Concatenate all section videos into final video."""
    concat_file = temp_dir / "concat_final.txt"
    with open(concat_file, "w") as f:
        for vf in video_files:
            f.write(f"file '{vf}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_file)
    ]

    result = subprocess.run(cmd, capture_output=True)
    concat_file.unlink()

    if result.returncode != 0:
        print(f"❌ Failed to concatenate videos")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create section-based video from audio and images"
    )
    parser.add_argument("--config", "-c", help="JSON config file with section definitions")
    parser.add_argument("--slides", "-s", help="Markdown slides file (auto-detect sections)")
    parser.add_argument("--audio-dir", "-a", default="audio",
                        help="Directory containing slide audio files (default: audio)")
    parser.add_argument("--image-dir", "-i", default="slides-section",
                        help="Directory containing section images (default: slides-section)")
    parser.add_argument("--output", "-o", default="presentation.mp4",
                        help="Output video file (default: presentation.mp4)")
    parser.add_argument("--temp-dir", default=None,
                        help="Temporary directory for intermediate files")

    args = parser.parse_args()

    check_dependencies()

    # Load sections from config or auto-detect from markdown
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            sys.exit(1)
        config = json.loads(config_path.read_text())
        sections = config["sections"]
    elif args.slides:
        slides_path = Path(args.slides)
        if not slides_path.exists():
            print(f"❌ Slides file not found: {slides_path}")
            sys.exit(1)
        print(f"📄 Auto-detecting sections from: {slides_path.name}")
        sections = parse_sections_from_markdown(slides_path)
    else:
        print("❌ Either --config or --slides must be provided")
        sys.exit(1)

    if not sections:
        print("❌ No sections found")
        sys.exit(1)

    audio_dir = Path(args.audio_dir)
    image_dir = Path(args.image_dir)
    output_file = Path(args.output)
    temp_dir = Path(args.temp_dir) if args.temp_dir else output_file.parent / ".video_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🎬 Creating Section-Based Video")
    print("=" * 60)
    print(f"   Sections: {len(sections)}")
    print(f"   Audio dir: {audio_dir}")
    print(f"   Image dir: {image_dir}")
    print(f"   Output: {output_file}")

    # Step 1: Merge audio by section
    print("\n📢 Step 1: Merging audio by section...")
    section_audio = {}
    for section in sections:
        audio_file = merge_audio_files(section, audio_dir, temp_dir / "audio")
        if audio_file:
            section_audio[section["id"]] = audio_file

    # Step 2: Create video clips for each section
    print("\n🎬 Step 2: Creating section video clips...")
    video_clips = []
    for section in sections:
        section_id = section["id"]
        section_name = section["name"]

        # Find image file
        image_file = image_dir / f"section_{section_id}_{section_name}.png"
        if not image_file.exists():
            print(f"   ⚠️  Missing image: {image_file.name}")
            continue

        audio_file = section_audio.get(section_id)
        if not audio_file or not audio_file.exists():
            print(f"   ⚠️  Missing audio for section {section_id}")
            continue

        video_clip = create_section_video(section, audio_file, image_file, temp_dir / "clips")
        if video_clip:
            video_clips.append(video_clip)

    if not video_clips:
        print("❌ No video clips created")
        sys.exit(1)

    # Step 3: Concatenate all clips
    print("\n🔗 Step 3: Concatenating all clips...")
    if not concatenate_videos(video_clips, output_file, temp_dir):
        sys.exit(1)

    # Get final video info
    duration = get_audio_duration(output_file)
    size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"\n{'='*60}")
    print(f"✅ Video creation complete!")
    print(f"   Duration: {duration:.1f}s ({duration/60:.1f} min)")
    print(f"   Size: {size_mb:.1f} MB")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    main()
