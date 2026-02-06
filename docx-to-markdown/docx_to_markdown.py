#!/usr/bin/env python3
"""
DOCX to Markdown Converter
Converts DOCX files to well-formatted markdown with images.
Designed for integration with EDM (Extract Document to Markdown) workflow.
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Inches
except ImportError as e:
    print(f"Error: Missing required package. Please install dependencies:")
    print("  pip install python-docx")
    sys.exit(1)


class DOCXToMarkdown:
    def __init__(self, docx_path: str, output_path: str = None):
        self.docx_path = Path(docx_path)
        self.output_path = Path(output_path) if output_path else self.docx_path.with_suffix('.md')
        self.output_dir = self.output_path.parent
        self.images_dir = self.output_dir / "_files_"
        self.document = None
        self.image_mapping = {}
        self.image_count = 0

    def load(self) -> bool:
        """Load DOCX file."""
        try:
            self.document = Document(str(self.docx_path))
            return True
        except Exception as e:
            print(f"Error loading DOCX: {e}", file=sys.stderr)
            return False

    def extract_metadata(self) -> dict:
        """Extract document metadata from DOCX."""
        metadata = {}
        core_props = self.document.core_properties

        # Title (fallback to filename)
        metadata['title'] = core_props.title if core_props.title else self.docx_path.stem

        # Author
        if core_props.author:
            metadata['author'] = [core_props.author]
        else:
            metadata['author'] = ['Unknown']

        # Other metadata
        metadata['subject'] = core_props.subject
        metadata['keywords'] = core_props.keywords
        metadata['created'] = core_props.created
        metadata['modified'] = core_props.modified

        return metadata

    def _get_book_prefix(self, title: str) -> str:
        """Generate a book prefix from title (first 3 words, special chars removed)."""
        if not title:
            return "Doc"
        # Remove special characters and split into words
        words = re.sub(r'[^\w\s]', '', title).split()[:3]
        return ''.join(words) if words else "Doc"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename)
        filename = filename.strip()
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def extract_images(self, metadata: dict = None) -> dict:
        """Extract all images from DOCX to _files_ folder with document prefix."""
        self.images_dir.mkdir(parents=True, exist_ok=True)
        image_mapping = {}

        # Get document prefix from metadata for unique filenames
        doc_title = metadata.get('title', '') if metadata else ''
        prefix = self._get_book_prefix(doc_title)

        # Iterate through all relationships to find images
        for rel in self.document.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    image_data = rel.target_part.blob
                    original_name = Path(rel.target_ref).name

                    # Determine file extension from content type
                    content_type = rel.target_part.content_type
                    ext = self._get_extension_from_content_type(content_type, original_name)

                    safe_filename = self._sanitize_filename(original_name)
                    if not safe_filename:
                        safe_filename = f"image_{self.image_count}{ext}"

                    # Add document prefix to filename
                    safe_filename = f"{prefix}_{safe_filename}"

                    image_path = self.images_dir / safe_filename

                    # Handle duplicate filenames
                    counter = 1
                    while image_path.exists():
                        stem = Path(safe_filename).stem
                        suffix = Path(safe_filename).suffix
                        image_path = self.images_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                    with open(image_path, 'wb') as f:
                        f.write(image_data)

                    local_path = f"_files_/{image_path.name}"
                    # Map by relationship id for later reference
                    image_mapping[rel.rId] = local_path
                    image_mapping[original_name] = local_path

                    self.image_count += 1
                except Exception as e:
                    print(f"Warning: Could not extract image {rel.target_ref}: {e}", file=sys.stderr)

        return image_mapping

    def _get_extension_from_content_type(self, content_type: str, fallback_name: str) -> str:
        """Get file extension from content type."""
        type_map = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/webp': '.webp',
        }
        ext = type_map.get(content_type)
        if ext:
            return ext
        # Fallback to original extension
        return Path(fallback_name).suffix or '.png'

    def _process_paragraph(self, paragraph) -> str:
        """Convert a paragraph to markdown."""
        text = paragraph.text.strip()
        if not text:
            return ""

        style_name = paragraph.style.name if paragraph.style else ""

        # Handle headings
        if style_name.startswith('Heading'):
            try:
                level = int(style_name.split()[-1])
                level = min(level, 6)  # Markdown only supports H1-H6
                return '#' * level + ' ' + text
            except (ValueError, IndexError):
                pass

        # Handle title
        if style_name == 'Title':
            return '# ' + text

        # Handle list items
        if style_name.startswith('List'):
            if 'Number' in style_name or 'Ordered' in style_name:
                return '1. ' + text
            else:
                return '- ' + text

        # Handle quotes
        if style_name == 'Quote' or style_name == 'Intense Quote':
            return '> ' + text

        # Regular paragraph with inline formatting
        return self._process_inline_formatting(paragraph)

    def _process_inline_formatting(self, paragraph) -> str:
        """Process inline formatting (bold, italic) in a paragraph."""
        result = []
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue

            if run.bold and run.italic:
                text = f"***{text}***"
            elif run.bold:
                text = f"**{text}**"
            elif run.italic:
                text = f"*{text}*"

            result.append(text)

        return ''.join(result)

    def _process_table(self, table) -> str:
        """Convert a table to markdown format."""
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            rows.append('| ' + ' | '.join(cells) + ' |')

            # Add header separator after first row
            if i == 0:
                rows.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')

        return '\n'.join(rows)

    def convert(self, quiet: bool = False) -> str:
        """Convert DOCX to markdown string with images extracted."""
        if not self.load():
            return None

        # Extract metadata first (needed for image prefix)
        metadata = self.extract_metadata()

        # Extract images with document prefix
        if not quiet:
            print(f"Extracting images...")
        self.image_mapping = self.extract_images(metadata)
        if not quiet and self.image_mapping:
            print(f"  Extracted {len(set(self.image_mapping.values()))} images to {self.images_dir}")

        # Build frontmatter
        frontmatter_lines = [
            '---',
            f'title: "{metadata["title"]}"',
        ]

        if len(metadata['author']) == 1:
            frontmatter_lines.append(f'author: "{metadata["author"][0]}"')
        else:
            frontmatter_lines.append('author:')
            for author in metadata['author']:
                frontmatter_lines.append(f'  - "{author}"')

        if metadata.get('subject'):
            frontmatter_lines.append(f'subject: "{metadata["subject"]}"')

        frontmatter_lines.extend([
            f'source_file: "{self.docx_path.name}"',
            'source_type: docx',
            f'extracted: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'status: extracted',
            '---',
            ''
        ])

        frontmatter = '\n'.join(frontmatter_lines)

        # Process document content
        content_parts = []

        # Add title
        content_parts.append(f'# {metadata["title"]}')
        content_parts.append('')

        for element in self.document.element.body:
            tag = element.tag.split('}')[-1]  # Remove namespace

            if tag == 'p':  # Paragraph
                from docx.text.paragraph import Paragraph
                para = Paragraph(element, self.document)
                markdown = self._process_paragraph(para)
                if markdown:
                    content_parts.append(markdown)
                    content_parts.append('')

            elif tag == 'tbl':  # Table
                from docx.table import Table
                table = Table(element, self.document)
                content_parts.append('')
                content_parts.append(self._process_table(table))
                content_parts.append('')

        # Combine frontmatter and content
        content = '\n'.join(content_parts)

        # Clean up excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)

        if not quiet:
            print(f"  Converted document to markdown")

        return frontmatter + '\n' + content


def main():
    parser = argparse.ArgumentParser(
        description='Convert DOCX to Markdown file with images (EDM-compatible)'
    )
    parser.add_argument('docx_file', help='Path to DOCX file')
    parser.add_argument(
        '-o', '--output',
        help='Output markdown file path (default: same as docx with .md extension)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    args = parser.parse_args()

    docx_path = Path(args.docx_file)
    if not docx_path.exists():
        print(f"Error: DOCX file not found: {docx_path}", file=sys.stderr)
        sys.exit(1)

    if docx_path.suffix.lower() not in ['.docx', '.doc']:
        print(f"Error: File must be a DOCX: {docx_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = docx_path.with_suffix('.md')

    if not args.quiet:
        print(f"Converting: {docx_path.name}")

    converter = DOCXToMarkdown(str(docx_path), str(output_path))
    markdown = converter.convert(quiet=args.quiet)

    if markdown is None:
        print("Error: Conversion failed", file=sys.stderr)
        sys.exit(1)

    output_path.write_text(markdown, encoding='utf-8')

    if not args.quiet:
        print(f"Output: {output_path}")
        if converter.image_mapping:
            print(f"Images: {converter.images_dir}")
        print("Done.")

    sys.exit(0)


if __name__ == '__main__':
    main()
