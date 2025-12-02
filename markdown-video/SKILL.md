---
name: markdown-video
description: Convert Deckset-format markdown slides with speaker notes to presentation video with TTS narration. Use when user requests to create video from slides, generate presentation video, or convert slides to MP4 format.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
license: MIT
---

# Markdown Video Skill

Convert Deckset-format markdown slides to presentation video with TTS audio narration.

## When to Use This Skill

Activate this skill when the user:
- Asks to create video from markdown slides
- Requests to convert presentation to MP4 format
- Wants to generate narrated video from slides
- Mentions video creation from Deckset slides
- Needs automated slide-to-video conversion

## Input Requirements

- **Deckset-format markdown file** with speaker notes
- **Speaker notes** marked with `^` prefix (Deckset format)
- **Images** in `_files_/` directory relative to markdown file
- **OpenAI API Key** in environment for TTS generation

## Output Specifications

- **MP4 video file** with slides synced to audio
- **Resolution**: 1920x1080 (Full HD)
- **Duration**: Each slide displays for duration of its audio narration
- **Standalone file**: No dependencies or broken links
- **File naming**: `{input_filename}.mp4`

## Workflow Options

Choose between two workflows based on your needs:

### Option A: With Deckset (Recommended for Complex Slides)
**Best for**: Professional presentations, complex layouts, emoji support, multiple themes

**Pros**:
- Perfect layout rendering (exactly as designed in Deckset)
- Full emoji support
- All Deckset themes and features available
- Complex image positioning (fit, fill, left, right, etc.)

**Cons**:
- Requires manual Deckset export step
- Deckset app must be installed

### Option B: Auto-Generate (No Deckset Required)
**Best for**: Quick video creation, simple layouts, personal videos

**Pros**:
- Fully automated (no manual steps)
- No Deckset installation required
- Multiple theme options (romantic, professional, minimal)

**Cons**:
- **No emoji support** (PIL limitation - remove emojis from titles)
- Simple gradient backgrounds only
- Limited image positioning (center or side-by-side only)

**Choose Option B when**:
- Creating quick personal videos
- Simple slide layouts are sufficient
- Emojis are not needed in titles
- Deckset is not available

---

## Complete Workflow

### Step 1: Preparation and Validation

**Objective**: Ensure slides are ready for video generation

**Actions**:
1. **Read markdown file** to verify structure
2. **Check speaker notes** - slides must have `^` prefix notes for narration
3. **Verify images** - ensure all referenced images exist
4. **Check pronunciation** - replace technical terms with phonetic equivalents if needed

**Example speaker notes**:
```markdown
# Slide Title
![](image.png)

^ This text becomes the audio narration for the slide.
^ Multiple lines with ^ prefix will be combined.

---
```

**Important**:
- Only slides with `^` speaker notes will be included in video
- Slides without notes are excluded from final video
- Sequential numbering ensures images match audio files

### Step 2: Generate Audio Files

**Objective**: Create TTS audio narration from speaker notes

**Execute**:
```bash
cd "{slides_directory}"
python path/to/generate_audio.py "{slides_filename}" --output-dir "audio"
```

**What it does**:
- Parses markdown to find all `^` speaker notes
- Generates MP3 audio for each slide with notes
- Uses OpenAI TTS API
- Numbers audio files sequentially: `slide_0.mp3`, `slide_1.mp3`, etc.

**Output**:
```
✅ Found 60 slides
   48 slides with speaker notes
   12 slides without speaker notes

⚠️  Slides without speaker notes (excluded from video):
   Slide 0: slidenumbers: true (metadata)
   Slide 6: Section title slide
   ...
```

**Audio Files Created**:
- `audio/slide_0.mp3` - First slide with notes
- `audio/slide_1.mp3` - Second slide with notes
- ...
- `audio/slide_N.mp3` - Last slide with notes

### Step 3: Export Base Slide Images from Deckset

**Objective**: Get high-quality slide images from Deckset

