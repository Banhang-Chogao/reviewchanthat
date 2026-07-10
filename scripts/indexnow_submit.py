#!/usr/bin/env python3
"""
IndexNow Submission: Submit changed URLs to IndexNow (Bing/Yandex/etc).

IndexNow is a lightweight notification protocol that alerts search engines
when content changes. Uses INDEXNOW_KEY environment variable.
"""

import argparse
import json
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = 'https://banhang-chogao.github.io/reviewchanthat/'
INDEXNOW_KEY = os.getenv('INDEXNOW_KEY', '').strip()
INDEXNOW_ENDPOINT = 'https://www.bing.com/webmaster/api.svc/submit'
KEY_LOCATION = 'https://banhang-chogao.github.io/reviewchanthat/.well-known/indexnow-key.txt'
MAX_URLS_PER_REQUEST = 10000
BATCH_SIZE = 100

# Skip patterns - don't submit these
SKIP_PATTERNS = [
    '/admin/', '/draft/', '/search/', '/tag/', '/tags/', '/category/',
    '/categories/', '/series/', '/crawl-health/', '/deployment-doctor/',
    '/content-direction/', '/reports/', '/search-index'
]


def should_skip_url(url: str) -> bool:
    """Check if URL should be skipped"""
    for pattern in SKIP_PATTERNS:
        if pattern in url:
            return True
    return False


def load_status_file() -> list:
    """Load content-publish-status.json to get indexable URLs"""
    status_file = Path('data/content-publish-status.json')
    if not status_file.exists():
        logger.warning(f"{status_file} not found")
        return []

    try:
        data = json.loads(status_file.read_text())
        # Filter to indexable URLs
        urls = [
            r['url'] for r in data
            if r.get('live_http') and r.get('indexable') and not should_skip_url(r['url'])
        ]
        return urls
    except Exception as e:
        logger.error(f"Failed to load status file: {e}")
        return []


def submit_batch(urls: list, retry_count: int = 3) -> dict:
    """Submit a batch of URLs to IndexNow with retry"""
    if not urls:
        return {'success': False, 'reason': 'empty_batch'}

    payload = {
        'host': 'banhang-chogao.github.io',
        'key': INDEXNOW_KEY,
        'keyLocation': KEY_LOCATION,
        'urlList': urls
    }

    for attempt in range(1, retry_count + 1):
        try:
            req = urllib.request.Request(
                INDEXNOW_ENDPOINT,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                status = response.status
                if status == 200:
                    logger.info(f"✓ Submitted {len(urls)} URLs (attempt {attempt})")
                    return {'success': True, 'count': len(urls), 'attempt': attempt}
                else:
                    logger.warning(f"Unexpected status {status} (attempt {attempt})")
                    if attempt < retry_count:
                        wait = 2 ** (attempt - 1)
                        logger.info(f"Retrying in {wait}s...")
                        time.sleep(wait)

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Too Many Requests
                logger.warning(f"Rate limited (attempt {attempt})")
                if attempt < retry_count:
                    wait = 2 ** (attempt - 1)
                    logger.info(f"Backoff {wait}s...")
                    time.sleep(wait)
            elif e.code >= 500:  # Server error
                logger.warning(f"Server error {e.code} (attempt {attempt})")
                if attempt < retry_count:
                    wait = 2 ** (attempt - 1)
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
            else:
                logger.error(f"HTTP error {e.code}: {e}")
                return {'success': False, 'error': f'HTTP {e.code}', 'attempt': attempt}
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            if attempt < retry_count:
                wait = 2 ** (attempt - 1)
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {'success': False, 'error': str(e), 'attempt': attempt}

    return {'success': False, 'reason': f'Failed after {retry_count} attempts'}


def main():
    parser = argparse.ArgumentParser(description='IndexNow Submission')
    parser.add_argument('--urls-file', help='File with URLs (one per line)', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Don\'t actually submit')
    args = parser.parse_args()

    # Check if key is configured
    if not INDEXNOW_KEY:
        logger.warning("INDEXNOW_KEY not configured. Set environment variable or skip IndexNow.")
        return 0  # Not an error - IndexNow is optional

    logger.info("IndexNow Submission starting...")

    # Get URLs
    if args.urls_file:
        with open(args.urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not should_skip_url(line.strip())]
    else:
        urls = load_status_file()

    if not urls:
        logger.info("No URLs to submit")
        return 0

    logger.info(f"Submitting {len(urls)} URLs")

    # Dry run
    if args.dry_run:
        logger.info(f"[DRY-RUN] Would submit {len(urls)} URLs")
        for url in urls[:5]:
            logger.info(f"  {url}")
        if len(urls) > 5:
            logger.info(f"  ... and {len(urls) - 5} more")
        return 0

    # Submit in batches
    results = []
    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i:i + BATCH_SIZE]
        logger.info(f"Batch {i // BATCH_SIZE + 1}/{(len(urls) + BATCH_SIZE - 1) // BATCH_SIZE}")
        result = submit_batch(batch)
        results.append(result)

        if not result['success']:
            logger.error(f"Batch submission failed: {result}")
            if result.get('error') == 'HTTP 403':  # Invalid key
                logger.error("Invalid IndexNow key. Check INDEXNOW_KEY.")
                return 1

    # Summary
    total_submitted = sum(r.get('count', 0) for r in results if r.get('success'))
    logger.info(f"\n=== Summary ===")
    logger.info(f"Total URLs: {len(urls)}")
    logger.info(f"Submitted: {total_submitted}")
    logger.info(f"Batches: {len(results)}")

    return 0 if all(r.get('success') for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
