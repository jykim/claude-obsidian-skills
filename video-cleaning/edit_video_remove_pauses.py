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
    --no-fillers               Skip filler word removal (only remove pauses)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# FFmpeg-based editing only (MoviePy removed for performance)


# Korean clear filler words (unambiguous)
CLEAR_FILLERS = ['어', '음', '아', '이', '오', '저']


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
    padding: float = 0.1,
    tail_buffer: float = 0.15
) -> List[Tuple[float, float, float]]:
    """
    Generate list of video segments to KEEP (everything except pauses and fillers).

    Returns: List of (start, end, preceding_pause_duration) tuples for segments to keep
             preceding_pause_duration is the duration of the pause that was removed before this segment
             (0 if no pause preceded, or if it was a filler removal)
    """
    # Create list of all time ranges to REMOVE with type info and duration
    remove_ranges = []

    # Add pause ranges (type: 'pause', duration)
    for pause_start, pause_end, pause_duration in pauses:
        remove_ranges.append((pause_start, pause_end, 'pause', pause_duration))

    # Add filler word ranges (type: 'filler', duration=0 for indicator purposes)
    for filler in fillers:
        remove_ranges.append((filler['start'], filler['end'], 'filler', 0))

    # Sort by start time
    remove_ranges.sort(key=lambda x: x[0])

    # Merge overlapping ranges (keep track if any filler is involved, sum pause durations)
    merged_removes = []
    for start, end, rtype, duration in remove_ranges:
        if merged_removes and start <= merged_removes[-1][1]:
            # Overlapping or adjacent, merge (mark as filler if either is filler)
            prev_start, prev_end, prev_type, prev_duration = merged_removes[-1]
            new_type = 'filler' if (prev_type == 'filler' or rtype == 'filler') else 'pause'
            # Keep the max pause duration for indicator
            new_duration = max(prev_duration, duration) if new_type == 'pause' else 0
            merged_removes[-1] = (prev_start, max(prev_end, end), new_type, new_duration)
        else:
            merged_removes.append((start, end, rtype, duration))

    # Generate KEEP segments (everything between removes)
    keep_segments = []

    # Start from beginning of video
    current_time = 0.0
    preceding_pause = 0  # Duration of pause before this segment

    for remove_start, remove_end, remove_type, remove_duration in merged_removes:
        # Add segment before this removal (if it exists and has content)
        # Only add tail_buffer for pauses (silence), NOT for fillers (would include filler audio)
        if current_time < remove_start:
            if remove_type == 'pause':
                segment_end = remove_start + tail_buffer
            else:
                segment_end = remove_start  # No buffer before filler words
            keep_segments.append((current_time, segment_end, preceding_pause))

        # Track the pause duration for the NEXT segment
        preceding_pause = remove_duration if remove_type == 'pause' else 0

        # Move past this removal (add padding to skip any residual sound)
        current_time = remove_end + padding

    # Add final segment from last removal to end
    if words:
        video_end = words[-1]['end']
        if current_time < video_end:
            keep_segments.append((current_time, video_end, preceding_pause))

    # Filter out segments that are too short (< 0.1 seconds)
    # These cause FFmpeg errors and are too brief to be meaningful
    MIN_SEGMENT_DURATION = 0.1
    keep_segments = [(start, end, pause_dur) for start, end, pause_dur in keep_segments
                     if end - start >= MIN_SEGMENT_DURATION]

    return keep_segments


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm for display."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def edit_video_with_ffmpeg(video_path: str, keep_segments: List[Tuple[float, float, float]], output_path: str, skip_indicator: float = 5.0) -> bool:
    """FFmpeg를 사용한 고속 비디오 편집 (drawtext 필터 활용)

    MoviePy 대비 5-10배 빠름. FFmpeg의 네이티브 필터를 사용하여 텍스트 오버레이.

    Args:
        video_path: 입력 비디오 파일 경로
        keep_segments: (start, end, preceding_pause_duration) 튜플 리스트
        output_path: 출력 비디오 파일 경로
        skip_indicator: 이 값 이상의 pause가 스킵되면 텍스트 표시 (0이면 비활성화)
    """
    import subprocess
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp(prefix="video_edit_")
    segment_files = []

    try:
        print(f"Using FFmpeg for fast encoding (temp dir: {temp_dir})")

        for i, (start, end, pause_duration) in enumerate(keep_segments):
            segment_file = os.path.join(temp_dir, f"segment_{i:04d}.mp4")
            segment_files.append(segment_file)
            duration = end - start

            # Build FFmpeg command for this segment
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(duration),
            ]

            # Add drawtext filter if this segment follows a long pause
            if skip_indicator > 0 and pause_duration >= skip_indicator:
                text_duration = min(2.0, duration)
                # Escape special characters for FFmpeg drawtext
                text = f"[Skipping {int(pause_duration)} secs...]"
                # FFmpeg drawtext filter: white text with black border at bottom-right
                drawtext_filter = (
                    f"drawtext=text='{text}':"
                    f"fontsize=48:"
                    f"fontcolor=yellow:"
                    f"borderw=2:"
                    f"bordercolor=black:"
                    f"x=w-tw-20:"
                    f"y=h-th-20:"
                    f"enable='lt(t,{text_duration})'"
                )
                cmd.extend(["-vf", drawtext_filter])

            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                segment_file
            ])

            print(f"Segment {i+1}/{len(keep_segments)}: {start:.2f} -> {end:.2f}", end="")
            if pause_duration >= skip_indicator:
                print(f" [+text overlay]", end="")
            print()

            # Run FFmpeg for this segment
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg error for segment {i}: {result.stderr}", file=sys.stderr)
                return False

        # Create concat list file
        concat_file = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")

        # Concatenate all segments
        print(f"\nConcatenating {len(segment_files)} segments...")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ]

        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg concat error: {result.stderr}", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    finally:
        # Cleanup temp files
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temp directory")


