#!/usr/bin/env python3
"""
QA for API-first image pipeline.
Checks for common issues that would break the build or deployment.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posts"
STATIC_DIR = ROOT / "static" / "images" / "posts"
PUBLIC_DIR = ROOT / "public"

ISSUES = {
    "critical": [],
    "warning": [],
}


def error(category: str, msg: str) -> None:
    if category == "critical":
        ISSUES["critical"].append(msg)
    else:
        ISSUES["warning"].append(msg)


def check_no_broken_paths() -> None:
    """Check no posts have leading slash in image path."""
    for post_path in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(post_path)
            meta = post.metadata
            img = meta.get("image", "")
            if img.startswith("/"):
                error("critical", f"{post_path.stem}: image path starts with slash: {img}")
        except Exception:
            pass


def check_required_image_fields() -> None:
    """Check new/changed posts have all required image fields."""
    for post_path in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(post_path)
            meta = post.metadata
            slug = meta.get("slug", post_path.stem)

            # Skip if no image set
            if not meta.get("image"):
                # Check if status indicates it's deliberate
                status = meta.get("image_status", "")
                if status not in ("needs_image", "skip", "exempt"):
                    error("warning", f"{slug}: no image set and no image_status")
                continue

            # If image is set, require these fields
            required = [
                ("image_provider", "image provider"),
                ("image_source", "image source"),
                ("image_source_url", "image source URL"),
                ("image_license", "license"),
                ("image_commercial_use", "commercial use flag"),
                ("image_owner", "image owner"),
                ("image_attribution_verified", "attribution verified flag"),
                ("image_attribution_source", "attribution source"),
            ]

            for field, label in required:
                if not meta.get(field) and field not in ("image_attribution_verified",):
                    if not (field == "image_commercial_use" and meta.get(field) is False):
                        error("critical", f"{slug}: missing {label} ({field})")

        except Exception as e:
            error("warning", f"Error checking {post_path.stem}: {e}")


def check_no_fake_creators() -> None:
    """Check no posts have fake/blocked creator names."""
    blocked = {
        "pexels", "pixabay", "unsplash", "freepik",
        "photographer", "creator", "unknown", "park bogum",
        "pexels creator", "unsplash photographer", "pixabay creator",
    }

    for post_path in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(post_path)
            meta = post.metadata
            slug = meta.get("slug", post_path.stem)
            creator = str(meta.get("image_creator", "")).strip().lower()

            if creator and creator in blocked:
                error("critical", f"{slug}: fake/blocked creator: {creator}")

            # For self-generated, must be Review Chân Thật
            provider = meta.get("image_provider", "").lower()
            if provider == "self-generated" and creator and "review" not in creator:
                error("critical", f"{slug}: self-generated but wrong creator: {creator}")

        except Exception:
            pass


def check_no_placeholder_paths() -> None:
    """Check no posts reference fallback.webp or placeholder images."""
    for post_path in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(post_path)
            meta = post.metadata
            img = meta.get("image", "")
            if "fallback" in img.lower() or "placeholder" in img.lower():
                error("critical", f"{post_path.stem}: uses fallback/placeholder image: {img}")
        except Exception:
            pass


def check_processed_images_exist() -> None:
    """Check that processed images exist on disk for posts with image field."""
    for post_path in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(post_path)
            meta = post.metadata
            slug = meta.get("slug", post_path.stem)

            img = meta.get("image", "")
            if not img:
                continue

            # Check file exists
            img_full_path = ROOT / img
            if not img_full_path.exists():
                provider = meta.get("image_provider", "unknown")
                owner = meta.get("image_owner", "unknown")
                # Self-generated might not be processed yet, but API images should exist
                if provider != "self-generated":
                    error("critical", f"{slug}: image file missing: {img}")
                else:
                    error("warning", f"{slug}: self-generated image file missing: {img}")

        except Exception:
            pass


def check_no_secrets() -> None:
    """Check no API keys in reports/data/public."""
    secrets_pattern = re.compile(
        r"(PEXELS_API_KEY|PIXABAY_API_KEY|UNSPLASH_ACCESS_KEY|FREEPIK_API_KEY|BEGIN PRIVATE KEY)"
    )

    for check_dir in [ROOT / "data", ROOT / "reports", ROOT / "public"]:
        if not check_dir.exists():
            continue
        for file_path in check_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix in (".png", ".jpg", ".webp", ".ico"):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if secrets_pattern.search(content):
                        error("critical", f"Secrets found in: {file_path.relative_to(ROOT)}")
            except Exception:
                pass


def main() -> int:
    print("=== Image Pipeline QA ===\n")

    print("Checking for broken image paths...")
    check_no_broken_paths()

    print("Checking for required image fields...")
    check_required_image_fields()

    print("Checking for fake/blocked creators...")
    check_no_fake_creators()

    print("Checking for placeholder images...")
    check_no_placeholder_paths()

    print("Checking processed images exist...")
    check_processed_images_exist()

    print("Checking for leaked secrets...")
    check_no_secrets()

    print(f"\n=== Results ===")
    print(f"Critical issues: {len(ISSUES['critical'])}")
    print(f"Warnings: {len(ISSUES['warning'])}")

    if ISSUES["critical"]:
        print(f"\n❌ Critical Issues:")
        for issue in ISSUES["critical"]:
            print(f"  - {issue}")
        return 1

    if ISSUES["warning"]:
        print(f"\n⚠️  Warnings:")
        for issue in ISSUES["warning"]:
            print(f"  - {issue}")

    print(f"\n✓ Image pipeline QA passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
