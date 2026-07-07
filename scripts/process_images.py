#!/usr/bin/env python3
"""Hugo blog image pipeline: resize, crop, WebP, watermark, manifest.

Usage:
  python scripts/process_images.py

Layout:
  static/images/posts-src/       source images (self-owned or external)
  static/images/posts/           processed output (WebP)
  data/images.json               image manifest
"""

import hashlib
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "static" / "images" / "posts-src"
OUT_DIR = REPO_ROOT / "static" / "images" / "posts"
MANIFEST_PATH = REPO_ROOT / "data" / "images.json"
BLOG_URL = "https://banhang-chogao.github.io/reviewchanthat/"

PRESETS = {
    "hero": (800, 450),
    "card": (220, 165),
}

WATERMARK_BLOG = BLOG_URL
WATERMARK_OPACITY = 0.50
WATERMARK_FONT_SIZE = 14
WATERMARK_PADDING = 12
WATERMARK_BG_ALPHA = 0.35

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def stable_hash16(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        h.update(f.read())
    num = int(h.hexdigest()[:16], 16)
    return str(num)[-16:].zfill(16)


def load_metadata(image_path: Path) -> dict:
    meta_path = image_path.with_name(image_path.name + ".meta.json")
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"source": "self", "source_url": "", "license": "Owned by Review Chân Thật", "commercial_use": True}


def get_image_id(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"\.[^.]+$", "", stem)
    stem = stem.lower().strip()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    stem = stem.strip("-")
    return stem or "image"


def resize_crop_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    ratio = max(target_w / img.width, target_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def apply_watermark(img: Image.Image, hash16: str) -> Image.Image:
    watermark_text = f"{hash16}_{WATERMARK_BLOG}"
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", WATERMARK_FONT_SIZE)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", WATERMARK_FONT_SIZE)
        except (IOError, OSError):
            font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = img.width - tw - WATERMARK_PADDING
    y = img.height - th - WATERMARK_PADDING
    bp = 6
    draw.rectangle(
        [x - bp, y - bp, x + tw + bp, y + th + bp],
        fill=(0, 0, 0, int(255 * WATERMARK_BG_ALPHA)),
    )
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, int(255 * WATERMARK_OPACITY)))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def process_image(src_path: Path, out_dir: Path) -> dict | None:
    image_id = get_image_id(src_path.name)
    metadata = load_metadata(src_path)
    is_self = metadata.get("source", "self") == "self"
    hash16 = stable_hash16(src_path) if is_self else ""
    try:
        img = Image.open(src_path).convert("RGB")
    except Exception as e:
        print(f"  ERROR: cannot open — {e}")
        return None
    max_preset_w = max(w for w, h in PRESETS.values())
    max_preset_h = max(h for w, h in PRESETS.values())
    if img.width < max_preset_w * 0.5 or img.height < max_preset_h * 0.5:
        print(f"  SKIP: too small ({img.width}x{img.height})")
        return None
    entry = {
        "id": image_id,
        "src": f"images/posts/{image_id}-hero.webp",
        "source": metadata.get("source", "self"),
        "source_url": metadata.get("source_url", ""),
        "license": metadata.get("license", "Owned by Review Chân Thật"),
        "commercial_use": metadata.get("commercial_use", True),
        "watermarked": is_self,
        "hash16": hash16,
    }
    for preset_name, (pw, ph) in PRESETS.items():
        processed = resize_crop_fill(img, pw, ph)
        if is_self:
            processed = apply_watermark(processed, hash16)
        out_filename = f"{image_id}-{preset_name}.webp"
        out_path = out_dir / out_filename
        processed.save(out_path, "WEBP", quality=85, method=6)
        print(f"  -> {out_filename} ({pw}x{ph}){' [watermarked]' if is_self else ''}")
    return entry


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not SRC_DIR.exists():
        print(f"OK: {SRC_DIR} does not exist. Nothing to process.")
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump({"images": []}, f, indent=2, ensure_ascii=False)
        print(f"Created empty {MANIFEST_PATH}")
        return
    image_files = sorted([f for f in SRC_DIR.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONS])
    if not image_files:
        print(f"No images found in {SRC_DIR}")
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump({"images": []}, f, indent=2, ensure_ascii=False)
        return
    print(f"Processing {len(image_files)} image(s) from {SRC_DIR}")
    print(f"Output → {OUT_DIR}\n")
    manifest_images = []
    for img_path in image_files:
        print(f"Image: {img_path.name}")
        entry = process_image(img_path, OUT_DIR)
        if entry:
            manifest_images.append(entry)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump({"images": manifest_images}, f, indent=2, ensure_ascii=False)
    print(f"\nManifest: {MANIFEST_PATH}")
    print(f"Done. {len(manifest_images)} image(s) processed.")


if __name__ == "__main__":
    main()
