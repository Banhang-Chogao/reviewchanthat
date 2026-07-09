#!/usr/bin/env python3
"""Generate hero images from content analysis using AI.

Integrates with image generation backends:
- DALL-E 3 (via OpenAI API)
- Stable Diffusion (via Replicate)
- Placeholder generation (fallback)

Usage:
  python3 scripts/generate_hero_image.py \\
    --analysis reports/image-context/post.json \\
    --backend dalle3 --size 1200x630

  python3 scripts/generate_hero_image.py \\
    --post content/posts/post.md \\
    --backend placeholder
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze_post_for_image import analyze_post
from image_prompt_builder import build_image_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static" / "images" / "posts"


@dataclass
class ImageGenerationConfig:
    backend: str
    size: str
    quality: str = "standard"
    style: str = "natural"
    timeout: int = 300


@dataclass
class GeneratedImage:
    path: Path
    prompt: str
    backend: str
    timestamp: str


def parse_size(size_str: str) -> tuple[int, int]:
    """Parse size string 'WIDTHxHEIGHT'."""
    try:
        w, h = size_str.lower().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 1200, 630


def generate_with_dalle3(
    prompt: str,
    size: str = "1200x630",
    quality: str = "standard",
    style: str = "natural",
) -> str | None:
    """Generate image using DALL-E 3 via OpenAI API."""
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found")
            return None

        client = openai.Client(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            style=style,
            n=1,
        )

        if response.data and len(response.data) > 0:
            return response.data[0].url
    except Exception as e:
        print(f"❌ DALL-E 3 failed: {e}")

    return None


def create_placeholder_image(
    prompt: str,
    size: str = "1200x630",
    topic: str = "general",
) -> bytes | None:
    """Create placeholder image using PIL."""
    try:
        from PIL import Image, ImageDraw

        w, h = parse_size(size)
        color_map = {
            "autumn_leaves": ((139, 69, 19), (255, 165, 0)),
            "korea_travel": ((25, 25, 112), (255, 215, 0)),
            "thailand_travel": ((0, 102, 204), (255, 200, 0)),
            "apple_product": ((50, 50, 50), (200, 200, 200)),
            "apple_dma": ((30, 30, 30), (100, 100, 255)),
        }

        color_start, color_end = color_map.get(topic, ((100, 100, 100), (200, 200, 200)))

        img = Image.new("RGB", (w, h), color_start)
        pixels = img.load()

        for y in range(h):
            r = int(color_start[0] + (color_end[0] - color_start[0]) * y / h)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * y / h)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * y / h)
            for x in range(w):
                pixels[x, y] = (r, g, b)

        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as e:
        print(f"⚠️  Placeholder generation failed: {e}")

    return None


def save_image(image_data: bytes | str, output_path: Path) -> bool:
    """Save image to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if isinstance(image_data, bytes):
            with open(output_path, "wb") as f:
                f.write(image_data)
            return True
        elif isinstance(image_data, str):
            import requests
            response = requests.get(image_data, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
    except Exception as e:
        print(f"❌ Failed to save image: {e}")

    return False


def generate_image(analysis: dict[str, Any], config: ImageGenerationConfig) -> GeneratedImage | None:
    """Generate image from analysis."""
    prompt_obj = build_image_prompt(analysis)
    prompt = prompt_obj.to_full_prompt()

    print(f"\n🎨 Generating with {config.backend}")
    print(f"   Topic: {analysis.get('primary_topic')}")
    print(f"   Prompt: {prompt[:70]}...")

    result = None

    if config.backend == "dalle3":
        result = generate_with_dalle3(prompt, config.size, config.quality, config.style)
    elif config.backend == "placeholder":
        result = create_placeholder_image(prompt, config.size, analysis.get("primary_topic"))

    if not result:
        print(f"❌ Generation failed")
        return None

    slug = analysis.get("slug", "generated")
    output_path = STATIC_DIR / f"{slug}.webp"

    if save_image(result, output_path):
        print(f"✅ Saved: {output_path}")
        return GeneratedImage(
            path=output_path,
            prompt=prompt,
            backend=config.backend,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate hero images")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--post", help="Post path")
    input_group.add_argument("--analysis", help="Analysis JSON path")
    parser.add_argument("--backend", default="placeholder", choices=["dalle3", "placeholder"])
    parser.add_argument("--size", default="1200x630")
    parser.add_argument("--quality", default="standard")
    parser.add_argument("--style", default="natural")

    args = parser.parse_args()

    if args.post:
        analysis = analyze_post(args.post)
        if not analysis:
            return 1
        analysis = asdict(analysis)
    else:
        with open(args.analysis, "r") as f:
            analysis = json.load(f)

    config = ImageGenerationConfig(
        backend=args.backend,
        size=args.size,
        quality=args.quality,
        style=args.style,
    )

    result = generate_image(analysis, config)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
