#!/usr/bin/env python3
"""QA checks for blog posts: drafts, dates, slugs, images, internal links."""

import os
import re
import sys
from datetime import datetime, timezone
import yaml

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "posts")
STATIC_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images")
SITE_URL = "https://banhang-chogao.github.io/reviewchanthat"

has_errors = False


def error(msg: str):
    global has_errors
    has_errors = True
    print(f"ERROR: {msg}")


def warn(msg: str):
    print(f"WARN: {msg}")


def parse_front_matter(filepath: str) -> tuple[dict | None, str]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    try:
        return yaml.safe_load(parts[1]), parts[2]
    except yaml.YAMLError:
        return None, content


def extract_internal_links(body: str) -> list[str]:
    pattern = re.compile(r'\[.*?\]\((/[^)]+)\)')
    return pattern.findall(body)


def extract_image_refs(body: str) -> list[str]:
    pattern = re.compile(r'!\[.*?\]\((.*?)\)')
    return pattern.findall(body)


def main():
    if not os.path.isdir(CONTENT_DIR):
        print(f"OK: {CONTENT_DIR} does not exist yet")
        sys.exit(0)

    now = datetime.now(timezone.utc)
    valid_slug = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)

        fm, body = parse_front_matter(fpath)
        if fm is None:
            warn(f"{fname}: cannot parse front matter, skipping")
            continue

        # 1. Check draft: must be false
        if fm.get("draft", False):
            error(f"{fname}: draft should be false for published content")

        # 2. Check date not in future
        date_val = fm.get("date")
        if date_val:
            if isinstance(date_val, datetime):
                if date_val > now:
                    error(f"{fname}: date {date_val} is in the future")
            elif isinstance(date_val, str):
                try:
                    parsed = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                    if parsed > now:
                        error(f"{fname}: date {date_val} is in the future")
                except ValueError:
                    warn(f"{fname}: cannot parse date '{date_val}'")

        # 3. Check slug from filename
        slug_part = fname.replace(".md", "")
        # Remove date prefix if present (YYYY-MM-DD-)
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug_part)
        if not valid_slug.match(slug):
            error(f"{fname}: slug '{slug}' is not valid (use lowercase, hyphens only)")

        # 4. Check image references
        for img_path in extract_image_refs(body):
            if not img_path.startswith(("http://", "https://", "/")):
                error(f"{fname}: image path '{img_path}' should be absolute URL or root-relative")

        # 5. Check internal links (basic)
        for link in extract_internal_links(body):
            if not link.startswith("/"):
                error(f"{fname}: internal link '{link}' should be root-relative")

        # 6. Verify required fields exist
        required = ["title", "date", "description", "categories", "tags", "author"]
        for field in required:
            if field not in fm or fm[field] is None or fm[field] == "" or fm[field] == []:
                error(f"{fname}: missing required field '{field}'")

    if has_errors:
        print("\nQA FAILED: Some issues found.")
        sys.exit(1)
    else:
        print("QA PASSED: All checks completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
