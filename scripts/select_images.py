#!/usr/bin/env python3
"""
select_images.py — Stock API image selection (Pexels + Pixabay primary).

Policy:
  1. Load permanent keys from repo `.env` (PEXELS_API_KEY, PIXABAY_API_KEY)
  2. Try API providers: Pexels → Pixabay only
  3. Do NOT auto-draw / self-generate placeholder art
  4. Lightweight matching: no heavy compliance scoring that blocks deploy
  5. Strict attribution: never fake creator names
  6. Write data/images.json for process_images.py

Usage:
  python scripts/select_images.py --post content/posts/example.md --fix
  python scripts/select_images.py --all --fix --only-missing-or-bad
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import frontmatter

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

from article_image_context import ArticleImageContext, build_context_from_post
from creator_policy import clean_text, sanitize_candidate, is_blocked_creator
from fetch_relevant_image import select_best_image, manifest_entry_from_selection

CONTENT_DIR = "content/posts"
IMAGES_MANIFEST_PATH = "data/images.json"
SELECTION_REPORT_PATH = "data/image-selection-report.json"


def load_images_manifest() -> dict:
    """Load existing images manifest."""
    if os.path.exists(IMAGES_MANIFEST_PATH):
        try:
            with open(IMAGES_MANIFEST_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"posts": [], "generated_at": ""}


def try_api_image(
    post: dict[str, Any],
    body: str,
    used_urls: set[str],
    providers: list[Any] | None = None,
) -> dict[str, Any] | None:
    """Try to select best API image. Returns manifest entry or None."""
    try:
        result = select_best_image(post, body, providers=providers, used_urls=used_urls)
        if not result or not result.get("candidate"):
            return None
        entry = manifest_entry_from_selection(post.get("slug", ""), post.get("title", ""), result)
        return entry
    except Exception as e:
        print(f"    API selection error: {e}")
        return None


def select_image_for_post(
    post: dict[str, Any],
    body: str,
    used_urls: set[str],
    force_generated: bool = False,
    api_first: bool = True,
    allow_self_generated: bool = False,
    providers: list[Any] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """
    Select best stock API image for post.
    Self-generated art is disabled by policy.
    Returns (manifest_entry, reason).
    """
    slug = post.get("slug", "")
    if force_generated:
        return None, "self_generated_disabled_by_policy"

    # Default path: stock APIs only (Pexels / Pixabay)
    api_entry = try_api_image(post, body, used_urls, providers=providers)
    if api_entry:
        return api_entry, f"api_selected:{api_entry.get('source_platform', 'unknown')}"

    if allow_self_generated:
        return None, "self_generated_disabled_by_policy"

    return None, "api_failed_no_stock_image"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select images for posts from Pexels/Pixabay APIs (no auto-draw)"
    )
    parser.add_argument("--post", type=str, help="Single post path (e.g. content/posts/iphone-...md)")
    parser.add_argument("--all", action="store_true", help="Process all posts in content/posts/")
    parser.add_argument("--fix", action="store_true", help="Write frontmatter and manifest")
    parser.add_argument("--api-first", action="store_true", default=True, help="Try API images first (default)")
    parser.add_argument(
        "--force-generated",
        action="store_true",
        help="Disabled by policy: article images must come from Pexels/Pixabay APIs",
    )
    parser.add_argument(
        "--allow-self-generated",
        action="store_true",
        help="Disabled by policy: article images must come from Pexels/Pixabay APIs",
    )
    parser.add_argument("--only-missing-or-bad", action="store_true", help="Only process posts missing images")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

    if args.force_generated or args.allow_self_generated:
        print("ERROR: self-generated article images are disabled; use Pexels/Pixabay APIs.")
        return 1

    # Ensure permanent API keys from .env are available (override empty shell)
    from image_providers import load_dotenv
    load_dotenv(override=True)
    pexels = bool(os.environ.get("PEXELS_API_KEY"))
    pixabay = bool(os.environ.get("PIXABAY_API_KEY"))
    print(f"API keys: PEXELS={'yes' if pexels else 'NO'} PIXABAY={'yes' if pixabay else 'NO'}")
    if not pexels and not pixabay:
        print("ERROR: Set PEXELS_API_KEY and/or PIXABAY_API_KEY in repo .env")
        return 1

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

    print("=== Image Selection (Pexels + Pixabay API; no auto-draw) ===\n")
    allow_self = bool(args.allow_self_generated or args.force_generated)

    report = {
        "generated_at": None,
        "processed": 0,
        "api_selected": 0,
        "self_generated": 0,
        "skipped": 0,
        "errors": [],
        "posts": [],
    }

    manifest = load_images_manifest()
    used_urls: set[str] = {entry.get("source_url", "") for entry in manifest.get("posts", [])}
    existing_slugs = {entry.get("slug", "") for entry in manifest.get("posts", [])}

    for fpath in posts_to_process:
        try:
            text = open(fpath, encoding="utf-8").read()
            if text.lstrip().startswith("+++"):
                m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", text, re.S)
                if not m:
                    raise ValueError("invalid TOML front matter (+++)")
                if tomllib is None:
                    raise ValueError("tomllib unavailable; cannot parse TOML front matter")
                meta = dict(tomllib.loads(m.group(1)))
                body = m.group(2) or ""
            else:
                post_file = frontmatter.load(fpath)
                meta = dict(post_file.metadata or {})
                body = post_file.content or ""
        except Exception as e:
            print(f"ERROR reading {fpath}: {e}")
            report["errors"].append({"file": fpath, "reason": str(e)})
            continue

        slug = meta.get("slug") or os.path.basename(fpath).replace(".md", "")
        title = meta.get("title") or slug
        meta["slug"] = slug
        meta["title"] = title

        print(f"  [{slug}] {title}")

        # Filter by --only-missing-or-bad
        if args.only_missing_or_bad:
            img = meta.get("image", "")
            if img and "needs_api_image" not in img and "needs_image" not in img \
               and img != "needs_api_image" and slug in existing_slugs \
               and meta.get("image_owner") != "self":
                print(f"    Skipped (image already set)")
                report["skipped"] += 1
                continue

        if args.dry_run:
            entry, reason = select_image_for_post(
                meta, body, used_urls, args.force_generated, args.api_first, allow_self
            )
            if entry:
                source = entry.get("source_platform", "unknown")
                print(f"    Would select: {source} ({reason})")
            else:
                print(f"    Would fail to select image ({reason})")
            report["processed"] += 1
            continue

        # Select image (Pexels/Pixabay stock APIs only)
        entry, reason = select_image_for_post(
            meta, body, used_urls, args.force_generated, args.api_first, allow_self
        )
        if not entry:
            print(f"    FAIL: {reason}")
            report["errors"].append({"slug": slug, "reason": reason})
            report["processed"] += 1
            continue

        if args.fix:
            # Update manifest
            if slug in existing_slugs:
                manifest["posts"] = [e for e in manifest["posts"] if e.get("slug") != slug]
            manifest["posts"].append(entry)
            used_urls.add(entry.get("source_url", ""))

            # Update post frontmatter
            write_image_frontmatter(fpath, entry)

        source = entry.get("source_platform", "unknown")
        if source == "self":
            report["self_generated"] += 1
        elif source != "self-generated":
            report["api_selected"] += 1
        else:
            report["self_generated"] += 1

        report["posts"].append({
            "slug": slug,
            "title": title,
            "source": source,
            "reason": reason,
        })
        report["processed"] += 1
        print(f"    Selected: {source} ({reason})")
        print()

    if args.fix:
        from datetime import datetime, timezone
        manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
        os.makedirs("data", exist_ok=True)
        with open(IMAGES_MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"\nManifest saved: {IMAGES_MANIFEST_PATH}")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    report["generated_at"] = now

    os.makedirs("data", exist_ok=True)
    with open(SELECTION_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"=== Report ===")
    print(f"  Processed: {report['processed']}")
    print(f"  API selected: {report['api_selected']}")
    print(f"  Self-generated: {report['self_generated']}")
    print(f"  Skipped: {report['skipped']}")
    if report["errors"]:
        print(f"  Errors: {len(report['errors'])}")
        for e in report["errors"]:
            print(f"    - {e.get('slug', e.get('file'))}: {e['reason']}")
    print(f"  Report: {SELECTION_REPORT_PATH}")
    print(f"  Manifest: {IMAGES_MANIFEST_PATH}")

    return 0 if not report["errors"] else 1 if args.fix else 0


def write_image_frontmatter(post_path: str, entry: dict[str, Any]) -> None:
    """Update post frontmatter with selected image metadata."""
    try:
        from lib.toml_util import has_toml_fm, read_fm, update_post_file as _toml_update

        text = open(post_path, encoding="utf-8").read()

        stale = [
            "image_reject_reason", "image_attribution_checked_at", "image_query",
            "image_semantic_score", "image_color_score", "image_total_score",
            "image_attribution_error",
        ]

        _out = entry.get("output_path", "").lstrip("/")
        if _out.startswith("static/"):
            _out = _out[len("static/"):]
        updates = {
            "image": _out,
            "thumbnail": _out,
            "image_source": entry.get("source", entry.get("source_platform", "")),
            "image_source_url": entry.get("source_url", ""),
            "image_provider": entry.get("image_provider", ""),
            "image_license": entry.get("license", ""),
            "image_license_url": entry.get("license_url", ""),
            "image_commercial_use": entry.get("commercial_use", True),
            "image_owner": entry.get("image_owner", "external"),
            "image_creator": entry.get("creator", ""),
            "image_creator_url": entry.get("creator_url", ""),
            "image_creator_id": entry.get("creator_id", ""),
            "image_attribution_verified": entry.get("attribution_verified", False),
            "image_attribution_source": entry.get("attribution_source", "not_found"),
            "image_status": "verified",
        }

        if has_toml_fm(text):
            from lib.toml_util import remove_key as _rm, set_field as _set

            parts = read_fm(text)
            if not parts:
                print(f"    WARNING: Invalid TOML frontmatter in {post_path}")
                return
            fm_text = parts[1]
            for k in stale:
                fm_text = _rm(fm_text, k)
            for k, v in updates.items():
                fm_text = _set(fm_text, k, v)
            new_text = parts[0] + fm_text.strip() + "\n+++" + parts[2]
            with open(post_path, "w", encoding="utf-8") as f:
                f.write(new_text)
        else:
            post = frontmatter.load(post_path)
            meta = post.metadata
            for k in stale:
                meta.pop(k, None)
            for k, v in updates.items():
                meta[k] = v
            with open(post_path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"    WARNING: Could not write frontmatter for {post_path}: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
