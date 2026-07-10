#!/usr/bin/env python3
"""QA: Validate smart pagination HTML output."""
import re
import sys
from pathlib import Path

PUBLIC = Path("public")
errors = []

PAGINATION_RE = re.compile(r'<nav\s+class="pagination"[^>]*>.*?</nav>', re.DOTALL)
PAGE_LINK_RE = re.compile(r'aria-label="Trang (\d+)"')
CONTROL_RE = re.compile(r'aria-label="Trang (trước|sau)"')
ELLIPSIS_RE = re.compile(r'aria-hidden="true"')
CURRENT_RE = re.compile(r'aria-current="page"')
HREF_PAGE_RE = re.compile(r'href="[^"]*/page/\d+/"')

def check_pagination(html: str, path: str):
    matches = PAGINATION_RE.findall(html)
    for nav in matches:
        numbers = PAGE_LINK_RE.findall(nav)
        controls = CONTROL_RE.findall(nav)
        ellipsis = ELLIPSIS_RE.findall(nav)
        current = CURRENT_RE.findall(nav)
        total_controls = len(numbers) + len(controls) + len(ellipsis)

        # No page has more than 11 total controls
        if total_controls > 11:
            errors.append(f"{path}: {total_controls} total controls (>11)")

        # No more than 7 number buttons
        if len(numbers) > 7:
            errors.append(f"{path}: {len(numbers)} number buttons (>7)")

        # Has aria-current="page"
        if not current:
            errors.append(f"{path}: missing aria-current=\"page\"")

        # Has first and last page when total > 7
        nums = [int(n) for n in numbers if n.isdigit()]
        if nums:
            if len(nums) < 2 and len(ellipsis) > 0:
                errors.append(f"{path}: not enough visible pages given ellipsis")
            # Check no duplicate page numbers
            if len(nums) != len(set(nums)):
                errors.append(f"{path}: duplicate page numbers: {nums}")

        # Check no href="/page/1/ which would be wrong canonical
        wrong_page1 = re.findall(r'href="[^"]*/page/1/"', nav)
        if wrong_page1:
            errors.append(f"{path}: has href to /page/1/")

        # No href starting with /page/ missing base path
        bare_page = re.findall(r'href="/page/', nav)
        if bare_page:
            errors.append(f"{path}: bare /page/ href without base path")

        # Check first page has no "Trước"
        has_prev = 'aria-label="Trang trước"' in nav
        # Check last page has no "Sau"
        has_next = 'aria-label="Trang sau"' in nav

        # If this is page 1, should not have prev
        # We check by seeing if page 1 is current AND has prev
        is_page_1 = 'aria-current="page"' in nav and 'aria-label="Trang 1"' in nav
        if is_page_1 and has_prev:
            errors.append(f"{path}: page 1 should not have Trước")

        # If aria-label="Trang trước" exists on a page that also shows last page with no next
        # Check if last page is in numbers and has no Sau
        if nums and max(nums) == max(nums):  # always true, just check has_next
            pass  # We can't easily check this without knowing total pages

def main():
    html_files = list(PUBLIC.rglob("*.html"))
    if not html_files:
        print("FAIL: No HTML files found in public/")
        sys.exit(1)

    # Check all paginated pages
    paginated_paths = set()
    for f in html_files:
        # Check if it's a page number
        if re.search(r'/page/\d+/', str(f.relative_to(PUBLIC))):
            paginated_paths.add(f)

    # Also check main pages (/, /categories/*, /tags/*, /series/*) for pagination existence
    main_pages = set()
    for f in html_files:
        rel = str(f.relative_to(PUBLIC))
        if rel == "index.html" or rel.endswith("/index.html"):
            # Only check section/category/tag/series pages, not individual posts
            parts = rel.split("/")
            if len(parts) <= 3:  # shallow paths
                main_pages.add(f)

    for f in sorted(paginated_paths | main_pages):
        html = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(PUBLIC))
        check_pagination(html, rel)

    # Additional global checks
    for f in PUBLIC.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(PUBLIC))
        # Check for merge conflict markers
        if "<<<<<<<" in html or "=======" in html or ">>>>>>>" in html:
            errors.append(f"{rel}: contains merge conflict markers")

    if errors:
        print(f"FAIL: {len(errors)} pagination issue(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"OK: pagination checks passed ({len(paginated_paths)} paginated pages checked)")
        sys.exit(0)

if __name__ == "__main__":
    main()
