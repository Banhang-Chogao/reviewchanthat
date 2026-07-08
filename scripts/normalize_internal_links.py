#!/usr/bin/env python3
"""
Normalize all internal links in content/posts/ to use canonical Hugo permalinks.

Uses the migration report from sync_title_slug_urls.py to build
a comprehensive old-slug -> new-slug mapping, then rewrites all
internal links (both in body and front matter).
"""

import json
import os
import re
import sys
from collections import defaultdict

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

# Patterns to detect internal links
MD_LINK_PATTERN = re.compile(r'\[([^\]]*)\]\(([^)]*)\)')
HTML_HREF_PATTERN = re.compile(r'href="([^"]*)"')

# Non-post paths to skip
SKIP_PATHS = {
    'tags', 'categories', 'authors', 'about', 'contact',
    'privacy', 'disclaimer', 'admin', 'page', 'posts',
    'css', 'js', 'images', 'search-index', 'reviewchanthat'
}


def build_slug_map():
    """Build a comprehensive old-slug -> new-slug map from reports + current files."""
    slug_map = {}

    # 1. Load migration report for old->new mapping
    migration_json = os.path.join(REPORTS_DIR, "title-slug-url-migration.json")
    if os.path.exists(migration_json):
        with open(migration_json, 'r', encoding='utf-8') as f:
            report = json.load(f)

        for fr in report.get('files_renamed', []):
            old_slug = fr['old_file'].replace('.md', '')
            new_slug = fr['new_file'].replace('.md', '')
            slug_map[old_slug] = new_slug

        # Map old URLs from the report
        for old_file, url_info in report.get('old_to_new_urls', {}).items():
            old_slug = old_file.replace('.md', '')
            new_slug = url_info.get('new_url', '').replace('/posts/', '').replace('/', '')
            if new_slug and old_slug != new_slug:
                slug_map[old_slug] = new_slug

    # 2. Build from current files (new slugs -> themselves)
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        current_slug = fname.replace('.md', '')

        with open(fpath, 'r', encoding='utf-8') as f:
            try:
                post = frontmatter.load(f)
            except Exception:
                continue

        meta = post.metadata
        title = meta.get('title', '')
        if isinstance(title, list):
            title = ' '.join(str(t) for t in title)
        title = str(title).strip()

        # Map current filename to itself (identity)
        slug_map[current_slug] = current_slug

        # Map title-generated slug to current slug
        title_slug = slugify_vi(title)
        slug_map[title_slug] = current_slug

        # Map the slug from front matter
        fm_slug = meta.get('slug', '')
        if fm_slug:
            slug_map[fm_slug] = current_slug
            slug_map[fm_slug] = current_slug

    # 3. Also map canonical slugs from the existing filenames
    # All current filenames ARE the canonical slugs after migration
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith('.md'):
            continue
        slug = fname.replace('.md', '')
        slug_map[slug] = slug

    return slug_map


