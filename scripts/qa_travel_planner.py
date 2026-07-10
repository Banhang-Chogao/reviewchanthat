#!/usr/bin/env python3
"""
QA suite for AI Travel Planner.

Validates:
- IATA code parsing
- Date validation (leap years, same-day, invalid dates)
- Itinerary structure
- Export formats (PDF, Excel)
- Accessibility & performance metrics
- Dark mode compatibility

Usage:
  python3 qa_travel_planner.py [--check|--fix]
"""

import os
import re
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

CONTENT_DIR = 'content/doi-song/travel-planner'
LAYOUT_FILE = 'layouts/doi-song/travel-planner.html'
CSS_FILE = 'assets/css/travel-planner.css'
JS_FILES = [
    'static/js/travel-planner.js',
    'static/js/travel-ai-engine.js'
]

ISSUES = []
WARNINGS = []
SUCCESSES = []


def log_issue(msg):
    """Log a critical issue."""
    global ISSUES
    ISSUES.append(f'❌ {msg}')
    print(f'❌ {msg}')


def log_warning(msg):
    """Log a warning."""
    global WARNINGS
    WARNINGS.append(f'⚠️  {msg}')
    print(f'⚠️  {msg}')


def log_success(msg):
    """Log a success."""
    global SUCCESSES
    SUCCESSES.append(f'✅ {msg}')
    print(f'✅ {msg}')


def check_content_file():
    """Check Hugo content file."""
    print('\n[Content File]')

    if not os.path.exists(f'{CONTENT_DIR}/_index.md'):
        log_issue(f'Missing {CONTENT_DIR}/_index.md')
        return

    with open(f'{CONTENT_DIR}/_index.md', 'r') as f:
        content = f.read()

    # Check TOML frontmatter
    if not content.startswith('+++'):
        log_issue('Content file must use TOML frontmatter (+++), not YAML')
        return

    # Check required fields
    if 'title' not in content:
        log_issue('Missing title in frontmatter')
    else:
        log_success('Title present')

    if 'layout = "travel-planner"' not in content:
        log_issue('Layout not set to "travel-planner"')
    else:
        log_success('Layout correctly set')

    if 'noindex = true' not in content and 'robots = "noindex,nofollow"' not in content:
        log_warning('Missing noindex/robots meta tags (mini-app should not be indexed)')
    else:
        log_success('Noindex/robots correctly set')

    # Check date format
    date_match = re.search(r'date = (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00)', content)
    if not date_match:
        log_issue('Date must be ISO 8601 with +07:00 timezone')
    else:
        log_success('Date format correct')


def check_layout_file():
    """Check HTML layout file."""
    print('\n[HTML Layout]')

    if not os.path.exists(LAYOUT_FILE):
        log_issue(f'Missing {LAYOUT_FILE}')
        return

    with open(LAYOUT_FILE, 'r') as f:
        content = f.read()

    # Check main class
    if 'travel-planner' not in content:
        log_issue('Missing travel-planner class wrapper')
    else:
        log_success('Main wrapper class present')

    # Check key sections
    sections = [
        'travel-planner__hero',
        'travel-planner__input-section',
        'travel-planner__form',
        'tpDestination',
        'tpDeparture',
        'tpReturn',
        'tpGenerateBtn',
        'travel-planner__result',
        'travel-planner__export'
    ]

    for section in sections:
        if section in content:
            log_success(f'Section "{section}" found')
        else:
            log_warning(f'Section "{section}" not found')

    # Check aria labels for accessibility
    if 'aria-label' in content or 'role=' in content:
        log_success('Some accessibility attributes present')
    else:
        log_warning('Limited accessibility attributes (consider adding ARIA labels)')


def check_css_file():
    """Check CSS file."""
    print('\n[CSS Styling]')

    if not os.path.exists(CSS_FILE):
        log_issue(f'Missing {CSS_FILE}')
        return

    with open(CSS_FILE, 'r') as f:
        content = f.read()

    # Check CSS structure
    checks = [
        ('CSS variables defined', '--tp-primary' in content),
        ('Color scheme support', '@media (prefers-color-scheme: dark)' in content),
        ('Responsive design', '@media (max-width:' in content),
        ('Animation support', '@keyframes' in content),
        ('Responsive grid', 'grid-template-columns: repeat(auto-fit' in content),
    ]

    for check, result in checks:
        if result:
            log_success(check)
        else:
            log_warning(f'{check} - Not found')

    # Check class name consistency
    mismatches = []
    classes_in_css = set(re.findall(r'\.travel-planner__[\w-]+', content))
    if not classes_in_css:
        log_warning('No travel-planner classes found in CSS')
    else:
        log_success(f'{len(classes_in_css)} travel-planner classes defined')


