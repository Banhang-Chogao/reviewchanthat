#!/usr/bin/env python3
"""
QA Crawl System: Comprehensive validation for Crawl Doctor automation.

Hard checks:
- No deprecated Google endpoints (ping, Indexing API for blog posts)
- No secrets in public/data/reports
- No relative URLs in generated HTML
- Description always inside +++
- Dates always have +07:00
- No merge conflicts
- All required files exist
"""

import sys
import re
import logging
from pathlib import Path
from typing import list, dict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

PUBLIC_DIR = Path('public')
SCRIPTS_DIR = Path('scripts')
DATA_DIR = Path('data')
REPORTS_DIR = Path('reports')
CONTENT_DIR = Path('content/posts')


def check_no_deprecated_google_endpoints() -> list:
    """Ensure no deprecated Google API endpoints"""
    errors = []
    patterns = [
        (r'google\.com/ping\?sitemap', 'Deprecated sitemap ping endpoint'),
        (r'indexing\.googleapis\.com', 'Google Indexing API (reserved for news/jobs)'),
        (r'content\.googleapis\.com', 'Deprecated content API')
    ]

    for script_file in SCRIPTS_DIR.glob('*.py'):
        content = script_file.read_text()
        for pattern, description in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f'{script_file.name}: Found {description}')

    if errors:
        logger.error("❌ Deprecated Google endpoints found:")
        for error in errors:
            logger.error(f"   {error}")
    else:
        logger.info("✓ No deprecated Google endpoints")

    return errors


def check_no_secrets_in_public() -> list:
    """Ensure no secrets in public/data/reports directories"""
    errors = []
    secret_patterns = [
        r'INDEXNOW_KEY',
        r'GSC_CLIENT_SECRET',
        r'GOOGLE_APPLICATION_CREDENTIALS',
        r'CLOUDFLARE_API_TOKEN',
        r'oauth_token',
        r'api_key'
    ]

    for directory in [PUBLIC_DIR, DATA_DIR, REPORTS_DIR]:
        if not directory.exists():
            continue

        for file_path in directory.rglob('*'):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(errors='ignore')
                for pattern in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        errors.append(f'{file_path.relative_to(Path("."))}: Found {pattern}')
            except Exception as e:
                logger.warning(f'Failed to check {file_path}: {e}')

    if errors:
        logger.error("❌ Secrets found in public directories:")
        for error in errors:
            logger.error(f"   {error}")
    else:
        logger.info("✓ No secrets in public/data/reports")

    return errors


def check_no_relative_urls() -> list:
    """Ensure no relative URLs in generated HTML"""
    errors = []
    patterns = [
        r'href="/posts/',
        r'href="/series/',
        r'href="/category/',
        r'src="/images/',
        r'src="/static/'
    ]

    html_count = 0
    for html_file in PUBLIC_DIR.rglob('*.html'):
        html_count += 1
        content = html_file.read_text(errors='ignore')

        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                errors.append(f'{html_file.relative_to(PUBLIC_DIR)}: {len(matches)} relative URL(s)')

    if errors:
        logger.error("❌ Relative URLs found in HTML:")
        for error in errors[:10]:
            logger.error(f"   {error}")
        if len(errors) > 10:
            logger.error(f"   ... and {len(errors) - 10} more")
    else:
        logger.info(f"✓ No relative URLs in {html_count} HTML files")

    return errors


def check_frontmatter_compliance() -> list:
    """Check description inside +++ and dates have +07:00"""
    errors = []

    for post_file in CONTENT_DIR.glob('*.md'):
        content = post_file.read_text()
        slug = post_file.stem

        # Check description
        close_m = re.search(r'^\+{3}\s*$', content, re.MULTILINE)
        close_pos = close_m.start() if close_m else -1
        if close_pos > 0:
            frontmatter = content[:close_pos]
            after_frontmatter = content[close_pos:]

            if 'description' not in frontmatter and 'description' in after_frontmatter:
                errors.append(f'{slug}: description outside +++')

        # Check date format
        date_match = re.search(r'^date\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if date_match:
            date_str = date_match.group(1)
            if '+07:00' not in date_str:
                errors.append(f'{slug}: date missing +07:00 - {date_str}')

    if errors:
        logger.error("❌ Front matter compliance issues:")
        for error in errors[:10]:
            logger.error(f"   {error}")
        if len(errors) > 10:
            logger.error(f"   ... and {len(errors) - 10} more")
    else:
        logger.info(f"✓ Front matter compliant ({len(list(CONTENT_DIR.glob('*.md')))} posts)")

    return errors


def check_no_merge_conflicts() -> list:
    """Check for merge conflict markers"""
    errors = []
    conflict_markers = ['<<<<<<<', '=======', '>>>>>>>']

    for root_path in [SCRIPTS_DIR, CONTENT_DIR, Path('layouts'), DATA_DIR, REPORTS_DIR, Path('.github')]:
        if not root_path.exists():
            continue

        for file_path in root_path.rglob('*'):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(errors='ignore')
                for marker in conflict_markers:
                    if marker in content:
                        errors.append(f'{file_path.relative_to(Path("."))}: Found {marker}')
                        break
            except Exception:
                pass

    if errors:
        logger.error("❌ Merge conflict markers found:")
        for error in errors:
            logger.error(f"   {error}")
    else:
        logger.info("✓ No merge conflict markers")

    return errors


def check_required_files() -> list:
    """Check all required Crawl Doctor files exist"""
    errors = []
    required_files = [
        'scripts/content_publish_bot.py',
        'scripts/indexnow_submit.py',
        'scripts/gsc_crawl_collector.py',
        'scripts/build_crawl_health.py',
        'scripts/crawl_doctor.py',
        'scripts/organic_opportunity_bot.py',
        '.github/workflows/crawl-doctor.yml'
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            errors.append(f'Missing: {file_path}')

    if errors:
        logger.error("❌ Required files missing:")
        for error in errors:
            logger.error(f"   {error}")
    else:
        logger.info(f"✓ All required Crawl Doctor files present")

    return errors


def main():
    logger.info("=== QA Crawl System ===\n")

    all_errors = []

    all_errors.extend(check_no_deprecated_google_endpoints())
    all_errors.extend(check_no_secrets_in_public())
    all_errors.extend(check_no_relative_urls())
    all_errors.extend(check_frontmatter_compliance())
    all_errors.extend(check_no_merge_conflicts())
    all_errors.extend(check_required_files())

    logger.info("\n=== QA Summary ===")
    if all_errors:
        logger.error(f"❌ {len(all_errors)} QA failure(s)")
        return 1
    else:
        logger.info("✓ All QA checks passed!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
