#!/usr/bin/env python3
"""Register curated Pexels images for iOS/macOS 27 series posts into data/images.json."""

import hashlib
import json
import os
import re
import sys

import frontmatter

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "data", "images.json")
CONTENT = os.path.join(os.path.dirname(__file__), "..", "content", "posts")
SERIES_SLUGS = {
    "ios-27-co-gi-moi",
    "macos-27-co-gi-moi",
}


def photo_id_from_url(url):
    url = url.rstrip("/")
    match = re.search(r"-(\d+)/?$", url)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)/?$", url)
    return match.group(1) if match else ""


def main():
    with open(MANIFEST, encoding="utf-8") as handle:
        manifest = json.load(handle)

    by_slug = {entry["slug"]: entry for entry in manifest.get("posts", [])}
    added = 0

    for fname in sorted(os.listdir(CONTENT)):
        if not fname.endswith(".md"):
            continue
        post = frontmatter.load(os.path.join(CONTENT, fname))
        meta = post.metadata
        series = meta.get("series")
        if isinstance(series, list):
            series = series[0] if series else ""
        if series not in SERIES_SLUGS:
            continue
        slug = meta.get("slug", fname.replace(".md", ""))
        source_url = meta.get("image_source_url", "")
        if not source_url:
            print(f"SKIP {slug}: no image_source_url")
            continue
        photo_id = photo_id_from_url(source_url)
        if not photo_id:
            print(f"SKIP {slug}: cannot parse photo id from {source_url}")
            continue
        direct_url = (
            f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg"
            f"?auto=compress&cs=tinysrgb&w=1920"
        )
        entry = {
            "slug": slug,
            "title": meta.get("title", slug),
            "image_id": f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}",
            "source_platform": "Pexels",
            "source_url": source_url,
            "direct_url": direct_url,
            "creator": meta.get("image_creator", "") or "",
            "creator_url": meta.get("image_creator_url", "") or "",
            "license": "Pexels License",
            "commercial_use": True,
            "local_source_path": f"static/images/posts-src/{slug}.jpg",
            "output_path": f"static/images/posts/{slug}.webp",
            "watermark_text": "Source: Pexels",
            "provider_used": "manual-curate",
        }
        if entry["creator"]:
            entry["watermark_text"] = f"Source: Pexels / {entry['creator']}"
        by_slug[slug] = entry
        added += 1
        print(f"REGISTER {slug} -> photo {photo_id}")

    manifest["posts"] = sorted(by_slug.values(), key=lambda item: item["slug"])
    with open(MANIFEST, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Done. Registered/updated {added} series images.")


if __name__ == "__main__":
    main()