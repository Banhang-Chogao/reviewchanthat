#!/usr/bin/env python3
"""
Deploy Failure Auto-Healer
===========================
Comprehensive system to detect, diagnose, and auto-heal deployment failures.
Follows all rules from AGENTS.md and applies experience from past fixes.

Usage:
  python3 scripts/deploy-failure-healer.py --scan         # Detect issues
  python3 scripts/deploy-failure-healer.py --fix-all      # Auto-heal all
  python3 scripts/deploy-failure-healer.py --dry-run      # Preview fixes
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
SCRIPTS_DIR = REPO_ROOT / "scripts"

class DeployFailureHealer:
    """Auto-healer for deployment failures based on AGENTS.md rules."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.issues = []
        self.fixes = []
        self.error_patterns = {
            'toml_syntax': r'commit:\s+|date:\s+|image:\s+',  # YAML in TOML
            'missing_commit': r'^(?!.*commit\s*=)',
            'missing_image': r'(image\s*=\s*""|thumbnail\s*=\s*"")',
            'future_date': None,  # Checked separately
            'missing_word_count': None,  # Checked separately
            'fake_links': r'/posts/placeholder-',
            'image_api_marker': r'!\[\[IMAGE_API_QUERY:',
            'yaml_date': r'date:\s+',
            'broken_frontmatter': r'^\+\+\+$',  # Unclosed TOML
        }

    def scan_all_posts(self) -> List[Dict]:
        """Scan all posts for deployment failures."""
        issues = []
        files = sorted(CONTENT_DIR.rglob("*.md"))

        for filepath in files:
            file_issues = self.scan_post(filepath)
            issues.extend(file_issues)

        issues.extend(self.scan_site())
        return issues

    def scan_site(self) -> List[Dict]:
        """Site-level (non-post) checks."""
        issues = []
        # Rule 11: render-image hook must exist. Without it, inline body images that
        # use root-absolute paths (/images/posts/x.webp) keep the bare path and 404
        # on a subpath baseURL (GitHub Pages /reviewchanthat/). The hook trims the
        # leading slash then relURL, resolving them under the baseURL.
        hook = REPO_ROOT / 'layouts' / '_default' / '_markup' / 'render-image.html'
        if not hook.exists():
            issues.append({
                'file': 'layouts/_default/_markup/render-image.html',
                'type': 'missing_render_image_hook',
                'severity': 'CRITICAL',
                'message': 'render-image hook missing — inline images will 404 under the baseURL subpath',
                'fix': 'Run: python3 scripts/qa_inline_images.py --fix (recreates the hook)',
                'line': None,
            })
        return issues

    def scan_post(self, filepath: Path) -> List[Dict]:
        """Scan a single post for all deployment issues."""
        issues = []
        content = filepath.read_text(encoding='utf-8')
        filename = filepath.name

        # Rule 12: Check for empty/zero-byte files
        if len(content.strip()) == 0:
            issues.append({
                'file': filename,
                'type': 'empty_file',
                'severity': 'CRITICAL',
                'message': 'File is empty (0 bytes) — not valid TOML frontmatter, breaks Hugo build',
                'fix': 'Delete the file',
                'line': 1
            })
            return issues

        # Extract frontmatter
        fm_match = re.match(r'^\+\+\+\r?\n(.*?)\r?\n\+\+\+', content, re.DOTALL)
        if not fm_match:
            issues.append({
                'file': filename,
                'type': 'broken_frontmatter',
                'severity': 'CRITICAL',
                'message': 'Frontmatter not found or malformed',
                'fix': 'Ensure post starts with +++ and ends with +++',
                'line': 1
            })
            return issues

        fm_text = fm_match.group(1)
        body_text = content[fm_match.end():]

        # Rule 1: Check for YAML syntax in TOML
        if re.search(r'^\s*(commit|date|image|title|draft|tags):\s+', fm_text, re.MULTILINE):
            issues.append({
                'file': filename,
                'type': 'yaml_syntax_in_toml',
                'severity': 'CRITICAL',
                'message': 'YAML syntax (key: value) used instead of TOML (key = "value")',
                'fix': 'Replace all colons with equals and wrap values in quotes',
                'line': fm_text.split('\n').index([l for l in fm_text.split('\n') if ':' in l][0]) + 2
            })

        # Rule 2: Check for missing commit hash
        if not re.search(r'commit\s*=\s*"[a-f0-9]{7,}"', fm_text):
            issues.append({
                'file': filename,
                'type': 'missing_commit_hash',
                'severity': 'CRITICAL',
                'message': 'Missing or invalid commit hash field',
                'fix': 'Run: python3 scripts/add_commit_id.py',
                'line': 3
            })

        # Rule 3: Check for missing image/thumbnail
        if not re.search(r'image\s*=\s*"[^"]+\.webp"', fm_text) or \
           not re.search(r'thumbnail\s*=\s*"[^"]+\.webp"', fm_text):
            issues.append({
                'file': filename,
                'type': 'missing_image',
                'severity': 'CRITICAL',
                'message': 'Missing hero image or thumbnail in frontmatter',
                'fix': 'Run: python3 scripts/select_images.py --post content/posts/' + filename + ' --fix',
                'line': 6
            })

        # Rule 4: Check for draft status
        if re.search(r'draft\s*=\s*true', fm_text):
            issues.append({
                'file': filename,
                'type': 'draft_post',
                'severity': 'WARNING',
                'message': 'Post is marked as draft',
                'fix': 'Change draft = false or remove from deployment',
                'line': re.search(r'draft\s*=', fm_text).start() // len(fm_text.split('\n')[0]) + 2
            })

        # Rule 5: Check date format (must be ISO 8601 +07:00)
        date_match = re.search(r'date\s*=\s*"([^"]+)"', fm_text)
        if date_match:
            date_str = date_match.group(1)
            if '+07:00' not in date_str:
                issues.append({
                    'file': filename,
                    'type': 'wrong_timezone',
                    'severity': 'CRITICAL',
                    'message': f'Date missing +07:00 timezone: {date_str}',
                    'fix': 'Add +07:00 to date. Run: python3 scripts/qa_dates.py --fix-obvious',
                    'line': fm_text.count('\n', 0, date_match.start()) + 2
                })

            # Check for future dates
            try:
                dt = datetime.fromisoformat(date_str)
                now = datetime.now(timezone.utc).astimezone()
                if dt > now:
                    issues.append({
                        'file': filename,
                        'type': 'future_date',
                        'severity': 'ERROR',
                        'message': f'Date is in future: {date_str}',
                        'fix': 'Set date to current time. Run: python3 scripts/qa_dates.py --fix-obvious',
                        'line': fm_text.count('\n', 0, date_match.start()) + 2
                    })
            except ValueError:
                issues.append({
                    'file': filename,
                    'type': 'invalid_date_format',
                    'severity': 'CRITICAL',
                    'message': f'Invalid date format: {date_str}',
                    'fix': 'Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS+07:00',
                    'line': fm_text.count('\n', 0, date_match.start()) + 2
                })

        # Rule 6: Check word count (must be 3000+ words)
        body_words = len(body_text.split())
        if body_words < 3000:
            issues.append({
                'file': filename,
                'type': 'insufficient_content',
                'severity': 'WARNING',
                'message': f'Post has only {body_words} words (minimum 3000 required)',
                'fix': 'Add more content to reach 3000 words minimum',
                'line': None
            })

        # Rule 7: Check for fake internal links
        if re.search(r'/posts/placeholder-', body_text):
            issues.append({
                'file': filename,
                'type': 'fake_internal_links',
                'severity': 'CRITICAL',
                'message': 'Contains placeholder internal links (/posts/placeholder-*)',
                'fix': 'Remove all fake internal links that reference non-existent posts',
                'line': None
            })

        # Rule 8: Check for IMAGE_API_QUERY markers
        if re.search(r'!\[\[IMAGE_API_QUERY:', body_text):
            issues.append({
                'file': filename,
                'type': 'dead_image_marker',
                'severity': 'CRITICAL',
                'message': 'Contains dead ![[IMAGE_API_QUERY:...]] markers in content',
                'fix': 'Remove markers and replace with actual image URLs using ![](URL) format',
                'line': None
            })

        # Rule 9: Check meta description length (SEO: 50-160 chars)
        # Google truncates >160 chars in SERP; <50 wastes snippet space.
        # No safe regex auto-fix — rewriting needs semantic edit, so report only.
        desc_match = re.search(r'(?m)^description\s*=\s*"(.*)"\s*$', fm_text)
        if desc_match:
            desc_len = len(desc_match.group(1))
            if desc_len < 50 or desc_len > 160:
                issues.append({
                    'file': filename,
                    'type': 'meta_description_length',
                    'severity': 'WARNING',
                    'message': f'Meta description is {desc_len} chars (SEO range 50-160)',
                    'fix': 'Rewrite description to 50-160 chars, keyword up front, aim ~150-158',
                    'line': fm_text.count('\n', 0, desc_match.start()) + 2
                })

        # Rule 10: Check inline images point to real files on disk.
        # Inline body images (![](...images/posts/x.webp)) resolve to a webp under
        # static/images/posts/. If the file is missing, the image renders broken on
        # live. baseURL/subpath resolution itself is handled by the render-image hook
        # (layouts/_default/_markup/render-image.html) — see Rule 11.
        for im in re.finditer(r'!\[[^\]]*\]\((/?images/posts/[^)]+?\.webp)\)', body_text):
            ref = im.group(1)
            disk_path = REPO_ROOT / 'static' / ref.lstrip('/')
            if not disk_path.exists():
                issues.append({
                    'file': filename,
                    'type': 'broken_inline_image',
                    'severity': 'WARNING',
                    'message': f'Inline image references a missing file: {ref}',
                    'fix': 'Generate the webp (Pexels/Pixabay) or remove the ![](...) line; do not ship a broken image',
                    'line': None
                })

        return issues

    def auto_fix_post(self, filepath: Path) -> Tuple[bool, List[str]]:
        """Auto-fix common issues in a post."""
        if self.dry_run:
            return False, []

        # Fix 0: Delete empty/zero-byte files
        if filepath.stat().st_size == 0:
            filepath.unlink()
            return True, ['🗑 Deleted empty file (0 bytes) — would break Hugo build']

        content = filepath.read_text(encoding='utf-8')
        original_content = content
        fixes_applied = []

        # Fix 1: Convert YAML syntax to TOML in frontmatter
        content = re.sub(
            r'^\s*(commit|date|image|title|draft|tags|description|categories):\s+([^\n]+)',
            lambda m: f'{m.group(1)} = "{m.group(2).strip()}"' if m.group(1) != 'draft' else f'{m.group(1)} = {m.group(2).strip().lower()}',
            content,
            flags=re.MULTILINE
        )
        if content != original_content:
            fixes_applied.append('✓ Fixed YAML to TOML syntax conversion')
            original_content = content

        # Fix 2: Add missing commit hash
        if not re.search(r'commit\s*=\s*"[a-f0-9]{7,}"', content):
            try:
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%h', '--', str(filepath)],
                    capture_output=True, text=True, cwd=str(REPO_ROOT)
                )
                commit_hash = result.stdout.strip()
                if commit_hash:
                    content = re.sub(
                        r'(title\s*=\s*"[^"]*")\n(date\s*=)',
                        rf'\1\ncommit = "{commit_hash}"\n\2',
                        content,
                        count=1
                    )
                    fixes_applied.append(f'✓ Added commit hash: {commit_hash}')
            except Exception as e:
                fixes_applied.append(f'⚠ Failed to add commit hash: {e}')

        # Fix 3: Remove fake links
        if re.search(r'/posts/placeholder-', content):
            content = re.sub(r'\[([^\]]*)\]\(/posts/placeholder-[^\)]*\)', r'\1', content)
            fixes_applied.append('✓ Removed fake internal links to placeholder posts')

        # Fix 4: Remove dead IMAGE_API_QUERY markers
        if re.search(r'!\[\[IMAGE_API_QUERY:', content):
            content = re.sub(r'!\[\[IMAGE_API_QUERY:[^\]]*\]\]', '', content)
            fixes_applied.append('✓ Removed dead IMAGE_API_QUERY markers')

        # Write back if changes made
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            return True, fixes_applied

        return False, fixes_applied

    def run_external_validators(self) -> Dict:
        """Run qa_dates.py and rule.py validators."""
        results = {
            'qa_dates': {'passed': False, 'output': ''},
            'rule_py': {'passed': False, 'output': ''},
        }

        try:
            # Run qa_dates.py
            result = subprocess.run(
                ['python3', 'scripts/qa_dates.py'],
                capture_output=True, text=True, cwd=str(REPO_ROOT)
            )
            results['qa_dates']['passed'] = result.returncode == 0
            results['qa_dates']['output'] = result.stdout + result.stderr
        except Exception as e:
            results['qa_dates']['output'] = str(e)

        try:
            # Run rule.py --fix
            result = subprocess.run(
                ['python3', 'scripts/rule.py', '--fix'],
                capture_output=True, text=True, cwd=str(REPO_ROOT)
            )
            results['rule_py']['passed'] = result.returncode == 0
            results['rule_py']['output'] = result.stdout + result.stderr
        except Exception as e:
            results['rule_py']['output'] = str(e)

        return results

    def generate_report(self, issues: List[Dict]) -> str:
        """Generate a detailed report of all issues found."""
        if not issues:
            return "✅ No deployment issues found!"

        report = "🔴 DEPLOYMENT FAILURE REPORT\n" + "=" * 80 + "\n\n"

        # Group by severity
        critical = [i for i in issues if i['severity'] == 'CRITICAL']
        errors = [i for i in issues if i['severity'] == 'ERROR']
        warnings = [i for i in issues if i['severity'] == 'WARNING']

        if critical:
            report += f"🔴 CRITICAL ISSUES ({len(critical)}):\n"
            for issue in critical:
                report += f"  - {issue['file']}: {issue['type']}\n"
                report += f"    Message: {issue['message']}\n"
                report += f"    Fix: {issue['fix']}\n\n"

        if errors:
            report += f"🟠 ERRORS ({len(errors)}):\n"
            for issue in errors:
                report += f"  - {issue['file']}: {issue['type']}\n"
                report += f"    Message: {issue['message']}\n"
                report += f"    Fix: {issue['fix']}\n\n"

        if warnings:
            report += f"🟡 WARNINGS ({len(warnings)}):\n"
            for issue in warnings:
                report += f"  - {issue['file']}: {issue['type']}\n"
                report += f"    Message: {issue['message']}\n"
                report += f"    Fix: {issue['fix']}\n\n"

        report += "\n" + "=" * 80 + "\n"
        report += f"Total Issues: {len(issues)} (Critical: {len(critical)}, Errors: {len(errors)}, Warnings: {len(warnings)})\n"

        return report

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Deploy Failure Auto-Healer')
    parser.add_argument('--scan', action='store_true', help='Scan for issues')
    parser.add_argument('--fix-all', action='store_true', help='Auto-fix all issues')
    parser.add_argument('--dry-run', action='store_true', help='Preview fixes without applying')
    parser.add_argument('--post', help='Scan/fix specific post file')

    args = parser.parse_args()

    healer = DeployFailureHealer(dry_run=args.dry_run)

    if args.scan or (not args.fix_all):
        print("🔍 Scanning for deployment failures...\n")
        if args.post:
            issues = healer.scan_post(Path(args.post))
        else:
            issues = healer.scan_all_posts()

        print(healer.generate_report(issues))

        if not args.dry_run:
            print("\n🔧 Running external validators...")
            results = healer.run_external_validators()
            for validator, result in results.items():
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"{validator}: {status}")

    if args.fix_all:
        print("🔨 Auto-fixing deployment issues...\n")
        if args.post:
            fixed, fixes = healer.auto_fix_post(Path(args.post))
            if fixed:
                print(f"Fixed {Path(args.post).name}:")
                for fix in fixes:
                    print(f"  {fix}")
        else:
            files = sorted(CONTENT_DIR.rglob("*.md"))
            fixed_count = 0
            for filepath in files:
                fixed, fixes = healer.auto_fix_post(filepath)
                if fixed:
                    fixed_count += 1
                    print(f"✓ {filepath.name}")
                    for fix in fixes:
                        print(f"  {fix}")
            print(f"\n✅ Fixed {fixed_count} post(s)")

if __name__ == '__main__':
    main()
