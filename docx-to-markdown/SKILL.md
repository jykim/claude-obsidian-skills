# DOCX to Markdown Skill

Convert DOCX files to well-formatted markdown files with images extracted.

## Usage

```bash
python3 docx_to_markdown.py "<docx_path>" -o "<output_path>"
```

## Features

- **Metadata extraction**: title, author, subject, keywords
- **Heading preservation**: Maintains H1-H6 hierarchy from Word styles
- **Inline formatting**: Bold, italic conversion
- **List support**: Ordered and unordered lists
- **Table extraction**: Tables converted to markdown format
- **Image extraction**: Extracts images to `_files_/` folder with document prefix

## Output Structure

```
output_dir/
├── document.docx           # Original file
├── document.md             # Extracted markdown
└── _files_/                # Images folder
    ├── DocTitle_image1.png
    ├── DocTitle_figure2.jpg
    └── ...
```

## Image Prefix

Images are extracted with a document prefix derived from the title:
- Title: "Die Empty: Unleash Your Best Work Every Day"
- Prefix: `DieEmptyUnleash` (first 3 words, special chars removed)
- Image: `_files_/DieEmptyUnleash_image1.png`

This prevents filename collisions when extracting multiple documents to the same folder.

## Output Format

```markdown
---
title: {from metadata}
author: {from metadata}
source_file: original.docx
source_type: docx
extracted: YYYY-MM-DD HH:MM:SS
status: extracted
---

# {Document Title}

{content with ![alt](_files_/DocTitle_image.png) links}
```

## Dependencies

```bash
pip install python-docx
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

## Options

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output markdown file path (default: same as docx with .md) |
| `-q`, `--quiet` | Suppress progress messages |

## Limitations

- **Password-protected DOCX**: Cannot be opened (will fail with error)
- **Complex layouts**: May not preserve exact positioning
- **Embedded objects**: Non-image objects may not be extracted
