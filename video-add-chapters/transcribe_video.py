#!/usr/bin/env python3
"""
Transcribe video to text using OpenAI Whisper API.
Handles long videos by chunking audio and merging results with proper timestamp offsets.

Usage:
    python transcribe_video.py "video.mp4"
    python transcribe_video.py "video.mp4" --chunk-duration 600  # 10 min chunks
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)

# Default configuration
DEFAULT_CHUNK_DURATION = 900  # 15 minutes per chunk
DEFAULT_LANGUAGE = "ko"


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_audio_chunks(video_path: Path, output_dir: Path, chunk_duration: int) -> list:
    """Extract audio chunks from video using ffmpeg."""
    duration = get_video_duration(video_path)
    num_chunks = int(duration // chunk_duration) + (1 if duration % chunk_duration > 0 else 0)

    chunks = []
    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_path = output_dir / f"chunk_{i:03d}.m4a"

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(start_time), "-t", str(chunk_duration),
            "-vn", "-acodec", "aac", "-b:a", "128k",
            str(chunk_path)
        ]
        subprocess.run(cmd, capture_output=True)
        chunks.append(chunk_path)
        print(f"  Extracted chunk {i+1}/{num_chunks}: {chunk_path.name}")

    return chunks


def transcribe_chunk(client: OpenAI, chunk_path: Path, chunk_index: int,
                     chunk_duration: int, language: str) -> dict:
    """Transcribe a single chunk and return word-level data with offset timestamps."""
    offset = chunk_index * chunk_duration

    print(f"  Transcribing chunk {chunk_index} (offset: {offset}s)...")

    with open(chunk_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"]
        )

    result = response.model_dump()

    # Adjust timestamps with offset
    if "words" in result:
        for word in result["words"]:
            word["start"] += offset
            word["end"] += offset

    if "segments" in result:
        for segment in result["segments"]:
            segment["start"] += offset
            segment["end"] += offset

    return result


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def save_outputs(merged: dict, output_dir: Path, video_name: str):
    """Save transcript in multiple formats."""
    # JSON transcript
    json_path = output_dir / f"{video_name} - transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {json_path}")

    # Markdown transcript with timestamps
    md_path = output_dir / f"{video_name} - transcript.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {video_name} Video Transcript\n\n")
        f.write(f"**Duration**: {format_timestamp(merged['duration'])}\n")
        f.write(f"**Total Words**: {len(merged.get('words', []))}\n")
        f.write(f"**Total Segments**: {len(merged.get('segments', []))}\n\n")
        f.write("---\n\n")

        for segment in merged.get("segments", []):
            start_ts = format_timestamp(segment["start"])
            f.write(f"**[{start_ts}]** {segment['text']}\n\n")
    print(f"  Saved: {md_path}")

    # Word timings
    timings_path = output_dir / f"{video_name} - word_timings.txt"
    with open(timings_path, "w", encoding="utf-8") as f:
        for word in merged.get("words", []):
            ts = format_timestamp(word["start"])
            f.write(f"[{ts}] {word['word']}\n")
    print(f"  Saved: {timings_path}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe video using Whisper API")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--chunk-duration", type=int, default=DEFAULT_CHUNK_DURATION,
                        help=f"Chunk duration in seconds (default: {DEFAULT_CHUNK_DURATION})")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE,
                        help=f"Language code (default: {DEFAULT_LANGUAGE})")
    parser.add_argument("--output-dir", help="Output directory (default: same as video)")
    parser.add_argument("--keep-chunks", action="store_true",
                        help="Keep audio chunks after transcription")
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="Skip transcription if transcript already exists")

    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    video_name = video_path.stem
    output_dir = Path(args.output_dir) if args.output_dir else video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")

    # Check if transcript already exists
    json_path = output_dir / f"{video_name} - transcript.json"
    if args.skip_if_exists and json_path.exists():
        print(f"\nTranscript already exists: {json_path}")
        print("Skipping transcription (use without --skip-if-exists to regenerate)")
        return

    # Initialize OpenAI client
    client = OpenAI()

    # Create temp dir for chunks
    with tempfile.TemporaryDirectory() as temp_dir:
        chunks_dir = Path(temp_dir) if not args.keep_chunks else output_dir / f"{video_name}_chunks"
        if args.keep_chunks:
            chunks_dir.mkdir(exist_ok=True)

        # Extract audio chunks
        print(f"\n[1/3] Extracting audio chunks ({args.chunk_duration}s each)...")
        chunks = extract_audio_chunks(video_path, Path(chunks_dir), args.chunk_duration)
        print(f"  Created {len(chunks)} chunks")

        # Transcribe each chunk
        print(f"\n[2/3] Transcribing chunks...")
        all_words = []
        all_segments = []
        all_text = []

        for i, chunk_path in enumerate(chunks):
            result = transcribe_chunk(client, chunk_path, i, args.chunk_duration, args.language)

            if "words" in result:
                all_words.extend(result["words"])
            if "segments" in result:
                all_segments.extend(result["segments"])
            if "text" in result:
                all_text.append(result["text"])

            print(f"    Words: {len(result.get('words', []))}, Segments: {len(result.get('segments', []))}")

        # Merge results
        merged = {
            "text": " ".join(all_text),
            "words": all_words,
            "segments": all_segments,
            "language": args.language,
            "duration": len(chunks) * args.chunk_duration,
            "source_video": str(video_path),
            "chunk_duration": args.chunk_duration
        }

        # Save outputs
        print(f"\n[3/3] Saving outputs...")
        save_outputs(merged, output_dir, video_name)

        print(f"\nDone! Total words: {len(all_words)}, Total segments: {len(all_segments)}")


if __name__ == "__main__":
    main()
