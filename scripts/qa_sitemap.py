#!/usr/bin/env python3
"""Validate public/sitemap.xml for Search Console compatibility."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

SITEMAP_PATH = os.path.join("public", "sitemap.xml")
SITE_ROOT = "https://banhang-chogao.github.io/reviewchanthat/"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
FORBIDDEN_FRAGMENTS = (
    "/about/",
    "/review/",
    "/cong-nghe/",
    "/doi-song/",
    "/tai-chinh/",
    "/tags/",
    "/series/",
    "/page/",
    "/categories/",
    "/authors/",
    "/branding-ci/",
    "/privacy/",
    "/contact/",
    "/disclaimer/",
)


def fail(message: str) -> None:
    print(f"QA SITEMAP FAILED: {message}", file=sys.stderr)


def main() -> int:
    if not os.path.isfile(SITEMAP_PATH):
        fail(f"missing file: {SITEMAP_PATH}")
        return 1

    size = os.path.getsize(SITEMAP_PATH)
    if size < 200:
        fail(f"sitemap too small ({size} bytes)")
        return 1

    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
    except ET.ParseError as exc:
        fail(f"invalid XML: {exc}")
        return 1

    if root.tag != f"{{{NS['sm']}}}urlset":
        fail(f"unexpected root tag: {root.tag}")
        return 1

    urls = root.findall("sm:url", NS)
    if not urls:
        fail("no <url> entries found")
        return 1

    errors: list[str] = []
    locs: list[str] = []

    for index, url_el in enumerate(urls, start=1):
        loc_el = url_el.find("sm:loc", NS)
        if loc_el is None or not (loc_el.text or "").strip():
            errors.append(f"url[{index}] missing <loc>")
            continue

        loc = loc_el.text.strip()
        locs.append(loc)

        if not loc.startswith(SITE_ROOT):
            errors.append(f"url[{index}] loc outside site root: {loc}")
        if loc.count(SITE_ROOT) > 1 or "reviewchanthat/reviewchanthat" in loc:
            errors.append(f"url[{index}] duplicated base URL: {loc}")
        if not loc.startswith(f"{SITE_ROOT}posts/"):
            errors.append(f"url[{index}] loc is not a post URL: {loc}")
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in loc:
                errors.append(f"url[{index}] forbidden path '{fragment}' in {loc}")

    if errors:
        for err in errors[:20]:
            fail(err)
        if len(errors) > 20:
            fail(f"... and {len(errors) - 20} more issue(s)")
        return 1

    print(f"QA SITEMAP PASSED: {len(locs)} post URL(s)")
    print(f"  file: {SITEMAP_PATH} ({size} bytes)")
    print(f"  sample: {locs[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())