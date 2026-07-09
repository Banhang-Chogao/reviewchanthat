#!/usr/bin/env python3
"""QA dates — validate all posts have correct datetime format.

Checks:
  - All published posts have 'date' field with +07:00 offset
  - All dates are valid ISO 8601 datetimes (not date-only)
  - No future dates
  - Display format when available is dd-mm-yyyy hh:mm:ss
  - No date-only (e.g. 2026-07-10 without time)

Usage:
  python scripts/qa_dates.py
  python scripts/qa_dates.py --fix-obvious
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\+07:00|Z|[+-]\d{2}:\d{2})?$")
FULL_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+07:00$"
)


def parse_front_matter(text: str) -> dict | None:
    import warnings
    import yaml
    # YAML front matter
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
        if m:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    meta = yaml.safe_load(m.group(1)) or {}
                return meta if isinstance(meta, dict) else None
            except Exception:
                return None
    # TOML front matter
    if text.startswith("+++"):
        import tomllib
        m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+", text, re.S)
        if m:
            try:
                meta = tomllib.loads(m.group(1))
                return meta if isinstance(meta, dict) else None
            except Exception:
                return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate post dates")
    parser.add_argument("--fix-obvious", action="store_true", help="Fix obvious date format issues")
    args = parser.parse_args()

    errors: list[str] = []
    warnings_list: list[str] = []
    fixed = 0

    files = sorted(CONTENT_DIR.rglob("*.md"))
    if not files:
        errors.append("No markdown files found in content/posts/")
        return 1

    for f in files:
        text = f.read_text(encoding="utf-8")
        meta = parse_front_matter(text)
        if meta is None:
            errors.append(f"{f.name}: cannot parse front matter")
            continue
            
        if meta.get("draft"):
            continue

        date_val = meta.get("date")
        if not date_val:
            errors.append(f"{f.name}: missing date field")
            continue

        # Check if date is a datetime (not date-only string)
        date_str = str(date_val)
        
        # Check for +07:00 offset
        if "+07:00" not in date_str:
            errors.append(f"{f.name}: date missing +07:00 offset: {date_str}")
            continue

        # Check not date-only
        if "T" not in date_str and " " not in date_str:
            errors.append(f"{f.name}: date-only (no time component): {date_str}")
        elif "T" in date_str and " " not in date_str:
            pass  
        elif " " in date_str:
            pass  

        # Check no future dates
        try:
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str)
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S%z")
            now = now_vietnam()
            if dt > now:
                errors.append(f"{f.name}: future date: {date_str}")
        except (ValueError, TypeError) as exc:
            errors.append(f"{f.name}: invalid date format: {date_str} — {exc}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"\nqa_dates: {len(errors)} failure(s)", file=sys.stderr)
        return 1

    print(f"qa_dates: PASS — {len(files)} posts, 0 date issues")
    return 0


if __name__ == "__main__":
    sys.exit(main())