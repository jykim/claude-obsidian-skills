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

Convert markdown slides to presentation video using three different workflows: AI-generated visuals (Gemini) or React components (Remotion).

## When to Use This Skill

Activate this skill when the user:
- Asks to create video from markdown slides
- Requests to convert presentation to MP4 format
- Wants to generate narrated video from slides
- Needs automated slide-to-video conversion

## Workflow Comparison

| | Slide-by-Slide (Gemini) | Section-Based (Gemini) | Remotion (React) |
|---|---|---|---|
| **비주얼** | AI JPEG / 슬라이드 | AI JPEG / 섹션 | React 컴포넌트 |
| **API 비용** | ~$0.04/슬라이드 | ~$0.04/섹션 | $0 (로컬 렌더) |
| **필수 키** | GEMINI + OPENAI | GEMINI + OPENAI | OPENAI만 |
| **추가 요건** | Python, ffmpeg | Python, ffmpeg | Node.js 18+, npm |
| **적합** | 빠른 일회성 | 긴 프레젠테이션 | 브랜드/반복 사용, 정밀 제어 |

## When to Use Which

- **Slide-by-Slide (Gemini)**: 빠르게 일회성 영상이 필요할 때. 표준 프레젠테이션에 적합.
- **Section-Based (Gemini)**: 20+ 슬라이드 긴 발표. 섹션별 인포그래픽 스타일 선호 시.
- **Remotion (React)**: 브랜딩 일관성, 반복 제작, 애니메이션 커스터마이징이 필요할 때. API 비용 $0.

## Input Requirements

- **Markdown file** with speaker notes marked with `^` prefix
- **OPENAI_API_KEY** environment variable for TTS audio (all workflows)
- **GEMINI_API_KEY** environment variable for image generation (Workflow 1, 2 only)

## Output Specifications

- **MP4 video**: 1920x1080 (Full HD)
- **Duration**: Each slide displays for duration of its audio narration
- **File naming**: `{input_filename}.mp4`

---

## Shared: Audio Generation (All Workflows)

All three workflows share the same audio generation step.

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/generate_audio.py "{slides_filename}" --output-dir "audio"
```

**Delta update**: Only regenerates audio for slides with changed speaker notes.
- Use `--force` to regenerate all audio files

**Output**:
- `audio/slide_0.mp3`, `slide_1.mp3`, ... (0-indexed)
- Cache file: `audio/.audio_cache.json`

---

## Workflow 1: Slide-by-Slide (Gemini)

### Step 1: Generate Audio Files

See [Shared: Audio Generation](#shared-audio-generation-all-workflows) above.

### Step 2: Generate Slide Images with Gemini

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/create_slides_gemini.py "{slides_filename}" \
  --output-dir "slides-gemini" \
  --style "technical-diagram" \
  --auto-approve
```

**Delta update**: Only regenerates images for slides with changed content.
- Use `--force` to regenerate all slide images

**Style Options**:

| Style | Description | Best For |
|-------|-------------|----------|
| `technical-diagram` | Clean lines, infographic icons, muted blue/gray | Technical, education |
| `professional` | Minimalist, geometric shapes | Corporate, formal |
| `vibrant-cartoon` | Bright gradients, flat design | Marketing, startups |
| `watercolor` | Soft pastels, organic shapes | Creative, personal |

**Other Parameters**:
- `--model`: Gemini model (default: gemini-3-pro-image-preview)
- `--aspect-ratio`: 16:9 (default), 1:1, 9:16, 4:3, 3:4
- `--start-from N`: Resume from slide N
- `--dry-run`: Preview prompts without generating

**Output**:
- `slides-gemini/1.jpeg`, `2.jpeg`, ... (1-indexed)
- Cache file: `slides-gemini/.slides_cache.json`

### Step 3: Create Final Video

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/slides_to_video.py \
  --slides-dir "slides-gemini" \
  --audio-dir "audio" \
  --output "{output_filename}.mp4"
