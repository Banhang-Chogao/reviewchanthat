#!/usr/bin/env python3
"""
QA audit script for blog posts.

Checks every post for required front matter fields,
especially image metadata. Fails if critical fields are missing.
"""

import glob
import os
import re
import sys

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

POSTS_GLOB = "content/posts/**/*.md"
REQUIRED_FIELDS = {
    "title": "missing title",
    "image": "missing main image",
    "thumbnail": "missing thumbnail (should match image)",
    "image_source": "missing image source",
    "image_source_url": "missing image source URL",
    "image_license": "missing image license",
    "image_commercial_use": "missing commercial use flag",
    "image_owner": "missing image owner (external/self)",
}

errors = []
warnings = []
total = 0
ok = 0


def check_image_exists(image_path, post_slug):
    """Check if a local image file exists in static/images/posts/."""
    if image_path.startswith("http"):
        return True  # external URL, skip check
    full_path = os.path.join("static", image_path.lstrip("/"))
    if os.path.exists(full_path):
        return True
    # Try without leading path
    full_path2 = os.path.join("static/images/posts", os.path.basename(image_path))
    if os.path.exists(full_path2):
        return True
    warnings.append(f"  [WARN] {post_slug}: local image not found: {image_path}")
    return False


def main():
    global total, ok

    posts = glob.glob(POSTS_GLOB, recursive=True)
    total = len(posts)
    print(f"Auditing {total} posts...\n")

    for filepath in sorted(posts):
        slug = os.path.basename(filepath).replace(".md", "")
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                post = frontmatter.load(f)
            except Exception as e:
                errors.append(f"  [FAIL] {slug}: cannot parse front matter: {e}")
                continue

        meta = post.metadata

        title = meta.get("title", slug)
        label = f"{title} ({filepath})"

        # Check required fields
        for field, msg in REQUIRED_FIELDS.items():
            val = meta.get(field)
            if val is None or val == "" or val is False:
                errors.append(f"  [FAIL] {label}: {msg}")
            elif field == "image_commercial_use":
                if val is not True:
                    errors.append(f"  [FAIL] {label}: image_commercial_use must be true")

        # Check no field starts with /images/ (must use relative images/posts/)
        image = meta.get("image", "")
        thumbnail = meta.get("thumbnail", "")
        for field_name, val in [("image", image), ("thumbnail", thumbnail)]:
            if val and val.startswith("/images/"):
                errors.append(f"  [FAIL] {label}: {field_name} starts with /images/ — use 'images/posts/...'")

        # Check thumbnail matches image semantics
        if thumbnail and image and thumbnail != image:
            warnings.append(f"  [WARN] {label}: thumbnail differs from image")

        # Check local image existence
        if image and not image.startswith("http"):
            check_image_exists(image, label)
        if thumbnail and not thumbnail.startswith("http") and thumbnail != image:
            check_image_exists(thumbnail, label)

        ok += 1

    print(f"\nResults:")
    print(f"  Total posts:  {total}")
    print(f"  Passed:       {ok}")
    print(f"  Errors:       {len(errors)}")
    print(f"  Warnings:     {len(warnings)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(e)
        print("\n❌ QA FAILED")
        sys.exit(1)
    else:
        print("\n✅ QA PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
