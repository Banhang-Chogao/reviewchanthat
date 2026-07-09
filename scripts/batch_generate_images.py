#!/usr/bin/env python3
"""Batch generate hero images for all posts.

Usage:
  python3 scripts/batch_generate_images.py --backend placeholder
  python3 scripts/batch_generate_images.py --backend dalle3 --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dataclasses import asdict

from generate_hero_image import generate_image, ImageGenerationConfig
from batch_analyze_posts_for_image import IMAGE_CONTEXT_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"


def batch_generate(backend: str, limit: int | None = None) -> tuple[int, int]:
    """Generate images for all posts with analyses.

    Returns:
        (success_count, error_count)
    """
    analysis_files = sorted(IMAGE_CONTEXT_DIR.glob("*.json"))
    if limit:
        analysis_files = analysis_files[:limit]

    print(f"📊 Generating {len(analysis_files)} images with {backend}...")

    success = 0
    errors = 0

    config = ImageGenerationConfig(
        backend=backend,
        size="1200x630",
        quality="standard",
        style="natural",
    )

    for idx, analysis_file in enumerate(analysis_files, 1):
        try:
            import json
            with open(analysis_file, "r") as f:
                analysis = json.load(f)

            result = generate_image(analysis, config)
            if result:
                success += 1
            else:
                errors += 1

            if idx % 10 == 0:
                print(f"  {idx}/{len(analysis_files)} ✓")

        except Exception as e:
            errors += 1
            print(f"  ✗ {analysis_file.name}: {e}")

    return success, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch generate hero images")
    parser.add_argument("--backend", default="placeholder", choices=["dalle3", "placeholder"])
    parser.add_argument("--limit", type=int, help="Generate only first N images")

    args = parser.parse_args()

    success, errors = batch_generate(args.backend, limit=args.limit)

    print(f"\n✅ Complete: {success} generated, {errors} errors")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
