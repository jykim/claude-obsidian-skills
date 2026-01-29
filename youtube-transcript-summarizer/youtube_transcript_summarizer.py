#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Transcript Summarizer

Extract transcripts from YouTube videos and generate AI-powered summaries
in any language. Supports batch processing and customizable output.

Usage:
    python youtube_transcript_summarizer.py "VIDEO_URL" [options]
    python youtube_transcript_summarizer.py --batch "urls.txt" [options]

Requirements:
    pip install youtube-transcript-api anthropic

Environment:
    ANTHROPIC_API_KEY: Your Claude API key for summarization
"""

import sys
import io
import os
import re
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

# Windows console UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Language configurations
LANGUAGE_NAMES = {
    'en': 'English',
    'ko': 'Korean',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'auto': 'Auto-detect'
}


class YouTubeTranscriptSummarizer:
    """YouTube video transcript extraction and summarization."""

    def __init__(
        self,
        source_lang: str = 'en',
        target_lang: str = 'ko',
        api_key: Optional[str] = None,
        timeline_interval: int = 5
    ):
        """
        Initialize the summarizer.

        Args:
            source_lang: Source transcript language code
            target_lang: Target summary language code
            api_key: Claude API key (or uses ANTHROPIC_API_KEY env var)
            timeline_interval: Timeline interval in minutes
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.timeline_interval = timeline_interval

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]+)',
            r'(?:youtu\.be\/)([a-zA-Z0-9_-]+)',
            r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]+)',
            r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]+)',
            r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If no pattern matches, assume the input is already a video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        return url

    def get_transcript(self, video_id: str) -> Optional[List[Dict]]:
        """
        Fetch transcript from YouTube.

        Args:
            video_id: YouTube video ID

        Returns:
            List of transcript segments with 'text' and 'start' keys
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            # Determine which language to fetch
            languages_to_try = []

            if self.source_lang == 'auto':
                # Try to get any available transcript
                try:
                    transcript = next(iter(transcript_list))
                    print(f"[*] Auto-detected language: {transcript.language}")
                except StopIteration:
                    print("[X] No transcripts available")
                    return None
            else:
                languages_to_try = [self.source_lang]
                # Add common fallbacks
                if self.source_lang != 'en':
                    languages_to_try.append('en')

                try:
                    transcript = transcript_list.find_transcript(languages_to_try)
                except:
                    print(f"[!] Language '{self.source_lang}' not found. Using first available.")
                    try:
                        transcript = next(iter(transcript_list))
                    except StopIteration:
                        print("[X] No transcripts available")
                        return None

            fetched = transcript.fetch()
            return fetched

        except ImportError:
            print("[X] youtube-transcript-api not installed.")
            print("    Install with: pip install youtube-transcript-api")
            return None
        except Exception as e:
            print(f"[X] Transcript extraction failed: {e}")
            return None

    def format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS or MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def create_timeline(self, transcript: List[Dict]) -> str:
        """Generate timeline summary at configured intervals."""
        timeline = []
        interval_seconds = self.timeline_interval * 60

        current_time = 0
        current_texts = []

        for entry in transcript:
            entry_start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
            entry_text = entry.text if hasattr(entry, 'text') else entry.get('text', '')

            if entry_start >= current_time + interval_seconds:
                if current_texts:
                    timestamp = self.format_timestamp(current_time)
                    preview = ' '.join(current_texts[:50])
                    if len(preview) > 150:
                        preview = preview[:150] + "..."
                    timeline.append(f"- **{timestamp}**: {preview}")
                    current_texts = []
                current_time += interval_seconds

            current_texts.append(entry_text.strip())

        # Add final segment
        if current_texts:
            timestamp = self.format_timestamp(current_time)
            preview = ' '.join(current_texts[:50])
            if len(preview) > 150:
                preview = preview[:150] + "..."
            timeline.append(f"- **{timestamp}**: {preview}")

        return "\n".join(timeline)

    def summarize_with_claude(self, transcript_text: str, video_title: str = "") -> Dict[str, Any]:
        """
        Generate AI summary using Claude API.

        Args:
            transcript_text: Full transcript text
            video_title: Video title for context

        Returns:
            Dictionary with 'summary', 'key_points', and 'sections'
        """
        if not self.api_key:
            print("\n[!] Claude API key not found. Skipping AI summary.")
            return {
                'summary': "To generate AI summaries, set ANTHROPIC_API_KEY environment variable.",
                'key_points': ["No AI summary available"],
                'sections': ""
            }

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)

            # Get target language name
            target_lang_name = LANGUAGE_NAMES.get(self.target_lang, self.target_lang)

            # Build prompt
            prompt = f"""You are analyzing a YouTube video transcript. The video is titled: "{video_title}"

Here is the transcript:
{transcript_text[:15000]}

Please provide a comprehensive analysis in {target_lang_name} with the following structure:

