#!/usr/bin/env python3
"""Post-build link audit for Hugo site.

Run after `hugo --minify`. Checks all internal links in public/ output:
- No missing /reviewchanthat/ base path
- No broken internal links
- No hardcoded banhang-chogao.github.io URLs without project path
- Search index, sitemap, RSS URLs are correct
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
SITE_DOMAIN = "banhang-chogao.github.io"


def load_base_url():
    try:
        import tomllib
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "hugo.toml"), "rb") as f:
            cfg = tomllib.load(f)
        return cfg.get("baseURL", f"https://{SITE_DOMAIN}/reviewchanthat/")
    except Exception:
        return f"https://{SITE_DOMAIN}/reviewchanthat/"


def extract_hrefs(html):
    """Extract all href values from HTML (quoted or unquoted), deduplicated."""
    seen = set()
    hrefs = []
    for m in re.finditer(r'href\s*=\s*"([^"]*)"', html):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            hrefs.append(v)
    for m in re.finditer(r"href\s*=\s*'([^']*)'", html):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            hrefs.append(v)
    for m in re.finditer(r'href\s*=\s*([^\s>"\'=]+)', html):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            hrefs.append(v)
    return hrefs


def exists_in_public(path, public_dir, base_path):
    from urllib.parse import unquote
    path = path.split("?")[0].split("#")[0].rstrip("/") or "/"
    if path.startswith("http"):
        parsed = urlparse(path)
        if parsed.hostname == SITE_DOMAIN:
            path = unquote(parsed.path).rstrip("/") or "/"
        else:
            return True
    path = unquote(path)
    # Strip base path prefix for filesystem lookup
    if base_path and path.startswith(base_path):
        path = path[len(base_path):] or "/"
    candidates = [
        os.path.join(public_dir, path.lstrip("/"), "index.html"),
        os.path.join(public_dir, path.lstrip("/")),
    ]
    return any(os.path.exists(c) for c in candidates)


def check_href(href, rel, base_path, errors):
    if not href or href.startswith(("#", "mailto:", "tel:", "//", "javascript:")):
        return

    # Hardcoded domain URL without base path
    if SITE_DOMAIN in href:
        parsed = urlparse(href)
        if parsed.hostname == SITE_DOMAIN and base_path not in parsed.path:
            errors.append(f"  {rel}: hardcoded URL missing base path: {href}")

    # Root-relative without base path
    if href.startswith("/") and SITE_DOMAIN not in href:
        if not href.startswith(base_path):
            errors.append(f"  {rel}: root-relative without base path: {href}")

    # Broken internal link
    is_internal = href.startswith("/") or base_path in href or SITE_DOMAIN in href
    if is_internal and not href.startswith("//"):
        if not exists_in_public(href, PUBLIC_DIR, base_path):
            errors.append(f"  {rel}: broken link (no public file): {href}")


def main():
    base_url = load_base_url()
    base_path = urlparse(base_url).path.rstrip("/")
    if not base_path:
        base_path = "/reviewchanthat"

    errors = []
    total = 0

    print(f"=== Link Audit: {base_url} ===")
    print(f"Base path: {base_path}\n")

    # 1. HTML files
    for root, dirs, files in os.walk(PUBLIC_DIR):
        for fname in files:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, PUBLIC_DIR)
            with open(fpath, "r", encoding="utf-8") as f:
                html = f.read()
            for href in extract_hrefs(html):
                total += 1
                check_href(href, rel, base_path, errors)

    # 2. Search index
    si_path = os.path.join(PUBLIC_DIR, "search-index.json")
    if os.path.exists(si_path):
        with open(si_path, "r", encoding="utf-8") as f:
            try:
                si = json.load(f)
                for item in si if isinstance(si, list) else []:
                    uri = item.get("uri", "")
                    if uri and not uri.startswith(base_path):
                        errors.append(f"  search-index.json: URL missing base path: {uri}")
                print(f"  Search index: {len(si) if isinstance(si, list) else 0} entries")
            except json.JSONDecodeError as e:
                errors.append(f"  search-index.json: invalid JSON ({e})")

    # 3. Sitemap
    sm_path = os.path.join(PUBLIC_DIR, "sitemap.xml")
    if os.path.exists(sm_path):
        with open(sm_path, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"<loc>([^<]+)</loc>", content):
            url = m.group(1)
            if SITE_DOMAIN in url and base_path not in urlparse(url).path:
                errors.append(f"  sitemap.xml: URL missing base path: {url}")
        print(f"  Sitemap: {len(re.findall(r'<loc>', content))} URLs")

    # 4. RSS
    rss_path = os.path.join(PUBLIC_DIR, "index.xml")
    if os.path.exists(rss_path):
        with open(rss_path, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"<link>([^<]+)</link>", content):
            url = m.group(1)
            if SITE_DOMAIN in url and base_path not in urlparse(url).path:
                errors.append(f"  index.xml: RSS link missing base path: {url}")
        print("  RSS feed checked")

    # Summary
    print(f"\n  Total links checked: {total}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors:
            print(e)
        print("\n❌ LINK AUDIT FAILED")
        sys.exit(1)
    else:
        print("\n✅ LINK AUDIT PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
