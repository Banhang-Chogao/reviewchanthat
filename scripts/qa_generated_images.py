#!/usr/bin/env python3
"""
QA checker for self-generated editorial images.

Verifies:
- Every image_provider="self-generated" has registry entry
- File exists in static/images/posts/
- Path in frontmatter matches registry
- Not a fallback/placeholder
- Dimensions >= valid minimum
- Metadata is complete
- No forbidden brand/logo words
"""

from __future__ import annotations

import json
import os
import re
import sys

from PIL import Image

CONTENT_DIR = "content/posts"
IMAGES_DIR = "static/images/posts"
REGISTRY_PATH = "data/generated-images.json"
MIN_WIDTH = 600
MIN_HEIGHT = 300
FORBIDDEN_WORDS = [
    "github logo", "apple logo", "samsung logo", "oppo logo",
    "trademark screenshot", "fake screenshot", "brand logo",
]

ERRORS: list[str] = []


def error(msg: str) -> None:
    ERRORS.append(msg)
    print(f"  ERROR: {msg}")


def main() -> int:
    print("=== QA: Self-Generated Images ===\n")

    # Load registry
    registry = {}
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH) as f:
                reg = json.load(f)
                registry = reg.get("items", {})
        except Exception as e:
            error(f"Cannot load registry: {e}")
    else:
        print("  SKIP: No registry file (no generated images to check)")

    # Scan all markdown posts
    if not os.path.isdir(CONTENT_DIR):
        error(f"Content directory not found: {CONTENT_DIR}")
        return 1

    import frontmatter

    checked = 0
    generated_found = 0

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        try:
            post = frontmatter.load(fpath)
        except Exception:
            continue

        meta = post.metadata
        slug = meta.get("slug", fname.replace(".md", ""))
        provider = (meta.get("image_provider") or "").strip().lower()

        if provider != "self-generated":
            continue

        generated_found += 1
        print(f"\n  [{slug}]")

        # Check registry entry
        reg_entry = registry.get(slug)
        if not reg_entry:
            error(f"{slug}: missing registry entry in {REGISTRY_PATH}")
        else:
            print(f"    Registry: OK")

        # Check image path
        image = meta.get("image", "")
        if not image:
            error(f"{slug}: image field is empty")
        else:
            # File on disk
            local_path = os.path.join("static", image) if not image.startswith("static/") else image
            if not os.path.exists(local_path):
                error(f"{slug}: image file not found: {local_path}")
            else:
                fsize = os.path.getsize(local_path)
                if fsize < 5000:
                    error(f"{slug}: image too small: {fsize} bytes")
                else:
                    print(f"    File: {local_path} ({fsize} bytes)")

                # Check dimensions
                try:
                    with Image.open(local_path) as img:
                        w, h = img.size
                        if w < MIN_W or h < MIN_HEIGHT:
                            error(f"{slug}: dimensions too small: {w}x{h} (min {MIN_W}x{MIN_HEIGHT})")
                        else:
                            print(f"    Dimensions: {w}x{h}")
                except Exception as e:
                    error(f"{slug}: cannot read image: {e}")

                # Check path matches registry
                if reg_entry:
                    expected_path = reg_entry.get("path", "")
                    if expected_path and image != expected_path:
                        error(f"{slug}: frontmatter path '{image}' != registry path '{expected_path}'")

        # Check metadata
        required_fields = [
            "image_source", "image_source_url", "image_license",
            "image_commercial_use", "image_owner", "image_creator",
        ]
        for field in required_fields:
            val = meta.get(field)
            if val is None or val == "":
                error(f"{slug}: missing required field: {field}")

        # Check attribution
        if meta.get("image_attribution_verified") is not True:
            error(f"{slug}: image_attribution_verified must be true for self-generated")

        if meta.get("image_attribution_source") != "self_generated":
            error(f"{slug}: image_attribution_source should be self_generated")

        # Check no forbidden words
        blob = f"{slug} {meta.get('title', '')} {meta.get('image_alt', '')}".lower()
        for word in FORBIDDEN_WORDS:
            if word in blob:
                error(f"{slug}: forbidden word detected: '{word}'")

        # Check no fallback markers in filename
        low_path = image.lower()
        if any(m in low_path for m in ("fallback", "placeholder", "default")):
            error(f"{slug}: image path looks like fallback: {image}")

        # Check image_status
        if meta.get("image_status") != "verified":
            error(f"{slug}: image_status should be 'verified' for self-generated (got: {meta.get('image_status')})")

        # Check image_owner
        if meta.get("image_owner") != "self":
            error(f"{slug}: image_owner should be 'self' for self-generated")

        checked += 1

    print(f"\n=== Summary ===")
    print(f"  Generated images found: {generated_found}")
    print(f"  Checked (passed basic checks): {checked}")
    print(f"  Registry entries: {len(registry)}")
    print(f"  Errors: {len(ERRORS)}")

    for e in ERRORS:
        print(f"    - {e}")

    if ERRORS:
        print("\nFAILED: QA found errors in generated images.")
        return 1

    if generated_found == 0:
        print("\nNo generated images to verify. (This is fine if no posts needed fallback.)")
    else:
        print("\nAll generated images pass QA.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())