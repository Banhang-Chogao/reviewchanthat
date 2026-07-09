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
    parser = argparse.ArgumentParser(description="Add links to orphan posts from relevant indexable posts")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return

    with open(DATA_FILE) as f:
        graph = json.load(f)

    links = graph.get("links", {})
    inbound = graph.get("inbound_counts", {})
    indexable = set(graph.get("indexable_slugs", []))

    orphan_slugs = [s for s in indexable if inbound.get(s, 0) == 0]

    if not orphan_slugs:
        print("No orphan posts found")
        return

    slug_to_file = {}
    for f in CONTENT_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, _ = parse_front_matter(text)
        if meta:
            slug = meta.get("slug", f.stem)
            slug_to_file[slug] = (f, meta.get("title", ""))

    changed = 0
    skipped_no_internal_links_fm = 0
    skipped_no_suitable = 0

    for orphan_slug in orphan_slugs:
        if changed >= MAX_FILES:
            break
        if orphan_slug not in slug_to_file:
            continue
        f_path, _ = slug_to_file[orphan_slug]
        text = f_path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if meta is None:
            continue
        if "internal_links" not in meta:
            skipped_no_internal_links_fm += 1
            continue
        best_source = None
        best_score = -1
        for source_slug, targets in links.items():
            if source_slug == orphan_slug:
                continue
            if source_slug in inbound and inbound[source_slug] == 0:
                continue
            for t in targets:
                if t["target"] == orphan_slug:
                    if t["score"] > best_score:
                        best_score = t["score"]
                        best_source = source_slug
                        best_title = t.get("title", orphan_slug.replace("-", " ").title())
                    break
        if not best_source:
            skipped_no_suitable += 1
            continue
        if best_source not in slug_to_file:
            skipped_no_suitable += 1
            continue
        src_path, src_title = slug_to_file[best_source]
        src_text = src_path.read_text(encoding="utf-8")
        src_meta, src_body = parse_front_matter(src_text)
        if src_meta is None:
            skipped_no_suitable += 1
            continue
        existing_links = src_meta.get("internal_links", [])
        if isinstance(existing_links, list):
            existing_slugs = set()
            for link in existing_links:
                if isinstance(link, dict):
                    existing_slugs.update(link.values())
                elif isinstance(link, str):
                    existing_slugs.add(link.strip().rstrip("/").split("/")[-1])
            if orphan_slug in existing_slugs:
                skipped_no_suitable += 1
                continue
        new_link = {orphan_slug: f"/posts/{orphan_slug}/"}
        src_meta.setdefault("internal_links", []).append(new_link)
        if args.write:
            new_text = serialize_front_matter(src_meta) + "\n" + src_body
            src_path.write_text(new_text, encoding="utf-8")
        print(f"{f_path.name}: linked from {best_source}")
        changed += 1

    print(f"\nSummary: {changed} changed, {skipped_no_internal_links_fm} no internal_links fm, {skipped_no_suitable} no suitable source")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
