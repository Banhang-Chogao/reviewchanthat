"""
scripts/process_images.py
Image processing pipeline for verified provider images only:
1. Download images from source URLs (direct_url required)
2. Convert to WebP (800x450, 16:9)
3. Add watermark attribution
4. Update post frontmatter
5. Fail if no real source image available
"""

import os
import sys
import json
import hashlib
import requests
from PIL import Image, ImageDraw, ImageFont

from creator_policy import attribution_text, clean_text, sanitize_creator_pair
from image_gate_policy import (
    GATE_FIELDS,
    gate_meta_from_entry,
    is_gate_verified_entry,
    resolve_image_status,
)

IMAGES_MANIFEST_PATH = "data/images.json"
POSTS_SRC_DIR = "static/images/posts-src"
POSTS_DIR = "static/images/posts"
CONTENT_DIR = "content/posts"
SITE_BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"
SELF_SOURCE_PLATFORMS = {"self", "self-owned", "self-generated"}


def watermark_attribution(source, creator):
    return attribution_text(source, creator)


def normalized(value):
    return clean_text(str(value)).lower()


def is_self_owned_entry(entry):
    platform = normalized(entry.get("source_platform", ""))
    license_val = normalized(entry.get("license", ""))
    return platform in SELF_SOURCE_PLATFORMS or license_val in SELF_SOURCE_PLATFORMS


def resolve_image_attribution(entry):
    """Map manifest entry to frontmatter image fields."""
    source_platform = clean_text(entry.get("source_platform", ""))
    source_url = clean_text(entry.get("source_url", ""))
    license_val = entry.get("license", "")

    if is_self_owned_entry(entry):
        src_path = clean_text(entry.get("local_source_path", ""))
        if not source_url and src_path.startswith("static/"):
            source_url = f"{SITE_BASE_URL}/{src_path.removeprefix('static/')}"
        return {
            "source": "self",
            "source_url": source_url,
            "owner": "self",
            "license_val": license_val or "Self-owned",
        }

    return {
        "source": source_platform,
        "source_url": source_url,
        "owner": "external",
        "license_val": license_val,
    }


def load_manifest():
    if not os.path.exists(IMAGES_MANIFEST_PATH):
        print(f"ERROR: {IMAGES_MANIFEST_PATH} not found. Run select_images.py first.")
        sys.exit(1)
    with open(IMAGES_MANIFEST_PATH) as f:
        return json.load(f)


def download_image(url, dest_path):
    if not url:
        return False
    try:
        print(f"    Downloading: {url}")
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(1024 * 1024):
                    f.write(chunk)
            return True
        print(f"    Download failed: HTTP {resp.status_code}")
    except Exception as e:
        print(f"    Download failed: {e}")
    return False


def has_placeholder_characteristics(img_path):
    """Detect if an image is likely a fake/solid-color placeholder."""
    try:
        img = Image.open(img_path).convert("RGB")
        if img.size[0] < 400 or img.size[1] < 300:
            return True
        pixels = list(img.getdata())
        r_vals = [p[0] for p in pixels[::100]]
        g_vals = [p[1] for p in pixels[::100]]
        b_vals = [p[2] for p in pixels[::100]]
        r_range = max(r_vals) - min(r_vals)
        g_range = max(g_vals) - min(g_vals)
        b_range = max(b_vals) - min(b_vals)
        if r_range < 30 and g_range < 30 and b_range < 30:
            return True
        return False
    except Exception:
        return False


def process_image(src_path, dest_path, watermark_text=""):
    try:
        img = Image.open(src_path).convert("RGB")
        target_w, target_h = 800, 450
        img_w, img_h = img.size
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h
        if img_ratio > target_ratio:
            new_w = int(img_h * target_ratio)
            offset = (img_w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, img_h))
        elif img_ratio < target_ratio:
            new_h = int(img_w / target_ratio)
            offset = (img_h - new_h) // 2
            img = img.crop((0, offset, img_w, offset + new_h))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        if watermark_text:
            draw = ImageDraw.Draw(img, "RGBA")
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except (IOError, OSError):
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            padding = 6
            margin = 10
            x = target_w - tw - margin - padding * 2
            y = target_h - th - margin - padding * 2
            draw.rectangle(
                [x, y, x + tw + padding * 2, y + th + padding * 2],
                fill=(0, 0, 0, 100),
            )
            draw.text(
                (x + padding, y + padding),
                watermark_text,
                fill=(255, 255, 255, 220),
                font=font,
            )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, "WebP", quality=85)
        print(f"    Saved: {dest_path} ({os.path.getsize(dest_path)} bytes)")
        return True
    except Exception as e:
        print(f"    Processing failed: {e}")
        return False


