#!/usr/bin/env python3
"""Content Direction Report — SEO / content / freshness / internal-link audit.

Scans content/posts/**/*.md (YAML + TOML front matter). Does NOT audit images.

Usage:
  python scripts/content_direction.py \\
    --json data/content-direction.json \\
    --md reports/content-direction-report.md
  python scripts/content_direction.py --check
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_JSON = DATA_DIR / "content-direction.json"
DEFAULT_MD = REPORTS_DIR / "content-direction-report.md"
INTERNAL_LINKS_PATH = DATA_DIR / "internal-links.json"

VN_STOP_WORDS = {
    "ve", "la", "cua", "va", "hoac", "de", "cho", "voi", "the", "nay",
    "do", "mot", "co", "duoc", "nhung", "cac", "nhu", "khi", "neu",
}
TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 50, 160
SLUG_MAX = 75
CATEGORY_LOW_THRESHOLD = 3
CLUSTER_MIN_POSTS = 5

TOPIC_CLUSTERS = {
    "korea-summer": ["han-quoc", "korea", "mua-he", "thang-7", "thang-8", "caribbean-bay", "tranh-nong", "cong-vien-nuoc"],
    "korea-autumn": ["thang-10", "thang-11", "la-do", "seoraksan", "mua-thu", "nami"],
    "jeju": ["jeju", "udo"],
    "busan": ["busan", "haeundae", "gwangalli", "songdo", "dadaepo", "cheongsapo"],
    "seoul": ["seoul", "suwon", "incheon", "wolmido"],
    "apple-iphone": ["iphone", "ios", "camera-iphone", "pin-iphone"],
    "apple-macos": ["macos", "macbook"],
    "apple-dma": ["dma", "digital-markets", "app-store", "gatekeeper"],
    "thailand": ["thai-lan", "thailand", "bangkok", "phuket", "chiang-mai", "krabi", "koh-samui"],
    "starbucks": ["starbucks"],
    "review-tips": ["cach-doc", "thoi-quen", "checklist", "review-dai"],
    "ski": ["ski", "truot-tuyet", "alpensia", "yongpyong", "elysian"],
}

MD_INTERNAL_LINK_RE = re.compile(
    r"\]\(\s*(?:https?://[^)\s]+)?(?:/reviewchanthat)?/posts/([a-z0-9][a-z0-9\-]*)/?",
    re.I,
)
MD_REL_INTERNAL_RE = re.compile(
    r"\]\(\s*(?:\.\./)*(?:posts/)?([a-z0-9][a-z0-9\-]*)/?\s*\)",
    re.I,
)


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    return {}


def parse_front_matter(text: str) -> tuple[dict | None, str, str | None]:
    """Parse YAML (---) or TOML (+++) front matter. Returns (meta, body, error)."""
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
        if not m:
            return None, text, "yaml-boundary-fail"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                meta = yaml.safe_load(m.group(1)) or {}
            if not isinstance(meta, dict):
                return None, m.group(2), "yaml-not-mapping"
            return meta, m.group(2), None
        except Exception as exc:  # noqa: BLE001
            return None, text, f"yaml-parse-error: {exc}"

    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", text, re.S)
        if not m:
            return None, text, "toml-boundary-fail"
        try:
            meta = tomllib.loads(m.group(1))
            if not isinstance(meta, dict):
                return None, m.group(2), "toml-not-mapping"
            return meta, m.group(2), None
        except Exception as exc:  # noqa: BLE001
            return None, text, f"toml-parse-error: {exc}"

    return {}, text, "no-frontmatter"


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    s = str(value).strip().replace("Z", "+00:00")
    # Hugo bare dates sometimes use space before offset
    s = re.sub(r"(\d{2}:\d{2}:\d{2})\s+(\+\d{2}:\d{2})", r"\1\2", s)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def extract_md_internal_links(body: str, self_slug: str) -> list[str]:
    found: list[str] = []
    for m in MD_INTERNAL_LINK_RE.finditer(body or ""):
        slug = m.group(1)
        if slug and slug != self_slug:
            found.append(slug)
    # Relative refs that look like post slugs (best-effort; only keep known later)
    for m in MD_REL_INTERNAL_RE.finditer(body or ""):
        slug = m.group(1)
        if slug and slug != self_slug and len(slug) > 8 and "-" in slug:
            found.append(slug)
    # Dedup preserve order
    seen = set()
    out = []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def parse_post(md_file: Path) -> tuple[dict | None, str | None]:
    try:
        text = md_file.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"read-error: {exc}"

    meta, body, err = parse_front_matter(text)
    if err and err != "no-frontmatter":
        return None, err
    if meta is None:
        return None, err or "parse-failed"

    slug = str(meta.get("slug") or md_file.stem).strip()
    title = str(meta.get("title") or "").strip() or slug
    # Effective SEO title used for <title>/SERP length (layouts/partials/seo.html)
    seo_title = str(meta.get("seo_title") or "").strip()
    effective_title = seo_title if seo_title else title
    draft = bool(meta.get("draft", False))
    cats = [str(c).strip() for c in _as_list(meta.get("categories")) if str(c).strip()]
    tags = [str(t).strip() for t in _as_list(meta.get("tags")) if str(t).strip()]
    author = str(meta.get("author") or "").strip()
    description = str(meta.get("description") or "").strip()
    word_count = len((body or "").split())
    md_links = extract_md_internal_links(body or "", slug)
    fm_links = []
    for link in _as_list(meta.get("internal_links")):
        if isinstance(link, dict):
            for key in ("ref", "url", "link", "href", "slug", "path", "target"):
                val = link.get(key)
                if val and isinstance(val, str):
                    fm_links.append(os.path.splitext(os.path.basename(val.rstrip("/")))[0])
                    break
        elif isinstance(link, str) and link.strip():
            fm_links.append(os.path.splitext(os.path.basename(link.strip().rstrip("/")))[0])

    return {
        "slug": slug,
        "path": str(md_file.relative_to(REPO_ROOT)),
        "title": title,
        "seo_title": seo_title,
        "effective_title": effective_title,
        "date": meta.get("date"),
        "lastmod": meta.get("lastmod", meta.get("date")),
        "draft": draft,
        "categories": cats,
        "tags": tags,
        "author": author,
        "description": description,
        "word_count": word_count,
        "fm_internal_links": fm_links,
        "md_internal_links": md_links,
        "has_faq": bool(meta.get("faq")),
        "pillar": bool(meta.get("pillar", False) or meta.get("is_pillar", False)),
        "noindex": bool(meta.get("noindex", False) or meta.get("private", False)),
        "warning": None if title != slug or meta.get("title") else "missing-title",
    }, None


def analyze_posts() -> tuple[list[dict], list[dict], list[str]]:
    """Return (published_posts, draft_posts, warnings)."""
    published: list[dict] = []
    drafts: list[dict] = []
    warnings_list: list[str] = []

    files = sorted(CONTENT_DIR.rglob("*.md"))
    if not files:
        return [], [], [f"No markdown files under {CONTENT_DIR}"]

    for md_file in files:
        post, err = parse_post(md_file)
        if err:
            warnings_list.append(f"{md_file.relative_to(REPO_ROOT)}: {err}")
            continue
        assert post is not None
        if post.get("warning"):
            warnings_list.append(f"{post['path']}: {post['warning']}")
        if post["draft"]:
            drafts.append(post)
        else:
            published.append(post)

    return published, drafts, warnings_list


def detect_clusters(post: dict) -> list[str]:
    text = " ".join(
        [
            post["slug"].lower(),
            (post["title"] or "").lower(),
            " ".join(post["categories"]),
            " ".join(post["tags"]),
        ]
    )
    matched = []
    for name, keywords in TOPIC_CLUSTERS.items():
        if any(kw in text for kw in keywords):
            matched.append(name)
    return matched


def is_pillar_candidate(post: dict) -> bool:
    """Heuristic: long overview / hub posts act as pillars."""
    if post.get("pillar"):
        return True
    title = (post["title"] or "").lower()
    slug = post["slug"].lower()
    markers = (
        "nen-di-dau", "top-", "tong-hop", "lich-trinh", "series", "vs",
        "co-gi-moi", "huong-dan", "checklist", "complete", "roundup",
        "lich-su", "hanh-trinh", "playbook", "overview", "tong-quan",
    )
    if post["word_count"] >= 1800:
        return True
    return any(m in slug or m in title for m in markers)


def load_gap_brief_mitigations() -> set[tuple[str, str]]:
    """Gaps addressed by planned/resolved briefs count as mitigated."""
    path = DATA_DIR / "content-gap-briefs.json"
    data = load_json(path)
    mitigated: set[tuple[str, str]] = set()
    for brief in data.get("briefs") or []:
        if not isinstance(brief, dict):
            continue
        status = str(brief.get("status") or "").lower()
        if status not in {"planned", "resolved", "in_progress", "briefed", "queued"}:
            continue
        gap = brief.get("addresses_gap") or {}
        gtype = str(gap.get("type") or "").strip()
        gname = str(gap.get("name") or "").strip()
        if gtype and gname:
            mitigated.add((gtype, gname))
    return mitigated


def compute_report(posts: list[dict], draft_posts: list[dict], warnings_list: list[str]) -> dict:
    now = now_vietnam()
    total = len(posts)
    total_words = sum(p["word_count"] for p in posts)
    avg_words = round(total_words / total) if total else 0

    cat_counter: Counter = Counter()
    author_counter: Counter = Counter()
    tag_counter: Counter = Counter()
    dates: list[datetime] = []

    for p in posts:
        for c in p["categories"]:
            cat_counter[c] += 1
        for t in p["tags"]:
            tag_counter[t] += 1
        if p["author"]:
            author_counter[p["author"]] += 1
        dt = _parse_dt(p["date"])
        if dt:
            dates.append(dt)

    categories = [{"name": n, "count": c} for n, c in cat_counter.most_common()]
    authors = [{"name": n, "count": c} for n, c in author_counter.most_common()]

    oldest = min(dates) if dates else None
    newest = max(dates) if dates else None

    # SEO lists
    title_too_short = []
    title_too_long = []
    desc_missing = []
    desc_too_short = []
    desc_too_long = []
    slug_too_long = []
    slug_stop_words = []

    for p in posts:
        # Score SERP title length via effective title (seo_title if set, else title)
        effective = p.get("effective_title") or p.get("title") or ""
        tl = len(effective)
        if tl < TITLE_MIN:
            title_too_short.append({
                "slug": p["slug"],
                "title": p["title"],
                "seo_title": p.get("seo_title") or "",
                "effective_title": effective,
                "length": tl,
            })
        elif tl > TITLE_MAX:
            title_too_long.append({
                "slug": p["slug"],
                "title": p["title"],
                "seo_title": p.get("seo_title") or "",
                "effective_title": effective,
                "length": tl,
            })

        d = p.get("description") or ""
        if not d:
            desc_missing.append({"slug": p["slug"], "title": p["title"]})
        elif len(d) < DESC_MIN:
            desc_too_short.append({"slug": p["slug"], "title": p["title"], "length": len(d)})
        elif len(d) > DESC_MAX:
            desc_too_long.append({"slug": p["slug"], "title": p["title"], "length": len(d)})

        slug = p["slug"]
        if len(slug) > SLUG_MAX:
            slug_too_long.append({"slug": slug, "length": len(slug)})
        parts = slug.replace("-", " ").split()
        found_stops = sorted({w for w in parts if w in VN_STOP_WORDS})
        if found_stops:
            slug_stop_words.append({"slug": slug, "stop_words": found_stops})

    # Freshness
    ages: list[int] = []
    old_posts = []
    new_posts = []
    for p in posts:
        dt = _parse_dt(p["date"])
        if not dt:
            continue
        age = (now - dt.astimezone(now.tzinfo)).days
        ages.append(age)
        entry = {
            "slug": p["slug"],
            "title": p["title"],
            "age_days": age,
            "date": format_vietnam_datetime(dt),
        }
        if age > 365:
            old_posts.append(entry)
        elif age < 30:
            new_posts.append(entry)

    # Internal linking: markdown + FM + generated graph
    il_data = load_json(INTERNAL_LINKS_PATH)
    generated_links: dict[str, list] = il_data.get("links") or {}
    inbound_from_graph: dict[str, int] = {
        k: int(v) for k, v in (il_data.get("inbound_counts") or {}).items()
    }

    inbound: Counter = Counter()
    outbound_counts: dict[str, int] = {}
    posts_missing_il: list[dict] = []
    all_slugs = {p["slug"] for p in posts}

    for p in posts:
        md_out = [s for s in p["md_internal_links"] if s in all_slugs or s in inbound_from_graph]
        fm_out = [s for s in p["fm_internal_links"] if s]
        gen_out = []
        for item in generated_links.get(p["slug"], []) or []:
            if isinstance(item, dict):
                t = item.get("target") or item.get("slug")
                if t:
                    gen_out.append(str(t))
            elif isinstance(item, str):
                gen_out.append(item)

        combined = list(dict.fromkeys(md_out + fm_out + gen_out))
        outbound_counts[p["slug"]] = len(combined)
        for target in combined:
            inbound[target] += 1
        if not combined:
            posts_missing_il.append({"slug": p["slug"], "title": p["title"]})

    # Prefer graph inbound if richer
    for slug, count in inbound_from_graph.items():
        if count > inbound.get(slug, 0):
            inbound[slug] = count

    orphan_posts = [
        {"slug": p["slug"], "title": p["title"]}
        for p in posts
        if inbound.get(p["slug"], 0) == 0
    ]

    top_linked = []
    for slug, count in inbound.most_common(10):
        match = next((p for p in posts if p["slug"] == slug), None)
        title = match["title"] if match else slug
        top_linked.append({"slug": slug, "title": title, "inbound": count})

    # Content gaps
    content_gaps: list[dict] = []
    for name, count in cat_counter.most_common():
        if count < CATEGORY_LOW_THRESHOLD:
            content_gaps.append({
                "type": "low_category_count",
                "name": name,
                "detail": f"Danh mục '{name}' chỉ có {count} bài (ngưỡng {CATEGORY_LOW_THRESHOLD}).",
                "count": count,
            })

    cluster_posts: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        for c in detect_clusters(p):
            cluster_posts[c].append(p)

    for cluster, cposts in sorted(cluster_posts.items(), key=lambda x: -len(x[1])):
        if len(cposts) < CLUSTER_MIN_POSTS:
            continue
        pillars = [p for p in cposts if is_pillar_candidate(p)]
        if not pillars:
            content_gaps.append({
                "type": "missing_pillar",
                "name": cluster,
                "detail": (
                    f"Cluster '{cluster}' có {len(cposts)} bài nhưng thiếu pillar/hub overview."
                ),
                "count": len(cposts),
            })
        ages_c = []
        for p in cposts:
            dt = _parse_dt(p["date"])
            if dt:
                ages_c.append((now - dt.astimezone(now.tzinfo)).days)
        if ages_c and (sum(ages_c) / len(ages_c)) > 180:
            content_gaps.append({
                "type": "outdated_cluster",
                "name": cluster,
                "detail": (
                    f"Cluster '{cluster}' tuổi trung bình "
                    f"{round(sum(ages_c)/len(ages_c))} ngày — cân nhắc refresh."
                ),
                "count": len(cposts),
            })

    # Mitigate gaps covered by actionable briefs (planned/resolved) without writing full posts
    mitigated = load_gap_brief_mitigations()
    if mitigated:
        content_gaps = [
            g for g in content_gaps
            if (g.get("type"), g.get("name")) not in mitigated
        ]

    # Action items P0/P1/P2
    action_items: list[dict] = []

    def add_action(priority: str, atype: str, title: str, detail: str, affected: int, fix: str):
        action_items.append({
            "priority": priority,
            "type": atype,
            "title": title,
            "detail": detail,
            "affected_count": affected,
            "suggested_fix": fix,
        })

    if desc_missing:
        add_action(
            "P0", "SEO",
            "Thêm meta description cho bài thiếu",
            f"{len(desc_missing)} bài chưa có meta description.",
            len(desc_missing),
            "Viết description 50–160 ký tự, chứa keyword chính.",
        )
    if title_too_short or title_too_long:
        n = len(title_too_short) + len(title_too_long)
        add_action(
            "P1", "SEO",
            "Tối ưu độ dài title tag",
            f"{len(title_too_short)} title quá ngắn, {len(title_too_long)} title quá dài (chuẩn {TITLE_MIN}–{TITLE_MAX} ký tự).",
            n,
            "Rút gọn/mở rộng title về 30–60 ký tự, giữ keyword đầu.",
        )
    if desc_too_short or desc_too_long:
        n = len(desc_too_short) + len(desc_too_long)
        add_action(
            "P1", "SEO",
            "Tối ưu độ dài meta description",
            f"{len(desc_too_short)} quá ngắn, {len(desc_too_long)} quá dài (chuẩn {DESC_MIN}–{DESC_MAX}).",
            n,
            "Chỉnh description về 50–160 ký tự.",
        )
    if slug_too_long:
        add_action(
            "P2", "SEO",
            "Rút ngắn slug quá dài",
            f"{len(slug_too_long)} slug > {SLUG_MAX} ký tự.",
            len(slug_too_long),
            "Rút gọn slug (report-only — đổi slug cần redirect).",
        )
    if slug_stop_words:
        add_action(
            "P2", "SEO",
            "Slug chứa stop words (report-only)",
            f"{len(slug_stop_words)} slug chứa stop words tiếng Việt.",
            len(slug_stop_words),
            "Ghi nhận; chỉ đổi slug khi refactor có redirect.",
        )

    thin = [p for p in posts if p["word_count"] < 300]
    if thin:
        add_action(
            "P0", "Content",
            "Mở rộng thin posts",
            f"{len(thin)} bài dưới 300 từ.",
            len(thin),
            "Bổ sung nội dung thực tế, so sánh, FAQ nếu phù hợp.",
        )

    missing_cat = [p for p in posts if not p["categories"]]
    if missing_cat:
        add_action(
            "P1", "Content",
            "Gán category cho bài thiếu",
            f"{len(missing_cat)} bài không có categories.",
            len(missing_cat),
            "Thêm categories trong front matter.",
        )

    if posts_missing_il:
        add_action(
            "P1", "Internal Linking",
            "Thêm internal links cho bài thiếu outbound",
            f"{len(posts_missing_il)} bài không có internal link outbound (MD/FM/graph).",
            len(posts_missing_il),
            "Chèn 2–5 internal links liên quan trong thân bài hoặc graph.",
        )
    if orphan_posts:
        add_action(
            "P1", "Internal Linking",
            "Giảm orphan posts (không có inbound)",
            f"{len(orphan_posts)} bài không nhận internal link.",
            len(orphan_posts),
            "Link tới orphan từ bài hub/pillar cùng cluster.",
        )

    if old_posts:
        add_action(
            "P1", "Freshness",
            "Cập nhật bài cũ (>365 ngày)",
            f"{len(old_posts)} bài đã cũ hơn 1 năm.",
            len(old_posts),
            "Refresh số liệu, lastmod, bổ sung section mới.",
        )

    if content_gaps:
        add_action(
            "P2", "Content",
            "Lấp content gaps / thiếu pillar",
            f"{len(content_gaps)} khoảng trống nội dung được phát hiện.",
            len(content_gaps),
            "Viết pillar hoặc mở rộng category/cluster yếu.",
        )

    if warnings_list:
        add_action(
            "P2", "Technical",
            "Sửa bài parse front matter lỗi / cảnh báo",
            f"{len(warnings_list)} cảnh báo khi scan posts.",
            len(warnings_list),
            "Kiểm tra front matter YAML/TOML của các file bị cảnh báo.",
        )

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    action_items.sort(key=lambda a: (priority_order.get(a["priority"], 9), a["type"], a["title"]))

    report = {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "summary": {
            "total_posts": total,
            "draft_posts": len(draft_posts),
            "total_words": total_words,
            "average_words_per_post": avg_words,
            "categories_count": len(cat_counter),
            "tags_count": len(tag_counter),
            "authors_count": len(author_counter),
            "parse_warnings": len(warnings_list),
        },
        "categories": categories,
        "authors": authors,
        "tags_top": [{"name": n, "count": c} for n, c in tag_counter.most_common(20)],
        "time": {
            "oldest": oldest.isoformat() if oldest else "",
            "oldest_display": format_vietnam_datetime(oldest) if oldest else "",
            "newest": newest.isoformat() if newest else "",
            "newest_display": format_vietnam_datetime(newest) if newest else "",
        },
        "seo": {
            "title_too_short": title_too_short,
            "title_too_long": title_too_long,
            "description_missing": desc_missing,
            "description_too_short": desc_too_short,
            "description_too_long": desc_too_long,
            "slug_too_long": slug_too_long,
            "slug_stop_words": slug_stop_words,
        },
        "freshness": {
            "average_age_days": round(sum(ages) / len(ages)) if ages else 0,
            "old_posts_over_365_days": old_posts,
            "new_posts_under_30_days": new_posts,
        },
        "internal_linking": {
            "total_outbound_links": sum(outbound_counts.values()),
            "average_outbound_per_post": round(
                sum(outbound_counts.values()) / total, 2
            ) if total else 0,
            "top_linked_posts": top_linked,
            "orphan_posts": orphan_posts,
            "posts_missing_internal_links": posts_missing_il,
        },
        "content_gaps": content_gaps,
        "action_items": action_items,
        "warnings": warnings_list[:50],
    }
    return report


def generate_md(report: dict) -> str:
    s = report["summary"]
    w: list[str] = []
    w.append("# Báo cáo Content Direction\n")
    w.append(f"_Tạo lúc: {report['generated_at_display']}_\n")
    w.append("## 1. Tổng quan\n")
    w.append(f"- **Tổng số bài viết:** {s['total_posts']}")
    w.append(f"- **Bài nháp:** {s['draft_posts']}")
    w.append(f"- **Tổng số từ:** {s['total_words']:,}")
    w.append(f"- **Trung bình từ/bài:** {s['average_words_per_post']:,}")
    w.append(f"- **Số danh mục:** {s['categories_count']}")
    w.append(f"- **Số tags:** {s['tags_count']}")
    w.append(f"- **Số tác giả:** {s['authors_count']}")
    t = report["time"]
    w.append(f"- **Bài cũ nhất:** {t.get('oldest_display') or '—'}")
    w.append(f"- **Bài mới nhất:** {t.get('newest_display') or '—'}")
    w.append("\n## 2. Danh mục\n")
    for c in report["categories"]:
        w.append(f"- {c['name']}: {c['count']} bài")
    w.append("\n## 3. Tác giả\n")
    for a in report["authors"]:
        w.append(f"- {a['name']}: {a['count']} bài")
    fr = report["freshness"]
    w.append("\n## 4. Freshness\n")
    w.append(f"- Tuổi TB: {fr['average_age_days']} ngày")
    w.append(f"- Bài >365 ngày: {len(fr['old_posts_over_365_days'])}")
    w.append(f"- Bài <30 ngày: {len(fr['new_posts_under_30_days'])}")
    seo = report["seo"]
    w.append("\n## 5. SEO\n")
    w.append(f"- Title quá ngắn: {len(seo['title_too_short'])}")
    w.append(f"- Title quá dài: {len(seo['title_too_long'])}")
    w.append(f"- Thiếu description: {len(seo['description_missing'])}")
    w.append(f"- Slug stop words: {len(seo['slug_stop_words'])}")
    il = report["internal_linking"]
    w.append("\n## 6. Internal Linking\n")
    w.append(f"- Outbound links: {il['total_outbound_links']}")
    w.append(f"- TB outbound/bài: {il['average_outbound_per_post']}")
    w.append(f"- Orphan: {len(il['orphan_posts'])}")
    w.append(f"- Thiếu outbound: {len(il['posts_missing_internal_links'])}")
    w.append("\n## 7. Content Gaps\n")
    if report["content_gaps"]:
        for g in report["content_gaps"]:
            w.append(f"- [{g['type']}] {g['detail']}")
    else:
        w.append("- Không có gap lớn.")
    w.append("\n## 8. Action Items\n")
    for item in report["action_items"]:
        w.append(
            f"- **[{item['priority']}] [{item['type']}]** {item['title']} "
            f"(affected={item['affected_count']})"
        )
        w.append(f"  - {item['detail']}")
        w.append(f"  - Fix: {item['suggested_fix']}")
    if report.get("warnings"):
        w.append("\n## Warnings\n")
        for msg in report["warnings"][:20]:
            w.append(f"- {msg}")
    w.append("")
    return "\n".join(w)


def validate_report(report: dict) -> list[str]:
    errors = []
    if not isinstance(report, dict):
        return ["report is not an object"]
    if "generated_at" not in report:
        errors.append("missing generated_at")
    display = report.get("generated_at_display") or ""
    if not re.match(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$", display):
        errors.append(f"generated_at_display invalid: {display!r}")
    summary = report.get("summary") or {}
    total = int(summary.get("total_posts") or 0)
    words = int(summary.get("total_words") or 0)
    if total <= 0:
        errors.append("summary.total_posts must be > 0")
    if words <= 0:
        errors.append("summary.total_words must be > 0")
    if "action_items" not in report or not isinstance(report["action_items"], list):
        errors.append("action_items must be a list")
    if "image_attribution_risk" in report:
        errors.append("image_attribution_risk must not be present in Content Direction")
    return errors


def write_report(report: dict, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Written JSON: {json_path}")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_md(report))
    print(f"Written MD: {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Content Direction Report")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON output path")
    parser.add_argument("--md", default=str(DEFAULT_MD), help="Markdown output path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate existing data/content-direction.json (no regenerate)",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow writing empty report when 0 posts found (default: refuse overwrite)",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero if any P0 action items",
    )
    args = parser.parse_args()
    json_path = Path(args.json)
    md_path = Path(args.md)

    if args.check:
        if not json_path.exists():
            print(f"ERROR: missing {json_path}", file=sys.stderr)
            return 1
        report = load_json(json_path)
        errors = validate_report(report)
        if errors:
            for e in errors:
                print(f"CHECK FAIL: {e}", file=sys.stderr)
            return 1
        s = report["summary"]
        print(
            f"CHECK OK — posts={s['total_posts']} words={s['total_words']} "
            f"actions={len(report.get('action_items') or [])}"
        )
        return 0

    if not CONTENT_DIR.is_dir():
        print(f"ERROR: posts directory missing: {CONTENT_DIR}", file=sys.stderr)
        return 1

    posts, drafts, warnings_list = analyze_posts()
    for msg in warnings_list:
        print(f"WARN: {msg}", file=sys.stderr)

    if not posts:
        print(
            "ERROR: scanned 0 published posts under content/posts/**/*.md — refusing empty report",
            file=sys.stderr,
        )
        if args.allow_empty:
            empty = compute_report([], drafts, warnings_list)
            write_report(empty, json_path, md_path)
            print("Wrote empty report because --allow-empty was set")
            return 1
        # Do not overwrite existing valid JSON
        if json_path.exists():
            existing = load_json(json_path)
            prev = (existing.get("summary") or {}).get("total_posts")
            print(
                f"Preserved existing report (previous total_posts={prev})",
                file=sys.stderr,
            )
        return 2

    report = compute_report(posts, drafts, warnings_list)
    errors = validate_report(report)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    write_report(report, json_path, md_path)
    s = report["summary"]
    p0 = [a for a in report["action_items"] if a["priority"] == "P0"]
    print(
        f"Report OK — posts={s['total_posts']} words={s['total_words']} "
        f"categories={s['categories_count']} authors={s['authors_count']} "
        f"actions={len(report['action_items'])} (P0={len(p0)}) warnings={len(warnings_list)}"
    )
    if args.fail_on_critical and p0:
        print(f"Found {len(p0)} P0 action items — failing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
