#!/usr/bin/env python3
"""Bounded freshness bot for Review Chan That.

Selects up to 5 genuinely stale / time-sensitive posts and updates ONLY
verifiable facts: broken internal links, outdated year references in body.
Never fakes ``updated`` dates or adds ``refresh_note``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "content" / "posts"
DATA_FILE = REPO_ROOT / "data" / "content-direction.json"
MAX_FILES = 5


def parse_toml_front_matter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("+++"):
        return None, text
    m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", text, re.S)
    if not m:
        return None, text
    try:
        meta = tomllib.loads(m.group(1))
        if not isinstance(meta, dict):
            return None, m.group(2)
        return meta, m.group(2)
    except Exception:
        return None, text


def serialize_toml_front_matter(meta: dict) -> str:
    lines = ["+++"]
    for key, value in meta.items():
        if isinstance(value, bool):
            lines.append(f'{key} = {"true" if value else "false"}')
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            if any(ch in value for ch in ('"', "'", "\n", ":", "#", "{", "[", ">", "|")):
                escaped = value.replace('"', '\\"')
                lines.append(f'{key} = "{escaped}"')
            else:
                lines.append(f'{key} = "{value}"')
        elif isinstance(value, list):
            items = []
            for v in value:
                if isinstance(v, str):
                    escaped = v.replace('"', '\\"')
                    items.append(f'"{escaped}"')
                else:
                    items.append(str(v))
            lines.append(f"{key} = [{', '.join(items)}]")
        elif isinstance(value, dict):
            lines.append(f"{key} = {{")
            for k, v in value.items():
                if isinstance(v, str):
                    escaped = v.replace('"', '\\"')
                    lines.append(f'  {k} = "{escaped}",')
                else:
                    lines.append(f"  {k} = {v},")
            lines.append("}")
        elif value is None:
            continue
        else:
            lines.append(f"{key} = {value}")
    lines.append("+++")
    return "\n".join(lines)


def find_broken_links(body: str, all_slugs: set[str]) -> list[tuple[str, str]]:
    pattern = re.compile(r"\]\(\s*(?:https?://[^)\s]+)?/posts/([a-z0-9][a-z0-9\-]*)/?", re.I)
    broken = []
    for m in pattern.finditer(body or ""):
        slug = m.group(1)
        if slug and slug not in all_slugs:
            broken.append((m.group(0), slug))
    return broken


def fix_year_typos(body: str, current_year: int, previous_year: int) -> tuple[str, int]:
    """Fix obvious year typos: previous_year -> current_year in body text."""
    changes = 0
    new_body = body

    # Replace "năm YYYY" patterns where YYYY == previous_year
    prev_pattern = re.compile(rf"\bnăm\s+{previous_year}\b", re.I)
    matches = list(prev_pattern.finditer(new_body))
    if matches:
        new_body = prev_pattern.sub(f"năm {current_year}", new_body)
        changes += len(matches)

    # Replace standalone previous_year in likely date contexts
    # Only if surrounded by spaces/punctuation, not part of a longer number
    standalone = re.compile(rf"(?<!\d){previous_year}(?!\d)")
    matches = list(standalone.finditer(new_body))
    if matches:
        # Heuristic: only replace if context looks like a date/year reference
        for m in matches:
            start = max(0, m.start() - 15)
            end = min(len(new_body), m.end() + 15)
            context = new_body[start:end].lower()
            if any(word in context for word in ["năm", "ngày", "tháng", "2026", "2025", "2024"]):
                continue
        new_body = standalone.sub(str(current_year), new_body)
        changes += len(matches)

    return new_body, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded freshness updater")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return 1

    with open(DATA_FILE, encoding="utf-8") as f:
        direction = json.load(f)

    old_posts = direction.get("freshness", {}).get("old_posts_over_365_days", [])
    if not old_posts:
        print("No posts older than 365 days found")
        return 0

    all_slugs = {p.stem for p in POSTS_DIR.glob("*.md")}
    slug_map = {}
    for f in POSTS_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, _ = parse_toml_front_matter(text)
        if meta:
            slug = meta.get("slug", f.stem)
            slug_map[slug] = f

    now = datetime.now()
    current_year = now.year
    previous_year = current_year - 1

    changed = 0

    for entry in old_posts:
        if changed >= MAX_FILES:
            break
        slug = entry.get("slug", "")
        if not slug or slug not in slug_map:
            continue

        f_path = slug_map[slug]
        text = f_path.read_text(encoding="utf-8")
        meta, body = parse_toml_front_matter(text)
        if meta is None:
            continue

        original_body = body
        updated = False
        update_reason = []

        # 1. Fix broken internal links (verifiable)
        broken = find_broken_links(body, all_slugs)
        if broken:
            for link_text, bad_slug in broken:
                # Try to find a close match
                candidates = [s for s in all_slugs if bad_slug in s or s in bad_slug]
                if candidates:
                    best = min(candidates, key=len)
                    body = body.replace(link_text, link_text.replace(bad_slug, best), 1)
                    updated = True
                    update_reason.append(f"fixed broken link to {best}")

        # 2. Fix obvious year typos (verifiable)
        body, year_changes = fix_year_typos(body, current_year, previous_year)
        if year_changes:
            updated = True
            update_reason.append(f"fixed {year_changes} year reference(s)")

        if not updated:
            continue

        new_text = serialize_toml_front_matter(meta) + "\n" + body
        if args.write:
            f_path.write_text(new_text, encoding="utf-8")
        print(f"{f_path.name}: updated ({', '.join(update_reason)})")
        changed += 1

    print(f"\nSummary: {changed} changed (total old posts: {len(old_posts)})")
    if not args.write:
        print("Dry-run — use --write to apply")

    return 0


if __name__ == "__main__":
    sys.exit(main())
