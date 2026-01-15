#!/usr/bin/env python3
"""
Export transcript as an editable highlight script.
Users can delete unwanted lines, then use generate_highlights.py to create video.

Usage:
    python export_highlight_script.py "video.mp4" --transcript "./output/transcript.json"
    python export_highlight_script.py "video.mp4" --transcript "./output/transcript.json" --output "./output/highlights.md"
"""

import argparse
import json
import sys
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def get_video_duration(video_path: Path) -> float:
    """Get video duration using ffprobe."""
    import subprocess
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def load_transcript(transcript_path: Path) -> dict:
    """Load transcript JSON file."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def export_highlight_script(video_path: Path, transcript: dict, output_path: Path):
    """Generate editable highlight script from transcript."""

    segments = transcript.get("segments", [])
    if not segments:
        print("Error: No segments found in transcript")
        sys.exit(1)

    # Get actual video duration
    duration = get_video_duration(video_path)
    if duration == 0:
        duration = transcript.get("duration", 0)

    video_name = video_path.stem

    with open(output_path, "w", encoding="utf-8") as f:
        # Write header
        f.write(f"# Highlight Script: {video_name}\n\n")
        f.write(f"**Source Video**: {video_path}\n")
        f.write(f"**Total Duration**: {format_timestamp(duration)}\n\n")
        f.write("---\n\n")

        # Instructions
        f.write("<!-- INSTRUCTIONS -->\n")
        f.write("<!-- 1. Delete lines you DON'T want in the highlight video -->\n")
        f.write("<!-- 2. Keep lines you WANT to include -->\n")
        f.write("<!-- 3. Add optional title: [START-END] {Title Here} Text content -->\n")
        f.write("<!-- 4. Run: python generate_highlights.py \"this_file.md\" -->\n")
        f.write("<!-- TIP: 0.5s padding is added automatically to avoid mid-sentence cuts -->\n\n")

        # Write segments with start-end timestamps
        for i, segment in enumerate(segments):
            start_time = segment.get("start", 0)

            # Calculate end time: next segment's start or video duration
            if i + 1 < len(segments):
                end_time = segments[i + 1].get("start", start_time + 5)
            else:
                end_time = duration if duration > 0 else start_time + 5

            text = segment.get("text", "").strip()
            if not text:
                continue

            start_ts = format_timestamp(start_time)
            end_ts = format_timestamp(end_time)

            f.write(f"[{start_ts}-{end_ts}] {text}\n\n")

    print(f"Highlight script exported: {output_path}")
    print(f"  Total segments: {len(segments)}")
    print(f"\nNext steps:")
    print(f"  1. Edit {output_path.name} - delete unwanted lines")
    print(f"  2. Run: python generate_highlights.py \"{output_path}\"")


def main():
    parser = argparse.ArgumentParser(description="Export transcript as editable highlight script")
    parser.add_argument("video", help="Path to source video file")
    parser.add_argument("--transcript", "-t", required=True,
                        help="Path to transcript JSON file")
    parser.add_argument("--output", "-o",
                        help="Output path for highlight script (default: video - highlight_script.md)")

    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    transcript_path = Path(args.transcript).resolve()

    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}")
        sys.exit(1)

    # Default output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = transcript_path.parent / f"{video_path.stem} - highlight_script.md"

    # Load transcript
    transcript = load_transcript(transcript_path)

    # Export highlight script
    export_highlight_script(video_path, transcript, output_path)


if __name__ == "__main__":
    main()
