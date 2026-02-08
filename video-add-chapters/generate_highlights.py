#!/usr/bin/env python3
"""
Generate highlight video from edited highlight script.
Parses [START-END] timestamps and merges selected segments into single video.
Supports optional segment titles displayed as yellow centered text overlay.

Usage:
    python generate_highlights.py "highlight_script.md"
    python generate_highlights.py "highlight_script.md" --output "highlights.mp4"
    python generate_highlights.py "highlight_script.md" --padding 0.5
    python generate_highlights.py "highlight_script.md" --title-duration 3
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


# Default padding in seconds (before/after each segment)
DEFAULT_PADDING = 0.5
DEFAULT_TITLE_DURATION = 3  # seconds to display title overlay


def parse_timestamp(ts: str) -> float:
    """Convert MM:SS or HH:MM:SS timestamp to seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


def get_video_duration(video_path: Path) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def parse_highlight_script(script_path: Path) -> tuple:
    """
    Parse highlight script and extract video path + segments.
    Returns: (video_path, [(start, end, title, text), ...])

    Script format:
        [MM:SS-MM:SS] {Optional Title} Text content
    """
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract source video path
    video_match = re.search(r"\*\*Source Video\*\*:\s*(.+)", content)
    if not video_match:
        print("Error: Could not find Source Video in script")
        sys.exit(1)

    video_path = Path(video_match.group(1).strip())

    # Extract segments: [MM:SS-MM:SS] {optional title} text
    pattern = r"\[(\d{1,2}:\d{2}(?::\d{2})?)-(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?:\{([^}]+)\})?\s*(.+)"
    segments = []

    for match in re.finditer(pattern, content):
        start_ts, end_ts, title, text = match.groups()
        start = parse_timestamp(start_ts)
        end = parse_timestamp(end_ts)
        # title may be None if not provided
        segments.append((start, end, title, text.strip()))

    return video_path, segments


def escape_text_for_ffmpeg(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    # Escape backslashes first, then other special chars
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    return text


def generate_highlight_video(video_path: Path, segments: list, output_path: Path,
                              padding: float = DEFAULT_PADDING,
                              title_duration: float = DEFAULT_TITLE_DURATION):
    """
    Generate merged highlight video using FFmpeg filter_complex.
    Supports optional title overlays (yellow centered text).
    """
    if not segments:
        print("Error: No segments to process")
        sys.exit(1)

    video_duration = get_video_duration(video_path)

    # Apply padding to segments
    padded_segments = []
    for start, end, title, text in segments:
        # Apply padding, but clamp to video bounds
        padded_start = max(0, start - padding)
        padded_end = min(video_duration, end + padding) if video_duration > 0 else end + padding
        padded_segments.append((padded_start, padded_end, title, text))

    print(f"Processing {len(padded_segments)} segments...")

    # Build FFmpeg filter_complex
    filter_parts = []
    concat_inputs = []

    for i, (start, end, title, text) in enumerate(padded_segments):
        # Video trim and optional title overlay
        video_filter = f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS"

        # Add drawtext if title is provided
        if title:
            escaped_title = escape_text_for_ffmpeg(title)
            video_filter += (
                f",drawtext=text='{escaped_title}':"
                f"fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc:"
                f"fontsize=108:"
                f"fontcolor=yellow:"
                f"borderw=4:"
                f"bordercolor=black:"
                f"x=(w-tw)/2:"
                f"y=(h-th)/2:"
                f"enable='lt(t,{title_duration})'"
            )

        filter_parts.append(f"{video_filter}[v{i}]")

        # Audio trim
        filter_parts.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

        duration = end - start
        title_info = f" [{title}]" if title else ""
        print(f"  [{i+1}] {start:.1f}s - {end:.1f}s ({duration:.1f}s){title_info}: {text[:40]}...")

    # Concat all segments
    concat_filter = "".join(concat_inputs) + f"concat=n={len(padded_segments)}:v=1:a=1[outv][outa]"
    filter_parts.append(concat_filter)

    filter_complex = ";".join(filter_parts)

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path)
    ]

    print(f"\nGenerating highlight video...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: FFmpeg failed")
        print(result.stderr)
        sys.exit(1)

    # Calculate total duration
    total_duration = sum(end - start for start, end, _, _ in padded_segments)

    print(f"\nDone!")
    print(f"  Output: {output_path}")
    print(f"  Duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"  Segments: {len(padded_segments)}")


def main():
    parser = argparse.ArgumentParser(description="Generate highlight video from edited script")
    parser.add_argument("script", help="Path to edited highlight script (.md)")
    parser.add_argument("--output", "-o",
                        help="Output video path (default: video - highlights.mp4)")
    parser.add_argument("--padding", "-p", type=float, default=DEFAULT_PADDING,
                        help=f"Padding before/after each segment in seconds (default: {DEFAULT_PADDING})")
    parser.add_argument("--title-duration", "-t", type=float, default=DEFAULT_TITLE_DURATION,
                        help=f"Duration to display title overlay in seconds (default: {DEFAULT_TITLE_DURATION})")

    args = parser.parse_args()

    script_path = Path(args.script).resolve()

    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    # Parse script
    video_path, segments = parse_highlight_script(script_path)

    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    print(f"Video: {video_path}")
    print(f"Segments found: {len(segments)}")

    # Default output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = script_path.parent / f"{video_path.stem} - highlights.mp4"

    # Generate video
    generate_highlight_video(video_path, segments, output_path, args.padding, args.title_duration)


if __name__ == "__main__":
    main()
