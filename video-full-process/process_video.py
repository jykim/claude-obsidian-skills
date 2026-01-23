#!/usr/bin/env python3
"""
Video Full Process: Unified workflow for video-clean + video-add-chapters.

Orchestrates transcription, chapter detection, pause removal, and chapter remapping
in a single workflow, reusing the transcript to save API costs.

Usage:
    python process_video.py "video.mp4" --language ko
    python process_video.py "video.mp4" --preview
    python process_video.py "video.mp4" --skip-clean

Steps:
1. Transcribe (reuses if exists)
2. Detect chapters
3. Clean video (remove pauses)
4. Remap chapters to cleaned timestamps
5. Embed chapters into cleaned video
6. Generate chapter documents
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Skill paths (relative to this script)
SCRIPT_DIR = Path(__file__).parent.resolve()
VIDEO_CLEAN_DIR = SCRIPT_DIR.parent / "video-cleaning"
VIDEO_CHAPTERS_DIR = SCRIPT_DIR.parent / "video-add-chapters"


def run_script(script_path: Path, args: list, description: str = "") -> bool:
    """Run a Python script with given arguments."""
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n{'=' * 60}")
    print(f"STEP: {description}" if description else f"Running: {script_path.name}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)
    return result.returncode == 0


def check_file_exists(path: Path, name: str = "File") -> bool:
    """Check if file exists and print status."""
    exists = path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {name}: {path.name}")
    return exists


def main():
    parser = argparse.ArgumentParser(description="Full video processing workflow")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--language", default="ko", help="Language code (default: ko)")
    parser.add_argument("--output-dir", help="Output directory (default: same as video)")
    parser.add_argument("--pause-threshold", type=float, default=1.0,
                        help="Minimum pause length to remove (default: 1.0)")
    parser.add_argument("--preview", action="store_true",
                        help="Preview mode - show what would be done without changes")
    parser.add_argument("--skip-transcribe", action="store_true",
                        help="Skip transcription (use existing transcript)")
    parser.add_argument("--skip-clean", action="store_true",
                        help="Skip video cleaning (only add chapters)")
    parser.add_argument("--skip-chapters", action="store_true",
                        help="Skip chapter detection and embedding")
    parser.add_argument("--no-embed-chapters", action="store_true",
                        help="Skip embedding chapters into video")
    parser.add_argument("--force-transcribe", action="store_true",
                        help="Force re-transcription even if transcript exists")
    parser.add_argument("--youtube-url", help="YouTube URL for chapter links")

    args = parser.parse_args()

    # Validate input
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return 1

    video_name = video_path.stem
    output_dir = Path(args.output_dir) if args.output_dir else video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("VIDEO FULL PROCESS")
    print(f"{'=' * 60}")
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")
    print(f"Language: {args.language}")
    print(f"Mode: {'Preview' if args.preview else 'Execute'}")

    # Define output paths
    transcript_path = output_dir / f"{video_name} - transcript.json"
    chapters_path = output_dir / f"{video_name}_chapter_suggestions.json"
    pauses_path = output_dir / f"{video_name} - pauses.json"
    cleaned_video_path = output_dir / f"{video_name} - edited{video_path.suffix}"
    chapters_remapped_path = output_dir / f"{video_name} - chapters_remapped.json"
    final_video_path = output_dir / f"{video_name} - cleaned-chapters{video_path.suffix}"

    # =========================================================================
    # STEP 1: TRANSCRIPTION
    # =========================================================================
    print(f"\n{'=' * 60}")
    print("STEP 1: TRANSCRIPTION")
    print(f"{'=' * 60}")

    transcript_exists = transcript_path.exists()
    print(f"Transcript exists: {transcript_exists}")

    if transcript_exists and not args.force_transcribe:
        print("Using existing transcript (use --force-transcribe to regenerate)")
    else:
        if args.skip_transcribe and not transcript_exists:
            print("Error: --skip-transcribe specified but transcript doesn't exist")
            return 1

        if not args.skip_transcribe:
            if args.preview:
                print("[PREVIEW] Would run transcription")
            else:
                # Use video-add-chapters transcriber (handles long videos with chunking)
                transcribe_script = VIDEO_CHAPTERS_DIR / "transcribe_video.py"
                if not transcribe_script.exists():
                    # Fallback to video-clean transcriber
                    transcribe_script = VIDEO_CLEAN_DIR / "transcribe_video.py"

                transcribe_args = [
                    str(video_path),
                    "--language", args.language,
                    "--output-dir", str(output_dir)
                ]

                if not run_script(transcribe_script, transcribe_args, "Transcribing video"):
                    print("Error: Transcription failed")
                    return 1

    # =========================================================================
    # STEP 2: CHAPTER DETECTION
    # =========================================================================
    if not args.skip_chapters:
        print(f"\n{'=' * 60}")
        print("STEP 2: CHAPTER DETECTION")
        print(f"{'=' * 60}")

        if not transcript_path.exists():
            print("Error: Transcript required for chapter detection")
            return 1

        if args.preview:
            print("[PREVIEW] Would detect chapter boundaries")
        else:
            suggest_script = VIDEO_CHAPTERS_DIR / "suggest_chapters.py"
            if suggest_script.exists():
                suggest_args = [
                    str(video_path),
                    "--output", str(chapters_path)
                ]
                if not run_script(suggest_script, suggest_args, "Detecting chapters"):
                    print("Warning: Chapter detection failed, continuing without chapters")
            else:
                print("Warning: suggest_chapters.py not found, skipping chapter detection")

    # =========================================================================
    # STEP 3: VIDEO CLEANING
    # =========================================================================
    if not args.skip_clean:
        print(f"\n{'=' * 60}")
        print("STEP 3: VIDEO CLEANING")
        print(f"{'=' * 60}")

        if not transcript_path.exists():
            print("Error: Transcript required for video cleaning")
            return 1

        if args.preview:
            print("[PREVIEW] Would remove pauses and filler words")
            # Run in preview mode
            edit_script = VIDEO_CLEAN_DIR / "edit_video_remove_pauses.py"
            if edit_script.exists():
                edit_args = [
                    str(video_path),
                    "--transcript", str(transcript_path),
                    "--pause-threshold", str(args.pause_threshold),
                    "--preview",
                    "--output-pauses", str(pauses_path)
                ]
                run_script(edit_script, edit_args, "Preview: Video cleaning")
        else:
            edit_script = VIDEO_CLEAN_DIR / "edit_video_remove_pauses.py"
            if edit_script.exists():
                edit_args = [
                    str(video_path),
                    "--transcript", str(transcript_path),
                    "--pause-threshold", str(args.pause_threshold),
                    "--output", str(cleaned_video_path),
                    "--output-pauses", str(pauses_path)
                ]
                if not run_script(edit_script, edit_args, "Cleaning video"):
                    print("Error: Video cleaning failed")
                    return 1
            else:
                print("Error: edit_video_remove_pauses.py not found")
                return 1

    # =========================================================================
    # STEP 4: CHAPTER REMAPPING
    # =========================================================================
    if not args.skip_chapters and not args.skip_clean:
        print(f"\n{'=' * 60}")
        print("STEP 4: CHAPTER REMAPPING")
        print(f"{'=' * 60}")

        if not chapters_path.exists():
            print("Warning: No chapters file found, skipping remapping")
        elif not pauses_path.exists():
            print("Warning: No pauses file found, skipping remapping")
        else:
            if args.preview:
                print("[PREVIEW] Would remap chapter timestamps")
            else:
                remap_script = SCRIPT_DIR / "remap_chapters.py"
                remap_args = [
                    str(chapters_path),
                    "--pauses", str(pauses_path),
                    "--output", str(chapters_remapped_path),
                    "--youtube"
                ]
                if not run_script(remap_script, remap_args, "Remapping chapters"):
                    print("Warning: Chapter remapping failed")

    # =========================================================================
    # STEP 5: EMBED CHAPTERS
    # =========================================================================
    if not args.skip_chapters and not args.no_embed_chapters and not args.skip_clean:
        print(f"\n{'=' * 60}")
        print("STEP 5: EMBED CHAPTERS")
        print(f"{'=' * 60}")

        source_video = cleaned_video_path if cleaned_video_path.exists() else video_path
        source_chapters = chapters_remapped_path if chapters_remapped_path.exists() else chapters_path

        if not source_chapters.exists():
            print("Warning: No chapters to embed")
        else:
            if args.preview:
                print(f"[PREVIEW] Would embed chapters from {source_chapters.name} into {source_video.name}")
            else:
                remap_script = SCRIPT_DIR / "remap_chapters.py"
                embed_args = [
                    str(source_chapters),
                    "--pauses", str(pauses_path) if pauses_path.exists() else "",
                    "--video", str(source_video),
                    "--embed-output", str(final_video_path)
                ]
                # Filter out empty args
                embed_args = [a for a in embed_args if a]

                # If no pauses file, we still need to provide one for the script
                # In this case, skip remapping and just embed
                if pauses_path.exists():
                    if not run_script(remap_script, embed_args, "Embedding chapters"):
                        print("Warning: Chapter embedding failed")
                else:
                    print("Note: Skipping chapter embedding (no pauses data)")

    # =========================================================================
    # STEP 6: GENERATE DOCUMENTATION
    # =========================================================================
    if not args.skip_chapters:
        print(f"\n{'=' * 60}")
        print("STEP 6: GENERATE DOCUMENTATION")
        print(f"{'=' * 60}")

        source_chapters = chapters_remapped_path if chapters_remapped_path.exists() else chapters_path

        if not source_chapters.exists():
            print("Warning: No chapters for documentation")
        else:
            if args.preview:
                print("[PREVIEW] Would generate chapter documentation")
            else:
                generate_script = VIDEO_CHAPTERS_DIR / "generate_docs.py"
                if generate_script.exists():
                    source_video = cleaned_video_path if cleaned_video_path.exists() else video_path
                    docs_output_dir = output_dir / f"{video_name} Chapters"

                    gen_args = [
                        str(source_video),
                        "--chapters", str(source_chapters),
                        "--output-dir", str(docs_output_dir)
                    ]
                    if args.youtube_url:
                        gen_args.extend(["--youtube-url", args.youtube_url])

                    if not run_script(generate_script, gen_args, "Generating documentation"):
                        print("Warning: Documentation generation failed")
                else:
                    print("Warning: generate_docs.py not found, skipping documentation")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n{'=' * 60}")
    print("PROCESSING COMPLETE")
    print(f"{'=' * 60}")

    print("\nOutput files:")
    files_to_check = [
        (transcript_path, "Transcript"),
        (chapters_path, "Chapters (original)"),
        (pauses_path, "Pauses data"),
        (cleaned_video_path, "Cleaned video"),
        (chapters_remapped_path, "Chapters (remapped)"),
        (final_video_path, "Final video with chapters"),
    ]

    for path, name in files_to_check:
        check_file_exists(path, name)

    # Check for YouTube chapters file
    yt_chapters = output_dir / f"{video_name} - chapters_remapped_youtube.txt"
    if yt_chapters.exists():
        print(f"  ✓ YouTube chapters: {yt_chapters.name}")

    # Check for chapter docs folder
    docs_dir = output_dir / f"{video_name} Chapters"
    if docs_dir.exists():
        doc_count = len(list(docs_dir.glob("*.md")))
        print(f"  ✓ Chapter docs: {doc_count} files in {docs_dir.name}/")

    print(f"\n{'=' * 60}")
    print("Done!")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
