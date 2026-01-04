#!/usr/bin/env python3
"""
Generate images using Google Gemini Image API.

This script generates ONE image at a time with user approval workflow.
Designed to be called by agents/skills for slides or documents.

IMPORTANT - Model Selection:
    - ALWAYS use gemini-3-pro-image-preview for Korean text quality
    - Other models have poor Korean text rendering
    - gemini-3-pro is the default and RECOMMENDED model

Usage:
    generate_gemini_image.py "Image description" \\
        --output-path "_files_/output.png" \\
        [--style "vibrant modern minimalist"] \\
        [--model "gemini-3-pro-image-preview"] \\
        [--aspect-ratio "1:1"] \\
        [--auto-approve]

Batch Generation (Speed Up):
    For generating multiple images, use parallel execution:
    - Run multiple instances concurrently (up to 5 parallel)
    - Rate limit: ~10 requests/minute, add delays between batches
    - Example: Use Python concurrent.futures or GNU parallel

    # Parallel with Python:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(generate_image, prompts)

Environment:
    GEMINI_API_KEY: Required for Gemini API access

Cost: Varies by model (gemini-3-pro: $0.06/image)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: Google GenAI SDK not installed. Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)

from io import BytesIO


# Constants
DEFAULT_STYLE = "professional presentation slide infographic with clear text hierarchy, key bullet points, icons, and visual data representation. Include readable Korean/English text labels and annotations that convey the main message"
DEFAULT_MODEL = "gemini-3-pro-image-preview"

AVAILABLE_MODELS = {
    "gemini-2.0-flash-exp": {
        "cost": 0.00,  # Free tier available
        "description": "Fast, free tier, good for iteration (no aspect ratio support)",
        "supports_aspect_ratio": False
    },
    "gemini-2.5-flash-image": {
        "cost": 0.039,
        "description": "Latest 2.5 flash image, supports aspect ratios",
        "supports_aspect_ratio": True
    },
    "gemini-2.0-flash-exp-image-generation": {
        "cost": 0.00,
        "description": "2.0 flash image generation",
        "supports_aspect_ratio": True
    },
    "gemini-3-pro-image-preview": {
        "cost": 0.06,
        "description": "Gemini 3 Pro Image, highest quality",
        "supports_aspect_ratio": True
    },
    "imagen-4.0-generate-001": {
        "cost": 0.03,
        "description": "Imagen 4.0, high quality",
        "supports_aspect_ratio": True
    },
}

ASPECT_RATIOS = ["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "21:9"]


def generate_gemini_prompt(description: str, style: str, include_text: bool = True) -> str:
    """
    Generate optimized prompt for Gemini image generation.

    Args:
        description: Image content description
        style: Visual style specification
        include_text: Whether to include text/labels in the image

    Returns:
        Complete Gemini prompt
    """
    base_prompt = f"""A {style} representing '{description}'.
The image should be visually appealing and relevant to the content.
Use clear visual hierarchy, meaningful icons, and professional composition."""

    if include_text:
        base_prompt += """
Include relevant Korean text labels, titles, or annotations that help explain the concept.
Text should be minimal, readable, and well-integrated into the design."""
    else:
        base_prompt += """
