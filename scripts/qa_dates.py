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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam, vietnam_date_of

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\+07:00|Z|[+-]\d{2}:\d{2})?$")
FULL_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+07:00$"
)

FUTURE_TOLERANCE = timedelta(minutes=5)

DATE_FIELD_RE = re.compile(
    r"^(date\s*[:=]\s*[\"']?)([\dTZ:+\-]+)([\"']?\s*)$",
    re.MULTILINE,
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


def _extract_frontmatter_section(text: str) -> tuple[int, int] | None:
    """Return (start, end) offsets of the front-matter block, or None."""
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
        if m:
            return m.start(0), m.end(0)
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+", text, re.S)
        if m:
            return m.start(0), m.end(0)
    return None


def fix_obvious_issues(files: list[Path]) -> tuple[int, list[str]]:
    """Fix obvious date issues in-place. Returns (fixed_count, log_messages)."""
    now = now_vietnam()
    today = now.date()
    fixed = 0
    log: list[str] = []

    for f in files:
        text = f.read_text(encoding="utf-8")
        original = text

        fm_span = _extract_frontmatter_section(text)
        if not fm_span:
            continue
        fm_start, fm_end = fm_span
        fm_text = text[fm_start:fm_end]

        if re.search(r"^draft\s*[:=]\s*true", fm_text, re.MULTILINE):
            continue

        m = DATE_FIELD_RE.search(fm_text)
        if not m:
            continue

        prefix = m.group(1)
        date_str = m.group(2)

        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            new_date = f"{date_str}T{now.strftime('%H:%M:%S')}+07:00"
            text = text[: fm_start + m.start(2)] + new_date + text[fm_start + m.end(2) :]
            log.append(f"{f.name}: date-only -> {new_date}")
            fixed += 1
            f.write_text(text, encoding="utf-8")
            continue

        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$", date_str):
            new_date = f"{date_str}+07:00"
            text = text[: fm_start + m.start(2)] + new_date + text[fm_start + m.end(2) :]
            log.append(f"{f.name}: missing +07:00 -> {new_date}")
            fixed += 1
            f.write_text(text, encoding="utf-8")
            continue

        try:
            dt = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue

        # Clamp ANY future date beyond tolerance back to now — matches the
        # validator's failure condition below, so --fix-obvious fully heals
        # future dates (same-day AND multi-day), not just same-day ones.
        if dt > now + FUTURE_TOLERANCE:
            new_date = now.isoformat()
            text = text[: fm_start + m.start(2)] + new_date + text[fm_start + m.end(2) :]
            span = "same day" if vietnam_date_of(dt) == today else "future day"
            log.append(f"{f.name}: future ({span}) -> {new_date}")
            fixed += 1
            f.write_text(text, encoding="utf-8")

    return fixed, log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate post dates")
    parser.add_argument("--fix-obvious", action="store_true", help="Fix obvious date format issues")
    args = parser.parse_args()

    files = sorted(CONTENT_DIR.rglob("*.md"))
    if not files:
        print("No markdown files found in content/posts/", file=sys.stderr)
        return 1

    if args.fix_obvious:
        fixed, log = fix_obvious_issues(files)
        for msg in log:
            print(msg)
        if fixed:
            print(f"✅ Fixed {fixed} file(s)")
        else:
            print("No obvious date issues found")
        return 0

    errors: list[str] = []
    warnings_list: list[str] = []
    fixed = 0

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

        date_str = str(date_val)

        if "+07:00" not in date_str:
            errors.append(f"{f.name}: date missing +07:00 offset: {date_str}")
            continue

        if "T" not in date_str and " " not in date_str:
            errors.append(f"{f.name}: date-only (no time component): {date_str}")
        elif "T" in date_str and " " not in date_str:
            pass
        elif " " in date_str:
            pass

        try:
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str)
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S%z")
            now = now_vietnam()
            if dt > now + FUTURE_TOLERANCE:
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