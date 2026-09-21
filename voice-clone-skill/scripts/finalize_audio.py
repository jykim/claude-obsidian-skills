#!/usr/bin/env python3
"""Idempotently make cloned PCM WAV files safe at edit boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path

from audio_tail import (
    DEFAULT_FADE_SECONDS,
    DEFAULT_SILENCE_SECONDS,
    finalize_wav,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add trailing silence to PCM WAV files without fading speech."
    )
    parser.add_argument(
        "--input",
        required=True,
        nargs="+",
        type=Path,
        help="WAV file or directory containing WAV files",
    )
    parser.add_argument("--fade-ms", type=float, default=DEFAULT_FADE_SECONDS * 1000)
    parser.add_argument(
        "--silence-ms", type=float, default=DEFAULT_SILENCE_SECONDS * 1000
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess even when the file already has a cut-safe tail",
    )
    return parser.parse_args()


def collect_wavs(inputs: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for item in inputs:
        resolved = item.expanduser().resolve()
        if resolved.is_dir():
            files.update(resolved.glob("*.wav"))
        elif resolved.is_file() and resolved.suffix.casefold() == ".wav":
            files.add(resolved)
        else:
            raise SystemExit(f"Expected a WAV file or directory: {resolved}")
    if not files:
        raise SystemExit("No WAV files found")
    return sorted(files)


def main() -> None:
    args = parse_args()
    for audio in collect_wavs(args.input):
        metrics, changed = finalize_wav(
            audio,
            fade_seconds=args.fade_ms / 1000,
            silence_seconds=args.silence_ms / 1000,
            force=args.force,
        )
        status = "FINALIZED" if changed else "ALREADY_SAFE"
        print(
            f"{status}: {audio} | silence={metrics.zero_tail:.3f}s "
            f"edge={metrics.edge_level:.6f} fade={args.fade_ms:.0f}ms"
        )


if __name__ == "__main__":
    main()
