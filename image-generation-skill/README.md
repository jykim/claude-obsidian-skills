# Image Generation Skill

**Automatically generate AI images for documents and slide decks with user-defined styles.**

## Quick Start

Simply ask Claude to:
- "Add images to my presentation"
- "Generate visuals for my slides"
- "Illustrate my markdown document"

Claude will:
1. Analyze your document/slides
2. Ask you to choose a visual style
3. Generate appropriate images
4. Insert them with proper formatting

## Available Styles

1. **Vibrant Modern Cartoon** - Bright, friendly, business-appropriate
2. **Professional Minimalist** - Clean, corporate, muted colors
3. **Playful Illustration** - Hand-drawn, whimsical, creative
4. **Technical Diagram** - Structured, infographic-inspired
5. **Artistic Watercolor** - Soft, expressive, artistic
6. **Bold Graphic** - High contrast, eye-catching, modern
7. **Custom Style** - Describe your own style

## Cost

- $0.04 per image
- Cost estimate shown before generation
- Example: 10 images = $0.40

## Features

- ✅ Automatic section/slide detection
- ✅ Consistent visual style across all images
- ✅ Smart image placement
- ✅ Speaker notes/caption updates
- ✅ Square format optimized for slides
- ✅ Batch generation support

## Technical Details

- Uses OpenAI DALL-E 3 via `generate_slide_cartoon.py`
- Generates 1024x1024 JPG images
- Inserts with `![right fit]()` for slides, `![]()` for documents
- Saves to `_files_/` directory

## Example Output

Before:
```markdown
## AI Changes Everything

**Key points**:
- Traditional skills declining
- New opportunities emerging
```

After:
```markdown
## AI Changes Everything

**Key points**:
- Traditional skills declining
- New opportunities emerging

![right fit](_files_/ai-changes-everything.jpg)

^ This image shows the shift in knowledge work...
```

## Maintained By

This skill is part of the AI4PKM toolkit.
