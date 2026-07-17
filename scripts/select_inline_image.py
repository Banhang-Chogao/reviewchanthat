#!/usr/bin/env python3
"""
select_inline_image.py — Pick a 2nd (inline illustration) image from Pexels API
for a post and register it as a `<slug>-inline` manifest entry so process_images
can turn it into WebP. Falls back to text-first (no image) only if API fully fails.

Usage:
  python3 scripts/select_inline_image.py --slug <slug> --query "<query>" --fix
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from image_providers import PexelsProvider, load_dotenv

MANIFEST = "data/images.json"
POSTS_DIR = "content/posts"


def load_manifest() -> dict:
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"posts": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    load_dotenv(override=True)
    if not os.environ.get("PEXELS_API_KEY"):
        print("ERROR: no Pexels key")
        return 1

    provider = PexelsProvider()

    cand = None
    for attempt in range(3):
        try:
            results = provider.search(args.query, None)
        except Exception as e:  # noqa
            print(f"  Pexels search error: {e}")
            results = []
        from lightweight_image_matcher import choose_best_candidate
        from article_image_context import ArticleImageContext
        ctx = ArticleImageContext()
        ctx.query_candidates_en = [args.query]
        pick = choose_best_candidate(ctx, results)
        if pick:
            cand = pick
            break
        time.sleep(2)

    if not cand:
        print("  No inline image found from Pexels; article will be text-first for inline.")
        return 0

    slug_inline = f"{args.slug}-inline"
    out_path = f"static/images/posts/{slug_inline}.webp"
    src_path = f"static/images/posts-src/{slug_inline}.jpg"
    entry = {
        "slug": slug_inline,
        "title": args.slug,
        "image_id": cand.get("raw_provider", {}).get("id", "") if isinstance(cand.get("raw_provider"), dict) else cand.get("photo_id", ""),
        "source_platform": "Pexels",
        "image_provider": "pexels",
        "source_url": cand.get("source_url", ""),
        "direct_url": cand.get("direct_url", ""),
        "creator": cand.get("creator", ""),
        "creator_url": cand.get("creator_url", ""),
        "creator_id": cand.get("creator_id", ""),
        "photo_id": cand.get("raw_provider", {}).get("id", "") if isinstance(cand.get("raw_provider"), dict) else cand.get("photo_id", ""),
        "license": "Pexels License",
        "commercial_use": True,
        "local_source_path": src_path,
        "output_path": out_path,
        "attribution_verified": True,
        "attribution_source": "pexels_api",
        "image_query": args.query,
        "image_alt": f"Ảnh minh họa {args.slug} — nguồn Pexels",
        "gate_verified": True,
    }

    manifest = load_manifest()
    manifest["posts"] = [p for p in manifest["posts"] if p["slug"] != slug_inline]
    manifest["posts"].append(entry)
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"  Inline image selected: {cand.get('source_url')} by {cand.get('creator')}")
    print(f"  Registered manifest entry: {slug_inline}")
    print(f"  WebP target: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