**Manual Process** (User must perform):
1. Open markdown file in Deckset
2. File → Export → Export as Images
3. Choose **JPEG format**, **Full size**
4. Export **ALL slides** (including ones without notes)
5. Save to folder: `base-slides/`

**Important**:
- Images numbered according to markdown order: `1.jpeg`, `2.jpeg`, `3.jpeg`, ...
- Includes ALL slides (with and without notes)
- Used as source for composite image generation

**Agent should**:
- Inform user they need to perform this manual step
- Provide exact instructions
- Wait for user confirmation before proceeding

### Step 4: Create Composite Images

**Objective**: Create images with slides and notes combined

**Execute**:
```bash
cd "{slides_directory}"
python path/to/create_slide_images.py "{slides_filename}" \
  --base-slides "base-slides" \
  --output-dir "slides-with-notes"
```

**What it does**:
1. Parses markdown to find slides with `^` speaker notes
2. Numbers them sequentially (1, 2, 3, ... no gaps)
3. For each slide with notes:
   - Loads corresponding base slide image
   - Creates 1280x1440 composite:
     - Top 720px: Slide content
     - Bottom 720px: Speaker notes as text
   - Saves as `{N}.jpeg`

**Output**:
- Composite images: `1.jpeg`, `2.jpeg`, `3.jpeg`, ...
- Number of images = number of slides with notes
- Perfect 1:1 match with audio files

**Slide-Audio Mapping**:
```
1.jpeg  ← Slide with notes #1 → slide_0.mp3
2.jpeg  ← Slide with notes #2 → slide_1.mp3
3.jpeg  ← Slide with notes #3 → slide_2.mp3
...
48.jpeg ← Slide with notes #48 → slide_47.mp3
```

### Step 5: Create Final Video

**Objective**: Combine images and audio into MP4 video

**Execute**:
```bash
cd "{slides_directory}"
python path/to/slides_to_video.py \
  --slides-dir "slides-with-notes" \
  --audio-dir "audio" \
  --crop-bottom 720 \
  --output "{output_filename}.mp4"
```

**Parameters**:
- `--slides-dir`: Folder with composite images
- `--audio-dir`: Folder with audio files
- `--crop-bottom 720`: Remove bottom 720px (notes section), show only slide
- `--output`: Output video filename

**What it does**:
1. Loads composite images (1.jpeg, 2.jpeg, ...)
2. Matches with audio files (slide_0.mp3, slide_1.mp3, ...)
3. Crops bottom half from each image (removes notes text)
4. Creates video segments with audio narration
5. Concatenates into final MP4

**Output**:
- MP4 video showing only slide content (notes cropped out)
- Audio narration from speaker notes
- Each slide displays for duration of its audio
- Total duration = sum of all audio files

### Step 6: Quality Assurance

**Objective**: Verify video quality and correctness

**Checks**:
- ✅ Video plays correctly
- ✅ Slide-audio sync is accurate
- ✅ All slides appear in correct order
- ✅ Audio quality is clear and natural
- ✅ Proper slide timing (matches audio duration)
- ✅ Notes text NOT visible (cropped out)
- ✅ Resolution is 1920x1080
- ✅ File size reasonable for sharing

**Report to user**:
- Total slides in video
- Total duration
- File size
- Output location

## Technical Specifications

### Audio Generation
- **TTS Engine**: OpenAI API (gpt-4o-mini-tts recommended)
- **Voice**: nova (default), or alloy, echo, fable, onyx, shimmer
- **Model**: tts-1 (standard) or tts-1-hd (higher quality)
- **Format**: MP3
- **Naming**: slide_0.mp3, slide_1.mp3, slide_2.mp3, ... (0-indexed)
- **Only for slides with notes**: Slides without `^` notes have no audio file

### Composite Images
- **Dimensions**: 1280 x 1440 pixels
- **Layout**:
  - Top 720px: Slide content
  - Bottom 720px: Speaker notes text
