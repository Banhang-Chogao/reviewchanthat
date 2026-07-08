#!/usr/bin/env python3
"""Add root-level URL aliases so legacy /:slug/ links redirect to /posts/:slug/."""

from __future__ import annotations

import csv
import glob
import io
import subprocess
import sys
from urllib.parse import unquote, urlparse

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

def load_base_path() -> str:
    """Read baseURL from hugo.toml and extract the path component."""
    import tomllib
    with open("hugo.toml", "rb") as f:
        cfg = tomllib.load(f)
    base_url = cfg.get("baseURL", "https://banhang-chogao.github.io/reviewchanthat/")
    parsed = urlparse(base_url)
    return parsed.path.rstrip("/") or "/reviewchanthat"


SITE_BASE_PATH = load_base_path()


def legacy_alias(permalink: str) -> str:
    path = unquote(urlparse(permalink).path)
    if path.startswith(SITE_BASE_PATH):
        path = path[len(SITE_BASE_PATH) :]
    if path.startswith("/posts/"):
        path = path[len("/posts/") :]
    slug = path.strip("/")
    return f"/{slug}/" if slug else "/"


def main() -> int:
    output = subprocess.check_output(["hugo", "list", "all"], text=True, stderr=subprocess.DEVNULL)
    reader = csv.DictReader(io.StringIO(output))
    permalink_by_path = {
        row["path"]: row["permalink"]
        for row in reader
        if row["path"].startswith("content/posts/")
    }

    updated = 0
    for filepath in sorted(glob.glob("content/posts/**/*.md", recursive=True)):
        permalink = permalink_by_path.get(filepath)
        if not permalink:
            continue

        alias = legacy_alias(permalink)
        with open(filepath, encoding="utf-8") as handle:
            post = frontmatter.load(handle)

        aliases = [alias]
        post.metadata["aliases"] = aliases
        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write(frontmatter.dumps(post))
            handle.write("\n")
        updated += 1
        print(f"  alias {alias} -> {filepath}")

    print(f"Updated {updated} posts with legacy URL aliases")
    return 0


if __name__ == "__main__":
    sys.exit(main())