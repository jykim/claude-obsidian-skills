---
name: voice-clone-skill
description: Generate and verify complete-ending local speech with a saved cloned voice, or prepare a reusable Qwen3-TTS voice profile from user-authorized reference audio. Use for cloned-voice narration, including Remotion or video-editing assets, and requests such as 보이스 클론, 이 목소리로 읽어줘, or 클론된 목소리로 음성 생성. Do not use for ordinary preset-voice TTS.
---

# Voice Clone

Use the local MLX runtime selected by `VOICE_CLONE_PROJECT` (default: `~/dev/VoiceCloning`). It should contain the Qwen3-TTS 1.7B Base 8-bit model, a Python 3.11 environment, saved voice profiles, and `clone_voice.py`.

Treat source recordings as immutable. Use only reference voices the user supplied or authorized, and do not upload, publish, or send generated speech unless explicitly requested.

This skill includes the repository owner's authorized `jin` reference profile under `assets/voices/jin/`. To install it locally, copy that directory to `$VOICE_CLONE_PROJECT/voices/jin/`. The sample is provided for transparent voice-cloning experiments; do not use it to deceive, impersonate the speaker, imply endorsement, or bypass consent requirements.

## Choose the mode

- For speech in an existing cloned voice, use the generation workflow below. If exactly one profile exists and the user does not name one, use it. If several exist and the intended voice is ambiguous, list them and ask which one.
- For a new reference recording, create a reusable profile first. If the user supplied no target text, generate the neutral Korean test sentence `안녕하세요. 이 목소리를 바탕으로 만든 보이스 클로닝 테스트입니다.` after preparing the profile.
- Preserve user-provided target text exactly. Default the language to Korean unless the text or request clearly indicates another language.

## Generate with a saved profile

List available profiles when needed:

```bash
python3 <skill-directory>/scripts/generate_voice.py --list
```

Generate speech:

```bash
python3 <skill-directory>/scripts/generate_voice.py \
  --voice jin \
  --text "읽을 문장"
```

The helper reads the profile's `reference.wav` and `reference.txt`, calls the local Base model with both values, and writes a timestamped 24 kHz mono PCM WAV under `$VOICE_CLONE_PROJECT/output/` unless `--output` is provided.

For multi-sentence narration, the helper groups preceding sentences into chunks of at most 220 characters when possible and always generates the final sentence independently. It joins chunks with 220 ms of silence. It does not fade speech or append trailing silence. A single sentence uses the same direct generation path without chunking. Preserve the supplied text exactly; chunking may add timing between sentences but must not add, remove, or rewrite words.

Use `--max-chunk-characters`, `--between-chunks-ms`, or `--chunks-dir` only when a project needs different pacing or retained audit chunks.

Verify every final file:

```bash
python3 <skill-directory>/scripts/verify_output.py \
  --audio "/absolute/path/to/output.wav" \
  --expected-text "읽을 문장" \
  --language ko
```

The verifier checks 24 kHz mono PCM output, re-transcribes it with the locally cached MLX Whisper Large v3 Turbo model, checks that the expected final sentence is present at the end, and runs `RELEASE_CHECK`: the peak amplitude of the closing 20 ms must stay at or below `--release-threshold` (0.02 by default; 0 disables it). Transcription alone cannot prove the ending survived, because Whisper reconstructs a clipped `~습니다` as complete text — a file can pass `END_CHECK` and `CONTENT_CHECK` while the last phoneme is audibly cut. A healthy ending decays to roughly zero; speech still at full amplitude on the final sample was truncated.

It also runs `TRAIL_CHECK`: the near-silent tail must be at least `--min-trail-ms` (100 ms by default; 0 disables it). This is a separate failure mode from `RELEASE_CHECK` and the one listeners notice most. A file can decay to a peak of 0.000 and still sound cut off, because the speech stops and the file ends 20-40 ms later — the ear hears a phrase at 0.3 amplitude vanish instantly. Pass `--min-trail-ms 0` only for a chunk that the pipeline follows with its own inter-chunk silence, which supplies the pause.

If content verification fails, inspect the transcript and retry that narration at most once. After the retry, preserve the candidate and report any remaining near-homophone, proper-name, number, or semantic mismatch instead of looping.

Read a `CONTENT_CHECK` failure before acting on it. Whisper writes Korean numerals as digits (`스물다섯 명` becomes `25명`, `팔십삼 퍼센트` becomes `83%`), so a mismatch confined to numerals, spacing, or a near-homophone is an ASR artifact, not a defective take. What does require regeneration is a transcript that ends with words the target text does not contain — the model sometimes tacks an extra fragment onto the end of a generation, and that fragment is really in the audio.

When a chunk fails `RELEASE_CHECK`, or is transcribed as complete but its release still sounds clipped, regenerate it with sentence-final punctuation appended to the target text. Append `" ."` first, then `"\n."`, then `"."`; the model finishes the last phoneme and emits its own trailing silence, so nothing is trimmed, faded, or padded afterwards. Only punctuation is added — never change, add, or remove a spoken word. Generation is stochastic, so a variant that fails once can succeed on a retry; cycle the variants and retry rather than concluding the sentence cannot be fixed. Verify each candidate with `RELEASE_CHECK` and confirm by transcription that the ending is intact. This applies to every affected internal chunk, not only the narration's final sentence.

### Sentence boundaries inside a chunk

A chunk holding several sentences is generated in one call, and the model tends to rush every phrase ending inside it: the
pauses between sentences shrink and the endings lose their release. `RELEASE_CHECK` and `TRAIL_CHECK` only see the chunk's
last sample, so they cannot detect this. Measure it against the source text instead — count sentences, then count the
150 ms-or-longer silences whose preceding 20 ms sits at or below 0.05. One clean pause per sentence boundary is the target.

