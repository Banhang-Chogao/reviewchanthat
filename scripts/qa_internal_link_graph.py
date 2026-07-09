#!/usr/bin/env python3
import json, os, sys

DATA_FILE = "data/internal-links.json"
POSTS_DIR = "content/posts"
GENERIC_ANCHORS = {"xem thêm", "tại đây", "click here", "bài viết này", "tìm hiểu thêm"}

def main():
    errors = 0

    if not os.path.exists(DATA_FILE):
        print("FAIL: internal-links.json not found")
        return 1

    with open(DATA_FILE) as f:
        data = json.load(f)

    links = data.get("links", {})
    inbound = data.get("inbound_counts", {})
    indexable = set(data.get("indexable_slugs", []))
    orphan = [s for s in indexable if inbound.get(s, 0) == 0]

    print(f"# Internal Link Graph QA\n")
    print(f"Links entries: {len(links)}")
    print(f"Indexable slugs: {len(indexable)}")
    print(f"Orphan posts: {len(orphan)}")
    print(f"Total links: {sum(len(v) for v in links.values())}\n")

    total_links = 0
    max_per_post = 0
    self_links = 0
    missing_targets = set()
    long_anchors = 0
    short_anchors = 0
    generic_anchors = 0
    noindex_targets = 0

    for source, targets in links.items():
        max_per_post = max(max_per_post, len(targets))
        total_links += len(targets)
        for t in targets:
            if t["target"] == source:
                self_links += 1
            if t["target"] not in indexable:
                missing_targets.add(t["target"])

    issues = []
    if orphan:
        issues.append(f"Orphan posts: {len(orphan)} (target: <= 5)")
        for s in orphan[:10]:
            issues.append(f"  - {s}")
    if total_links == 0:
        issues.append("No links generated")
    if max_per_post > 10:
        issues.append(f"Max links per post: {max_per_post} (target: <= 10)")
    if self_links:
        issues.append(f"Self-links: {self_links}")
    if missing_targets:
        issues.append(f"Missing targets (slug not indexable): {len(missing_targets)}")

    if issues:
        print("## Issues Found\n")
        for i in issues:
            print(f"- {i}")
            errors += 1

    print(f"\n## Stats\n")
    print(f"Total links: {total_links}")
    print(f"Max per post: {max_per_post}")
    print(f"Self-links: {self_links}")
    print(f"Missing targets: {len(missing_targets)}")

    if errors == 0:
        print("\nPASS: Internal link graph QA passed")
    else:
        print(f"\nFAIL: {errors} issue(s) found")

    return 1 if errors > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
