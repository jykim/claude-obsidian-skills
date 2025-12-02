#!/usr/bin/env python3
"""
Video Editor: Remove Pauses & Filler Words

Analyzes word-level transcript to remove long pauses and Korean filler words
from video using FFmpeg for precise cuts.

This version uses CONSERVATIVE editing:
- Removes pauses longer than threshold (default: 1.0 seconds)
- Removes only clear filler words: 어, 음, 아
- Does NOT remove context-dependent words (이제, 뭐, 그, 좀, etc.)

Usage:
    python edit_video_remove_pauses.py <video_file> [options]

Options:
    --transcript <path>        Path to transcript JSON (default: auto-detect)
    --pause-threshold <sec>    Minimum pause length to remove (default: 1.0)
    --padding <sec>            Padding around cuts (default: 0.1)
    --preview                  Show what would be removed without editing
    --output <path>            Output file path (default: <input>_edited.mov)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict


# Korean clear filler words (unambiguous)
CLEAR_FILLERS = ['어', '음', '아']


def load_transcript(json_path: str) -> dict:
    """Load word-level transcript from JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def identify_pauses(words: List[dict], threshold: float) -> List[Tuple[float, float, float]]:
    """
    Identify pauses longer than threshold between words.

    Returns: List of (start_time, end_time, duration) tuples
    """
    pauses = []

    for i in range(len(words) - 1):
        current_end = words[i]['end']
        next_start = words[i + 1]['start']
        pause_duration = next_start - current_end

        if pause_duration >= threshold:
            pauses.append((current_end, next_start, pause_duration))

    return pauses


def identify_filler_words(words: List[dict]) -> List[Dict]:
    """
    Identify clear filler words to remove.

    Returns: List of dicts with word info
    """
    filler_instances = []

    for i, word_data in enumerate(words):
        word = word_data['word'].strip()

        # Check if word is a clear filler
        if word in CLEAR_FILLERS:
            filler_instances.append({
                'index': i,
                'word': word,
                'start': word_data['start'],
                'end': word_data['end']
            })

    return filler_instances


def generate_keep_segments(
    words: List[dict],
    pauses: List[Tuple[float, float, float]],
    fillers: List[Dict],
    padding: float = 0.1
) -> List[Tuple[float, float]]:
    """
    Generate list of video segments to KEEP (everything except pauses and fillers).

    Returns: List of (start, end) tuples for segments to keep
    """
    # Create list of all time ranges to REMOVE
    remove_ranges = []

    # Add pause ranges
    for pause_start, pause_end, _ in pauses:
        remove_ranges.append((pause_start, pause_end))

    # Add filler word ranges
    for filler in fillers:
        remove_ranges.append((filler['start'], filler['end']))

    # Sort by start time
    remove_ranges.sort(key=lambda x: x[0])

    # Merge overlapping ranges
    merged_removes = []
    for start, end in remove_ranges:
        if merged_removes and start <= merged_removes[-1][1]:
            # Overlapping or adjacent, merge
            merged_removes[-1] = (merged_removes[-1][0], max(merged_removes[-1][1], end))
        else:
            merged_removes.append((start, end))

    # Generate KEEP segments (everything between removes)
    keep_segments = []

    # Start from beginning of video
    current_time = 0.0

    for remove_start, remove_end in merged_removes:
        # Add segment before this removal (if it exists and has content)
        if current_time < remove_start - padding:
            keep_segments.append((current_time, remove_start - padding))

        # Move past this removal
        current_time = remove_end + padding

    # Add final segment from last removal to end
    if words:
        video_end = words[-1]['end']
        if current_time < video_end:
            keep_segments.append((current_time, video_end))

    # Filter out segments that are too short (< 0.1 seconds)
    # These cause FFmpeg errors and are too brief to be meaningful
    MIN_SEGMENT_DURATION = 0.1
    keep_segments = [(start, end) for start, end in keep_segments
                     if end - start >= MIN_SEGMENT_DURATION]

    return keep_segments


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm for FFmpeg."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def create_ffmpeg_concat_file(segments: List[Tuple[float, float]], video_path: str, output_path: str):
    """Create FFmpeg concat demuxer file for segment assembly."""
    temp_dir = Path(output_path).parent / "temp_segments"
    temp_dir.mkdir(exist_ok=True)

    concat_file = temp_dir / "concat_list.txt"
    segment_files = []

    with open(concat_file, 'w') as f:
        for i, (start, end) in enumerate(segments):
            segment_file = temp_dir / f"segment_{i:04d}.ts"
            segment_files.append(segment_file)
            f.write(f"file '{segment_file.absolute()}'\n")

    return concat_file, segment_files, temp_dir


