#!/usr/bin/env python3
"""
Content Publish Bot: Verify published content indexability and submit to search engines.

Runs after deploy to verify URLs are live, correct metadata, in sitemap/RSS,
and submit via IndexNow (Bing) + Search Console API (Google).

No direct Google Indexing API for blog posts (reserved for time-critical content).
"""

import argparse
import json
import os
import re
import sys
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import dict, list, Optional
from urllib.parse import urljoin, urlparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
BASE_URL = "https://banhang-chogao.github.io/reviewchanthat/"
PUBLIC_DIR = Path("public")
CONTENT_DIR = Path("content/posts")
REPORTS_DIR = Path("reports")
DATA_DIR = Path("data")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_changed_urls(sha: Optional[str] = None) -> list:
    """Get changed posts from git diff, filtered to public/posts/*.html"""
    if not sha:
        sha = os.getenv('GITHUB_SHA', 'HEAD')

    try:
        # Get changed files in this commit
        result = subprocess.run(
            ['git', 'diff-tree', '--no-commit-id', '--name-status', '-r', sha],
            capture_output=True, text=True, check=True
        )
        changed_files = result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        logger.warning(f"Failed to get git diff for {sha}, assuming HEAD")
        changed_files = []

    urls = []
    for line in changed_files:
        if not line.strip():
            continue
        status, filepath = line.split('\t', 1)
        # Only index posts, not categories/tags/lists
        if filepath.startswith('content/posts/') and filepath.endswith('.md'):
            slug = Path(filepath).stem
            url = urljoin(BASE_URL, f'posts/{slug}/')
            urls.append({'url': url, 'slug': slug, 'status': status})

    return urls


