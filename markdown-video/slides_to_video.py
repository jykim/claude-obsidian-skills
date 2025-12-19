#!/usr/bin/env python3
"""
Slides to Video Converter

Converts slide images and audio narration into a presentation video.
Supports flexible naming conventions and automatic slide-audio matching.

Usage:
    # Basic usage - auto-detect slides and audio in current directory
    python slides_to_video.py

    # Specify directories and output
    python slides_to_video.py --slides-dir ./slides --audio-dir ./audio --output presentation.mp4

    # Crop composite images (remove notes from bottom half)
    python slides_to_video.py --slides-dir ./slides --audio-dir ./audio --crop-bottom 720 --output presentation.mp4

    # Dry run - show what would be created
    python slides_to_video.py --slides-dir ./slides --dry-run

Features:
    - Auto-detects slide images (jpg, jpeg, png, pdf)
    - Matches slides with audio files (mp3, wav, m4a) using 0-indexed mapping
    - Strict audio matching (slide N.jpeg → slide_{N-1}.mp3)
    - Crop support for composite images (slide+notes layout)
    - Creates 1080p video with proper audio sync
    - Progress bar and duration estimates
    - Silent segments for slides without audio
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
import shutil


class ProgressBar:
    """Simple progress bar for terminal"""

    def __init__(self, total: int, prefix: str = ''):
        self.total = total
        self.current = 0
        self.prefix = prefix

    def update(self, n: int = 1):
        """Update progress by n steps"""
        self.current += n
        self._print()

    def _print(self):
        """Print progress bar"""
        percent = 100 * (self.current / self.total)
        bar_length = 40
        filled = int(bar_length * self.current / self.total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f'\r{self.prefix} |{bar}| {self.current}/{self.total} ({percent:.1f}%)', end='', flush=True)

    def finish(self):
        """Complete the progress bar"""
        self.current = self.total
        self._print()
        print()


def check_dependencies():
    """Check if required tools are installed"""
    missing = []

    # Check ffmpeg
    if not shutil.which('ffmpeg'):
        missing.append('ffmpeg')

    # Check ffprobe
    if not shutil.which('ffprobe'):
        missing.append('ffprobe')

    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        print("\nInstall with:")
        if sys.platform == 'darwin':
            print("  brew install ffmpeg")
        elif sys.platform.startswith('linux'):
            print("  sudo apt-get install ffmpeg  # Ubuntu/Debian")
            print("  sudo yum install ffmpeg      # CentOS/RHEL")
        sys.exit(1)


def find_slide_images(slides_dir: Path) -> List[Path]:
    """
    Find and sort slide images in directory.

    Supports naming conventions:
    - Numbered: 1.jpg, 2.jpg, 3.jpg
    - Slide prefix: slide_1.jpg, slide_2.jpg
    - Zero-padded: 001.jpg, 002.jpg
    """
    # Supported image formats
    patterns = ['*.jpg', '*.jpeg', '*.png', '*.pdf']

    images = []
    for pattern in patterns:
        images.extend(slides_dir.glob(pattern))

    if not images:
        return []

    # Extract numbers from filenames for sorting
    def extract_number(path: Path) -> int:
        # Try to find a number in the filename
        match = re.search(r'(\d+)', path.stem)
        return int(match.group(1)) if match else 0

    # Sort by extracted number
    images.sort(key=extract_number)

    return images


def find_audio_file(slide_num: int, audio_dir: Path, total_slides: int, strict: bool = False) -> Optional[Path]:
    """
    Find matching audio file for a slide number.

    Tries multiple naming conventions:
    - slide_0.mp3, slide_1.mp3 (0-indexed) - PRIMARY
    - slide_1.mp3, slide_2.mp3 (1-indexed)
    - 1.mp3, 2.mp3
    - 001.mp3, 002.mp3

    Args:
        slide_num: Slide number (1-indexed)
        audio_dir: Directory containing audio files
        total_slides: Total number of slides
        strict: If True, only try 0-indexed pattern (slide_N-1.mp3)
    """
    # Supported audio formats
    extensions = ['.mp3', '.wav', '.m4a', '.aac']

    if strict:
        # Only try the primary 0-indexed pattern
        patterns = [f"slide_{slide_num - 1}"]
    else:
        # Try different naming patterns
        patterns = [
            f"slide_{slide_num - 1}",  # 0-indexed (slide_0, slide_1, ...) - PREFERRED
            f"slide_{slide_num}",       # 1-indexed (slide_1, slide_2, ...)
            f"{slide_num}",             # Simple number (1, 2, 3, ...)
            f"{slide_num:03d}",         # Zero-padded (001, 002, 003, ...)
            f"audio_{slide_num}",       # audio_1, audio_2, ...
            f"narration_{slide_num}",   # narration_1, narration_2, ...
        ]

    for pattern in patterns:
        for ext in extensions:
            audio_file = audio_dir / f"{pattern}{ext}"
            if audio_file.exists():
                return audio_file

    return None


def get_audio_duration(audio_file: Path) -> float:
    """Get audio duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(audio_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception as e:
        print(f"\n⚠️  Warning: Could not get duration for {audio_file.name}: {e}")
        return 5.0  # Default fallback duration


def create_video_segment(
    image: Path,
    audio: Optional[Path],
    duration: float,
    output: Path,
    resolution: str = "1920:1080",
    crop_bottom: int = 0
) -> bool:
    """Create a single video segment from image and audio

    Args:
        image: Path to slide image
        audio: Optional path to audio file
        duration: Duration in seconds
        output: Output video file path
        resolution: Output resolution (WIDTHxHEIGHT)
        crop_bottom: Remove bottom N pixels from image (default: 0)
    """

    # Build video filter chain
    vf_filters = []

    # Add crop filter if specified
    if crop_bottom > 0:
        vf_filters.append(f"crop=iw:ih-{crop_bottom}:0:0")

    # Add scale and pad filters
    vf_filters.append(f"scale={resolution}:force_original_aspect_ratio=decrease")
    vf_filters.append(f"pad={resolution}:(ow-iw)/2:(oh-ih)/2")

    # Combine filters with commas
    vf_string = ','.join(vf_filters)

    if audio:
        # With audio
        # IMPORTANT: -t must come BEFORE -i for looped image to limit loop duration
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-t', str(duration),
            '-i', str(image),
            '-i', str(audio),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', vf_string,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map', '0:v',
            '-map', '1:a',
            '-y',
            str(output)
        ]
    else:
        # Without audio - create silent video
        # IMPORTANT: -t must come BEFORE -i for looped image to limit loop duration
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-t', str(duration),
            '-i', str(image),
            '-f', 'lavfi',
            '-t', str(duration),
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', vf_string,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map', '0:v',
            '-map', '1:a',
            '-y',
            str(output)
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def concatenate_segments(segment_files: List[Path], output_file: Path) -> bool:
    """Concatenate video segments into final video using filter_complex.

    Uses filter_complex concat instead of -f concat -c copy to ensure
    proper audio/video synchronization across all segments.
    """

    # Build inputs array
    inputs = []
    for seg_file in segment_files:
        inputs.extend(['-i', str(seg_file)])

    # Build filter_complex string: [0:v][0:a][1:v][1:a]...concat=n=N:v=1:a=1[vout][aout]
    filter_parts = []
    for i in range(len(segment_files)):
        filter_parts.append(f"[{i}:v][{i}:a]")
    filter_string = ''.join(filter_parts) + f"concat=n={len(segment_files)}:v=1:a=1[vout][aout]"

    cmd = [
        'ffmpeg', '-y',
        *inputs,
        '-filter_complex', filter_string,
        '-map', '[vout]',
        '-map', '[aout]',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '192k',
        str(output_file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n⚠️  ffmpeg error: {result.stderr[:500]}")

    return result.returncode == 0


def format_duration(seconds: float) -> str:
    """Format duration as MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(
        description='Convert slide images and audio to presentation video',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--slides-dir',
        type=Path,
        help='Directory containing slide images (default: current directory)'
    )

    parser.add_argument(
        '--audio-dir',
        type=Path,
        help='Directory containing audio files (default: ./audio or same as slides-dir)'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output video file (default: presentation.mp4)'
    )

    parser.add_argument(
        '--resolution',
        default='1920:1080',
        help='Video resolution as WIDTHxHEIGHT (default: 1920:1080)'
    )

    parser.add_argument(
        '--default-duration',
        type=float,
        default=5.0,
        help='Default duration for slides without audio (default: 5.0 seconds)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without creating it'
    )

    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary segment files'
    )

    parser.add_argument(
        '--crop-bottom',
        type=int,
        default=0,
        help='Remove bottom N pixels from each image. Use 720 for 1280x1440 composite images with notes (default: 0)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Limit to first N slides (default: 0 = all slides)'
    )

    args = parser.parse_args()

    # Check dependencies
    check_dependencies()

    # Determine directories
    slides_dir = args.slides_dir or Path.cwd()
    if not slides_dir.exists():
        print(f"❌ Error: Slides directory not found: {slides_dir}")
        sys.exit(1)

    # Auto-detect audio directory
    if args.audio_dir:
        audio_dir = args.audio_dir
    elif (slides_dir / 'audio').exists():
        audio_dir = slides_dir / 'audio'
    else:
        audio_dir = slides_dir

    if not audio_dir.exists():
        print(f"⚠️  Warning: Audio directory not found: {audio_dir}")
        audio_dir = None

    # Determine output file
    output_file = args.output or (Path.cwd() / 'presentation.mp4')

    print("🎬 Slides to Video Converter")
    print("=" * 60)
    print(f"Slides directory: {slides_dir}")
    print(f"Audio directory:  {audio_dir or 'None (silent video)'}")
    print(f"Output file:      {output_file}")
    print(f"Resolution:       {args.resolution}")
    print()

    # Find slide images
    slide_images = find_slide_images(slides_dir)

    if not slide_images:
        print(f"❌ Error: No slide images found in {slides_dir}")
        print("Supported formats: jpg, jpeg, png, pdf")
        sys.exit(1)

    print(f"📸 Found {len(slide_images)} slide images")

    # Apply limit if specified
    if args.limit > 0 and args.limit < len(slide_images):
        slide_images = slide_images[:args.limit]
        print(f"📌 Limited to first {args.limit} slides")

    print()

    # Build slide-audio pairs
    segments = []
    total_duration = 0.0

    for i, slide_img in enumerate(slide_images, start=1):
        audio_file = find_audio_file(i, audio_dir, len(slide_images), strict=True) if audio_dir else None

        if audio_file:
            duration = get_audio_duration(audio_file)
            status = f"✅ {slide_img.name} + {audio_file.name} ({format_duration(duration)})"
        else:
            duration = args.default_duration
            status = f"⚪ {slide_img.name} (silent, {format_duration(duration)})"

        segments.append({
            'number': i,
            'image': slide_img,
            'audio': audio_file,
            'duration': duration
        })

        total_duration += duration
        print(f"  {i:2d}. {status}")

    print()
    print(f"📊 Total duration: {format_duration(total_duration)} ({total_duration:.1f}s)")
    print(f"📊 Average slide:  {format_duration(total_duration / len(segments))}")

    if args.dry_run:
        print("\n🔍 Dry run - no video created")
        return

    # Create temporary directory for segments
    temp_dir = Path('/tmp/slides_to_video')
    temp_dir.mkdir(exist_ok=True)

    # Create video segments
    print("\n🎥 Creating video segments...")
    progress = ProgressBar(len(segments), prefix='Progress')

    segment_files = []

    for seg in segments:
        segment_file = temp_dir / f"segment_{seg['number']:03d}.mp4"

        success = create_video_segment(
            seg['image'],
            seg['audio'],
            seg['duration'],
            segment_file,
            args.resolution,
            args.crop_bottom
        )

        if not success:
            print(f"\n❌ Error creating segment {seg['number']}")
            continue

        segment_files.append(segment_file)
        progress.update()

    progress.finish()

    if not segment_files:
        print("❌ Error: No segments created")
        sys.exit(1)

    # Concatenate segments
    print("🔗 Combining segments into final video...")

    success = concatenate_segments(segment_files, output_file)

    if not success:
        print("❌ Error: Failed to concatenate segments")
        sys.exit(1)

    # Cleanup
    if not args.keep_temp:
        print("🧹 Cleaning up temporary files...")
        for seg_file in segment_files:
            seg_file.unlink()

    print()
    print("✅ Video created successfully!")
    print(f"📂 {output_file}")
    print(f"📊 {len(segments)} slides, {format_duration(total_duration)} duration")
    print(f"💾 {output_file.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
