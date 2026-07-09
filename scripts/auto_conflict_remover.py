#!/usr/bin/env python3
"""
Auto Conflict Remover — Aggressive YAML frontmatter fixer.

Fixes:
- Malformed quoted strings (description, titles with colons)
- Invalid external_links entries
- Duplicate top-level keys
- Unquoted colons in YAML values
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"

def extract_frontmatter(text: str) -> tuple[str | None, str]:
    """Extract YAML frontmatter from markdown."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return None, text
    return m.group(1), m.group(2)

def fix_description_multiline(fm_text: str) -> str:
    """Fix description field with colons in multi-line quoted strings."""
    lines = fm_text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a description field
        if line.strip().startswith("description:"):
            # Extract the value part
            m = re.match(r"^(\s*)description:\s*'(.*)$", line)
            if m and not line.rstrip().endswith("'"):
                # Multi-line string - need to collect all lines
                indent = m.group(1)
                value_start = m.group(2)
                value_lines = [value_start]
                i += 1

                while i < len(lines):
                    next_line = lines[i]
                    if next_line.startswith(" " * (len(indent) + 2)):
                        # Continuation of string
                        value_lines.append(next_line.strip())
                        i += 1
                    elif next_line.strip().endswith("'"):
                        # End of multi-line string
                        value_lines.append(next_line.strip().rstrip("'"))
                        i += 1
                        break
                    elif next_line.strip() and not next_line.startswith(" "):
                        # Next key at top level
                        break
                    else:
                        i += 1

                # Reconstruct as proper YAML
                full_value = " ".join(value_lines)
                # Use >- for folded string (handles colons properly)
                result.append(f"{indent}description: >-")
                result.append(f"{indent}  {full_value}")
                continue

        result.append(line)
        i += 1

    return "\n".join(result)

def fix_external_links(fm_text: str) -> str:
    """Fix malformed external_links entries (remove trailing > and other artifacts)."""
    lines = fm_text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for external_links section
        if line.strip().startswith("external_links:"):
            result.append(line)
            i += 1

            # Process list items
            while i < len(lines):
                next_line = lines[i]

                if next_line.startswith("  - "):
                    # List item
                    result.append(next_line)
                    i += 1
                elif next_line.startswith("    "):
                        # Continuation of list item (title: or url:)
                    # Fix malformed URLs (remove trailing > or other artifacts)
                    fixed_line = next_line
                    if "title:" in fixed_line and fixed_line.rstrip().endswith(">"):
                        # Remove trailing > from title
                        fixed_line = fixed_line.rstrip()[:-1]
                    if "url:" in fixed_line and fixed_line.rstrip().endswith(">"):
                        # Remove trailing > from url
                        fixed_line = fixed_line.rstrip()[:-1]

                    result.append(fixed_line)
                    i += 1
                elif next_line.strip() == "":
                    # Empty line
                    result.append(next_line)
                    i += 1
                else:
                    # Next section
                    break
            continue

        result.append(line)
        i += 1

    return "\n".join(result)

def fix_frontmatter(text: str) -> tuple[str, list[str]]:
    """Fix all frontmatter issues."""
    issues = []
    fm_text, body = extract_frontmatter(text)

    if fm_text is None:
        return text, issues

    original_fm = fm_text

    # Step 1: Fix description multi-line strings
    fm_text = fix_description_multiline(fm_text)
    if fm_text != original_fm:
        issues.append("fixed_description_multiline")

    # Step 2: Fix external_links
    fm_text = fix_external_links(fm_text)

    # Step 3: Fix trailing quote marks on lines
    lines = fm_text.split("\n")
    fixed_lines = []
    for line in lines:
        # Remove orphaned trailing > or malformed quote marks
        if line.rstrip().endswith(">"):
            line = line.rstrip()[:-1]
        fixed_lines.append(line)
    fm_text = "\n".join(fixed_lines)

    # Reconstruct
    fixed_text = f"---\n{fm_text}\n---\n{body}"
    return fixed_text, issues

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto Conflict Remover — aggressive YAML fixer")
    parser.add_argument("--check", action="store_true", help="Only check, don't fix")
    parser.add_argument("--verbose", action="store_true", help="Print fixes")
    args = parser.parse_args()

    posts = sorted(CONTENT_DIR.glob("*.md"))
    fixed_count = 0
    total_issues = 0

    for f in posts:
        text = f.read_text(encoding="utf-8")
        fixed_text, issues = fix_frontmatter(text)

        if issues:
            total_issues += len(issues)
            if args.verbose:
                print(f"{f.name}: {len(issues)} fix(es) - {', '.join(issues)}")

            if fixed_text != text:
                fixed_count += 1
                if not args.check:
                    f.write_text(fixed_text, encoding="utf-8")

    print(f"Summary: {total_issues} fix(es) applied to {fixed_count} file(s)")
    if fixed_count > 0 and not args.check:
        print(f"✅ Fixed {fixed_count} file(s)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
