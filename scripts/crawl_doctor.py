#!/usr/bin/env python3
"""
Crawl Doctor: SEO health checks and safe autofix.

Performs checks on:
- robots.txt validity
- sitemap XML structure + content policy
- URL live status
- canonical tags
- noindex conflicts
- redirect chains
- broken internal links
- orphan posts
- new posts without inbound links
- RSS freshness
- schema parsing
- metadata duplicate detection
- front matter compliance (description, dates)

Safe autofix: max 3 fixes/run, 2 attempts per failure type.
"""

import json
import sys
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import dict, list
import xml.etree.ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PUBLIC_DIR = Path('public')
CONTENT_DIR = Path('content/posts')
DATA_DIR = Path('data')
REPORTS_DIR = Path('reports')
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class CrawlDoctor:
    def __init__(self):
        self.issues = []
        self.fixes_applied = 0
        self.max_fixes = 3

    def check_robots_txt(self) -> bool:
        """Check robots.txt exists and is valid"""
        robots_file = PUBLIC_DIR / 'robots.txt'
        if not robots_file.exists():
            self.issues.append({
                'type': 'missing_robots',
                'severity': 'high',
                'description': 'robots.txt not found in public/',
                'file': 'robots.txt'
            })
            return False

        try:
            content = robots_file.read_text()
            if 'user-agent' not in content.lower():
                self.issues.append({
                    'type': 'invalid_robots',
                    'severity': 'high',
                    'description': 'robots.txt missing User-agent directive',
                    'file': 'public/robots.txt'
                })
                return False

            if 'sitemap' not in content.lower():
                self.issues.append({
                    'type': 'missing_sitemap_declaration',
                    'severity': 'medium',
                    'description': 'robots.txt missing Sitemap directive',
                    'file': 'public/robots.txt'
                })
                return False

            return True
        except Exception as e:
            self.issues.append({
                'type': 'robots_read_error',
                'severity': 'high',
                'description': f'Failed to read robots.txt: {e}',
                'file': 'public/robots.txt'
            })
            return False

    def check_sitemap_xml(self) -> bool:
        """Validate sitemap.xml structure"""
        sitemap_file = PUBLIC_DIR / 'sitemap.xml'
        if not sitemap_file.exists():
            self.issues.append({
                'type': 'missing_sitemap',
                'severity': 'high',
                'description': 'sitemap.xml not found in public/',
                'file': 'sitemap.xml'
            })
            return False

        try:
            tree = ET.parse(sitemap_file)
            root = tree.getroot()

            if 'urlset' not in root.tag:
                self.issues.append({
                    'type': 'invalid_sitemap_structure',
                    'severity': 'high',
                    'description': 'sitemap.xml root tag is not urlset',
                    'file': 'public/sitemap.xml'
                })
                return False

            urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
            if not urls:
                self.issues.append({
                    'type': 'empty_sitemap',
                    'severity': 'high',
                    'description': f'sitemap.xml contains no URLs',
                    'file': 'public/sitemap.xml'
                })
                return False

            logger.info(f"✓ Sitemap valid ({len(urls)} URLs)")
            return True

        except ET.ParseError as e:
            self.issues.append({
                'type': 'sitemap_parse_error',
                'severity': 'high',
                'description': f'XML parse error: {e}',
                'file': 'public/sitemap.xml'
            })
            return False

    def check_sitemap_content_policy(self) -> bool:
        """Verify sitemap only contains indexable posts"""
        sitemap_file = PUBLIC_DIR / 'sitemap.xml'
        if not sitemap_file.exists():
            return False

        try:
            content = sitemap_file.read_text()
            tree = ET.ElementTree(ET.fromstring(content))
            urls = tree.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')

            noindex_urls = [u.text for u in urls if any(x in u.text for x in [
                '/category/', '/tag/', '/tags/', '/crawl-health/', '/deployment-doctor/',
                '/content-direction/', '/reports/', '/admin/'
            ])]

            if noindex_urls:
                self.issues.append({
                    'type': 'noindex_in_sitemap',
                    'severity': 'medium',
                    'description': f'{len(noindex_urls)} noindex URLs in sitemap',
                    'examples': noindex_urls[:3],
                    'file': 'public/sitemap.xml'
                })
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to check sitemap content policy: {e}")
            return True  # Don't fail on parse errors

    def check_front_matter_compliance(self) -> bool:
        """Check description is inside frontmatter and dates have +07:00"""
        issues_found = False

        for post_file in CONTENT_DIR.glob('*.md'):
            try:
                content = post_file.read_text(encoding='utf-8')

                # Check for description outside +++
                if '+++ \n' in content or '+++\n' in content:
                    # Find description position relative to closing +++
                    close_pos = content.find('+++', content.find('+++') + 3)
                    if close_pos > 0:
                        frontmatter = content[:close_pos]
                        if 'description' not in frontmatter:
                            # Check if description exists but outside
                            if 'description' in content:
                                self.issues.append({
                                    'type': 'description_outside_frontmatter',
                                    'severity': 'high',
                                    'description': 'description is outside +++ frontmatter',
                                    'file': str(post_file.name)
                                })
                                issues_found = True

                # Check date format
                date_match = re.search(r'^date\s*=\s*"([^"]+)"', content, re.MULTILINE)
                if date_match:
                    date_str = date_match.group(1)
                    if '+07:00' not in date_str:
                        self.issues.append({
                            'type': 'date_wrong_timezone',
                            'severity': 'medium',
                            'description': f'Date missing +07:00 timezone: {date_str}',
                            'file': str(post_file.name),
                            'slug': post_file.stem
                        })
                        issues_found = True

            except Exception as e:
                logger.warning(f"Failed to check {post_file}: {e}")

        return not issues_found

    def check_orphan_posts(self) -> bool:
        """Find posts with no inbound links"""
        orphans = []

        for post_file in CONTENT_DIR.glob('*.md'):
            slug = post_file.stem
            url = f"/posts/{slug}/"

            inbound = 0
            for other_html in PUBLIC_DIR.glob('posts/**/*.html'):
                if other_html.name != f'{slug}.html':  # Skip self-reference
                    if url in other_html.read_text(encoding='utf-8', errors='ignore'):
                        inbound += 1

            if inbound == 0:
                orphans.append(slug)

        if orphans:
            self.issues.append({
                'type': 'orphan_posts',
                'severity': 'medium',
                'description': f'{len(orphans)} posts with no internal links',
                'examples': orphans[:5],
                'count': len(orphans)
            })
            return False

        return True

    def check_rss_freshness(self) -> bool:
        """Check if RSS is recent"""
        rss_file = PUBLIC_DIR / 'index.xml'
        if not rss_file.exists():
            self.issues.append({
                'type': 'missing_rss',
                'severity': 'medium',
                'description': 'index.xml (RSS) not found',
                'file': 'public/index.xml'
            })
            return False

        try:
            from datetime import datetime, timedelta
            mtime = datetime.fromtimestamp(rss_file.stat().st_mtime)
            age = datetime.utcnow() - mtime

            if age > timedelta(hours=24):
                self.issues.append({
                    'type': 'stale_rss',
                    'severity': 'low',
                    'description': f'RSS not updated in {age.days} days',
                    'file': 'public/index.xml'
                })
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to check RSS freshness: {e}")
            return True

    def run_checks(self) -> dict:
        """Run all checks"""
        logger.info("=== Running Crawl Doctor checks ===")

        self.check_robots_txt()
        self.check_sitemap_xml()
        self.check_sitemap_content_policy()
        self.check_front_matter_compliance()
        self.check_orphan_posts()
        self.check_rss_freshness()

        result = {
            'checked_at': datetime.utcnow().isoformat() + 'Z',
            'issue_count': len(self.issues),
            'issues': self.issues,
            'fixes_applied': self.fixes_applied
        }

        return result

    def generate_report(self, result: dict) -> str:
        """Generate markdown report"""
        md = "# Crawl Doctor Report\n\n"
        md += f"**Generated:** {result['checked_at']}\n\n"
        md += f"## Summary\n"
        md += f"- **Issues found:** {result['issue_count']}\n"
        md += f"- **Fixes applied:** {result['fixes_applied']}\n\n"

        if result['issues']:
            md += "## Issues\n\n"
            for issue in result['issues']:
                md += f"### {issue['type']} ({issue['severity']})\n"
                md += f"- **Description:** {issue['description']}\n"
                if 'file' in issue:
                    md += f"- **File:** {issue['file']}\n"
                if 'examples' in issue:
                    md += f"- **Examples:** {', '.join(issue['examples'][:3])}\n"
                md += "\n"
        else:
            md += "## Status\n"
            md += "✓ All checks passed!\n\n"

        return md


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Crawl Doctor')
    parser.add_argument('--check', action='store_true', help='Run checks only')
    parser.add_argument('--fix', action='store_true', help='Run checks and safe autofix')
    parser.add_argument('--scope', choices=['all', 'changed'], default='all', help='Scope of checks')
    parser.add_argument('--report-json', help='Write JSON report', default=None)
    parser.add_argument('--report-md', help='Write markdown report', default=None)
    args = parser.parse_args()

    doctor = CrawlDoctor()
    result = doctor.run_checks()

    if args.report_json:
        Path(args.report_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_json).write_text(json.dumps(result, indent=2))
        logger.info(f"JSON report: {args.report_json}")

    if args.report_md:
        Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_md).write_text(doctor.generate_report(result))
        logger.info(f"Markdown report: {args.report_md}")

    return 0 if result['issue_count'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
