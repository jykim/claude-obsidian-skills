# Video Cleaning - Quick Start

Remove pauses and filler words from Korean videos automatically.

## Setup

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
# OR sudo apt install ffmpeg  # Linux

# Install Python dependencies
pip install openai

# Set OpenAI API key
export OPENAI_API_KEY="sk-..."
```

## Basic Usage

```bash
# Step 1: Transcribe video
python transcribe_video.py "my_video.mp4"

# Step 2: Preview edits
python edit_video_remove_pauses.py "my_video.mp4" --preview

# Step 3: Create edited video
python edit_video_remove_pauses.py "my_video.mp4"
```

## What Gets Removed

- ✅ Pauses longer than 1.0 seconds
- ✅ Korean filler words: 어, 음, 아

## Expected Results

- **Time saved**: 5-10% (1-2 min per 25-min video)
- **Cost**: ~$0.15 per 25-min video (OpenAI API)
- **Output**: `{video_name} - edited.mov`

## Common Options

```bash
# Custom pause threshold (remove pauses > 0.8 seconds)
python edit_video_remove_pauses.py "video.mp4" --pause-threshold 0.8

# Custom output path
python edit_video_remove_pauses.py "video.mp4" --output "cleaned.mp4"

# Adjust padding around cuts
python edit_video_remove_pauses.py "video.mp4" --padding 0.15

# Transcribe English video
python transcribe_video.py "video.mp4" --language "en"
```

## Output Files

**After transcription**:
- `video - transcript.json` (complete data)
- `video - transcript.md` (formatted)
- `video - word_timings.txt` (reference)

**After editing**:
- `video - edited.mov` (cleaned video)
- `video - edited_edit_report.txt` (detailed report)

## Troubleshooting

**"Transcript not found"**: Run transcription first
```bash
python transcribe_video.py "video.mp4"
```

**"FFmpeg not found"**: Install FFmpeg
```bash
brew install ffmpeg  # macOS
```

**"API key missing"**: Set environment variable
```bash
export OPENAI_API_KEY="sk-..."
```

## Full Documentation

See [SKILL.md](_Settings_/Skills/video-cleaning/SKILL.md) for:
- Detailed usage guide
- Advanced options
- Troubleshooting
- Best practices
- Technical details

## Cost Breakdown

- OpenAI Whisper: $0.006 per minute
- 25-minute video: $0.15
- 1-hour video: $0.36

---

**Quick Workflow**: Transcribe → Preview → Edit → Done!