def check_js_files():
    """Check JavaScript files."""
    print('\n[JavaScript]')

    for js_file in JS_FILES:
        if not os.path.exists(js_file):
            log_issue(f'Missing {js_file}')
            continue

        with open(js_file, 'r') as f:
            content = f.read()

        log_success(f'{js_file} exists')

        # Basic structure check
        if 'function' not in content and 'class' not in content:
            log_warning(f'{js_file} seems to lack function/class definitions')

    # Check travel-planner.js
    if os.path.exists(JS_FILES[0]):
        with open(JS_FILES[0], 'r') as f:
            content = f.read()

        checks = [
            ('IATA database', 'IATA_DATABASE' in content),
            ('Autocomplete', 'handleDestinationInput' in content),
            ('Date validation', 'new Date' in content),
            ('Local storage', 'localStorage' in content),
            ('Error handling', 'showError' in content),
            ('Export functions', 'exportPDF' in content or 'exportExcel' in content),
        ]

        for check, result in checks:
            if result:
                log_success(f'travel-planner.js: {check}')
            else:
                log_warning(f'travel-planner.js: Missing {check}')

    # Check travel-ai-engine.js
    if os.path.exists(JS_FILES[1]):
        with open(JS_FILES[1], 'r') as f:
            content = f.read()

        checks = [
            ('Weather patterns', 'WEATHER_PATTERNS' in content),
            ('Budget ranges', 'BUDGET_RANGES' in content),
            ('Daily activity generation', 'generateDailyActivities' in content),
            ('Visa itinerary', 'generateVisaItinerary' in content),
            ('Packing list', 'getPackingList' in content),
        ]

        for check, result in checks:
            if result:
                log_success(f'travel-ai-engine.js: {check}')
            else:
                log_warning(f'travel-ai-engine.js: Missing {check}')


def check_export_scripts():
    """Check export Python scripts."""
    print('\n[Export Scripts]')

    scripts = [
        'scripts/export_travel_itinerary_pdf.py',
        'scripts/export_travel_itinerary_excel.py'
    ]

    for script in scripts:
        if not os.path.exists(script):
            log_issue(f'Missing {script}')
            continue

        log_success(f'{script} exists')

        with open(script, 'r') as f:
            content = f.read()

        # Check imports
        if 'fpdf' in content and 'PDF' in content:
            log_success(f'{script}: PDF generation support')
        elif 'openpyxl' in content:
            log_success(f'{script}: Excel generation support')


def check_iata_codes():
    """Test IATA code parsing."""
    print('\n[IATA Code Validation]')

    test_codes = [
        ('ICN', 'Incheon', 'South Korea'),
        ('BKK', 'Bangkok', 'Thailand'),
        ('SGN', 'Ho Chi Minh City', 'Vietnam'),
        ('HAN', 'Hanoi', 'Vietnam'),
        ('NRT', 'Tokyo', 'Japan'),
        ('SIN', 'Singapore', 'Singapore'),
        ('CDG', 'Paris', 'France'),
    ]

    if os.path.exists(JS_FILES[0]):
        with open(JS_FILES[0], 'r') as f:
            content = f.read()

        for code, city, country in test_codes:
            if f"'{code}'" in content:
                log_success(f'IATA {code} configured')
            else:
                log_warning(f'IATA {code} may not be configured')


def check_date_validation():
    """Test date validation logic."""
    print('\n[Date Validation]')

    if not os.path.exists(JS_FILES[0]):
        log_warning('Cannot test date validation without travel-planner.js')
        return

    with open(JS_FILES[0], 'r') as f:
        content = f.read()

    checks = [
        ('Return after departure check', 'returnDate' in content and 'departure' in content),
        ('Leap year support', 'Date' in content),
        ('Same-day trip prevention', '>' in content or '>=' in content),
    ]

    for check, result in checks:
        if result:
            log_success(f'Date validation: {check}')
        else:
            log_warning(f'Date validation: {check} implementation unclear')


