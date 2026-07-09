"""
scripts/process_images.py
Image processing pipeline for real images only:
1. Download images from source URLs (direct_url required)
2. Convert to WebP (800x450, 16:9)
3. Add watermark attribution
4. Update post frontmatter
5. Fail if no real source image available
"""

import os
import sys
import json
import hashlib
import requests
from PIL import Image, ImageDraw, ImageFont

from creator_policy import attribution_text, clean_text, sanitize_creator_pair

IMAGES_MANIFEST_PATH = "data/images.json"
POSTS_SRC_DIR = "static/images/posts-src"
POSTS_DIR = "static/images/posts"
CONTENT_DIR = "content/posts"
SITE_BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"
SELF_SOURCE_PLATFORMS = {"self", "self-owned"}


def watermark_attribution(source, creator):
    return attribution_text(source, creator)


def normalized(value):
    return clean_text(str(value)).lower()


def is_self_owned_entry(entry):
    platform = normalized(entry.get("source_platform", ""))
    license_val = normalized(entry.get("license", ""))
    return platform in SELF_SOURCE_PLATFORMS or license_val in SELF_SOURCE_PLATFORMS


def resolve_image_attribution(entry):
    """Map manifest entry to frontmatter image fields."""
    source_platform = clean_text(entry.get("source_platform", ""))
    source_url = clean_text(entry.get("source_url", ""))
    license_val = entry.get("license", "")

    if is_self_owned_entry(entry):
        src_path = clean_text(entry.get("local_source_path", ""))
        if not source_url and src_path.startswith("static/"):
            source_url = f"{SITE_BASE_URL}/{src_path.removeprefix('static/')}"
        return {
            "source": "self",
            "source_url": source_url,
            "owner": "self",
            "license_val": license_val or "Self-owned",
        }

    return {
        "source": source_platform,
        "source_url": source_url,
        "owner": "external",
        "license_val": license_val,
    }


def load_manifest():
    if not os.path.exists(IMAGES_MANIFEST_PATH):
        print(f"ERROR: {IMAGES_MANIFEST_PATH} not found. Run select_images.py first.")
        sys.exit(1)
    with open(IMAGES_MANIFEST_PATH) as f:
        return json.load(f)


def download_image(url, dest_path):
    if not url:
        return False
    try:
        print(f"    Downloading: {url}")
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(1024 * 1024):
                    f.write(chunk)
            return True
        print(f"    Download failed: HTTP {resp.status_code}")
    except Exception as e:
        print(f"    Download failed: {e}")
    return False


def has_placeholder_characteristics(img_path):
    """Detect if an image is likely a fake/solid-color placeholder."""
    try:
        img = Image.open(img_path).convert("RGB")
        if img.size[0] < 400 or img.size[1] < 300:
            return True
        pixels = list(img.getdata())
        r_vals = [p[0] for p in pixels[::100]]
        g_vals = [p[1] for p in pixels[::100]]
        b_vals = [p[2] for p in pixels[::100]]
        r_range = max(r_vals) - min(r_vals)
        g_range = max(g_vals) - min(g_vals)
        b_range = max(b_vals) - min(b_vals)
        if r_range < 30 and g_range < 30 and b_range < 30:
            return True
        return False
    except Exception:
        return False


def process_image(src_path, dest_path, watermark_text=""):
    try:
        img = Image.open(src_path).convert("RGB")
        target_w, target_h = 800, 450
        img_w, img_h = img.size
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h
        if img_ratio > target_ratio:
            new_w = int(img_h * target_ratio)
            offset = (img_w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, img_h))
        elif img_ratio < target_ratio:
            new_h = int(img_w / target_ratio)
            offset = (img_h - new_h) // 2
            img = img.crop((0, offset, img_w, offset + new_h))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        if watermark_text:
            draw = ImageDraw.Draw(img, "RGBA")
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except (IOError, OSError):
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            padding = 6
            margin = 10
            x = target_w - tw - margin - padding * 2
            y = target_h - th - margin - padding * 2
            draw.rectangle(
                [x, y, x + tw + padding * 2, y + th + padding * 2],
                fill=(0, 0, 0, 100),
            )
            draw.text(
                (x + padding, y + padding),
                watermark_text,
                fill=(255, 255, 255, 220),
                font=font,
            )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, "WebP", quality=85)
        print(f"    Saved: {dest_path} ({os.path.getsize(dest_path)} bytes)")
        return True
    except Exception as e:
        print(f"    Processing failed: {e}")
        return False


def clear_post_image(slug):
    """Remove all image fields and mark needs_image when no real image available."""
    import frontmatter
    for f in os.listdir(CONTENT_DIR):
        if not f.endswith(".md"):
            continue
        try:
            post = frontmatter.load(os.path.join(CONTENT_DIR, f))
            if post.metadata.get("slug") == slug:
                meta = post.metadata
                for key in ["image", "thumbnail", "image_source", "image_source_url",
                            "image_license", "image_commercial_use", "image_owner",
                            "image_creator", "image_creator_url"]:
                    meta.pop(key, None)
                meta["image_status"] = "needs_review"
                meta["image_reject_reason"] = "No verified image available after processing"
                with open(os.path.join(CONTENT_DIR, f), "w", encoding="utf-8") as fh:
                    fh.write(frontmatter.dumps(post))
                print(f"    Cleared image data, set needs_image: {f}")
                return
        except Exception:
            continue


