#!/usr/bin/env python3
"""Release gate for local, responsive blog image delivery.

This is intentionally a source/build-input check. It does not require a Hugo
build and rejects the regressions that are otherwise only visible in a
waterfall: remote runtime images, missing dimensions, missing variants and
over-large card/article derivatives.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import tomllib


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content/posts"
STATIC = ROOT / "static"
ASSET_INDEX = ROOT / "data/image-assets.json"
CARD_HARD_LIMIT = 150 * 1024
ARTICLE_HARD_LIMIT = 350 * 1024
REMOTE_IMAGE = re.compile(r"(?:<img\b[^>]*(?:src|srcset)\s*=\s*['\"]https?://|background-image\s*:\s*url\(\s*['\"]?https?://)", re.I | re.S)
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I | re.S)


def frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++"):
        return {}, text
    lines = text.splitlines(keepends=True)
    closing = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "+++"), None)
    if closing is None:
        raise ValueError("missing TOML front matter terminator")
    fm = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    return tomllib.loads(fm), body


def fail(issues: list[str], message: str) -> None:
    issues.append(message)


def local_post_asset_key(value: str) -> str | None:
    """Return the indexed key for a local post image, if it needs variants."""
    clean = value.split("#", 1)[0].split("?", 1)[0].lstrip("/")
    if not clean.startswith("images/posts/"):
        return None
    stem = Path(clean).stem
    return None if stem == "fallback" else stem


def check_posts(issues: list[str], assets: dict) -> int:
    posts = 0
    for path in sorted(CONTENT.glob("*.md")):
        try:
            meta, body = frontmatter(path)
        except Exception as exc:
            fail(issues, f"{path}: TOML parse error: {exc}")
            continue
        posts += 1
        for field in ("image", "thumbnail"):
            value = str(meta.get(field, ""))
            if value.startswith(("http://", "https://")):
                fail(issues, f"{path}: remote runtime {field}: {value}")
            elif value:
                asset = STATIC / value.lstrip("/")
                if not asset.is_file():
                    fail(issues, f"{path}: missing local {field}: {value}")
                else:
                    key = local_post_asset_key(value)
                    if key and key not in assets:
                        fail(issues, f"{path}: local {field} has no responsive variant index: {value}")
        for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", body):
            destination = match.group(1).split()[0]
            if destination.startswith(("http://", "https://", "//")):
                fail(issues, f"{path}: remote inline image: {destination}")
            else:
                key = local_post_asset_key(destination)
                if key and key not in assets:
                    fail(issues, f"{path}: inline image has no responsive variant index: {destination}")
    return posts


def load_assets(issues: list[str]) -> dict:
    if not ASSET_INDEX.is_file():
        fail(issues, "data/image-assets.json is missing; run build_image_variants.py")
        return {}
    try:
        data = json.loads(ASSET_INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(issues, f"data/image-assets.json is invalid JSON: {exc}")
        return {}
    return data.get("assets", {})


def check_index(issues: list[str], assets: dict) -> tuple[int, int, int]:
    card_bytes = []
    article_bytes = []
    for key, asset in sorted(assets.items()):
        for role, limit, sizes in (
            ("card", CARD_HARD_LIMIT, card_bytes),
            ("article", ARTICLE_HARD_LIMIT, article_bytes),
        ):
            role_data = asset.get(role, {})
            for fmt in ("avif", "webp", "jpeg"):
                fmt_data = role_data.get(fmt, {})
                variants = fmt_data.get("variants", [])
                if not variants:
                    fail(issues, f"{key}: missing {role}/{fmt} variants")
                for variant in variants:
                    path = STATIC / str(variant.get("src", "")).lstrip("/")
                    if not path.is_file():
                        fail(issues, f"{key}: missing variant file: {path.relative_to(ROOT) if path.is_absolute() else path}")
                        continue
                    actual_bytes = path.stat().st_size
                    sizes.append(actual_bytes)
                    if actual_bytes > limit:
                        fail(issues, f"{key}: {role}/{fmt} exceeds {limit // 1024}KiB: {path.name} ({actual_bytes} bytes)")
                    if not variant.get("width") or not variant.get("height"):
                        fail(issues, f"{key}: {role}/{fmt} variant has no dimensions: {path.name}")
    return len(assets), max(card_bytes or [0]), max(article_bytes or [0])


def check_templates(issues: list[str]) -> int:
    count = 0
    for directory in (ROOT / "layouts/partials", ROOT / "layouts/posts", ROOT / "layouts/_default", ROOT / "layouts/shortcodes"):
        for path in directory.rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if REMOTE_IMAGE.search(text):
                fail(issues, f"{path.relative_to(ROOT)}: remote image URL in runtime template")
            for tag in IMG_TAG.findall(text):
                count += 1
                if not re.search(r"\bwidth\s*=", tag) or not re.search(r"\bheight\s*=", tag):
                    fail(issues, f"{path.relative_to(ROOT)}: <img> lacks explicit width/height: {tag[:160]}")
    return count


def main() -> int:
    issues: list[str] = []
    assets = load_assets(issues)
    posts = check_posts(issues, assets)
    asset_count, max_card, max_article = check_index(issues, assets)
    img_tags = check_templates(issues)
    print("=== Image performance QA ===")
    print(f"Posts checked: {posts}; assets indexed: {asset_count}; template img tags: {img_tags}")
    print(f"Largest card derivative: {max_card} bytes; largest article derivative: {max_article} bytes")
    if issues:
        print(f"FAIL: {len(issues)} issue(s)")
        for issue in issues[:120]:
            print(f"  - {issue}")
        if len(issues) > 120:
            print(f"  ... {len(issues) - 120} more")
        return 1
    print("PASS: local runtime images, dimensions and responsive variants are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
