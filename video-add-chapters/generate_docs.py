#!/usr/bin/env python3
"""
Generate markdown documents from video transcript and chapter definitions.
Creates individual chapter files, index file, YouTube chapter markers, and merged document.

Usage:
    python generate_docs.py "video.mp4" --chapters chapters.json
    python generate_docs.py "video.mp4" --output-dir "./chapters" --youtube-url "https://youtu.be/xxx"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

# Chapter definition format: (start_seconds, title, description)
ChapterDef = Tuple[int, str, str]


def format_timestamp(seconds: float, include_hours: bool = False) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0 or include_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def load_transcript(path: Path) -> dict:
    """Load transcript from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chapters(path: Path) -> List[ChapterDef]:
    """Load chapter definitions from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both list format and dict with 'chapters' key
    chapters_data = data if isinstance(data, list) else data.get("chapters", [])

    chapters = []
    for ch in chapters_data:
        if isinstance(ch, list):
            chapters.append(tuple(ch))
        elif isinstance(ch, dict):
            chapters.append((
                ch.get("start", ch.get("timestamp", 0)),
                ch.get("title", "Untitled"),
                ch.get("description", "")
            ))
    return chapters


def get_segment_text(segments: list, start: float, end: float) -> str:
    """Extract transcript text between start and end times."""
    texts = []
    for seg in segments:
        if seg["end"] > start and seg["start"] < end:
            texts.append(f"**[{format_timestamp(seg['start'])}]** {seg['text']}")
    return "\n\n".join(texts)


def create_chapter_file(chapter_num: int, start: float, end: float,
                        title: str, description: str, segments: list,
                        output_dir: Path, video_path: str, video_name: str,
                        youtube_url: Optional[str] = None) -> Path:
    """Create a markdown file for a chapter."""
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript = get_segment_text(segments, start, end)

    # YouTube link if URL provided
    youtube_link = ""
    if youtube_url:
        base_url = youtube_url.split("?")[0]
        youtube_link = f"- [YouTube에서 보기]({base_url}?t={int(start)})\n"

    content = f"""---
title: "{title}"
video_source: "{Path(video_path).name}"
start_time: "{format_timestamp(start)}"
end_time: "{format_timestamp(end)}"
duration: "{format_timestamp(end - start)}"
chapter: {chapter_num}
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags:
  - video-chapter
---

## 챕터 {chapter_num}: {title}

**시간**: {format_timestamp(start)} - {format_timestamp(end)} ({format_timestamp(end - start)})

{description}

