#!/usr/bin/env python3
"""Cut-safe PCM WAV tail helpers shared by voice-clone scripts."""

from __future__ import annotations

import array
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


DEFAULT_FADE_SECONDS = 0.0
EMERGENCY_FADE_SECONDS = 0.005
DEFAULT_SILENCE_SECONDS = 0.5
MIN_SILENCE_SECONDS = 0.45
MAX_EDGE_LEVEL = 0.002


@dataclass(frozen=True)
class TailMetrics:
    duration: float
    zero_tail: float
    edge_level: float
    sample_rate: int
    channels: int
    sample_width: int

    @property
    def cut_safe(self) -> bool:
        return (
            self.zero_tail >= MIN_SILENCE_SECONDS
            and self.edge_level <= MAX_EDGE_LEVEL
        )


def inspect_tail(path: Path) -> TailMetrics:
    with wave.open(str(path), "rb") as source:
        sample_rate = source.getframerate()
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        frame_count = source.getnframes()
        payload = source.readframes(frame_count)

    if sample_width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV, got {sample_width * 8}-bit: {path}")

    samples = array.array("h")
    samples.frombytes(payload)
    if channels > 1:
        samples = array.array("h", samples[::channels])

    last_nonzero = next(
        (index for index in range(len(samples) - 1, -1, -1) if samples[index]),
        -1,
    )
    zero_samples = len(samples) if last_nonzero < 0 else len(samples) - 1 - last_nonzero
    edge_level = 0.0 if last_nonzero < 0 else abs(samples[last_nonzero]) / 32768
    return TailMetrics(
        duration=frame_count / sample_rate,
        zero_tail=zero_samples / sample_rate,
        edge_level=edge_level,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
    )


def finalize_wav(
    source: Path,
    output: Path | None = None,
    *,
    fade_seconds: float = DEFAULT_FADE_SECONDS,
    silence_seconds: float = DEFAULT_SILENCE_SECONDS,
    force: bool = False,
) -> tuple[TailMetrics, bool]:
    source = source.expanduser().resolve()
    output = source if output is None else output.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Audio not found: {source}")
    if fade_seconds < 0 or silence_seconds < MIN_SILENCE_SECONDS:
        raise ValueError(
            f"Require a non-negative fade and at least {MIN_SILENCE_SECONDS:.2f}s silence"
        )
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required")

    current = inspect_tail(source)
    if not force and current.cut_safe:
        if output != source:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, output)
        return inspect_tail(output), False

    fade_start = max(0.0, current.duration - fade_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}-tail-", suffix=".wav", dir=output.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        filters: list[str] = []
        if fade_seconds > 0:
            filters.append(
                f"afade=t=out:st={fade_start:.6f}:d={fade_seconds}"
            )
        filters.append(f"apad=pad_dur={silence_seconds}")

        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-af",
                ",".join(filters),
                "-ar",
                "24000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(temporary),
            ],
            check=True,
        )
        result = inspect_tail(temporary)
        if not result.cut_safe:
            raise RuntimeError(
                "Tail finalization failed: "
                f"silence={result.zero_tail:.3f}s edge={result.edge_level:.6f}"
            )
        os.replace(temporary, output)
        return result, True
    finally:
        temporary.unlink(missing_ok=True)