Do not judge internal boundaries by scanning every silence for a loud edge. Korean stops (ㄱ/ㄷ/ㅂ/ㅈ) produce 50-120 ms
closures mid-word with the vowel still ringing into them; counting those reports dozens of false cuts and will not match
what the listener hears.

To fix a chunk whose internal boundaries are rushed, separate its sentences with a blank line (`\n\n`) so the model
treats each as its own paragraph. That reliably lengthens the internal pauses — but it also makes the model hurry the
chunk's own closing sentence, and no trailing punctuation rescues it. So split the work:

- join every sentence except the last with `\n\n`, generate that as one part;
- generate the final sentence on its own with trailing punctuation, as above;
- concatenate the two parts with a short pause (about 100 ms).

This is the same "final sentence generated independently" split `generate_chunked.py` already applies at narration level,
applied one level down. Retry each part separately against its own criteria: the body needs one clean pause per internal
boundary, the closing part needs `RELEASE_CHECK` and `TRAIL_CHECK`.

Prefer that method: it leaves the waveform the model produced. Fall back to the guarded-sentence recovery only if punctuation repeatedly fails — generate the exact sentence followed by a short neutral sacrificial sentence in the same model call, locate the sacrificial sentence's first word with Whisper word timestamps, then find the overlapping low-energy interval with `silencedetect` and trim inside that pause while retaining some of its naturally generated silence. Require a real inter-sentence pause (roughly 80 ms or longer) anchored on the detected guard position: Whisper word timestamps can overlap or coincide, and picking merely “the last silence near the end”, or trusting the target's own word end, can delete the target chunk's final sentence. Never infer the boundary from total duration. Do not fade, append silence, rewrite the target sentence, or include the sacrificial sentence in the delivered file. Use a versioned filename and re-run transcription on every trimmed chunk and on the assembled narration.

Only when the user or delivery format explicitly requires actual silence inside the audio file, run the optional legacy finalizer:

```bash
python3 <skill-directory>/scripts/finalize_audio.py \
  --input "/absolute/path/to/file-or-directory"
```

The finalizer is idempotent and defaults to padding only. Do not use it to repair an incomplete final phoneme: regenerate with the independent-final-sentence workflow instead. Reserve `--fade-ms 5` for an explicitly accepted emergency de-click repair.

## Use in video timelines

- Use the directly generated WAV as the source of truth. Do not add a fade or silence tail unless explicitly requested.
- Do not treat trailing zero samples or a low terminal edge as proof that the final phoneme is complete. Verify the final sentence by transcription, `RELEASE_CHECK`, and listening; regenerate when the model stops before a natural release. If a standalone retry still sounds clipped, use the punctuation recovery above rather than adding a synthetic tail.
- Check every chunk, not just each scene's last one. An internal chunk that was cut off is joined to the next chunk by the fixed inter-chunk silence, so the truncation is audible mid-scene while the assembled file's ending looks healthy.
- Judge a scene by three separate measures, because passing one says nothing about the others: the closing peak (`RELEASE_CHECK`), the closing silence (`TRAIL_CHECK`), and one clean pause per internal sentence boundary. The second and third are what a listener reports as “cut off in the middle”.
- When rebuilding a scene from recovered chunks, resolve the source chunk directory explicitly rather than from a pointer the build script rewrites. A pipeline that regenerates its own selection metadata can silently reset that pointer to the original take, and the next rebuild will then reassemble the scene from unrecovered chunks while still reporting success.
- When transcoding to MP3 or AAC, preserve the complete generated waveform.
- Derive each scene duration from the encoded asset, account for transition overlap, and verify that speech end to next speech start remains at least 0.5 seconds.
- For a batch, use versioned filenames so Studio cannot reuse stale audio. Verify every narration rather than sampling only reported timestamps.
- When a batch narration is assembled from chunks, retain a manifest that maps exact source text to each chunk and records the guarded source, detected target-word end, guard-word start, chosen silence interval, and trim time. A whole-file transcript alone cannot prove that every internal boundary is intact.
- Before handoff, confirm every expected ending, no negative or sub-0.5-second speech gaps, and no render or Studio errors attributable to the audio change.

## Prepare a new voice profile

1. Inspect the source with `ffprobe` and `silencedetect`. Transcribe it with `$VOICE_CLONE_PROJECT/.venv/bin/python -m mlx_whisper.cli`, model `mlx-community/whisper-large-v3-turbo`, the correct language, JSON output, and word timestamps. Use `mlx-whisper` rather than `mlx_audio.stt.generate`; the cached checkpoint uses the former's model format.
2. Choose one clean, complete utterance, usually about 5–15 seconds. Exclude clipped or unfinished phrases. Confirm its exact transcript from word timestamps.
3. Create a lowercase hyphenated voice ID and run:

```bash
python3 <skill-directory>/scripts/prepare_voice.py \
  --source "/absolute/path/to/reference.m4a" \
  --voice new-voice-id \
  --start 0.25 \
  --end 7.25 \
  --transcript "기준 음성에서 실제로 말한 정확한 문장"
```

This preserves a raw 24 kHz mono trim, creates a loudness-normalized `reference.wav`, and saves `reference.txt`. It refuses to overwrite an existing profile; do not replace one without a new explicit user request.

4. Generate a short test sentence with the new profile and run `verify_output.py`.

## Deliver the result

Report the chosen voice profile, generated text, duration, format, and verification result. Render the local audio in the response with an absolute path, for example:

```markdown
![클론 음성](/absolute/path/to/output.wav)
```

Keep the reusable profile in `$VOICE_CLONE_PROJECT/voices/<voice-id>/`; do not duplicate the source recording elsewhere.
