"""
scripts/image_dedupe.py
Strict image deduplication check.
- Duplicate source_url -> error (unless whitelisted)
- Duplicate local output file -> error
- Perceptual similarity warning
- Whitelist in data/image-dedupe-whitelist.json
"""

import os
import json
import sys
from collections import defaultdict

CONTENT_DIR = "content/posts"
POSTS_DIR = "static/images/posts"
MANIFEST_PATH = "data/images.json"
REPORT_PATH = "data/image-dedupe-report.json"
WHITELIST_PATH = "data/image-dedupe-whitelist.json"


def load_whitelist():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH) as f:
            return set(json.load(f).get("whitelisted_urls", []))
    return set()


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"posts": []}


def get_perceptual_hash(image_path):
    try:
        from PIL import Image
        import imagehash
        img = Image.open(image_path)
        return str(imagehash.average_hash(img))
    except Exception:
        return None


def dedupe():
    print("=== Image Deduplication Check ===")
    whitelist = load_whitelist()
    manifest = load_manifest()
    errors = []

    import frontmatter
    source_urls = defaultdict(list)
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        try:
            post = frontmatter.load(fpath)
            slug = post.metadata.get("slug", fname.replace(".md", ""))
            url = post.metadata.get("image_source_url", "")
            if url:
                source_urls[url].append(slug)
        except Exception:
            continue

    url_dupes = {}
    for url, slugs in source_urls.items():
        if len(slugs) > 1:
            if url not in whitelist:
                url_dupes[url] = slugs
                errors.append(f"DUPLICATE source_url: {url} used by {slugs}")

    output_usage = defaultdict(list)
    for entry in manifest.get("posts", []):
        out_path = entry.get("output_path", "")
        if out_path:
            output_usage[out_path].append(entry["slug"])

    file_dupes = {path: slugs for path, slugs in output_usage.items() if len(slugs) > 1}
    for path, slugs in file_dupes.items():
        errors.append(f"DUPLICATE output file: {path} used by {slugs}")

    perceptual_dupes = []
    processed_files = []
    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".webp") or fname == "fallback.webp":
            continue
        fpath = os.path.join(POSTS_DIR, fname)
        phash = get_perceptual_hash(fpath)
        if phash:
            for pf, pv in processed_files:
                if phash == pv:
                    perceptual_dupes.append((pf, fpath, phash))
            processed_files.append((fpath, phash))

    for a, b, h in perceptual_dupes:
        print(f"  WARNING: Perceptual duplicate: {a} <-> {b} (hash: {h})")

    report = {
        "total_source_urls": len(source_urls),
        "duplicate_source_urls": {url: slugs for url, slugs in url_dupes.items()},
        "duplicate_output_files": dict(file_dupes),
        "perceptual_duplicates": [(a, b, h) for a, b, h in perceptual_dupes],
        "whitelisted_urls": list(whitelist),
        "errors": errors,
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReport: {REPORT_PATH}")
    print(f"  Duplicate source URLs: {len(url_dupes)}")
    for url, slugs in url_dupes.items():
        print(f"    {url}: {slugs}")
    print(f"  Duplicate output files: {len(file_dupes)}")
    print(f"  Perceptual duplicates: {len(perceptual_dupes)}")

    if errors:
        for err in errors:
            print(f"  ERROR: {err}")
        sys.exit(1)

    print("  No duplicate errors found.")
    return report


if __name__ == "__main__":
    dedupe()