## Summary
(A 2-3 sentence overview of the entire video content)

## Key Points
- (Key insight 1)
- (Key insight 2)
- (Key insight 3)
- (Continue with all important points...)

## Main Content

### Section 1: [Topic Title]
- (Key details)
- (Supporting information)

### Section 2: [Topic Title]
- (Key details)
- (Supporting information)

(Continue with logical sections based on the video structure...)

IMPORTANT: Write everything in {target_lang_name}. Be thorough but concise."""

            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse response
            summary_match = re.search(r'## Summary\n(.+?)(?=\n## |\Z)', result_text, re.DOTALL)
            key_points_match = re.search(r'## Key Points\n(.+?)(?=\n## |\Z)', result_text, re.DOTALL)
            sections_match = re.search(r'## Main Content\n(.+)', result_text, re.DOTALL)

            summary = summary_match.group(1).strip() if summary_match else "Summary not available"

            key_points_text = key_points_match.group(1).strip() if key_points_match else ""
            key_points = [
                line.strip()
                for line in key_points_text.split('\n')
                if line.strip().startswith('-')
            ]

            sections = sections_match.group(1).strip() if sections_match else ""

            return {
                'summary': summary,
                'key_points': key_points if key_points else ["Key points not available"],
                'sections': sections
            }

        except ImportError:
            print("\n[X] anthropic library not installed.")
            print("    Install with: pip install anthropic")
            return {
                'summary': "Install anthropic library for AI summaries.",
                'key_points': ["AI summary unavailable"],
                'sections': ""
            }
        except Exception as e:
            print(f"\n[X] Summary generation failed: {e}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'key_points': ["Summary generation failed"],
                'sections': ""
            }

    def generate_markdown(
        self,
        video_id: str,
        video_url: str,
        video_title: str,
        transcript: List[Dict],
        include_summary: bool = True
    ) -> str:
        """
        Generate structured markdown document.

        Args:
            video_id: YouTube video ID
            video_url: Full YouTube URL
            video_title: Video title
            transcript: Transcript data
            include_summary: Whether to include AI summary

        Returns:
            Formatted markdown string
        """
        # Build full transcript text
        full_text = " ".join([
            entry.text.strip() if hasattr(entry, 'text') else entry.get('text', '').strip()
            for entry in transcript
        ])

        # Generate AI summary if requested
        if include_summary:
            print("\n[*] Generating AI summary...")
            analysis = self.summarize_with_claude(full_text, video_title)
        else:
            analysis = {
                'summary': "(AI summary skipped)",
                'key_points': [],
                'sections': ""
            }

        # Generate timeline
        timeline = self.create_timeline(transcript)

        # Build markdown
        today = datetime.now().strftime("%Y-%m-%d")
        source_lang_name = LANGUAGE_NAMES.get(self.source_lang, self.source_lang)
        target_lang_name = LANGUAGE_NAMES.get(self.target_lang, self.target_lang)

        markdown = f"""# {video_title}

**Original Video**: [{video_url}]({video_url})
**Generated**: {today}
**Video ID**: {video_id}
**Language**: {source_lang_name} -> {target_lang_name}

---

## Summary

{analysis['summary']}

---

## Key Points

"""

        for point in analysis['key_points']:
            markdown += f"{point}\n"

        if analysis['sections']:
            markdown += f"""
---

## Main Content

{analysis['sections']}
"""

        markdown += f"""
---

## Timeline

{timeline}

---

## Full Transcript

"""

        # Add full transcript with timestamps
        for entry in transcript:
            entry_start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
            entry_text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
            timestamp = self.format_timestamp(entry_start)
            markdown += f"**[{timestamp}]** {entry_text.strip()}\n\n"

        markdown += """
---

