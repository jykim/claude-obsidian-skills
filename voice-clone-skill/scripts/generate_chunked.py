#!/usr/bin/env python3
"""Generate complete-ending speech with direct local Qwen voice cloning."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import mlx.core as mx
from mlx_audio.audio_io import write as audio_write
from mlx_audio.tts.utils import load_model


PROJECT = Path(
    os.environ.get("VOICE_CLONE_PROJECT", Path.home() / "dev" / "VoiceCloning")
).expanduser().resolve()
MODEL = PROJECT / "models/Qwen3-TTS-12Hz-1.7B-Base-8bit"
SAMPLE_RATE = 24_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref-audio", required=True, type=Path)
    parser.add_argument("--ref-text", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", default="Korean")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-chunk-characters", type=int, default=220)
    parser.add_argument("--between-chunks-ms", type=int, default=220)
    parser.add_argument("--chunks-dir", type=Path)
    return parser.parse_args()


def split_sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in re.findall(r".+?(?:[.!?](?=\s|$)|$)", text)]
    if not sentences or " ".join(sentences) != text:
        raise ValueError("Sentence splitting changed the target text")
    return sentences


def chunk_text(text: str, max_characters: int) -> list[str]:
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return sentences

    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences[:-1]:
        candidate = " ".join([*current, sentence])
        if current and len(candidate) > max_characters:
            chunks.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    chunks.append(sentences[-1])

    if " ".join(chunks) != text:
        raise ValueError("Chunking changed the target text")
    return chunks


def generate(model, args: argparse.Namespace, text: str):
    results = list(
        model.generate(
            text=text,
            lang_code=args.language,
            ref_audio=str(args.ref_audio.expanduser().resolve()),
            ref_text=args.ref_text,
            verbose=True,
        )
    )
    if not results:
        raise RuntimeError("The model returned no audio")
    rates = {result.sample_rate for result in results}
    if rates != {SAMPLE_RATE}:
        raise RuntimeError(f"Unexpected sample rates: {sorted(rates)}")
    return mx.concatenate([result.audio for result in results])


def main() -> None:
    args = parse_args()
    text = args.text
    reference = args.ref_audio.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not text.strip():
        raise SystemExit("--text cannot be empty")
    if not args.ref_text.strip():
        raise SystemExit("--ref-text cannot be empty")
    if not reference.is_file():
        raise SystemExit(f"Reference audio not found: {reference}")
    if not (MODEL / "model.safetensors").is_file():
        raise SystemExit(f"Model not found: {MODEL}")
    if output.suffix.lower() != ".wav":
        raise SystemExit("--output must use the .wav extension")
    if args.max_chunk_characters < 1:
        raise SystemExit("--max-chunk-characters must be positive")
    if args.between_chunks_ms < 0:
        raise SystemExit("--between-chunks-ms cannot be negative")

    chunks = chunk_text(text, args.max_chunk_characters)
    model = load_model(MODEL)
    pause = mx.zeros((round(SAMPLE_RATE * args.between_chunks_ms / 1000),))
    pieces = []

    if args.chunks_dir:
        args.chunks_dir.mkdir(parents=True, exist_ok=True)
    for index, chunk in enumerate(chunks, start=1):
        print(f"CHUNK: {index}/{len(chunks)}", flush=True)
        audio = generate(model, args, chunk)
        if args.chunks_dir:
            audio_write(args.chunks_dir / f"chunk-{index:02d}.wav", audio, SAMPLE_RATE)
        if pieces:
            pieces.append(pause)
        pieces.append(audio)

    output.parent.mkdir(parents=True, exist_ok=True)
    audio_write(output, mx.concatenate(pieces), SAMPLE_RATE)
    print(f"CHUNKS: {len(chunks)}")
    print(f"BETWEEN_CHUNKS_MS: {args.between_chunks_ms}")
    print("TRAILING_PROCESSING: none")


if __name__ == "__main__":
    main()
