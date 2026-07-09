#!/usr/bin/env python3
import argparse
import re
import sys
import warnings
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
MAX_FILES = 20

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
                lines.append(f"  - {v if isinstance(v, str) else v}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif value is None:
            continue
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)

def truncate_at_word_boundary(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.strip().rstrip(",;:")

def main():
    parser = argparse.ArgumentParser(description="Add seo_title to posts with title > 60 chars")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    posts = sorted(CONTENT_DIR.glob("*.md"))
    changed = 0
    skipped_existing = 0
    skipped_short = 0

    for f in posts:
        if changed >= MAX_FILES:
            break
        text = f.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if meta is None:
            continue
        title = meta.get("title", "")
        if not title or len(title) <= 60:
            skipped_short += 1
            continue
        if meta.get("seo_title"):
            print(f"{f.name}: already has seo_title")
            skipped_existing += 1
            continue
        seo = truncate_at_word_boundary(title, 58)
        if len(seo) < 30:
            seo = truncate_at_word_boundary(title, 55)
        if not seo or len(seo) >= len(title):
            continue
        if args.write:
            meta["seo_title"] = seo
            new_text = serialize_front_matter(meta) + "\n" + body
            f.write_text(new_text, encoding="utf-8")
        print(f"{f.name}: added seo_title ({len(seo)} chars) — {seo}")
        changed += 1

    print(f"\nSummary: {changed} changed, {skipped_existing} had seo_title, {skipped_short} titles <= 60")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
