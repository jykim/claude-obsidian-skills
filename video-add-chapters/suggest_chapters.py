#!/usr/bin/env python3
"""
Suggest chapter boundaries by analyzing transcript for transition signals.
Detects topic changes based on linguistic patterns and pauses.

Usage:
    python suggest_chapters.py "video.mp4"
    python suggest_chapters.py "transcript.json" --threshold 0.7
"""

import argparse
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

# Korean transition signal patterns
# Based on 0108 AI4PKM 온보딩 비디오 분석

SECTION_START_PATTERNS = [
    (r"네\s*이제\s*한번", 0.9, "topic_start"),
    (r"우선은\s*.+\s*설치", 0.85, "installation_start"),
    (r"그러면\s*이제", 0.8, "transition"),
    (r"다음은", 0.85, "next_topic"),
    (r"그래서\s*이제", 0.75, "continuation"),
    (r"자\s*그러면", 0.8, "new_section"),
    (r"이번에는", 0.85, "new_topic"),
    (r"첫\s*번째로", 0.9, "numbered_start"),
    (r"두\s*번째로", 0.9, "numbered_start"),
]

SECTION_END_PATTERNS = [
    (r"네\s*그래서\s*설명은\s*드렸고", 0.95, "explanation_end"),
    (r"여기까지\s*질문\s*있으신가요", 0.9, "q_and_a"),
    (r"그래서\s*요거는\s*그냥\s*편한\s*대로", 0.8, "optional_end"),
    (r"요거는\s*이제\s*여기까지", 0.85, "section_end"),
    (r"이렇게\s*하시면\s*됩니다", 0.8, "instruction_end"),
]

# Pause threshold (seconds) - long pauses often indicate topic changes
PAUSE_THRESHOLD = 3.0
PAUSE_CONFIDENCE = 0.6


@dataclass
class ChapterSuggestion:
    """A suggested chapter boundary."""
    timestamp: float  # seconds
    confidence: float  # 0-1
    reason: str
    context: str  # surrounding text
    pattern_type: Optional[str] = None


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def detect_transition_signals(segments: List[dict]) -> List[ChapterSuggestion]:
    """Detect transition signals in transcript segments."""
    suggestions = []

    for seg in segments:
        text = seg.get("text", "")
        start = seg.get("start", 0)

        # Check start patterns
        for pattern, confidence, ptype in SECTION_START_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                suggestions.append(ChapterSuggestion(
                    timestamp=start,
                    confidence=confidence,
                    reason=f"Section start signal: '{pattern}'",
                    context=text[:100],
                    pattern_type=ptype
                ))
                break

        # Check end patterns (mark the next segment as potential start)
        for pattern, confidence, ptype in SECTION_END_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # End pattern found - mark this for potential chapter boundary
                suggestions.append(ChapterSuggestion(
                    timestamp=seg.get("end", start + 5),
                    confidence=confidence * 0.9,  # Slightly lower for end-based detection
                    reason=f"Section end signal: '{pattern}'",
                    context=text[:100],
                    pattern_type=f"after_{ptype}"
                ))
                break

    return suggestions


def detect_pauses(segments: List[dict], threshold: float = PAUSE_THRESHOLD) -> List[ChapterSuggestion]:
    """Detect long pauses between segments that might indicate topic changes."""
    suggestions = []

    for i in range(1, len(segments)):
        prev_end = segments[i-1].get("end", 0)
        curr_start = segments[i].get("start", 0)
        gap = curr_start - prev_end

        if gap >= threshold:
            suggestions.append(ChapterSuggestion(
                timestamp=curr_start,
                confidence=min(PAUSE_CONFIDENCE + (gap - threshold) * 0.1, 0.85),
                reason=f"Long pause ({gap:.1f}s)",
                context=segments[i].get("text", "")[:100],
                pattern_type="pause"
            ))

    return suggestions


def merge_nearby_suggestions(suggestions: List[ChapterSuggestion],
                             window: float = 30.0) -> List[ChapterSuggestion]:
    """Merge suggestions that are close together, keeping the highest confidence."""
    if not suggestions:
        return []

    # Sort by timestamp
    sorted_sugs = sorted(suggestions, key=lambda x: x.timestamp)
    merged = []
    current_group = [sorted_sugs[0]]

    for sug in sorted_sugs[1:]:
        if sug.timestamp - current_group[-1].timestamp < window:
            current_group.append(sug)
        else:
            # Pick the highest confidence from the group
            best = max(current_group, key=lambda x: x.confidence)
            merged.append(best)
            current_group = [sug]

    # Don't forget the last group
    if current_group:
        best = max(current_group, key=lambda x: x.confidence)
        merged.append(best)

    return merged


def load_transcript(path: Path) -> dict:
    """Load transcript from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Suggest chapter boundaries from transcript")
    parser.add_argument("input", help="Video file or transcript JSON")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="Minimum confidence threshold (default: 0.6)")
    parser.add_argument("--pause-threshold", type=float, default=PAUSE_THRESHOLD,
                        help=f"Pause threshold in seconds (default: {PAUSE_THRESHOLD})")
    parser.add_argument("--output", help="Output JSON file (default: {input}_chapter_suggestions.json)")

    args = parser.parse_args()

    input_path = Path(args.input).resolve()

    # Determine transcript path
    if input_path.suffix.lower() == ".json":
        transcript_path = input_path
    else:
        # Assume it's a video file, look for transcript
        video_name = input_path.stem
        transcript_path = input_path.parent / f"{video_name} - transcript.json"

    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}")
        print("Run transcribe_video.py first to generate the transcript.")
        sys.exit(1)

    print(f"Loading transcript: {transcript_path}")
    data = load_transcript(transcript_path)
    segments = data.get("segments", [])

    if not segments:
        print("Error: No segments found in transcript")
        sys.exit(1)

    print(f"Analyzing {len(segments)} segments...")

    # Detect transition signals
    signal_suggestions = detect_transition_signals(segments)
    print(f"  Found {len(signal_suggestions)} transition signals")

    # Detect pauses
    pause_suggestions = detect_pauses(segments, args.pause_threshold)
    print(f"  Found {len(pause_suggestions)} significant pauses")

    # Combine and merge
    all_suggestions = signal_suggestions + pause_suggestions
    merged = merge_nearby_suggestions(all_suggestions)

    # Filter by threshold
    filtered = [s for s in merged if s.confidence >= args.threshold]
    print(f"  After merging and filtering: {len(filtered)} suggestions")

    # Sort by timestamp
    filtered.sort(key=lambda x: x.timestamp)

    # Output
    output_path = Path(args.output) if args.output else \
                  transcript_path.parent / f"{transcript_path.stem.replace(' - transcript', '')}_chapter_suggestions.json"

    output_data = {
        "source": str(transcript_path),
        "threshold": args.threshold,
        "total_segments": len(segments),
        "suggestions": [asdict(s) for s in filtered]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved suggestions to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("CHAPTER BOUNDARY SUGGESTIONS")
    print("=" * 60)

    for i, sug in enumerate(filtered, 1):
        ts = format_timestamp(sug.timestamp)
        print(f"\n{i:2d}. [{ts}] (confidence: {sug.confidence:.2f})")
        print(f"    Reason: {sug.reason}")
        print(f"    Context: {sug.context[:60]}...")

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Review these suggestions against the video")
    print("2. Adjust timestamps based on actual content transitions")
    print("3. Remember: keyword first mention ≠ chapter start")
    print("4. Look for transition signals like '네 이제 한번 가보시죠'")
    print("=" * 60)


if __name__ == "__main__":
    main()
