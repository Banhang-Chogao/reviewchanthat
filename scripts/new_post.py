#!/usr/bin/env python3
"""Create a new Hugo blog post — title is single source of truth for slug/url/file."""

import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slug_utils import slugify_vi

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "posts")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_category_slugs():
    """Load valid category slugs from data/categories.json."""
    path = os.path.join(DATA_DIR, "categories.json")
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()
    slugs = set()
    for item in data.get("items", []):
        slug = item.get("slug", "").strip()
        if slug:
            slugs.add(slug)
    aliases = data.get("aliases", {})
    for alias, canonical in aliases.items():
        if canonical:
            slugs.add(alias.lower())
    return slugs


def main():
    parser = argparse.ArgumentParser(description="Create a new Hugo blog post (title = slug)")
    parser.add_argument("title", help="Post title — single source of truth for slug/url")
    parser.add_argument("--author", default="Admin", help="Author name")
    parser.add_argument("--category", action="append", default=[], help="Category (can be repeated)")
    parser.add_argument("--tag", action="append", default=[], help="Tag (can be repeated)")
    parser.add_argument("--description", default="", help="Post description/excerpt")
    parser.add_argument("--image", default="", help="Thumbnail image URL")
    parser.add_argument("--avatar", default="", help="Author avatar URL")
    args = parser.parse_args()

    if not args.category:
        args.category = ["review"]

    valid_slugs = load_category_slugs()
    for cat in args.category:
        if valid_slugs and cat.lower() not in valid_slugs:
            print(
                f"ERROR: Category '{cat}' not found in data/categories.json. "
                f"Valid categories: {sorted(valid_slugs)}",
                file=sys.stderr,
            )
            sys.exit(1)

    slug = slugify(args.title)
    canonical_slug = slugify_vi(args.title)
    date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
    filename = f"{slug}.md"
    filepath = os.path.join(CONTENT_DIR, filename)

    description = args.description or args.title

    categories = "[" + ", ".join(f'"{c}"' for c in args.category) + "]"
    tags = "[" + ", ".join(f'"{t}"' for t in args.tag) + "]" if args.tag else "[]"

    front_matter = f"""---
title: "{args.title}"
date: {date}
description: "{description}"
slug: {canonical_slug}
categories: {categories}
tags: {tags}
author: "{args.author}"
avatar: "{args.avatar}"
image: "{args.image}"
slug: "{slug}"
draft: false
---
"""

    os.makedirs(CONTENT_DIR, exist_ok=True)
    if os.path.exists(filepath):
        print(f"ERROR: {filepath} already exists", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter)

    print(f"Created: {filepath}")
    print(f"Title: {args.title}")
    print(f"Slug: {slug}")
    print(f"URL: {url_from_slug(slug)}")


if __name__ == "__main__":
    main()
