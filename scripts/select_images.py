#!/usr/bin/env python3
"""
select_images.py — Generate self-hosted editorial images for all blog posts.

Replaces the old provider-cascade (Pexels/Pixabay/Unsplash/Freepik) pipeline.
Every post gets:
  1. Hero image (1200x630) from abstract topic-based generator
  2. Inline illustrations (800x600) for each H2 section in body

No external API calls, no brand logos, no fake screenshots, no fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import frontmatter

from generate_hero_image import (
    generate_for_post,
    get_image_meta,
    detect_style,
)

CONTENT_DIR = "content/posts"
REGISTRY_PATH = "data/generated-images.json"
SELECTION_REPORT_PATH = "data/image-selection-report.json"


def load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"generated_at": "", "items": {}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate self-hosted editorial images for all posts")
    parser.add_argument("--post", type=str, help="Single post path (e.g. content/posts/iphone-...md)")
    parser.add_argument("--all", action="store_true", help="Process all posts in content/posts/")
    parser.add_argument("--force", action="store_true", help="Regenerate even if image exists")
    parser.add_argument("--skip-inline", action="store_true", help="Skip inline illustration generation")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

    posts_to_process = []

    if args.post:
        if not os.path.exists(args.post):
            print(f"ERROR: Post not found: {args.post}")
            return 1
        posts_to_process = [args.post]
    elif args.all:
        if not os.path.isdir(CONTENT_DIR):
            print(f"ERROR: {CONTENT_DIR} not found")
            return 1
        posts_to_process = sorted(
            os.path.join(CONTENT_DIR, f) for f in os.listdir(CONTENT_DIR) if f.endswith(".md")
        )
    else:
        print("ERROR: Use --post <path> or --all")
        return 1

    print(f"=== Self-Hosted Image Generation ===\n")

    report = {
        "generated_at": None,
        "processed": 0,
        "hero_generated": 0,
        "inline_generated": 0,
        "skipped_hero": 0,
        "inline_skipped": 0,
        "errors": [],
        "posts": [],
    }

    for fpath in posts_to_process:
        try:
            post = frontmatter.load(fpath)
        except Exception as e:
            print(f"ERROR reading {fpath}: {e}")
            report["errors"].append({"file": fpath, "reason": str(e)})
            continue

        meta = post.metadata
        slug = meta.get("slug", os.path.basename(fpath).replace(".md", ""))
        title = meta.get("title", slug)
        body = post.content or ""
        category = meta.get("categories", "")
        if isinstance(category, list):
            category = category[0] if category else ""
        tags = list(meta.get("tags", []) or [])

        print(f"  [{slug}] {title}")

        if args.dry_run:
            style_key = detect_style(category, tags, title)
            from generate_hero_image import extract_headings
            headings = extract_headings(body)
            print(f"    Style: {style_key}")
            print(f"    H2 sections: {len(headings)}")
            print(f"    Would generate: 1 hero + {len(headings)} inline")
            report["processed"] += 1
            continue

        imgs = generate_for_post(slug, title, body, category, tags, force=args.force)

        if imgs["hero"]:
            write_frontmatter(fpath, imgs["frontmatter_hero"])
        else:
            if meta.get("image") and meta.get("image_owner") != "self":
                pass

        if not args.skip_inline and imgs["frontmatter_inline"]:
            inline_meta = {
                "inline_images": [x["image"] for x in imgs["frontmatter_inline"]],
                "inline_image_count": len(imgs["frontmatter_inline"]),
            }
            if imgs["inline"]:
                inline_meta["inline_illustrations"] = [
                    {"heading": x["heading"], "image": x["path"]} for x in imgs["inline"]
                ]
            write_frontmatter(fpath, inline_meta)

        post_result = {
            "slug": slug,
            "title": title,
            "hero": "generated" if imgs["hero"] else "skipped",
            "inline_count": len(imgs.get("inline", [])),
        }
        report["posts"].append(post_result)
        report["processed"] += 1
        if imgs["hero"]:
            report["hero_generated"] += 1
        else:
            report["skipped_hero"] += 1
        report["inline_generated"] += len(imgs.get("inline", []))
        report["inline_skipped"] += len(imgs.get("inline", [])) if not imgs.get("inline") else 0

        print()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    report["generated_at"] = now

    os.makedirs("data", exist_ok=True)
    with open(SELECTION_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"=== Report ===")
    print(f"  Processed: {report['processed']}")
    print(f"  Hero generated: {report['hero_generated']} | skipped: {report['skipped_hero']}")
    print(f"  Inline generated: {report['inline_generated']}")
    if report["errors"]:
        print(f"  Errors: {len(report['errors'])}")
        for e in report["errors"]:
            print(f"    - {e['file']}: {e['reason']}")
    print(f"  Report: {SELECTION_REPORT_PATH}")

    return 0 if not report["errors"] else 1


def write_frontmatter(post_path: str, fields: dict) -> None:
    try:
        post = frontmatter.load(post_path)
        meta = post.metadata
        stale = ["image_reject_reason", "image_attribution_checked_at", "image_query",
                  "image_semantic_score", "image_color_score", "image_total_score",
                  "image_creator_id"]
        for k in stale:
            meta.pop(k, None)
        for k, v in fields.items():
            meta[k] = v
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"    WARNING: Could not write frontmatter for {post_path}: {e}")


if __name__ == "__main__":
    raise SystemExit(main())