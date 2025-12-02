# Video Cleaning Skill

Automated video transcription and editing workflow that removes pauses and filler words from Korean videos using OpenAI Whisper API and FFmpeg.

## When to Use This Skill

Use this skill when you need to:
- Clean up recorded presentations or talks
- Remove awkward pauses and "uh/um" sounds from videos
- Reduce video length by removing dead air
- Create polished videos from raw recordings
- Process Korean language videos with natural speech patterns

**Perfect for**: Presentation recordings, lecture videos, podcast recordings, interview footage, or any speaking video that needs cleaning.

## Requirements

### System Requirements
- **FFmpeg**: Video processing tool (must be installed)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/)

### Python Requirements
- **OpenAI Python SDK**: `pip install openai`
- **OpenAI API Key**: Set environment variable `OPENAI_API_KEY`
  - Get your API key from [platform.openai.com](https://platform.openai.com/)
  - Cost: ~$0.15 per 25-minute video (Whisper transcription)

### Python Version
- Python 3.7 or higher

## How It Works

This skill uses a **two-step workflow**:

### Step 1: Transcription (`transcribe_video.py`)
1. Extracts audio from video using FFmpeg
2. Sends audio to OpenAI Whisper API for transcription
3. Receives word-level timestamps (precise timing for each word)
4. Generates three output files:
   - `{video_name} - transcript.json` (complete API response)
   - `{video_name} - transcript.md` (formatted markdown)
   - `{video_name} - word_timings.txt` (simple text reference)

### Step 2: Video Editing (`edit_video_remove_pauses.py`)
1. Loads word-level transcript from Step 1
2. Identifies long pauses between words (> 1.0 seconds by default)
3. Identifies Korean filler words (어, 음, 아)
4. Calculates which video segments to keep
5. Uses FFmpeg to cut and reassemble video
6. Generates edited video and detailed report

## Conservative Editing Philosophy

This skill uses **conservative editing** to ensure safe, predictable results:

### What Gets Removed
- ✅ **Long pauses** (>1.0 seconds of silence between words)
- ✅ **Clear filler words**: 어, 음, 아 (Korean equivalents of "uh", "um", "ah")

### What Gets Kept
- ✅ **Context-dependent words**: 이제, 뭐, 그, 좀, 네, 약간
  - These words can be legitimate in Korean speech
  - Removing them risks cutting meaningful content
- ✅ **Short pauses** (< 1.0 seconds)
  - Natural breathing and thinking pauses
  - Important for speech rhythm

### Expected Results
- **Time saved**: 5-10% typically (1-2 minutes per 25-minute video)
- **Video segments**: 50-100 cuts (manageable, smooth transitions)
- **Safety**: Very low risk of removing important content
- **Quality**: Natural-sounding edited video

## Usage Guide

### Basic Workflow

```bash
# Step 1: Transcribe your video
python transcribe_video.py "my_presentation.mp4"

# Step 2: Preview what will be removed
python edit_video_remove_pauses.py "my_presentation.mp4" --preview

# Step 3: Create edited video
python edit_video_remove_pauses.py "my_presentation.mp4"
```

### Step 1: Transcription Options

```bash
# Basic transcription (Korean, default)
python transcribe_video.py "video.mp4"

# Custom output directory
python transcribe_video.py "video.mp4" --output-dir "transcripts"

# Keep extracted audio file
python transcribe_video.py "video.mp4" --keep-audio

# English transcription
python transcribe_video.py "video_en.mp4" --language "en"
```

**Transcription outputs** (auto-generated in same directory as video):
- `video - transcript.json` (464 KB for 25-min video, ~2,800 words)
- `video - transcript.md` (formatted with timestamps)
- `video - word_timings.txt` (simple reference)

### Step 2: Video Editing Options

```bash
# Preview mode (see what will be removed)
python edit_video_remove_pauses.py "video.mp4" --preview

# Basic editing (default settings)
python edit_video_remove_pauses.py "video.mp4"

# Custom pause threshold (remove pauses > 0.8 seconds)
python edit_video_remove_pauses.py "video.mp4" --pause-threshold 0.8

# Custom output path
python edit_video_remove_pauses.py "video.mp4" --output "cleaned_video.mp4"

# Adjust padding around cuts (default: 0.1 seconds)
python edit_video_remove_pauses.py "video.mp4" --padding 0.15

# Specify transcript location (if not auto-detected)
python edit_video_remove_pauses.py "video.mp4" --transcript "path/to/transcript.json"
```

**Editing outputs**:
- `video - edited.mov` (cleaned video)
- `video - edited_edit_report.txt` (detailed report)
- `temp_segments/` (temporary, auto-deleted after completion)

## Understanding the Edit Report

After editing, you'll receive a detailed report showing exactly what was removed:

```
============================================================
VIDEO EDIT REPORT (Conservative Mode)
============================================================

SUMMARY
------------------------------------------------------------
Original Duration:  00:25:21.000
Edited Duration:    00:23:16.690
Time Saved:         00:02:04.310 (8.2%)
Segments Kept:      67

PAUSES REMOVED
------------------------------------------------------------
Total Pauses:       43
Total Pause Time:   87.81 seconds

Top 10 Longest Pauses:
   1.  5.64s at 00:07:51.500
   2.  5.52s at 00:09:21.020
   3.  3.54s at 00:00:11.520
   ...

FILLER WORDS REMOVED (Clear Fillers Only)
------------------------------------------------------------
Total Fillers:      28
Breakdown:
  어     :  25 occurrences
  아     :   3 occurrences

SAMPLE EDITS (First 5)
------------------------------------------------------------
  1. Pause (3.54s) at 00:00:11.520
  2. Pause (1.50s) at 00:00:29.400
  3. Filler '어' (0.84s) at 00:05:32.140
  ...
```

## Advanced Usage

### Custom Pause Thresholds

Adjust based on your content:

```bash
# More aggressive pause removal (0.8 seconds)
python edit_video_remove_pauses.py "video.mp4" --pause-threshold 0.8

# Very conservative (only remove 2+ second pauses)
python edit_video_remove_pauses.py "video.mp4" --pause-threshold 2.0
```

**Guidelines**:
- **0.5-0.8s**: Aggressive, removes more pauses but may feel rushed
- **1.0s** (default): Balanced, removes awkward pauses while keeping natural rhythm
- **1.5-2.0s**: Very conservative, only removes obvious dead air

### Batch Processing Multiple Videos

```bash
# Process all videos in a directory
for video in *.mp4; do
    echo "Processing: $video"
    python transcribe_video.py "$video"
    python edit_video_remove_pauses.py "$video"
done
```

### Preview Before Editing

Always preview first when working with important content:

```bash
# Step 1: Transcribe
python transcribe_video.py "important_presentation.mp4"

# Step 2: Preview edits
python edit_video_remove_pauses.py "important_presentation.mp4" --preview

# Step 3: If satisfied, execute
python edit_video_remove_pauses.py "important_presentation.mp4"
```

## File Naming Conventions

The scripts follow consistent naming patterns:

**Input**:
- `presentation.mp4` (your original video)

**Transcription outputs**:
- `presentation - transcript.json` (complete data)
- `presentation - transcript.md` (formatted markdown)
- `presentation - word_timings.txt` (simple reference)

**Editing outputs**:
- `presentation - edited.mov` (cleaned video)
- `presentation - edited_edit_report.txt` (detailed report)

## Technical Details

### FFmpeg Processing

The editing script uses FFmpeg in **codec copy mode** (`-c copy`):
- ✅ **Fast**: No re-encoding, preserves original quality
- ✅ **Efficient**: Processes segments in minutes, not hours
- ⚠️ **Limitation**: Limited to keyframe boundaries
  - May add ~0.8 seconds of padding per cut
  - This is why segment count matters

### Minimum Segment Duration

Segments shorter than **0.1 seconds** are automatically filtered out:
- Prevents FFmpeg errors
- Avoids meaningless micro-cuts
- Ensures smooth playback

### Word-Level Timestamp Precision

Whisper API provides timestamps accurate to ~0.01 seconds:
- Precise enough for clean cuts between words
- Allows surgical removal of specific words
- Enables accurate pause detection

## Troubleshooting

### "Transcript not found" Error

```
Error: Transcript not found: video - transcript.json
```

**Solution**: Run transcription first or specify transcript location:
```bash
python transcribe_video.py "video.mp4"
# OR
python edit_video_remove_pauses.py "video.mp4" --transcript "path/to/transcript.json"
```

### "No word-level data found" Error

**Solution**: Transcript JSON is incomplete or corrupted. Re-run transcription:
```bash
python transcribe_video.py "video.mp4"
```

### FFmpeg Not Found

```
Error: ffmpeg not found
```

**Solution**: Install FFmpeg:
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/)

