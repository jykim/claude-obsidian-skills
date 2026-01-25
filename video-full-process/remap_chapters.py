#!/usr/bin/env python3
"""
Remap chapter timestamps based on removed pauses.

When pauses are removed from a video, chapter timestamps need to be adjusted
to point to the correct positions in the cleaned video.

Usage:
    python remap_chapters.py "chapters.json" --pauses "pauses.json"
    python remap_chapters.py "chapters.json" --pauses "pauses.json" --output "remapped.json"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    """Save JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def map_timestamp(original_time: float, pauses: List[Dict]) -> float:
    """
    Calculate new timestamp after pause removal.

    Args:
        original_time: Timestamp in original video (seconds)
        pauses: List of pause dicts with 'start', 'end', 'duration' keys

    Returns:
        Adjusted timestamp for cleaned video
    """
    removed_time = 0.0

    for pause in pauses:
        pause_start = pause.get("start", 0)
        pause_end = pause.get("end", 0)
        pause_duration = pause.get("duration", pause_end - pause_start)

        if pause_end <= original_time:
            # This pause was completely before our timestamp
            removed_time += pause_duration
        elif pause_start < original_time < pause_end:
            # Our timestamp is within a pause - snap to pause start
            removed_time += (original_time - pause_start)

    return max(0, original_time - removed_time)


def remap_chapters(chapters_data: dict, pauses_data: dict) -> dict:
    """
    Remap all chapter timestamps based on removed pauses.

    Args:
        chapters_data: Original chapters JSON
        pauses_data: Pauses JSON from video cleaning

    Returns:
        New chapters dict with remapped timestamps
    """
    # Extract pauses list
    pauses = pauses_data.get("pauses", [])

    if not pauses:
        print("Warning: No pauses found in pauses data")
        return chapters_data

    # Sort pauses by start time
    pauses = sorted(pauses, key=lambda x: x.get("start", 0))

    # Calculate total removed time
    total_removed = sum(p.get("duration", 0) for p in pauses)
    print(f"Total pause time removed: {total_removed:.2f}s ({len(pauses)} pauses)")

    # Get chapters (support both list and dict formats)
    if isinstance(chapters_data, list):
        chapters = chapters_data
    else:
        chapters = chapters_data.get("chapters", chapters_data.get("suggestions", []))

    # Remap each chapter
    remapped_chapters = []
    for ch in chapters:
        if isinstance(ch, (list, tuple)):
            # Format: (start, title, description)
            original_start = ch[0]
            new_start = map_timestamp(original_start, pauses)
            remapped = [new_start, ch[1], ch[2] if len(ch) > 2 else ""]
        else:
            # Format: dict with 'start' or 'timestamp' key
            original_start = ch.get("start", ch.get("timestamp", 0))
            new_start = map_timestamp(original_start, pauses)
            remapped = {**ch, "start": new_start, "original_start": original_start}

        remapped_chapters.append(remapped)
        print(f"  {format_timestamp(original_start)} → {format_timestamp(new_start)}")

    # Build output
    result = {
        "chapters": remapped_chapters,
        "total_removed": total_removed,
        "pause_count": len(pauses),
        "source_pauses": str(pauses_data.get("source", "unknown"))
    }

    return result


def generate_ffmpeg_metadata(chapters: List[Dict], output_path: Path):
    """
    Generate ffmpeg chapter metadata file.

    FFmpeg chapter format:
    ;FFMETADATA1
    [CHAPTER]
    TIMEBASE=1/1000
    START=0
    END=120000
    title=Chapter 1
    """
    lines = [";FFMETADATA1", ""]

    for i, ch in enumerate(chapters):
        start_ms = int(ch.get("start", 0) * 1000)
        # End time is start of next chapter, or +1 hour for last
        if i + 1 < len(chapters):
            end_ms = int(chapters[i + 1].get("start", 0) * 1000) - 1
        else:
            end_ms = start_ms + 3600000  # +1 hour placeholder

        title = ch.get("title", f"Chapter {i + 1}")

        lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start_ms}",
            f"END={end_ms}",
            f"title={title}",
            ""
        ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"FFmpeg metadata saved to: {output_path}")


def embed_chapters(video_path: Path, metadata_path: Path, output_path: Path) -> bool:
    """
    Embed chapters into video using ffmpeg.

    Uses ffmpeg's -i for metadata file and -map_chapters for embedding.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(metadata_path),
        "-map_metadata", "1",
        "-map_chapters", "1",
        "-c", "copy",
        str(output_path)
    ]

    print(f"Embedding chapters into video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        return False

    print(f"Video with chapters saved to: {output_path}")
    return True


def generate_youtube_chapters(chapters: List[Dict], output_path: Path, video_name: str = ""):
    """Generate YouTube chapter markers text file."""
    lines = [f"# YouTube Chapters{' for ' + video_name if video_name else ''}", ""]
    lines.append("Copy the following to your YouTube video description:")
    lines.append("")
    lines.append("---")
    lines.append("")

    for ch in chapters:
        start = ch.get("start", 0)
        title = ch.get("title", "Untitled")
        ts = format_timestamp(start)
        lines.append(f"{ts} {title}")

    lines.append("")
    lines.append("---")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"YouTube chapters saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Remap chapter timestamps based on removed pauses")
    parser.add_argument("chapters", help="Chapters JSON file")
    parser.add_argument("--pauses", required=True, help="Pauses JSON file from video cleaning")
    parser.add_argument("--output", help="Output JSON file (default: {chapters}_remapped.json)")
    parser.add_argument("--video", help="Video file to embed chapters into")
    parser.add_argument("--embed-output", help="Output video path with embedded chapters")
    parser.add_argument("--youtube", action="store_true", help="Generate YouTube chapters file")

    args = parser.parse_args()

    chapters_path = Path(args.chapters)
    pauses_path = Path(args.pauses)

    if not chapters_path.exists():
        print(f"Error: Chapters file not found: {chapters_path}")
        return 1

    if not pauses_path.exists():
        print(f"Error: Pauses file not found: {pauses_path}")
        return 1

    print(f"Loading chapters: {chapters_path}")
    chapters_data = load_json(chapters_path)

    print(f"Loading pauses: {pauses_path}")
    pauses_data = load_json(pauses_path)

    # Remap chapters
    print("\nRemapping chapter timestamps...")
    remapped = remap_chapters(chapters_data, pauses_data)

    # Save remapped chapters
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = chapters_path.parent / f"{chapters_path.stem}_remapped.json"

    save_json(remapped, output_path)
    print(f"\nRemapped chapters saved to: {output_path}")

    # Generate YouTube chapters if requested
    if args.youtube:
        yt_path = output_path.parent / f"{output_path.stem}_youtube.txt"
        generate_youtube_chapters(remapped["chapters"], yt_path)

    # Embed chapters if video provided
    if args.video:
        video_path = Path(args.video)
        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}")
            return 1

        # Generate FFmpeg metadata
        metadata_path = output_path.parent / f"{output_path.stem}_ffmetadata.txt"
        generate_ffmpeg_metadata(remapped["chapters"], metadata_path)

        # Embed chapters
        if args.embed_output:
            embed_output = Path(args.embed_output)
        else:
            embed_output = video_path.parent / f"{video_path.stem} - chapters{video_path.suffix}"

        if not embed_chapters(video_path, metadata_path, embed_output):
            return 1

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
