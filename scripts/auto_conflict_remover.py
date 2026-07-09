#!/usr/bin/env python3
"""
Auto Conflict Remover — Conservative YAML fixer for deployment.

Only fixes:
1. Description field with colons (convert to folded string)
2. Trailing > in external_links entries
3. Skip ai_summary entirely (let normalize handle it)
"""

import re
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

def fix_description_only(fm_text: str) -> str:
    """
    ONLY fix description field: if it has multiline with colons,
    collapse to a single double-quoted line.

    Very conservative: don't touch anything else.
    """
    lines = fm_text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # description: "..." single-line (balanced quotes) — leave alone
        if re.match(r"^description:\s*", line):
            stripped = line.rstrip()
            # Already a complete single-line quoted value
            if re.match(r'^description:\s*"[^"]*"\s*$', stripped) or re.match(
                r"^description:\s*'[^']*'\s*$", stripped
            ):
                result.append(line)
                i += 1
                continue

            # Multi-line quoted / unquoted description: gather until next top-level key
            m = re.match(r"^(description:\s*)(.*)$", line)
            if m:
                prefix_rest = m.group(2)
                value_parts = []
                if prefix_rest.strip():
                    value_parts.append(prefix_rest.strip().lstrip("'\""))
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if re.match(r"^[A-Za-z0-9_]+:\s*", next_line):
                        break
                    if next_line.strip():
                        value_parts.append(next_line.strip().rstrip("'\""))
                    i += 1
                full_value = " ".join(value_parts).strip().strip("'\"")
                escaped = full_value.replace("\\", "\\\\").replace('"', '\\"')
                result.append(f'description: "{escaped}"')
                continue

        result.append(line)
        i += 1

    return "\n".join(result)

def fix_external_links_trailing_chars(fm_text: str) -> str:
    """Remove trailing > from external_links title/url values."""
    lines = fm_text.split("\n")
    result = []

    for line in lines:
        # Only fix lines inside external_links section (indented lines with title: or url:)
        if re.match(r"^\s{4}(title|url):", line):
            # Remove trailing > if present
            if line.rstrip().endswith(">"):
                line = line.rstrip()[:-1]
        result.append(line)

    return "\n".join(result)

def dedupe_top_level_keys(fm_text: str) -> tuple[str, list[str]]:
    """Keep the first occurrence of each top-level key; drop later duplicates.

    Hugo fails hard on duplicate keys (e.g. two description: lines).
    """
    lines = fm_text.split("\n")
    seen: set[str] = set()
    out: list[str] = []
    removed: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_]+):\s*", line)
        if m:
            key = m.group(1)
            if key in seen:
                removed.append(key)
                i += 1
                # Skip indented continuation lines belonging to the duplicate key
                while i < len(lines):
                    nxt = lines[i]
                    if not nxt.strip():
                        i += 1
                        continue
                    if re.match(r"^[A-Za-z0-9_]+:\s*", nxt):
                        break
                    if nxt.startswith(" ") or nxt.startswith("\t"):
                        i += 1
                        continue
                    break
                continue
            seen.add(key)
        out.append(line)
        i += 1
    return "\n".join(out), removed


def fix_frontmatter(text: str) -> tuple[str, list[str]]:
    """Apply fixes conservatively."""
    issues = []
    fm_text, body = extract_frontmatter(text)

    if fm_text is None:
        return text, issues

    # Step 0: Drop duplicate top-level keys (Hugo fatal)
    fm_text_before = fm_text
    fm_text, removed = dedupe_top_level_keys(fm_text)
    if removed:
        issues.append(f"deduped_keys:{','.join(removed)}")

    # Step 1: Fix description field ONLY
    fm_text_before = fm_text
    fm_text = fix_description_only(fm_text)
    if fm_text != fm_text_before:
        issues.append("fixed_description")

    # Step 2: Fix trailing > in external_links
    fm_text_before = fm_text
    fm_text = fix_external_links_trailing_chars(fm_text)
    if fm_text != fm_text_before:
        issues.append("fixed_external_links")

    # Reconstruct
    fixed_text = f"---\n{fm_text}\n---\n{body}"
    return fixed_text, issues

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto Conflict Remover — conservative fixes only")
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
                print(f"{f.name}: {', '.join(issues)}")

            if fixed_text != text:
                fixed_count += 1
                if not args.check:
                    f.write_text(fixed_text, encoding="utf-8")

    print(f"Summary: {total_issues} issue(s) found in {fixed_count} file(s)")
    if fixed_count > 0 and not args.check:
        print(f"✅ Fixed {fixed_count} file(s)")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