def cut_video_segments(video_path: str, segments: List[Tuple[float, float]], segment_files: List[Path]) -> bool:
    """Cut video into segments using FFmpeg."""
    for i, ((start, end), segment_file) in enumerate(zip(segments, segment_files)):
        duration = end - start

        cmd = [
            'ffmpeg',
            '-y',  # Overwrite
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-c', 'copy',  # Fast copy, no re-encoding
            '-avoid_negative_ts', 'make_zero',
            str(segment_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error cutting segment {i}: {result.stderr}", file=sys.stderr)
            return False

        print(f"Cut segment {i+1}/{len(segments)}: {format_time(start)} -> {format_time(end)}")

    return True


def concatenate_segments(concat_file: Path, output_path: str) -> bool:
    """Concatenate video segments using FFmpeg."""
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        output_path
    ]

    print(f"\nConcatenating {len(list(concat_file.parent.glob('segment_*.ts')))} segments...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error concatenating: {result.stderr}", file=sys.stderr)
        return False

    return True


def cleanup_temp_files(temp_dir: Path):
    """Remove temporary segment files."""
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary files")


def generate_report(
    pauses: List[Tuple[float, float, float]],
    fillers: List[Dict],
    keep_segments: List[Tuple[float, float]],
    original_duration: float,
    output_path: str
):
    """Generate human-readable edit report."""

    edited_duration = sum(end - start for start, end in keep_segments)
    time_saved = original_duration - edited_duration

    lines = []
    lines.append("=" * 60)
    lines.append("VIDEO EDIT REPORT (Conservative Mode)")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Original Duration:  {format_time(original_duration)}")
    lines.append(f"Edited Duration:    {format_time(edited_duration)}")
    lines.append(f"Time Saved:         {format_time(time_saved)} ({time_saved/original_duration*100:.1f}%)")
    lines.append(f"Segments Kept:      {len(keep_segments)}")
    lines.append("")

    # Pauses
    lines.append("PAUSES REMOVED")
    lines.append("-" * 60)
    lines.append(f"Total Pauses:       {len(pauses)}")
    lines.append(f"Total Pause Time:   {sum(p[2] for p in pauses):.2f} seconds")
    lines.append("")

    if pauses:
        lines.append("Top 10 Longest Pauses:")
        sorted_pauses = sorted(pauses, key=lambda x: x[2], reverse=True)[:10]
        for i, (start, end, duration) in enumerate(sorted_pauses, 1):
            lines.append(f"  {i:2d}. {duration:5.2f}s at {format_time(start)}")
    lines.append("")

    # Fillers
    lines.append("FILLER WORDS REMOVED (Clear Fillers Only)")
    lines.append("-" * 60)
    lines.append(f"Total Fillers:      {len(fillers)}")

    # Group by word
    filler_counts = {}
    for f in fillers:
        word = f['word']
        filler_counts[word] = filler_counts.get(word, 0) + 1

    if filler_counts:
        lines.append("Breakdown:")
        for word, count in sorted(filler_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {word:6s}: {count:3d} occurrences")
    lines.append("")

    # Sample edits
    lines.append("SAMPLE EDITS (First 5)")
    lines.append("-" * 60)
    all_edits = []

    for start, end, duration in pauses[:5]:
        all_edits.append(('pause', start, end, duration, None))

    for f in fillers[:5]:
        all_edits.append(('filler', f['start'], f['end'], f['end']-f['start'], f['word']))

    all_edits.sort(key=lambda x: x[1])

    for i, (edit_type, start, end, duration, word) in enumerate(all_edits[:5], 1):
        if edit_type == 'pause':
            lines.append(f"  {i}. Pause ({duration:.2f}s) at {format_time(start)}")
        else:
            lines.append(f"  {i}. Filler '{word}' ({duration:.2f}s) at {format_time(start)}")

    lines.append("")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    # Print to console
    print("\n" + report_text)

    # Save to file
    report_file = output_path.replace('.mov', '_edit_report.txt').replace('.mp4', '_edit_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Remove pauses and clear filler words from video (conservative mode)")
    parser.add_argument("video_file", help="Path to video file")
    parser.add_argument("--transcript", help="Path to transcript JSON (default: auto-detect)")
    parser.add_argument("--pause-threshold", type=float, default=1.0, help="Min pause length (seconds)")
    parser.add_argument("--padding", type=float, default=0.1, help="Padding around cuts (seconds)")
    parser.add_argument("--preview", action="store_true", help="Preview without editing")
    parser.add_argument("--output", help="Output file path (default: <input>_edited.mov)")

    args = parser.parse_args()

    # Validate input
    video_path = Path(args.video_file)
    if not video_path.exists():
        print(f"Error: Video file not found: {args.video_file}", file=sys.stderr)
        return 1

    # Find transcript
    if args.transcript:
        transcript_path = Path(args.transcript)
    else:
        # Auto-detect: same name with - transcript.json
        transcript_path = video_path.parent / f"{video_path.stem} - transcript.json"

    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}", file=sys.stderr)
        print("Use --transcript to specify location", file=sys.stderr)
        return 1

    # Output path
    if args.output:
        output_path = args.output
    else:
        output_path = str(video_path.parent / f"{video_path.stem} - edited{video_path.suffix}")

    print(f"Loading transcript from {transcript_path}...")
    transcript = load_transcript(str(transcript_path))
    words = transcript.get('words', [])

    if not words:
        print("Error: No word-level data found in transcript", file=sys.stderr)
        return 1

    print(f"Found {len(words)} words in transcript")

    # Analyze
    print(f"\nAnalyzing pauses (threshold: {args.pause_threshold}s)...")
    pauses = identify_pauses(words, args.pause_threshold)
    print(f"Found {len(pauses)} pauses > {args.pause_threshold}s")

    print(f"\nIdentifying clear filler words (어, 음, 아)...")
    fillers = identify_filler_words(words)
    print(f"Found {len(fillers)} filler word instances")

    # Generate segments
    print(f"\nGenerating keep segments (padding: {args.padding}s)...")
    keep_segments = generate_keep_segments(words, pauses, fillers, args.padding)
    print(f"Video will be split into {len(keep_segments)} segments")

    original_duration = words[-1]['end']

    # Generate report
    generate_report(pauses, fillers, keep_segments, original_duration, output_path)

    # Preview mode - stop here
    if args.preview:
        print("\n[PREVIEW MODE] No video was edited. Remove --preview to proceed.")
        return 0

    # Execute edit
    print(f"\nCreating edited video: {output_path}")
    print("This may take several minutes...")

    # Create temp files
    concat_file, segment_files, temp_dir = create_ffmpeg_concat_file(
        keep_segments, str(video_path), output_path
    )

    try:
        # Cut segments
        print("\nStep 1/2: Cutting video segments...")
        if not cut_video_segments(str(video_path), keep_segments, segment_files):
            return 1

        # Concatenate
        print("\nStep 2/2: Concatenating segments...")
        if not concatenate_segments(concat_file, output_path):
            return 1

        print(f"\n✅ Success! Edited video saved to: {output_path}")

    finally:
        # Cleanup
        cleanup_temp_files(temp_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
