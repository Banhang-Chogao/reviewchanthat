#!/usr/bin/env python3
"""
Check image attribution integrity across posts, public HTML, and reports.
Exit non-zero on hard failures.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posts"
PUBLIC_DIR = ROOT / "public"
REPORT_JSON = ROOT / "reports" / "image-attribution-report.json"
MANIFEST_PATH = ROOT / "data" / "images.json"

BLOCKED_CREATORS = {
    "unknown",
    "anonymous",
    "photographer",
    "creator",
    "admin",
    "ai",
    "generated",
    "placeholder",
    "pexels",
    "pixabay",
    "unsplash",
    "freepik",
    "wikimedia",
    "wikimedia commons",
    "review chân thật",
    "review chan that",
    "park bogum",
    "park bo-gum",
    "park bo gum",
    "bae suzy",
    "iu",
    "yoo jaesuk",
    "choi wooshik",
    "lee minho",
    "lee min ho",
    "kim soo hyun",
    "song hye kyo",
}

FAKE_HTML_PATTERNS = [
    re.compile(r"Pexels\s*/\s*Park\s*Bogum", re.I),
    re.compile(r"Pixabay\s*/\s*Unknown", re.I),
    re.compile(r"Unsplash\s*/\s*Photographer", re.I),
    re.compile(r"Pexels\s*/\s*Unknown", re.I),
]


def clean(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def norm(v) -> str:
    return " ".join(clean(v).casefold().split())


def is_blocked(name: str) -> bool:
    n = norm(name)
    return bool(n) and n in BLOCKED_CREATORS


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not CONTENT_DIR.exists():
        print("FAIL: content/posts not found")
        return 1

    for path in sorted(CONTENT_DIR.glob("*.md")):
        try:
            post = frontmatter.load(str(path))
        except Exception as e:
            errors.append(f"[PARSE] {path.name}: {e}")
            continue
        meta = post.metadata
        slug = clean(meta.get("slug")) or path.stem
        creator = clean(meta.get("image_creator"))
        creator_url = clean(meta.get("image_creator_url"))
        verified = meta.get("image_attribution_verified")
        source_url = clean(meta.get("image_source_url"))
        image = clean(meta.get("image"))

        if not image and not source_url:
            continue

        if creator and verified is not True:
            errors.append(
                f"[UNVERIFIED_CREATOR] {slug}: image_creator={creator!r} but "
                f"image_attribution_verified={verified!r}"
            )

        if is_blocked(creator):
            errors.append(f"[PLACEHOLDER_CREATOR] {slug}: {creator!r}")

        if creator_url and not creator:
            errors.append(f"[CREATOR_URL_WITHOUT_NAME] {slug}: {creator_url}")

        if image.startswith("/"):
            errors.append(f"[BAD_IMAGE_PATH] {slug}: starts with / ({image})")

        # creator must not equal slug/title
        if creator and norm(creator) in {
            norm(slug),
            norm(meta.get("title", "")),
            norm(path.stem),
        }:
            errors.append(f"[GUESSED_CREATOR] {slug}: creator matches title/slug")

        if verified is True and not creator:
            errors.append(f"[VERIFIED_WITHOUT_CREATOR] {slug}")

        if verified is False or verified is None:
            if not clean(meta.get("image_attribution_source")):
                warnings.append(f"[NO_ATTR_SOURCE] {slug}: missing image_attribution_source")

    # grep-style scan public HTML if present
    if PUBLIC_DIR.exists():
        for html in PUBLIC_DIR.rglob("*.html"):
            try:
                text = html.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for rx in FAKE_HTML_PATTERNS:
                if rx.search(text):
                    errors.append(f"[FAKE_HTML] {html.relative_to(ROOT)}: matches {rx.pattern}")

    # Report consistency (if exists)
    if REPORT_JSON.exists():
        try:
            report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
            for row in report.get("posts") or []:
                if row.get("verified") and not clean(row.get("creator")):
                    errors.append(f"[REPORT] verified without creator: {row.get('slug')}")
        except Exception as e:
            warnings.append(f"[REPORT_READ] {e}")

    print("=== check_image_attribution ===")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  WARN {w}")
    if errors:
        for e in errors:
            print(f"  FAIL {e}")
        return 1
    print("  PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
