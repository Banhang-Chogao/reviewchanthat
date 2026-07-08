#!/usr/bin/env python3
"""Verify built blog post pages include print/PDF watermark assets."""

from __future__ import annotations

import pathlib
import sys

PUBLIC_DIR = pathlib.Path("public")
SKIP_PREFIXES = (
    "about/",
    "admin/",
    "authors/",
    "categories/",
    "cong-nghe/",
    "contact/",
    "css/",
    "disclaimer/",
    "doi-song/",
    "images/",
    "js/",
    "page/",
    "posts/",
    "privacy/",
    "review/",
    "tags/",
    "tai-chinh/",
)
REQUIRED_MARKERS = (
    "has-print-watermark",
    "id=print-watermark",
    "print-watermark",
)


def is_post_page(path: pathlib.Path) -> bool:
    rel = path.relative_to(PUBLIC_DIR).as_posix()
    if rel in {"index.html", "404.html"}:
        return False
    return not rel.startswith(SKIP_PREFIXES)


def main() -> int:
    if not PUBLIC_DIR.exists():
        print("❌ public/ not found — run hugo build first")
        return 1

    checked = 0
    errors: list[str] = []

    for page in sorted(PUBLIC_DIR.rglob("index.html")):
        if not is_post_page(page):
            continue
        checked += 1
        html = page.read_text(encoding="utf-8")
        missing = [marker for marker in REQUIRED_MARKERS if marker not in html]
        if missing:
            errors.append(f"  [FAIL] {page.relative_to(PUBLIC_DIR)}: missing {', '.join(missing)}")

    print(f"Checked {checked} built blog post pages for print watermark")
    if errors:
        print("\n".join(errors))
        print("\n❌ PRINT WATERMARK VERIFY FAILED")
        return 1

    print("✅ PRINT WATERMARK VERIFY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())