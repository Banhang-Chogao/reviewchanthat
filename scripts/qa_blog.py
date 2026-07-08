"""
scripts/qa_blog.py
Quality assurance checks for the blog.
Hard failures on: fallback images, missing images, missing metadata, duplicates, etc.
"""

import os
import sys
import json
import frontmatter

CONTENT_DIR = "content/posts"
IMAGES_POSTS_DIR = "static/images/posts"
AUDIT_REPORT_PATH = "data/image-audit-report.json"
DEDUPE_REPORT_PATH = "data/image-dedupe-report.json"
WHITELIST_PATH = "data/dupe-whitelist.json"

FALLBACK_PATHS = {"images/posts/fallback.webp", "images/fallback.webp"}


def load_whitelist():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH) as f:
            return set(json.load(f).get("whitelisted_urls", []))
    return set()


def has_placeholder_characteristics(filepath):
    try:
        from PIL import Image
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        if w < 400 or h < 300:
            return True
        pixels = list(img.getdata())
        r_vals = [p[0] for p in pixels[::200]]
        g_vals = [p[1] for p in pixels[::200]]
        b_vals = [p[2] for p in pixels[::200]]
        r_range = max(r_vals) - min(r_vals)
        g_range = max(g_vals) - min(g_vals)
        b_range = max(b_vals) - min(b_vals)
        if r_range < 25 and g_range < 25 and b_range < 25:
            return True
        return False
    except Exception:
        return False


def qa():
    errors = []
    whitelist = load_whitelist()
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    if not os.path.exists(posts_dir):
        print(f"FAIL: {CONTENT_DIR} not found")
        sys.exit(1)

    seen_urls = {}
    posts_with_fallback_images = 0
    posts_with_needs_image = 0

    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            post = frontmatter.load(fpath)
        except Exception as e:
            errors.append(f"[PARSE_ERROR] {fname}: {e}")
            continue

        meta = post.metadata
        slug = meta.get("slug", fname.replace(".md", ""))

        image = meta.get("image", "")
        thumbnail = meta.get("thumbnail", "")
        source_url = meta.get("image_source_url", "")
        license_val = meta.get("image_license", "")
        commercial = meta.get("image_commercial_use", False)
        image_status = meta.get("image_status", "")
        image_source = meta.get("image_source", "")

        if not image:
            errors.append(f"[MISSING_IMAGE] {slug}")
        if not thumbnail:
            errors.append(f"[MISSING_THUMBNAIL] {slug}")

        if image in FALLBACK_PATHS:
            errors.append(f"[FALLBACK_IMAGE] {slug}: image is fallback path ({image})")
            posts_with_fallback_images += 1
        if thumbnail in FALLBACK_PATHS:
            errors.append(f"[FALLBACK_THUMBNAIL] {slug}: thumbnail is fallback path ({thumbnail})")
            posts_with_fallback_images += 1

        if image.startswith("/"):
            errors.append(f"[BAD_PATH] {slug}: image starts with '/' ({image})")
        if thumbnail and thumbnail.startswith("/"):
            errors.append(f"[BAD_PATH] {slug}: thumbnail starts with '/' ({thumbnail})")

        for field, val in [("image", image), ("thumbnail", thumbnail)]:
            if val and not val.startswith("http") and not val.startswith("/") and val not in FALLBACK_PATHS:
                local_path = os.path.join(os.getcwd(), "static", val)
                if not os.path.exists(local_path):
                    errors.append(f"[FILE_NOT_FOUND] {slug}: {field}={val}")
                elif os.path.getsize(local_path) < 5000:
                    errors.append(f"[TOO_SMALL] {slug}: {field}={val} ({os.path.getsize(local_path)} bytes)")
                elif has_placeholder_characteristics(local_path):
                    errors.append(f"[PLACEHOLDER_DETECTED] {slug}: {field}={val} appears to be solid-color placeholder")

        if not source_url:
            errors.append(f"[MISSING_SOURCE_URL] {slug}")
        if not license_val:
            errors.append(f"[MISSING_LICENSE] {slug}")
        if commercial is not True:
            errors.append(f"[COMMERCIAL_USE_NOT_TRUE] {slug}")
        if not image_source:
            errors.append(f"[MISSING_IMAGE_SOURCE] {slug}")

        if image_status == "needs_image":
            errors.append(f"[NEEDS_IMAGE] {slug}: post still needs a real image")
            posts_with_needs_image += 1

        if source_url:
            if source_url in seen_urls:
                if source_url not in whitelist:
                    prev = seen_urls[source_url]
                    errors.append(f"[DUPLICATE_URL] {slug} shares source_url with {prev}: {source_url}")
            else:
                seen_urls[source_url] = slug

    if errors:
        print(f"QA FAILED: {len(errors)} error(s)\n")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("QA PASSED: All posts have valid real images.")
        sys.exit(0)


if __name__ == "__main__":
    qa()
