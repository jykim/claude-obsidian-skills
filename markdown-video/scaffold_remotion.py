#!/usr/bin/env python3
"""
Scaffold Remotion Project from Deckset Markdown

Parses Deckset-format markdown slides, classifies layouts, and generates
a complete Remotion (React) project with typed data files and scene components.

Usage:
    python scaffold_remotion.py "slides.md" --audio-dir "audio" --output-dir "my-video"
    python scaffold_remotion.py "slides.md" --audio-dir "audio" --output-dir "my-video" --project-name "SBCVideo"
    python scaffold_remotion.py "slides.md" --dry-run  # Preview parsing + classification
    python scaffold_remotion.py "slides.md" --force-scenes  # Overwrite existing scene files

Features:
    - Reuses markdown parser from create_slides_gemini.py
    - ffprobe-based audio duration detection
    - Slide classification: title, table, bullets, two_column, numbered_flow, closing
    - Generates slides.ts, slideContent.ts, scene files, scenes/index.ts
    - Copies template + audio files into output project
    - Idempotent: data files always overwritten, scenes skipped unless --force-scenes
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR / "remotion-template"

# Default part colors cycling
DEFAULT_PART_COLORS = [0, 1, 2, 3, 4, 5, 6]


# ---------------------------------------------------------------------------
# Markdown parser (reused from create_slides_gemini.py / generate_audio.py)
# ---------------------------------------------------------------------------

def parse_markdown_slides(md_file: Path) -> List[Dict]:
    """Parse Deckset markdown, return slides with speaker notes only."""
    content = md_file.read_text(encoding="utf-8")

    # Remove frontmatter settings (slidenumbers, theme, etc.)
    content = re.sub(r"^[a-z]+:\s*\S+\s*\n", "", content, flags=re.MULTILINE)

    # Split by --- that is a slide separator (standalone line), NOT inside tables
    # Table separators look like |---|---| or | --- | --- |
    raw_slides = re.split(r"\n---\n(?!\|)", content)
    slides: List[Dict] = []
    output_num = 1

    for idx, slide_content in enumerate(raw_slides):
        slide_content = slide_content.strip()
        if not slide_content:
            continue

        # Speaker notes required
        notes_match = re.search(r"^\^\s*(.+?)$", slide_content, re.MULTILINE | re.DOTALL)
        if not notes_match:
            continue

        speaker_notes = notes_match.group(1).strip()

        # Remove speaker notes from display content
        display_content = re.sub(r"^\^\s*.+?$", "", slide_content, flags=re.MULTILINE).strip()

        # Extract title — prefer ## subtitle over # Part N header
        all_headings = re.findall(r"^(#+)\s*(.+?)$", display_content, re.MULTILINE)
        title = ""
        if all_headings:
            # If first heading looks like a Part label, use the second heading as title
            part_like = re.search(r"Part\s+\d+", all_headings[0][1])
            if part_like and len(all_headings) >= 2:
                title = all_headings[1][1].strip()
            else:
                title = all_headings[0][1].strip()

        # Body without headings
        body_content = re.sub(r"^#+\s*.+?$", "", display_content, flags=re.MULTILINE).strip()

        # Tables
        table_match = re.search(r"(\|.+\|[\s\S]*?\|.+\|)", body_content)
        table = table_match.group(1).strip() if table_match else None

        # Numbered lists (1. or 1️⃣)
        numbered_items = re.findall(
            r"^(?:\d+[.️⃣)]\s*\*{0,2})(.+?)$", body_content, re.MULTILINE
        )

        # Bullet items
        bullet_items = re.findall(r"^[-*]\s+(.+?)$", body_content, re.MULTILINE)

        # Two-column detection: two bold headers with bullet lists
        bold_sections = re.findall(r"\*\*(.+?)\*\*", body_content)

        # Part label detection (# Part N or ## Part N)
        part_match = re.search(r"Part\s+(\d+)", display_content, re.IGNORECASE)
        part_label = f"Part {part_match.group(1)}" if part_match else None

        # Clean bold markers from bullet items
        bullet_items = [re.sub(r"\*\*([^*]+)\*\*", r"\1", b) for b in bullet_items]

        slides.append(
            {
                "num": output_num,
                "original_idx": idx,
                "title": title,
                "body": body_content,
                "table_raw": table,
                "numbered_items": numbered_items,
                "bullet_items": bullet_items,
                "bold_sections": bold_sections,
                "part_label": part_label,
                "speaker_notes": speaker_notes,
            }
        )
        output_num += 1

    return slides


# ---------------------------------------------------------------------------
# Audio duration via ffprobe
# ---------------------------------------------------------------------------

def get_audio_duration(audio_path: Path) -> float:
    """Return duration in seconds using ffprobe. Falls back to 15s."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 15.0