- **Format**: JPEG
- **Naming**: 1.jpeg, 2.jpeg, 3.jpeg, ... (1-indexed)
- **Only slides with notes**: Sequential numbering, no gaps

### Video Output
- **Resolution**: 1920x1080 (Full HD)
- **Video Codec**: H.264 (libx264)
- **Audio Codec**: AAC at 192kbps
- **Format**: MP4
- **Duration**: Each slide duration matches its audio narration length
- **Crop**: Bottom 720px removed, showing only slide portion

### Slide-Audio Mapping
- **Images**: 1-indexed (1.jpeg, 2.jpeg, 3.jpeg, ...)
- **Audio**: 0-indexed (slide_0.mp3, slide_1.mp3, slide_2.mp3, ...)
- **Mapping**: Image N.jpeg → Audio slide_{N-1}.mp3
- **Perfect match**: Same count, sequential numbering

## Requirements

### System Dependencies
- **Python 3.7+** - For running scripts
- **ffmpeg** - Video processing
- **OpenAI API Key** - For TTS audio generation (in `OPENAI_API_KEY` env var)
- **Pillow** - Image processing: `pip install Pillow`
- **Deckset** - For exporting base slide images

### Environment Check
Before starting, verify:
```bash
# Check Python
python --version

# Check ffmpeg
which ffmpeg

# Check OpenAI API key
echo $OPENAI_API_KEY

# Check Pillow
python -c "import PIL; print(PIL.__version__)"
```

### Installation Commands
```bash
# Install ffmpeg (macOS)
brew install ffmpeg

# Install Python dependencies
pip install Pillow requests openai
```

## Error Handling

### Issue: No speaker notes found

**Problem**: Markdown file has no `^` prefixed speaker notes
**Solution**:
- Inform user slides need speaker notes for narration
- Example of proper format
- Ask if they want to add notes or use slide titles as narration

### Issue: Audio-image mismatch

**Problem**: Different number of audio files and composite images
**Solution**:
- This shouldn't happen with automated workflow
- Verify base slides were exported correctly
- Re-run create_slide_images.py
- Check for parsing errors in markdown

### Issue: Notes visible in video

**Problem**: Forgot `--crop-bottom 720` parameter
**Solution**: Always use `--crop-bottom 720` when creating video

### Issue: Pronunciation problems

**Problem**: TTS mispronounces technical terms
**Solution**:
- Replace with phonetic equivalents in speaker notes
- Use phonetic spelling
- Test with `--dry-run` first

### Issue: Missing ffmpeg

**Problem**: ffmpeg not installed
**Solution**:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Issue: Missing OpenAI API key

**Problem**: `OPENAI_API_KEY` environment variable not set
**Solution**:
```bash
export OPENAI_API_KEY="sk-..."
# Or add to ~/.zshrc for persistence
```

## Quality Checklist

Before marking task complete, verify:

- [ ] All required tools installed (Python, ffmpeg, Pillow)
- [ ] OpenAI API key configured
- [ ] Markdown file has speaker notes with `^` prefix
- [ ] All referenced images exist
- [ ] Audio files generated successfully
- [ ] User exported base slides from Deckset
- [ ] Composite images created (count matches audio files)
- [ ] Final video created successfully
- [ ] Video resolution is 1920x1080
- [ ] Audio-slide sync is correct
- [ ] Notes text NOT visible in video
- [ ] Video duration matches total audio duration
- [ ] File size is reasonable
- [ ] Video plays without errors

## Tool Workflow Diagram

```
Markdown File (slides.md)
         |
         v
[1] generate_audio.py
         |
         v
   Audio Files (slide_0.mp3, slide_1.mp3, ...)
         |
         +------------------+
         |                  |
         v                  v
[2] Deckset Export    Markdown File
    (manual step)          |
         |                  |
         v                  v
  Base Images         Speaker Notes
  (1.jpeg, ...)            |
         |                  |
         +--------+---------+
                  |
                  v
         [3] create_slide_images.py
                  |
                  v
          Composite Images
       (1.jpeg with notes, ...)
                  |
                  v
         [4] slides_to_video.py
                  |
                  v
           Final MP4 Video
```

