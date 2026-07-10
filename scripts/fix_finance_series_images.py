#!/usr/bin/env python3
"""Fix 15 quant-finance series posts: real Pexels/Pixabay heroes + inline images.

Policy: stock APIs only, WebP + watermark, full attribution, undraft, min 2 images.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from creator_policy import attribution_text, clean_text  # noqa: E402
from image_providers import load_dotenv  # noqa: E402
from process_images import download_image, process_image, update_post_frontmatter  # noqa: E402
from toml_util import has_toml_fm, read_fm, set_field  # noqa: E402

# (slug, hero_queries, inline_queries)
SERIES: list[tuple[str, list[str], list[str]]] = [
    (
        "ham-so-mu-e-trong-tai-chinh-la-gi",
        ["compound interest growth chart finance", "exponential growth graph investment", "savings growth piggy bank calculator"],
        ["financial calculator laptop desk", "mathematics formula notebook pen"],
    ),
    (
        "log-tu-nhien-log-return-trong-dau-tu",
        ["stock market candlestick chart analysis", "trading chart screen finance", "logarithmic graph data science"],
        ["investor analyzing stock charts laptop"],
    ),
    (
        "quy-dau-tu-dung-toan-hoc-nhu-the-nao",
        ["investment portfolio diversification coins", "mutual fund portfolio chart", "asset allocation pie chart finance"],
        ["hands counting money coins investment"],
    ),
    (
        "cong-ty-bao-hiem-dung-toan-hoc-tinh-phi-rui-ro",
        ["insurance policy documents calculator", "actuary risk calculator desk", "insurance protection umbrella finance"],
        ["family financial planning insurance documents"],
    ),
    (
        "cfa-dung-toan-hoc-gi",
        ["finance professional studying books certification", "chartered financial analyst study desk", "financial exam books calculator"],
        ["business student library finance textbooks"],
    ),
    (
        "frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh",
        ["financial risk dashboard charts", "risk management analytics screen", "VaR risk analysis graph"],
        ["compliance risk management meeting office"],
    ),
    (
        "goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao",
        ["wall street financial district skyscrapers", "investment bank trading floor", "new york stock exchange building"],
        ["bankers in modern office glass building"],
    ),
    (
        "blackrock-dung-toan-hoc-va-du-lieu-quan-ly-danh-muc",
        ["institutional investment portfolio management", "big data finance analytics office", "asset management skyline finance"],
        ["global investment data center screens"],
    ),
    (
        "renaissance-technologies-quantitative-finance-toan-hoc-dau-tu",
        ["quantitative trading algorithms computer screens", "math formulas data science quant", "high frequency trading computers"],
        ["scientist programmer mathematics whiteboard code"],
    ),
    (
        "mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien",
        ["business valuation financial modeling laptop", "discounted cash flow spreadsheet", "equity research analyst desk"],
        ["corporate finance meeting charts presentation"],
    ),
    (
        "black-scholes-la-gi-so-e-dinh-gia-quyen-chon",
        ["options trading stock market screen", "derivatives trading terminal green red", "financial options chain monitor"],
        ["trader looking at option prices screen"],
    ),
    (
        "risk-management-trong-tai-chinh-dung-toan-hoc",
        ["risk management chart finance umbrella", "stress test financial dashboard", "portfolio risk heatmap analytics"],
        ["business protection planning documents desk"],
    ),
    (
        "monte-carlo-trong-tai-chinh-la-gi",
        ["probability simulation random data charts", "monte carlo statistics graph", "dice probability finance risk"],
        ["data scientist probability charts multiple screens"],
    ),
    (
        "ai-trong-tai-chinh-dung-toan-hoc-gi",
        ["artificial intelligence finance technology trading", "machine learning stock market AI", "neural network finance data visualization"],
        ["robot hand and human handshake technology business"],
    ),
    (
        "toan-hoc-dinh-cao-trong-tai-chinh",
        ["advanced mathematics chalkboard finance", "quantitative finance books formulas desk", "mathematical equations financial theory"],
        ["stack of finance mathematics textbooks"],
    ),
]


def pexels_search(query: str, api_key: str, per_page: int = 12) -> list[dict[str, Any]]:
    headers = {"Authorization": api_key, "User-Agent": "ReviewChanThat-FinanceFix/1.0"}
    url = f"https://api.pexels.com/v1/search?query={quote(query)}&orientation=landscape&size=large&per_page={per_page}"
    resp = requests.get(url, headers=headers, timeout=25)
    if resp.status_code != 200:
        print(f"    [Pexels] {resp.status_code} for {query!r}")
        return []
    out = []
    for photo in resp.json().get("photos", []):
        src = photo.get("src") or {}
        direct = src.get("large2x") or src.get("large") or src.get("original")
        if not direct:
            continue
        out.append(
            {
                "source_platform": "Pexels",
                "source_url": clean_text(photo.get("url")),
                "direct_url": clean_text(direct),
                "creator": clean_text(photo.get("photographer")),
                "creator_url": clean_text(photo.get("photographer_url")),
                "creator_id": str(photo.get("photographer_id") or ""),
                "license": "Pexels License",
                "license_url": "https://www.pexels.com/license/",
                "commercial_use": True,
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "query": query,
            }
        )
    return out


def pixabay_search(query: str, api_key: str, per_page: int = 12) -> list[dict[str, Any]]:
    url = (
        f"https://pixabay.com/api/?key={api_key}&q={quote(query)}&lang=en"
        f"&image_type=photo&orientation=horizontal&min_width=1200"
        f"&order=popular&safesearch=true&per_page={per_page}"
    )
    resp = requests.get(url, headers={"User-Agent": "ReviewChanThat-FinanceFix/1.0"}, timeout=25)
    if resp.status_code != 200:
        print(f"    [Pixabay] {resp.status_code} for {query!r}")
        return []
    out = []
    for hit in resp.json().get("hits", []):
        direct = hit.get("largeImageURL") or hit.get("webformatURL")
        if not direct:
            continue
        user = clean_text(hit.get("user"))
        out.append(
            {
                "source_platform": "Pixabay",
                "source_url": clean_text(hit.get("pageURL")),
                "direct_url": clean_text(direct),
                "creator": user,
                "creator_url": f"https://pixabay.com/users/{user}-{hit.get('user_id')}/" if user else "",
                "creator_id": str(hit.get("user_id") or ""),
                "license": "Pixabay License",
                "license_url": "https://pixabay.com/service/license-summary/",
                "commercial_use": True,
                "width": hit.get("imageWidth", 0),
                "height": hit.get("imageHeight", 0),
                "query": query,
            }
        )
    return out


def pick_candidate(queries: list[str], used_urls: set[str], pexels_key: str, pixabay_key: str) -> dict[str, Any] | None:
    for q in queries:
        pool: list[dict[str, Any]] = []
        if pexels_key:
            pool.extend(pexels_search(q, pexels_key))
            time.sleep(0.35)
        if not pool and pixabay_key:
            pool.extend(pixabay_search(q, pixabay_key))
            time.sleep(0.5)
        for c in pool:
            url = c.get("source_url") or c.get("direct_url")
            if not url or url in used_urls:
                continue
            if not c.get("creator"):
                continue
            if (c.get("width") or 0) and (c.get("width") or 0) < 1000:
                continue
            used_urls.add(url)
            return c
    return None


def apply_inline_body(path: Path, rel_path: str, alt: str, caption: str) -> None:
    text = path.read_text(encoding="utf-8")
    # Remove prior auto inline block for this series fix
    text = re.sub(
        r"\n+!\[[^\]]*\]\(/?(?:images/posts/[^)]+-inline\.webp)\)\n+(?:\*[^\n]+\*\n+)?",
        "\n\n",
        text,
        count=1,
    )
    block = f"\n\n![{alt}](/{rel_path.lstrip('/')})\n\n*{caption}*\n\n"
    # Insert after first level-2 heading section start (after the heading line)
    m = re.search(r"(^## .+\n)", text, re.M)
    if m:
        idx = m.end()
        text = text[:idx] + block + text[idx:]
    else:
        # after front matter
        if text.startswith("+++"):
            parts = text.split("+++", 2)
            if len(parts) >= 3:
                text = "+++" + parts[1] + "+++" + block + parts[2]
            else:
                text = text + block
        else:
            text = text + block
    path.write_text(text, encoding="utf-8")


def undraft_and_meta(path: Path, image_alt: str, image_query: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not has_toml_fm(text):
        return
    parts = read_fm(text)
    if not parts:
        return
    opener, fm_text, body = parts[0], parts[1], parts[2]
    fm_text = set_field(fm_text, "draft", False)
    fm_text = set_field(fm_text, "image_alt", image_alt)
    fm_text = set_field(fm_text, "image_query", image_query)
    path.write_text(opener + fm_text.strip() + "\n+++" + body, encoding="utf-8")


def main() -> int:
    load_dotenv()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not pexels_key and not pixabay_key:
        print("ERROR: need PEXELS_API_KEY or PIXABAY_API_KEY in .env")
        return 1

    used: set[str] = set()
    manifest_path = ROOT / "data" / "images.json"
    manifest = {"posts": [], "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00")}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    by_slug = {e.get("slug"): e for e in manifest.get("posts", []) if e.get("slug")}

    ok = 0
    fail = 0
    for slug, hero_qs, inline_qs in SERIES:
        print(f"\n=== {slug} ===")
        post_path = ROOT / "content" / "posts" / f"{slug}.md"
        if not post_path.exists():
            print("  MISSING post file")
            fail += 1
            continue

        hero = pick_candidate(hero_qs, used, pexels_key, pixabay_key)
        if not hero:
            print("  FAIL: no hero candidate")
            fail += 1
            continue
        inline = pick_candidate(inline_qs, used, pexels_key, pixabay_key)
        if not inline:
            # fallback: second hero query pool
            inline = pick_candidate(hero_qs[::-1], used, pexels_key, pixabay_key)
        if not inline:
            print("  FAIL: no inline candidate")
            fail += 1
            continue

        print(f"  hero: {hero['source_platform']} / {hero['creator']} — {hero['query']}")
        print(f"  inline: {inline['source_platform']} / {inline['creator']} — {inline['query']}")

        # Download + process hero
        hero_src = ROOT / "static" / "images" / "posts-src" / f"{slug}.jpg"
        hero_out = ROOT / "static" / "images" / "posts" / f"{slug}.webp"
        if not download_image(hero["direct_url"], str(hero_src)):
            print("  FAIL: hero download")
            fail += 1
            continue
        wm = attribution_text(hero["source_platform"], hero["creator"])
        if not process_image(str(hero_src), str(hero_out), wm):
            print("  FAIL: hero process")
            fail += 1
            continue

        # Download + process inline
        inline_slug = f"{slug}-inline"
        inline_src = ROOT / "static" / "images" / "posts-src" / f"{inline_slug}.jpg"
        inline_out = ROOT / "static" / "images" / "posts" / f"{inline_slug}.webp"
        if not download_image(inline["direct_url"], str(inline_src)):
            print("  FAIL: inline download")
            fail += 1
            continue
        wm_i = attribution_text(inline["source_platform"], inline["creator"])
        if not process_image(str(inline_src), str(inline_out), wm_i):
            print("  FAIL: inline process")
            fail += 1
            continue

        # Front matter via process_images helper
        platform = hero["source_platform"]
        attr_source = "pexels_api" if platform == "Pexels" else "pixabay_api"
        update_post_frontmatter(
            slug=slug,
            image_path=f"images/posts/{slug}.webp",
            thumbnail_path=f"images/posts/{slug}.webp",
            source=platform,
            source_url=hero["source_url"],
            license_val=hero["license"],
            commercial_use=True,
            owner="external",
            creator=hero["creator"],
            creator_url=hero.get("creator_url") or "",
            creator_id=hero.get("creator_id") or "",
            image_status="verified",
            attribution_verified=True,
            attribution_source=attr_source,
            license_url=hero.get("license_url") or "",
        )

        title_guess = slug.replace("-", " ")
        image_alt = f"Ảnh minh họa {title_guess} — nguồn {platform}"
        undraft_and_meta(post_path, image_alt=image_alt, image_query=hero["query"])

        caption = f"Nguồn: {inline['source_platform']} / {inline['creator']}"
        apply_inline_body(
            post_path,
            rel_path=f"images/posts/{inline_slug}.webp",
            alt=image_alt.replace("Ảnh minh họa", "Minh họa nội dung"),
            caption=caption,
        )

        # Manifest entries
        by_slug[slug] = {
            "slug": slug,
            "title": title_guess,
            "source_platform": platform,
            "source_url": hero["source_url"],
            "direct_url": hero["direct_url"],
            "creator": hero["creator"],
            "creator_url": hero.get("creator_url") or "",
            "license": hero["license"],
            "commercial_use": True,
            "local_source_path": f"static/images/posts-src/{slug}.jpg",
            "output_path": f"static/images/posts/{slug}.webp",
            "attribution_verified": True,
            "status": "verified",
        }
        by_slug[inline_slug] = {
            "slug": inline_slug,
            "title": f"{title_guess} inline",
            "source_platform": inline["source_platform"],
            "source_url": inline["source_url"],
            "direct_url": inline["direct_url"],
            "creator": inline["creator"],
            "creator_url": inline.get("creator_url") or "",
            "license": inline["license"],
            "commercial_use": True,
            "local_source_path": f"static/images/posts-src/{inline_slug}.jpg",
            "output_path": f"static/images/posts/{inline_slug}.webp",
            "attribution_verified": True,
            "status": "verified",
        }
        ok += 1
        print("  OK")

    manifest["posts"] = list(by_slug.values())
    manifest["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nDone: ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
