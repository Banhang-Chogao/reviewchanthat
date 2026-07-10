#!/usr/bin/env python3
"""QA checks for Income Insights — privacy, structure, no leak."""

import json
import os
import re
import subprocess
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # pip install tomli for Python <3.11

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []

def err(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}")

def ok(msg):
    print(f"  OK: {msg}")

def read_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None  # skip binary
    except FileNotFoundError:
        return None

def check_plaintext_code():
    """Ensure '9898' does not appear in plaintext in public/ or source files (except .py, .md)."""
    paths = [
        os.path.join(PROJECT_ROOT, "public"),
        os.path.join(PROJECT_ROOT, "static"),
        os.path.join(PROJECT_ROOT, "layouts"),
        os.path.join(PROJECT_ROOT, "assets"),
    ]
    for base in paths:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for fname in files:
                path = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1]
                if ext in (".py", ".md", ".css", ".gitignore", ".toml", ".json", ".lock"):
                    continue
                content = read_file(path)
                if content and "9898" in content:
                    err(f"Plaintext '9898' found in {path}")
                    return
    ok("No plaintext '9898' found in public/static/layouts/assets")

def check_no_secrets():
    """Check no secrets/keys in source."""
    patterns = ["private_key", "github_token", "ghp_"]
    paths = ["public", "static", "layouts", "assets", "data"]
    for base in paths:
        full = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(full):
            continue
        for root, dirs, files in os.walk(full):
            for fname in files:
                path = os.path.join(root, fname)
                content = read_file(path)
                if content:
                    for pat in patterns:
                        if pat in content:
                            err(f"Secret pattern '{pat}' found in {path}")
                            return
    ok("No secret patterns found in source")

def check_no_income_insights_in_sitemap():
    """Ensure income-insights is not in sitemap, index.xml, or search index."""
    sitemap = read_file(os.path.join(PROJECT_ROOT, "public", "sitemap.xml"))
    if sitemap and "income-insights" in sitemap:
        err("income-insights found in sitemap.xml")
    else:
        ok("income-insights NOT in sitemap.xml")

    rss = read_file(os.path.join(PROJECT_ROOT, "public", "index.xml"))
    if rss and "income-insights" in rss:
        err("income-insights found in index.xml (RSS)")
    else:
        ok("income-insights NOT in index.xml")

    search = None
    for candidate in ["public/search-index.json", "public/search.json"]:
        c = read_file(os.path.join(PROJECT_ROOT, candidate))
        if c:
            search = c
            break
    if search and "income-insights" in search:
        err("income-insights found in search index")
    else:
        ok("income-insights NOT in search index")

def check_no_private_data():
    """Ensure private-data/ is not in public/."""
    private_in_public = read_file(os.path.join(PROJECT_ROOT, "public", "private-data", "income-insights.local.json"))
    if private_in_public:
        err("private-data leaked into public/")
    else:
        ok("private-data NOT in public/")

def check_front_matter():
    """Verify front matter of income-insights _index.md."""
    path = os.path.join(PROJECT_ROOT, "content", "doi-song", "income-insights", "_index.md")
    content = read_file(path)
    if not content:
        err("content/doi-song/income-insights/_index.md not found")
        return

    if "+++" not in content:
        err("Front matter must be TOML (+++)")
        return

    # Parse TOML
    try:
        fm = tomllib.loads(content.split("+++")[1].strip())
    except Exception:
        err("Cannot parse TOML front matter")
        return

    if fm.get("title") != "Income Insights":
        err("title should be 'Income Insights'")
    else:
        ok("title is correct")

    if fm.get("robots") != "noindex,nofollow":
        err("robots should be 'noindex,nofollow'")
    else:
        ok("robots is noindex,nofollow")

    if fm.get("draft") is not False:
        err("draft should be false")
    else:
        ok("draft is false")

    if fm.get("layout") != "income-insights":
        err("layout should be 'income-insights'")
    else:
        ok("layout is income-insights")

    if "date" in fm:
        ds = str(fm["date"])
        if "+07:00" not in ds:
            err(f"date missing +07:00 timezone: {ds}")
        else:
            ok(f"date has +07:00: {ds}")

def check_files_exist():
    """Ensure all required files exist."""
    required = [
        "content/doi-song/income-insights/_index.md",
        "layouts/doi-song/income-insights.html",
        "assets/css/income-insights.css",
        "static/js/income-insights.js",
        "static/js/income-insights-engine.js",
        "static/data/income-insights-schema.json",
        "scripts/qa_income_insights.py",
    ]
    for rel in required:
        path = os.path.join(PROJECT_ROOT, rel)
        if os.path.isfile(path):
            ok(f"File exists: {rel}")
        else:
            err(f"File missing: {rel}")

def check_gitignore():
    """Ensure private data entries in .gitignore."""
    gitignore = read_file(os.path.join(PROJECT_ROOT, ".gitignore"))
    if not gitignore:
        err(".gitignore not found")
        return
    required_patterns = ["private-data/", "data/private-income-insights", "static/private-income-insights", "*.income-insights.private.json"]
    for pat in required_patterns:
        if pat in gitignore:
            ok(f"gitignore contains {pat}")
        else:
            err(f"gitignore missing {pat}")

def check_no_git_conflicts():
    """Check for merge conflict markers."""
    paths = ["content", "layouts", "assets", "static", "scripts", "docs", ".github"]
    found = False
    # Only check new/changed files for actual git conflict markers
    conflict_re = re.compile(r"^<<<<<<< |^=======$|^>>>>>>> ", re.MULTILINE)
    for base in paths:
        full = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(full):
            continue
        for root, dirs, files in os.walk(full):
            for fname in files:
                path = os.path.join(root, fname)
                content = read_file(path)
                if content and conflict_re.search(content):
                    err(f"Merge conflict markers in {path}")
                    found = True
    if not found:
        ok("No merge conflict markers")

def check_access_hash():
    """Verify the access hash in JS matches SHA-256('9898')."""
    js_path = os.path.join(PROJECT_ROOT, "static", "js", "income-insights.js")
    content = read_file(js_path)
    if not content:
        err("income-insights.js not found")
        return

    import hashlib
    expected_hash = hashlib.sha256(b"9898").hexdigest()
    if expected_hash in content:
        ok("Access hash in JS matches SHA-256('9898')")
    else:
        err("Access hash mismatch or missing in JS")

    # Also check the hash doesn't appear as plain "9898" in JS
    if "9898" in content.replace(expected_hash, ""):
        # Check if it's in comments or string literals that aren't the hash
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "9898" in stripped and expected_hash not in stripped:
                err(f"Possible plaintext 9898 in JS at line {i}: {stripped[:80]}")
                return
    ok("No plaintext 9898 in JS beyond hash")

def main():
    print("=== Income Insights QA ===")

    check_files_exist()
    check_front_matter()
    check_plaintext_code()
    check_no_secrets()
    check_no_income_insights_in_sitemap()
    check_no_private_data()
    check_gitignore()
    check_no_git_conflicts()
    check_access_hash()

    print(f"\nResults: {len(errors)} errors")
    for e in errors:
        print(f"  - {e}")

    if errors:
        sys.exit(1)
    else:
        print("All checks passed!")

if __name__ == "__main__":
    main()
