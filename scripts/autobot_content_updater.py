#!/usr/bin/env python3
import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_FILE = REPO_ROOT / "data" / "content-direction.json"
MAX_FILES = 10

def parse_front_matter(text: str) -> tuple[dict | None, str]:
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
        if not m:
            return None, text
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            return None, m.group(2)
        return meta, m.group(2)
    return {}, text

def serialize_front_matter(meta: dict) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, str):
            if any(ch in value for ch in (":", "#", "{", "[", ">", "|", '"', "'", "\n")):
                lines.append(f"{key}: >-")
                lines.append(f"  {value}")
            else:
                lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for v in value:
                lines.append(f"  - {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
        elif value is None:
            continue
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Update freshness metadata for posts older than 365 days")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return

    with open(DATA_FILE) as f:
        direction = json.load(f)

    old_posts = direction.get("freshness", {}).get("old_posts_over_365_days", [])
    if not old_posts:
        print("No posts older than 365 days found")
        return

    slug_map = {}
    for f in CONTENT_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, _ = parse_front_matter(text)
        if meta:
            slug = meta.get("slug", f.stem)
            slug_map[slug] = f

    now = now_vietnam()
    now_iso = now.isoformat()
    refresh_date = format_vietnam_datetime(now)

    changed = 0

    for entry in old_posts:
        if changed >= MAX_FILES:
            break
        slug = entry.get("slug", "")
        if not slug or slug not in slug_map:
            continue
        f_path = slug_map[slug]
        text = f_path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if meta is None:
            continue
        meta["updated"] = now_iso
        meta["refresh_note"] = f"Bài viết đã được cập nhật {refresh_date}"
        if args.write:
            new_text = serialize_front_matter(meta) + "\n" + body
            f_path.write_text(new_text, encoding="utf-8")
        print(f"{f_path.name}: updated + refresh_note added [{refresh_date}]")
        changed += 1

    print(f"\nSummary: {changed} changed (total old posts: {len(old_posts)})")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
