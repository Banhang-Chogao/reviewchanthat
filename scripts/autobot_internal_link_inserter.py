#!/usr/bin/env python3
import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_FILE = REPO_ROOT / "data" / "internal-links.json"
MAX_FILES = 15
MAX_CANDIDATES = 5

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

def count_existing_internal_links(body: str, self_slug: str) -> list[str]:
    pattern = re.compile(r"\]\(\s*(?:https?://[^)\s]+)?/posts/([a-z0-9][a-z0-9\-]*)/?", re.I)
    found = []
    for m in pattern.finditer(body or ""):
        slug = m.group(1)
        if slug and slug != self_slug:
            found.append(slug)
    seen = set()
    out = []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def find_insertion_point(body: str) -> int | None:
    paragraphs = re.split(r"(\n\n|\r\n\r\n)", body)
    if len(paragraphs) < 3:
        return None
    insert_idx = len(body)
    for i in range(len(paragraphs) - 2, 0, -1):
        candidate = "".join(paragraphs[:i]).strip()
        if len(candidate) >= 100:
            insert_idx = len("".join(paragraphs[:i]))
            break
    return insert_idx if insert_idx < len(body) else None

def main():
    parser = argparse.ArgumentParser(description="Insert internal links from internal-links.json into posts")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return

    with open(DATA_FILE) as f:
        graph = json.load(f)

    links = graph.get("links", {})
    indexable = set(graph.get("indexable_slugs", []))

    posts = sorted(CONTENT_DIR.glob("*.md"))
    changed = 0
    skipped_already_linked = 0
    skipped_no_candidates = 0
    skipped_no_insertion = 0

    for f in posts:
        if changed >= MAX_FILES:
            break
        text = f.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if meta is None:
            continue
        slug = meta.get("slug", f.stem)
        if slug not in links or not links[slug]:
            skipped_no_candidates += 1
            continue
        existing = count_existing_internal_links(body, slug)
        if len(existing) >= 3:
            skipped_already_linked += 1
            continue
        candidates = [c for c in links[slug][:MAX_CANDIDATES] if c["target"] != slug]
        if not candidates:
            skipped_no_candidates += 1
            continue
        to_insert = []
        for c in candidates:
            if c["target"] in existing:
                continue
            pattern_link = re.compile(
                r"\]\(\s*(?:https?://[^)\s]+)?/posts/" + re.escape(c["target"]) + r"/?",
                re.I,
            )
            if pattern_link.search(body):
                existing.append(c["target"])
                continue
            to_insert.append(c)
            if len(to_insert) >= 2:
                break
        if not to_insert:
            skipped_already_linked += 1
            continue
        insert_point = find_insertion_point(body)
        if insert_point is None:
            skipped_no_insertion += 1
            continue
        link_texts = []
        for c in to_insert:
            link_texts.append(f'Xem thêm: [{c["title"]}](/posts/{c["target"]}/)')
        insertion = "\n\n" + "\n".join(link_texts) + "\n"
        new_body = body[:insert_point] + insertion + body[insert_point:]
        if args.write:
            new_text = serialize_front_matter(meta) + "\n" + new_body
            f.write_text(new_text, encoding="utf-8")
        print(f"{f.name}: inserted {len(to_insert)} link(s) — {', '.join(c['target'] for c in to_insert)}")
        changed += 1

    print(f"\nSummary: {changed} changed, {skipped_already_linked} already have >=3 links, {skipped_no_candidates} no candidates, {skipped_no_insertion} no insertion point")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
