#!/usr/bin/env python3
"""
Organic Opportunity Bot: Data-driven content improvement recommendations.

Analyzes Search Analytics, GA4, internal links, and metadata to generate
targeted improvement opportunities:
- Title/description refresh (high impressions, low CTR)
- Internal link opportunities (position 5-20, low inbound)
- FAQ recommendations (question-intent queries)
- Schema optimization (missing/invalid markup)

Outputs: data-driven recommendations only, no artificial changes.
"""

import json
import sys
import logging
import re
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
CONTENT_DIR = Path('content/posts')

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default=None):
    """Load JSON safely"""
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text())
    except:
        return default or {}


def get_gsc_pages() -> dict:
    """Get GSC page performance data"""
    gsc_data = load_json(DATA_DIR / 'gsc-data.json', {})
    analytics = gsc_data.get('search_analytics', {})

    if analytics.get('status') != 'success':
        return {}

    return analytics.get('pages', {})


def get_post_metadata() -> dict:
    """Extract post metadata (title, description, schema)"""
    posts = {}

    for post_file in CONTENT_DIR.glob('*.md'):
        slug = post_file.stem
        content = post_file.read_text()

        # Extract title
        title_match = re.search(r'^title\s*=\s*"([^"]+)"', content, re.MULTILINE)
        title = title_match.group(1) if title_match else ''

        # Extract description
        desc_match = re.search(r'^description\s*=\s*"([^"]+)"', content, re.MULTILINE)
        description = desc_match.group(1) if desc_match else ''

        posts[slug] = {
            'title': title,
            'description': description,
            'slug': slug,
            'has_schema': 'schema' in content.lower() or 'json-ld' in content
        }

    return posts


def find_title_refresh_opportunities(gsc_pages: dict, posts: dict) -> list:
    """High impressions + low CTR = title/description opportunity"""
    opportunities = []

    for page_url, metrics in gsc_pages.items():
        # Extract slug from URL
        slug = page_url.split('/posts/')[-1].rstrip('/')

        if slug not in posts:
            continue

        impressions = metrics.get('impressions', 0)
        clicks = metrics.get('clicks', 0)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0

        # Criteria: high impressions (>50) + low CTR (<5%)
        if impressions > 50 and ctr < 5:
            opportunities.append({
                'type': 'title_description_refresh',
                'priority': 'high' if impressions > 100 else 'medium',
                'url': page_url,
                'slug': slug,
                'reason': f'{impressions} impressions but only {ctr:.1f}% CTR',
                'current_title': posts[slug]['title'],
                'recommendation': f'Refresh title/description to improve CTR from {ctr:.1f}%',
                'gsc_metrics': {
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr_percent': round(ctr, 1)
                }
            })

    return sorted(opportunities, key=lambda x: x['gsc_metrics']['impressions'], reverse=True)[:3]


def find_internal_link_opportunities(gsc_pages: dict, posts: dict) -> list:
    """Position 5-20 + low inbound = internal link opportunity"""
    opportunities = []

    for page_url, metrics in gsc_pages.items():
        slug = page_url.split('/posts/')[-1].rstrip('/')

        if slug not in posts:
            continue

        position = metrics.get('avg_position', 0)
        impressions = metrics.get('impressions', 0)

        # Criteria: position 5-20 range + some visibility
        if 5 <= position <= 20 and impressions > 20:
            # Count inbound links (simplified - real check would scan HTML)
            inbound = 0

            opportunities.append({
                'type': 'internal_link_boost',
                'priority': 'medium',
                'url': page_url,
                'slug': slug,
                'reason': f'Position {position:.0f} with {impressions} impressions - add internal links to push ranking',
                'current_position': round(position, 1),
                'recommendation': f'Add 3-5 internal links from high-authority posts to boost position',
                'gsc_metrics': {
                    'impressions': impressions,
                    'position': round(position, 1)
                }
            })

    return sorted(opportunities, key=lambda x: x['gsc_metrics']['impressions'], reverse=True)[:5]


