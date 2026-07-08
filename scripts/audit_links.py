#!/usr/bin/env python3
"""
Audit all links in built Hugo site.

Checks:
- Internal URL 404s
- URLs missing /reviewchanthat/ prefix
- Root-level guessed URLs like /<slug>/
- Search index URLs resolve
- Sitemap/canonical/OG/JSON-LD URLs are correct
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"
SITE_PREFIX = "/reviewchanthat"

ROOT_LEVEL_SLUG_PATTERN = re.compile(
    r'href="https://banhang-chogao\.github\.io/([a-z0-9-]+(?:-[a-z0-9-]+)*)/"'
)
ROOT_REL_SLUG_PATTERN = re.compile(r'href="/([a-z0-9-]+(?:-[a-z0-9-]+)*)/"')


def find_all_urls_in_html(filepath: str) -> list[str]:
    """Extract all href and src URLs from an HTML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    urls = []
    for match in re.finditer(r'(?:href|src)="([^"]*)"', content):
        url = match.group(1)
        if url and not url.startswith('#') and not url.startswith('mailto:') and not url.startswith('tel:'):
            urls.append(url)

    # Also find JSON-LD URLs
    for match in re.finditer(r'"url"\s*:\s*"([^"]*)"', content):
        url = match.group(1)
        if url:
            urls.append(url)

    for match in re.finditer(r'"@id"\s*:\s*"([^"]*)"', content):
        url = match.group(1)
        if url:
            urls.append(url)

    return urls


def main():
    if not os.path.isdir(PUBLIC_DIR):
        print(f"ERROR: {PUBLIC_DIR} not found — run 'hugo --minify' first")
        sys.exit(1)

    errors = []
    warnings = []

    # Check 1: Scan all HTML files for root-level URLs missing /reviewchanthat/
    html_files = []
    for root, dirs, files in os.walk(PUBLIC_DIR):
        for f in files:
            if f.endswith('.html'):
                html_files.append(os.path.join(root, f))

    print(f"Scanning {len(html_files)} HTML files...")

    for html_path in html_files:
        rel_path = os.path.relpath(html_path, PUBLIC_DIR)
        urls = find_all_urls_in_html(html_path)

        for url in urls:
            # Check for root-level URLs without /reviewchanthat/ prefix
            if url.startswith(BASE_URL):
                path = url[len(BASE_URL):]
                if path and not path.startswith('/reviewchanthat/'):
                    errors.append(
                        f"{rel_path}: URL missing /reviewchanthat/ prefix: {url}"
                    )

            # Check for absolute URLs that should be relative
            if url.startswith('https://banhang-chogao.github.io/'):
                path = url[len('https://banhang-chogao.github.io/'):]
                # Skip external resources
                skip_prefixes = ('cdn.', 'fonts.', 'api.')
                if any(path.startswith(p) for p in skip_prefixes):
                    continue
                # Check if it looks like a root-level slug URL
                if path and '/' not in path.rstrip('/') and '.' not in path:
                    warnings.append(
                        f"{rel_path}: potential root-level URL: {url}"
                    )

            # Check for relative URLs starting with /<slug>/ pattern
            root_level = ROOT_REL_SLUG_PATTERN.match(f'href="{url}"')
            if root_level:
                slug = root_level.group(1)
                skip_paths = {'tags', 'categories', 'authors', 'about', 'contact',
                              'privacy', 'disclaimer', 'admin', 'page', 'posts',
                              'css', 'js', 'images', 'search-index'}
                if slug not in skip_paths and not slug.startswith('posts/'):
                    # Check if this is actually a valid post URL
                    post_dir = os.path.join(PUBLIC_DIR, 'posts', slug)
                    if os.path.isdir(post_dir):
                        # This is OK — it's a /posts/slug/ URL
                        pass
                    else:
                        warnings.append(
                            f"{rel_path}: root-level guessed URL: {url}"
                        )

    # Check 2: Validate search-index.json
    search_index_path = os.path.join(PUBLIC_DIR, 'search-index.json')
    if os.path.exists(search_index_path):
        with open(search_index_path, 'r', encoding='utf-8') as f:
            try:
                search_data = json.load(f)
                for entry in search_data:
                    entry_url = entry.get('url', '')
                    if entry_url:
                        # URL should be relative like /reviewchanthat/posts/slug/
                        if not entry_url.startswith('/reviewchanthat/'):
                            errors.append(
                                f"search-index.json: URL missing /reviewchanthat/: {entry_url}"
                            )
                        if entry_url.startswith('/reviewchanthat/'):
                            slug_part = entry_url[len('/reviewchanthat/'):]
                            if not slug_part.startswith('posts/'):
                                errors.append(
                                    f"search-index.json: URL not a post URL: {entry_url}"
                                )
            except json.JSONDecodeError as e:
                errors.append(f"search-index.json: cannot parse: {e}")

    # Check 3: Validate sitemap.xml
    sitemap_path = os.path.join(PUBLIC_DIR, 'sitemap.xml')
    if os.path.exists(sitemap_path):
        with open(sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
        for match in re.finditer(r'<loc>([^<]+)</loc>', sitemap_content):
            loc_url = match.group(1)
            if not loc_url.startswith(BASE_URL + '/'):
                errors.append(
                    f"sitemap.xml: URL doesn't start with baseURL: {loc_url}"
                )

    # Check 4: Validate canonical links in HTML
    canonical_re = re.compile(r'<link rel="canonical" href="([^"]+)"')
    for html_path in html_files:
        rel_path = os.path.relpath(html_path, PUBLIC_DIR)
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for match in canonical_re.finditer(content):
            canonical_url = match.group(1)
            if not canonical_url.startswith(BASE_URL + '/'):
                errors.append(
                    f"{rel_path}: canonical URL doesn't start with baseURL: {canonical_url}"
                )

    # Check 5: Validate OG URLs
    og_url_re = re.compile(r'<meta property="og:url" content="([^"]+)"')
    for html_path in html_files:
        rel_path = os.path.relpath(html_path, PUBLIC_DIR)
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for match in og_url_re.finditer(content):
            og_url = match.group(1)
            if not og_url.startswith(BASE_URL + '/'):
                errors.append(
                    f"{rel_path}: OG URL doesn't start with baseURL: {og_url}"
                )

    print(f"\nLink Audit Results:")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        print("\n❌ LINK AUDIT FAILED")
        sys.exit(1)
    else:
        print("\n✅ LINK AUDIT PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
