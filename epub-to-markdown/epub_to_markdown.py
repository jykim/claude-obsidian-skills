#!/usr/bin/env python3
"""
EPUB to Markdown Converter
Converts EPUB files to a single well-formatted markdown file with images.
Designed for integration with EDM (Extract Document to Markdown) workflow.
"""

import sys
import argparse
import re
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import html2text
except ImportError as e:
    print(f"Error: Missing required package. Please install dependencies:")
    print("  pip install ebooklib beautifulsoup4 html2text")
    sys.exit(1)

# Chapters to skip (copyright, title page, etc.)
SKIP_PATTERNS = [
    r'^copyright',
    r'^title\s*page',
    r'^cover',
    r'^also\s+by',
    r'^about\s+the\s+author',
    r'^praise\s+for',
    r'^portfolio\s*/\s*penguin',
    r'^penguin\s+(group|books|random)',
    r'^published\s+by',
    r'^library\s+of\s+congress',
    r'^\d{3,}',  # ISBN-like numbers
    r'^isbn',
    r'^dedication$',
    r'^contents$',
    r'^table\s+of\s+contents',
    r'^acknowledgments?$',
    r'^notes(\s+and)?',
    r'^index$',
    r'^bibliography',
    r'^appendix',
]


class EPUBToMarkdown:
    def __init__(self, epub_path: str, output_path: str = None):
        self.epub_path = Path(epub_path)
        self.output_path = Path(output_path) if output_path else self.epub_path.with_suffix('.md')
        self.output_dir = self.output_path.parent
        self.images_dir = self.output_dir / "_files_"
        self.book = None
        self.image_mapping = {}
        self.h2t = self._setup_html2text()

    def _setup_html2text(self) -> html2text.HTML2Text:
        """Configure HTML2Text converter for clean markdown output."""
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.ignore_images = False
        h2t.ignore_emphasis = False
        h2t.body_width = 0  # Don't wrap lines
        h2t.unicode_snob = True
        h2t.escape_snob = True
        h2t.mark_code = True
        return h2t

    def load(self) -> bool:
        """Load EPUB file."""
        try:
            self.book = epub.read_epub(str(self.epub_path))
            return True
        except Exception as e:
            print(f"Error loading EPUB: {e}", file=sys.stderr)
            return False

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return text
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ').strip()

    def extract_metadata(self) -> dict:
        """Extract book metadata from EPUB."""
        metadata = {}

        # Title
        title = self.book.get_metadata('DC', 'title')
        metadata['title'] = title[0][0] if title else self.epub_path.stem

        # Author(s)
        authors = self.book.get_metadata('DC', 'creator')
        if authors:
            metadata['author'] = [a[0] for a in authors]
        else:
            metadata['author'] = ['Unknown']

        # Language
        language = self.book.get_metadata('DC', 'language')
        metadata['language'] = language[0][0] if language else 'Unknown'

        # Publisher
        publisher = self.book.get_metadata('DC', 'publisher')
        metadata['publisher'] = publisher[0][0] if publisher else None

        # Publication date
        date = self.book.get_metadata('DC', 'date')
        metadata['pub_date'] = date[0][0] if date else None

        # Description - strip HTML tags
        description = self.book.get_metadata('DC', 'description')
        if description:
            metadata['description'] = self._strip_html(description[0][0])
        else:
            metadata['description'] = None

        return metadata

    def extract_toc(self) -> list:
        """Extract table of contents (content chapters only)."""
        toc_items = []

        def process_toc_item(item, level=0):
            if hasattr(item, 'title'):
                title = item.title
                # Skip non-content items
                if not self._is_skip_chapter(title):
                    toc_items.append({'title': title, 'level': level})
            elif isinstance(item, tuple):
                section, sub_items = item
                if hasattr(section, 'title'):
                    title = section.title
                    if not self._is_skip_chapter(title):
                        toc_items.append({'title': title, 'level': level})
                for sub in sub_items:
                    process_toc_item(sub, level + 1)
            elif isinstance(item, list):
                for sub in item:
                    process_toc_item(sub, level)

        for item in self.book.toc:
            process_toc_item(item)

        return toc_items

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename)
        filename = filename.strip()
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def _get_book_prefix(self, title: str) -> str:
        """Generate a book prefix from title (first 3 words, special chars removed)."""
        if not title:
            return "Book"
        # Remove special characters and split into words
        words = re.sub(r'[^\w\s]', '', title).split()[:3]
        return ''.join(words) if words else "Book"

    def extract_images(self, metadata: dict = None) -> dict:
        """Extract all images from EPUB to _files_ folder with book prefix."""
        self.images_dir.mkdir(parents=True, exist_ok=True)
        image_mapping = {}
        image_count = 0

        # Get book prefix from metadata for unique filenames
        book_title = metadata.get('title', '') if metadata else ''
        prefix = self._get_book_prefix(book_title)

        for item in self.book.get_items():
            # Check if item is an image by media type
            if item.media_type in epub.IMAGE_MEDIA_TYPES:
                image_content = item.get_content()
                original_name = item.get_name()
                filename = Path(original_name).name

                safe_filename = self._sanitize_filename(filename)
                if not safe_filename:
                    safe_filename = f"image_{image_count}.png"

                # Add book prefix to filename
                safe_filename = f"{prefix}_{safe_filename}"

                image_path = self.images_dir / safe_filename

                counter = 1
                while image_path.exists():
                    stem = Path(safe_filename).stem
                    suffix = Path(safe_filename).suffix
                    image_path = self.images_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                with open(image_path, 'wb') as f:
                    f.write(image_content)

                local_path = f"_files_/{image_path.name}"
                image_mapping[original_name] = local_path
                image_mapping[filename] = local_path
                image_mapping[Path(original_name).name] = local_path

                image_count += 1

        return image_mapping

    def _is_skip_chapter(self, title: str) -> bool:
        """Check if chapter should be skipped based on title."""
        if not title:
            return False
        title_lower = title.lower().strip()
        for pattern in SKIP_PATTERNS:
            if re.match(pattern, title_lower, re.IGNORECASE):
                return True
        return False

    def _is_frontmatter_content(self, text: str) -> bool:
        """Check if content is frontmatter (copyright, publisher info, TOC, dedication)."""
        if not text:
            return False
        text_lower = text[:500].lower()  # Check first 500 chars

        frontmatter_indicators = [
            'published by the penguin',
            'penguin group',
            'copyright ©',
            'all rights reserved',
            'library of congress',
            'isbn 978',
            'penguin random house',
            'registered offices',
            'without permission',
        ]

        matches = sum(1 for indicator in frontmatter_indicators if indicator in text_lower)
        if matches >= 2:
            return True

        # Also skip if it's a short dedication or TOC-like content
        text_clean = text.strip()
        lines = [l.strip() for l in text_clean.split('\n') if l.strip()]

        # Skip if mostly links (TOC page)
        if len(lines) > 5:
            link_lines = sum(1 for l in lines if l.startswith('#') or l.startswith('-') or len(l) < 30)
            if link_lines / len(lines) > 0.7:
                return True

        # Skip if very short dedication-like text
        if len(text_clean) < 300 and ('for my' in text_lower or 'dedicated to' in text_lower):
            return True

        return False

    def process_html_content(self, html_content: str, image_mapping: dict) -> str:
        """Convert HTML content to markdown with proper image links."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for elem in soup(['script', 'style']):
            elem.decompose()

        # Process images - replace src with local path
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')

            if src:
                src_decoded = urllib.parse.unquote(src)
                local_path = None

                if src_decoded in image_mapping:
                    local_path = image_mapping[src_decoded]
                elif src_decoded.lstrip('../') in image_mapping:
                    local_path = image_mapping[src_decoded.lstrip('../')]
                elif Path(src_decoded).name in image_mapping:
                    local_path = image_mapping[Path(src_decoded).name]

                if local_path:
                    img['src'] = local_path
                else:
                    img.decompose()  # Remove image if not found
                    continue

        # Convert to markdown
        markdown = self.h2t.handle(str(soup))

        # Clean up
        markdown = self._clean_markdown(markdown)

        return markdown

    def _clean_markdown(self, content: str) -> str:
        """Clean up markdown formatting."""
        # Remove excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

        # Remove internal EPUB links like [text](file.xhtml)
        content = re.sub(r'\[([^\]]*)\]\([^)]*\.xhtml[^)]*\)', r'\1', content)

        # Remove empty links
        content = re.sub(r'\[([^\]]*)\]\(\)', r'\1', content)

        # Fix escaped characters
        content = content.replace('\\*', '*')
        content = content.replace('\\_', '_')
        content = content.replace('\\(', '(')
        content = content.replace('\\)', ')')

        # Remove remaining HTML tags that might have slipped through
        content = re.sub(r'<[^>]+>', '', content)

        # Trim whitespace
        content = content.strip()

        return content

    def extract_chapters(self, image_mapping: dict) -> list:
        """Extract content chapters only (skip frontmatter)."""
        chapters = []
        spine_items = [item[0] for item in self.book.spine]

        for item_id in spine_items:
            item = self.book.get_item_with_id(item_id)

            if item is None or item.get_type() != 9:
                continue

            try:
                content = item.get_content().decode('utf-8')
            except Exception:
                continue

            # Extract title first
            soup = BeautifulSoup(content, 'html.parser')
            title_elem = soup.find(['h1', 'h2', 'h3'])
            chapter_title = title_elem.get_text().strip() if title_elem else None

            # Skip chapters based on title
            if chapter_title and self._is_skip_chapter(chapter_title):
                continue

            # Convert to markdown
            markdown_content = self.process_html_content(content, image_mapping)

            # Skip if content is too short
            if len(markdown_content.strip()) < 100:
                continue

            # Skip frontmatter content
            if self._is_frontmatter_content(markdown_content):
                continue

            chapters.append({
                'title': chapter_title,
                'content': markdown_content
            })

        return chapters

    def convert(self, quiet: bool = False) -> str:
        """Convert EPUB to single markdown string with images extracted."""
        if not self.load():
            return None

        # Extract metadata first (needed for image prefix)
        metadata = self.extract_metadata()

        # Extract images with book prefix
        if not quiet:
            print(f"Extracting images...")
        self.image_mapping = self.extract_images(metadata)
        if not quiet and self.image_mapping:
            print(f"  Extracted {len(set(self.image_mapping.values()))} images to {self.images_dir}")

        # Extract remaining components
        toc = self.extract_toc()
        chapters = self.extract_chapters(self.image_mapping)

        if not quiet:
            print(f"  Extracted {len(chapters)} content chapters")

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

        frontmatter_lines.append(f'language: {metadata["language"]}')

        if metadata.get('publisher'):
            frontmatter_lines.append(f'publisher: "{metadata["publisher"]}"')

        if metadata.get('pub_date'):
            frontmatter_lines.append(f'pub_date: "{metadata["pub_date"]}"')

        frontmatter_lines.extend([
            f'source_file: "{self.epub_path.name}"',
            'source_type: epub',
            f'extracted: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'status: extracted',
            '---',
            ''
        ])

        frontmatter = '\n'.join(frontmatter_lines)

        # Build body
        body_parts = []

        # Title
        body_parts.append(f'# {metadata["title"]}')
        body_parts.append('')

        # Description if available (HTML stripped)
        if metadata.get('description'):
            body_parts.append(f'> {metadata["description"]}')
            body_parts.append('')

        # Table of Contents (content only)
        if toc:
            body_parts.append('## Table of Contents')
            body_parts.append('')
            for item in toc:
                indent = '  ' * item['level']
                body_parts.append(f'{indent}- {item["title"]}')
            body_parts.append('')

        # Chapters
        for i, chapter in enumerate(chapters):
            body_parts.append('---')
            body_parts.append('')

            if chapter['title']:
                body_parts.append(f'## {chapter["title"]}')
            else:
                body_parts.append(f'## Chapter {i + 1}')

            body_parts.append('')
            body_parts.append(chapter['content'])
            body_parts.append('')

        body = '\n'.join(body_parts)

        return frontmatter + '\n' + body


def main():
    parser = argparse.ArgumentParser(
        description='Convert EPUB to single Markdown file with images (EDM-compatible)'
    )
    parser.add_argument('epub_file', help='Path to EPUB file')
    parser.add_argument(
        '-o', '--output',
        help='Output markdown file path (default: same as epub with .md extension)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    args = parser.parse_args()

    epub_path = Path(args.epub_file)
    if not epub_path.exists():
        print(f"Error: EPUB file not found: {epub_path}", file=sys.stderr)
        sys.exit(1)

    if epub_path.suffix.lower() != '.epub':
        print(f"Error: File must be an EPUB: {epub_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = epub_path.with_suffix('.md')

    if not args.quiet:
        print(f"Converting: {epub_path.name}")

    converter = EPUBToMarkdown(str(epub_path), str(output_path))
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
