#!/usr/bin/env python3
"""
select_images.py — Stock API image selection (Pexels + Pixabay primary).

Policy:
  1. Load permanent keys from repo `.env` (PEXELS_API_KEY, PIXABAY_API_KEY)
  2. Try API providers: Pexels → Pixabay → (optional Unsplash/Freepik if keyed)
  3. Do NOT auto-draw / self-generate placeholder art by default
  4. Lightweight matching: no heavy compliance scoring that blocks deploy
  5. Strict attribution: never fake creator names
  6. Write data/images.json for process_images.py

Usage:
  python scripts/select_images.py --post content/posts/example.md --fix
  python scripts/select_images.py --all --fix --only-missing-or-bad
"""

from __future__ import annotations

import argparse
import hashlib
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
SITE_BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"


def load_images_manifest() -> dict:
    """Load existing images manifest."""
    if os.path.exists(IMAGES_MANIFEST_PATH):
        try:
            with open(IMAGES_MANIFEST_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"posts": [], "generated_at": ""}


def try_api_image(post: dict[str, Any], body: str, used_urls: set[str]) -> dict[str, Any] | None:
    """Try to select best API image. Returns manifest entry or None."""
    try:
        result = select_best_image(post, body, used_urls=used_urls)
        if not result or not result.get("candidate"):
            return None
        entry = manifest_entry_from_selection(post.get("slug", ""), post.get("title", ""), result)
        return entry
    except Exception as e:
        print(f"    API selection error: {e}")
        return None


def check_self_generated_image(slug: str, title: str) -> dict[str, Any] | None:
    """Check if self-generated image already exists in assets."""
    candidate_paths = [
        f"assets/generated-images/{slug}.png",
        f"assets/generated-images/{slug}.jpg",
        f"assets/generated-images/{slug}.webp",
    ]

    existing_path = None
    for path in candidate_paths:
        if os.path.exists(path):
            existing_path = path
            break

    if not existing_path:
        return None

    return {
        "slug": slug,
        "title": title,
        "image_id": f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}",
        "source_platform": "self",
        "image_provider": "self-generated",
        "source_url": f"{SITE_BASE_URL}/",
        "source": "self",
        "direct_url": "",
        "creator": "Review Chân Thật",
        "creator_url": f"{SITE_BASE_URL}/",
        "creator_id": "review-chan-that-generated",
        "license": "Original self-hosted editorial illustration by Review Chân Thật",
        "license_url": f"{SITE_BASE_URL}/branding-ci/",
        "commercial_use": True,
        "image_owner": "self",
        "local_source_path": existing_path,
        "output_path": f"static/images/posts/{slug}.webp",
        "watermark_text": "Source: Review Chân Thật",
        "provider_used": "self-generated",
        "attribution_verified": True,
        "attribution_source": "self_generated",
        "image_generation_method": "context_aware_ai_assisted",
    }


def select_image_for_post(
    post: dict[str, Any],
    body: str,
    used_urls: set[str],
    force_generated: bool = False,
    api_first: bool = True,
    allow_self_generated: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    """
    Select best stock API image for post.
    Self-generated art is OFF unless allow_self_generated/force_generated.
    Returns (manifest_entry, reason).
    """
    slug = post.get("slug", "")
    title = post.get("title", "")

    if force_generated:
        entry = check_self_generated_image(slug, title)
        if entry:
            return entry, "force_generated"
        return None, "force_generated_but_not_found"

    # Default path: stock APIs only (Pexels / Pixabay / optional others)
    api_entry = try_api_image(post, body, used_urls)
    if api_entry:
        return api_entry, f"api_selected:{api_entry.get('source_platform', 'unknown')}"

    if allow_self_generated:
        fallback_entry = check_self_generated_image(slug, title)
        if fallback_entry:
            return fallback_entry, "api_failed_fallback_used"
        return None, "api_failed_no_fallback"

    return None, "api_failed_no_stock_image"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select images for posts from Pexels/Pixabay APIs (no auto-draw by default)"
    )
    parser.add_argument("--post", type=str, help="Single post path (e.g. content/posts/iphone-...md)")
    parser.add_argument("--all", action="store_true", help="Process all posts in content/posts/")
    parser.add_argument("--fix", action="store_true", help="Write frontmatter and manifest")
    parser.add_argument("--api-first", action="store_true", default=True, help="Try API images first (default)")
    parser.add_argument(
        "--force-generated",
        action="store_true",
        help="DEPRECATED emergency: only use existing self-generated asset if present",
    )
    parser.add_argument(
        "--allow-self-generated",
        action="store_true",
        help="Allow existing self-generated asset as last resort (off by default)",
    )
    parser.add_argument("--only-missing-or-bad", action="store_true", help="Only process posts missing images")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

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
            img_rel = str(meta.get("image") or "").lstrip("/")
            if img_rel.startswith("static/"):
                img_rel = img_rel[len("static/") :]
            candidates = [
                os.path.join("static", img_rel) if img_rel else "",
                os.path.join("static/images/posts", f"{slug}.webp"),
            ]
            file_ok = any(p and os.path.isfile(p) and os.path.getsize(p) > 1000 for p in candidates)
            status = str(meta.get("image_status") or "")
            needs = (
                not meta.get("image")
                or not file_ok
                or status in {"needs_review", "needs_image", "needs_replace", "missing"}
                or meta.get("image_owner") == "self"
            )
            if not needs:
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

        # Select image (stock APIs only unless --allow-self-generated)
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