def update_post_frontmatter(slug, image_path, thumbnail_path, source, source_url,
                            license_val, commercial_use, owner="external", creator="",
                            creator_url="", gate_meta=None):
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
    meta["image"] = image_path
    meta["thumbnail"] = thumbnail_path
    meta["image_source"] = source
    meta["image_source_url"] = source_url
    meta["image_license"] = license_val
    meta["image_commercial_use"] = commercial_use
    meta["image_owner"] = owner
    meta["image_creator"] = clean_text(creator)
    meta["image_creator_url"] = clean_text(creator_url) if clean_text(creator) else ""
    meta["image_status"] = "verified"
    meta.pop("image_reject_reason", None)
    if gate_meta:
        for key in (
            "image_provider", "image_query", "image_semantic_score",
            "image_color_score", "image_total_score", "image_alt",
        ):
            if gate_meta.get(key) not in (None, ""):
                meta[key] = gate_meta[key]
    if not meta.get("image_provider"):
        meta["image_provider"] = clean_text(source).lower()
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    print(f"    Updated frontmatter: {fname}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download and process verified stock images")
    parser.add_argument("--force", action="store_true", help="Re-download and reprocess existing images")
    args = parser.parse_args()

    print("=== Image Processing (Real Images Only) ===")
    manifest = load_manifest()
    success = 0
    skipped = 0
    failed = 0

    for entry in manifest.get("posts", []):
        slug = entry["slug"]
        direct_url = entry.get("direct_url", "")
        src_path = entry.get("local_source_path", f"static/images/posts-src/{slug}.jpg")
        dest_path = entry.get("output_path", f"static/images/posts/{slug}.webp")
        attribution = resolve_image_attribution(entry)
        source = attribution["source"]
        source_url = attribution["source_url"]
        license_val = attribution["license_val"]
        owner = attribution["owner"]
        commercial = entry.get("commercial_use", False)
        creator, creator_url = sanitize_creator_pair(
            entry.get("creator", ""),
            entry.get("creator_url", ""),
        )
        watermark = entry.get("watermark_text") or watermark_attribution(
            entry.get("source_platform", source),
            creator,
        )

        print(f"\n  [{slug}]")

        if not direct_url:
            print(f"    FAIL: No direct_url in manifest for {slug}")
            clear_post_image(slug)
            failed += 1
            continue

        if os.path.exists(dest_path) and not args.force:
            fsize = os.path.getsize(dest_path)
            if fsize > 5000 and not has_placeholder_characteristics(dest_path):
                print(f"    Already processed (real image): {dest_path} ({fsize} bytes)")
                gate_meta = {
                    "image_provider": clean_text(entry.get("source_platform", source)).lower(),
                    "image_query": entry.get("image_query", ""),
                    "image_semantic_score": entry.get("image_semantic_score", 0),
                    "image_color_score": entry.get("image_color_score", 0),
                    "image_total_score": entry.get("image_total_score", 0),
                    "image_alt": entry.get("image_alt", ""),
                }
                update_post_frontmatter(
                    slug=slug,
                    image_path=f"images/posts/{slug}.webp",
                    thumbnail_path=f"images/posts/{slug}.webp",
                    source=source,
                    source_url=source_url,
                    license_val=license_val,
                    commercial_use=commercial,
                    owner=owner,
                    creator=creator,
                    creator_url=creator_url,
                    gate_meta=gate_meta,
                )
                skipped += 1
                continue
            else:
                print(f"    Replacing existing file ({fsize} bytes)")

        if args.force:
            for path in (dest_path, src_path):
                if os.path.exists(path):
                    os.remove(path)
                    print(f"    Force refresh: removed {path}")

        if not os.path.exists(src_path):
            print(f"    Downloading source image...")
            ok = download_image(direct_url, src_path)
            if not ok:
                print(f"    FAIL: Could not download from {direct_url}")
                clear_post_image(slug)
                failed += 1
                continue

        if not os.path.exists(src_path):
            print(f"    FAIL: Source file not found at {src_path}")
            clear_post_image(slug)
            failed += 1
            continue

        if has_placeholder_characteristics(src_path):
            print(f"    FAIL: Downloaded source appears to be a placeholder/solid color")
            os.remove(src_path)
            clear_post_image(slug)
            failed += 1
            continue

        ok = process_image(src_path, dest_path, watermark)
        if not ok:
            print(f"    FAIL: Image processing failed for {slug}")
            clear_post_image(slug)
            failed += 1
            continue

        gate_meta = {
            "image_provider": clean_text(entry.get("source_platform", source)).lower(),
            "image_query": entry.get("image_query", ""),
            "image_semantic_score": entry.get("image_semantic_score", 0),
            "image_color_score": entry.get("image_color_score", 0),
            "image_total_score": entry.get("image_total_score", 0),
            "image_alt": entry.get("image_alt", ""),
        }
        update_post_frontmatter(
            slug=slug,
            image_path=f"images/posts/{slug}.webp",
            thumbnail_path=f"images/posts/{slug}.webp",
            source=source,
            source_url=source_url,
            license_val=license_val,
            commercial_use=commercial,
            owner=owner,
            creator=creator,
            creator_url=creator_url,
            gate_meta=gate_meta,
        )
        success += 1

    print(f"\n=== Summary ===")
    print(f"  Processed: {success}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