# ---------------------------------------------------------------------------
# Slide classification
# ---------------------------------------------------------------------------

def classify_slide(slide: Dict, idx: int, total: int) -> str:
    """Classify slide layout type."""
    title = slide["title"].lower()
    body = slide["body"]
    table = slide["table_raw"]
    numbered = slide["numbered_items"]
    bullets = slide["bullet_items"]
    bolds = slide["bold_sections"]

    # First slide → title
    if idx == 0:
        return "title"

    # Last slide with closing keywords
    if idx == total - 1:
        closing_keywords = ["논의", "마무리", "감사", "다음 단계", "closing", "discussion", "q&a"]
        if any(kw in title for kw in closing_keywords) or any(kw in body.lower() for kw in closing_keywords):
            return "closing"

    # Two-column: 2+ bold sections with bullets after each
    if len(bolds) >= 2 and len(bullets) >= 2:
        return "two_column"

    # Table
    if table:
        return "table"

    # Numbered flow: numbered list items
    if len(numbered) >= 3:
        return "numbered_flow"

    # Bullets
    if len(bullets) >= 2:
        return "bullets"

    # Fallback
    return "bullets"


# ---------------------------------------------------------------------------
# Parse table into structured data
# ---------------------------------------------------------------------------

def parse_table(table_raw: str) -> Optional[Dict]:
    """Parse markdown table into headers and rows."""
    if not table_raw:
        return None

    lines = [l.strip() for l in table_raw.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return None

    def split_row(line: str) -> List[str]:
        cells = [c.strip() for c in line.split("|")]
        return [c for c in cells if c]  # Remove empty from leading/trailing |

    headers = split_row(lines[0])

    # Skip separator line (|---|---|)
    data_start = 1
    if data_start < len(lines) and re.match(r"^[\s|:-]+$", lines[data_start]):
        data_start = 2

    rows = [split_row(line) for line in lines[data_start:] if line and not re.match(r"^[\s|:-]+$", line)]

    return {"headers": headers, "rows": rows}


# ---------------------------------------------------------------------------
# Parse two-column content
# ---------------------------------------------------------------------------

def parse_two_column(body: str) -> Dict:
    """Parse body into two columns based on bold headers."""
    sections = re.split(r"\*\*(.+?)\*\*", body)
    # sections = ['before', 'Header1', 'content1', 'Header2', 'content2', ...]

    columns = []
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        items = re.findall(r"^[-*]\s+(.+?)$", content, re.MULTILINE)
        items = [re.sub(r"\*\*([^*]+)\*\*", r"\1", item) for item in items]
        columns.append({"title": header, "items": items})

    if len(columns) >= 2:
        return {
            "leftTitle": columns[0]["title"],
            "leftItems": columns[0]["items"],
            "rightTitle": columns[1]["title"],
            "rightItems": columns[1]["items"],
        }
    return {"leftTitle": "", "leftItems": [], "rightTitle": "", "rightItems": []}


# ---------------------------------------------------------------------------
# TypeScript code generation helpers
# ---------------------------------------------------------------------------

def ts_string(s: str) -> str:
    """Escape string for TypeScript single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def ts_string_array(items: List[str], indent: int = 4) -> str:
    """Generate TypeScript string array literal."""
    pad = " " * indent
    lines = [f"{pad}'{ts_string(item)}'," for item in items]
    return "[\n" + "\n".join(lines) + f"\n{' ' * (indent - 2)}]"


def ts_string_array_2d(rows: List[List[str]], indent: int = 6) -> str:
    """Generate 2D string array."""
    pad = " " * indent
    row_strs = []
    for row in rows:
        cells = ", ".join(f"'{ts_string(c)}'" for c in row)
        row_strs.append(f"{pad}[{cells}],")
    return "[\n" + "\n".join(row_strs) + f"\n{' ' * (indent - 2)}]"


# ---------------------------------------------------------------------------
# Generate slides.ts (metadata)
# ---------------------------------------------------------------------------

def generate_slides_ts(slides: List[Dict], audio_durations: Dict[int, float], part_colors: Dict[int, int]) -> str:
    """Generate src/data/slides.ts content."""
    lines = [
        "export interface SlideData {",
        "  id: number;",
        "  audio: string;       // public/slide_N.mp3",
        "  durationSec: number; // from audio length",
        "  partColor: number;   // index into theme.colors.parts",
        "  title: string;",
        "}",
        "",
        "export const slides: SlideData[] = [",
    ]

    for s in slides:
        sid = s["num"]
        audio_file = f"slide_{sid - 1}.mp3"
        duration = int(round(audio_durations.get(sid, 15.0)))
        pc = part_colors.get(sid, (sid - 1) % len(DEFAULT_PART_COLORS))
        title = ts_string(s["title"])
        padding = " " * max(0, 4 - len(str(sid)))
        lines.append(
            f"  {{ id: {sid},{padding}audio: '{audio_file}', durationSec: {duration}, partColor: {pc}, title: '{title}' }},"
        )

    lines.append("];")
    lines.append("")
    lines.append("export const totalDurationSec = slides.reduce((sum, s) => sum + s.durationSec, 0);")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generate slideContent.ts (structured content)
# ---------------------------------------------------------------------------

def generate_slide_content_ts(slides: List[Dict], classifications: Dict[int, str]) -> str:
    """Generate src/data/slideContent.ts content."""
    parts: List[str] = []

    for s in slides:
        sid = s["num"]
        layout = classifications[sid]
        var_name = f"slide{sid:02d}"
        title = ts_string(s["title"])

        if layout == "title":
            # Title slide: title + subtitle (from body or part label)
            subtitle = ""
            body_lines = [l.strip() for l in s["body"].split("\n") if l.strip()]
            # Look for subtitle (## line was already parsed into title, check remaining)
            for line in body_lines:
                clean = re.sub(r"^#+\s*", "", line).strip()
                if clean and not clean.startswith("|") and not clean.startswith("-"):
                    subtitle = clean
                    break
            parts.append(
                f"// Slide {sid:02d} - Title\n"
                f"export const {var_name} = {{\n"
                f"  title: '{title}',\n"
                f"  subtitle: '{ts_string(subtitle)}',\n"
                f"}};"
            )

        elif layout == "table":
            table_data = parse_table(s["table_raw"])
            if table_data:
                headers_ts = ", ".join(f"'{ts_string(h)}'" for h in table_data["headers"])
                rows_ts = ts_string_array_2d(table_data["rows"])
                part_label = f"  partLabel: '{ts_string(s['part_label'])}',\n" if s["part_label"] else ""
                parts.append(
                    f"// Slide {sid:02d} - {title}\n"
                    f"export const {var_name} = {{\n"
                    f"  title: '{title}',\n"
                    f"{part_label}"
                    f"  table: {{\n"
                    f"    headers: [{headers_ts}],\n"
                    f"    rows: {rows_ts},\n"
                    f"  }},\n"
                    f"}};"
                )
            else:
                # Fallback to bullets
                items = s["bullet_items"] or [s["body"][:80]]
                items_ts = ts_string_array(items)
                parts.append(
                    f"// Slide {sid:02d} - {title}\n"
                    f"export const {var_name} = {{\n"
                    f"  title: '{title}',\n"
                    f"  items: {items_ts},\n"
                    f"}};"
                )

        elif layout == "two_column":
            col_data = parse_two_column(s["body"])
            left_items = ts_string_array(col_data["leftItems"])
            right_items = ts_string_array(col_data["rightItems"])
            part_label = f"  partLabel: '{ts_string(s['part_label'])}',\n" if s["part_label"] else ""
            parts.append(
                f"// Slide {sid:02d} - {title}\n"
                f"export const {var_name} = {{\n"
                f"  title: '{title}',\n"
                f"{part_label}"
                f"  leftTitle: '{ts_string(col_data['leftTitle'])}',\n"
                f"  leftItems: {left_items},\n"
                f"  rightTitle: '{ts_string(col_data['rightTitle'])}',\n"
                f"  rightItems: {right_items},\n"
                f"}};"
            )

        elif layout == "numbered_flow":
            steps = s["numbered_items"]
            steps = [re.sub(r"^\*\*(.+?)\*\*:?\s*", r"\1: ", step).strip() for step in steps]
            steps_ts = ts_string_array(steps)
            part_label = f"  partLabel: '{ts_string(s['part_label'])}',\n" if s["part_label"] else ""
            parts.append(
                f"// Slide {sid:02d} - {title}\n"
                f"export const {var_name} = {{\n"
                f"  title: '{title}',\n"
                f"{part_label}"
                f"  steps: {steps_ts},\n"
                f"}};"
            )

        elif layout == "closing":
            items = s["bullet_items"] or s["numbered_items"] or []
            items_ts = ts_string_array(items)
            # Find closing text
            closing = ""
            body_lines = s["body"].split("\n")
            for line in reversed(body_lines):
                line = line.strip()
                if line and not line.startswith("-") and not line.startswith("*") and not line.startswith("|"):
                    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
                    if clean:
                        closing = clean
                        break
            parts.append(
                f"// Slide {sid:02d} - {title}\n"
                f"export const {var_name} = {{\n"
                f"  title: '{title}',\n"
                f"  items: {items_ts},\n"
                f"  closing: '{ts_string(closing)}',\n"
                f"}};"
            )

        else:  # bullets (default)
            items = s["bullet_items"] or [s["body"][:80]] if s["body"] else [""]
            items_ts = ts_string_array(items)
            part_label = f"  partLabel: '{ts_string(s['part_label'])}',\n" if s["part_label"] else ""
            # Check for footnote-like content (last non-bullet line)
            footnote = ""
            body_lines = s["body"].split("\n")
            for line in reversed(body_lines):
                line = line.strip()
                if line and not line.startswith("-") and not line.startswith("*") and not line.startswith("|"):
                    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
                    if clean and len(clean) < 120:
                        footnote = clean
                        break
            footnote_line = f"  footnote: '{ts_string(footnote)}',\n" if footnote else ""
            parts.append(
                f"// Slide {sid:02d} - {title}\n"
                f"export const {var_name} = {{\n"
                f"  title: '{title}',\n"
                f"{part_label}"
                f"  items: {items_ts},\n"
                f"{footnote_line}"
                f"}};"
            )

    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Generate scene files
# ---------------------------------------------------------------------------

def scene_name(slide_num: int, title: str) -> str:
    """Generate scene component name like Slide01Title."""
    # Strip emoji and non-ASCII, keep only ASCII alphanumeric
    ascii_title = re.sub(r"[^\x20-\x7E]", " ", title).strip()
    # CamelCase from words
    words = re.findall(r"[A-Za-z0-9]+", ascii_title)
    suffix = "".join(w.capitalize() for w in words[:3])
    if not suffix:
        suffix = "Scene"
    return f"Slide{slide_num:02d}{suffix}"


def generate_scene_file(slide_num: int, layout: str, comp_name: str) -> str:
    """Generate a React scene component file."""
    var_name = f"slide{slide_num:02d}"

    if layout == "title":
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ interpolate, useCurrentFrame }} from 'remotion';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const frame = useCurrentFrame();
              const delay = theme.animation.slideDelay;
              const fadeIn = theme.animation.fadeIn;

              const titleOpacity = interpolate(frame, [delay, delay + fadeIn * 2], [0, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});
              const titleScale = interpolate(frame, [delay, delay + fadeIn * 2], [0.9, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});
              const subDelay = delay + 20;
              const subOpacity = interpolate(frame, [subDelay, subDelay + fadeIn], [0, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center' }}}}>
                    <div style={{{{ opacity: titleOpacity, transform: `scale(${{titleScale}})` }}}}>
                      <h1 style={{{{ fontSize: 80, fontWeight: 700, color: theme.colors.text, margin: 0, lineHeight: 1.2 }}}}>
                        {{{var_name}.title}}
                      </h1>
                      <div style={{{{ width: 120, height: 4, backgroundColor: partColor, margin: '24px auto', borderRadius: 2 }}}} />
                    </div>
                    <p style={{{{ opacity: subOpacity, fontSize: 44, color: theme.colors.textMuted, margin: 0, marginTop: 8 }}}}>
                      {{{var_name}.subtitle}}
                    </p>
                  </div>
                </SlideFrame>
              );
            }};
        """)

    elif layout == "table":
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ SlideHeader }} from '../components/SlideHeader';
            import {{ ComparisonTable }} from '../components/ComparisonTable';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
                    <SlideHeader
                      title={{{var_name}.title}}
                      subtitle={{({var_name} as any).partLabel}}
                      color={{partColor}}
                    />
                    <div style={{{{ flex: 1, display: 'flex', alignItems: 'center' }}}}>
                      <ComparisonTable
                        headers={{{var_name}.table.headers}}
                        rows={{{var_name}.table.rows}}
                        fontSize={{theme.font.body}}
                      />
                    </div>
                  </div>
                </SlideFrame>
              );
            }};
        """)

    elif layout == "two_column":
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ interpolate, useCurrentFrame }} from 'remotion';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ SlideHeader }} from '../components/SlideHeader';
            import {{ BulletList }} from '../components/BulletList';
            import {{ TwoColumn }} from '../components/TwoColumn';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const frame = useCurrentFrame();
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;
              const labelDelay = theme.animation.slideDelay + 15;
              const labelOpacity = interpolate(frame, [labelDelay, labelDelay + theme.animation.fadeIn], [0, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});
              const label2Delay = labelDelay + 40;
              const label2Opacity = interpolate(frame, [label2Delay, label2Delay + theme.animation.fadeIn], [0, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
                    <SlideHeader
                      title={{{var_name}.title}}
                      subtitle={{({var_name} as any).partLabel}}
                      color={{partColor}}
                    />
                    <TwoColumn
                      left={{
                        <div>
                          <h3 style={{{{ opacity: labelOpacity, fontSize: theme.font.subtitle, fontWeight: 700, color: theme.colors.accent, margin: '0 0 24px 0' }}}}>
                            {{{var_name}.leftTitle}}
                          </h3>
                          <BulletList items={{{var_name}.leftItems}} delay={{labelDelay + 10}} color={{partColor}} />
                        </div>
                      }}
                      right={{
                        <div>
                          <h3 style={{{{ opacity: label2Opacity, fontSize: theme.font.subtitle, fontWeight: 700, color: theme.colors.accent, margin: '0 0 24px 0' }}}}>
                            {{{var_name}.rightTitle}}
                          </h3>
                          <BulletList items={{{var_name}.rightItems}} delay={{label2Delay + 10}} color={{partColor}} />
                        </div>
                      }}
                      ratio={{0.55}}
                    />
                  </div>
                </SlideFrame>
              );
            }};
        """)

    elif layout == "numbered_flow":
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ SlideHeader }} from '../components/SlideHeader';
            import {{ NumberedFlow }} from '../components/NumberedFlow';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
                    <SlideHeader
                      title={{{var_name}.title}}
                      subtitle={{({var_name} as any).partLabel}}
                      color={{partColor}}
                    />
                    <div style={{{{ flex: 1, display: 'flex', alignItems: 'center' }}}}>
                      <NumberedFlow steps={{{var_name}.steps}} color={{partColor}} />
                    </div>
                  </div>
                </SlideFrame>
              );
            }};
        """)

    elif layout == "closing":
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ interpolate, useCurrentFrame }} from 'remotion';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ SlideHeader }} from '../components/SlideHeader';
            import {{ BulletList }} from '../components/BulletList';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const frame = useCurrentFrame();
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;
              const closingDelay = theme.animation.slideDelay + 60;
              const closingOpacity = interpolate(frame, [closingDelay, closingDelay + theme.animation.fadeIn * 2], [0, 1], {{
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }});

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
                    <SlideHeader title={{{var_name}.title}} color={{partColor}} />
                    <BulletList items={{{var_name}.items}} color={{partColor}} />
                    <div style={{{{ marginTop: 'auto', textAlign: 'center', opacity: closingOpacity }}}}>
                      <p style={{{{ fontSize: theme.font.subtitle, color: theme.colors.accent, fontWeight: 700 }}}}>
                        {{{var_name}.closing}}
                      </p>
                    </div>
                  </div>
                </SlideFrame>
              );
            }};
        """)

    else:  # bullets
        return textwrap.dedent(f"""\
            import React from 'react';
            import {{ SlideFrame }} from '../components/SlideFrame';
            import {{ SlideHeader }} from '../components/SlideHeader';
            import {{ BulletList }} from '../components/BulletList';
            import {{ theme }} from '../styles/theme';
            import {{ {var_name} }} from '../data/slideContent';
            import type {{ SlideData }} from '../data/slides';

            export const {comp_name}: React.FC<{{ slide: SlideData }}> = ({{ slide }}) => {{
              const partColor = theme.colors.parts[slide.partColor] || theme.colors.accent;

              return (
                <SlideFrame audio={{slide.audio}} partColor={{slide.partColor}}>
                  <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
                    <SlideHeader
                      title={{{var_name}.title}}
                      subtitle={{({var_name} as any).partLabel}}
                      color={{partColor}}
                    />
                    <div style={{{{ flex: 1, display: 'flex', alignItems: 'center' }}}}>
                      <BulletList items={{{var_name}.items}} color={{partColor}} />
                    </div>
                  </div>
                </SlideFrame>
              );
            }};
        """)


