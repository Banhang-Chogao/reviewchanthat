#!/usr/bin/env python3
"""
Audit all post slugs for consistency.

Fails if:
- filename != canonical slug from title
- front matter slug != slugify(title)
- front matter url (if present) doesn't match canonical slug
- aliases exist that only serve old URLs
"""

import os
import sys

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slug_utils import slugify_vi, url_from_slug

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "posts")


def main():
    if not os.path.isdir(CONTENT_DIR):
        print(f"OK: {CONTENT_DIR} does not exist")
        sys.exit(0)

    errors = []
    warnings = []
    total = 0

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        total += 1
        fpath = os.path.join(CONTENT_DIR, fname)
        file_slug = fname.replace('.md', '')

        with open(fpath, 'r', encoding='utf-8') as f:
            try:
                post = frontmatter.load(f)
            except Exception as e:
                errors.append(f"{fname}: cannot parse front matter: {e}")
                continue

        meta = post.metadata
        title = meta.get('title', '')
        if isinstance(title, list):
            title = ' '.join(str(t) for t in title)
        title = str(title).strip()

        if not title:
            errors.append(f"{fname}: no title found")
            continue

        canonical_slug = slugify_vi(title)

        # 1. Check filename matches canonical slug
        if file_slug != canonical_slug:
            errors.append(
                f"{fname}: filename '{file_slug}' != canonical slug '{canonical_slug}' "
                f"(from title: '{title[:60]}...')"
            )

        # 2. Check front matter slug matches
        fm_slug = meta.get('slug', '')
        if fm_slug:
            if fm_slug != canonical_slug:
                errors.append(
                    f"{fname}: front matter slug '{fm_slug}' != canonical slug '{canonical_slug}'"
                )
        else:
            warnings.append(f"{fname}: no slug field in front matter")

        # 3. Check url field if present
        fm_url = meta.get('url', '')
        if fm_url:
            expected_url = url_from_slug(canonical_slug).rstrip('/')
            cleaned_url = fm_url.rstrip('/')
            if cleaned_url != expected_url:
                errors.append(
                    f"{fname}: front matter url '{fm_url}' != expected '{expected_url}'"
                )

        # 4. Check aliases
        aliases = meta.get('aliases', [])
        if aliases:
            for alias in aliases:
                alias_slug = alias.strip().lstrip('/').rstrip('/')
                if alias_slug == canonical_slug or alias_slug == file_slug:
                    warnings.append(
                        f"{fname}: alias '{alias}' appears to be current slug — remove it"
                    )

    print(f"\nAudit Results:")
    print(f"  Total posts:  {total}")
    print(f"  Errors:       {len(errors)}")
    print(f"  Warnings:     {len(warnings)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        print("\n❌ SLUG AUDIT FAILED")
        sys.exit(1)
    else:
        print("\n✅ SLUG AUDIT PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