*Generated by YouTube Transcript Summarizer*
"""

        return markdown

    def process(
        self,
        url: str,
        title: Optional[str] = None,
        output_dir: str = "outputs/summaries",
        include_summary: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Process a single YouTube video.

        Args:
            url: YouTube URL
            title: Custom title (optional)
            output_dir: Output directory
            include_summary: Whether to include AI summary

        Returns:
            Dictionary with 'filepath' and 'content' or None on failure
        """
        video_id = self.extract_video_id(url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title = title or f"YouTube Video {video_id}"

        print(f"\n{'=' * 60}")
        print(f"Processing: {video_title}")
        print(f"Video ID: {video_id}")
        print(f"{'=' * 60}")

        # Fetch transcript
        print("\n[*] Fetching transcript...")
        transcript = self.get_transcript(video_id)

        if not transcript:
            print("\n[X] Could not retrieve transcript.")
            return None

        transcript_list = list(transcript)
        print(f"[OK] Transcript retrieved: {len(transcript_list)} segments")

        # Generate markdown
        print("\n[*] Generating markdown...")
        markdown_content = self.generate_markdown(
            video_id=video_id,
            video_url=video_url,
            video_title=video_title,
            transcript=transcript_list,
            include_summary=include_summary
        )

        # Save file
        os.makedirs(output_dir, exist_ok=True)

        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', video_title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        filename = f"{datetime.now().strftime('%Y%m%d')}_{safe_title}_{video_id}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"\n[OK] Saved: {filepath}")
        print(f"     Size: {len(markdown_content):,} characters")

        return {
            'filepath': filepath,
            'content': markdown_content,
            'video_id': video_id
        }

    def process_batch(
        self,
        urls_file: str,
        output_dir: str = "outputs/summaries",
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Process multiple URLs from a file.

        Args:
            urls_file: Path to file containing URLs (one per line)
            output_dir: Output directory
            include_summary: Whether to include AI summaries

        Returns:
            Summary of processing results
        """
        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'files': [],
            'errors': []
        }

        # Read URLs
        with open(urls_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        urls = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            urls.append(line)

        results['total'] = len(urls)
        print(f"\n{'=' * 60}")
        print(f"Batch Processing: {len(urls)} videos")
        print(f"{'=' * 60}")

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing...")

            try:
                result = self.process(
                    url=url,
                    output_dir=output_dir,
                    include_summary=include_summary
                )

                if result:
                    results['success'] += 1
                    results['files'].append(result['filepath'])
                else:
                    results['failed'] += 1
                    results['errors'].append({'url': url, 'error': 'Transcript not available'})

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
                print(f"[X] Error: {e}")

        # Print summary
        print(f"\n{'=' * 60}")
        print("Batch Processing Complete")
        print(f"{'=' * 60}")
        print(f"Total: {results['total']}")
        print(f"Success: {results['success']}")
        print(f"Failed: {results['failed']}")

        if results['files']:
            print(f"\nGenerated files:")
            for f in results['files']:
                print(f"  - {f}")

        if results['errors']:
            print(f"\nErrors:")
            for err in results['errors']:
                print(f"  - {err['url']}: {err['error']}")

        return results


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="YouTube Transcript Summarizer - Extract and summarize YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single video (default: English -> Korean)
  python youtube_transcript_summarizer.py "https://www.youtube.com/watch?v=VIDEO_ID"

  # Japanese video with English summary
  python youtube_transcript_summarizer.py "VIDEO_URL" --source-lang ja --target-lang en

  # Batch processing
  python youtube_transcript_summarizer.py --batch "urls.txt" --output-dir "summaries"

  # Transcript only (no AI summary)
  python youtube_transcript_summarizer.py "VIDEO_URL" --no-summary
"""
    )

    parser.add_argument(
        'url',
        nargs='?',
        help='YouTube URL or video ID'
    )
    parser.add_argument(
        '--batch',
        metavar='FILE',
        help='Process multiple URLs from a file'
    )
    parser.add_argument(
        '--title',
        help='Custom title for the video'
    )
    parser.add_argument(
        '--source-lang',
        default='en',
        help='Source transcript language (default: en)'
    )
    parser.add_argument(
        '--target-lang',
        default='ko',
        help='Target summary language (default: ko)'
    )
    parser.add_argument(
        '--output-dir',
        default='outputs/summaries',
        help='Output directory (default: outputs/summaries)'
    )
    parser.add_argument(
        '--timeline-interval',
        type=int,
        default=5,
        help='Timeline interval in minutes (default: 5)'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip AI summary (transcript only)'
    )
    parser.add_argument(
        '--api-key',
        help='Claude API key (or set ANTHROPIC_API_KEY env var)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.url and not args.batch:
        parser.print_help()
        print("\n[X] Error: Please provide a YouTube URL or use --batch option")
        sys.exit(1)

    # Initialize summarizer
    summarizer = YouTubeTranscriptSummarizer(
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        api_key=args.api_key,
        timeline_interval=args.timeline_interval
    )

    print("=" * 60)
    print("YouTube Transcript Summarizer")
    print("=" * 60)
    print(f"Source Language: {LANGUAGE_NAMES.get(args.source_lang, args.source_lang)}")
    print(f"Target Language: {LANGUAGE_NAMES.get(args.target_lang, args.target_lang)}")
    print(f"AI Summary: {'No' if args.no_summary else 'Yes'}")

    # Process
    if args.batch:
        summarizer.process_batch(
            urls_file=args.batch,
            output_dir=args.output_dir,
            include_summary=not args.no_summary
        )
    else:
        result = summarizer.process(
            url=args.url,
            title=args.title,
            output_dir=args.output_dir,
            include_summary=not args.no_summary
        )

        if result:
            print(f"\n{'=' * 60}")
            print("[OK] Processing complete!")
            print(f"{'=' * 60}")
        else:
            print(f"\n{'=' * 60}")
            print("[X] Processing failed")
            print(f"{'=' * 60}")
            sys.exit(1)


if __name__ == "__main__":
    main()