```

---

## Workflow 2: Section-Based (Gemini)

For presentations with many slides, generate one infographic image per section instead of per slide.

### When to Use Section-Based

- Presentations with 20+ slides
- Content naturally groups into logical sections
- Prefer infographic overview per section vs. individual slides
- Want to reduce API costs (fewer images)

### Step 1: Generate Audio Files

See [Shared: Audio Generation](#shared-audio-generation-all-workflows) above.

### Step 2: Generate Section Infographic Images

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/generate_section_images.py "{slides_filename}" \
  --output-dir "slides-section" \
  --style "infographic"
```

**Style Options**:

| Style | Description |
|-------|-------------|
| `infographic` | Clean professional with icons (default) |
| `professional` | Minimalist corporate design |
| `vibrant` | Bright gradients for marketing |
| `technical` | Flowcharts and technical diagrams |

**Other Parameters**:
- `--start-from N`: Resume from section N
- `--force`: Regenerate all images
- `--dry-run`: Preview sections without generating
- `--delay N`: Seconds between API calls (default: 2.0)

### Step 3: Create Video Script (Optional)

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/create_video_script.py "{slides_filename}" \
  --output "video_script.md" \
  --image-dir "slides-section"
```

### Step 4: Review & Edit Narration

1. Open `video_script.md`
2. Review narration in blockquotes
3. Edit directly in the document
4. Update original markdown file with changes
5. Regenerate audio for changed slides

### Step 5: Create Section-Based Video

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/create_section_video.py \
  --slides "{slides_filename}" \
  --audio-dir "audio" \
  --image-dir "slides-section" \
  --output "presentation.mp4"
```

**With config file** (for custom section mappings):

```bash
python create_section_video.py \
  --config "sections.json" \
  --audio-dir "audio" \
  --image-dir "slides-section" \
  --output "presentation.mp4"
```

---

## Workflow 3: Remotion (React Components)

Generate a complete Remotion project with typed React components. No Gemini API needed — visuals are programmatic with animations, tables, bullet lists, and more.

### Prerequisites

- **Node.js 18+** and **npm**
- **OPENAI_API_KEY** for TTS audio generation
- **ffmpeg** (for audio duration detection)

### Step 1: Generate Audio Files

