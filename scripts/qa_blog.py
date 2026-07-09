"""
scripts/qa_blog.py
Quality assurance checks for the blog.
Hard failures on: fallback images, missing images, missing metadata, duplicates, etc.
"""

import os
import re
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


def qa():
    errors = []
    whitelist = load_whitelist()
    manifest_by_slug = load_manifest_by_slug()
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
        sys.exit(1)
    else:
        print("QA PASSED: All posts have valid real images.")
        sys.exit(0)


if __name__ == "__main__":
    qa()
