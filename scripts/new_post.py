#!/usr/bin/env python3
"""Create a new Hugo blog post with proper front matter and slug."""

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


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a", text)
    text = re.sub(r"[èéẹẻẽêềếệểễ]", "e", text)
    text = re.sub(r"[ìíịỉĩ]", "i", text)
    text = re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o", text)
    text = re.sub(r"[ùúụủũưừứựửữ]", "u", text)
    text = re.sub(r"[ỳýỵỷỹ]", "y", text)
    text = re.sub(r"[đ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def main():
    parser = argparse.ArgumentParser(description="Create a new Hugo blog post")
    parser.add_argument("title", help="Post title")
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
    filename = f"{date[:10]}-{slug}.md"
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
draft: false
---
"""

    os.makedirs(CONTENT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter)

    print(f"Created: {filepath}")
    print(f"Slug: {slug}")


if __name__ == "__main__":
    main()
