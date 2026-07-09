#!/usr/bin/env python3
"""Fix duplicate YAML keys in Hugo front matter by merging them into lists."""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "posts"


def fix_file(path: Path) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return 0, []

    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return 0, []

    fm_text = m.group(1)
    lines = fm_text.split("\n")

    seen_keys: dict[str, list[int]] = {}
    dupes: set[str] = set()

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped or stripped.startswith(" ") or stripped.startswith("\t") or stripped.startswith("-"):
            continue
        key = stripped.split(":", 1)[0].strip()
        if key:
            if key in seen_keys:
                seen_keys[key].append(i)
                dupes.add(key)
            else:
                seen_keys[key] = [i]

    if not dupes:
        return 0, []

    fixed_lines = list(lines)
    merged: set[int] = set()

    for key in dupes:
        indices = seen_keys[key]
        first = indices[0]
        items = []

        for idx in indices:
            line = lines[idx]
            colon_pos = line.find(":")
            after_colon = line[colon_pos + 1:].strip() if colon_pos >= 0 else ""
            if after_colon == "" or after_colon.startswith(">"):
                continue

            val = after_colon
            items.append(val)

            rest_lines = []
            for j in range(idx + 1, len(lines)):
                if j in merged:
                    continue
                l = lines[j]
                if l.startswith("- "):
                    items.append(" " + l)
                    merged.add(j)
                elif l.startswith(" ") or l.startswith("\t"):
                    rest_lines.append(l)
                    merged.add(j)
                else:
                    break

            if idx != first:
                merged.add(idx)

        # Build the merged key
        merged_text = key + ":"
        for item in items:
            merged_text += "\n" + item

        fixed_first = first
        for fi in range(first + 1, min(indices[1] if len(indices) > 1 else first + 2, len(lines))):
            l = lines[fi]
            if l == key + ":" or l.startswith(key + ":"):
                fixed_first = fi
                break

        fixed_lines[fixed_first] = merged_text
        for idx in indices:
            if idx != fixed_first and idx not in merged:
                merged.add(idx)
        for j in range(fixed_first + 1, len(fixed_lines)):
            if j in merged:
                fixed_lines[j] = ""

    # rebuild
    new_fm = [l for l in fixed_lines if l != ""]
    body_start = m.end()
    body = text[body_start:]
    new_text = "---\n" + "\n".join(new_fm) + "\n---" + body
    path.write_text(new_text, encoding="utf-8")
    return 1, sorted(dupes)


def main() -> int:
    files = sorted(CONTENT_DIR.rglob("*.md"))
    fixed = 0
    for f in files:
        count, dupes = fix_file(f)
        if count > 0:
            print(f"Fixed: {f.name} — dupes: {', '.join(dupes)}")
            fixed += 1

    print(f"\nTotal fixed: {fixed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())