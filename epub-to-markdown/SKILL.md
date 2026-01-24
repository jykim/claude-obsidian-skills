# EPUB to Markdown Skill

Convert EPUB files to well-formatted single markdown files with images extracted.

## Usage

```bash
python3 epub_to_markdown.py "<epub_path>" -o "<output_path>"
```

## Features

- **Metadata extraction**: title, author, language, publisher, publication date
- **TOC parsing**: Extracts table of contents with hierarchy
- **HTML to Markdown**: Converts chapter HTML using html2text
- **Heading preservation**: Maintains H1-H6 hierarchy
- **Image extraction**: Extracts images to `_files_/` folder with book prefix
- **Single file output**: All chapters in one markdown file

## Output Structure

```
output_dir/
├── book.epub           # Original file
├── book.md             # Extracted markdown
└── _files_/            # Images folder
    ├── BookTitle_cover.jpg
    ├── BookTitle_figure1.png
    └── ...
```

## Image Prefix

Images are extracted with a book prefix derived from the title:
- Title: "Die Empty: Unleash Your Best Work Every Day"
- Prefix: `DieEmptyUnleash` (first 3 words, special chars removed)
- Image: `_files_/DieEmptyUnleash_cover.jpg`

This prevents filename collisions when extracting multiple books to the same folder.

## Output Format

```markdown
---
title: {from metadata}
author: {from metadata}
language: {from metadata}
source_file: original.epub
source_type: epub
extracted: YYYY-MM-DD HH:MM:SS
status: extracted
---

# {Book Title}

## Table of Contents
- Chapter 1
- Chapter 2
...

---

## Chapter 1

{content with ![alt](_files_/BookTitle_image.png) links}

---

## Chapter 2

{content}
```

## Dependencies

```bash
pip install ebooklib beautifulsoup4 html2text
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

## Options

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output markdown file path (default: same as epub with .md) |
| `-q`, `--quiet` | Suppress progress messages |

## Limitations

- **DRM-protected EPUBs**: Cannot be extracted (will fail with error)
- **Complex formatting**: May simplify to plain text
- **Large EPUBs**: May take time for books with many chapters/images
