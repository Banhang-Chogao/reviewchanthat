#!/usr/bin/env python3
"""QA for Content Direction report + rendered page.

Usage:
  python scripts/qa_content_direction.py
  python scripts/qa_content_direction.py --public
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = REPO_ROOT / "data" / "content-direction.json"
PUBLIC_PAGE = REPO_ROOT / "public" / "content-direction" / "index.html"
SITEMAP = REPO_ROOT / "public" / "sitemap.xml"
PUBLIC_ROOT = REPO_ROOT / "public"

DISPLAY_RE = re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$")
FORBIDDEN_IMAGE_PHRASES = (
    "Image / Attribution Risk",
    "Hero images",
    "Thiếu credit",
    "Nguồn ảnh",
    "image_attribution_risk",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def check_data() -> list[str]:
    errors: list[str] = []
    if not DATA_JSON.exists():
        errors.append(f"missing {DATA_JSON.relative_to(REPO_ROOT)}")
        return errors

    try:
        report = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"JSON parse error: {exc}")
        return errors

    if not isinstance(report, dict):
        errors.append("report root must be object")
        return errors

    if "generated_at" not in report:
        errors.append("generated_at missing")
    display = report.get("generated_at_display") or ""
    if not DISPLAY_RE.match(display):
        errors.append(f"generated_at_display format invalid: {display!r}")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary missing or not object")
        return errors

    total_posts = int(summary.get("total_posts") or 0)
    total_words = int(summary.get("total_words") or 0)
    if total_posts <= 0:
        errors.append("summary.total_posts must be > 0 (empty report not allowed)")
    else:
        ok(f"total_posts={total_posts}")
    if total_words <= 0:
        errors.append("summary.total_words must be > 0")
    else:
        ok(f"total_words={total_words}")

    categories = report.get("categories")
    if categories is None:
        errors.append("categories key missing")
    elif not isinstance(categories, list):
        errors.append("categories must be a list")
    elif total_posts > 0 and len(categories) == 0:
        # Allow only if posts truly have no categories — still warn as soft fail when authors empty too
        authors = report.get("authors") or []
        if authors:
            errors.append("categories empty but posts/authors exist — unexpected")
        else:
            print("WARN: categories empty")

    action_items = report.get("action_items")
    if not isinstance(action_items, list):
        errors.append("action_items must be a list")
    else:
        ok(f"action_items={len(action_items)}")

    if "image_attribution_risk" in report:
        errors.append("image_attribution_risk must not be in Content Direction report")

    # Image section keys must not be required / present as top-level audit block
    for key in ("hero_images", "missing_credit", "image_provider_distribution"):
        if key in report:
            errors.append(f"forbidden image key present: {key}")

    return errors


def check_public(total_posts: int) -> list[str]:
    errors: list[str] = []
    if not PUBLIC_PAGE.exists():
        errors.append(f"missing {PUBLIC_PAGE.relative_to(REPO_ROOT)} — run hugo --minify")
        return errors

    html = PUBLIC_PAGE.read_text(encoding="utf-8", errors="replace")

    if "Content Direction Report" not in html:
        errors.append("page missing 'Content Direction Report'")
    else:
        ok("page title/heading present")

    if 'content="noindex,follow"' not in html and "noindex,follow" not in html:
        errors.append("page missing noindex,follow robots meta")
    else:
        ok("noindex,follow present")

    if total_posts > 0:
        # Should not show fake empty dashboard
        if re.search(r'cd-stat-value">0</span>\s*<span class="cd-stat-label">Bài viết', html):
            errors.append("page shows 0 Bài viết while total_posts > 0")
        if "Content Direction data is empty" in html and f">{total_posts}" not in html:
            # error card only expected when empty
            errors.append("page shows empty-data error card while report has posts")
        # Positive signal: the real count appears
        if f">{total_posts}" not in html:
            errors.append(f"page does not contain total_posts value {total_posts}")
        else:
            ok(f"page contains total_posts={total_posts}")

    for phrase in FORBIDDEN_IMAGE_PHRASES:
        if phrase in html:
            errors.append(f"page still contains image section text: {phrase!r}")

    # Footer link with baseURL path
    footer_ok = False
    for candidate in (
        "/reviewchanthat/content-direction/",
        'href="/reviewchanthat/content-direction/"',
        "content-direction/",
    ):
        # Prefer checking any public HTML for footer; main page is enough if partial shared
        if candidate in html:
            footer_ok = True
            break
    # Footer is on all pages — also scan homepage if needed
    home = PUBLIC_ROOT / "index.html"
    if home.exists():
        home_html = home.read_text(encoding="utf-8", errors="replace")
        if "/reviewchanthat/content-direction/" in home_html or 'href="content-direction/' in home_html:
            footer_ok = True
        if "Content Direction" in home_html or "SEO Report" in home_html:
            # Label may be either during transition; relURL link is what matters
            pass
        if "/reviewchanthat/content-direction/" in home_html:
            ok("footer links to /reviewchanthat/content-direction/")
            footer_ok = True

    if not footer_ok:
        # With absURLs baseURL, footer should include base path
        if re.search(r'href="[^"]*content-direction/', html):
            ok("footer/content-direction href present on page")
        else:
            # Check a random other page for footer
            about = PUBLIC_ROOT / "about" / "index.html"
            if about.exists():
                about_html = about.read_text(encoding="utf-8", errors="replace")
                if re.search(r'content-direction/', about_html):
                    ok("footer content-direction link found on about page")
                else:
                    errors.append("footer link to content-direction/ not found")
            else:
                errors.append("footer link to content-direction/ not found")

    if SITEMAP.exists():
        sm = SITEMAP.read_text(encoding="utf-8", errors="replace")
        if "content-direction" in sm:
            errors.append("sitemap.xml must not include content-direction")
        else:
            ok("sitemap excludes content-direction")
    else:
        print("WARN: public/sitemap.xml missing — skip sitemap check")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="QA Content Direction")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Also validate public/content-direction after Hugo build",
    )
    args = parser.parse_args()

    errors = check_data()
    total_posts = 0
    if DATA_JSON.exists():
        try:
            report = json.loads(DATA_JSON.read_text(encoding="utf-8"))
            total_posts = int((report.get("summary") or {}).get("total_posts") or 0)
        except Exception:  # noqa: BLE001
            pass

    if args.public:
        errors.extend(check_public(total_posts))

    if errors:
        for e in errors:
            fail(e)
        print(f"qa_content_direction: {len(errors)} failure(s)", file=sys.stderr)
        return 1

    print("qa_content_direction: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