## Quick Reference Commands

**Full workflow**:
```bash
# Step 1: Create directories
mkdir -p audio base-slides slides-with-notes

# Step 2: Generate audio
python generate_audio.py "slides.md" \
  --output-dir "audio"

# Step 3: Export slides from Deckset (MANUAL)
# → File → Export → Export as Images → JPEG, Full size → base-slides/

# Step 4: Create composite images
python create_slide_images.py "slides.md" \
  --base-slides "base-slides" \
  --output-dir "slides-with-notes"

# Step 5: Create final video
python slides_to_video.py \
  --slides-dir "slides-with-notes" \
  --audio-dir "audio" \
  --crop-bottom 720 \
  --output "presentation.mp4"
```

**Preview mode** (no file creation):
```bash
# Preview audio generation
python generate_audio.py "slides.md" --dry-run

# Preview composite image creation
python create_slide_images.py "slides.md" \
  --base-slides "base-slides" --dry-run
```

## Benefits of Option A Workflow

- **Perfect numbering match** - Images and audio always sync correctly
- **Automated** - No manual counting or matching needed
- **Flexible** - Slides can have notes or be excluded
- **Clean video** - Only slide content visible (notes cropped)
- **Source documentation** - Composite images preserve notes for reference
- **High quality** - Full HD output with natural TTS

---

## Option B: Auto-Generate Workflow (No Deckset)

Use this workflow when Deckset is not available or for quick video creation.

### Prerequisites

1. **Remove emojis from slide titles** (PIL cannot render color emojis)
2. Ensure all images exist and have correct paths
3. OpenAI API key configured

### Step B1: Generate Audio Files

Same as Option A Step 2:

```bash
cd "{slides_directory}"
python path/to/generate_audio.py "{slides_filename}" --output-dir "audio"
```

### Step B2: Generate Slide Images (Auto)

**Execute**:
```bash
cd "{slides_directory}"
python path/to/create_slides_from_markdown.py "{slides_filename}" \
  --output-dir "slides" \
  --theme romantic
```

**Theme Options**:
- `romantic` - Purple/pink gradient, handwriting font (default)
- `professional` - Dark navy gradient, clean sans-serif
- `minimal` - Light background, dark text

**What it does**:
1. Parses markdown to find slides with `^` speaker notes
2. Creates gradient background based on theme
3. Renders title, body text, quotes
4. Embeds images with EXIF rotation fix
5. Outputs numbered JPEG images: `1.jpeg`, `2.jpeg`, ...

### Step B3: Create Final Video

```bash
cd "{slides_directory}"
python path/to/slides_to_video.py \
  --slides-dir "slides" \
  --audio-dir "audio" \
  --output "{output_filename}.mp4"
```

Note: No `--crop-bottom` needed for Option B (images are already final size).

### Option B Quick Reference

```bash
# Full workflow (no Deckset required)
mkdir -p audio slides

# Step 1: Generate audio
python generate_audio.py "slides.md" --output-dir "audio"

# Step 2: Generate slide images (choose theme)
python create_slides_from_markdown.py "slides.md" \
  --output-dir "slides" \
  --theme romantic

# Step 3: Create video
python slides_to_video.py \
  --slides-dir "slides" \
  --audio-dir "audio" \
  --output "presentation.mp4"
```

### Option B Limitations

- **No emoji support**: Remove all emojis from titles before running
- **Simple layouts**: Only center or side-by-side image placement
- **Gradient backgrounds only**: No image backgrounds or complex themes
- **Korean fonts**: Requires NanumPen (handwriting) or system fonts

### When to Choose Each Option

| Scenario | Recommended |
|----------|-------------|
| Professional presentation | Option A |
| Complex slide layouts | Option A |
| Emojis in titles | Option A |
| Quick personal video | Option B |
| No Deckset installed | Option B |
| Simple photo slideshow | Option B |
| Automated pipeline | Option B |