### OpenAI API Key Missing

```
Error: OPENAI_API_KEY environment variable not set
```

**Solution**: Set your API key:
```bash
export OPENAI_API_KEY="sk-..."  # Add to ~/.bashrc or ~/.zshrc
```

### Edited Video Longer Than Expected

This is normal due to FFmpeg padding at cut points:
- Expected: ~0.5-1 minute longer than calculated duration
- Reason: Codec copy mode adds padding at keyframes
- **More segments = more padding**

### Video Quality Issues

If you notice quality degradation:
- Check that FFmpeg is using `-c copy` mode (it should be)
- Verify original video quality is good
- Consider using `-c:v libx264` for re-encoding (slower but more control)

## Performance Characteristics

### Transcription (Step 1)
- **Speed**: ~1-2 minutes for 25-minute video
- **Cost**: ~$0.15 per 25 minutes (OpenAI Whisper pricing)
- **Output size**: ~500 KB JSON for 25-minute video

### Editing (Step 2)
- **Speed**: ~3-5 minutes for 25-minute video
- **CPU usage**: Low (FFmpeg codec copy is fast)
- **Disk space**: ~2x original video size during processing
  - Temporary segments are auto-deleted after completion

### Expected Time Savings

Based on typical Korean presentation videos:
- **Conservative mode**: 5-10% reduction (1-2 minutes per 25-minute video)
- **Longer pauses**: Can save 10-15% if speaker has many long pauses
- **Professional speakers**: May save less (3-5%) due to fewer pauses