### 비디오 링크
- [이 챕터 시작 지점](file://{video_path}#t={int(start)})
{youtube_link}
### 트랜스크립트

{transcript}

---

*Generated from {Path(video_path).name} transcript on {datetime.now().strftime('%Y-%m-%d')}*
"""

    filename = f"Chapter {chapter_num:02d} - {title.replace('/', '-')}.md"
    filepath = output_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def create_index_file(chapters_info: list, output_dir: Path, video_path: str,
                      video_name: str, total_duration: float,
                      youtube_url: Optional[str] = None) -> Path:
    """Create an index file for all chapters."""
    content = f"""---
title: "{video_name} 비디오 챕터 인덱스"
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
video_source: "{Path(video_path).name}"
total_chapters: {len(chapters_info)}
tags:
  - video-index
---

## {video_name} 비디오

**전체 길이**: {format_timestamp(total_duration, include_hours=True)}
**총 챕터 수**: {len(chapters_info)}개

### 챕터 목록

| # | 시간 | 챕터 | 설명 |
|---|------|------|------|
"""

    for i, (start, end, title, desc, filepath) in enumerate(chapters_info, 1):
        link = f"[[{filepath.name}|{title}]]"
        content += f"| {i} | {format_timestamp(start)} | {link} | {desc} |\n"

    content += f"""
### 비디오 파일
- 원본: `{video_path}`
"""

    if youtube_url:
        content += f"- YouTube: {youtube_url}\n"

    content += f"""
---

*Generated on {datetime.now().strftime('%Y-%m-%d')}*
"""

    index_path = output_dir / "00 - Index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    return index_path


def create_merged_document(chapters_info: list, segments: list,
                           output_dir: Path, video_path: str,
                           video_name: str, total_duration: float,
                           youtube_url: Optional[str] = None) -> Path:
    """Create a single merged document with all chapters."""
    date_str = datetime.now().strftime('%Y-%m-%d')

    content = f"""---
title: "{video_name}"
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
video_source: "{Path(video_path).name}"
duration: "{format_timestamp(total_duration, include_hours=True)}"
total_chapters: {len(chapters_info)}
tags:
  - video-transcript
---

# {video_name}

**비디오 길이**: {format_timestamp(total_duration, include_hours=True)}
**챕터 수**: {len(chapters_info)}개

"""

    if youtube_url:
        content += f"**YouTube**: {youtube_url}\n\n"

    content += "## 목차\n\n"

    for i, (start, end, title, desc, _) in enumerate(chapters_info, 1):
        content += f"{i}. [{title}](#{i}-{title.lower().replace(' ', '-')}) ({format_timestamp(start)})\n"

    content += "\n---\n\n"

    for i, (start, end, title, desc, _) in enumerate(chapters_info, 1):
        yt_link = ""
        if youtube_url:
            base_url = youtube_url.split("?")[0]
            yt_link = f"({base_url}?t={int(start)})"

        content += f"## {i}. {title} [{format_timestamp(start)}]{yt_link}\n\n"
        content += f"*{desc}*\n\n"

        transcript = get_segment_text(segments, start, end)
        content += f"{transcript}\n\n"

    content += f"""---

*Generated from {Path(video_path).name} on {date_str}*
"""

    merged_path = output_dir / f"{date_str} {video_name}.md"
    with open(merged_path, "w", encoding="utf-8") as f:
        f.write(content)

    return merged_path


def create_youtube_chapters(chapters: List[ChapterDef], output_dir: Path,
                            video_name: str) -> Path:
    """Create YouTube chapter markers file."""
    content = f"# YouTube Chapters for {video_name}\n\n"
    content += "Copy the following to your YouTube video description:\n\n"
    content += "---\n\n"

    for start, title, _ in chapters:
        ts = format_timestamp(start)
        content += f"{ts} {title}\n"

    content += "\n---\n"

    yt_path = output_dir / f"{video_name} - youtube_chapters.txt"
    with open(yt_path, "w", encoding="utf-8") as f:
        f.write(content)

    return yt_path


def main():
    parser = argparse.ArgumentParser(description="Generate chapter documents from transcript")
    parser.add_argument("video", help="Video file path")
    parser.add_argument("--chapters", required=True, help="Chapters definition JSON file")
    parser.add_argument("--output-dir", help="Output directory (default: ./chapters)")
    parser.add_argument("--youtube-url", help="YouTube video URL for linking")
    parser.add_argument("--no-merged", action="store_true", help="Skip merged document creation")
    parser.add_argument("--no-chapters", action="store_true", help="Skip individual chapter files")

    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    video_name = video_path.stem

    # Load transcript
    transcript_path = video_path.parent / f"{video_name} - transcript.json"
    if not transcript_path.exists():
        print(f"Error: Transcript not found: {transcript_path}")
        sys.exit(1)

    print(f"Loading transcript: {transcript_path}")
    data = load_transcript(transcript_path)
    segments = data.get("segments", [])
    total_duration = max(seg["end"] for seg in segments) if segments else 0

    # Load chapters
    chapters_path = Path(args.chapters)
    if not chapters_path.exists():
        print(f"Error: Chapters file not found: {chapters_path}")
        sys.exit(1)

    print(f"Loading chapters: {chapters_path}")
    chapters = load_chapters(chapters_path)
    print(f"Found {len(chapters)} chapters")

    # Output directory
    output_dir = Path(args.output_dir) if args.output_dir else \
                 video_path.parent / f"{video_name} Chapters"
    output_dir.mkdir(parents=True, exist_ok=True)

    chapters_info = []

    # Create individual chapter files
    if not args.no_chapters:
        print(f"\nCreating chapter files...")
        for i, (start, title, desc) in enumerate(chapters):
            # Determine end time
            end = chapters[i + 1][0] if i + 1 < len(chapters) else total_duration

            filepath = create_chapter_file(
                i + 1, start, end, title, desc, segments,
                output_dir, str(video_path), video_name, args.youtube_url
            )
            chapters_info.append((start, end, title, desc, filepath))
            print(f"  Created: {filepath.name}")

    # Create index file
    print(f"\nCreating index file...")
    index_path = create_index_file(
        chapters_info, output_dir, str(video_path),
        video_name, total_duration, args.youtube_url
    )
    print(f"  Created: {index_path.name}")

    # Create merged document
    if not args.no_merged:
        print(f"\nCreating merged document...")
        merged_path = create_merged_document(
            chapters_info, segments, output_dir, str(video_path),
            video_name, total_duration, args.youtube_url
        )
        print(f"  Created: {merged_path.name}")

    # Create YouTube chapters
    print(f"\nCreating YouTube chapters...")
    yt_path = create_youtube_chapters(chapters, output_dir, video_name)
    print(f"  Created: {yt_path.name}")

    print(f"\nDone! All files saved to: {output_dir}")


if __name__ == "__main__":
    main()
