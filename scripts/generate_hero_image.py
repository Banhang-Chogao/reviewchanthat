#!/usr/bin/env python3
"""
Generate self-hosted editorial images for Review Chân Thật.

Two modes:
1. hero — 1200x630 WebP for the post's main image field
2. inline — 800x400 WebP illustrations for H2 sections in the body

All images are abstract topic-based designs with no brand logos,
no fake screenshots, no celebrity content.

Output dir: static/images/posts/
Registry:    data/generated-images.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    sys.exit(2)

WIDTH = 1200
HEIGHT = 630
INLINE_W = 800
INLINE_H = 600
OUTPUT_DIR = "static/images/posts"
SVG_DIR = "assets/generated-images"
REGISTRY_PATH = "data/generated-images.json"

SITE_URL = "https://banhang-chogao.github.io/reviewchanthat/"
SITE_NAME = "Review Chan That"
SITE_NAME_DISPLAY = "Review Chân Thật"

TOPIC_STYLES: dict[str, dict[str, Any]] = {
    "technology": {
        "bg_gradient": ("#1a1a2e", "#16213e", "#0f3460"),
        "accent": "#e94560",
        "accent2": "#0f3460",
        "shape_color": "#1a3a6a",
        "title_color": "#ffffff",
        "subtitle_color": "#a0aec0",
        "deco": "pipeline",
    },
    "apple": {
        "bg_gradient": ("#1c1c1e", "#2c2c2e", "#3a3a3c"),
        "accent": "#007aff",
        "accent2": "#636366",
        "shape_color": "#2c2c2e",
        "title_color": "#ffffff",
        "subtitle_color": "#a1a1a6",
        "deco": "device_outline",
    },
    "travel": {
        "bg_gradient": ("#0f2027", "#203a43", "#2c5364"),
        "accent": "#f2994a",
        "accent2": "#f2c94c",
        "shape_color": "#1a3d4a",
        "title_color": "#ffffff",
        "subtitle_color": "#cbd5e1",
        "deco": "travel_map",
    },
    "finance": {
        "bg_gradient": ("#0d1321", "#1d2b3a", "#2d3a4a"),
        "accent": "#38b2ac",
        "accent2": "#319795",
        "shape_color": "#1a2a3a",
        "title_color": "#ffffff",
        "subtitle_color": "#a0aec0",
        "deco": "chart",
    },
    "review": {
        "bg_gradient": ("#1a202c", "#2d3748", "#4a5568"),
        "accent": "#ed8936",
        "accent2": "#48bb78",
        "shape_color": "#2d3748",
        "title_color": "#ffffff",
        "subtitle_color": "#cbd5e1",
        "deco": "checklist",
    },
    "default": {
        "bg_gradient": ("#1a1a2e", "#16213e", "#0f3460"),
        "accent": "#e94560",
        "accent2": "#533483",
        "shape_color": "#1a2a4a",
        "title_color": "#ffffff",
        "subtitle_color": "#a0aec0",
        "deco": "abstract",
    },
}


def detect_style(category: str, tags: list[str], title: str) -> str:
    blob = f"{category} {' '.join(tags)} {title}".lower()
    if any(k in blob for k in ("cong-nghe", "technology", "github", "ci/cd", "devops", "actions", "pipeline", "coding", "software")):
        return "technology"
    if any(k in blob for k in ("apple", "iphone", "ios", "macos", "ipad", "macbook", "imac", "watch", "airpods")):
        return "apple"
    if any(k in blob for k in ("du-lich", "travel", "tour", "destination", "beach", "mountain", "hotel", "flight")):
        return "travel"
    if any(k in blob for k in ("tai-chinh", "finance", "money", "invest", "bank", "stock", "crypto", "loan")):
        return "finance"
    if any(k in blob for k in ("review", "danh gia", "shopping", "mua sam", "product")):
        return "review"
    return "default"


DECO_PATTERNS = {
    "pipeline": draw_pipeline,
    "device_outline": draw_device_outline,
    "travel_map": draw_travel_map,
    "chart": draw_chart,
    "checklist": draw_checklist,
    "abstract": draw_abstract,
}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_gradient(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    colors = [hex_to_rgb(c) for c in style["bg_gradient"]]
    n = len(colors)
    for y in range(h):
        t = y / h
        seg = t * (n - 1)
        i = int(seg)
        frac = seg - i
        if i >= n - 1:
            c = colors[-1]
        else:
            c = lerp_color(colors[i], colors[i + 1], frac)
        draw.line([(0, y), (w, y)], fill=c)


def draw_pipeline(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cy = h // 2 + 40
    draw.line([(80, cy), (w - 80, cy)], fill=accent2, width=2)
    nodes_x = [int(w * 0.2), int(w * 0.35), int(w * 0.5), int(w * 0.65), int(w * 0.8)]
    for i, nx in enumerate(nodes_x):
        radius = 18 if i != 2 else 24
        draw.ellipse([nx - radius, cy - radius, nx + radius, cy + radius], fill=accent if i != 2 else accent2)
    for i in range(len(nodes_x) - 1):
        x1, x2 = nodes_x[i] + 18, nodes_x[i + 1] - 18
        draw.line([(x1, cy), (x2, cy)], fill=accent + (120,), width=2)
    draw.line([(int(w * 0.5), cy + 24), (int(w * 0.5), cy + 80)], fill=accent2, width=2)
    draw.rectangle([int(w * 0.5) - 30, cy + 80, int(w * 0.5) + 30, cy + 100], fill=accent2)


def draw_device_outline(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cx, cy = w // 2, h // 2 - 20
    dw, dh = 160, 280
    rx = 20
    draw.rounded_rectangle([cx - dw // 2, cy - dh // 2, cx + dw // 2, cy + dh // 2], radius=rx, outline=accent + (100,), width=3)
    draw.rounded_rectangle([cx - dw // 2 + 15, cy - dh // 2 + 15, cx + dw // 2 - 15, cy + dh // 2 - 60], radius=8, outline=accent2 + (60,), width=1)
    for i in range(3):
        sx = cx - dw // 2 + 25 + i * 40
        draw.line([(sx, cy - dh // 2 + 25), (sx, cy + dh // 2 - 60)], fill=accent + (30,), width=1)


def draw_travel_map(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cx, cy = w // 2, h // 2 - 10
    points = [(100, cy + 60), (300, cy - 40), (500, cy), (700, cy - 50), (900, cy + 30), (1100, cy - 20)]
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=accent2 + (150,), width=2)
    draw.ellipse([300 - 10, cy - 40 - 10, 300 + 10, cy - 40 + 10], fill=accent + (180,))
    draw.ellipse([700 - 10, cy - 50 - 10, 700 + 10, cy - 50 + 10], fill=accent + (180,))
    draw.ellipse([950, 80, 1050, 180], fill=accent2 + (100,))


def draw_chart(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cx, cy = w // 2, h // 2 + 10
    bars = [(150, 200), (250, 150), (350, 250), (500, 120), (600, 180), (700, 90), (850, 160), (950, 130), (1050, 200)]
    for bx, bh in bars:
        draw.rectangle([bx - 20, cy + 60 - bh, bx + 20, cy + 60], fill=accent2 + (150,))
    trend = [(100, cy + 50), (300, cy - 10), (500, cy + 20), (700, cy - 30), (900, cy + 10), (1100, cy - 40)]
    for i in range(len(trend) - 1):
        draw.line([trend[i], trend[i + 1]], fill=accent, width=3)
    draw.rectangle([100, cy + 80, 350, cy + 120], outline=accent + (80,), width=1)
    draw.rectangle([850, cy + 80, 1100, cy + 120], outline=accent + (80,), width=1)


def draw_checklist(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cx, cy = w // 2, h // 2 + 10
    items_y = [cy - 40, cy + 10, cy + 60]
    for i, iy in enumerate(items_y):
        draw.rectangle([200, iy - 10, 230, iy + 10], outline=accent + (150,) if i < 2 else accent2, width=2)
        draw.line([250, iy, 500, iy], fill=accent2 + (100,) if i < 2 else accent2, width=2)
    stars_x = [700, 760, 820, 880, 940]
    for j, sx in enumerate(stars_x):
        draw.rectangle([sx, cy - 10, sx + 20, cy + 10], fill=accent if j < 3 else accent2 + (120,))


def draw_abstract(draw: ImageDraw, style: dict, w: int, h: int) -> None:
    accent = hex_to_rgb(style["accent"])
    accent2 = hex_to_rgb(style["accent2"])
    cx, cy = w // 2, h // 2
    for r in range(100, 300, 40):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent + (40,), width=1)
    draw.polygon([(200, 400), (250, 300), (300, 400)], fill=accent + (100,))
    draw.polygon([(800, 300), (900, 250), (950, 350), (850, 400)], fill=accent2 + (100,))


def get_draw_image(w: int, h: int, style: dict, deco_label: str, text: str) -> Image.Image:
    img = Image.new("RGB", (w, h), color="#1a1a2e")
    draw = ImageDraw.Draw(img, "RGBA")
    draw_gradient(draw, style, w, h)
    deco_fn = DECO_PATTERNS.get(style.get("deco", "abstract"), draw_abstract)
    deco_fn(draw, style, w, h)

    if w >= 600:
        draw_text_centered(draw, text, style, w, h)

    gray = (180, 180, 190, 100)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((w - 200, h - 30), SITE_NAME, fill=gray, font=font)

    return img


def draw_text_centered(draw: ImageDraw, text: str, style: dict, w: int, h: int) -> None:
    title_color = hex_to_rgb(style["title_color"])
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    tfont = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                sz = 36 if w < 1200 else 48
                tfont = ImageFont.truetype(fp, sz)
                break
            except Exception:
                continue
    if tfont is None:
        tfont = ImageFont.load_default()
    max_tw = w - 200
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        try:
            bbox = tfont.getbbox(test)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(test) * 20
        if tw > max_tw and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    ty = h // 2 - len(lines) * 30
    for line in lines[:3]:
        try:
            bbox = tfont.getbbox(line)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(line) * 28
        tx = (w - tw) // 2
        draw.text((tx, ty), line, fill=title_color, font=tfont)
        ty += 60


def generate_image(
    slug: str,
    title: str,
    style_key: str,
    w: int = WIDTH,
    h: int = HEIGHT,
    write: bool = False,
    seed_text: str = "",
) -> dict[str, Any]:
    if style_key not in TOPIC_STYLES:
        style_key = "default"
    style = dict(TOPIC_STYLES[style_key])
    seed = seed_text or title
    hval = abs(hash(seed)) % 1000
    deco_keys = list(DECO_PATTERNS.keys())
    alt_deco = deco_keys[hval % len(deco_keys)]
    if hval % 3 != 0:
        style["deco"] = alt_deco
    accent_rgb = hex_to_rgb(style["accent"])
    shift = hval % 60 - 30
    shifted = tuple(max(0, min(255, c + shift)) for c in accent_rgb)
    style["accent"] = "#{:02x}{:02x}{:02x}".format(*shifted)
    img = get_draw_image(w, h, style, style_key, title)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SVG_DIR, exist_ok=True)
    fname = f"{slug}.webp"
    webp_path = os.path.join(OUTPUT_DIR, fname)
    svg_path = os.path.join(SVG_DIR, f"{slug}.svg")
    if write:
        img.save(webp_path, "WEBP", quality=85)
        sz = 36 if w < 800 else 48
        svg_content = (
            f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">\n'
            f'<rect width="{w}" height="{h}" fill="#1a1a2e"/>\n'
            f'<text x="50%" y="50%" text-anchor="middle" fill="#fff" font-size="{sz}" font-family="sans-serif">{title}</text>\n'
            f'</svg>\n'
        )
        with open(svg_path, "w") as f:
            f.write(svg_content)
    result = {
        "slug": slug,
        "path": f"images/posts/{fname}",
        "source_svg": f"assets/generated-images/{slug}.svg",
        "method": "programmatic_pillow",
        "style": style_key,
        "title": title,
        "dimensions": f"{w}x{h}",
        "format": "webp",
    }
    return result


def _load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"generated_at": "", "items": {}}


def _save_registry(reg: dict) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)


def registry_item(result: dict) -> dict:
    now = datetime.now(timezone.utc)
    now_vn = now.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    return {
        "path": result["path"],
        "source_svg": result["source_svg"],
        "method": "programmatic_pillow",
        "style": result["style"],
        "title": result["title"],
        "created_at": now_vn,
        "license": f"Original self-hosted editorial illustration by {SITE_NAME_DISPLAY}",
    }


def register_image(result: dict) -> None:
    reg = _load_registry()
    reg["items"][result["slug"]] = registry_item(result)
    reg["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    _save_registry(reg)


def get_image_meta(slug: str, title: str, img_path: str, is_inline: bool = False) -> dict[str, Any]:
    base = {
        "image": img_path,
        "thumbnail": img_path,
        "image_alt": f"Editorial illustration for: {title}",
        "image_status": "verified",
        "image_provider": "self-generated",
        "image_source": SITE_NAME_DISPLAY,
        "image_source_url": SITE_URL,
        "image_license": f"Original self-hosted editorial illustration by {SITE_NAME_DISPLAY}",
        "image_license_url": f"{SITE_URL}branding-ci/",
        "image_commercial_use": True,
        "image_owner": "self",
        "image_creator": SITE_NAME_DISPLAY,
        "image_creator_url": SITE_URL,
        "image_creator_id": "review-chan-that-generated",
        "image_attribution_verified": True,
        "image_attribution_source": "self_generated",
        "image_generation_method": "programmatic_pillow",
    }
    if is_inline:
        base["image_origin"] = "inline-illustration"
    return base


def extract_headings(body: str) -> list[str]:
    """Extract H2 section headings from markdown body."""
    headings = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
    return [h.strip() for h in headings if h.strip()]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text[:60]


def generate_for_post(
    slug: str,
    title: str,
    body: str = "",
    category: str = "",
    tags: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    tags = tags or []
    style_key = detect_style(category, tags, title)
    images: dict[str, Any] = {
        "hero": None,
        "inline": [],
        "frontmatter_hero": None,
        "frontmatter_inline": [],
    }

    hero_path = f"images/posts/{slug}.webp"
    hero_full = os.path.join(OUTPUT_DIR, f"{slug}.webp")
    hero_exists = os.path.exists(hero_full) and not force
    if not hero_exists:
        print(f"  Generating hero: {slug}.webp")
        result = generate_image(slug, title, style_key, WIDTH, HEIGHT, write=True, seed_text=title)
        register_metric(result)
        images["hero"] = result
        images["frontmatter_hero"] = get_image_meta(slug, title, result["path"])
        print(f"    -> {result['path']} ({os.path.getsize(hero_full)} bytes)")
    else:
        print(f"  Hero exists (skip): {hero_path}")

    # Inline illustrations from H2 headings
    headings = extract_headings(body)
    used_keys = set()
    for i, h2 in enumerate(headings):
        h2_key = f"{slug}_{slugify(h2)}"
        if h2_key in used_keys:
            h2_key = f"{h2_key}_{i}"
        used_keys.add(h2_key)
        inline_path = f"images/posts/{h2_key}.webp"
        inline_full = os.path.join(OUTPUT_DIR, f"{h2_key}.webp")
        if os.path.exists(inline_full) and not force:
            print(f"    Inline exists (skip): {inline_path}")
            images["inline"].append({"path": inline_path, "heading": h2})
            images["frontmatter_inline"].append(get_image_meta(h2_key, h2, inline_path, is_inline=True))
            continue
        print(f"  Generating inline: {h2_key}.webp (h2: {h2[:50]})")
        result = generate_image(h2_key, h2, style_key, INLINE_W, INLINE_H, write=True, seed_text=h2)
        register_metric(result)
        images["inline"].append({"path": result["path"], "heading": h2})
        images["frontmatter_inline"].append(get_image_meta(h2_key, h2, result["path"], is_inline=True))
        fsize = os.path.getsize(inline_full)
        print(f"    -> {result['path']} ({fsize} bytes)")

    return images


def register_metric(result: dict) -> None:
    reg = _load_registry()
    reg["items"][result["slug"]] = registry_item(result)
    reg["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    _save_registry(reg)


def write_frontmatter(post_path: str, meta: dict[str, Any]) -> None:
    import frontmatter
    post = frontmatter.load(post_path)
    m = post.metadata
    stale_fields = ["image_reject_reason", "image_attribution_checked_at", "image_query",
                     "image_semantic_score", "image_color_score", "image_total_score",
                     "image_creator_id"]
    for k in stale_fields:
        m.pop(k, None)
    for k, v in meta.items():
        m[k] = v
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    print(f"  Updated frontmatter: {os.path.basename(post_path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate self-hosted editorial images")
    parser.add_argument("--post", type=str, help="Single post path to process")
    parser.add_argument("--all", action="store_true", help="Process all posts in content/posts/")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
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
        content_dir = "content/posts"
        if not os.path.isdir(content_dir):
            print(f"ERROR: {content_dir} not found")
            return 1
        posts_to_process = sorted(os.path.join(content_dir, f) for f in os.listdir(content_dir) if f.endswith(".md"))

    if not posts_to_process:
        print("ERROR: Use --post <path> or --all")
        return 1

    import frontmatter

    results = {"processed": 0, "hero_generated": 0, "inline_generated": 0, "errors": []}

    for fpath in posts_to_process:
        try:
            post = frontmatter.load(fpath)
        except Exception as e:
            print(f"ERROR reading {fpath}: {e}")
            results["errors"].append(fpath)
            continue

        meta = post.metadata
        slug = meta.get("slug", os.path.basename(fpath).replace(".md", ""))
        title = meta.get("title", slug)
        body = post.content or ""
        category = meta.get("categories", "")
        if isinstance(category, list):
            category = category[0] if category else ""
        tags = list(meta.get("tags", []) or [])

        print(f"\n=== {slug} ===")

        if args.dry_run:
            style_key = detect_style(category, tags, title)
            print(f"  Title: {title}")
            print(f"  Style: {style_key}")
            headings = extract_headings(body)
            print(f"  H2 sections: {len(headings)}")
            print(f"  Would generate: hero + {len(headings)} inline illustrations")
            results["processed"] += 1
            continue

        imgs = generate_for_post(slug, title, body, category, tags, force=args.force)

        if imgs["hero"]:
            write_frontmatter(fpath, imgs["frontmatter_hero"])
            results["hero_generated"] += 1

        if not args.skip_inline and imgs["frontmatter_inline"]:
            inline_meta = {}
            inline_paths = []
            for fm in imgs["frontmatter_inline"]:
                p = fm["image"]
                inline_paths.append(p)
            inline_meta["inline_images"] = inline_paths
            inline_meta["inline_image_count"] = len(inline_paths)
            if imgs["inline"]:
                inline_meta["inline_illustrations"] = [
                    {"heading": x["heading"], "image": x["path"]} for x in imgs["inline"]
                ]
            write_frontmatter(fpath, inline_meta)
            results["inline_generated"] += len(imgs["frontmatter_inline"])

        results["processed"] += 1

    print(f"\n=== Summary ===")
    print(f"  Posts processed: {results['processed']}")
    print(f"  Hero images generated: {results['hero_generated']}")
    print(f"  Inline illustrations generated: {results['inline_generated']}")
    if results["errors"]:
        print(f"  Errors: {len(results['errors'])}")
        for e in results["errors"]:
            print(f"    - {e}")

    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())