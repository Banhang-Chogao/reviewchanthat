#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_FILE = REPO_ROOT / "data" / "content-direction.json"
MAX_FILES = 5
TARGET_TYPES = {"Missing", "Suggestion"}

def main():
    parser = argparse.ArgumentParser(description="Create draft posts for content gaps")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        return

    with open(DATA_FILE) as f:
        direction = json.load(f)

    gaps = direction.get("content_gaps", [])
    relevant = [g for g in gaps if g.get("type") in TARGET_TYPES]

    if not relevant:
        print("No Missing/Suggestion content gaps found")
        return

    now = now_vietnam()
    now_iso = now.isoformat()

    created = 0
    skipped_exists = 0
    skipped_no_slug = 0

    for gap in relevant:
        if created >= MAX_FILES:
            break
        name = gap.get("name", "").strip()
        if not name:
            skipped_no_slug += 1
            continue
        slug = name.lower().replace(" ", "-").replace("_", "-")
        draft_name = f"draft-{slug}.md"
        draft_path = CONTENT_DIR / draft_name
        if draft_path.exists():
            print(f"{draft_name}: already exists")
            skipped_exists += 1
            continue
        title = gap.get("detail", name).split(":")[0].strip()
        cats = []
        tags = []
        if "starbucks" in name.lower():
            cats.append("review")
            tags.append("starbucks")
        elif "tai-chinh" in name.lower() or "finance" in name.lower():
            cats.append("tai-chinh")
        else:
            cats.append("review")
        fm = [
            "---",
            f'title: "{title}"',
            f"slug: {slug}",
            "draft: true",
            f"date: {now_iso}",
            "categories:",
        ]
        for c in cats:
            fm.append(f"  - {c}")
        if tags:
            fm.append("tags:")
            for t in tags:
                fm.append(f"  - {t}")
        fm.append("---")
        fm.append("")
        fm.append("Bài viết đang được phát triển")
        fm.append("")
        content = "\n".join(fm)
        if args.write:
            draft_path.write_text(content, encoding="utf-8")
        print(f"{draft_name}: created draft for gap '{name}'")
        created += 1

    print(f"\nSummary: {created} created, {skipped_exists} already exist, {skipped_no_slug} no slug")
    if not args.write:
        print("Dry-run — use --write to apply")

if __name__ == "__main__":
    main()
