#!/usr/bin/env python3
"""Prepare a reusable, non-overwriting local voice-clone profile."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT = Path(
    os.environ.get("VOICE_CLONE_PROJECT", Path.home() / "dev" / "VoiceCloning")
).expanduser().resolve()
VOICES = PROJECT / "voices"
VOICE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trim and normalize a reference utterance into a voice profile."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", required=True, type=float)
    parser.add_argument("--transcript", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.expanduser().resolve()
    transcript = " ".join(args.transcript.split())

    if not source.is_file():
        raise SystemExit(f"Source audio not found: {source}")
    if not VOICE_ID.fullmatch(args.voice):
        raise SystemExit("--voice must contain lowercase letters, digits, and hyphens")
    if args.start < 0 or args.end <= args.start:
        raise SystemExit("--end must be greater than a non-negative --start")
    if not transcript:
        raise SystemExit("--transcript cannot be empty")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg and ffprobe are required")

    VOICES.mkdir(parents=True, exist_ok=True)
    profile = VOICES / args.voice
    if profile.exists():
        raise SystemExit(f"Voice profile already exists; refusing overwrite: {profile}")

    temporary = Path(tempfile.mkdtemp(prefix=f".{args.voice}-", dir=VOICES))
    raw = temporary / "reference-raw.wav"
    normalized = temporary / "reference.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                str(args.start),
                "-to",
                str(args.end),
                "-i",
                str(source),
                "-ar",
                "24000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(raw),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(raw),
                "-af",
                "loudnorm=I=-20:LRA=7:TP=-3",
                "-ar",
                "24000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(normalized),
            ],
            check=True,
        )
        (temporary / "reference.txt").write_text(transcript + "\n")

        probe = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,sample_rate,channels,duration",
                "-of",
                "json",
                str(normalized),
            ],
            text=True,
        )
        stream = json.loads(probe)["streams"][0]
        if stream.get("sample_rate") != "24000" or stream.get("channels") != 1:
            raise RuntimeError(f"Unexpected reference format: {stream}")

        temporary.rename(profile)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    print(f"PROFILE: {profile}")
    print(f"DURATION: {float(stream['duration']):.3f}s")
    print(f"TRANSCRIPT: {transcript}")


if __name__ == "__main__":
    main()
