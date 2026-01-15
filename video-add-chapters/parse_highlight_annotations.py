#!/usr/bin/env python3
"""
Parse highlight annotations from transcript markdown.
Supports <u>underline</u> and ==markdown highlight== formats.
Generates highlight script for video generation.

Usage:
    python parse_highlight_annotations.py "transcript.md"
    python parse_highlight_annotations.py "transcript.md" --output "highlights.md"
    python parse_highlight_annotations.py "transcript.md" --video "/path/to/video.mp4"
"""

import argparse
import re
import sys
from pathlib import Path


def parse_timestamp(ts: str) -> int:
    """Convert HH:MM:SS or MM:SS timestamp to seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def format_timestamp(seconds: int) -> str:
    """Convert seconds to MM:SS format."""
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def extract_highlights(content: str) -> list:
    """
    Extract highlighted segments from transcript.
    Returns list of (start_seconds, text) tuples.
    """
    highlights = []

    # Pattern to match timestamp lines: **[HH:MM:SS]** or **[MM:SS]**
    # Followed by content that may contain <u>...</u> or ==...==
    line_pattern = r'\*\*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\*\*\s*(.+?)(?=\n\n|\n\*\*\[|$)'

    for match in re.finditer(line_pattern, content, re.DOTALL):
        timestamp_str = match.group(1)
        line_content = match.group(2).strip()

        # Check for <u>...</u> highlights
        underline_matches = re.findall(r'<u>(.+?)</u>', line_content, re.DOTALL)

        # Check for ==...== highlights
        highlight_matches = re.findall(r'==(.+?)==', line_content, re.DOTALL)

        if underline_matches or highlight_matches:
            start_seconds = parse_timestamp(timestamp_str)
            # Combine all highlighted text
            highlighted_text = ' '.join(underline_matches + highlight_matches)
            # Clean up whitespace
            highlighted_text = ' '.join(highlighted_text.split())
            highlights.append((start_seconds, highlighted_text))

    return highlights


def merge_consecutive_highlights(highlights: list, gap_threshold: int = 10) -> list:
    """
    Merge consecutive highlights that are close together.
    Returns list of (start_seconds, end_seconds, merged_text) tuples.
    """
    if not highlights:
        return []

    merged = []
    current_start = highlights[0][0]
    current_texts = [highlights[0][1]]
    prev_time = highlights[0][0]

    for i in range(1, len(highlights)):
        start, text = highlights[i]

        # If gap is small, merge with current group
        if start - prev_time <= gap_threshold:
            current_texts.append(text)
        else:
            # Save current group and start new one
            merged.append((current_start, prev_time, ' '.join(current_texts)))
            current_start = start
            current_texts = [text]

        prev_time = start

    # Don't forget the last group
    merged.append((current_start, prev_time, ' '.join(current_texts)))

    return merged


def find_segment_end_times(content: str, merged_highlights: list) -> list:
    """
    Find proper end times for each highlight segment.
    Uses next segment's start time or adds default duration.
    """
    # Extract all timestamps from content
    all_timestamps = []
    for match in re.finditer(r'\*\*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\*\*', content):
        ts = parse_timestamp(match.group(1))
        all_timestamps.append(ts)

    all_timestamps = sorted(set(all_timestamps))

    result = []
    for start, last_highlight_time, text in merged_highlights:
        # Find the next timestamp after the last highlighted segment
        end_time = last_highlight_time + 10  # default: add 10 seconds

        for ts in all_timestamps:
            if ts > last_highlight_time:
                end_time = ts
                break

        result.append((start, end_time, text))

    return result


def generate_highlight_script(segments: list, video_path: str = None, source_file: str = None) -> str:
    """Generate highlight script markdown."""

    # Try to extract video path from source file if not provided
    if not video_path and source_file:
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
            video_match = re.search(r'\*\*Source Video\*\*:\s*(.+)', content)
            if video_match:
                video_path = video_match.group(1).strip()

    lines = [
        "# Highlight Script",
        "",
        f"**Source Video**: {video_path or 'N/A'}",
        "",
        "---",
        "",
        "<!-- Generated from <u> and == annotations -->",
        "",
    ]

    for i, (start, end, text) in enumerate(segments, 1):
        start_ts = format_timestamp(start)
        end_ts = format_timestamp(end)
        # Use first few words as default title
        title_words = text.split()[:3]
        title = ' '.join(title_words) + '...' if len(title_words) >= 3 else ' '.join(title_words)

        lines.append(f"[{start_ts}-{end_ts}] {{{title}}} {text}")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse highlight annotations from transcript markdown"
    )
    parser.add_argument("transcript", help="Path to transcript markdown file")
    parser.add_argument("--output", "-o", help="Output highlight script path")
    parser.add_argument("--video", "-v", help="Path to source video file")
    parser.add_argument("--gap", "-g", type=int, default=10,
                        help="Max gap (seconds) to merge consecutive highlights (default: 10)")

    args = parser.parse_args()

    transcript_path = Path(args.transcript).resolve()

    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}")
        sys.exit(1)

    # Read transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract highlights
    highlights = extract_highlights(content)

    if not highlights:
        print("No highlights found. Use <u>text</u> or ==text== to mark highlights.")
        sys.exit(1)

    print(f"Found {len(highlights)} highlighted segments")

    # Merge consecutive highlights
    merged = merge_consecutive_highlights(highlights, args.gap)
    print(f"Merged into {len(merged)} highlight groups")

    # Find end times
    segments = find_segment_end_times(content, merged)

    # Generate script
    script = generate_highlight_script(segments, args.video, str(transcript_path))

    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = transcript_path.parent / f"{transcript_path.stem} - highlight_script.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"\nHighlight script generated: {output_path}")

    # Print summary
    print("\nSegments:")
    for i, (start, end, text) in enumerate(segments, 1):
        duration = end - start
        print(f"  [{i}] {format_timestamp(start)}-{format_timestamp(end)} ({duration}s): {text[:50]}...")


if __name__ == "__main__":
    main()
