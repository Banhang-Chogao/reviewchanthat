"""
scripts/qa_blog.py
Quality assurance checks for the blog.
Fails on: missing images, broken paths, missing metadata, duplicates, etc.
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


def load_whitelist():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH) as f:
            return set(json.load(f).get("whitelisted_urls", []))
    return set()


def qa():
    errors = []
    whitelist = load_whitelist()
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    if not os.path.exists(posts_dir):
        print(f"FAIL: {CONTENT_DIR} not found")
        sys.exit(1)

    seen_urls = {}

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

        # 1. Check image
        image = meta.get("image", "")
        if not image:
            errors.append(f"[MISSING_IMAGE] {slug}")

        # 2. Check thumbnail
        thumbnail = meta.get("thumbnail", "")
        if not thumbnail:
            errors.append(f"[MISSING_THUMBNAIL] {slug}")

        # 3. Check image path starts with / (bad for GitHub Pages)
        if image.startswith("/"):
            errors.append(f"[BAD_PATH] {slug}: image starts with '/' ({image})")
        if thumbnail and thumbnail.startswith("/"):
            errors.append(f"[BAD_PATH] {slug}: thumbnail starts with '/' ({thumbnail})")

        # 4. Check local file exists
        for field, val in [("image", image), ("thumbnail", thumbnail)]:
            if val and not val.startswith("http") and not val.startswith("/"):
                local_path = os.path.join(os.getcwd(), "static", val)
                if not os.path.exists(local_path):
                    errors.append(f"[FILE_NOT_FOUND] {slug}: {field}={val}")

        # 5. Check image_source_url
        source_url = meta.get("image_source_url", "")
        if not source_url:
            errors.append(f"[MISSING_SOURCE_URL] {slug}")

        # 6. Check image_license
        license_val = meta.get("image_license", "")
        if not license_val:
            errors.append(f"[MISSING_LICENSE] {slug}")

        # 7. Check commercial_use
        commercial = meta.get("image_commercial_use", False)
        if commercial is not True:
            errors.append(f"[COMMERCIAL_USE_NOT_TRUE] {slug}")

        # 8. Track duplicates
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
        print("QA PASSED: All posts have valid image metadata.")
        sys.exit(0)


if __name__ == "__main__":
    qa()
