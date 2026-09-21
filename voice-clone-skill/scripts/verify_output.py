#!/usr/bin/env python3
"""Verify cloned WAV format and target-text intelligibility with MLX Whisper."""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import tempfile
import unicodedata
import wave
from pathlib import Path


PROJECT = Path(
    os.environ.get("VOICE_CLONE_PROJECT", Path.home() / "dev" / "VoiceCloning")
).expanduser().resolve()
PYTHON = PROJECT / ".venv" / "bin" / "python"
ASR_MODEL = "mlx-community/whisper-large-v3-turbo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check cloned WAV format and re-transcribed content."
    )
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--language", default="ko")
    parser.add_argument(
        "--release-threshold",
        type=float,
        default=0.02,
        help="Maximum allowed peak in the final 20 ms (0 disables the check)",
    )
    parser.add_argument(
        "--min-trail-ms",
        type=float,
        default=100.0,
        help=(
            "Minimum trailing silence in ms (0 disables). Set 0 for a chunk that is "
            "followed by the pipeline's inter-chunk silence, which supplies the pause"
        ),
    )
    return parser.parse_args()


def comparable(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if character.isalnum())


def tail_peak(path: Path, milliseconds: int = 20) -> float:
    """Peak amplitude of the closing window, as a 0-1 fraction of full scale.

    Whisper reconstructs a clipped '~습니다' as complete text, so transcription
    alone cannot prove the final phoneme was released. A healthy ending decays
    to near zero; speech still at full amplitude on the last sample was cut off.
    """
    with wave.open(str(path), "rb") as handle:
        frames, rate = handle.getnframes(), handle.getframerate()
        take = min(frames, int(rate * milliseconds / 1000))
        if take == 0:
            return 0.0
        handle.setpos(frames - take)
        data = handle.readframes(take)
    samples = struct.unpack("<%dh" % (len(data) // 2), data)
    return max(abs(sample) for sample in samples) / 32768 if samples else 0.0


def trailing_silence_ms(path: Path, floor: float = 0.01) -> float:
    """Length of the near-silent tail, in milliseconds.

    A release can be complete — the closing peak decays to zero — and the file
    can still sound cut off, because the speech stops and the file ends almost
    immediately. Natural phrase endings leave roughly 100 ms or more.
    """
    with wave.open(str(path), "rb") as handle:
        frames, rate = handle.getnframes(), handle.getframerate()
        data = handle.readframes(frames)
    samples = struct.unpack("<%dh" % (len(data) // 2), data)
    index = len(samples)
    while index > 0 and abs(samples[index - 1]) / 32768 < floor:
        index -= 1
    return (len(samples) - index) / rate * 1000


def final_sentence(text: str) -> str:
    sentences = [part.strip() for part in re.findall(r".+?(?:[.!?](?=\s|$)|$)", text)]
    if not sentences:
        raise ValueError("Expected text is empty")
    return sentences[-1]


def main() -> None:
    args = parse_args()
    audio = args.audio.expanduser().resolve()
    if not audio.is_file():
        raise SystemExit(f"Audio not found: {audio}")
    if not PYTHON.is_file():
        raise SystemExit(f"VoiceCloning Python runtime not found: {PYTHON}")

    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,duration",
            "-of",
            "json",
            str(audio),
        ],
        text=True,
    )
    stream = json.loads(probe)["streams"][0]
    if stream.get("codec_name") != "pcm_s16le":
        raise SystemExit(f"Expected 16-bit PCM WAV, got: {stream.get('codec_name')}")
    if stream.get("sample_rate") != "24000" or stream.get("channels") != 1:
        raise SystemExit(f"Expected 24 kHz mono audio, got: {stream}")

    print(f"FORMAT: pcm_s16le, 24000 Hz, mono, {float(stream['duration']):.3f}s")

    with tempfile.TemporaryDirectory(prefix="voice-clone-verify-") as tmp:
        output = Path(tmp) / "transcript"
        subprocess.run(
            [
                str(PYTHON),
                "-m",
                "mlx_whisper.cli",
                str(audio),
                "--model",
                ASR_MODEL,
                "--language",
                args.language,
                "--output-dir",
                tmp,
                "--output-name",
                "transcript",
                "--output-format",
                "json",
                "--verbose",
                "False",
            ],
            cwd=PROJECT,
            check=True,
        )
        actual = json.loads(output.with_suffix(".json").read_text())["text"].strip()

    print(f"EXPECTED: {args.expected_text}")
    print(f"TRANSCRIPT: {actual}")
    ending_matches = comparable(actual).endswith(
        comparable(final_sentence(args.expected_text))
    )
    print(f"END_CHECK: {'PASS' if ending_matches else 'FAIL'}")

    peak = tail_peak(audio)
    release_ok = args.release_threshold <= 0 or peak <= args.release_threshold
    print(f"RELEASE_CHECK: {'PASS' if release_ok else 'FAIL'} (tail peak {peak:.3f})")

    trail = trailing_silence_ms(audio)
    trail_ok = args.min_trail_ms <= 0 or trail >= args.min_trail_ms
    print(f"TRAIL_CHECK: {'PASS' if trail_ok else 'FAIL'} (trailing silence {trail:.0f} ms)")
    content_matches = comparable(actual) == comparable(args.expected_text)
    if not content_matches:
        raise SystemExit("CONTENT_CHECK: FAIL")
    print("CONTENT_CHECK: PASS")
    if not release_ok:
        raise SystemExit(
            f"RELEASE_CHECK: FAIL (tail peak {peak:.3f} > {args.release_threshold:.3f}); "
            "regenerate with sentence-final punctuation appended to the target text"
        )
    if not trail_ok:
        raise SystemExit(
            f"TRAIL_CHECK: FAIL (trailing silence {trail:.0f} ms < {args.min_trail_ms:.0f} ms); "
            "regenerate and keep the take that leaves a longer tail, or pass "
            "--min-trail-ms 0 when the pipeline adds the pause after this chunk"
        )


if __name__ == "__main__":
    main()
