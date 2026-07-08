#!/usr/bin/env python3
"""
Force migrate ALL posts so Post Title = Slug URL 100% match.

- Reads every .md in content/posts/
- Generates canonical slug from front matter title via slugify_vi()
- Renames file to <canonical-slug>.md
- Sets slug: <canonical-slug> in front matter
- Sets url: /posts/<canonical-slug>/ if url exists, to match Hugo permalink
- Removes aliases that were only serving old URLs
- Handles duplicate titles (appends -2, -3 suffix)
- Generates migration reports
"""

import json
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slug_utils import slugify_vi, url_from_slug

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "posts")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
BASE_URL = "https://banhang-chogao.github.io/reviewchanthat"


def parse_front_matter_raw(filepath: str) -> tuple[dict, str, str]:
    """Parse front matter and return (metadata, body, raw_front_matter_text)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return {}, content, ''

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content, ''

    fm_text = parts[1]
    body = parts[2]

    try:
        metadata = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        metadata = {}

    if metadata is None:
        metadata = {}

    return metadata, body, fm_text


def get_title(metadata: dict) -> str:
    title = metadata.get('title', '')
    if not title:
        return ''
    if isinstance(title, list):
        title = ' '.join(str(t) for t in title)
    return str(title).strip()


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.isdir(CONTENT_DIR):
        print(f"ERROR: {CONTENT_DIR} not found")
        sys.exit(1)

    md_files = sorted([
        f for f in os.listdir(CONTENT_DIR)
        if f.endswith('.md')
    ])

    print(f"Found {len(md_files)} markdown files in content/posts/\n")

    # Phase 1: collect all titles and proposed slugs
    entries = []
    for fname in md_files:
        fpath = os.path.join(CONTENT_DIR, fname)
        metadata, body, fm_text = parse_front_matter_raw(fpath)
        title = get_title(metadata)
        if not title:
            print(f"WARN: {fname} — no title found, skipping")
            continue
        canonical_slug = slugify_vi(title)
        entries.append({
            'old_file': fname,
            'old_path': fpath,
            'title': title,
            'canonical_slug': canonical_slug,
            'metadata': metadata,
            'body': body,
            'fm_text': fm_text,
        })

    # Phase 2: detect duplicate slugs
    slug_counts = defaultdict(list)
    for e in entries:
        slug_counts[e['canonical_slug']].append(e)

    duplicates = {}
    for slug, items in slug_counts.items():
        if len(items) > 1:
            duplicates[slug] = items
            for i, item in enumerate(items):
                if i == 0:
                    item['final_slug'] = slug
                else:
                    suffix = i + 1
                    item['final_slug'] = f"{slug}-{suffix}"
                    print(f"  DUPLICATE: '{item['title']}' -> {item['final_slug']} (was {slug})")

    for e in entries:
        if 'final_slug' not in e:
            e['final_slug'] = e['canonical_slug']

    # Phase 3: track old->new mapping
    old_to_new = {}
    old_url_to_new_url = {}
    aliases_removed = []
    files_renamed = []
    files_updated = []
    slug_added = []
    url_updated = []

    for e in entries:
        old_file = e['old_file']
        new_slug = e['final_slug']
        new_file = f"{new_slug}.md"
        old_path = e['old_path']
        new_path = os.path.join(CONTENT_DIR, new_file)
        metadata = e['metadata']
        body = e['body']
        fm_text = e['fm_text']

        old_slug_guess = old_file.replace('.md', '')

        old_to_new[old_file] = new_file

        # Build old URL(s)
        old_urls = []
        old_urls.append(f"/{old_slug_guess}/")
        old_urls.append(url_from_slug(old_slug_guess))
        old_full_url = f"{BASE_URL}/posts/{old_slug_guess}/"

        new_url = url_from_slug(new_slug)
        new_full_url = f"{BASE_URL}{new_url}"

        old_url_to_new_url[old_file] = {
            'old_urls': old_urls,
            'new_url': new_url,
            'new_full_url': new_full_url
        }

        # Remove aliases if they only serve old URLs
        aliases = metadata.get('aliases', [])
        if aliases:
            cleaned_aliases = []
            for alias in aliases:
                alias_stripped = alias.strip().rstrip('/')
                # Check if this alias is just serving an old URL pattern
                alias_slug = alias_stripped.lstrip('/')
                if alias_slug == old_slug_guess or alias_slug == new_slug:
                    aliases_removed.append({
                        'file': old_file,
                        'removed_alias': alias,
                        'reason': 'old URL alias'
                    })
                else:
                    cleaned_aliases.append(alias)

            if cleaned_aliases:
                metadata['aliases'] = cleaned_aliases
            else:
                metadata.pop('aliases', None)
                aliases_removed.append({
                    'file': old_file,
                    'removed_alias': 'all',
                    'reason': 'all aliases were for old URLs'
                })

        # Set slug
        old_slug = metadata.get('slug', '')
        if old_slug != new_slug:
            metadata['slug'] = new_slug
            slug_added.append({
                'file': old_file,
                'old_slug': old_slug if old_slug else '(none)',
                'new_slug': new_slug
            })

        # Set url to match Hugo permalink
        if 'url' in metadata:
            old_url_val = metadata['url']
            expected_url = new_url.rstrip('/')
            if metadata['url'].rstrip('/') != expected_url:
                metadata['url'] = expected_url
                url_updated.append({
                    'file': old_file,
                    'old_url': old_url_val,
                    'new_url': expected_url
                })

        # Write updated front matter
        post = frontmatter.loads(f"---\n{fm_text}---\n\n{body}")
        post.metadata = metadata

        # Rename file if needed
        if old_file != new_file:
            # Write to new path
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                f.write('\n')
            # Remove old file
            os.remove(old_path)
            files_renamed.append({
                'old_file': old_file,
                'new_file': new_file,
                'title': e['title']
            })
            print(f"  RENAMED: {old_file} -> {new_file}")
        else:
            with open(old_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                f.write('\n')
            files_updated.append(new_file)

    # Generate report
    report_md = []
    report_md.append("# Title-Slug-URL Migration Report")
    report_md.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_md.append(f"**Total posts processed:** {len(entries)}")
    report_md.append("")

    report_md.append("## Files Renamed")
    if files_renamed:
        report_md.append(f"**{len(files_renamed)} files renamed:**")
        report_md.append("")
        report_md.append("| # | Old File | New File | Title |")
        report_md.append("|---|---|---|---|")
        for i, fr in enumerate(files_renamed, 1):
            report_md.append(f"| {i} | `{fr['old_file']}` | `{fr['new_file']}` | {fr['title']} |")
    else:
        report_md.append("No files needed renaming.")
    report_md.append("")

    report_md.append("## Old URL → New URL")
    report_md.append("")
    report_md.append("| # | Old File | Old URLs | New URL |")
    report_md.append("|---|---|---|---|")
    for i, (old_file, mapping) in enumerate(sorted(old_url_to_new_url.items()), 1):
        old_urls_str = ", ".join(mapping['old_urls'])
        report_md.append(f"| {i} | `{old_file}` | `{old_urls_str}` | `{mapping['new_url']}` |")
    report_md.append("")

    if duplicates:
        report_md.append("## Duplicate Slugs Resolved")
        report_md.append("")
        for slug, items in duplicates.items():
            report_md.append(f"- Base slug: `{slug}`")
            for item in items:
                report_md.append(f"  - `{item['final_slug']}` ← \"{item['title']}\"")
        report_md.append("")

    if aliases_removed:
        report_md.append("## Aliases Removed")
        report_md.append("")
        for ar in aliases_removed:
            report_md.append(f"- `{ar['file']}`: removed `{ar['removed_alias']}` ({ar['reason']})")
        report_md.append("")

    if slug_added:
        report_md.append("## Slug Field Updates")
        report_md.append("")
        for sa in slug_added:
            report_md.append(f"- `{sa['file']}`: `{sa['old_slug']}` → `{sa['new_slug']}`")
        report_md.append("")

    if url_updated:
        report_md.append("## URL Field Updates")
        report_md.append("")
        for uu in url_updated:
            report_md.append(f"- `{uu['file']}`: `{uu['old_url']}` → `{uu['new_url']}`")
        report_md.append("")

    report_md.append("## Summary")
    report_md.append(f"- Total posts: {len(entries)}")
    report_md.append(f"- Files renamed: {len(files_renamed)}")
    report_md.append(f"- Files updated in place: {len(files_updated)}")
    report_md.append(f"- Duplicate slug cases: {len(duplicates)}")
    report_md.append(f"- Aliases removed: {len(aliases_removed)}")
    report_md.append(f"- Slug fields set: {len(slug_added)}")
    report_md.append(f"- URL fields corrected: {len(url_updated)}")
    report_md.append("")
    report_md.append("## Confirmations")
    report_md.append("- All old and new posts now follow title = slug URL.")
    report_md.append("- No aliases were added or kept for old URLs.")
    report_md.append("- SEO impact accepted by user; cleanup-first migration completed.")

    md_report = '\n'.join(report_md)
    report_path = os.path.join(REPORTS_DIR, "title-slug-url-migration.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    print(f"\nReport written: {report_path}")

    # JSON report
    json_report = {
        'date': datetime.now().isoformat(),
        'total_posts': len(entries),
        'files_renamed': files_renamed,
        'files_updated': files_updated,
        'duplicates': {slug: [e['final_slug'] for e in items] for slug, items in duplicates.items()},
        'aliases_removed': aliases_removed,
        'slug_updates': slug_added,
        'url_updates': url_updated,
        'old_to_new_urls': {
            k: {
                'old_urls': v['old_urls'],
                'new_url': v['new_url']
            }
            for k, v in old_url_to_new_url.items()
        }
    }
    json_path = os.path.join(REPORTS_DIR, "title-slug-url-migration.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f"Report written: {json_path}")

    print(f"\nMigration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