def generate_scenes_index(scene_entries: List[Tuple[int, str]]) -> str:
    """Generate src/scenes/index.ts barrel export."""
    lines = ["import React from 'react';"]

    for sid, comp in scene_entries:
        lines.append(f"import {{ {comp} }} from './{comp}';")

    lines.append("import type { SlideData } from '../data/slides';")
    lines.append("")
    lines.append("export const sceneMap: Record<number, React.FC<{ slide: SlideData }>> = {")

    for sid, comp in scene_entries:
        lines.append(f"  {sid}: {comp},")

    lines.append("};")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Assign part colors based on Part N labels
# ---------------------------------------------------------------------------

def assign_part_colors(slides: List[Dict]) -> Dict[int, int]:
    """Assign partColor index to each slide based on Part labels."""
    colors: Dict[int, int] = {}
    current_part = 0

    for s in slides:
        if s["part_label"]:
            # Extract part number(s)
            parts = re.findall(r"\d+", s["part_label"])
            if parts:
                current_part = int(parts[0])
        colors[s["num"]] = current_part % len(DEFAULT_PART_COLORS)

    return colors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a Remotion project from Deckset markdown slides",
        epilog="Generates a complete React/Remotion project with typed data and scene components.",
    )
    parser.add_argument("markdown_file", type=Path, help="Deckset markdown file with speaker notes")
    parser.add_argument("--audio-dir", type=Path, default=Path("audio"), help="Directory with slide_N.mp3 files")
    parser.add_argument("--output-dir", type=Path, default=Path("remotion-video"), help="Output project directory")
    parser.add_argument("--project-name", type=str, default=None, help="Composition ID (default: derived from markdown filename)")
    parser.add_argument("--force-scenes", action="store_true", help="Overwrite existing scene files")
    parser.add_argument("--dry-run", action="store_true", help="Preview parsing and classification without generating")
    parser.add_argument("--skip-npm", action="store_true", help="Skip npm install step")

    args = parser.parse_args()

    # Validate inputs
    if not args.markdown_file.exists():
        print(f"Error: File not found: {args.markdown_file}", file=sys.stderr)
        sys.exit(1)

    if not TEMPLATE_DIR.exists():
        print(f"Error: Template directory not found: {TEMPLATE_DIR}", file=sys.stderr)
        sys.exit(1)

    # Derive project name
    if not args.project_name:
        stem = args.markdown_file.stem
        # Remove common suffixes
        for suffix in [" - slides", "-slides", "_slides"]:
            stem = stem.replace(suffix, "")
        # CamelCase
        args.project_name = re.sub(r"[^\w]", "", stem.title().replace(" ", ""))
        if not args.project_name:
            args.project_name = "SlidesVideo"

    print("Scaffold Remotion Project")
    print("=" * 60)
    print(f"Input:       {args.markdown_file}")
    print(f"Audio:       {args.audio_dir}")
    print(f"Output:      {args.output_dir}")
    print(f"Composition: {args.project_name}")
    print()

    # Parse markdown
    print("Parsing markdown...")
    slides = parse_markdown_slides(args.markdown_file)
    total = len(slides)
    print(f"Found {total} slides with speaker notes")

    if total == 0:
        print("Error: No slides with speaker notes found", file=sys.stderr)
        sys.exit(1)

    # Classify slides
    print("\nClassifying slides:")
    classifications: Dict[int, str] = {}
    for i, s in enumerate(slides):
        layout = classify_slide(s, i, total)
        classifications[s["num"]] = layout
        print(f"  [{s['num']:02d}] {layout:15s} | {s['title'][:50]}")

    # Get audio durations
    print("\nReading audio durations...")
    audio_durations: Dict[int, float] = {}
    for s in slides:
        audio_file = args.audio_dir / f"slide_{s['num'] - 1}.mp3"
        if audio_file.exists():
            dur = get_audio_duration(audio_file)
            audio_durations[s["num"]] = dur
            print(f"  slide_{s['num'] - 1}.mp3 → {dur:.1f}s")
        else:
            audio_durations[s["num"]] = 15.0
            print(f"  slide_{s['num'] - 1}.mp3 → NOT FOUND (default 15s)")

    # Assign part colors
    part_colors = assign_part_colors(slides)

    if args.dry_run:
        print("\n--- DRY RUN: No files generated ---")
        print("\nslides.ts preview:")
        print(generate_slides_ts(slides, audio_durations, part_colors)[:500] + "...")
        print("\nScene files that would be created:")
        for s in slides:
            name = scene_name(s["num"], s["title"])
            print(f"  src/scenes/{name}.tsx")
        return

    # --- Generate project ---
    output = args.output_dir
    src = output / "src"

    # Step 1: Copy template (if not already initialized)
    if not (output / "package.json").exists():
        print(f"\nCopying template to {output}...")
        shutil.copytree(TEMPLATE_DIR, output, dirs_exist_ok=True)
    else:
        # Ensure components/styles are up to date
        for subdir in ["components", "styles"]:
            src_sub = TEMPLATE_DIR / "src" / subdir
            dst_sub = src / subdir
            if src_sub.exists():
                shutil.copytree(src_sub, dst_sub, dirs_exist_ok=True)
        # Copy Video.tsx and Root.tsx template
        for fname in ["Video.tsx", "index.ts"]:
            shutil.copy2(TEMPLATE_DIR / "src" / fname, src / fname)

    # Step 2: Replace composition ID placeholders
    for fpath in [output / "package.json", src / "Root.tsx"]:
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            content = content.replace("__COMPOSITION_ID__", args.project_name)
            fpath.write_text(content, encoding="utf-8")

    # Step 3: Create data directory and files (always overwrite)
    data_dir = src / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    slides_ts = generate_slides_ts(slides, audio_durations, part_colors)
    (data_dir / "slides.ts").write_text(slides_ts, encoding="utf-8")
    print(f"  Generated: src/data/slides.ts")

    content_ts = generate_slide_content_ts(slides, classifications)
    (data_dir / "slideContent.ts").write_text(content_ts, encoding="utf-8")
    print(f"  Generated: src/data/slideContent.ts")

    # Step 4: Generate scene files
    scenes_dir = src / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    scene_entries: List[Tuple[int, str]] = []
    created_scenes = 0
    skipped_scenes = 0

    for s in slides:
        sid = s["num"]
        layout = classifications[sid]
        comp = scene_name(sid, s["title"])
        scene_entries.append((sid, comp))

        scene_file = scenes_dir / f"{comp}.tsx"
        if scene_file.exists() and not args.force_scenes:
            skipped_scenes += 1
            continue

        scene_content = generate_scene_file(sid, layout, comp)
        scene_file.write_text(scene_content, encoding="utf-8")
        created_scenes += 1

    # Generate scenes/index.ts (always overwrite)
    index_content = generate_scenes_index(scene_entries)
    (scenes_dir / "index.ts").write_text(index_content, encoding="utf-8")

    print(f"  Generated: src/scenes/index.ts")
    print(f"  Created {created_scenes} scene files, skipped {skipped_scenes} existing")

    # Step 5: Copy audio files to public/
    public_dir = output / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    copied_audio = 0
    for s in slides:
        audio_src = args.audio_dir / f"slide_{s['num'] - 1}.mp3"
        audio_dst = public_dir / f"slide_{s['num'] - 1}.mp3"
        if audio_src.exists():
            shutil.copy2(audio_src, audio_dst)
            copied_audio += 1

    print(f"  Copied {copied_audio} audio files to public/")

    # Step 6: npm install (optional)
    if not args.skip_npm and not (output / "node_modules").exists():
        print("\nRunning npm install...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=str(output),
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            print("  npm install complete")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: npm install failed: {e.stderr[:200]}", file=sys.stderr)
        except FileNotFoundError:
            print("  Warning: npm not found, skipping install", file=sys.stderr)

    # Summary
    print()
    print("=" * 60)
    print("Scaffold complete!")
    print(f"  Project:      {output}")
    print(f"  Composition:  {args.project_name}")
    print(f"  Slides:       {total}")
    print(f"  Scenes:       {created_scenes} created, {skipped_scenes} preserved")
    print()
    print("Next steps:")
    print(f"  cd {output}")
    print(f"  npx remotion studio        # Preview")
    print(f"  npx remotion render src/index.ts {args.project_name} out/video.mp4  # Render")


if __name__ == "__main__":
    main()
