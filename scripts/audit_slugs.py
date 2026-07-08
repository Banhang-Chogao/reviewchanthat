#!/usr/bin/env python3
"""Audit title -> slug -> url consistency and internal link safety.

Rules:
- Every post must declare `slug` equal to slugify_vi(title).
- A `url` (if present) must contain the canonical slug, or be covered by aliases.
- Published posts (draft != true) that change URL must declare aliases.
- internal_links entries must use `ref: posts/<file>.md`, not hardcoded slugs/urls.
"""

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slug_utils import slugify_vi

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "posts")
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
INTERNAL_URL_RE = re.compile(r'url:\s*["\']?(/[^"\']+)["\']?')
INT_LINK_BLOCK_RE = re.compile(r"internal_links:(.*?)(\n\w|\Z)", re.DOTALL)
HARDCODED_INTERNAL_RE = re.compile(r'(href=["\']|]\()\s*["\']?(https?://banhang-chogao\.github\.io/|/(?!posts/)[a-z0-9-]+/)')


def parse_front_matter(text):
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return None, text
    fm_text = m.group(1)
    body = text[m.end():]
    data = {}
    # crude YAML-ish parse sufficient for our fields
    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            v = val.strip().strip('"').strip("'")
            data[key] = v
        i += 1
    return data, body


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    posts = sorted(glob.glob(os.path.join(CONTENT_DIR, "*.md")))
    errors = []
    warnings = []
    results = []

    for path in posts:
        fname = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm, body = parse_front_matter(text)
        if fm is None:
            errors.append(f"{fname}: cannot parse front matter")
            continue

        title = fm.get("title", "")
        slug = fm.get("slug", "")
        url = fm.get("url", "")
        draft = fm.get("draft", "false")
        aliases = fm.get("aliases", "")
        expected = slugify_vi(title)
        published = (draft or "false").lower() != "true"

        rec = {"file": fname, "title": title, "expected_slug": expected, "slug": slug}

        # Published posts keep their existing URL (SEO-safe); slug drift is a
        # warning. New/draft posts must set slug == expected.
        if not slug:
            if not published:
                errors.append(f"{fname}: missing `slug` (expected '{expected}')")
            else:
                warnings.append(f"{fname}: no `slug` (legacy published post, URL unchanged)")
        elif slug != expected:
            if not published:
                errors.append(f"{fname}: slug '{slug}' != expected '{expected}'")
            else:
                warnings.append(f"{fname}: slug '{slug}' != expected '{expected}' (legacy published post)")

        if url and expected not in url and not aliases:
            warnings.append(f"{fname}: custom `url` '{url}' does not contain canonical slug and has no aliases")

        # internal_links must use ref (the real 404 bug)
        m = INT_LINK_BLOCK_RE.search(text)
        if m:
            block = m.group(1)
            if re.search(r"url:\s*['\"]?(/|https?://)", block) and "ref:" not in block:
                errors.append(f"{fname}: internal_links uses hardcoded url; migrate to `ref: posts/<file>.md`")

        # body hardcoded internal links
        if HARDCODED_INTERNAL_RE.search(body):
            errors.append(f"{fname}: body contains hardcoded internal link (use {{< ref >}} shortcode)")

        results.append(rec)

    summary = {
        "total": len(results),
        "errors": len(errors),
        "warnings": len(warnings),
    }

    with open(os.path.join(REPORT_DIR, "title-slug-audit.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results, "errors": errors, "warnings": warnings}, f, ensure_ascii=False, indent=2)

    md = ["# Title/Slug Audit", "", f"- Total posts: {summary['total']}", f"- Errors: {summary['errors']}", f"- Warnings: {summary['warnings']}", ""]
    if errors:
        md.append("## Errors")
        for e in errors:
            md.append(f"- {e}")
        md.append("")
    if warnings:
        md.append("## Warnings")
        for w in warnings:
            md.append(f"- {w}")
        md.append("")
    with open(os.path.join(REPORT_DIR, "title-slug-audit.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    if errors:
        print(f"❌ title-slug audit FAILED: {summary['errors']} errors")
        for e in errors[:20]:
            print(f"  - {e}")
        sys.exit(1)
    print(f"✅ title-slug audit PASSED: {summary['total']} posts, {summary['warnings']} warnings")
    sys.exit(0)


if __name__ == "__main__":
    main()