## Example Workflow

Here's a complete example from start to finish:

```bash
# 1. You have a recorded presentation
ls
# presentation.mp4 (25:21 duration)

# 2. Transcribe the video
python transcribe_video.py "presentation.mp4"
# Output: Found 2,835 words
# Cost: $0.15
# Files created:
#   - presentation - transcript.json
#   - presentation - transcript.md
#   - presentation - word_timings.txt

# 3. Preview what will be removed
python edit_video_remove_pauses.py "presentation.mp4" --preview
# Found 43 pauses > 1.0s
# Found 28 filler word instances
# Video will be split into 67 segments
# Time saved: 00:02:04 (8.2%)

# 4. Looks good! Create edited video
python edit_video_remove_pauses.py "presentation.mp4"
# Cutting video segments... (3 minutes)
# Concatenating segments... (1 minute)
# ✅ Success! Edited video saved to: presentation - edited.mov

# 5. Review the results
ls
# presentation.mp4                          (original)
# presentation - edited.mov                 (cleaned, 23:17)
# presentation - edited_edit_report.txt     (detailed report)
# presentation - transcript.json
# presentation - transcript.md
# presentation - word_timings.txt
```

## Best Practices

### 1. Always Preview First
```bash
python edit_video_remove_pauses.py "video.mp4" --preview
```
Review the report before committing to editing.