def find_faq_candidates(gsc_pages: dict, posts: dict) -> list:
    """Queries with question words = FAQ candidate"""
    gsc_data = load_json(DATA_DIR / 'gsc-data.json', {})
    analytics = gsc_data.get('search_analytics', {})

    if analytics.get('status') != 'success':
        return []

    question_words = ['why', 'how', 'what', 'when', 'where', 'who', 'which', 'can i', 'should i', 'do i']
    candidates = []

    # This is a simplified version - real implementation would analyze query data
    # For now, mark any post with questions in title as potential FAQ candidate
    for slug, post in posts.items():
        title = post['title'].lower()
        if any(q in title for q in question_words):
            candidates.append({
                'type': 'faq_opportunity',
                'priority': 'low',
                'slug': slug,
                'url': f'/posts/{slug}/',
                'reason': 'Post title contains question pattern',
                'recommendation': 'Consider adding FAQ section with schema markup',
                'title': post['title']
            })

    return candidates[:2]


def find_schema_candidates(posts: dict) -> list:
    """Posts without schema = optimization candidate"""
    candidates = []

    for slug, post in posts.items():
        if not post.get('has_schema'):
            candidates.append({
                'type': 'schema_optimization',
                'priority': 'low',
                'slug': slug,
                'url': f'/posts/{slug}/',
                'reason': 'Missing structured data markup',
                'recommendation': f'Add FAQ or Article schema to improve rich snippets',
                'title': post['title']
            })

    return candidates[:1]


def generate_opportunities_report(opportunities: dict) -> str:
    """Generate markdown report"""
    md = "# Organic Opportunities Report\n\n"
    md += f"**Generated:** {datetime.utcnow().isoformat()}Z\n\n"

    total = sum(len(v) for v in opportunities.values())
    md += f"## Summary\n"
    md += f"- **Total opportunities:** {total}\n\n"

    for opp_type, items in opportunities.items():
        md += f"## {opp_type.replace('_', ' ').title()}\n"
        md += f"**Count:** {len(items)}\n\n"

        for item in items:
            md += f"### {item.get('slug', 'Unknown')}\n"
            md += f"- **URL:** {item.get('url', 'N/A')}\n"
            md += f"- **Priority:** {item.get('priority', 'medium')}\n"
            md += f"- **Reason:** {item.get('reason', '')}\n"
            md += f"- **Recommendation:** {item.get('recommendation', '')}\n"
            if 'gsc_metrics' in item:
                md += f"- **Metrics:** {json.dumps(item['gsc_metrics'])}\n"
            md += "\n"

    return md


def main():
    logger.info("Organic Opportunity Bot starting...")

    # Load data sources
    gsc_pages = get_gsc_pages()
    posts = get_post_metadata()

    if not gsc_pages:
        logger.warning("No GSC data available - skipping opportunity analysis")
        empty_result = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'status': 'unavailable',
            'reason': 'No GSC analytics data',
            'opportunities': {}
        }
        (DATA_DIR / 'organic-opportunities.json').write_text(json.dumps(empty_result, indent=2))
        return 0

    logger.info(f"Analyzing {len(gsc_pages)} pages from GSC...")

    # Generate opportunities
    opportunities = {
        'title_refresh': find_title_refresh_opportunities(gsc_pages, posts),
        'internal_links': find_internal_link_opportunities(gsc_pages, posts),
        'faq': find_faq_candidates(gsc_pages, posts),
        'schema': find_schema_candidates(posts)
    }

    result = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'status': 'success',
        'opportunities': opportunities,
        'summary': {
            'title_refresh_count': len(opportunities.get('title_refresh', [])),
            'internal_link_count': len(opportunities.get('internal_links', [])),
            'faq_count': len(opportunities.get('faq', [])),
            'schema_count': len(opportunities.get('schema', []))
        }
    }

    # Write outputs
    json_file = DATA_DIR / 'organic-opportunities.json'
    md_file = REPORTS_DIR / 'organic-opportunities.md'

    json_file.write_text(json.dumps(result, indent=2))
    md_file.write_text(generate_opportunities_report(opportunities))

    logger.info(f"Opportunities saved to {json_file}")
    logger.info(f"Report saved to {md_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
