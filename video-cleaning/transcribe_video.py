#!/usr/bin/env python3
"""
Video Transcription Tool with Word-Level Timestamps

Extracts audio from video files and transcribes them using OpenAI Whisper API
with word-level and segment-level timestamps for video editing.

Usage:
    python transcribe_video.py <video_file> [--output-dir <dir>] [--keep-audio]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from openai import OpenAI


def extract_audio(video_path: str, output_path: str) -> bool:
    """Extract audio from video using ffmpeg."""
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'aac',  # AAC codec (Whisper compatible)
            '-ab', '128k',  # Bitrate
            '-y',  # Overwrite output file
            output_path
        ]

        print(f"Extracting audio from {video_path}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error extracting audio: {result.stderr}", file=sys.stderr)
            return False

        print(f"Audio extracted to {output_path}")
        return True

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def transcribe_audio(audio_path: str, language: str = "ko") -> dict:
    """Transcribe audio using OpenAI Whisper API with word-level timestamps."""
    try:
        client = OpenAI()

        print(f"Transcribing audio with Whisper API (language: {language})...")

        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                language=language
            )

        print("Transcription complete!")
        return response.model_dump()

    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        return None


def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def create_markdown_transcript(transcript_data: dict, video_name: str, video_path: str) -> str:
    """Create formatted markdown transcript."""
    lines = []

    # YAML frontmatter
    date = datetime.now().strftime("%Y-%m-%d")
    lines.append("---")
    lines.append(f"title: {video_name}")
    lines.append(f"date: {date}")
    lines.append(f"source: {video_path}")
    lines.append("tags:")
    lines.append("  - transcription")
    lines.append("  - video")
    lines.append("---")
    lines.append("")

    # Main transcript header
    lines.append(f"# {video_name}")
    lines.append("")

    # Metadata
    duration = transcript_data.get('duration', 0)
    lines.append(f"**Duration**: {format_timestamp(duration)}")
    lines.append(f"**Language**: {transcript_data.get('language', 'unknown')}")
    lines.append("")

    # Segmented transcript
    lines.append("## Transcript")
    lines.append("")

    segments = transcript_data.get('segments', [])
    for i, segment in enumerate(segments, 1):
        start = segment.get('start', 0)
        end = segment.get('end', 0)
        text = segment.get('text', '').strip()

        # Segment header with timestamp
        lines.append(f"### Segment {i} [{format_timestamp(start)} - {format_timestamp(end)}]")
        lines.append("")
        lines.append(text)
        lines.append("")

    # Word-level timing reference
    lines.append("## Word-Level Timing Data")
    lines.append("")
    lines.append("For video editing reference, see the raw JSON file with word-level timestamps.")
    lines.append("")

    return "\n".join(lines)


def create_word_timing_text(transcript_data: dict) -> str:
    """Create a simple text file with word timings for quick reference."""
    lines = []
    lines.append("# Word-Level Timing")
    lines.append("# Format: [start-end] word")
    lines.append("")

    segments = transcript_data.get('segments', [])
    for segment in segments:
        words = segment.get('words', [])
        for word_data in words:
            word = word_data.get('word', '')
            start = word_data.get('start', 0)
            end = word_data.get('end', 0)
            lines.append(f"[{format_timestamp(start)}-{format_timestamp(end)}] {word}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Transcribe video with word-level timestamps")
    parser.add_argument("video_file", help="Path to video file")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: same as video)")
    parser.add_argument("--language", default="ko", help="Language code (default: ko)")
    parser.add_argument("--keep-audio", action="store_true", help="Keep extracted audio file")

    args = parser.parse_args()

    # Validate input
    video_path = Path(args.video_file)
    if not video_path.exists():
        print(f"Error: Video file not found: {args.video_file}", file=sys.stderr)
        return 1

    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = video_path.parent

    video_name = video_path.stem

    # Paths for outputs
    audio_path = output_dir / f"{video_name}_audio.m4a"
    json_path = output_dir / f"{video_name} - transcript.json"
    md_path = output_dir / f"{video_name} - transcript.md"
    words_path = output_dir / f"{video_name} - word_timings.txt"

    # Step 1: Extract audio
    if not extract_audio(str(video_path), str(audio_path)):
        return 1

    # Step 2: Transcribe
    transcript_data = transcribe_audio(str(audio_path), args.language)
    if not transcript_data:
        return 1

    # Step 3: Save raw JSON
    print(f"Saving raw transcript to {json_path}...")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    # Step 4: Create markdown transcript
    print(f"Creating formatted transcript...")
    markdown = create_markdown_transcript(transcript_data, video_name, str(video_path))
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Markdown transcript saved to {md_path}")

    # Step 5: Create word timing reference
    word_timings = create_word_timing_text(transcript_data)
    with open(words_path, 'w', encoding='utf-8') as f:
        f.write(word_timings)
    print(f"Word timings saved to {words_path}")

    # Cleanup
    if not args.keep_audio:
        audio_path.unlink()
        print(f"Removed temporary audio file")
    else:
        print(f"Audio file kept at {audio_path}")

    print("\nTranscription complete!")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  Word timings: {words_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
