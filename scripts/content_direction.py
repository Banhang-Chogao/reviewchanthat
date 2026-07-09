#!/usr/bin/env python3
"""Content Direction Report — automated SEO/content direction audit.

Usage:
  python scripts/content_direction.py
  python scripts/content_direction.py --json data/content-direction.json --md reports/content-direction-report.md
  python scripts/content_direction.py --fail-on-critical
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import format_vietnam_datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_JSON = DATA_DIR / "content-direction.json"
DEFAULT_MD = REPORTS_DIR / "content-direction-report.md"


def load_json(rel_path):
    path = DATA_DIR / rel_path
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def parse_post(md_file):
    try:
        post = frontmatter.load(md_file)
    except Exception:
        return None
    fm = post.metadata
    if not fm.get("title"):
        return None
    body = post.content or ""
    wc = len(body.split())
    slug = md_file.stem
    return {
        "slug": slug,
        "path": str(md_file.relative_to(REPO_ROOT)),
        "title": fm.get("title", ""),
        "date": str(fm.get("date", "")),
        "lastmod": str(fm.get("lastmod", fm.get("date", ""))),
        "draft": fm.get("draft", False),
        "categories": fm.get("categories") or [],
        "tags": fm.get("tags") or [],
        "author": fm.get("author", ""),
        "description": fm.get("description", ""),
        "word_count": wc,
        "internal_links": list(fm.get("internal_links") or []),
        "has_faq": bool(fm.get("faq")),
        "image": str(fm.get("image", "")),
        "image_source": str(fm.get("image_source", "")),
        "noindex": fm.get("noindex", False),
    }


def analyze_posts():
    posts = []
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        p = parse_post(md_file)
        if p:
            posts.append(p)
    return posts


def compute_overview(posts):
    total = len(posts)
    total_words = sum(p["word_count"] for p in posts)
    categories = Counter()
    authors = Counter()
    dates = []
    for p in posts:
        for cat in p["categories"]:
            categories[cat] += 1
        if p["author"]:
            authors[p["author"]] += 1
        try:
            d = datetime.fromisoformat(p["date"].replace("Z", "+00:00"))
            dates.append(d)
        except (ValueError, TypeError):
            pass
    return {
        "total_posts": total,
        "total_words": total_words,
        "avg_words": round(total_words / total) if total else 0,
        "categories": dict(categories.most_common()),
        "authors": dict(authors.most_common()),
        "date_range": {
            "first": min(dates).strftime("%d-%m-%Y %H:%M:%S") if dates else "",
            "latest": max(dates).strftime("%d-%m-%Y %H:%M:%S") if dates else "",
        },
        "draft_count": sum(1 for p in posts if p["draft"]),
    }


def compute_organic_search(ga4_data):
    result = {"ga4_data_available": bool(ga4_data)}
    if ga4_data:
        result["total_users"] = ga4_data.get("totals", {}).get("total_users", 0)
        result["total_sessions"] = ga4_data.get("totals", {}).get("total_sessions", 0)
        result["period_days"] = ga4_data.get("period_days", 28)
        top_pages = ga4_data.get("top_pages", [])
        result["top_pages_count"] = len(top_pages)
        if top_pages:
            result["top_pages"] = [
                {"title": p.get("page_title", ""), "url": p.get("page_url", ""), "sessions": p.get("sessions", 0)}
                for p in top_pages[:10]
            ]
    return result


def compute_seo(posts):
    desc = {"total": len(posts), "missing": 0, "short": 0, "long": 0, "good": 0}
    title_stats = {"total": len(posts), "too_short": 0, "good": 0, "too_long": 0}
    slug_issues = []
    faq_count = 0
    for p in posts:
        d = p.get("description", "")
        dl = len(d)
        if not d:
            desc["missing"] += 1
        elif dl < 50:
            desc["short"] += 1
        elif dl > 160:
            desc["long"] += 1
        else:
            desc["good"] += 1
        tl = len(p.get("title", ""))
        if tl < 30:
            title_stats["too_short"] += 1
        elif tl > 60:
            title_stats["too_long"] += 1
        else:
            title_stats["good"] += 1
        slug = p.get("slug", "")
        stop_words = {"ve", "la", "cua", "va", "hoac", "de", "cho", "voi", "the", "nay", "do", "mot", "co", "duoc"}
        slug_parts = slug.replace("-", " ").split()
        found = [w for w in slug_parts if w in stop_words]
        if found:
            slug_issues.append({"slug": slug, "reason": f"contains stop words: {', '.join(found)}"})
        if p.get("has_faq"):
            faq_count += 1
    return {
        "meta_descriptions": desc,
        "title_tags": title_stats,
        "slug_issues": slug_issues,
        "faq_present": faq_count,
        "posts_with_schema": len(posts),
    }


def compute_adsense_compliance(posts, compliance_data):
    if not compliance_data:
        return {"total_violations": 0, "clean_posts": len(posts)}
    violations = compliance_data.get("violations") or []
    restricted = []
    copyright_issues = []
    tone_issues = []
    other = []
    for v in violations:
        cat = v.get("category", "")
        if cat == "restricted_content":
            restricted.append(v)
        elif cat == "copyright":
            copyright_issues.append(v)
        elif cat == "tone":
            tone_issues.append(v)
        else:
            other.append(v)
    slug_set = {v.get("post") for v in violations}
    return {
        "total_violations": len(violations),
        "restricted_content": restricted,
        "copyright_issues": copyright_issues,
        "tone_issues": tone_issues,
        "other_violations": other,
        "clean_posts": sum(1 for p in posts if p["slug"] not in slug_set),
    }


def compute_content_quality(posts):
    wc_dist = {"<300": 0, "300-800": 0, "800-1500": 0, "1500-3000": 0, ">3000": 0}
    thin_posts = []
    for p in posts:
        wc = p["word_count"]
        if wc < 300:
            wc_dist["<300"] += 1
            thin_posts.append({"slug": p["slug"], "title": p["title"], "words": wc})
        elif wc < 800:
            wc_dist["300-800"] += 1
        elif wc < 1500:
            wc_dist["800-1500"] += 1
        elif wc < 3000:
            wc_dist["1500-3000"] += 1
        else:
            wc_dist[">3000"] += 1
    return {
        "word_count_distribution": wc_dist,
        "thin_posts": thin_posts,
        "avg_word_count": round(sum(p["word_count"] for p in posts) / len(posts)) if posts else 0,
        "missing_description": sum(1 for p in posts if not p.get("description")),
        "missing_image": sum(1 for p in posts if not p.get("image")),
        "missing_faq": sum(1 for p in posts if not p.get("has_faq")),
    }


def _extract_link(link):
    if isinstance(link, str):
        return os.path.splitext(os.path.basename(link))[0]
    if isinstance(link, dict):
        for key in ("ref", "url", "link", "href", "slug", "path"):
            val = link.get(key)
            if val and isinstance(val, str):
                return os.path.splitext(os.path.basename(val))[0]
        return str(link.get("url", ""))
    return str(link)


def compute_internal_linking(posts):
    all_links = []
    link_counter = Counter()
    for p in posts:
        links = p.get("internal_links") or []
        normalized = [_extract_link(l) for l in links]
        all_links.extend(normalized)
        for link in normalized:
            link_counter[link] += 1
    linked_slugs = set()
    for link in all_links:
        link_slug = os.path.splitext(os.path.basename(link))[0]
        linked_slugs.add(link_slug)
    all_slugs = {p["slug"] for p in posts}
    orphans = [p for p in posts if p["slug"] not in linked_slugs and not p["draft"]]
    top_linked = []
    for slug, count in link_counter.most_common(10):
        match = next((p for p in posts if p["slug"] == slug), None)
        if match:
            top_linked.append({"slug": slug, "title": match["title"], "links": count})
    return {
        "total_internal_links": len(all_links),
        "avg_per_post": round(len(all_links) / len(posts), 2) if posts else 0,
        "posts_with_links": sum(1 for p in posts if p.get("internal_links")),
        "posts_without_links": sum(1 for p in posts if not p.get("internal_links")),
        "orphan_posts": [{"slug": p["slug"], "title": p["title"]} for p in orphans],
        "orphan_count": len(orphans),
        "top_linked_posts": top_linked,
    }


def compute_freshness(posts):
    now = datetime.now(timezone.utc)
    stale = []
    recent = []
    ages = []
    for p in posts:
        try:
            pub = datetime.fromisoformat(p["date"].replace("Z", "+00:00"))
            last = datetime.fromisoformat(p.get("lastmod", p["date"]).replace("Z", "+00:00"))
            age = (now - pub).days
            ages.append(age)
            if age > 365:
                stale.append({"slug": p["slug"], "title": p["title"], "age_days": age, "lastmod": p.get("lastmod")})
            elif age < 30:
                recent.append({"slug": p["slug"], "title": p["title"], "age_days": age})
        except (ValueError, TypeError):
            pass
    return {
        "avg_age_days": round(sum(ages) / len(ages)) if ages else 0,
        "oldest_post_days": max(ages) if ages else 0,
        "newest_post_days": min(ages) if ages else 0,
        "stale_posts": stale,
        "stale_count": len(stale),
        "recent_posts": recent,
        "recent_count": len(recent),
        "total_posts_analyzed": len(ages),
    }


def compute_image_risk(posts, audit_data):
    source_counter = Counter()
    missing = []
    for p in posts:
        src = p.get("image_source", "")
        if src:
            source_counter[src] += 1
        if p.get("image") and not src:
            missing.append({"slug": p["slug"], "title": p["title"]})
    dedup_issues = []
    if audit_data:
        dedup_issues = (
            audit_data.get("duplicates")
            or audit_data.get("dedup_issues")
            or audit_data.get("errors")
            or []
        )
        if not isinstance(dedup_issues, list):
            dedup_issues = list(dedup_issues) if dedup_issues else []
    return {
        "total_images": sum(1 for p in posts if p.get("image")),
        "by_source": dict(source_counter.most_common()),
        "missing_credit_posts": missing,
        "missing_credit_count": len(missing),
        "dedup_issues": dedup_issues[:20] if dedup_issues else [],
        "dedup_count": len(dedup_issues),
    }


def generate_action_items(seo, quality, adsense, linking, freshness, image):
    items = []
    if seo["meta_descriptions"]["missing"]:
        items.append({
            "priority": "high", "area": "SEO",
            "title": "Thêm meta description cho bài viết thiếu",
            "detail": f"{seo['meta_descriptions']['missing']} bài chưa có meta description.",
        })
    if seo["title_tags"]["too_short"] or seo["title_tags"]["too_long"]:
        items.append({
            "priority": "medium", "area": "SEO",
            "title": "Tối ưu độ dài title tag",
            "detail": f"{seo['title_tags']['too_short']} title quá ngắn, {seo['title_tags']['too_long']} title quá dài (chuẩn: 50-60 ký tự).",
        })
    if seo["slug_issues"]:
        items.append({
            "priority": "low", "area": "SEO",
            "title": "Tối ưu slug loại bỏ stop words",
            "detail": f"{len(seo['slug_issues'])} slug chứa stop words tiếng Việt.",
        })
    if quality["thin_posts"]:
        items.append({
            "priority": "high", "area": "Content",
            "title": "Mở rộng thin posts",
            "detail": f"{len(quality['thin_posts'])} bài dưới 300 từ cần mở rộng nội dung.",
        })
    if quality["missing_description"]:
        items.append({
            "priority": "high", "area": "Content",
            "title": "Thêm description cho bài thiếu",
            "detail": f"{quality['missing_description']} bài chưa có description.",
        })
    if quality["missing_image"]:
        items.append({
            "priority": "medium", "area": "Content",
            "title": "Thêm hero image cho bài viết",
            "detail": f"{quality['missing_image']} bài chưa có hero image.",
        })
    if adsense.get("restricted_content"):
        items.append({
            "priority": "high", "area": "AdSense",
            "title": "Xử lý nội dung vi phạm chính sách AdSense",
            "detail": f"{len(adsense['restricted_content'])} vi phạm restricted content.",
        })
    if linking["orphan_count"]:
        items.append({
            "priority": "medium", "area": "Internal Linking",
            "title": "Bổ sung internal links cho orphan posts",
            "detail": f"{linking['orphan_count']} bài không có internal link trỏ đến.",
        })
    if linking["posts_without_links"]:
        items.append({
            "priority": "medium", "area": "Internal Linking",
            "title": "Thêm internal links cho bài thiếu",
            "detail": f"{linking['posts_without_links']} bài chưa có internal links trong front matter.",
        })
    if freshness["stale_count"]:
        items.append({
            "priority": "medium", "area": "Freshness",
            "title": "Cập nhật bài viết cũ (>365 ngày)",
            "detail": f"{freshness['stale_count']} bài đã cũ hơn 1 năm, cần cập nhật.",
        })
    if image["missing_credit_count"]:
        items.append({
            "priority": "high", "area": "Images",
            "title": "Gán image_source cho bài thiếu",
            "detail": f"{image['missing_credit_count']} bài thiếu thông tin nguồn ảnh.",
        })
    if image["dedup_count"]:
        items.append({
            "priority": "medium", "area": "Images",
            "title": "Xử lý ảnh trùng lặp",
            "detail": f"{image['dedup_count']} vấn đề trùng lặp ảnh.",
        })
    return items


def generate_md(report):
    w = []
    w.append("# Báo cáo Content Direction\n")
    w.append(f"_Tạo lúc: {report['generated_at']}_\n")
    o = report["overview"]
    w.append("## 1. Tổng quan\n")
    w.append(f"- **Tổng số bài viết:** {o['total_posts']}")
    w.append(f"- **Tổng số từ:** {o['total_words']:,}")
    w.append(f"- **Trung bình từ/bài:** {o['avg_words']:,}")
    w.append(f"- **Số bài nháp:** {o['draft_count']}")
    w.append(f"- **Ngày đầu:** {o['date_range']['first']}")
    w.append(f"- **Ngày mới nhất:** {o['date_range']['latest']}")
    w.append("\n**Danh mục:**\n")
    for cat, count in o["categories"].items():
        w.append(f"- {cat}: {count} bài")
    w.append("\n**Tác giả:**\n")
    for a, c in o["authors"].items():
        w.append(f"- {a}: {c} bài")
    w.append("")
    s = report["google_seo"]
    w.append("## 2. Google SEO\n")
    w.append(f"- **Meta descriptions:** {s['meta_descriptions']['good']}/{s['meta_descriptions']['total']} đạt chuẩn, {s['meta_descriptions']['missing']} thiếu, {s['meta_descriptions']['short']} quá ngắn, {s['meta_descriptions']['long']} quá dài.")
    w.append(f"- **Title tags:** {s['title_tags']['good']}/{s['title_tags']['total']} đạt chuẩn, {s['title_tags']['too_short']} quá ngắn, {s['title_tags']['too_long']} quá dài.")
    w.append(f"- **Slug issues:** {len(s['slug_issues'])} slug có vấn đề.")
    w.append(f"- **FAQ present:** {s['faq_present']} bài có FAQ schema.")
    w.append("")
    q = report["content_quality"]
    w.append("## 3. Chất lượng nội dung\n")
    w.append(f"- Trung bình: {q['avg_word_count']:,} từ/bài")
    w.append(f"- Thiếu description: {q['missing_description']} bài")
    w.append(f"- Thiếu hero image: {q['missing_image']} bài")
    w.append(f"- Thiếu FAQ: {q['missing_faq']} bài")
    w.append("\n**Phân bố word count:**\n")
    for bucket, count in q["word_count_distribution"].items():
        w.append(f"- {bucket} từ: {count} bài")
    if q["thin_posts"]:
        w.append("\n**Thin posts (<300 từ):**\n")
        for p in q["thin_posts"]:
            w.append(f"- [{p['slug']}] {p['title']} ({p['words']} từ)")
    w.append("")
    ads = report["adsense_compliance"]
    if ads.get("total_violations"):
        w.append("## 4. AdSense Compliance\n")
        w.append(f"- Tổng vi phạm: {ads['total_violations']}")
        w.append(f"- Bài sạch: {ads['clean_posts']}/{o['total_posts']}")
        w.append("")
    a = report["action_items"]
    if a:
        w.append("## 5. Action Items\n")
        for item in a:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["priority"], "⚪")
            w.append(f"- {icon} **[{item['priority'].upper()}] [{item['area']}]** {item['title']}")
            w.append(f"  - {item['detail']}")
        w.append("")
    return "\n".join(w)


def main():
    parser = argparse.ArgumentParser(description="Content Direction Report")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON output path")
    parser.add_argument("--md", default=str(DEFAULT_MD), help="Markdown output path")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit non-zero if critical issues")
    args = parser.parse_args()
    json_path = Path(args.json)
    md_path = Path(args.md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    posts = analyze_posts()
    if not posts:
        print("No posts found — exiting")
        sys.exit(0)
    compliance_data = load_json("compliance-report.json")
    ga4_data = load_json("ga4_footer.json")
    audit_data = load_json("image-audit-report.json")
    now_dt = datetime.now(timezone.utc)
    report = {
        "generated_at": now_dt.isoformat(),
        "generated_at_display": format_vietnam_datetime(now_dt),
        "overview": compute_overview(posts),
        "organic_search_direction": compute_organic_search(ga4_data),
        "google_seo": compute_seo(posts),
        "adsense_compliance": compute_adsense_compliance(posts, compliance_data),
        "content_quality": compute_content_quality(posts),
        "internal_linking": compute_internal_linking(posts),
        "freshness": compute_freshness(posts),
        "image_attribution_risk": compute_image_risk(posts, audit_data),
    }
    report["action_items"] = generate_action_items(
        report["google_seo"],
        report["content_quality"],
        report["adsense_compliance"],
        report["internal_linking"],
        report["freshness"],
        report["image_attribution_risk"],
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Written JSON: {json_path}")
    md_content = generate_md(report)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Written MD: {md_path}")
    critical = [a for a in report["action_items"] if a["priority"] == "high"]
    print(f"Report generated — {len(critical)} high-priority action items")
    if args.fail_on_critical and critical:
        print(f"Found {len(critical)} critical action items — failing")
        sys.exit(1)


if __name__ == "__main__":
    main()
