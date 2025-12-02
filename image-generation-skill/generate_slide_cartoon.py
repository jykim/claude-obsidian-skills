#!/usr/bin/env python3
"""
Generate a single cartoon-style image for a slide using OpenAI DALL-E API.

This script generates ONE image at a time with user approval workflow.
Designed to be called by agents/skills for each slide that needs an image.

Usage:
    generate_slide_cartoon.py "Slide title and content description" \\
        --output-path "_files_/slide-3-cartoon.jpg" \\
        [--style "vibrant modern minimalist cartoon"] \\
        [--auto-approve]

Environment:
    OPENAI_API_KEY: Required for DALL-E API access

Cost: ~$0.04 per image (DALL-E 3 standard quality)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI SDK not installed. Install with: pip install openai", file=sys.stderr)
    sys.exit(1)


DEFAULT_STYLE = "vibrant modern minimalist cartoon illustration"
DALLE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"
COST_PER_IMAGE = 0.04


def generate_dalle_prompt(description: str, style: str) -> str:
    """
    Generate DALL-E prompt from slide description.

    Args:
        description: Slide title and content description
        style: Visual style specification

    Returns:
        Complete DALL-E prompt
    """
    prompt = f"""A {style} representing '{description}'.
The image should be visually appealing and relevant to the content.
Use vibrant colors, simple composition, and clear visual metaphors.
Important: No text or words should appear in the image."""

    return prompt.strip()


def get_user_approval(prompt: str) -> tuple[bool, Optional[str]]:
    """
    Show prompt to user and get approval.

    Args:
        prompt: The DALL-E prompt to show

    Returns:
        Tuple of (approved, edited_prompt)
        - If approved without edit: (True, None)
        - If approved with edit: (True, edited_prompt)
        - If rejected: (False, None)
    """
    print("\n" + "="*70)
    print("Generated DALL-E Prompt:")
    print("="*70)
    print(prompt)
    print("="*70)
    print(f"\nEstimated cost: ${COST_PER_IMAGE:.2f}")
    print()

    while True:
        response = input("Generate this image? [Y]es / [N]o / [E]dit / [Q]uit: ").strip().lower()

        if response in ['y', 'yes', '']:
            return True, None
        elif response in ['n', 'no']:
            print("Skipped image generation.")
            return False, None
        elif response in ['e', 'edit']:
            print("\nEnter edited prompt (or press Enter to keep original):")
            edited = input("> ").strip()
            if edited:
                return True, edited
            else:
                continue  # Show options again
        elif response in ['q', 'quit']:
            print("Quit requested.")
            sys.exit(0)
        else:
            print("Invalid response. Please enter Y/N/E/Q.")


def generate_image(client: OpenAI, prompt: str, output_path: Path) -> bool:
    """
    Generate image using DALL-E API and save to file.

    Args:
        client: OpenAI client
        prompt: DALL-E prompt
        output_path: Where to save the image

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\nGenerating image with DALL-E 3...")

        response = client.images.generate(
            model=DALLE_MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
            n=1
        )

        # Get image URL
        image_url = response.data[0].url

        # Download image
        import urllib.request
        print(f"Downloading image to {output_path}...")
        urllib.request.urlretrieve(image_url, output_path)

        print(f"✓ Image saved to: {output_path}")
        return True

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate a cartoon-style image for a slide using DALL-E",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive approval (default)
  %(prog)s "AI for Knowledge Work" --output-path "_files_/slide-3.jpg"

  # Custom style
  %(prog)s "Data Analysis" --output-path "_files_/slide-5.jpg" \\
      --style "playful colorful cartoon with tech theme"

  # Auto-approve (skip confirmation)
  %(prog)s "Project Timeline" --output-path "_files_/slide-7.jpg" --auto-approve
        """
    )

    parser.add_argument(
        "description",
        help="Slide title and content description for image generation"
    )

    parser.add_argument(
        "--output-path",
        required=True,
        help="Output path for generated image (e.g., '_files_/slide-3.jpg')"
    )

    parser.add_argument(
        "--style",
        default=DEFAULT_STYLE,
        help=f"Visual style specification (default: '{DEFAULT_STYLE}')"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip approval and generate immediately (use with caution)"
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate DALL-E prompt
    dalle_prompt = generate_dalle_prompt(args.description, args.style)

    # Get approval (unless auto-approve)
    if args.auto_approve:
        print(f"Auto-approve enabled. Generating image for: {args.description}")
        print(f"Using prompt: {dalle_prompt}")
        approved = True
        final_prompt = dalle_prompt
    else:
        approved, edited_prompt = get_user_approval(dalle_prompt)
        final_prompt = edited_prompt if edited_prompt else dalle_prompt

    if not approved:
        sys.exit(1)

    # Generate image
    client = OpenAI(api_key=api_key)
    success = generate_image(client, final_prompt, output_path)

    if success:
        print(f"\n✓ Image generation complete!")
        print(f"  Path: {output_path}")
        print(f"  Cost: ${COST_PER_IMAGE:.2f}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
