#!/usr/bin/env python3
"""
Clean and polish transcript text in markdown documents.
Removes filler words, improves paragraph structure while preserving timestamps and chapter boundaries.

Usage:
    python clean_transcript.py "merged_document.md"
    python clean_transcript.py "merged_document.md" --dry-run
    python clean_transcript.py "merged_document.md" --backup
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Korean filler words and verbal tics to remove
FILLER_WORDS = [
    r"\b어+\b",           # 어, 어어
    r"\b음+\b",           # 음, 음음
    r"\b아+\b(?!\s*그)",  # 아 (but not "아 그래서")
    r"\b네+\s*네+\b",     # 네네, 네네네
    r"\b그+\s*그+\b",     # 그그, 그그그
    r"\b뭐+\s*뭐+\b",     # 뭐뭐
    r"그니까\s*그니까",   # 그니까 그니까
    r"그래서\s*그래서",   # 그래서 그래서
    r"\b막\b(?=\s+막)",   # 막 막
    r"\b좀\b(?=\s+좀)",   # 좀 좀
    r"\(웃음\)",          # (웃음)
    r"\(박수\)",          # (박수)
]

# Patterns that should be cleaned but content preserved
CLEANUP_PATTERNS = [
    (r"\s+", " "),                    # Multiple spaces to single
    (r"\.{3,}", "..."),               # Multiple periods
    (r"\?{2,}", "?"),                 # Multiple question marks
    (r"!{2,}", "!"),                  # Multiple exclamation marks
    (r"^\s*,\s*", ""),                # Leading comma
    (r",\s*,", ","),                  # Double comma
]

# Sentence ending patterns for paragraph grouping
SENTENCE_ENDINGS = r"[.!?](?:\s|$)"


def remove_filler_words(text: str) -> str:
    """Remove filler words from text."""
    result = text
    for pattern in FILLER_WORDS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return result


def apply_cleanup_patterns(text: str) -> str:
    """Apply cleanup patterns to text."""
    result = text
    for pattern, replacement in CLEANUP_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result.strip()


def clean_paragraph(text: str) -> str:
    """Clean a single paragraph of transcript text."""
    # Remove filler words
    text = remove_filler_words(text)

    # Apply cleanup patterns
    text = apply_cleanup_patterns(text)

    # Ensure proper spacing after punctuation
    text = re.sub(r"([.!?])([가-힣A-Za-z])", r"\1 \2", text)

    return text


def extract_timestamp(line: str) -> Tuple[str, str]:
    """Extract timestamp and content from a line.

    Returns (timestamp, content) or (None, line) if no timestamp found.
    """
    # Match **[HH:MM:SS]** or **[MM:SS]** pattern
    match = re.match(r"(\*\*\[\d{1,2}:\d{2}(?::\d{2})?\]\*\*)\s*(.*)", line)
    if match:
        return match.group(1), match.group(2)
    return None, line


def is_section_header(line: str) -> bool:
    """Check if line is a section header (## or ###)."""
    return line.strip().startswith("#")


def is_metadata(line: str) -> bool:
    """Check if line is metadata or frontmatter."""
    stripped = line.strip()
    return (
        stripped.startswith("---") or
        stripped.startswith("title:") or
        stripped.startswith("created:") or
        stripped.startswith("tags:") or
        stripped.startswith("- ") and not stripped.startswith("- [")  # YAML list but not markdown link
    )


def clean_document(content: str) -> str:
    """Clean entire document while preserving structure."""
    lines = content.split("\n")
    result = []
    in_frontmatter = False
    in_transcript_section = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Handle frontmatter
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                in_frontmatter = False
            result.append(line)
            i += 1
            continue

        if in_frontmatter:
            result.append(line)
            i += 1
            continue

        # Preserve section headers
        if is_section_header(line):
            result.append(line)
            # Check if this is a transcript section
            in_transcript_section = "트랜스크립트" in line or "Transcript" in line
            i += 1
            continue

        # Handle timestamped content
        timestamp, content_text = extract_timestamp(line)
        if timestamp:
            cleaned_content = clean_paragraph(content_text)
            if cleaned_content:  # Only add if there's content after cleaning
                result.append(f"{timestamp} {cleaned_content}")
            i += 1
            continue

        # Clean regular content lines
        if line.strip() and not is_metadata(line):
            cleaned = clean_paragraph(line)
            if cleaned:
                result.append(cleaned)
        else:
            result.append(line)

        i += 1

    return "\n".join(result)


def group_short_paragraphs(content: str) -> str:
    """Group short paragraphs together for better readability.

    Combines consecutive timestamped lines that form incomplete thoughts.
    """
    lines = content.split("\n")
    result = []
    pending_lines = []

    def flush_pending():
        if pending_lines:
            # Combine timestamps and content
            combined = " ".join(pending_lines)
            result.append(combined)
            pending_lines.clear()

    for line in lines:
        timestamp, _ = extract_timestamp(line)

        # If it's a timestamped line and short, consider grouping
        if timestamp and len(line) < 80:
            # Check if this continues a thought
            if pending_lines and not re.search(SENTENCE_ENDINGS, pending_lines[-1]):
                pending_lines.append(line)
                continue

        # Flush any pending lines
        flush_pending()

        # Add current line
        if timestamp and len(line) < 60:
            pending_lines.append(line)
        else:
            result.append(line)

    flush_pending()
    return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(description="Clean transcript text in markdown documents")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("--output", help="Output file (default: overwrite input)")
    parser.add_argument("--backup", action="store_true", help="Create backup before overwriting")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--no-group", action="store_true", help="Don't group short paragraphs")

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    print(f"Reading: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Clean the document
    print("Cleaning transcript...")
    cleaned = clean_document(original_content)

    # Optionally group short paragraphs
    if not args.no_group:
        print("Grouping short paragraphs...")
        cleaned = group_short_paragraphs(cleaned)

    # Show diff stats
    original_lines = len(original_content.split("\n"))
    cleaned_lines = len(cleaned.split("\n"))
    original_chars = len(original_content)
    cleaned_chars = len(cleaned)

    print(f"\nChanges:")
    print(f"  Lines: {original_lines} → {cleaned_lines} ({cleaned_lines - original_lines:+d})")
    print(f"  Characters: {original_chars} → {cleaned_chars} ({cleaned_chars - original_chars:+d})")

    if args.dry_run:
        print("\n[DRY RUN] No files modified.")
        print("\n--- Preview (first 2000 chars) ---")
        print(cleaned[:2000])
        print("...")
        return

    # Determine output path
    output_path = Path(args.output) if args.output else input_path

    # Create backup if requested
    if args.backup and output_path == input_path:
        backup_path = input_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(original_content)
        print(f"\nBackup created: {backup_path}")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
