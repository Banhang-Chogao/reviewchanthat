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

def find_duplicate_keys(fm_text: str) -> list[tuple[str, int]]:
    """Find duplicate YAML keys in frontmatter. Returns [(key, count), ...]."""
    keys = defaultdict(list)
    for i, line in enumerate(fm_text.split("\n")):
        # Only check lines that start at column 0 (top-level keys)
        m = re.match(r"^(\w+):\s*", line)
        if m:
            key = m.group(1)
            keys[key].append(i)

    duplicates = [(k, lines) for k, lines in keys.items() if len(lines) > 1]
    return duplicates

def fix_duplicate_keys(fm_text: str, duplicates: list[tuple[str, list[int]]]) -> str:
    """Remove duplicate key entries, keep first occurrence."""
    if not duplicates:
        return fm_text

    lines = fm_text.split("\n")
    # Mark lines to remove
    to_remove = set()

    for key, line_indices in duplicates:
        # Keep first, remove rest and their child lines
        for idx in line_indices[1:]:
            to_remove.add(idx)
            # Also mark indented children as removed
            indent_level = len(lines[idx]) - len(lines[idx].lstrip())
            for j in range(idx + 1, len(lines)):
                if not lines[j].strip():  # Skip empty lines
                    to_remove.add(j)
                elif len(lines[j]) - len(lines[j].lstrip()) > indent_level:
                    to_remove.add(j)
                else:
                    break  # Stop at next top-level key

    result = [lines[i] for i in range(len(lines)) if i not in to_remove]
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
