#!/usr/bin/env python3
"""Build data/series-index.json from front matter in content/posts/.

Scans all posts, groups by `series` field, and outputs a structured JSON file
suitable for Hugo's data directory or for CI/audit reporting.

Usage:
    python3 scripts/build_series_index.py
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime

CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'posts')
OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'series-index.json')

def parse_frontmatter(text):
    """Minimal YAML front matter parser (avoids dependencies)."""
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


def main():
    series = defaultdict(list)

    if not os.path.isdir(CONTENT_DIR):
        print(f"ERROR: {CONTENT_DIR} not found")
        return

    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = f.read()

        fm = parse_frontmatter(raw)

        series_slug = fm.get('series')
        if not series_slug:
            continue

        series_title = fm.get('series_title', '')
        series_order = int(fm.get('series_order', 999))
        title = fm.get('title', fname)
        date_str = fm.get('date', '')

        series[series_slug].append({
            'title': title,
            'url': fname.replace('.md', '/'),
            'order': series_order,
            'date': date_str[:10] if date_str else '',
            'series_title': series_title,
        })

    output = {'series': []}
    for slug in sorted(series):
        posts = series[slug]
        # Sort by series_order, fallback to date ascending
        posts.sort(key=lambda p: (p['order'], p['date']))
        # Deduce series title from first post
        title = posts[0]['series_title'] if posts[0]['series_title'] else slug.replace('-', ' ').title()
        output['series'].append({
            'id': slug,
            'title': title,
            'url': f'series/{slug}/',
            'count': len(posts),
            'posts': [{
                'title': p['title'],
                'url': p['url'],
                'order': p['order'],
                'date': p['date'],
            } for p in posts],
        })

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Written {len(output['series'])} series ({sum(s['count'] for s in output['series'])} posts) to {OUTPUT}")


if __name__ == '__main__':
    main()