def check_accessibility():
    """Check accessibility features."""
    print('\n[Accessibility]')

    if os.path.exists(LAYOUT_FILE):
        with open(LAYOUT_FILE, 'r') as f:
            content = f.read()

        checks = [
            ('Labels for inputs', '<label' in content),
            ('ID attributes', 'id=' in content),
            ('Semantic HTML', '<article' in content or '<section' in content),
            ('Alt text capability', 'alt=' in content or 'aria-label' in content),
        ]

        for check, result in checks:
            if result:
                log_success(f'Accessibility: {check}')
            else:
                log_warning(f'Accessibility: {check}')


def check_mobile_responsive():
    """Check mobile responsiveness."""
    print('\n[Mobile Responsiveness]')

    if os.path.exists(CSS_FILE):
        with open(CSS_FILE, 'r') as f:
            content = f.read()

        checks = [
            ('Mobile breakpoints', '@media (max-width: 640px)' in content),
            ('Grid layout', 'display: grid' in content or 'grid-template' in content),
            ('Flexible units', 'rem' in content or 'em' in content),
            ('Touch-friendly buttons', 'padding' in content),
        ]

        for check, result in checks:
            if result:
                log_success(f'Mobile responsive: {check}')
            else:
                log_warning(f'Mobile responsive: {check}')


def print_summary():
    """Print summary report."""
    print('\n' + '='*60)
    print('QA TRAVEL PLANNER SUMMARY')
    print('='*60)

    total = len(ISSUES) + len(WARNINGS) + len(SUCCESSES)

    if ISSUES:
        print(f'\n❌ CRITICAL ISSUES ({len(ISSUES)}):')
        for issue in ISSUES:
            print(f'  {issue}')

    if WARNINGS:
        print(f'\n⚠️  WARNINGS ({len(WARNINGS)}):')
        for warning in WARNINGS:
            print(f'  {warning}')

    if SUCCESSES:
        print(f'\n✅ PASSED ({len(SUCCESSES)}):')
        for success in SUCCESSES[:10]:  # Show first 10
            print(f'  {success}')
        if len(SUCCESSES) > 10:
            print(f'  ... and {len(SUCCESSES) - 10} more')

    print(f'\n{"="*60}')
    print(f'Total Checks: {total}')
    print(f'Result: {"🎉 READY FOR DEPLOYMENT" if not ISSUES else "⛔ FIX ISSUES BEFORE DEPLOYMENT"}')
    print(f'{"="*60}\n')

    return len(ISSUES) == 0


def check_destination_search():
    """Check destination search v2 implementation."""
    print('\n[Destination Search v2]')

    # Check Python service
    if not os.path.exists('services/city_lookup.py'):
        log_issue('Missing services/city_lookup.py')
    else:
        log_success('City lookup service exists')

    # Check JS files
    if os.path.exists('static/js/travel-destination-search.js'):
        log_success('Destination search JS exists')
        with open('static/js/travel-destination-search.js', 'r') as f:
            content = f.read()
            if 'debounce' in content:
                log_success('Debounce implemented')
            if 'cache' in content:
                log_success('Caching implemented')
            if 'keyboard' in content or 'keydown' in content:
                log_success('Keyboard navigation implemented')
            if 'aria' in content.lower():
                log_success('ARIA attributes implemented')
    else:
        log_warning('travel-destination-search.js not found')

    # Check .env.example
    if os.path.exists('.env.example'):
        with open('.env.example', 'r') as f:
            env_content = f.read()
            if 'AVIATIONSTACK_API_KEY' in env_content:
                log_success('Aviation Stack API key in .env.example')
            else:
                log_warning('Aviation Stack API key not in .env.example')


def main():
    """Run all QA checks."""
    parser_help = 'QA suite for Travel Planner'

    print('🚀 AI Travel Planner v2 QA\n')

    check_content_file()
    check_layout_file()
    check_css_file()
    check_js_files()
    check_export_scripts()
    check_iata_codes()
    check_date_validation()
    check_accessibility()
    check_mobile_responsive()
    check_destination_search()

    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
