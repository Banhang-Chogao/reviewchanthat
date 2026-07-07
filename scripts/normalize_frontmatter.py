#!/usr/bin/env python3
"""Scan content/posts and report missing required front matter fields."""

import os
import sys
import yaml

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "posts")
REQUIRED_FIELDS = ["title", "date", "description", "categories", "tags", "author"]
TEMPLATE_CATEGORIES = ["review", "cong-nghe", "doi-song", "tai-chinh"]


def parse_front_matter(filepath: str) -> dict | None:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def main():
    if not os.path.isdir(CONTENT_DIR):
        print(f"OK: {CONTENT_DIR} does not exist yet")
        sys.exit(0)

    has_errors = False
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        fm = parse_front_matter(fpath)
        if fm is None:
            print(f"ERROR: {fname} - cannot parse front matter")
            has_errors = True
            continue

        for field in REQUIRED_FIELDS:
            if field not in fm or fm[field] is None or fm[field] == "" or fm[field] == []:
                print(f"ERROR: {fname} - missing required field: {field}")
                has_errors = True

        if "draft" in fm and fm["draft"]:
            print(f"WARN: {fname} - is draft")

    if has_errors:
        print("\nSome posts have front matter issues.")
        sys.exit(1)
    else:
        print("All posts have valid front matter.")
        sys.exit(0)


if __name__ == "__main__":
    main()