CRITICAL: Absolutely NO text, words, letters, numbers, captions, labels, or any written characters should appear anywhere in the image. The image must be completely text-free."""

    return base_prompt.strip()


def get_user_approval(prompt: str, model: str, aspect_ratio: str) -> tuple[bool, Optional[str]]:
    """
    Show prompt to user and get approval.

    Args:
        prompt: The Gemini prompt to show
        model: Model being used
        aspect_ratio: Aspect ratio setting

    Returns:
        Tuple of (approved, edited_prompt)
        - If approved without edit: (True, None)
        - If approved with edit: (True, edited_prompt)
        - If rejected: (False, None)
    """
    model_info = AVAILABLE_MODELS.get(model, {"cost": 0.00, "description": "Unknown"})

    print("\n" + "=" * 70)
    print("Generated Gemini Prompt:")
    print("=" * 70)
    print(prompt)
    print("=" * 70)
    print(f"\nModel: {model}")
    print(f"Aspect Ratio: {aspect_ratio}")
    print(f"Estimated cost: ${model_info['cost']:.2f}")
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
                continue
        elif response in ['q', 'quit']:
            print("Quit requested.")
            sys.exit(0)
        else:
            print("Invalid response. Please enter Y/N/E/Q.")


def generate_image(
    client: genai.Client,
    prompt: str,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = "1:1"
) -> bool:
    """
    Generate image using Gemini API and save to file.

    Args:
        client: Gemini client
        prompt: Image generation prompt
        output_path: Where to save the image
        model: Model to use
        aspect_ratio: Aspect ratio for the image

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\nGenerating image with {model}...")

        model_info = AVAILABLE_MODELS.get(model, {"supports_aspect_ratio": False})
        supports_aspect_ratio = model_info.get("supports_aspect_ratio", False)

        # Use appropriate API based on model
        if model.startswith("imagen"):
            # Imagen model uses generate_images
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                )
            )

            if response.generated_images:
                image_data = response.generated_images[0].image.image_bytes
                image = Image.open(BytesIO(image_data))
            else:
                print("No image generated", file=sys.stderr)
                return False
        else:
            # Gemini model uses generate_content
            # Build config with or without aspect ratio support
            if supports_aspect_ratio:
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    imageConfig=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                )
            else:
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                )
                if aspect_ratio != "1:1":
                    print(f"Warning: Model {model} does not support aspect ratio. Using default 1:1.", file=sys.stderr)

            response = client.models.generate_content(
                model=model,
                contents=[prompt],
                config=config
            )

            # Extract image from response
            image_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    image_data = part.inline_data.data
                    break

            if not image_data:
                print("No image data in response", file=sys.stderr)
                return False

            image = Image.open(BytesIO(image_data))

        # Determine format from output path
        output_format = output_path.suffix.lower().lstrip('.')
        if output_format == 'jpg':
            output_format = 'jpeg'
        elif output_format not in ['png', 'jpeg']:
            output_format = 'png'

        # Convert RGBA to RGB for JPEG
        if output_format == 'jpeg' and image.mode == 'RGBA':
            image = image.convert('RGB')

        image.save(output_path, format=output_format.upper())
        print(f"Image saved to: {output_path}")
        return True

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Google Gemini Image API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive approval (default)
  %(prog)s "AI for Knowledge Work" --output-path "_files_/slide-3.png"

  # Custom style
  %(prog)s "Data Analysis" --output-path "_files_/slide-5.png" \\
      --style "playful colorful cartoon with tech theme"

  # Different aspect ratio
  %(prog)s "Team Meeting" --output-path "_files_/meeting.png" \\
      --aspect-ratio "16:9"

  # Auto-approve (skip confirmation)
  %(prog)s "Project Timeline" --output-path "_files_/slide-7.png" --auto-approve

  # Use Imagen 3 model
  %(prog)s "Product Design" --output-path "_files_/product.png" \\
      --model "imagen-3.0-generate-002"
        """
    )

    parser.add_argument(
        "description",
        help="Image description for generation"
    )

    parser.add_argument(
        "--output-path",
        required=True,
        help="Output path for generated image (e.g., '_files_/slide-3.png')"
    )

    parser.add_argument(
        "--style",
        default=DEFAULT_STYLE,
        help=f"Visual style specification (default: '{DEFAULT_STYLE}')"
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(AVAILABLE_MODELS.keys()),
        help=f"Gemini model to use (default: '{DEFAULT_MODEL}')"
    )

    parser.add_argument(
        "--aspect-ratio",
        default="1:1",
        choices=ASPECT_RATIOS,
        help="Aspect ratio for the image (default: '1:1')"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip approval and generate immediately (use with caution)"
    )

    parser.add_argument(
        "--no-text",
        action="store_true",
        help="Generate image without any text/labels (default: include text)"
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate prompt
    include_text = not args.no_text
    gemini_prompt = generate_gemini_prompt(args.description, args.style, include_text)

    # Get approval (unless auto-approve)
    if args.auto_approve:
        print(f"Auto-approve enabled. Generating image for: {args.description}")
        print(f"Using prompt: {gemini_prompt}")
        approved = True
        final_prompt = gemini_prompt
    else:
        approved, edited_prompt = get_user_approval(
            gemini_prompt, args.model, args.aspect_ratio
        )
        final_prompt = edited_prompt if edited_prompt else gemini_prompt

    if not approved:
        sys.exit(1)

    # Generate image
    client = genai.Client(api_key=api_key)
    success = generate_image(
        client,
        final_prompt,
        output_path,
        model=args.model,
        aspect_ratio=args.aspect_ratio
    )

    model_info = AVAILABLE_MODELS.get(args.model, {"cost": 0.00})

    if success:
        print(f"\nImage generation complete!")
        print(f"  Path: {output_path}")
        print(f"  Cost: ${model_info['cost']:.2f}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
