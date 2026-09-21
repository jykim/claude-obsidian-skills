#!/usr/bin/env python3
"""Generate speech with a saved local Qwen3-TTS voice profile."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT = Path(
    os.environ.get("VOICE_CLONE_PROJECT", Path.home() / "dev" / "VoiceCloning")
).expanduser().resolve()
PYTHON = PROJECT / ".venv" / "bin" / "python"
RUNNER = Path(__file__).with_name("generate_chunked.py")
VOICES = PROJECT / "voices"
VOICE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def available_profiles() -> list[str]:
    if not VOICES.is_dir():
        return []
    return sorted(
        path.name
        for path in VOICES.iterdir()
        if path.is_dir()
        and (path / "reference.wav").is_file()
        and (path / "reference.txt").is_file()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate speech with a saved cloned-voice profile."
    )
    parser.add_argument("--voice", help="Saved voice profile ID")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--language", default="Korean")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-chunk-characters", type=int, default=220)
    parser.add_argument("--between-chunks-ms", type=int, default=220)
    parser.add_argument("--chunks-dir", type=Path)
    parser.add_argument("--list", action="store_true", help="List saved profiles")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profiles = available_profiles()

    if args.list:
        print("\n".join(profiles) if profiles else "No saved voice profiles")
        return
    if not args.text:
        raise SystemExit("--text is required unless --list is used")

    voice = args.voice
    if voice is None:
        if len(profiles) == 1:
            voice = profiles[0]
        elif not profiles:
            raise SystemExit("No saved voice profiles")
        else:
            raise SystemExit(
                "Multiple profiles are available; pass --voice with one of: "
                + ", ".join(profiles)
            )
    if not VOICE_ID.fullmatch(voice):
        raise SystemExit(f"Invalid voice profile ID: {voice}")
    if voice not in profiles:
        raise SystemExit(f"Voice profile not found: {voice}")
    if not PYTHON.is_file() or not RUNNER.is_file():
        raise SystemExit(f"VoiceCloning runtime is incomplete: {PROJECT}")

    profile = VOICES / voice
    transcript = " ".join((profile / "reference.txt").read_text().split())
    if not transcript:
        raise SystemExit(f"Reference transcript is empty: {profile / 'reference.txt'}")

    output = args.output
    if output is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = PROJECT / "output" / f"{voice}-{stamp}.wav"
    elif not output.is_absolute():
        output = PROJECT / output
    output = output.resolve()

    command = [
        str(PYTHON),
        str(RUNNER),
        "--ref-audio",
        str(profile / "reference.wav"),
        "--ref-text",
        transcript,
        "--text",
        args.text,
        "--language",
        args.language,
        "--output",
        str(output),
        "--max-chunk-characters",
        str(args.max_chunk_characters),
        "--between-chunks-ms",
        str(args.between_chunks_ms),
    ]
    if args.chunks_dir:
        chunks_dir = args.chunks_dir
        if not chunks_dir.is_absolute():
            chunks_dir = PROJECT / chunks_dir
        command.extend(["--chunks-dir", str(chunks_dir.resolve())])
    subprocess.run(command, cwd=PROJECT, check=True)

    print(f"PROFILE: {voice}")
    print(f"OUTPUT: {output}")
    print("ENDING: final sentence generated independently; no fade or tail padding")


if __name__ == "__main__":
    main()
