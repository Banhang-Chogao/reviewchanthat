#!/usr/bin/env python3
"""
Enhance internal links across all posts using the link graph.
Called by :enhan zsh shortcut.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "internal-links.json"
POSTS = ROOT / "content" / "posts"

def parse_toml_fm(text: str):
    """Parse TOML front matter (+++...+++)."""
    m = re.match(r'^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+\r?\n?)(.*)$', text, re.DOTALL)
    if not m:
        return None, None, None, text
    return m.group(1), m.group(2), m.group(3), m.group(4)


 
def load_graph():
    if not DATA.exists():
        print("  data/internal-links.json not found — run build_internal_link_graph.py first")
        sys.exit(1)
    with open(DATA) as f:
        return json.load(f)

def insert_internal_links():
    graph = load_graph()
    links = graph.get("links", {})
    inbound = graph.get("inbound_counts", {})
    orphans = {s for s, c in inbound.items() if c == 0}
    print(f"  Orphan posts (0 inbound): {len(orphans)}")

    added_total = 0
    orphan_linked = set()

    for slug, candidates in links.items():
        fpath = POSTS / f"{slug}.md"
        if not fpath.exists():
            continue

        content = fpath.read_text(encoding="utf-8")
        open_fm, fm, close_fm, body = parse_toml_fm(content)
        if fm is None:
            continue

        existing_refs = set(re.findall(r'ref\s*=\s*"([^"]+)"', fm))
        max_links = 8

        to_add = []
        for c in candidates:
            target = c["target"]
            title = c["title"]
            ref_val = f"posts/{target}.md"
            if ref_val in existing_refs:
                continue
            if len(existing_refs) + len(to_add) >= max_links:
                break
            to_add.append((ref_val, title))
            if target in orphans:
                orphan_linked.add(target)

        if not to_add:
            continue

        # 2. Append [[internal_links]] to front matter only
        # Body links are the writer's responsibility (embedded naturally in text)
        for ref_val, title in to_add:
            safe_title = title.replace('"', '\\"')
            fm_block += f'\n[[internal_links]]\nref = "{ref_val}"\ntitle = "{safe_title}"\n'

        new_content = open_fm + fm + fm_block + close_fm + body
        fpath.write_text(new_content, encoding="utf-8")
        added_total += len(to_add)
        print(f"  + {slug}: added {len(to_add)} links (FM only)")

    print(f"\n  Total links added: {added_total}")
    print(f"  Orphans now linked: {len(orphan_linked)} / {len(orphans)}")

def report():
    graph = load_graph()
    links = graph.get("links", {})
    inbound = graph.get("inbound_counts", {})
    indexable = graph.get("indexable_slugs", [])

    total = len(indexable)
    with_links = sum(1 for s in indexable if len(links.get(s, [])) > 0)
    orphans = [s for s in indexable if inbound.get(s, 0) == 0]
    total_links = sum(len(v) for v in links.values())

    print(f"  • Indexable posts: {total}")
    print(f"  • Posts with outgoing links: {with_links}")
    print(f"  • Total internal links: {total_links}")
    print(f"  • Avg links per post: {total_links / max(total, 1):.1f}")
    print(f"  • Orphan posts (no inbound): {len(orphans)}")
    if orphans:
        print(f"  • Orphan list:")
        for s in orphans[:10]:
            print(f"      - {s}")
        if len(orphans) > 10:
            print(f"      - ... and {len(orphans) - 10} more")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "insert":
        insert_internal_links()
    elif mode == "report":
        report()
    else:
        insert_internal_links()
        report()