def apply_fallback(slug):
    """Set fallback.webp when no real image is available. Prevents broken image links."""
    import frontmatter
    from lib.toml_util import has_toml_fm, read_fm, set_field, remove_key
    import tomllib

    for f in os.listdir(CONTENT_DIR):
        if not f.endswith(".md"):
            continue
        try:
            fpath = os.path.join(CONTENT_DIR, f)
            text = open(fpath, encoding="utf-8").read()

            if has_toml_fm(text):
                parts = read_fm(text)
                if not parts:
                    continue
                fm_text = parts[1]
                meta = tomllib.loads(fm_text)
                # Match by slug or filename
                if meta.get("slug") != slug and f.replace(".md", "") != slug:
                    continue
                updates = {
                    "image": "images/posts/fallback.webp",
                    "thumbnail": "images/posts/fallback.webp",
                    "image_source": "self",
                    "image_license": "Self-owned",
                    "image_commercial_use": True,
                    "image_owner": "self",
                    "image_status": "needs_review",
                    "image_reject_reason": "No verified image available after processing",
                }
                removes = ["image_creator", "image_creator_url"]
                for k in removes:
                    fm_text = remove_key(fm_text, k)
                for k, v in updates.items():
                    fm_text = set_field(fm_text, k, v)
                new_text = parts[0] + fm_text.strip() + "\n+++" + parts[2]
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
                print(f"    Applied fallback: {f}")
                return

            post = frontmatter.load(fpath)
            if post.metadata.get("slug") == slug:
                meta = post.metadata
                meta["image"] = "images/posts/fallback.webp"
                meta["thumbnail"] = "images/posts/fallback.webp"
                meta["image_source"] = "self"
                meta["image_source_url"] = meta.get("image_source_url", "")
                meta["image_license"] = "Self-owned"
                meta["image_commercial_use"] = True
                meta["image_owner"] = "self"
                meta.pop("image_creator", None)
                meta.pop("image_creator_url", None)
                meta["image_status"] = "needs_review"
                meta["image_reject_reason"] = "No verified image available after processing"
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(frontmatter.dumps(post))
                print(f"    Applied fallback: {f}")
                return
        except Exception:
            continue


# Attribution content fields compared to decide whether image_attribution_checked_at
# should be bumped. If none of these differ from the existing frontmatter, the
# "checked_at" timestamp is preserved so re-running the pipeline doesn't rewrite
# every post with a new timestamp (idempotency — avoids diff churn).
ATTRIBUTION_CONTENT_KEYS = (
    "image", "thumbnail", "image_source", "image_source_url", "image_license",
    "image_license_url", "image_commercial_use", "image_owner",
    "image_creator", "image_creator_url", "image_creator_id",
    "image_attribution_verified", "image_attribution_source",
    "image_attribution_error",
)


def preserve_checked_at(meta, updates):
    """Keep the existing checked_at unless an attribution field actually changed.

    Mutates ``updates`` in place: when nothing substantive changed and the post
    already has a checked_at value, restore that value instead of the fresh one.
    """
    def norm(x):
        return "" if x is None else x

    changed = any(
        norm(meta.get(k)) != norm(updates[k])
        for k in ATTRIBUTION_CONTENT_KEYS
        if k in updates
    )
    existing = meta.get("image_attribution_checked_at")
    if not changed and existing:
        updates["image_attribution_checked_at"] = existing