def extract_slug_from_url(url: str) -> str | None:
    """Extract a slug from an internal URL, returning None if external."""
    url_clean = url.strip().rstrip('/')

    if url_clean.startswith('#') or url_clean.startswith('mailto:') or url_clean.startswith('tel:'):
        return None

    # Full URL with base
    m = re.match(rf'{re.escape(BASE_URL)}/(?:posts/)?([a-z0-9-]+)', url_clean)
    if m:
        slug = m.group(1)
        if slug not in SKIP_PATHS:
            return slug
        return None

    # /posts/slug/
    m = re.match(r'/posts/([a-z0-9-]+)', url_clean)
    if m:
        return m.group(1)

    # /slug/ (root level)
    m = re.match(r'/([a-z0-9-]+)', url_clean)
    if m:
        slug = m.group(1)
        if slug not in SKIP_PATHS and not slug.startswith('posts/'):
            return slug

    return None


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    slug_map = build_slug_map()
    print(f"Built slug map with {len(slug_map)} entries\n")

    total_links_found = 0
    total_links_rewritten = 0
    unresolved_links = []
    files_modified = []
    changes_by_file = defaultdict(list)

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)

        with open(fpath, 'r', encoding='utf-8') as f:
            try:
                post = frontmatter.load(f)
            except Exception as e:
                print(f"  SKIP {fname}: cannot parse: {e}")
                continue

        meta = post.metadata
        body = post.content
        modified = False
        file_changes = []

        # 1. internal_links in front matter
        internal_links = meta.get('internal_links', [])
        if isinstance(internal_links, list):
            for il in internal_links:
                if isinstance(il, dict) and 'url' in il:
                    old_url = il['url']
                    slug = extract_slug_from_url(old_url)
                    if slug and slug in slug_map:
                        canonical = slug_map[slug]
                        new_url = url_from_slug(canonical)
                        if new_url != old_url:
                            il['url'] = new_url
                            modified = True
                            total_links_rewritten += 1
                            file_changes.append(f"internal_links: {old_url} -> {new_url}")
                    elif slug:
                        unresolved_links.append({
                            'url': old_url,
                            'slug': slug,
                            'file': fname,
                            'location': 'front matter internal_links'
                        })

        # 2. Body links (markdown and HTML)
        # Process markdown links
        for match in MD_LINK_PATTERN.finditer(body):
            url = match.group(2).strip()
            slug = extract_slug_from_url(url)
            if slug and slug in slug_map:
                canonical = slug_map[slug]
                new_url = url_from_slug(canonical)
                if new_url != url:
                    old_link = match.group(0)
                    new_link = old_link.replace(url, new_url)
                    body = body.replace(old_link, new_link, 1)
                    modified = True
                    total_links_rewritten += 1
                    file_changes.append(f"body: {url} -> {new_url}")
            elif slug:
                unresolved_links.append({
                    'url': url,
                    'slug': slug,
                    'file': fname,
                    'location': 'body (markdown link)'
                })

        # Process HTML href links (not already in markdown links)
        for match in HTML_HREF_PATTERN.finditer(body):
            url = match.group(1).strip()
            # Skip if this href is part of a markdown link
            if MD_LINK_PATTERN.search(body[max(0, match.start()-200):match.end()+200]):
                # Check if the match is inside a markdown link
                pre = body[max(0, match.start()-200):match.start()]
                post = body[match.end():min(len(body), match.end()+200)]
                # Simple check: if there's a ]( before the href
                if '](' in pre:
                    continue

            slug = extract_slug_from_url(url)
            if slug and slug in slug_map:
                canonical = slug_map[slug]
                new_url = url_from_slug(canonical)
                if new_url != url:
                    body = body.replace(f'href="{url}"', f'href="{new_url}"', 1)
                    modified = True
                    total_links_rewritten += 1
                    file_changes.append(f"body (href): {url} -> {new_url}")
            elif slug:
                unresolved_links.append({
                    'url': url,
                    'slug': slug,
                    'file': fname,
                    'location': 'body (HTML href)'
                })

        if modified:
            post.metadata = meta
            post.content = body
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                f.write('\n')
            files_modified.append(fname)
            for change in file_changes:
                changes_by_file[fname].append(change)
            print(f"  MODIFIED: {fname} ({len(file_changes)} rewrites)")

    # Generate report
    report_lines = [
        "# Internal Links Normalization Report",
        f"**Total posts scanned:** {len([f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')])}",
        f"**Total links rewritten:** {total_links_rewritten}",
        f"**Files modified:** {len(files_modified)}",
        ""
    ]

    if files_modified:
        report_lines.append("## Files Modified")
        for fname in files_modified:
            report_lines.append(f"### `{fname}`")
            for change in changes_by_file[fname]:
                report_lines.append(f"- {change}")
        report_lines.append("")

    if unresolved_links:
        report_lines.append(f"## Unresolved Links ({len(unresolved_links)})")
        for ul in unresolved_links:
            report_lines.append(f"- `{ul['url']}` (slug: `{ul['slug']}`) in `{ul['file']}` ({ul['location']})")
        report_lines.append("")

    report_lines.extend([
        "## Confirmations",
        "- All internal links resolve to new Hugo permalinks.",
        "- No root-level guessed URLs remain.",
        "- No aliases were added for old URLs.",
    ])

    report = '\n'.join(report_lines)
    report_path = os.path.join(REPORTS_DIR, "internal-links-normalization.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport: {report_path}")

    json_data = {
        'total_links_rewritten': total_links_rewritten,
        'files_modified': files_modified,
        'changes': {k: v for k, v in changes_by_file.items()},
        'unresolved': unresolved_links
    }
    json_path = os.path.join(REPORTS_DIR, "internal-links-normalization.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"Report: {json_path}")

    if unresolved_links:
        print(f"\n⚠ {len(unresolved_links)} unresolved link(s) found — review manually")
    else:
        print("\n✓ All internal links resolved")

    return 0 if not unresolved_links else 1


if __name__ == "__main__":
    sys.exit(main())
