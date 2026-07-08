#!/usr/bin/env python3
"""Normalize every post's slug to slugify_vi(title) and add a Hugo alias from
the post's previous URL so no traffic/SEO is lost.

- Posts without a `slug` (URL was title-based) -> add slug + alias(old title URL)
- Posts with a wrong `slug` -> replace slug + alias(old slug URL)
- Posts already canonical -> left untouched
Handles existing slug/aliases fields without creating duplicate YAML keys.
"""
import os
import re
import sys
import json
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "posts")
OLD_MAP = os.path.join(ROOT, "reports", "_old_permalinks.json")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
from slug_utils import slugify_vi

DRY = "--dry" in sys.argv


def title_slug(fname):
    base = fname[:-3] if fname.endswith(".md") else fname
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", base)
    return m.group(1) if m else base


def extract_title(fm_text):
    # match title: only at column 0 (ignore nested ai_summary title:)
    m = re.search(r"(?m)^title:\s*(.*?)(?=\n[a-zA-Z_]+:|\n---)", fm_text, re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip().strip("'").strip('"')


def main():
    old_map = {}
    if os.path.exists(OLD_MAP):
        old_map = json.load(open(OLD_MAP, encoding="utf-8"))

    files = [os.path.basename(f) for f in glob.glob(os.path.join(CONTENT, "*.md"))]
    changed = []
    for f in files:
        path = os.path.join(CONTENT, f)
        text = open(path, encoding="utf-8").read()
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end < 0:
            continue
        fm = text[:end]          # includes opening --- and up to before closing ---
        body = text[end:]        # starts with \n---
        fm_lines = fm.split("\n")

        title = extract_title(fm)
        canonical = slugify_vi(title)
        if not canonical:
            continue  # cannot determine canonical slug; skip

        # current effective slug
        cur_slug = None
        for ln in fm_lines:
            mm = re.match(r"^slug:\s*(.*)$", ln)
            if mm:
                cur_slug = mm.group(1).strip()
                break

        if cur_slug == canonical:
            continue  # already canonical, no change

        # old URL path to alias
        if cur_slug:
            old_path = "/posts/%s/" % cur_slug
        else:
            old_path = old_map.get(f)
            if not old_path:
                # fallback: build title-based slug
                s = title.lower()
                s = re.sub(r"[^\w\s-]", " ", s, flags=re.UNICODE)
                s = re.sub(r"\s+", "-", s).strip("-")
                old_path = "/posts/%s/" % s

        # 1) update or insert slug
        new_fm_lines = []
        replaced_slug = False
        for ln in fm_lines:
            mm = re.match(r"^slug:\s*(.*)$", ln)
            if mm and not replaced_slug:
                new_fm_lines.append("slug: %s" % canonical)
                replaced_slug = True
            else:
                new_fm_lines.append(ln)
        if not replaced_slug:
            # insert right after the title block (after first non-continuation line
            # following 'title:'); simplest: insert before closing handled later
            new_fm_lines.append("slug: %s" % canonical)

        # 2) remove any existing aliases block
        cleaned = []
        i = 0
        while i < len(new_fm_lines):
            ln = new_fm_lines[i]
            if re.match(r"^aliases:\s*$", ln):
                i += 1
                while i < len(new_fm_lines) and re.match(r"^\s*-\s+", new_fm_lines[i]):
                    i += 1
                continue
            if re.match(r"^aliases:\s*\S", ln):  # inline form (unlikely)
                i += 1
                continue
            cleaned.append(ln)
            i += 1

        # 3) append slug (if not already) + aliases before closing ---
        # ensure slug present
        has_slug = any(re.match(r"^slug:\s", l) for l in cleaned)
        out_lines = list(cleaned)
        if not has_slug:
            out_lines.append("slug: %s" % canonical)
        out_lines.append("aliases:")
        out_lines.append("  - %s" % old_path)

        new_fm = "\n".join(out_lines)
        # drop duplicate slug if both inserted and existed (defensive)
        # (handled: replaced_slug path doesn't append; non-replaced appends once)
        new_text = new_fm + body
        if new_text != text:
            changed.append((f, cur_slug, canonical, old_path))
            if not DRY:
                open(path, "w", encoding="utf-8").write(new_text)

    print(("DRY-RUN " if DRY else "") + "Normalized %d posts:" % len(changed))
    for c in changed:
        print("  %s : %s -> %s (alias %s)" % c)


if __name__ == "__main__":
    main()
