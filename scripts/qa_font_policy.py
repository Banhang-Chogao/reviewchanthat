#!/usr/bin/env python3
"""
qa_font_policy.py — Font stack must never change.

Checks:
  1. --font-sans preserved exactly (system stack)
  2. --font-mono preserved exactly
  3. No Google Fonts import (fonts.googleapis / fonts.gstatic)
  4. No external font URL (woff/woff2/ttf/otf from http)
  5. No new @font-face
  6. body uses var(--font-sans)
  7. code/mono uses var(--font-mono)

Run: python scripts/qa_font_policy.py
Exit: 0 = pass, 1 = violations found
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["assets", "layouts", "static"]
MAIN_CSS = os.path.join(ROOT, "assets", "css", "main.css")

EXPECTED_SANS = (
    '--font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",'
    'Roboto,"Noto Sans",system-ui,sans-serif'
)
EXPECTED_MONO = (
    '--font-mono:"SF Mono",Menlo,Monaco,Consolas,'
    '"Roboto Mono","Noto Mono",monospace'
)


def norm(css: str) -> str:
    """Collapse whitespace so formatting differences don't matter."""
    return re.sub(r"\s+", "", css)


def iter_files():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for fname in filenames:
                if fname.endswith((".css", ".html", ".js", ".scss")):
                    yield os.path.join(dirpath, fname)


def main() -> int:
    errors: list[str] = []

    # 1+2: token equality in main.css
    if not os.path.exists(MAIN_CSS):
        errors.append(f"main.css not found at {MAIN_CSS}")
    else:
        css = norm(open(MAIN_CSS, encoding="utf-8").read())
        if norm(EXPECTED_SANS) not in css:
            errors.append("--font-sans token changed or missing in assets/css/main.css")
        if norm(EXPECTED_MONO) not in css:
            errors.append("--font-mono token changed or missing in assets/css/main.css")
        # 6: body uses the token
        if not re.search(r"body\{[^}]*font-family:var\(--font-sans\)", css):
            errors.append("body no longer uses var(--font-sans)")
        # 7: mono usage still present somewhere
        if "var(--font-mono)" not in css:
            errors.append("no rule uses var(--font-mono) anymore")

    # 3+4+5: scan for foreign fonts (skip main.css.bak backups)
    for path in iter_files():
        if path.endswith(".bak"):
            continue
        rel = os.path.relpath(path, ROOT)
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if "fonts.googleapis" in text or "fonts.gstatic" in text:
            errors.append(f"{rel}: Google Fonts reference")
        # Only actual declarations (@font-face {...}), not documentation text
        if re.search(r"@font-face\s*\{", text):
            errors.append(f"{rel}: @font-face declaration found")
        for m in re.finditer(r"https?://[^\s\"')]+\.(?:woff2?|ttf|otf|eot)", text):
            errors.append(f"{rel}: external font URL {m.group(0)}")

    if errors:
        print("FONT POLICY: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("FONT POLICY: PASS")
    print("  --font-sans: preserved (system stack)")
    print("  --font-mono: preserved")
    print("  no Google Fonts / external fonts / @font-face")
    return 0


if __name__ == "__main__":
    sys.exit(main())
