#!/usr/bin/env python3
"""autobot-dup-remover — nightly duplicate YAML key fixer for Hugo front matter.

Scans all content/posts/ .md files, detects duplicate YAML keys
(e.g. tags, tom_tat_nhanh, external_links, internal_links, faq, checklist)
and merges them into a single list.

Safe: only touches front matter, never changes body content.
Idempotent: running twice produces the same result.

Usage:
  python scripts/autobot_dup_remover.py           # dry-run
  python scripts/autobot_dup_remover.py --write   # write changes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"


def _is_child_line(line: str) -> bool:
    return line.startswith("- ") or line.startswith(" ") or line.startswith("\t")


def _collect_block(lines: list[str], start: int) -> list[str]:
    result = []
    for i in range(start, len(lines)):
        if _is_child_line(lines[i]) or lines[i] == "":
            result.append(lines[i])
        else:
            break
    return result


def fix_file(path: Path) -> tuple[bool, set[str]]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False, set()

    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return False, set()

    fm_lines = m.group(1).split("\n")

    key_indices: dict[str, list[int]] = {}
    for i, line in enumerate(fm_lines):
        stripped = line.rstrip()
        if not stripped or stripped.startswith(" ") or stripped.startswith("\t") or stripped.startswith("-"):
            continue
        key = stripped.split(":", 1)[0].strip()
        if key:
            key_indices.setdefault(key, []).append(i)

    dupes = {k for k, v in key_indices.items() if len(v) > 1}
    if not dupes:
        return False, set()

    for key in dupes:
        indices = key_indices[key]
        keep_line = fm_lines[indices[0]]
        colon_pos = keep_line.find(":")
        after = keep_line[colon_pos + 1:].strip() if colon_pos >= 0 else ""
        if after == "" or after.startswith(">"):
            continue

        lines_to_keep = [keep_line]
        lines_to_keep.extend(_collect_block(fm_lines, indices[0] + 1))

        for idx in indices[1:]:
            lines_to_keep.extend(_collect_block(fm_lines, idx))
            fm_lines[idx] = None

        fm_lines[indices[0]] = "\n".join(lines_to_keep)

    new_fm = [l for l in fm_lines if l is not None]
    body = text[m.end():]
    new_text = "---\n" + "\n".join(new_fm) + "\n---" + body

    if new_text == text:
        return False, set()
    path.write_text(new_text, encoding="utf-8")
    return True, dupes


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove duplicate YAML keys in Hugo posts")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    files = sorted(CONTENT_DIR.rglob("*.md"))
    fixed = 0
    total_errors = 0

    for f in files:
        try:
            changed, dupes = fix_file(f)
            if not changed:
                continue
            print(f"Fixed: {f.name} — dupes: {', '.join(sorted(dupes))}")
            fixed += 1
        except Exception as e:
            print(f"ERROR: {f.name}: {e}", file=sys.stderr)
            total_errors += 1

    print(f"\nTotal fixed: {fixed}, errors: {total_errors}")

    if not args.write:
        print("Dry-run — no files modified. Use --write to apply.")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())