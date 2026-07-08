#!/usr/bin/env python3
"""
QA audit for SEO indexing policy.

Verifies the built `public/` output:
- All pages are indexed by default unless they have noindex, private, or draft in frontmatter.
- sitemap.xml contains only post URLs (no category/tag/about/pagination).

Usage:
    python scripts/qa_seo_indexing.py [path/to/public]
"""

import os
import re
import sys
import glob

PUBLIC = sys.argv[1] if len(sys.argv) > 1 else "public"

INDEX_ROBOTS = 'content="index,follow'
NOINDEX_ROBOTS = 'content="noindex,follow"'

errors = []
ok = []


def check_file(path, expected_index, label):
    if not os.path.exists(path):
        if "pagination" in label:
            ok.append(f"SKIP (no pagination): {label}")
            return
        errors.append(f"MISSING: {label} ({path})")
        return
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    if expected_index:
        if INDEX_ROBOTS in html:
            ok.append(f"OK index: {label}")
        else:
            errors.append(f"NOT INDEXED: {label} should be index,follow")
    else:
        if NOINDEX_ROBOTS in html:
            ok.append(f"OK noindex: {label}")
        else:
            errors.append(f"NOT NOINDEX: {label} should be noindex,follow")


# Posts: index (exclude section list page and its pagination)
post_pages = sorted(glob.glob(os.path.join(PUBLIC, "posts", "**", "index.html"), recursive=True))
post_pages = [
    p for p in post_pages
    if not re.search(r"/posts/index\.html$", p)
    and not re.search(r"/posts/page/\d+/index\.html$", p)
]
indexed_posts = 0
for p in post_pages:
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()
    if INDEX_ROBOTS in html:
        indexed_posts += 1
    else:
        errors.append(f"POST NOT INDEXED: {p}")
ok.append(f"Posts indexed: {indexed_posts}/{len(post_pages)}")

# Indexable pages (home, about, categories, tags, pagination should all be indexable now)
check_file(os.path.join(PUBLIC, "index.html"), True, "home")
check_file(os.path.join(PUBLIC, "about", "index.html"), True, "about")
check_file(os.path.join(PUBLIC, "review", "index.html"), True, "category review")
check_file(os.path.join(PUBLIC, "cong-nghe", "index.html"), True, "category cong-nghe")
check_file(os.path.join(PUBLIC, "doi-song", "index.html"), True, "category doi-song")
check_file(os.path.join(PUBLIC, "tai-chinh", "index.html"), True, "category tai-chinh")
check_file(os.path.join(PUBLIC, "tags", "index.html"), True, "tags index")
check_file(os.path.join(PUBLIC, "page", "2", "index.html"), True, "pagination page/2")
check_file(os.path.join(PUBLIC, "review", "page", "2", "index.html"), True, "pagination review/page/2 (if present)")

# Sitemap
sitemap_path = os.path.join(PUBLIC, "sitemap.xml")
if not os.path.exists(sitemap_path):
    errors.append("MISSING: sitemap.xml")
else:
    with open(sitemap_path, "r", encoding="utf-8") as f:
        sm = f.read()
    locs = re.findall(r"<loc>(.*?)</loc>", sm)
    bad = [u for u in locs if not re.search(r"/reviewchanthat/posts/", u)]
    if bad:
        errors.append(f"SITEMAP has non-post URLs: {bad[:5]}")
    else:
        ok.append(f"Sitemap contains only post URLs: {len(locs)}")

print("\n".join(ok))
if errors:
    print("\nERRORS:")
    print("\n".join(errors))
    sys.exit(1)
print("\nSEO indexing QA PASSED")
