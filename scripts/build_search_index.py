#!/usr/bin/env python3
"""Build search-index.json from Hugo's rendered searchindex.json."""
import json
import os
import sys

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


def main():
    hugo_output = os.path.join(PUBLIC_DIR, "search-index.json")
    static_output = os.path.join(STATIC_DIR, "search-index.json")

    if os.path.exists(hugo_output):
        with open(hugo_output, "r", encoding="utf-8") as f:
            data = json.load(f)
        os.makedirs(STATIC_DIR, exist_ok=True)
        with open(static_output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Search index built: {len(data)} entries -> {static_output}")
    else:
        print(f"Search index build skipped: {hugo_output} not found (run 'hugo' first)")
        sys.exit(1)


if __name__ == "__main__":
    main()