def generate_report(
    pauses: List[Tuple[float, float, float]],
    fillers: List[Dict],
    keep_segments: List[Tuple[float, float, float]],
    original_duration: float,
    output_path: str
):
    """Generate human-readable edit report."""

    edited_duration = sum(end - start for start, end, _ in keep_segments)
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
    parser.add_argument("--no-fillers", action="store_true", help="Skip filler word removal (only remove pauses)")
    parser.add_argument("--skip-indicator", type=float, default=5.0,
                        help="Show 'Skipping X secs' for pauses >= this value (0 to disable)")
    parser.add_argument("--output-pauses", help="Save pauses data to JSON file for chapter remapping")

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

    if args.no_fillers:
        print(f"\nSkipping filler word removal (--no-fillers)")
        fillers = []
    else:
        print(f"\nIdentifying clear filler words ({', '.join(CLEAR_FILLERS)})...")
        fillers = identify_filler_words(words)
        print(f"Found {len(fillers)} filler word instances")

    # Save pauses data if requested (for chapter remapping)
    if args.output_pauses:
        pauses_data = {
            "source_video": str(video_path),
            "transcript": str(transcript_path),
            "pause_threshold": args.pause_threshold,
            "pauses": [
                {"start": start, "end": end, "duration": duration}
                for start, end, duration in pauses
            ],
            "fillers": fillers,
            "total_pause_time": sum(p[2] for p in pauses),
            "total_filler_count": len(fillers)
        }
        with open(args.output_pauses, 'w', encoding='utf-8') as f:
            json.dump(pauses_data, f, ensure_ascii=False, indent=2)
        print(f"\nPauses data saved to: {args.output_pauses}")

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
    success = edit_video_with_ffmpeg(str(video_path), keep_segments, output_path, args.skip_indicator)

    if not success:
        return 1

    print(f"\n✅ Success! Edited video saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
