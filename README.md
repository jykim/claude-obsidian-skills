# Claude Obsidian Skills

> Reusable AI agent skills for Obsidian and Markdown workflows with Claude Code, Gemini CLI, and other AI assistants.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Claude Obsidian Skills is a collection of AI agent skills designed to automate personal knowledge management (PKM) workflows. These skills work with Claude Code, Gemini CLI, and other AI assistants that support skill-based extensions.

## Available Skills

### PKM Management Skills

| Skill | Description |
|-------|-------------|
| [ai4pkm-helper](ai4pkm-helper/) | AI4PKM helper for onboarding guidance, quick help, and seamless handoff to DDA for daily use |

### Obsidian Skills

| Skill | Description |
|-------|-------------|
| [obsidian-canvas](obsidian-canvas/) | Create and manage Obsidian Canvas files with automatic layout generation for knowledge maps and visual summaries |
| [obsidian-links](obsidian-links/) | Format, validate, and fix wiki links with proper filename, section, and folder conventions |
| [obsidian-yaml-frontmatter](obsidian-yaml-frontmatter/) | Standardize YAML frontmatter properties with consistent formatting and naming |
| [obsidian-markdown-structure](obsidian-markdown-structure/) | Validate and enforce markdown document structure, heading hierarchy, and organization |
| [obsidian-mermaid](obsidian-mermaid/) | Create Obsidian-compatible Mermaid diagrams avoiding common errors (markdown in labels, wide layouts) |

### Markdown Skills

| Skill | Description |
|-------|-------------|
| [markdown-slides](markdown-slides/) | Create Deckset/Marp compatible presentation slides from markdown content |
| [interactive-writing-assistant](interactive-writing-assistant/) | AI-powered writing companion with outline-prose co-evolution and PKM integration |

### Video Skills

| Skill | Description |
|-------|-------------|
| [markdown-video](markdown-video/) | Convert markdown slides to MP4 video with TTS narration (with or without Deckset) |
| [video-cleaning](video-cleaning/) | Remove silent pauses from videos using AI-powered transcription and FFmpeg |

### Image Skills

| Skill | Description |
|-------|-------------|
| [gemini-image-skill](gemini-image-skill/) | Generate AI images using Google Gemini API with multiple models and aspect ratios |

## Installation

### For Claude Code

1. Clone this repository or copy the skill folders:
```bash
git clone https://github.com/jykim/claude-obsidian-skills.git
```

2. Copy skills to your Claude Code skills directory:
```bash
cp -r claude-obsidian-skills/*-* ~/.claude/skills/
```

3. Claude Code will automatically detect and use the skills.

### For Other AI Assistants

Copy the `SKILL.md` file from the desired skill folder to your assistant's skill directory. Each skill is self-contained and documented within its SKILL.md file.

### Advanced: Git Submodule Integration

For vault maintainers who want to keep skills in sync with this repository while avoiding duplication:

1. Add as a submodule to your vault:
```bash
git submodule add https://github.com/jykim/claude-obsidian-skills.git path/to/skills/public-skills
```

2. Create symlinks for backward compatibility:
```bash
cd path/to/skills
ln -s public-skills/obsidian-canvas obsidian-canvas
ln -s public-skills/obsidian-links obsidian-links
ln -s public-skills/obsidian-yaml-frontmatter obsidian-yaml-frontmatter
ln -s public-skills/obsidian-markdown-structure obsidian-markdown-structure
ln -s public-skills/obsidian-mermaid obsidian-mermaid
ln -s public-skills/markdown-slides markdown-slides
ln -s public-skills/markdown-video markdown-video
ln -s public-skills/interactive-writing-assistant interactive-writing-assistant
ln -s public-skills/video-cleaning video-cleaning
```

3. Update skills when new versions are released:
```bash
git submodule update --remote
```

**Benefits:**
- Single source of truth - edit in one place
- Version control - pin to specific commits if needed
- Easy updates via git submodule commands

**Note:** When cloning a vault with submodules, use `--recursive`:
```bash
git clone --recursive your-vault-repo
```

## Requirements

Some skills require external dependencies. Install them before using:

| Skill | Requirements |
|-------|--------------|
| markdown-video | FFmpeg, OpenAI API key, Python 3.7+, Pillow |
| video-cleaning | FFmpeg, OpenAI API key, Python 3.7+ |
| gemini-image-skill | Gemini API key, Python 3.7+, google-genai, Pillow |
| markdown-slides | None (markdown only) |
| obsidian-* | None (file operations only) |
| interactive-writing-assistant | None |

### Common Installation Commands

```bash
# FFmpeg (macOS)
brew install ffmpeg

# Python dependencies
pip install Pillow openai google-genai

# Set API keys
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="your-gemini-api-key"
```

## Quick Start

### Validate Wiki Links
```
Use the obsidian-links skill to check and fix broken wiki links in my vault
```

### Standardize Frontmatter
```
Use obsidian-yaml-frontmatter to ensure consistent properties across my notes
```

### Create Mermaid Diagrams
```
Use obsidian-mermaid to create a flowchart for this process
```

### Create Visual Canvas
```
Use obsidian-canvas to create a knowledge map for this topic
```

### Create Presentation
```
Use markdown-slides to convert this document into a Deckset presentation
```

### Generate Video
```
Use markdown-video to create a narrated video from my slides
```

### Clean Video
```
Use video-cleaning to remove silent pauses from this video
```

## Skill Structure

Each skill follows a consistent structure:

```
skill-name/
├── SKILL.md          # Main skill definition and documentation
├── reference/        # Reference materials (optional)
└── examples/         # Usage examples (optional)
```

The `SKILL.md` file contains:
- Skill metadata (name, description, allowed tools)
- When to use the skill
- Core rules and guidelines
- Step-by-step workflows
- Quality checklists

## Contributing

We welcome contributions! Here's how you can help:

1. **Report bugs** - Open an issue describing the problem
2. **Suggest improvements** - Share ideas for enhancing existing skills
3. **Add new skills** - Create skills for other PKM workflows
4. **Improve documentation** - Help clarify usage and examples

### Creating a New Skill

1. Create a folder in the repo root with your skill name
2. Add a `SKILL.md` with:
   - Frontmatter (name, description, allowed-tools, license)
   - Clear "When to Use" section
   - Step-by-step process documentation
   - Quality checklist
3. Test the skill with Claude Code or your preferred assistant
4. Submit a pull request

## Related Projects

- [AI4PKM](https://github.com/jykim/AI4PKM) - Full PKM automation framework
- [AI4PKM Docs](https://jykim.github.io/AI4PKM/) - Documentation and guides
- [Discord Community](https://discord.gg/58cmahcbx3) - Join the discussion

## AI4PKM Framework

These skills are part of the [AI4PKM](https://github.com/jykim/AI4PKM) framework for AI-powered personal knowledge management. For the complete automation system including workflows, templates, and integrations, check out the main project.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with AI assistance for AI assistance.