See [Shared: Audio Generation](#shared-audio-generation-all-workflows) above.

### Step 2: Scaffold Remotion Project

```bash
cd "{slides_directory}"
python /Users/lifidea/.claude/skills/markdown-video/scaffold_remotion.py "{slides_filename}" \
  --audio-dir "audio" \
  --output-dir "remotion-video" \
  --project-name "MyVideo"
```

**What it does**:
1. Parses Deckset markdown (same parser as Workflow 1)
2. Classifies each slide layout: `title`, `table`, `bullets`, `two_column`, `numbered_flow`, `closing`
3. Reads audio durations via ffprobe
4. Generates `src/data/slides.ts` (metadata) and `src/data/slideContent.ts` (content)
5. Generates `src/scenes/SlideNN*.tsx` per slide (layout-specific React components)
6. Generates `src/scenes/index.ts` (barrel export)
7. Copies template + audio files
8. Runs `npm install`

**Parameters**:
- `--project-name`: Composition ID (default: derived from filename)
- `--force-scenes`: Overwrite existing scene files (default: skip)
- `--dry-run`: Preview parsing and classification
- `--skip-npm`: Skip npm install step

**Output structure**:
```
remotion-video/
  package.json
  tsconfig.json
  public/
    slide_0.mp3, slide_1.mp3, ...
  src/
    index.ts
    Root.tsx
    Video.tsx
    data/
      slides.ts          ← auto-generated (always overwritten)
      slideContent.ts    ← auto-generated (always overwritten)
    scenes/
      index.ts           ← auto-generated (always overwritten)
      Slide01Title.tsx   ← auto-generated (preserved on re-run)
      Slide02*.tsx       ← auto-generated (preserved on re-run)
      ...
    styles/
      theme.ts
      fonts.ts
    components/
      SlideFrame.tsx
      SlideHeader.tsx
      BulletList.tsx
      ComparisonTable.tsx
      TwoColumn.tsx
      Badge.tsx
      NumberedFlow.tsx
```

### Step 3: Preview & Refine

```bash
cd "remotion-video"
npx remotion studio
```

Opens browser preview at `http://localhost:3000`. Edit scene files in `src/scenes/` to customize layouts, animations, and styling.

### Step 4: Render Final Video

```bash
cd "remotion-video"
npx remotion render src/index.ts MyVideo out/video.mp4
```

Or use the npm script:
```bash
npm run build
```

### Re-scaffolding After Changes

When markdown content changes (e.g., new slides, edited text):

```bash
# Re-run scaffold — data files updated, existing scenes preserved
python scaffold_remotion.py "slides.md" --audio-dir "audio" --output-dir "remotion-video"

# Force overwrite all scenes (discards customizations)
python scaffold_remotion.py "slides.md" --audio-dir "audio" --output-dir "remotion-video" --force-scenes
```

**Idempotency rules**:
- `slides.ts`, `slideContent.ts`, `scenes/index.ts` → always overwritten
- Scene files (`Slide*.tsx`) → preserved unless `--force-scenes`
- `components/`, `styles/` → updated from template
- Audio files → re-copied

### Component Library Reference

| Component | Props | Use Case |
|-----------|-------|----------|
| `SlideFrame` | `audio`, `partColor`, `children` | Wrapper: background, audio, fade transitions |
| `SlideHeader` | `title`, `subtitle?`, `color`, `delay?` | Animated title + accent bar |
| `BulletList` | `items[]`, `delay?`, `color?`, `fontSize?` | Staggered bullet points |
| `ComparisonTable` | `headers[]`, `rows[][]`, `headerColors?` | Animated data table |
| `TwoColumn` | `left`, `right`, `ratio?`, `gap?` | Side-by-side layout |
| `NumberedFlow` | `steps[]`, `delay?`, `color?` | Numbered step sequence with connectors |
| `Badge` | `text`, `variant`, `delay?` | Status badges (success/danger/info/muted) |

---

## Delta Updates

Both audio and image generation (Workflows 1, 2) support **delta updates** — only regenerating what changed.

### How It Works

1. **Content hashing**: Each slide's content is hashed (MD5)
2. **Cache storage**: Hashes stored in `.audio_cache.json` / `.slides_cache.json`
3. **Change detection**: On subsequent runs, only changed slides are regenerated
4. **File verification**: Also checks if output file exists

### Force Regeneration

```bash
# Force regenerate all audio
python generate_audio.py "slides.md" --output-dir "audio" --force

# Force regenerate all images
python create_slides_gemini.py "slides.md" --output-dir "slides-gemini" --force
```

---

## Requirements

### System Dependencies
- **Python 3.7+**
- **ffmpeg**: `brew install ffmpeg`
- **Node.js 18+** (Workflow 3 only): `brew install node`

### Python Packages
```bash
pip install Pillow requests google-genai
```

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."     # Required for all workflows
export GEMINI_API_KEY="..."         # Required for Workflow 1, 2 only
```

---

## Cost Estimation

| Component | Cost | Example (20 slides) |
|-----------|------|---------------------|
| Gemini images (WF 1, 2) | ~$0.04/slide | ~$0.80 |
| OpenAI TTS (all) | ~$0.015/1K chars | ~$0.50 |
| Remotion render (WF 3) | $0 (local) | $0 |
| **Total (WF 1)** | | ~$1.30 |
| **Total (WF 3)** | | ~$0.50 |

With delta updates, subsequent runs only cost for changed slides.

---

## Error Handling

### No speaker notes found
- Slides need `^` prefixed speaker notes for narration
- Example: `^ This is the speaker note for this slide.`

### Pronunciation problems
- Replace technical terms with phonetic equivalents in speaker notes
- Test with `--dry-run` first

### API errors
- Check API key environment variables
- Gemini rate limits: script includes 1-second delay between generations

---

## Quality Checklist

Before marking complete:

**All Workflows**:
- [ ] OPENAI_API_KEY configured
- [ ] Markdown file has speaker notes with `^` prefix
- [ ] Audio files generated successfully
- [ ] Video plays correctly with synced audio
- [ ] Resolution is 1920x1080

**Workflow 1, 2 (Gemini)**:
- [ ] GEMINI_API_KEY configured
- [ ] Slide images generated successfully

**Workflow 3 (Remotion)**:
- [ ] Node.js 18+ installed
- [ ] `npx remotion studio` preview looks correct
- [ ] Scene files customized as needed
- [ ] `npx remotion render` completes without errors
