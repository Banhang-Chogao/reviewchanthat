#!/usr/bin/env python3
"""Single pre-deploy source-of-truth rule for blog content.

What this owns:
- All post front matter must be TOML (`+++`).
- Publish/composed date fields must be real Vietnam time, never future-dated.
- Hugo storage dates stay ISO `+07:00`; display companion fields use
  `dd-mm-yyyy hh:mm:ss GMT +7`.
- Known safe fixes from the blog's deployment-doctor experience are run before
  validation when `--fix` is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
KNOWLEDGE_PATH = REPO_ROOT / "data" / "deployment-doctor-knowledge.json"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
from dates import VN_TZ, now_vietnam  # noqa: E402

DATE_FIELDS = ("date", "publishDate", "published", "composed", "created", "lastmod", "updated")
DISPLAY_FIELDS = {
    "date": "date_display",
    "publishDate": "publishDate_display",
    "published": "published_display",
    "composed": "composed_display",
    "created": "created_display",
    "lastmod": "lastmod_display",
    "updated": "updated_display",
}
SAFE_FIX_COMMANDS = (
    [sys.executable, "scripts/auto_conflict_remover.py", "--verbose"],
    [sys.executable, "scripts/autobot_dup_remover.py", "--write"],
    [sys.executable, "scripts/normalize_ai_summaries.py", "--fix"],
)


def split_frontmatter(text: str) -> tuple[str, str, str, str] | None:
    if text.startswith("+++"):
        match = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+\r?\n?)(.*)$", text, re.S)
        if match:
            return "toml", match.group(2), match.group(4), match.group(1) + match.group(3)
        # Known conflict: TOML opener with YAML closer. Treat the first YAML
        # delimiter as the close marker so --fix can rewrite canonical TOML.
        match = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n---\r?\n?)(.*)$", text, re.S)
        if match:
            return "toml_mixed", match.group(2), match.group(4), match.group(1) + match.group(3)
    if text.startswith("---"):
        match = re.match(r"^(---\r?\n)(.*?)(\r?\n---\r?\n?)(.*)$", text, re.S)
        if match:
            return "yaml", match.group(2), match.group(4), match.group(1) + match.group(3)
    return None


def load_meta(kind: str, fm_text: str) -> dict[str, Any]:
    """Parse front matter. TOML first for pure TOML; YAML for pure YAML and mixed."""
    meta: Any = None
    if kind == "toml":
        import tomllib

        meta = tomllib.loads(fm_text)
    elif kind == "toml_mixed":
        # Mixed +++ ... --- often has YAML-shaped keys; try TOML then YAML.
        try:
            import tomllib

            meta = tomllib.loads(fm_text)
        except Exception:
            meta = yaml.safe_load(fm_text) or {}
    else:
        meta = yaml.safe_load(fm_text) or {}
    if not isinstance(meta, dict):
        raise ValueError("front matter is not a mapping")
    return dict(meta)


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=VN_TZ)
    elif isinstance(value, str):
        raw = value.strip().strip("'\"")
        raw = raw.replace(" GMT +7", "+07:00").replace(" GMT+7", "+07:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S GMT +7", "%Y-%m-%d %H:%M:%S%z"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    dt = None
            if dt is None:
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ).replace(microsecond=0)


def display_datetime(dt: datetime) -> str:
    return dt.astimezone(VN_TZ).strftime("%d-%m-%Y %H:%M:%S GMT +7")


def toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, datetime):
        return toml_quote(value.astimezone(VN_TZ).replace(microsecond=0).isoformat())
    if isinstance(value, date):
        return toml_quote(datetime(value.year, value.month, value.day, tzinfo=VN_TZ).isoformat())
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return "[" + ", ".join(toml_value(item) for item in value) + "]"
        return toml_quote(json.dumps(value, ensure_ascii=False))
    if value is None:
        return toml_quote("")
    return toml_quote(str(value))


def dump_toml(meta: dict[str, Any]) -> str:
    lines: list[str] = []

    for key, value in meta.items():
        if isinstance(value, dict) or (isinstance(value, list) and value and all(isinstance(x, dict) for x in value)):
            continue
        lines.append(f"{key} = {toml_value(value)}")

    for key, value in meta.items():
        if isinstance(value, dict):
            lines.append("")
            lines.append(f"[{key}]")
            for child_key, child_value in value.items():
                lines.append(f"{child_key} = {toml_value(child_value)}")
        elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            for item in value:
                lines.append("")
                lines.append(f"[[{key}]]")
                for child_key, child_value in item.items():
                    lines.append(f"{child_key} = {toml_value(child_value)}")

    return "\n".join(lines).rstrip() + "\n"


def normalize_dates(meta: dict[str, Any], *, fix: bool) -> tuple[bool, list[str]]:
    now = now_vietnam()
    changed = False
    issues: list[str] = []

    if not meta.get("date"):
        issues.append("missing date")
        if fix:
            meta["date"] = now.isoformat()
            meta["date_display"] = display_datetime(now)
            changed = True

    for field in DATE_FIELDS:
        if field not in meta or meta.get(field) in ("", None):
            continue
        dt = parse_datetime(meta.get(field))
        if dt is None:
            issues.append(f"{field} invalid format: {meta.get(field)!r}")
            if fix:
                dt = now
            else:
                continue
        if dt > now:
            issues.append(f"{field} future/fake: {dt.isoformat()}")
            if fix:
                dt = now
        iso = dt.isoformat()
        display_field = DISPLAY_FIELDS.get(field)
        if fix:
            if meta.get(field) != iso:
                meta[field] = iso
                changed = True
            if display_field and meta.get(display_field) != display_datetime(dt):
                meta[display_field] = display_datetime(dt)
                changed = True
    return changed, issues


def run_known_safe_fixes() -> None:
    if KNOWLEDGE_PATH.exists():
        data = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
        safe = [p["id"] for p in data.get("patterns", []) if p.get("safe_to_autofix")]
        print(f"rule.py: loaded deployment-doctor safe-fix knowledge ({len(safe)} safe patterns)")

    for cmd in SAFE_FIX_COMMANDS:
        print("rule.py:", " ".join(cmd))
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def check_posts(*, fix: bool) -> int:
    errors: list[str] = []
    fixed = 0
    posts = sorted(CONTENT_DIR.glob("*.md"))

    for path in posts:
        text = path.read_text(encoding="utf-8")
        parsed = split_frontmatter(text)
        if not parsed:
            errors.append(f"{path.name}: missing front matter")
            continue
        kind, fm_text, body, _markers = parsed
        try:
            meta = load_meta(kind, fm_text)
        except Exception as exc:
            errors.append(f"{path.name}: front matter parse failed: {exc}")
            continue

        if kind != "toml":
            errors.append(f"{path.name}: front matter is YAML, must be TOML")

        changed_dates, date_issues = normalize_dates(meta, fix=fix)
        errors.extend(f"{path.name}: {issue}" for issue in date_issues if "future/fake" in issue or "invalid" in issue or "missing" in issue)

        if fix and (kind != "toml" or changed_dates):
            path.write_text("+++\n" + dump_toml(meta) + "+++\n" + body, encoding="utf-8")
            fixed += 1

    if fixed:
        print(f"rule.py: fixed {fixed} post file(s)")

    remaining = []
    if fix:
        for path in posts:
            text = path.read_text(encoding="utf-8")
            parsed = split_frontmatter(text)
            if not parsed or parsed[0] != "toml":
                remaining.append(f"{path.name}: still not TOML")
                continue
            try:
                meta = load_meta(parsed[0], parsed[1])
            except Exception as exc:
                remaining.append(f"{path.name}: TOML parse failed after fix: {exc}")
                continue
            _, issues = normalize_dates(meta, fix=False)
            remaining.extend(f"{path.name}: {issue}" for issue in issues if "future/fake" in issue or "invalid" in issue or "missing" in issue)
    else:
        remaining = errors

    if remaining:
        for item in remaining[:80]:
            print(f"FAIL: {item}", file=sys.stderr)
        if len(remaining) > 80:
            print(f"FAIL: ... {len(remaining) - 80} more", file=sys.stderr)
        print(f"rule.py: FAILED ({len(remaining)} issue(s))", file=sys.stderr)
        return 1

    print(f"rule.py: PASS — {len(posts)} posts TOML + no fake future dates")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-deploy source-of-truth rule")
    parser.add_argument("--fix", action="store_true", help="Apply safe fixes before validation")
    args = parser.parse_args()

    if args.fix:
        run_known_safe_fixes()
    return check_posts(fix=args.fix)


if __name__ == "__main__":
    raise SystemExit(main())
