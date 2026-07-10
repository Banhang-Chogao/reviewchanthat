"""
scripts/qa_blog.py
Quality assurance checks for the blog.
Hard failures on: fallback images, missing images, missing metadata, duplicates, etc.
"""

import argparse
import os
import re
import subprocess
import sys
import json
import frontmatter

from creator_policy import is_blocked_creator, is_generated_creator

CONTENT_DIR = "content/posts"
PUBLIC_DIR = "public"
IMAGES_POSTS_DIR = "static/images/posts"
AUDIT_REPORT_PATH = "data/image-audit-report.json"
DEDUPE_REPORT_PATH = "data/image-dedupe-report.json"
WHITELIST_PATH = "data/dupe-whitelist.json"
IMAGES_MANIFEST_PATH = "data/images.json"

FALLBACK_PATHS = {"images/posts/fallback.webp", "images/fallback.webp"}
IMAGE_FIX_STATUSES = {"needs_image", "needs_review"}
IMAGE_FIX_PROVIDERS = {"Pexels", "Pixabay"}

def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def load_manifest_by_slug():
    if not os.path.exists(IMAGES_MANIFEST_PATH):
        return {}
    with open(IMAGES_MANIFEST_PATH) as f:
        manifest = json.load(f)
    return {
        clean_text(entry.get("slug")): entry
        for entry in manifest.get("posts", [])
        if clean_text(entry.get("slug"))
    }


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
        pixels = list(img.get_flattened_data())
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


def ai_summary_item_issues(items):
    issues = []
    for index, item in enumerate(items or []):
        if not isinstance(item, str):
            issues.append((index, type(item).__name__))
        elif "map[" in item:
            issues.append((index, "contains map["))
    return issues


def scan_public_ai_summary_map_literals(public_dir):
    hits = []
    if not os.path.isdir(public_dir):
        return hits
    pattern = re.compile(r'<ul[^>]*\bai-summary__list\b[^>]*>.*?</ul>', re.DOTALL)
    for dirpath, _, filenames in os.walk(public_dir):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            for match in pattern.finditer(content):
                if "map[" in match.group(0):
                    hits.append(fpath)
                    break
    return hits


def read_post_meta_body(fpath):
    """Read either TOML or YAML frontmatter without normalizing the file."""
    text = open(fpath, encoding="utf-8").read()
    if text.lstrip().startswith("+++"):
        import tomllib

        match = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", text, re.S)
        if not match:
            raise ValueError("invalid TOML frontmatter")
        return dict(tomllib.loads(match.group(1))), match.group(2) or ""

    post = frontmatter.loads(text)
    return dict(post.metadata or {}), post.content or ""


def post_slug(fname, meta):
    return clean_text(meta.get("slug")) or fname.replace(".md", "")


def post_local_image_missing(image):
    if not image or image.startswith("http") or image.startswith("/"):
        return False
    local_path = os.path.join(os.getcwd(), "static", image)
    return not os.path.exists(local_path)


def post_needs_image_fix(meta):
    image = clean_text(meta.get("image", ""))
    thumbnail = clean_text(meta.get("thumbnail", ""))
    image_status = clean_text(meta.get("image_status", ""))
    return (
        not image
        or not thumbnail
        or image in FALLBACK_PATHS
        or thumbnail in FALLBACK_PATHS
        or image_status in IMAGE_FIX_STATUSES
        or post_local_image_missing(image)
        or post_local_image_missing(thumbnail)
    )


def changed_post_slugs_from_files(changed_files):
    slugs = set()
    for path in changed_files:
        if path.startswith("content/posts/") and path.endswith(".md"):
            slugs.add(os.path.splitext(os.path.basename(path))[0])
    return slugs


def load_scope_slugs(scope_report):
    if not scope_report:
        return None
    if not os.path.exists(scope_report):
        raise FileNotFoundError(f"scope report not found: {scope_report}")
    with open(scope_report, encoding="utf-8") as fh:
        report = json.load(fh)
    return set(report.get("changed_posts") or [])


def load_changed_slugs_from_git(base, head):
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{head}"],
            cwd=os.getcwd(),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        print(f"FAIL: git diff failed while determining blog QA scope: {exc}")
        return set()
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=os.getcwd(),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    if result.returncode != 0:
        print(result.stderr.strip() or "FAIL: git diff failed while determining blog QA scope")
        return set()
    return changed_post_slugs_from_files(result.stdout.splitlines())


def load_post_slugs_from_paths(paths):
    if paths is None:
        return None
    slugs = set()
    for path in paths:
        fpath = path
        if not os.path.isabs(fpath):
            fpath = os.path.join(os.getcwd(), fpath)
        if not os.path.exists(fpath):
            print(f"FAIL: post path not found: {path}")
            continue
        try:
            meta, _ = read_post_meta_body(fpath)
        except Exception:
            meta = {}
        slugs.add(os.path.splitext(os.path.basename(fpath))[0])
        slugs.add(post_slug(os.path.basename(fpath), meta))
    return slugs


