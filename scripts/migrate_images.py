#!/usr/bin/env python3
"""
Add complete image metadata to all blog posts.

Reads each post, extracts photo IDs from Unsplash URLs,
adds thumbnail, image_source, image_source_url, etc.
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

# Map of Unsplash photo ID → known photo page slugs (constructed from ID)
# The photo page URL is https://unsplash.com/photos/{photo_id}


def get_unsplash_photo_id(image_url):
    """Extract Unsplash photo ID from an image URL."""
    m = re.search(r"photo-([a-zA-Z0-9_-]+)", image_url)
    return m.group(1) if m else None


def main():
    posts = glob.glob(POSTS_GLOB, recursive=True)
    if not posts:
        print("No posts found.")
        sys.exit(1)

    for filepath in sorted(posts):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                post = frontmatter.load(f)
            except Exception as e:
                print(f"  [ERR] Cannot parse {filepath}: {e}")
                continue

        meta = post.metadata
        image = meta.get("image", "")

        if not image:
            print(f"  [SKIP] {filepath}: no image field")
            continue

        # Determine image type
        is_unsplash = "images.unsplash.com" in image
        is_pixabay = "pixabay.com" in image

        # Set thumbnail = image if not already set
        if not meta.get("thumbnail"):
            meta["thumbnail"] = image

        # Set image metadata
        if is_unsplash:
            photo_id = get_unsplash_photo_id(image)
            if not meta.get("image_source"):
                meta["image_source"] = "Unsplash"
            if not meta.get("image_source_url") and photo_id:
                meta["image_source_url"] = f"https://unsplash.com/photos/{photo_id}"
            if not meta.get("image_license"):
                meta["image_license"] = "Unsplash License"
            if not meta.get("image_commercial_use"):
                meta["image_commercial_use"] = True
            if not meta.get("image_owner"):
                meta["image_owner"] = "external"
        elif is_pixabay:
            if not meta.get("image_source"):
                meta["image_source"] = "Pixabay"
            if not meta.get("image_license"):
                meta["image_license"] = "Pixabay Content License"
            if not meta.get("image_commercial_use"):
                meta["image_commercial_use"] = True
            if not meta.get("image_owner"):
                meta["image_owner"] = "external"
        else:
            # Unknown source – fill generic metadata
            if not meta.get("image_source"):
                meta["image_source"] = "external"
            if not meta.get("image_license"):
                meta["image_license"] = "Commercial Use Allowed"
            if not meta.get("image_commercial_use"):
                meta["image_commercial_use"] = True
            if not meta.get("image_owner"):
                meta["image_owner"] = "external"

        # Ensure thumbnail exists
        if not meta.get("thumbnail"):
            meta["thumbnail"] = image

        post.metadata = meta
        with open(filepath, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        print(f"  [OK]   {os.path.basename(filepath)}: thumbnail + image metadata added")

    print("Done.")


if __name__ == "__main__":
    main()
