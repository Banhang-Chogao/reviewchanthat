#!/usr/bin/env python3
"""QA internal links — validate no broken internal links in built site.

Scans public/ directory for HTML files, extracts all internal links
to /reviewchanthat/posts/*, and verifies target pages exist.

Usage:
  python scripts/qa_internal_links.py           # check public/
  python scripts/qa_internal_links.py --public-dir public
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = REPO_ROOT / "public"
SITE_ROOT = "https://banhang-chogao.github.io/reviewchanthat/"
POSTS_ROOT = SITE_ROOT + "posts/"

# Match any href containing /reviewchanthat/posts/ (with or without quotes)
HREF_POSTS_RE = re.compile(r'href[=:][\s]*(?:"|\')?(?:https?://[^/]+)?/reviewchanthat/posts/([^"\' >]+)')


def main() -> int:
    parser = argparse.ArgumentParser(description="Check internal links in built site")
    parser.add_argument("--public-dir", default=str(PUBLIC_DIR))
    args = parser.parse_args()

    public = Path(args.public_dir)
    if not public.is_dir():
        print(f"FAIL: public directory not found: {public}", file=sys.stderr)
        return 1

    html_files = sorted(public.rglob("*.html"))
    if not html_files:
        print("FAIL: no HTML files in public directory", file=sys.stderr)
        return 1

    # Build set of existing post slugs (URL-decoded)
    existing_posts: set[str] = set()
    for html in html_files:
        rel = str(html.relative_to(public).as_posix())
        if rel.startswith("posts/") and rel.endswith("/index.html"):
            slug = rel[len("posts/"):-len("/index.html")]
            existing_posts.add(urllib.parse.unquote(slug))

    errors: list[str] = []
    scanned = 0

    for html in html_files:
        text = html.read_text(encoding="utf-8", errors="replace")
        for m in HREF_POSTS_RE.finditer(text):
            slug = m.group(1)
            # Remove trailing / or /index.html
            slug = slug.rstrip("/")
            if slug.endswith("/index.html"):
                slug = slug[:-len("/index.html")]
            if not slug:
                continue
            scanned += 1
            # Normalize URL encoding
            slug = urllib.parse.unquote(slug)
            if slug not in existing_posts:
                source = str(html.relative_to(public))
                errors.append(f"Broken link in {source}: posts/{slug}")

    if errors:
        for e in errors[:30]:
            print(f"FAIL: {e}", file=sys.stderr)
        if len(errors) > 30:
            print(f"FAIL: ... and {len(errors) - 30} more", file=sys.stderr)
        print(f"\nqa_internal_links: {len(errors)} broken link(s), {scanned} scanned")
        return 1

    print(f"qa_internal_links: PASS — {scanned} links scanned, 0 broken")
    return 0


if __name__ == "__main__":
    main()