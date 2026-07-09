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
DESC_MIN = 50
DESC_MAX = 160

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
            has_colon = ':' in value
            has_newline = '\n' in value
            has_quote = '"' in value or "'" in value

            if has_newline or (has_colon and len(value) > 50):
                # Use folded literal for long text or multiline
                lines.append(f"{key}: >-")
                lines.append(f"  {value}")
            elif has_colon:
                # Quote values with colons
                if '"' not in value:
                    lines.append(f"{key}: \"{value}\"")
                elif "'" not in value:
                    lines.append(f"{key}: '{value}'")
                else:
                    lines.append(f"{key}: >-")
                    lines.append(f"  {value}")
            elif any(ch in value for ch in ("#", "{", "[", ">", "|")):
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

def make_description(title: str) -> str:
    desc = title.strip().rstrip(".?!")
    if len(desc) > DESC_MAX:
        desc = desc[:DESC_MAX]
        last_space = desc.rfind(" ")
        if last_space > 0:
            desc = desc[:last_space]
    return desc.strip().rstrip(",;:")

def main():
    parser = argparse.ArgumentParser(description="Fix description length on posts")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    posts = sorted(CONTENT_DIR.glob("*.md"))
    changed = 0
    fixed_short = 0
    fixed_long = 0
    added = 0

    for f in posts:
        if changed >= MAX_FILES:
            break
        text = f.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if meta is None:
            continue
        title = meta.get("title", "")
        desc = meta.get("description", "")
        if not title:
            continue
        if not desc:
            new_desc = make_description(title)
            if args.write:
                meta["description"] = new_desc
                new_text = serialize_front_matter(meta) + "\n" + body
                f.write_text(new_text, encoding="utf-8")
            print(f"{f.name}: added description ({len(new_desc)} chars)")
            added += 1
            changed += 1
            continue
        desc_len = len(desc)
        if desc_len < DESC_MIN:
            new_desc = make_description(title)
            if args.write:
                meta["description"] = new_desc
                new_text = serialize_front_matter(meta) + "\n" + body
                f.write_text(new_text, encoding="utf-8")
            print(f"{f.name}: fixed short description ({desc_len} -> {len(new_desc)} chars)")
            fixed_short += 1
            changed += 1
        elif desc_len > DESC_MAX:
            new_desc = desc[:DESC_MAX]
            last_space = new_desc.rfind(" ")
            if last_space > 0:
                new_desc = new_desc[:last_space]
            new_desc = new_desc.strip().rstrip(",;:")
            if args.write:
                meta["description"] = new_desc
                new_text = serialize_front_matter(meta) + "\n" + body
                f.write_text(new_text, encoding="utf-8")
            print(f"{f.name}: fixed long description ({desc_len} -> {len(new_desc)} chars)")
            fixed_long += 1
            changed += 1

    print(f"\nSummary: {changed} changed (added={added}, short={fixed_short}, long={fixed_long})")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