def verify_url_live(url: str) -> dict:
    """Check if URL is live and returns 200"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'ContentPublishBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            if status_code == 200:
                return {'live': True, 'status_code': 200}
            else:
                return {'live': False, 'status_code': status_code}
    except Exception as e:
        return {'live': False, 'status_code': 0, 'error': str(e)}


def get_page_metadata(url: str) -> dict:
    """Extract canonical, robots meta, title, description from HTML"""
    try:
        import urllib.request
        from html.parser import HTMLParser

        class MetaParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.canonical = None
                self.robots = None
                self.title = None
                self.description = None
                self.in_title = False

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == 'link' and attrs_dict.get('rel') == 'canonical':
                    self.canonical = attrs_dict.get('href')
                elif tag == 'meta':
                    if attrs_dict.get('name') == 'robots':
                        self.robots = attrs_dict.get('content', '')
                    elif attrs_dict.get('name') == 'description':
                        self.description = attrs_dict.get('content', '')
                elif tag == 'title':
                    self.in_title = True

            def handle_data(self, data):
                if self.in_title:
                    self.title = data.strip()

            def handle_endtag(self, tag):
                if tag == 'title':
                    self.in_title = False

        req = urllib.request.Request(url, headers={'User-Agent': 'ContentPublishBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')

        parser = MetaParser()
        parser.feed(content)

        return {
            'canonical': parser.canonical,
            'robots': parser.robots or 'index,follow',
            'title': parser.title or '',
            'description': parser.description or ''
        }
    except Exception as e:
        logger.warning(f"Failed to parse metadata from {url}: {e}")
        return {'canonical': None, 'robots': '', 'title': '', 'description': '', 'error': str(e)}


def check_in_sitemap(url: str) -> bool:
    """Check if URL is in sitemap.xml"""
    sitemap_path = PUBLIC_DIR / 'sitemap.xml'
    if not sitemap_path.exists():
        logger.warning("sitemap.xml not found")
        return False

    try:
        with open(sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
        return url in sitemap_content
    except Exception as e:
        logger.error(f"Failed to check sitemap: {e}")
        return False


def check_in_rss() -> dict:
    """Check if RSS index.xml is up to date"""
    rss_path = PUBLIC_DIR / 'index.xml'
    if not rss_path.exists():
        return {'found': False, 'error': 'index.xml not found'}

    try:
        with open(rss_path, 'r', encoding='utf-8') as f:
            rss_content = f.read()
        return {
            'found': True,
            'size_bytes': len(rss_content),
            'last_modified': datetime.fromtimestamp(rss_path.stat().st_mtime).isoformat()
        }
    except Exception as e:
        return {'found': False, 'error': str(e)}


def check_inbound_links(url: str) -> int:
    """Count inbound links from other posts (naive scan)"""
    count = 0
    try:
        for html_file in PUBLIC_DIR.glob('posts/**/*.html'):
            if url in html_file.read_text(encoding='utf-8', errors='ignore'):
                count += 1
    except Exception as e:
        logger.warning(f"Failed to scan inbound links: {e}")
    return max(0, count - 1)  # Exclude self-reference


def process_url(url: str, slug: str) -> dict:
    """Verify a published URL"""
    result = {
        'url': url,
        'slug': slug,
        'verified_at': datetime.utcnow().isoformat() + 'Z',
        'checks': {}
    }

    # Check live
    live_result = verify_url_live(url)
    result['checks']['live'] = live_result
    result['live_http'] = live_result.get('status_code') == 200

    if result['live_http']:
        # Get metadata
        meta = get_page_metadata(url)
        result['checks']['metadata'] = meta
        result['canonical'] = meta.get('canonical', '')

        robots = (meta.get('robots') or '').lower()
        result['checks']['robots_meta'] = robots
        result['indexable'] = 'noindex' not in robots

        # Check sitemap
        in_sitemap = check_in_sitemap(url)
        result['checks']['in_sitemap'] = in_sitemap
        result['in_sitemap'] = in_sitemap

        # Check inbound links
        inbound = check_inbound_links(url)
        result['checks']['inbound_links'] = inbound
        result['inbound_links'] = inbound
    else:
        result['indexable'] = False
        result['in_sitemap'] = False
        result['inbound_links'] = 0

    # RSS check (global, not per-URL)
    if 'rss_status' not in result:
        result['rss_status'] = check_in_rss()

    return result


def submit_indexnow(urls: list) -> dict:
    """Submit URLs to IndexNow (Bing) if key available"""
    import urllib.request
    import json

    indexnow_key = os.getenv('INDEXNOW_KEY', '').strip()
    if not indexnow_key:
        logger.info("INDEXNOW_KEY not set, skipping IndexNow submission")
        return {'submitted': False, 'reason': 'No API key'}

    # Only index posts that are live and indexable
    indexable_urls = [
        u['url'] for u in urls
        if u.get('live_http') and u.get('indexable')
    ]

    if not indexable_urls:
        return {'submitted': False, 'reason': 'No indexable URLs', 'count': 0}

    payload = {
        'host': 'banhang-chogao.github.io',
        'key': indexnow_key,
        'keyLocation': 'https://banhang-chogao.github.io/reviewchanthat/.well-known/indexnow-key.txt',
        'urlList': indexable_urls
    }

    try:
        req = urllib.request.Request(
            'https://www.bing.com/webmaster/api.svc/submit',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            if status == 200:
                return {'submitted': True, 'count': len(indexable_urls)}
            else:
                return {'submitted': False, 'status': status, 'count': 0}
    except Exception as e:
        logger.error(f"IndexNow submission failed: {e}")
        return {'submitted': False, 'error': str(e), 'count': 0}


def generate_report(results: list, indexnow_result: dict) -> str:
    """Generate markdown report"""
    md = "# Content Publish Report\n\n"
    md += f"**Generated:** {datetime.utcnow().isoformat()}Z\n\n"

    live_count = sum(1 for r in results if r.get('live_http'))
    indexable_count = sum(1 for r in results if r.get('indexable'))
    in_sitemap_count = sum(1 for r in results if r.get('in_sitemap'))

    md += f"## Summary\n"
    md += f"- **URLs checked:** {len(results)}\n"
    md += f"- **Live (200):** {live_count}\n"
    md += f"- **Indexable:** {indexable_count}\n"
    md += f"- **In sitemap:** {in_sitemap_count}\n"
    md += f"- **IndexNow submitted:** {indexnow_result.get('submitted', False)}\n"
    md += f"  - Count: {indexnow_result.get('count', 0)}\n\n"

    if results:
        md += "## Details\n\n"
        for r in results:
            md += f"### [{r['slug']}]({r['url']})\n"
            md += f"- Live: {'✓' if r.get('live_http') else '✗'}\n"
            md += f"- HTTP: {r.get('live_http', {}).get('status_code') if isinstance(r.get('live_http'), dict) else r.get('live_http')}\n"
            md += f"- Indexable: {'✓' if r.get('indexable') else '✗'}\n"
            md += f"- In sitemap: {'✓' if r.get('in_sitemap') else '✗'}\n"
            md += f"- Inbound links: {r.get('inbound_links', 0)}\n"
            if r.get('checks', {}).get('metadata', {}).get('error'):
                md += f"- Error: {r['checks']['metadata']['error']}\n"
            md += "\n"

    return md


def main():
    parser = argparse.ArgumentParser(description='Content Publish Bot')
    parser.add_argument('--sha', help='Git SHA to check', default=None)
    parser.add_argument('--urls-file', help='File with URLs (one per line)', default=None)
    parser.add_argument('--write', action='store_true', help='Write results to reports')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t submit IndexNow')
    args = parser.parse_args()

    # Get URLs
    if args.urls_file:
        with open(args.urls_file, 'r') as f:
            urls = [{'url': line.strip(), 'slug': urlparse(line.strip()).path.split('/')[-2]} for line in f if line.strip()]
    else:
        urls = get_changed_urls(args.sha)

    if not urls:
        logger.info("No URLs to process")
        if args.write:
            (DATA_DIR / 'content-publish-status.json').write_text(json.dumps([], indent=2))
        return 0

    logger.info(f"Processing {len(urls)} URLs")

    # Process each URL
    results = []
    for url_info in urls:
        logger.info(f"Checking {url_info['url']}")
        result = process_url(url_info['url'], url_info['slug'])
        results.append(result)

    # Submit IndexNow (unless dry-run)
    indexnow_result = {}
    if not args.dry_run:
        indexnow_result = submit_indexnow(results)
        logger.info(f"IndexNow: {indexnow_result}")
    else:
        logger.info("Dry-run: skipping IndexNow submission")
        indexnow_result = {'dry_run': True}

    # Write reports
    if args.write:
        status_file = DATA_DIR / 'content-publish-status.json'
        report_file = REPORTS_DIR / 'content-publish-report.md'

        status_file.write_text(json.dumps(results, indent=2))
        report_file.write_text(generate_report(results, indexnow_result))

        logger.info(f"Reports written to {status_file} and {report_file}")
    else:
        print(json.dumps(results, indent=2))

    return 0 if all(r.get('live_http') for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
