#!/usr/bin/env python3
"""
scripts/qa_hero_images.py

Narrow, dependency-free deploy gate that blocks the exact "broken hero"
bug class: a post whose front matter references an `image`/`thumbnail`
path that does NOT exist as a real file under static/.

This is intentionally NOT compliance.py: it does ZERO metadata/creator/
license validation (which carries known baseline debt). It only asserts
"every referenced local image file actually exists", so it can run as a
blocking step without tripping over legacy debt.

Exit 0 = every post's referenced local image exists.
Exit 1 = at least one referenced local image is missing/empty.
"""
import os
import sys
import glob

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

CONTENT_DIR = "content/posts"
STATIC_DIR = "static"


def read_toml_frontmatter(path):
    import re
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.lstrip().startswith("+++"):
        return None
    # Strip opening +++ and extract content until closing +++ on its own line.
    # Using re.MULTILINE ensures we do NOT match +++ inside string values.
    body = text.lstrip()[3:]
    end_match = re.search(r"^\+{3}\s*$", body, re.MULTILINE)
    if not end_match:
        return None
    return tomllib.loads(body[:end_match.start()])


def local_image_missing(value):
    """True if `value` is a local path that does not exist on disk."""
    if not value:
        return True  # empty image/thumbnail is itself a broken hero
    if value.startswith("http://") or value.startswith("https://"):
        return False  # remote image: out of scope for this on-disk gate
    rel = value.lstrip("/")
    return not os.path.exists(os.path.join(STATIC_DIR, rel))


def main():
    errors = []
    checked = 0
    for path in sorted(glob.glob(os.path.join(CONTENT_DIR, "*.md"))):
        meta = read_toml_frontmatter(path)
        if meta is None:
            continue
        slug = os.path.splitext(os.path.basename(path))[0]
        checked += 1
        for field in ("image", "thumbnail"):
            value = (meta.get(field) or "").strip()
            if local_image_missing(value):
                errors.append(f"[BROKEN_HERO] {slug}: {field}={value!r} -> no file at {STATIC_DIR}/{value.lstrip('/')}")

    if errors:
        print(f"qa_hero_images FAILED: {len(errors)} broken image reference(s)\n")
        for err in errors:
            print(f"  {err}")
        print("\nFix: commit the missing static/images/posts/<slug>.webp "
              "(select_images.py + process_images.py), or repoint the front matter.")
        return 1
    print(f"qa_hero_images PASSED: {checked} posts, all referenced images exist on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
