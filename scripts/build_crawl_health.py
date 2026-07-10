#!/usr/bin/env python3
"""
Build Crawl Health: Aggregate crawl/index monitoring data into dashboard.

Consumes data from GSC, content_publish_bot, and crawl_doctor to generate
the crawl-health.json data source for /crawl-health/ dashboard.

Metrics labeled: exact, sampled, estimated, unavailable
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import dict, list

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
REPORTS_DIR = Path('reports')
PUBLIC_DIR = Path('public')


def load_json(path: Path, default=None):
    """Load JSON file safely"""
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text())
    except:
        return default or {}


def count_indexed_posts() -> dict:
    """Count posts marked as indexed from content-publish-status"""
    status_data = load_json(DATA_DIR / 'content-publish-status.json', [])
    indexed = sum(1 for r in status_data if r.get('live_http') and r.get('indexable'))
    total = len(status_data)
    return {
        'sample_type': 'exact',
        'indexed_count': indexed,
        'total_checked': total,
        'sample_size': total
    }


def get_gsc_metrics() -> dict:
    """Extract metrics from GSC data"""
    gsc_data = load_json(DATA_DIR / 'gsc-data.json', {})

    if gsc_data.get('search_analytics', {}).get('status') != 'success':
        return {
            'status': 'unavailable',
            'reason': 'GSC data not available'
        }

    pages = gsc_data.get('search_analytics', {}).get('pages', {})
    if not pages:
        return {'status': 'unavailable', 'reason': 'No GSC data'}

    total_clicks = sum(p.get('clicks', 0) for p in pages.values())
    total_impressions = sum(p.get('impressions', 0) for p in pages.values())
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_position = sum(p.get('avg_position', 0) for p in pages.values()) / len(pages) if pages else 0

    return {
        'status': 'success',
        'sample_type': 'sampled',
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'avg_ctr_percent': round(avg_ctr, 2),
        'avg_position': round(avg_position, 1),
        'pages_with_data': len(pages)
    }


def get_last_crawl_sample() -> dict:
    """Get last crawl time from GSC URL inspection sample"""
    gsc_data = load_json(DATA_DIR / 'gsc-data.json', {})
    inspection = gsc_data.get('url_inspection', {})

    if inspection.get('status') != 'success':
        return {
            'status': 'unavailable',
            'reason': 'No URL inspection data'
        }

    urls = inspection.get('urls', [])
    if not urls:
        return {'status': 'unavailable'}

    # Get most recent crawl from sample
    last_crawl = None
    for u in urls:
        crawl_time = u.get('last_crawl_time')
        if crawl_time:
            if not last_crawl or crawl_time > last_crawl:
                last_crawl = crawl_time

    return {
        'status': 'success',
        'sample_type': 'sampled',
        'last_crawl_time': last_crawl,
        'sample_size': len(urls),
        'note': 'Based on URL inspection sample, not full site'
    }


def get_sitemap_status() -> dict:
    """Get sitemap submission status from GSC"""
    gsc_data = load_json(DATA_DIR / 'gsc-data.json', {})
    sitemap = gsc_data.get('sitemap_status', {})

    if sitemap.get('status') != 'success':
        return {
            'status': 'unavailable',
            'reason': 'GSC sitemap data not available'
        }

    sitemaps = sitemap.get('sitemaps', [])
    if not sitemaps:
        return {'status': 'unavailable'}

    return {
        'status': 'success',
        'sample_type': 'exact',
        'sitemaps': sitemaps
    }


def get_robots_status() -> dict:
    """Check if robots.txt is accessible and valid"""
    robots_file = PUBLIC_DIR / 'robots.txt'
    if not robots_file.exists():
        return {'status': 'error', 'reason': 'robots.txt not found'}

    try:
        content = robots_file.read_text()
        has_sitemap = 'sitemap' in content.lower()
        return {
            'status': 'valid',
            'sample_type': 'exact',
            'has_sitemap_declaration': has_sitemap,
            'size_bytes': len(content)
        }
    except Exception as e:
        return {'status': 'error', 'reason': str(e)}


def get_live_status() -> dict:
    """Count live 200/redirect/404 status from publish bot"""
    status_data = load_json(DATA_DIR / 'content-publish-status.json', [])

    status_200 = sum(1 for r in status_data if r.get('live_http') is True)
    status_error = sum(1 for r in status_data if r.get('live_http') is False)

    return {
        'status': 'success',
        'sample_type': 'exact',
        'http_200_count': status_200,
        'error_count': status_error,
        'total': len(status_data)
    }


def get_canonical_audit() -> dict:
    """Canonical tag audit from crawl doctor"""
    doctor_report = load_json(REPORTS_DIR / 'crawl-doctor-report.json', {})
    issues = doctor_report.get('issues', [])

    canonical_issues = [i for i in issues if 'canonical' in i.get('type', '').lower()]
    return {
        'status': 'audit_complete' if issues else 'clean',
        'sample_type': 'exact',
        'canonical_issues': len(canonical_issues),
        'issue_types': [i.get('type') for i in canonical_issues[:5]]
    }


def get_orphan_posts() -> dict:
    """Orphan post detection"""
    doctor_report = load_json(REPORTS_DIR / 'crawl-doctor-report.json', {})
    issues = doctor_report.get('issues', [])

    orphan_issues = [i for i in issues if 'orphan' in i.get('type', '').lower()]
    if orphan_issues:
        return {
            'status': 'has_orphans',
            'sample_type': 'exact',
            'count': len(orphan_issues),
            'examples': [i.get('url', i.get('slug', 'unknown'))[:50] for i in orphan_issues[:3]]
        }

    return {'status': 'clean', 'sample_type': 'exact', 'orphan_count': 0}


def get_action_items() -> list:
    """Generate action items from all data sources"""
    actions = []

    # From crawl doctor
    doctor_report = load_json(REPORTS_DIR / 'crawl-doctor-report.json', {})
    doctor_issues = doctor_report.get('issues', [])

    for issue in doctor_issues[:5]:  # Top 5
        actions.append({
            'priority': 'high' if issue.get('severity') == 'error' else 'medium',
            'type': issue.get('type'),
            'description': issue.get('description', ''),
            'url': issue.get('url', issue.get('slug', 'unknown'))
        })

    # From organic opportunities
    opp_data = load_json(DATA_DIR / 'organic-opportunities.json', {})
    for opp in opp_data.get('opportunities', [])[:3]:
        actions.append({
            'priority': 'medium',
            'type': 'content_improvement',
            'description': opp.get('recommendation', ''),
            'url': opp.get('url')
        })

    return actions[:10]  # Top 10 actions


def main():
    logger.info("Building crawl-health dashboard data...")

    health_data = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'site': {
            'base_url': 'https://banhang-chogao.github.io/reviewchanthat/',
            'note': 'GitHub Pages project URL - robots.txt at project path has limitations'
        },
        'indexing': {
            'google_indexed_sample': count_indexed_posts(),
            'gsc_metrics': get_gsc_metrics(),
            'last_crawl_sample': get_last_crawl_sample()
        },
        'technical': {
            'sitemap': get_sitemap_status(),
            'robots': get_robots_status(),
            'live_status': get_live_status()
        },
        'quality': {
            'canonical_audit': get_canonical_audit(),
            'orphan_posts': get_orphan_posts()
        },
        'actions': get_action_items()
    }

    # Write dashboard data
    output_file = DATA_DIR / 'crawl-health.json'
    output_file.write_text(json.dumps(health_data, indent=2))
    logger.info(f"Crawl health data written to {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
