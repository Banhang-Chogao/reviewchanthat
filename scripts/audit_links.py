#!/usr/bin/env python3
"""Audit internal links after `hugo --minify`.

Scans public/ HTML, sitemap.xml and search-index.json. Any internal link
(same-domain or root-relative) that does not resolve to a generated file is
reported as broken. External links are ignored.

Run AFTER `hugo --minify`.
"""

import json
import os
import re
import sys
import glob
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
REPORT = os.path.join(ROOT, "reports")

HREF_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']')
CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
OG_RE = re.compile(r'property="og:url"\s+content="([^"]+)"', re.I)
JSONLD_URL_RE = re.compile(r'"@id"\s*:\s*"([^"]+)"|"url"\s*:\s*"([^"]+)"')


def normalize_internal(url):
    """Return public-relative path if internal, else None."""
    if url.startswith("#") or url.startswith("mailto:") or url.startswith("tel:"):
        return None
    # ignore JS template fragments mistakenly captured from minified scripts
    if "{" in url or "$" in url or "<" in url or ">" in url:
        return None
    parsed = urlparse(url)
    if parsed.netloc:
        # only treat banhang-chogao.github.io as internal
        if "banhang-chogao.github.io" not in parsed.netloc:
            return None
        path = parsed.path
    else:
        path = parsed.path
    if not path or path == "/":
        return None
    # strip the GitHub Pages project base path from the path segment
    path = unquote(path.lstrip("/"))
    if path.startswith("reviewchanthat/"):
        path = path[len("reviewchanthat/"):]
    return path


def exists_in_public(rel):
    # public is the site root; rel paths map directly
    cand = os.path.join(PUBLIC, rel)
    if os.path.exists(cand):
        return True
    # hugo generates dir/index.html; also accept dir/
    if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "index.html")):
        return True
    return False


def main():
    if not os.path.isdir(PUBLIC):
        print("ERROR: public/ not found. Run `hugo --minify` first.")
        sys.exit(1)
    os.makedirs(REPORT, exist_ok=True)

    collected = set()
    broken = []

    html_files = glob.glob(os.path.join(PUBLIC, "**", "*.html"), recursive=True)
    for hf in html_files:
        try:
            c = open(hf, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for m in HREF_RE.finditer(c):
            u = m.group(1)
            rel = normalize_internal(u)
            if rel is not None:
                collected.add(rel)
        # canonical / og:url should be absolute internal
        for mm in CANON_RE.finditer(c):
            rel = normalize_internal(mm.group(1))
            if rel:
                collected.add(rel)
        for mm in OG_RE.finditer(c):
            rel = normalize_internal(mm.group(1))
            if rel:
                collected.add(rel)

    # sitemap
    sm = os.path.join(PUBLIC, "sitemap.xml")
    if os.path.exists(sm):
        c = open(sm, encoding="utf-8", errors="ignore").read()
        for loc in re.findall(r"<loc>([^<]+)</loc>", c):
            rel = normalize_internal(loc)
            if rel:
                collected.add(rel)

    # search index
    si = os.path.join(PUBLIC, "search-index.json")
    if os.path.exists(si):
        try:
            data = json.load(open(si, encoding="utf-8"))
            for entry in data:
                u = entry.get("url") or entry.get("permalink")
                if u:
                    rel = normalize_internal(u)
                    if rel:
                        collected.add(rel)
        except Exception:
            pass

    for rel in sorted(collected):
        if not exists_in_public(rel):
            broken.append(rel)

    summary = {"total_internal_links": len(collected), "broken": len(broken)}
    report = {"summary": summary, "broken": broken}
    json.dump(report, open(os.path.join(REPORT, "broken-internal-links.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    md = ["# Broken internal links", "", f"- Checked: {summary['total_internal_links']}", f"- Broken: {summary['broken']}", ""]
    for b in broken:
        md.append(f"- /{b}")
    open(os.path.join(REPORT, "broken-internal-links.md"), "w", encoding="utf-8").write("\n".join(md))

    if broken:
        print(f"❌ audit_links FAILED: {len(broken)} broken internal links")
        for b in broken[:30]:
            print(f"  - /{b}")
        sys.exit(1)
    print(f"✅ audit_links PASSED: {len(collected)} internal links, 0 broken")
    sys.exit(0)


if __name__ == "__main__":
    main()
