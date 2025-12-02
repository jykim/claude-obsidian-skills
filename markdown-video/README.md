# Markdown Video - Quick Start

Convert Deckset-format markdown slides to MP4 video with TTS narration.

## Setup

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
# OR sudo apt install ffmpeg  # Linux

# Install Python dependencies
pip install Pillow openai

# Set OpenAI API key
export OPENAI_API_KEY="sk-..."
```

## Input Requirements

| Input | Description |
|-------|-------------|
| Markdown file | Deckset-format with `---` slide separators |
| Speaker notes | Lines starting with `^` become audio narration |
| Images | Referenced in markdown, stored in `_files_/` folder |

### Example Slide Format

```markdown
# Slide Title

![](image.png)

^ This text becomes the audio narration.
^ Multiple lines with ^ prefix are combined.

---
```

## Two Workflow Options

### Option A: With Deckset (Recommended)

Best for professional presentations with complex layouts and emoji support.

```bash
# Step 1: Generate audio from speaker notes
python generate_audio.py "slides.md" --output-dir "audio"

# Step 2: Export slides from Deckset (MANUAL)
# → File → Export → Export as Images → JPEG, Full size → base-slides/

# Step 3: Create composite images (slide + notes)
python create_slide_images.py "slides.md" \
  --base-slides "base-slides" \
  --output-dir "slides-with-notes"

# Step 4: Create final video
python slides_to_video.py \
  --slides-dir "slides-with-notes" \
  --audio-dir "audio" \
  --crop-bottom 720 \
  --output "presentation.mp4"
```

### Option B: Auto-Generate (No Deckset)

Best for quick video creation without Deckset app.

```bash
# Step 1: Generate audio
python generate_audio.py "slides.md" --output-dir "audio"

# Step 2: Generate slide images
python create_slides_from_markdown.py "slides.md" \
  --output-dir "slides" \
  --theme romantic

# Step 3: Create video
python slides_to_video.py \
  --slides-dir "slides" \
  --audio-dir "audio" \
  --output "presentation.mp4"
```

**Theme Options**: `romantic` (purple/pink), `professional` (dark navy), `minimal` (light)

**Limitation**: No emoji support in Option B (PIL cannot render color emojis)

## Expected Output

| Output | Description |
|--------|-------------|
| `audio/slide_N.mp3` | TTS audio files (0-indexed) |
| `slides/N.jpeg` | Slide images (1-indexed) |
| `presentation.mp4` | Final video (1920x1080, H.264) |

### Video Specifications

- **Resolution**: 1920x1080 (Full HD)
- **Video Codec**: H.264 (libx264)
- **Audio Codec**: AAC at 192kbps
- **Duration**: Each slide displays for duration of its audio

## Common Options

```bash
# Preview audio generation (no files created)
python generate_audio.py "slides.md" --dry-run

# Custom TTS voice (OpenAI voices: alloy, echo, fable, nova, onyx, shimmer)
python generate_audio.py "slides.md" --voice nova

# Different theme for auto-generate
python create_slides_from_markdown.py "slides.md" --theme professional

# Custom output filename
python slides_to_video.py --slides-dir "slides" --audio-dir "audio" \
  --output "my_presentation.mp4"
```

## Cost Breakdown

- OpenAI TTS: ~$0.015 per 1,000 characters
- 15-slide presentation (~3,000 chars): ~$0.05
- 50-slide presentation (~10,000 chars): ~$0.15

## Troubleshooting

**"No speaker notes found"**: Add `^` prefixed lines to slides
```markdown
# Title

^ This is a speaker note that becomes audio.
```

**"Emoji not rendering"** (Option B): Remove emojis from titles - PIL limitation

**"FFmpeg not found"**: Install FFmpeg
```bash
brew install ffmpeg  # macOS
```

**"API key missing"**: Set environment variable
```bash
export OPENAI_API_KEY="sk-..."
```

**"Audio-image mismatch"**: Ensure slide count matches
- Images: 1-indexed (1.jpeg, 2.jpeg, ...)
- Audio: 0-indexed (slide_0.mp3, slide_1.mp3, ...)

## Workflow Comparison

| Feature | Option A (Deckset) | Option B (Auto) |
|---------|-------------------|-----------------|
| Emoji support | Yes | No |
| Complex layouts | Yes | Simple only |
| Manual step | Deckset export | None |
| Best for | Professional | Quick/Personal |

## Full Documentation

See [SKILL.md](SKILL.md) for complete workflow details, technical specs, and quality checklists.

---

**Quick Workflow**: Write slides → Generate audio → Create images → Build video!