def update_post_frontmatter(slug, image_path, thumbnail_path, source, source_url,
                            license_val, commercial_use, owner="external", creator="",
                            creator_url="", creator_id="", gate_meta=None, image_status=None,
                            attribution_verified=False, attribution_source="not_found",
                            license_url=""):
    import frontmatter
    from datetime import datetime, timedelta, timezone
    from lib.toml_util import has_toml_fm, read_fm, set_field, remove_key
    import tomllib

    fname = None
    for f in os.listdir(CONTENT_DIR):
        if not f.endswith(".md"):
            continue
        try:
            fpath = os.path.join(CONTENT_DIR, f)
            # Match by slug field first, fall back to filename match
            if f.replace(".md", "") == slug:
                fname = f
                break
            text = open(fpath, encoding="utf-8").read()
            if has_toml_fm(text):
                parts = read_fm(text)
                if parts:
                    meta = tomllib.loads(parts[1])
                    if meta.get("slug") == slug:
                        fname = f
                        break
            post = frontmatter.load(fpath)
            if post.metadata.get("slug") == slug:
                fname = f
                break
        except Exception:
            continue

    if not fname:
        print(f"    Post not found for slug: {slug}")
        return False

    fpath = os.path.join(CONTENT_DIR, fname)
    text = open(fpath, encoding="utf-8").read()

    verified = bool(attribution_verified) and bool(clean_text(creator))
    now_iso = datetime.now(timezone(timedelta(hours=7))).replace(microsecond=0).isoformat()
    removes = ["image_reject_reason", "image_attribution_error"]
    updates = {
        "image": (image_path or "").lstrip("/"),
        "thumbnail": (thumbnail_path or "").lstrip("/"),
        "image_source": source,
        "image_source_url": source_url,
        "image_license": license_val,
        "image_commercial_use": commercial_use,
        "image_owner": owner,
        "image_creator": clean_text(creator) if verified else "",
        "image_creator_url": clean_text(creator_url) if verified else "",
        "image_creator_id": clean_text(creator_id) if verified else "",
        "image_attribution_verified": verified,
        "image_attribution_source": attribution_source or ("not_found" if not verified else ""),
        "image_attribution_checked_at": now_iso,
    }
    if license_url:
        updates["image_license_url"] = license_url
    if not verified:
        updates["image_attribution_error"] = "Provider/source page did not expose verified creator metadata"
    if image_status:
        updates["image_status"] = image_status

    if has_toml_fm(text):
        parts = read_fm(text)
        if not parts:
            print(f"    ERROR: Invalid TOML frontmatter: {fname}")
            return False
        fm_text = parts[1]
        try:
            meta = tomllib.loads(fm_text)
        except Exception as e:
            print(f"    ERROR: Corrupt TOML frontmatter: {fname}: {e}")
            return False
        original_date = meta.get("date")
        preserve_checked_at(meta, updates)

        for k in removes:
            fm_text = remove_key(fm_text, k)
        if not image_status:
            fm_text = remove_key(fm_text, "image_status")
            for key in GATE_FIELDS:
                fm_text = remove_key(fm_text, key)

        for k, v in updates.items():
            fm_text = set_field(fm_text, k, v)

        if gate_meta:
            for key in GATE_FIELDS:
                value = gate_meta.get(key)
                if value not in (None, "") and not (key.endswith("_score") and value == 0):
                    fm_text = set_field(fm_text, key, value)
        elif image_status == "verified" and not gate_meta:
            fm_text = set_field(fm_text, "image_provider", clean_text(source).lower())
        if original_date is not None:
            fm_text = set_field(fm_text, "date", original_date)

        new_text = parts[0] + fm_text.strip() + "\n+++" + parts[2]
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"    Updated TOML frontmatter: {fname}")
        return True

    # YAML path
    post = frontmatter.load(fpath)
    meta = post.metadata
    original_date = meta.get("date")
    preserve_checked_at(meta, updates)
    for k in removes:
        meta.pop(k, None)
    for k, v in updates.items():
        meta[k] = v
    if not image_status:
        meta.pop("image_status", None)
        for key in GATE_FIELDS:
            meta.pop(key, None)
    if gate_meta:
        for key in GATE_FIELDS:
            value = gate_meta.get(key)
            if value not in (None, "") and not (key.endswith("_score") and value == 0):
                meta[key] = value
    elif image_status == "verified" and not gate_meta:
        meta["image_provider"] = clean_text(source).lower()
    if original_date is not None:
        meta["date"] = original_date
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    print(f"    Updated frontmatter: {fname}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download and process verified Pexels/Pixabay stock images")
    parser.add_argument("--force", action="store_true", help="Re-download and reprocess existing images")
    parser.add_argument("--skip-watermark", action="store_true", help="Skip adding watermark attribution")
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        metavar="SLUG",
        help="Chỉ process slug này (lặp lại được). Ưu tiên khi commit/merge theo scope.",
    )
    args = parser.parse_args()

    print("=== Image Processing (verified API images) ===")
    manifest = load_manifest()
    success = 0
    skipped = 0
    failed = 0
    slug_filter = set(args.slugs) if args.slugs else None
    if slug_filter:
        print(f"  Scope: {', '.join(sorted(slug_filter))}")

    for entry in manifest.get("posts", []):
        slug = entry["slug"]
        if slug_filter is not None and slug not in slug_filter:
            continue
        direct_url = entry.get("direct_url", "")
        src_path = entry.get("local_source_path", f"static/images/posts-src/{slug}.jpg")
        dest_path = entry.get("output_path", f"static/images/posts/{slug}.webp")
        attribution = resolve_image_attribution(entry)
        source = attribution["source"]
        source_url = attribution["source_url"]
        license_val = attribution["license_val"]
        owner = attribution["owner"]
        commercial = entry.get("commercial_use", False)
        attr_verified = bool(entry.get("attribution_verified"))
        creator, creator_url = sanitize_creator_pair(
            entry.get("creator", ""),
            entry.get("creator_url", ""),
        )
        if not attr_verified:
            creator, creator_url = "", ""
        creator_id = clean_text(entry.get("creator_id", "")) if creator else ""
        attr_source = clean_text(entry.get("attribution_source")) or (
            "not_found" if not attr_verified else ""
        )
        from creator_policy import attribution_text as _attr_text
        watermark = _attr_text(
            entry.get("source_platform", source),
            creator,
            verified=attr_verified and bool(creator),
        )
        fm_attr = dict(
            creator=creator,
            creator_url=creator_url,
            creator_id=creator_id,
            attribution_verified=attr_verified and bool(creator),
            attribution_source=attr_source,
        )

        print(f"\n  [{slug}]")

        is_self_owned = source in SELF_SOURCE_PLATFORMS or is_self_owned_entry(entry)

        # Self-owned images do not require direct_url
        if is_self_owned:
            if os.path.exists(dest_path):
                fsize = os.path.getsize(dest_path)
                if fsize > 5000 and not has_placeholder_characteristics(dest_path):
                    print(f"    Already processed (self-owned image): {dest_path} ({fsize} bytes)")
                    gate_meta = gate_meta_from_entry(entry)
                    image_status = resolve_image_status(entry)
                    status_note = image_status or "legacy"
                    if is_gate_verified_entry(entry):
                        status_note = "gate-verified"
                    print(f"    Frontmatter status: {status_note}")
                    update_post_frontmatter(
                        slug=slug,
                        image_path=f"images/posts/{slug}.webp",
                        thumbnail_path=f"images/posts/{slug}.webp",
                        source=source,
                        source_url=source_url,
                        license_val=license_val,
                        commercial_use=commercial,
                        owner=owner,
                        gate_meta=gate_meta,
                        image_status=image_status,
                        **fm_attr,
                    )
                    skipped += 1
                    continue
            # Self-owned image file missing or not ready yet; skip processing but don't fail
            print(f"    Self-owned image not ready: {dest_path} (will be processed later)")
            skipped += 1
            continue

        # Provider/external images require direct_url
        if not direct_url:
            print(f"    FAIL: No direct_url in manifest for {slug}")
            apply_fallback(slug)
            failed += 1
            continue

        if os.path.exists(dest_path) and not args.force:
            fsize = os.path.getsize(dest_path)
            if fsize > 5000 and not has_placeholder_characteristics(dest_path):
                print(f"    Already processed (real image): {dest_path} ({fsize} bytes)")
                gate_meta = gate_meta_from_entry(entry)
                image_status = resolve_image_status(entry)
                status_note = image_status or "legacy"
                if is_gate_verified_entry(entry):
                    status_note = "gate-verified"
                print(f"    Frontmatter status: {status_note}")
                update_post_frontmatter(
                    slug=slug,
                    image_path=f"images/posts/{slug}.webp",
                    thumbnail_path=f"images/posts/{slug}.webp",
                    source=source,
                    source_url=source_url,
                    license_val=license_val,
                    commercial_use=commercial,
                    owner=owner,
                    gate_meta=gate_meta,
                    image_status=image_status,
                    **fm_attr,
                )
                skipped += 1
                continue
            else:
                print(f"    Replacing existing file ({fsize} bytes)")

        if args.force:
            for path in (dest_path, src_path):
                if os.path.exists(path):
                    os.remove(path)
                    print(f"    Force refresh: removed {path}")

        if not os.path.exists(src_path):
            print(f"    Downloading source image...")
            ok = download_image(direct_url, src_path)
            if not ok:
                print(f"    FAIL: Could not download from {direct_url}")
                apply_fallback(slug)
                failed += 1
                continue

        if not os.path.exists(src_path):
            print(f"    FAIL: Source file not found at {src_path}")
            apply_fallback(slug)
            failed += 1
            continue

        if has_placeholder_characteristics(src_path):
            print(f"    FAIL: Downloaded source appears to be a placeholder/solid color")
            os.remove(src_path)
            apply_fallback(slug)
            failed += 1
            continue

        ok = process_image(src_path, dest_path, watermark)
        if not ok:
            print(f"    FAIL: Image processing failed for {slug}")
            apply_fallback(slug)
            failed += 1
            continue

        gate_meta = gate_meta_from_entry(entry)
        image_status = resolve_image_status(entry)
        update_post_frontmatter(
            slug=slug,
            image_path=f"images/posts/{slug}.webp",
            thumbnail_path=f"images/posts/{slug}.webp",
            source=source,
            source_url=source_url,
            license_val=license_val,
            commercial_use=commercial,
            owner=owner,
            gate_meta=gate_meta,
            image_status=image_status,
            **fm_attr,
        )
        success += 1

    print(f"\n=== Summary ===")
    print(f"  Processed: {success}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
