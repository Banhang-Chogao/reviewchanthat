#!/usr/bin/env python3
"""QA checks for deployment-snapshot page and data."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SECRET_PATTERNS = (
    r"BEGIN PRIVATE KEY",
    r"GITHUB_TOKEN",
    r"GH_TOKEN",
    r"GOOGLE_APPLICATION_CREDENTIALS",
    r"PEXELS_API_KEY",
    r"PIXABAY_API_KEY",
    r"UNSPLASH_ACCESS_KEY",
)


def fail(msg: str) -> None:
    print(f"QA DEPLOYMENT-SNAPSHOT FAILED: {msg}", file=sys.stderr)


def check_data_file(path: str) -> bool:
    """Check data/deployment-snapshot.json integrity."""
    if not os.path.isfile(path):
        fail(f"missing file: {path}")
        return False

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"invalid JSON: {e}")
        return False

    errors = []

    if "generated_at" not in data:
        errors.append("missing generated_at")
    if "summary" not in data:
        errors.append("missing summary")
    if "items" not in data:
        errors.append("missing items")

    items = data.get("items", [])
    if not isinstance(items, list):
        errors.append("items is not a list")
        return False

    if len(items) > 30:
        errors.append(f"too many items: {len(items)} > 30")

    with open(path) as f:
        content = f.read()
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f"secret pattern detected: {pattern}")

    if errors:
        for err in errors:
            fail(err)
        return False

    print(f"QA DATA PASSED: {path} ({len(items)} items)")
    return True


def check_public_page(public_dir: str) -> bool:
    """Check public/deployment-snapshot/index.html."""
    index_path = os.path.join(public_dir, "deployment-snapshot", "index.html")

    if not os.path.isfile(index_path):
        fail(f"missing page: {index_path}")
        return False

    with open(index_path) as f:
        content = f.read()

    errors = []

    if "noindex" not in content:
        errors.append("missing noindex meta tag")

    if "Deployment Snapshot" not in content:
        errors.append("missing page title")

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"secret pattern in HTML: {pattern}")

    if re.search(r'href="/deployment-snapshot', content):
        errors.append("hardcoded /deployment-snapshot link found")

    if errors:
        for err in errors:
            fail(err)
        return False

    print(f"QA PAGE PASSED: {index_path}")
    return True


def check_sitemap(sitemap_path: str) -> bool:
    """Ensure /deployment-snapshot/ not in sitemap."""
    if not os.path.isfile(sitemap_path):
        print(f"Note: {sitemap_path} not found, skipping sitemap check")
        return True

    with open(sitemap_path) as f:
        content = f.read()

    if "/deployment-snapshot/" in content:
        fail("deployment-snapshot found in sitemap (should not be indexed)")
        return False

    print("QA SITEMAP PASSED: deployment-snapshot excluded")
    return True


def check_footer_link(public_dir: str) -> bool:
    """Verify footer has deployment-snapshot link."""
    index_path = os.path.join(public_dir, "index.html")

    if not os.path.isfile(index_path):
        print(f"Note: {index_path} not found, skipping footer check")
        return True

    with open(index_path) as f:
        content = f.read()

    if "deployment-snapshot" not in content.lower():
        print("Note: deployment-snapshot link not yet in footer (expected on first load)")
        return True

    if 'href="/deployment-snapshot/' in content:
        fail("hardcoded /deployment-snapshot link in footer")
        return False

    print("QA FOOTER PASSED: deployment-snapshot link uses relURL")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="QA deployment-snapshot")
    parser.add_argument("--public", action="store_true", help="Check public/ build output")

    args = parser.parse_args()

    passed = 0
    failed = 0

    if check_data_file("data/deployment-snapshot.json"):
        passed += 1
    else:
        failed += 1

    if check_sitemap("public/sitemap.xml"):
        passed += 1
    else:
        failed += 1

    if args.public:
        if check_public_page("public"):
            passed += 1
        else:
            failed += 1

        if check_footer_link("public"):
            passed += 1
        else:
            failed += 1

    if failed > 0:
        print(f"\nQA DEPLOYMENT-SNAPSHOT FAILED: {failed} check(s)", file=sys.stderr)
        return 1

    print(f"\nQA DEPLOYMENT-SNAPSHOT PASSED: {passed} check(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
