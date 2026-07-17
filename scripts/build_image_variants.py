#!/usr/bin/env python3
"""Build immutable, responsive image variants for the blog image pipeline.

The post front matter continues to point at the original, attribution-bearing
local asset.  This script creates content-hashed derivatives and a small Hugo
data index so templates can choose the right format and width at render time.
It never downloads anything and never upscales a source image.

Usage:
  python3 scripts/build_image_variants.py --slug post-slug
  python3 scripts/build_image_variants.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "static/images/posts"
VARIANTS_DIR = POSTS_DIR / "variants"
DATA_PATH = ROOT / "data/image-assets.json"

# The card sizes match the largest desktop card and the mobile/list slot. The
# article sizes match the ~840px reading column and a 1200px high-density view.
SPECS = {
    "card": ("4:3", ((320, 240), (480, 360))),
    "article": ("16:9", ((800, 450), (1200, 675))),
}
FORMATS = ("avif", "webp", "jpeg")
MIME_TYPES = {"avif": "image/avif", "webp": "image/webp", "jpeg": "image/jpeg"}
EXTENSIONS = {"avif": "avif", "webp": "webp", "jpeg": "jpg"}
PREFERRED_LIMITS = {"card": 100 * 1024, "article": 250 * 1024}


def image_key(path: Path) -> str:
    return path.stem


def source_for_slug(slug: str) -> Path | None:
    preferred = POSTS_DIR / f"{slug}.webp"
    if preferred.exists():
        return preferred
    for suffix in (".jpg", ".jpeg", ".png", ".avif"):
        candidate = POSTS_DIR / f"{slug}{suffix}"
        if candidate.exists():
            return candidate
    return None


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def dominant_color(image: Image.Image) -> str:
    sample = image.copy()
    sample.thumbnail((32, 32), Image.Resampling.BILINEAR)
    mean = ImageStat.Stat(sample.convert("RGB")).mean
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(value))) for value in mean)


def crop_without_upscale(image: Image.Image, width: int, height: int) -> Image.Image:
    """Crop to the slot ratio and resize only when the source is large enough."""
    source = ImageOps.exif_transpose(image).convert("RGB")
    target_ratio = width / height
    source_ratio = source.width / source.height
    if source_ratio > target_ratio:
        crop_width = round(source.height * target_ratio)
        left = (source.width - crop_width) // 2
        source = source.crop((left, 0, left + crop_width, source.height))
    elif source_ratio < target_ratio:
        crop_height = round(source.width / target_ratio)
        top = (source.height - crop_height) // 2
        source = source.crop((0, top, source.width, top + crop_height))

    if source.width <= width and source.height <= height:
        return source
    return source.resize((width, height), Image.Resampling.LANCZOS)


def encode(image: Image.Image, destination: Path, fmt: str, preferred_limit: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size <= preferred_limit:
        return
    quality = 52 if fmt == "avif" else 78
    while True:
        # No EXIF/ICC/XMP is passed to any encoder. This deliberately strips
        # metadata that adds bytes and can leak capture/device information.
        if fmt == "avif":
            image.save(destination, format="AVIF", quality=quality, speed=6)
        elif fmt == "webp":
            image.save(destination, format="WEBP", quality=quality, method=6)
        else:
            image.save(destination, format="JPEG", quality=quality, optimize=True, progressive=True)
        if destination.stat().st_size <= preferred_limit or quality <= 36:
            return
        quality -= 6


def variant_record(source: Path, role: str, width: int, height: int, digest: str) -> dict[str, Any]:
    image = Image.open(source)
    prepared = crop_without_upscale(image, width, height)
    record: dict[str, Any] = {
        "width": prepared.width,
        "height": prepared.height,
        "variants": [],
    }
    for fmt in FORMATS:
        filename = f"{digest}-{role}-{width}.{EXTENSIONS[fmt]}"
        destination = VARIANTS_DIR / filename
        encode(prepared, destination, fmt, PREFERRED_LIMITS[role])
        record["variants"].append(
            {
                "src": f"images/posts/variants/{filename}",
                "width": prepared.width,
                "bytes": destination.stat().st_size,
                "type": MIME_TYPES[fmt],
                "format": fmt,
            }
        )
    image.close()
    return record


def build_one(slug: str) -> dict[str, Any] | None:
    source = source_for_slug(slug)
    if source is None or source.name == "fallback.webp":
        return None

    digest = content_hash(source)
    with Image.open(source) as opened:
        source_image = ImageOps.exif_transpose(opened).convert("RGB")
        source_width, source_height = source_image.size
        color = dominant_color(source_image)
        source_image.close()

    asset: dict[str, Any] = {
        "source": f"images/posts/{source.name}",
        "hash": digest,
        "source_width": source_width,
        "source_height": source_height,
        "dominant_color": color,
        "card": {},
        "article": {},
    }
    for role, (_, sizes) in SPECS.items():
        records = []
        seen_dimensions = set()
        for width, height in sizes:
            record = variant_record(source, role, width, height, digest)
            dimensions = (record["width"], record["height"])
            if dimensions not in seen_dimensions:
                records.append(record)
                seen_dimensions.add(dimensions)
        for fmt in FORMATS:
            variants = [
                next(item for item in record["variants"] if item["format"] == fmt)
                | {"height": record["height"]}
                for record in records
            ]
            asset[role][fmt] = {
                "src": variants[0]["src"],
                "width": variants[0]["width"],
                "height": variants[0]["height"],
                "variants": variants,
            }
    return asset


def load_index() -> dict[str, Any]:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 1, "assets": {}}


def save_index(index: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build hashed responsive blog image variants")
    parser.add_argument("--slug", action="append", dest="slugs", help="Process one slug (repeatable)")
    parser.add_argument("--all", action="store_true", help="Process every base post image")
    parser.add_argument("--prune", action="store_true", help="Remove unreferenced generated variants")
    args = parser.parse_args()
    if not args.all and not args.slugs:
        parser.error("use --slug SLUG or --all")

    if args.all:
        slugs = sorted(
            p.stem
            for p in POSTS_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png", ".avif"}
        )
    else:
        slugs = sorted(set(args.slugs or []))

    index = load_index()
    assets = index.setdefault("assets", {})
    built = 0
    skipped = 0
    for slug in slugs:
        asset = build_one(slug)
        if asset is None:
            skipped += 1
            continue
        assets[image_key(Path(asset["source"]))] = asset
        built += 1

    index["version"] = 1
    index["generated_by"] = "scripts/build_image_variants.py"
    save_index(index)
    if args.prune:
        referenced = {
            str(variant.get("src", "")).split("/", 4)[-1]
            for asset in assets.values()
            for role in ("card", "article")
            for fmt in FORMATS
            for variant in asset.get(role, {}).get(fmt, {}).get("variants", [])
        }
        removed = 0
        for candidate in VARIANTS_DIR.glob("*"):
            if candidate.is_file() and candidate.name not in referenced:
                candidate.unlink()
                removed += 1
        print(f"Pruned unreferenced variants: {removed}")
    print(f"Built image assets: {built}; skipped: {skipped}; index: {DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
