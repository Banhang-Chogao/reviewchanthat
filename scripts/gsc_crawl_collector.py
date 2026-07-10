#!/usr/bin/env python3
"""
GSC Crawl Collector: Fetch data from Google Search Console API.

Collects Search Analytics (impressions, clicks, CTR, position) and
URL Inspection data (index status, crawl stats).

Requires OAuth or service account credentials. Graceful skip if unavailable.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import dict, list, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GSC_SITE_URL = os.getenv('GSC_SITE_URL', 'https://banhang-chogao.github.io/reviewchanthat/')
DATA_DIR = Path('data')
DATA_DIR.mkdir(parents=True, exist_ok=True)


def check_credentials() -> bool:
    """Check if Google API credentials are available"""
    # Check for service account key or OAuth token
    return (
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or
        os.getenv('GSC_OAUTH_TOKEN') or
        Path('credentials.json').exists()
    )


def get_gsc_client():
    """Create GSC API client (stub - requires actual Google API setup)"""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        # Try service account
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path:
            creds = Credentials.from_service_account_file(creds_path)
            return build('webmasters', 'v3', credentials=creds)

        # Try default credentials
        return build('webmasters', 'v3')

    except ImportError:
        logger.warning("google-auth/google-api-client not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to create GSC client: {e}")
        return None


def collect_search_analytics(client, days: int = 90) -> dict:
    """Collect search performance data from Search Analytics"""
    if not client:
        return {'status': 'unavailable', 'reason': 'No GSC client'}

    try:
        service = client.searchanalytics()
        request = service.query(
            siteUrl=GSC_SITE_URL,
            body={
                'startDate': (datetime.now() - timedelta(days=days)).isoformat()[:10],
                'endDate': datetime.now().isoformat()[:10],
                'dimensions': ['page', 'query'],
                'rowLimit': 25000
            }
        )
        results = request.execute()

        # Aggregate by page
        by_page = {}
        for row in results.get('rows', []):
            page = row['keys'][0]
            clicks = row.get('clicks', 0)
            impressions = row.get('impressions', 0)
            ctr = row.get('ctr', 0.0)
            position = row.get('position', 0)

            if page not in by_page:
                by_page[page] = {'clicks': 0, 'impressions': 0, 'queries': 0}

            by_page[page]['clicks'] += clicks
            by_page[page]['impressions'] += impressions
            by_page[page]['queries'] += 1
            by_page[page]['avg_position'] = position

        return {
            'status': 'success',
            'sample_type': 'sampled',
            'days': days,
            'pages': by_page,
            'row_count': len(results.get('rows', []))
        }

    except Exception as e:
        logger.warning(f"Failed to collect search analytics: {e}")
        return {'status': 'unavailable', 'error': str(e)}


def collect_sitemap_status(client) -> dict:
    """Get sitemap submission status"""
    if not client:
        return {'status': 'unavailable'}

    try:
        service = client.sitemaps()
        request = service.list(siteUrl=GSC_SITE_URL)
        results = request.execute()

        sitemaps = []
        for sm in results.get('sitemap', []):
            sitemaps.append({
                'url': sm.get('path'),
                'type': sm.get('type'),
                'submitted_date': sm.get('submitted'),
                'indexed': sm.get('contents', [{}])[0].get('indexed'),
                'submitted_count': sm.get('contents', [{}])[0].get('submitted')
            })

        return {
            'status': 'success',
            'sitemaps': sitemaps
        }

    except Exception as e:
        logger.warning(f"Failed to collect sitemap status: {e}")
        return {'status': 'unavailable', 'error': str(e)}


def inspect_sample_urls(client, urls: list, limit: int = 10) -> dict:
    """Inspect up to N URLs to check index status"""
    if not client or not urls:
        return {'status': 'unavailable', 'reason': 'No client or URLs' if not client else 'No URLs'}

    try:
        service = client.urlInspection()
        inspected = []

        for url in urls[:limit]:
            request = service.inspect(
                siteUrl=GSC_SITE_URL,
                body={'inspectionUrl': url}
            )
            result = request.execute()

            inspection_result = result.get('inspectionResult', {})
            inspected.append({
                'url': url,
                'index_status': inspection_result.get('indexStatus'),
                'coverage_state': inspection_result.get('coverageState'),
                'last_crawl_time': inspection_result.get('lastCrawlTime'),
                'crawl_state': inspection_result.get('crawlState'),
                'referrer': inspection_result.get('referrer')
            })

        return {
            'status': 'success',
            'sample_type': 'exact',
            'inspected_count': len(inspected),
            'urls': inspected
        }

    except Exception as e:
        logger.warning(f"Failed to inspect URLs: {e}")
        return {'status': 'unavailable', 'error': str(e)}


def main():
    logger.info("GSC Crawl Collector starting...")

    if not check_credentials():
        logger.info("GSC credentials not configured. Skipping GSC collection.")
        # Write empty/unavailable data
        data = {
            'collected_at': datetime.utcnow().isoformat() + 'Z',
            'search_analytics': {'status': 'unavailable', 'reason': 'No credentials'},
            'sitemap_status': {'status': 'unavailable', 'reason': 'No credentials'},
            'url_inspection': {'status': 'unavailable', 'reason': 'No credentials'}
        }
        (DATA_DIR / 'gsc-data.json').write_text(json.dumps(data, indent=2))
        return 0

    client = get_gsc_client()
    if not client:
        logger.warning("Failed to create GSC client")
        data = {
            'collected_at': datetime.utcnow().isoformat() + 'Z',
            'status': 'error'
        }
        (DATA_DIR / 'gsc-data.json').write_text(json.dumps(data, indent=2))
        return 0

    # Collect data
    logger.info("Collecting Search Analytics...")
    analytics = collect_search_analytics(client)

    logger.info("Collecting sitemap status...")
    sitemap = collect_sitemap_status(client)

    # Get sample of top URLs for inspection
    sample_urls = []
    if analytics.get('pages'):
        sample_urls = sorted(
            analytics['pages'].items(),
            key=lambda x: x[1]['impressions'],
            reverse=True
        )[:10]
        sample_urls = [url for url, _ in sample_urls]

    logger.info(f"Inspecting {len(sample_urls)} sample URLs...")
    inspection = inspect_sample_urls(client, sample_urls)

    # Aggregate data
    result = {
        'collected_at': datetime.utcnow().isoformat() + 'Z',
        'site_url': GSC_SITE_URL,
        'search_analytics': analytics,
        'sitemap_status': sitemap,
        'url_inspection': inspection
    }

    # Write data
    output_file = DATA_DIR / 'gsc-data.json'
    output_file.write_text(json.dumps(result, indent=2))
    logger.info(f"GSC data saved to {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