### 2. Keep Original Files
Never delete your original video until you've verified the edited version.

### 3. Test Threshold Settings
Try different `--pause-threshold` values on a test video to find what works best for your content.

### 4. Check Audio Quality
Ensure audio is clear before transcription. Whisper works best with:
- Clear speech (not too fast or mumbled)
- Minimal background noise
- Good microphone quality

### 5. Batch Process Wisely
For multiple videos, process one completely first to verify settings, then batch the rest.

## Limitations

### What This Skill Cannot Do
- ❌ Remove background noise or improve audio quality
- ❌ Fix video quality issues
- ❌ Remove visual distractions or objects
- ❌ Auto-detect and remove specific speakers
- ❌ Add subtitles or captions (use transcript for this separately)

### Language Support
- ✅ **Optimized for Korean**: Filler word detection is Korean-specific
- ⚠️ **English**: Works for pauses, but filler words need adjustment
- ⚠️ **Other languages**: Transcription works, but filler detection needs customization

### Video Format Compatibility
- ✅ **Tested**: MP4, MOV, AVI, MKV
- ✅ **Output**: MOV format (universally compatible)
- ⚠️ **Codecs**: Best with H.264/AAC, may have issues with exotic codecs

## Cost Breakdown

### OpenAI Whisper API Costs
- **Pricing**: $0.006 per minute of audio
- **Examples**:
  - 25-minute video: $0.15
  - 1-hour video: $0.36
  - 10 videos (25 min each): $1.50

### Computing Costs
- **Transcription**: Minimal (API call only)
- **Editing**: Minimal (local FFmpeg processing)
- **Storage**: ~500 KB per 25-minute video (transcript JSON)

**Total cost per video**: Primarily OpenAI API fees (~$0.006/minute)

## Support & Updates

### Getting Help
- Check error messages in the edit report
- Review troubleshooting section above
- Verify FFmpeg installation: `ffmpeg -version`
- Verify OpenAI API key: `echo $OPENAI_API_KEY`

### Skill Location
```
_Settings_/Skills/video-cleaning/
├── SKILL.md                          # This documentation
├── README.md                         # Quick reference
├── transcribe_video.py               # Step 1: Transcription
└── edit_video_remove_pauses.py       # Step 2: Editing
```

### Version History
- **v1.0** (2024): Initial conservative mode release
  - Removed aggressive and smart clustering modes
  - Focused on reliable, predictable editing
  - Korean filler word support (어, 음, 아)

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ VIDEO CLEANING WORKFLOW - QUICK REFERENCE              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ STEP 1: TRANSCRIBE                                      │
│   python transcribe_video.py "video.mp4"                │
│   → Creates: video - transcript.json                    │
│                                                          │
│ STEP 2: PREVIEW                                         │
│   python edit_video_remove_pauses.py "video.mp4" \      │
│     --preview                                            │
│   → Shows: What will be removed                         │
│                                                          │
│ STEP 3: EDIT                                            │
│   python edit_video_remove_pauses.py "video.mp4"        │
│   → Creates: video - edited.mov                         │
│                                                          │
│ COMMON OPTIONS:                                         │
│   --pause-threshold 0.8    Remove pauses > 0.8s         │
│   --padding 0.15           Add 0.15s padding at cuts    │
│   --output "clean.mp4"     Custom output path           │
│                                                          │
│ WHAT GETS REMOVED:                                      │
│   ✓ Pauses > 1.0 seconds                                │
│   ✓ Filler words: 어, 음, 아                            │
│                                                          │
│ EXPECTED RESULTS:                                       │
│   • 5-10% time reduction                                │
│   • 50-100 video segments                               │
│   • Natural-sounding output                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

**Ready to clean your videos?** Start with the basic workflow and adjust settings as needed. Remember: always preview first, and keep your originals safe!
