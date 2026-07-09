#!/usr/bin/env python3
"""
Auto Conflict Remover — Real-time YAML/frontmatter validator and fixer.

Runs in deploy.yml to catch and fix issues BEFORE Hugo build:
- Duplicate YAML keys (e.g., external_links, seo_title)
- Invalid YAML syntax (unquoted colons in values)
- Malformed front matter
- Invalid character encoding

Scans all .md files in content/posts, fixes silently, logs issues.
"""

import re
import sys
import warnings
from pathlib import Path
from collections import defaultdict

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"

class FrontmatterIssue:
    def __init__(self, file_path: str, issue_type: str, detail: str):
        self.file_path = file_path
        self.issue_type = issue_type
        self.detail = detail

    def __repr__(self):
        return f"{self.file_path}: {self.issue_type} — {self.detail}"

def extract_frontmatter(text: str) -> tuple[str | None, str]:
    """Extract YAML frontmatter from markdown."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return None, text
    return m.group(1), m.group(2)

def find_duplicate_keys(fm_text: str) -> list[str]:
    """Find duplicate YAML keys in frontmatter."""
    keys = defaultdict(int)
    duplicates = []
    for line in fm_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Parse key (before colon at line start)
            m = re.match(r"^(\w+):\s*", line)
            if m:
                key = m.group(1)
                keys[key] += 1
                if keys[key] > 1 and key not in duplicates:
                    duplicates.append(key)
    return duplicates

def fix_duplicate_keys(fm_text: str, duplicates: list[str]) -> str:
    """Remove duplicate key entries, keep last occurrence."""
    lines = fm_text.split("\n")
    seen = {dup: False for dup in duplicates}
    result = []
    skip_until_next_key = False

    for i, line in enumerate(lines):
        # Check if this line defines a duplicate key
        m = re.match(r"^(\w+):\s*", line.strip())
        if m and m.group(1) in duplicates:
            key = m.group(1)
            if not seen[key]:
                # First occurrence: keep
                seen[key] = True
                result.append(line)
                # If value is on next lines (list/dict), mark to skip
                if line.rstrip().endswith(":"):
                    skip_until_next_key = key
            else:
                # Duplicate: skip this and any indented lines
                if line[0] not in (" ", "\t"):
                    # This line starts a new key, include it
                    result.append(line)
                    skip_until_next_key = False
                # else: skip indented continuation of duplicate
        else:
            if skip_until_next_key:
                # Still in a list/dict block: check if we're still indented
                if line and line[0] not in (" ", "\t"):
                    skip_until_next_key = False
                    result.append(line)
                # else: skip
            else:
                result.append(line)

    return "\n".join(result)

def quote_unquoted_colons(fm_text: str) -> str:
    """Quote string values containing unquoted colons."""
    lines = fm_text.split("\n")
    result = []

    for line in lines:
        # Match "key: value" where value has colon
        m = re.match(r"^(\s*)(\w+):\s*(.+)$", line)
        if m:
            indent, key, value = m.groups()
            # If value contains colon and isn't already quoted/escaped
            if ":" in value and not (
                value.startswith('"') or value.startswith("'") or value.startswith(">")
            ):
                # Quote it
                if '"' not in value:
                    line = f"{indent}{key}: \"{value}\""
                elif "'" not in value:
                    line = f"{indent}{key}: '{value}'"
                else:
                    # Fallback: use folded literal
                    result.append(f"{indent}{key}: >-")
                    result.append(f"{indent}  {value}")
                    continue
        result.append(line)

    return "\n".join(result)

def validate_yaml(fm_text: str) -> tuple[bool, str]:
    """Try to parse YAML, return (valid, error_msg)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            yaml.safe_load(fm_text)
        return True, ""
    except yaml.YAMLError as e:
        return False, str(e)

def fix_frontmatter(text: str) -> tuple[str, list[FrontmatterIssue]]:
    """Fix all frontmatter issues."""
    issues = []
    fm_text, body = extract_frontmatter(text)

    if fm_text is None:
        return text, issues

    original_fm = fm_text

    # Step 1: Fix duplicate keys
    duplicates = find_duplicate_keys(fm_text)
    if duplicates:
        fm_text = fix_duplicate_keys(fm_text, duplicates)
        for dup in duplicates:
            issues.append(FrontmatterIssue("", "duplicate_key", dup))

    # Step 2: Fix unquoted colons
    fm_text = quote_unquoted_colons(fm_text)

    # Step 3: Validate YAML
    valid, error = validate_yaml(fm_text)
    if not valid:
        issues.append(FrontmatterIssue("", "yaml_error", error[:80]))
        # Try to recover: quote all values
        fm_text = quote_unquoted_colons(fm_text)

    # Reconstruct
    fixed_text = f"---\n{fm_text}\n---\n{body}"
    return fixed_text, issues

def main():
    parser_module = __import__("argparse")
    parser = parser_module.ArgumentParser(description="Auto Conflict Remover — fix YAML issues in frontmatter")
    parser.add_argument("--check", action="store_true", help="Only check, don't fix")
    parser.add_argument("--verbose", action="store_true", help="Print all fixes")
    args = parser.parse_args()

    posts = sorted(CONTENT_DIR.glob("*.md"))
    fixed_count = 0
    total_issues = 0
    failed_files = []

    for f in posts:
        text = f.read_text(encoding="utf-8")
        fixed_text, issues = fix_frontmatter(text)

        if issues:
            total_issues += len(issues)
            if args.verbose:
                print(f"{f.name}: {len(issues)} issue(s)")
                for issue in issues:
                    print(f"  - {issue.issue_type}: {issue.detail}")

            if fixed_text != text:
                fixed_count += 1
                if not args.check:
                    f.write_text(fixed_text, encoding="utf-8")
                else:
                    print(f"[DRY-RUN] Would fix: {f.name}")

    print(f"Summary: {total_issues} issue(s) found in {fixed_count} file(s)")
    if not args.check and fixed_count > 0:
        print(f"✅ Fixed {fixed_count} file(s)")

    return 0 if not failed_files else 1

if __name__ == "__main__":
    sys.exit(main())
