#!/usr/bin/env python3
"""
Normalize ai_summary.items in Hugo post front matter.

Ensures every summary bullet is a plain string (never dict/map/object).
Use --check to validate, --fix to rewrite affected posts.
"""

import argparse
import os
import re
import sys

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

CONTENT_DIR = "content/posts"
PUBLIC_DIR = "public"
SUMMARY_KEY = "ai_summary"
BULLET_PREFIX_RE = re.compile(r"^[-•*]\s+")
MULTISPACE_RE = re.compile(r"\s+")


def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def sanitize_string(text):
    text = clean_text(text)
    text = BULLET_PREFIX_RE.sub("", text)
    text = MULTISPACE_RE.sub(" ", text)
    return text.strip()


def dict_to_string(item):
    if not item:
        return ""
    if len(item) == 1:
        key, value = next(iter(item.items()))
        key = clean_text(str(key))
        value = clean_text(str(value))
        if key and value:
            return f"{key}: {value}"
        return key or value
    parts = []
    for key, value in item.items():
        key = clean_text(str(key))
        value = clean_text(str(value))
        if key and value:
            parts.append(f"{key}: {value}")
        else:
            parts.append(key or value)
    return "; ".join(parts)


def parse_map_string(text):
    inner = text[4:-1].strip()
    if not inner:
        return None
    if ": " in inner:
        key, value = inner.split(": ", 1)
        key = clean_text(key)
        value = clean_text(value)
        if key and value:
            return f"{key}: {value}"
    if ":" in inner:
        key, value = inner.rsplit(":", 1)
        key = clean_text(key)
        value = clean_text(value)
        if key and value:
            return f"{key}: {value}"
    return None


def item_to_string(item):
    if item is None:
        return ""
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        text = dict_to_string(item)
    elif isinstance(item, (list, tuple)):
        text = " ".join(part for part in (item_to_string(x) for x in item) if part)
    else:
        text = str(item)

    text = clean_text(text)
    if text.startswith("map[") and text.endswith("]"):
        parsed = parse_map_string(text)
        if parsed:
            text = parsed
    return sanitize_string(text)


def normalize_items(items):
    normalized = []
    failures = []
    for index, item in enumerate(items or []):
        if isinstance(item, dict):
            text = item_to_string(item)
            if text:
                normalized.append(text)
            else:
                failures.append((index, item, "empty dict"))
            continue
        if isinstance(item, (list, tuple)) and not isinstance(item, str):
            text = item_to_string(item)
            if text:
                normalized.append(text)
            else:
                failures.append((index, item, "empty sequence"))
            continue
        if not isinstance(item, str):
            failures.append((index, item, f"unsupported type {type(item).__name__}"))
            continue
        text = item_to_string(item)
        if not text:
            failures.append((index, item, "empty string"))
            continue
        if text.startswith("map[") and text.endswith("]") and parse_map_string(text) is None:
            failures.append((index, item, "unparseable map[ string"))
            continue
        normalized.append(text)
    return normalized, failures


def scan_posts():
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    if not os.path.isdir(posts_dir):
        print(f"ERROR: {CONTENT_DIR} not found")
        sys.exit(1)

    results = []
    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            post = frontmatter.load(fpath)
        except Exception as exc:
            results.append(
                {
                    "path": fpath,
                    "slug": fname,
                    "error": str(exc),
                    "changed": False,
                    "issues": [],
                    "failures": [("parse", exc, "parse error")],
                }
            )
            continue

        ai_summary = post.metadata.get(SUMMARY_KEY)
        if not ai_summary or not ai_summary.get("items"):
            continue

        original_items = ai_summary.get("items", [])
        normalized_items, failures = normalize_items(original_items)
        changed = normalized_items != original_items or any(
            not isinstance(item, str) for item in original_items
        )
        issues = []
        for index, item in enumerate(original_items):
            if not isinstance(item, str):
                issues.append((index, item, f"was {type(item).__name__}"))
            elif "map[" in item:
                issues.append((index, item, "contains map["))

        results.append(
            {
                "path": fpath,
                "slug": post.metadata.get("slug", fname.replace(".md", "")),
                "post": post,
                "ai_summary": ai_summary,
                "original_items": original_items,
                "normalized_items": normalized_items,
                "changed": changed,
                "issues": issues,
                "failures": failures,
            }
        )
    return results


def scan_public_ai_summary_map_literals(public_dir):
    hits = []
    if not os.path.isdir(public_dir):
        return hits
    pattern = re.compile(r'<ul[^>]*\bai-summary__list\b[^>]*>.*?</ul>', re.DOTALL)
    for dirpath, _, filenames in os.walk(public_dir):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            for match in pattern.finditer(content):
                if "map[" in match.group(0):
                    hits.append((fpath, 0, match.group(0)[:120]))
                    break
    return hits


def write_post(result):
    post = result["post"]
    ai_summary = dict(result["ai_summary"])
    ai_summary["items"] = result["normalized_items"]
    post.metadata[SUMMARY_KEY] = ai_summary
    with open(result["path"], "w", encoding="utf-8") as handle:
        frontmatter.dump(post, handle)


def main():
    parser = argparse.ArgumentParser(description="Normalize ai_summary.items in post front matter")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Validate only; exit 1 on issues")
    group.add_argument("--fix", action="store_true", help="Rewrite posts with invalid summary items")
    args = parser.parse_args()

    if not args.check and not args.fix:
        args.check = True

    results = scan_posts()
    fixed = []
    blocked = []
    unchanged = []

    for result in results:
        if result.get("error"):
            blocked.append(result)
            continue
        if result["failures"]:
            blocked.append(result)
            continue
        if result["changed"]:
            if args.fix:
                write_post(result)
                fixed.append(result)
            else:
                blocked.append(result)
        else:
            unchanged.append(result)

    map_hits = scan_public_ai_summary_map_literals(os.path.join(os.getcwd(), PUBLIC_DIR))

    print("=== AI Summary Normalization ===")
    print(f"  Posts scanned with ai_summary: {len(results)}")
    print(f"  Posts unchanged: {len(unchanged)}")
    print(f"  Posts needing fix: {len(fixed) if args.fix else len([r for r in results if r.get('changed') and not r.get('failures')])}")
    print(f"  Posts blocked/unfixable: {len(blocked)}")

    if fixed:
        print("\nFixed posts:")
        for result in fixed:
            print(f"  - {result['slug']}")
            for index, item, reason in result["issues"]:
                preview = repr(item)[:120]
                print(f"      item[{index}] ({reason}): {preview}")

    if blocked and not args.fix:
        print("\nIssues found:")
        for result in blocked:
            print(f"  - {result['slug']}")
            if result.get("error"):
                print(f"      parse error: {result['error']}")
            for index, item, reason in result.get("issues", []):
                preview = repr(item)[:120]
                print(f"      item[{index}] ({reason}): {preview}")
            for index, item, reason in result.get("failures", []):
                preview = repr(item)[:120]
                print(f"      item[{index}] ({reason}): {preview}")

    if map_hits:
        print(f"\nmap[ literals found: {len(map_hits)}")
        for fpath, line_no, line in map_hits[:20]:
            rel = os.path.relpath(fpath, os.getcwd())
            print(f"  - {rel}:{line_no}: {line[:120]}")

    has_errors = bool(blocked) or bool(map_hits)
    if has_errors:
        print("\nFAILED: ai_summary normalization checks did not pass.")
        sys.exit(1)

    print("\nPASSED: all ai_summary items are clean strings.")
    sys.exit(0)


if __name__ == "__main__":
    main()