def target_matches(slug, fname, target_slugs):
    if target_slugs is None:
        return True
    return slug in target_slugs or fname.replace(".md", "") in target_slugs


def seed_seen_urls_for_unscoped_posts(posts_dir, target_slugs):
    seen = {}
    if target_slugs is None:
        return seen
    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        if fname.replace(".md", "") in target_slugs:
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            meta, _ = read_post_meta_body(fpath)
        except Exception:
            continue
        slug = post_slug(fname, meta)
        if target_matches(slug, fname, target_slugs):
            continue
        source_url = clean_text(meta.get("image_source_url", ""))
        if source_url:
            seen.setdefault(source_url, slug)
    return seen


def remediable_post_paths(target_slugs):
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    paths = []
    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        if target_slugs is not None and fname.replace(".md", "") not in target_slugs:
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            meta, _ = read_post_meta_body(fpath)
        except Exception:
            continue
        slug = post_slug(fname, meta)
        if not target_matches(slug, fname, target_slugs):
            continue
        if post_needs_image_fix(meta):
            paths.append(fpath)
    return paths


def save_manifest_entry(entry):
    manifest = load_manifest_by_slug()
    by_slug = dict(manifest)
    by_slug[entry["slug"]] = entry
    payload = {
        "posts": sorted(by_slug.values(), key=lambda item: item.get("slug", "")),
    }
    if os.path.exists(IMAGES_MANIFEST_PATH):
        try:
            with open(IMAGES_MANIFEST_PATH, encoding="utf-8") as fh:
                existing = json.load(fh)
            for key, value in existing.items():
                if key != "posts":
                    payload[key] = value
        except (json.JSONDecodeError, OSError):
            pass
    from datetime import datetime, timezone

    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(IMAGES_MANIFEST_PATH), exist_ok=True)
    with open(IMAGES_MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def process_selected_manifest_entry(entry):
    from creator_policy import attribution_text, sanitize_creator_pair
    from image_gate_policy import gate_meta_from_entry, resolve_image_status
    from process_images import (
        download_image,
        has_placeholder_characteristics,
        process_image,
        resolve_image_attribution,
        update_post_frontmatter,
    )

    slug = entry["slug"]
    provider = clean_text(entry.get("source_platform", ""))
    if provider not in IMAGE_FIX_PROVIDERS:
        print(f"    FAIL: selected disallowed provider for {slug}: {provider}")
        return False

    direct_url = clean_text(entry.get("direct_url", ""))
    if not direct_url:
        print(f"    FAIL: selected image has no direct_url for {slug}")
        return False

    src_path = entry.get("local_source_path", f"static/images/posts-src/{slug}.jpg")
    dest_path = entry.get("output_path", f"static/images/posts/{slug}.webp")
    os.makedirs(os.path.dirname(src_path), exist_ok=True)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    if not os.path.exists(src_path):
        if not download_image(direct_url, src_path):
            print(f"    FAIL: could not download selected image for {slug}")
            return False

    if not os.path.exists(src_path):
        print(f"    FAIL: selected source file was not created for {slug}")
        return False
    if has_placeholder_characteristics(src_path):
        print(f"    FAIL: selected source looks like a placeholder for {slug}")
        return False

    creator, creator_url = sanitize_creator_pair(
        entry.get("creator", ""),
        entry.get("creator_url", ""),
    )
    attribution_verified = bool(entry.get("attribution_verified")) and bool(creator)
    watermark = attribution_text(provider, creator, verified=attribution_verified)
    if not process_image(src_path, dest_path, watermark):
        print(f"    FAIL: could not process selected image for {slug}")
        return False

    attribution = resolve_image_attribution(entry)
    update_post_frontmatter(
        slug=slug,
        image_path=f"images/posts/{slug}.webp",
        thumbnail_path=f"images/posts/{slug}.webp",
        source=attribution["source"],
        source_url=attribution["source_url"],
        license_val=attribution["license_val"],
        commercial_use=entry.get("commercial_use", True),
        owner=attribution["owner"],
        creator=creator if attribution_verified else "",
        creator_url=creator_url if attribution_verified else "",
        creator_id=clean_text(entry.get("creator_id", "")) if attribution_verified else "",
        gate_meta=gate_meta_from_entry(entry),
        image_status=resolve_image_status(entry) or "verified",
        attribution_verified=attribution_verified,
        attribution_source=entry.get("attribution_source") or f"{provider.lower()}_api",
        license_url=entry.get("license_url", ""),
    )
    return True


def autofix_missing_images(target_slugs):
    targets = remediable_post_paths(target_slugs)
    if not targets:
        if target_slugs is not None and not target_slugs:
            print("QA Blog Image Autofix: no changed posts in scope.")
        else:
            print("QA Blog Image Autofix: no missing/broken images in scope.")
        return True

    from image_providers import PexelsProvider, PixabayProvider, load_dotenv
    from select_images import select_image_for_post

    load_dotenv(override=True)
    providers = [PexelsProvider(), PixabayProvider()]
    enabled = [provider for provider in providers if provider.is_enabled()]
    if not enabled:
        print("FAIL: missing image API keys; set PEXELS_API_KEY and/or PIXABAY_API_KEY")
        return False

    manifest_by_slug = load_manifest_by_slug()
    ok = True
    print(f"QA Blog Image Autofix: fixing {len(targets)} post(s)")
    for fpath in targets:
        fname = os.path.basename(fpath)
        try:
            meta, body = read_post_meta_body(fpath)
        except Exception as exc:
            print(f"  [{fname}] FAIL: could not read post: {exc}")
            ok = False
            continue
        slug = post_slug(fname, meta)
        title = clean_text(meta.get("title")) or slug
        meta["slug"] = slug
        meta["title"] = title
        used_without_current = {
            url
            for entry_slug, entry in manifest_by_slug.items()
            for url in [clean_text(entry.get("source_url", ""))]
            if url and entry_slug != slug
        }

        print(f"  [{slug}] selecting Pexels/Pixabay image")
        entry, reason = select_image_for_post(
            meta,
            body,
            used_without_current,
            api_first=True,
            allow_self_generated=False,
            providers=enabled,
        )
        if not entry:
            print(f"    FAIL: no acceptable Pexels/Pixabay image found ({reason})")
            ok = False
            continue
        if clean_text(entry.get("source_platform")) not in IMAGE_FIX_PROVIDERS:
            print(f"    FAIL: disallowed provider selected ({entry.get('source_platform')})")
            ok = False
            continue

        if process_selected_manifest_entry(entry):
            save_manifest_entry(entry)
            manifest_by_slug[slug] = entry
            print(f"    OK: {entry.get('source_platform')} image added")
        else:
            ok = False
    return ok


def qa(target_slugs=None):
    errors = []
    whitelist = load_whitelist()
    manifest_by_slug = load_manifest_by_slug()
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    if not os.path.exists(posts_dir):
        print(f"FAIL: {CONTENT_DIR} not found")
        return 1

    seen_urls = seed_seen_urls_for_unscoped_posts(posts_dir, target_slugs)
    posts_with_fallback_images = 0
    posts_with_needs_image = 0
    checked_posts = 0

    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        if target_slugs is not None and fname.replace(".md", "") not in target_slugs:
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            meta, _ = read_post_meta_body(fpath)
        except Exception as e:
            errors.append(f"[PARSE_ERROR] {fname}: {e}")
            continue

        slug = post_slug(fname, meta)
        if not target_matches(slug, fname, target_slugs):
            continue
        checked_posts += 1

        image = clean_text(meta.get("image", ""))
        thumbnail = clean_text(meta.get("thumbnail", ""))
        source_url = clean_text(meta.get("image_source_url", ""))
        license_val = clean_text(meta.get("image_license", ""))
        commercial = meta.get("image_commercial_use", False)
        image_status = clean_text(meta.get("image_status", ""))
        image_source = clean_text(meta.get("image_source", ""))
        image_creator = clean_text(meta.get("image_creator", ""))
        image_creator_url = clean_text(meta.get("image_creator_url", ""))
        image_attribution_verified = meta.get("image_attribution_verified")

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

        if is_blocked_creator(image_creator):
            errors.append(f"[INVALID_IMAGE_CREATOR] {slug}: blocked creator value ({image_creator})")
        if is_generated_creator(image_creator, meta, fname):
            errors.append(f"[GENERATED_IMAGE_CREATOR] {slug}: creator appears derived from title/slug/file ({image_creator})")
        if image_creator and image_attribution_verified is not True:
            errors.append(
                f"[CREATOR_WITHOUT_VERIFIED] {slug}: image_creator set but "
                f"image_attribution_verified={image_attribution_verified!r}"
            )
        if image_attribution_verified is True and not image_creator:
            errors.append(f"[VERIFIED_WITHOUT_CREATOR] {slug}: verified true but creator empty")
        if image_creator_url and not image_creator:
            errors.append(f"[IMAGE_CREATOR_URL_WITHOUT_CREATOR] {slug}: {image_creator_url}")

        manifest_entry = manifest_by_slug.get(slug)
        if manifest_entry:
            expected_creator = clean_text(manifest_entry.get("creator", ""))
            expected_verified = bool(manifest_entry.get("attribution_verified"))
            if expected_verified and expected_creator:
                if not image_creator:
                    errors.append(
                        f"[MISSING_IMAGE_CREATOR] {slug}: verified manifest creator ({expected_creator})"
                    )
                elif image_creator != expected_creator:
                    errors.append(
                        f"[IMAGE_CREATOR_MISMATCH] {slug}: frontmatter={image_creator} manifest={expected_creator}"
                    )
            elif image_creator and not expected_verified and image_attribution_verified is not True:
                errors.append(
                    f"[UNVERIFIED_IMAGE_CREATOR] {slug}: creator without verification, frontmatter={image_creator}"
                )

        if image_status in {"needs_image", "needs_review"}:
            errors.append(f"[NEEDS_IMAGE] {slug}: post still needs a verified image ({image_status})")
            posts_with_needs_image += 1

        if meta.get("image_reject_reason") and image:
            errors.append(f"[IMAGE_REJECT_WITH_IMAGE] {slug}: reject_reason set but image still assigned")

        if image_status == "verified":
            from image_gate_policy import gate_score_passes, requires_gate_score

            if requires_gate_score(meta):
                score = meta.get("image_total_score")
                if score in (None, ""):
                    errors.append(f"[IMAGE_SCORE_MISSING] {slug}: gate-verified image missing score")
                elif not gate_score_passes(score):
                    errors.append(f"[IMAGE_SCORE_LOW] {slug}: image_total_score={score}")

        if source_url:
            if source_url in seen_urls:
                if source_url not in whitelist:
                    prev = seen_urls[source_url]
                    errors.append(f"[DUPLICATE_URL] {slug} shares source_url with {prev}: {source_url}")
            else:
                seen_urls[source_url] = slug

        ai_summary = meta.get("ai_summary", {})
        if ai_summary and ai_summary.get("items"):
            for index, issue in ai_summary_item_issues(ai_summary.get("items", [])):
                errors.append(f"[AI_SUMMARY_ITEM] {slug}: items[{index}] {issue}")

    if target_slugs is None:
        for fpath in scan_public_ai_summary_map_literals(os.path.join(os.getcwd(), PUBLIC_DIR)):
            rel = os.path.relpath(fpath, os.getcwd())
            errors.append(f"[AI_SUMMARY_MAP_LITERAL] {rel}")

    warnings = []
    ga4_path = os.path.join("data", "ga4_footer.json")
    if not os.path.exists(ga4_path):
        warnings.append("[GA4_FOOTER_MISSING] data/ga4_footer.json not found")
    else:
        try:
            with open(ga4_path, encoding="utf-8") as fh:
                ga4_data = json.load(fh)
            if ga4_data.get("status") != "ok":
                warnings.append(
                    f"[GA4_FOOTER_PENDING] footer GA4 status={ga4_data.get('status', 'unknown')}"
                )
        except (json.JSONDecodeError, OSError) as exc:
            warnings.append(f"[GA4_FOOTER_INVALID] data/ga4_footer.json unreadable: {exc}")

    if warnings:
        print(f"QA WARN: {len(warnings)} warning(s)\n")
        for warn in warnings:
            print(f"  {warn}")

    if errors:
        print(f"QA FAILED: {len(errors)} error(s)\n")
        for err in errors:
            print(f"  {err}")
        return 1
    else:
        scope_note = "in scope" if target_slugs is not None else "all posts"
        print(f"QA PASSED: {checked_posts} {scope_note} have valid real images.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Quality assurance checks for blog post images.")
    parser.add_argument(
        "--autofix-missing-images",
        action="store_true",
        help="Before QA, use Pexels/Pixabay APIs to add images for scoped posts missing/broken images.",
    )
    parser.add_argument(
        "--scope-report",
        help="Read changed post slugs from reports/qa-scope.json and only check those posts.",
    )
    parser.add_argument(
        "--changed-files-from-git",
        nargs=2,
        metavar=("BASE", "HEAD"),
        help="Only check posts changed between two git refs.",
    )
    parser.add_argument(
        "--post",
        action="append",
        help="Only check a specific post path. Can be passed multiple times.",
    )
    args = parser.parse_args()

    target_slugs = None
    if args.scope_report:
        try:
            target_slugs = load_scope_slugs(args.scope_report)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"FAIL: cannot read scope report {args.scope_report}: {exc}")
            return 1
    if args.changed_files_from_git:
        target_slugs = load_changed_slugs_from_git(*args.changed_files_from_git)
    if args.post:
        target_slugs = load_post_slugs_from_paths(args.post)

    if args.autofix_missing_images and not autofix_missing_images(target_slugs):
        return 1

    return qa(target_slugs)


if __name__ == "__main__":
    sys.exit(main())
