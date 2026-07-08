#!/usr/bin/env python3
"""Audit series front matter in content/posts/.

Reports:
- Posts with valid series (series + series_title + series_order)
- Posts missing series_title or series_order
- Series with only one post
- Hardcoded /series/ URLs in templates
- Duplicate series_order values within a series
- Suggested series assignments based on title/tags

Usage:
    python3 scripts/audit_series.py
"""

import os
import re
from collections import defaultdict

CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'posts')
LAYOUTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'layouts')

def parse_frontmatter(text):
    fm = {}
    m = re.match(r'^---\s*\n(.+?)\n---', text, re.DOTALL)
    if not m:
        return fm
    for line in m.group(1).split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, val = line.partition(':')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm


def audit_posts():
    print("=" * 60)
    print("SERIES AUDIT REPORT")
    print("=" * 60)

    if not os.path.isdir(CONTENT_DIR):
        print(f"ERROR: {CONTENT_DIR} not found")
        return

    all_series = defaultdict(list)
    issues = []
    valid = []

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = f.read()

        fm = parse_frontmatter(raw)
        title = fm.get('title', fname)

        series_slug = fm.get('series')
        if not series_slug:
            continue

        series_title = fm.get('series_title', '')
        series_order = fm.get('series_order', '')
        tags = fm.get('tags', '')

        missing = []
        if not series_title:
            missing.append('series_title')
        if not series_order:
            missing.append('series_order')

        if missing:
            issues.append({
                'file': fname,
                'title': title,
                'series': series_slug,
                'missing': missing,
            })
        else:
            valid.append({
                'file': fname,
                'title': title,
                'series': series_slug,
                'order': int(series_order),
            })

        all_series[series_slug].append(fname)

    # --- Report posts with issues ---
    print(f"\n## Posts with valid series: {len(valid)}")
    print(f"## Posts with missing fields: {len(issues)}")
    if issues:
        print("\n### Missing fields:")
        for i in issues:
            print(f"  ⚠️  [{i['series']}] {i['file'][:60]}")
            for m in i['missing']:
                print(f"      missing: {m}")

    # --- Duplicate orders ---
    print(f"\n## Duplicate series_order values:")
    dupes_found = False
    for slug in sorted(all_series):
        orders = defaultdict(list)
        for v in valid:
            if v['series'] == slug:
                orders[v['order']].append(v['file'])
        for order, files in sorted(orders.items()):
            if len(files) > 1:
                dupes_found = True
                print(f"  ⚠️  [{slug}] order={order}: {len(files)} posts")
                for f in files[:5]:
                    print(f"       {f[:60]}")
    if not dupes_found:
        print("  ✅ No duplicates")

    # --- Single-post series ---
    print(f"\n## Single-post series:")
    single = False
    for slug, files in sorted(all_series.items()):
        if len(files) == 1:
            single = True
            print(f"  ℹ️  {slug}: 1 post ({files[0][:60]})")
    if not single:
        print("  ✅ No single-post series")

    # --- Series summary ---
    print(f"\n## Series summary:")
    for slug in sorted(all_series):
        files = all_series[slug]
        orders_in_series = [v['order'] for v in valid if v['series'] == slug]
        order_range = f"{min(orders_in_series)}–{max(orders_in_series)}" if orders_in_series else "N/A"
        print(f"  {slug}: {len(files)} posts, orders {order_range}")

    return all_series


def audit_templates():
    print(f"\n{'=' * 60}")
    print("TEMPLATE HARDCODED URL AUDIT")
    print('=' * 60)

    pattern = re.compile(r'["\']/series/')
    found = False
    for root, dirs, files in os.walk(LAYOUTS_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            for i, line in enumerate(content.split('\n'), 1):
                if pattern.search(line):
                    found = True
                    rel = os.path.relpath(fpath, os.path.join(os.path.dirname(__file__), '..'))
                    print(f"  ⚠️  {rel}:{i}  {line.strip()[:80]}")

    if not found:
        print("  ✅ No hardcoded /series/ URLs in templates")


def main():
    audit_posts()
    audit_templates()

    print(f"\n{'=' * 60}")
    print("DONE")
    print('=' * 60)


if __name__ == '__main__':
    main()
