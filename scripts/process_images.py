"""
scripts/process_images.py
Image processing pipeline:
1. Download images from source URLs (if direct_url available)
2. Convert to WebP
3. Add watermark attribution text
4. Update post frontmatter to point to local images
"""

import os
import sys
import json
import hashlib
from urllib.parse import urlparse

IMAGES_MANIFEST_PATH = "data/images.json"
POSTS_SRC_DIR = "static/images/posts-src"
POSTS_DIR = "static/images/posts"
CONTENT_DIR = "content/posts"


def load_manifest():
    if not os.path.exists(IMAGES_MANIFEST_PATH):
        print(f"ERROR: {IMAGES_MANIFEST_PATH} not found. Run select_images.py first.")
        sys.exit(1)
    with open(IMAGES_MANIFEST_PATH) as f:
        return json.load(f)


def download_image(url, dest_path):
    """Download an image from URL to local path."""
    if not url:
        return False
    try:
        import requests
        print(f"    Downloading: {url}")
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(1024 * 1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"    Download failed: {e}")
    return False


def process_image(src_path, dest_path, watermark_text=""):
    """
    Process image:
    - Resize/crop to 800x450 (16:9)
    - Convert to WebP
    - Add watermark text attribution
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("    Pillow not installed. Install: pip install Pillow")
        return False

    if not os.path.exists(src_path):
        print(f"    Source not found: {src_path}")
        return False

    try:
        img = Image.open(src_path).convert("RGB")

        # Resize/crop to 16:9 (800x450)
        target_w, target_h = 800, 450
        img_w, img_h = img.size

        # Crop to 16:9 aspect ratio
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h

        if img_ratio > target_ratio:
            # Image is wider — crop width
            new_w = int(img_h * target_ratio)
            offset = (img_w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, img_h))
        elif img_ratio < target_ratio:
            # Image is taller — crop height
            new_h = int(img_w / target_ratio)
            offset = (img_h - new_h) // 2
            img = img.crop((0, offset, img_w, offset + new_h))

        img = img.resize((target_w, target_h), Image.LANCZOS)

        # Add watermark text
        if watermark_text:
            draw = ImageDraw.Draw(img, "RGBA")
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except (IOError, OSError):
                font = ImageFont.load_default()

            # Measure text
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            padding = 6
            margin = 10
            x = target_w - tw - margin - padding * 2
            y = target_h - th - margin - padding * 2

            # Background bar
            draw.rectangle(
                [x, y, x + tw + padding * 2, y + th + padding * 2],
                fill=(0, 0, 0, 100),
            )

            # Text
            draw.text(
                (x + padding, y + padding),
                watermark_text,
                fill=(255, 255, 255, 220),
                font=font,
            )

        # Save as WebP
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, "WebP", quality=85)
        print(f"    Saved: {dest_path}")
        return True

    except Exception as e:
        print(f"    Processing failed: {e}")
        return False


def update_post_frontmatter(slug, image_path, thumbnail_path, source, source_url,
                            license_val, commercial_use, owner="external", creator=""):
    """Update post frontmatter with local image paths."""
    import frontmatter

    fname = None
    for f in os.listdir(CONTENT_DIR):
        if f.endswith(".md"):
            try:
                post = frontmatter.load(os.path.join(CONTENT_DIR, f))
                if post.metadata.get("slug") == slug:
                    fname = f
                    break
            except Exception:
                continue

    if not fname:
        print(f"    Post not found for slug: {slug}")
        return False

    fpath = os.path.join(CONTENT_DIR, fname)
    post = frontmatter.load(fpath)
    meta = post.metadata

    # Update image fields
    meta["image"] = image_path
    meta["thumbnail"] = thumbnail_path
    meta["image_source"] = source
    meta["image_source_url"] = source_url
    meta["image_license"] = license_val
    meta["image_commercial_use"] = commercial_use
    meta["image_owner"] = owner
    if creator:
        meta["image_creator"] = creator

    # Write back preserving YAML
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    print(f"    Updated frontmatter: {fname}")
    return True


def main():
    print("=== Image Processing + Watermark ===")
    manifest = load_manifest()

    success = 0
    skipped = 0
    failed = 0

    for entry in manifest.get("posts", []):
        slug = entry["slug"]
        direct_url = entry.get("direct_url", "")
        src_path = entry.get("local_source_path", f"static/images/posts-src/{slug}.jpg")
        dest_path = entry.get("output_path", f"static/images/posts/{slug}.webp")
        watermark = entry.get("watermark_text", "")

        print(f"\n  [{slug}]")

        # Check if already processed
        if os.path.exists(dest_path):
            print(f"    Already processed: {dest_path}")
            skipped += 1
            continue

        # Try to download if direct URL exists
        if direct_url and not os.path.exists(src_path):
            downloaded = download_image(direct_url, src_path)
            if not downloaded:
                print(f"    Cannot download. Place image manually at: {src_path}")
                failed += 1
                continue

        # If no direct URL and no local file, skip
        if not os.path.exists(src_path) and not direct_url:
            print(f"    No source available. Place image at: {src_path}")
            failed += 1
            continue

        # Process image
        if os.path.exists(src_path):
            ok = process_image(src_path, dest_path, watermark)
            if ok:
                success += 1
            else:
                failed += 1
                continue

        # Update frontmatter
        source = entry.get("source_platform", "")
        source_url = entry.get("source_url", "")
        license_val = entry.get("license", "")
        commercial = entry.get("commercial_use", False)
        creator = entry.get("creator", "")

        update_post_frontmatter(
            slug=slug,
            image_path=f"images/posts/{slug}.webp",
            thumbnail_path=f"images/posts/{slug}.webp",
            source=source,
            source_url=source_url,
            license_val=license_val,
            commercial_use=commercial,
            owner="external",
            creator=creator,
        )

    print(f"\n=== Summary ===")
    print(f"  Processed: {success}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Failed: {failed}")


if __name__ == "__main__":
    main()
