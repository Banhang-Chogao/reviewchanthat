#!/usr/bin/env python3
"""
Generate sitemap-posts.xml — only blog post URLs, no structural pages.

Reads the Hugo-built public/ directory, extracts only URLs that
match content/posts/ slug pattern, and writes a clean sitemap.

Usage: python scripts/gen_posts_sitemap.py [--public-dir public]
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"
PUBLIC_DIR = "public"
POST_PATTERN = re.compile(r"^/?posts/")
# Pagination list pages (posts/page/2/…) and the posts section root are not
# canonical content — they must never appear in a sitemap.
PAGE_PATTERN = re.compile(r"(^|/)page/\d+/")
SECTION_ROOT = "posts/index.html"
# A post rendered with noindex carries the same robots meta Hugo emits in
# layouts/partials/seo.html. Advertising a noindex URL in a sitemap triggers
# GSC "Submitted URL marked 'noindex'" errors, so skip those posts here too.
NOINDEX_RE = re.compile(r'<meta[^>]+name=["\']?robots["\']?[^>]+noindex', re.I)
SITEMAP_FILENAME = "sitemap-posts.xml"
PRIORITY = "0.8"
CHANGEFREQ = "weekly"


def is_noindex(full_path: str) -> bool:
    try:
        with open(full_path, encoding="utf-8") as handle:
            return bool(NOINDEX_RE.search(handle.read()))
    except OSError:
        return False


def collect_html_files(root: str) -> list[str]:
    html_files: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            if not (rel.startswith("posts/") or POST_PATTERN.match(rel)):
                continue
            if rel == SECTION_ROOT or PAGE_PATTERN.search(rel):
                continue
            if is_noindex(full):
                continue
            html_files.append(rel)
    return sorted(html_files)


def build_sitemap(urls: list[str], base: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in urls:
        url = f"{base.rstrip('/')}/{path}".replace("/./", "/")
        url = url.replace("/index.html", "")
        if not url.endswith("/"):
            url += "/"
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(url)}</loc>")
        lines.append(f"    <lastmod>{now}</lastmod>")
        lines.append(f"    <changefreq>{CHANGEFREQ}</changefreq>")
        lines.append(f"    <priority>{PRIORITY}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate posts-only sitemap")
    parser.add_argument("--public-dir", default=PUBLIC_DIR, help="Hugo output directory (default: public)")
    args = parser.parse_args()

    if not os.path.isdir(args.public_dir):
        print(f"ERROR: {args.public_dir} not found. Run hugo first.")
        return 1

    urls = collect_html_files(args.public_dir)
    if not urls:
        print(f"WARNING: No post URLs found in {args.public_dir}")
        return 0

    sitemap = build_sitemap(urls, BASE_URL)
    out_path = os.path.join(args.public_dir, SITEMAP_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"Generated {out_path} with {len(urls)} post URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())