def _toml_quote(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


def _remove_toml_keys(fm: str, keys: list[str]) -> str:
    lines = fm.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    key_re = re.compile(r"^(" + "|".join(re.escape(k) for k in keys) + r")\s*=")
    while i < len(lines):
        if key_re.match(lines[i]):
            line = lines[i]
            i += 1
            if '"""' in line and line.count('"""') == 1:
                while i < len(lines) and '"""' not in lines[i]:
                    i += 1
                if i < len(lines):
                    i += 1
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def write_image_frontmatter_toml(post_path: str, fields: dict[str, Any]) -> None:
    """Surgically update image_* keys in TOML (+++) front matter without converting to YAML."""
    text = open(post_path, encoding="utf-8").read()
    m = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+)(\r?\n?)(.*)$", text, re.S)
    if not m:
        raise ValueError("invalid TOML front matter")
    prefix, fm, close, nl, body = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    keys = list(fields.keys())
    fm = _remove_toml_keys(fm, keys)
    block = "\n".join(f"{k} = {_toml_quote(v)}" for k, v in fields.items())
    table_m = re.search(r"(?m)^\[", fm)
    if table_m:
        idx = table_m.start()
        head = fm[:idx].rstrip("\n")
        tail = fm[idx:]
        fm = head + "\n" + block + "\n\n" + tail.lstrip("\n")
    else:
        fm = fm.rstrip("\n") + "\n" + block + "\n"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(f"{prefix}{fm}{close}{nl or chr(10)}{body}")


def write_image_frontmatter(post_path: str, entry: dict[str, Any]) -> None:
    """Update post frontmatter with selected image metadata.

    Hugo uses paths like images/posts/<slug>.webp (no static/ prefix).
    TOML posts must stay TOML — never run frontmatter.dumps on them.
    """
    try:
        out = (entry.get("output_path") or "").lstrip("/")
        if out.startswith("static/"):
            out = out[len("static/") :]
        if not out:
            out = f"images/posts/{entry.get('slug', 'post')}.webp"

        fields = {
            "image": out,
            "thumbnail": out,
            "image_source": entry.get("source", entry.get("source_platform", "")),
            "image_source_url": entry.get("source_url", ""),
            "image_provider": entry.get("image_provider", ""),
            "image_license": entry.get("license", ""),
            "image_license_url": entry.get("license_url", "") or "",
            "image_commercial_use": bool(entry.get("commercial_use", True)),
            "image_owner": entry.get("image_owner", "external"),
            "image_creator": entry.get("creator", "") or "",
            "image_creator_url": entry.get("creator_url", "") or "",
            "image_creator_id": entry.get("creator_id", "") or "",
            "image_attribution_verified": bool(entry.get("attribution_verified", False)),
            "image_attribution_source": entry.get("attribution_source", "not_found"),
            "image_status": "verified",
        }

        with open(post_path, encoding="utf-8") as fh:
            head = fh.read(8)
        if head.lstrip().startswith("+++"):
            write_image_frontmatter_toml(post_path, fields)
            return

        post = frontmatter.load(post_path)
        meta = post.metadata

        stale = [
            "image_reject_reason", "image_attribution_checked_at", "image_query",
            "image_semantic_score", "image_color_score", "image_total_score",
            "image_attribution_error",
        ]
        for k in stale:
            meta.pop(k, None)

        meta.update(fields)

        with open(post_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"    WARNING: Could not write frontmatter for {post_path}: {e}")


if __name__ == "__main__":
    raise SystemExit(main())