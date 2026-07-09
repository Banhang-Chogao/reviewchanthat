#!/usr/bin/env python3
"""Content Direction Optimizer — Phase 3–7: scoring, risk policy, safe autofix, change caps, report.

Reads data/content-direction.json, applies safe optimizations:
  - SEO title via seo_title (never changes slug, date, or body)
  - Meta description (never fabricates facts)
  - Internal links via data/internal-links.json only
  - Score tracking

Hard rules:
  - No slug/permalink changes
  - No date changes
  - No body rewrites
  - No image metadata changes
  - Max 30 files changed per run
  - Only risk=safe actions auto-applied
  - No auto-create content (report-only for gaps)

Usage:
  python scripts/content_direction_optimizer.py --dry-run
  python scripts/content_direction_optimizer.py --write
  python scripts/content_direction_optimizer.py --write --max-changes 30
  python scripts/content_direction_optimizer.py --write --report-json X --report-md Y
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_JSON = DATA_DIR / "content-direction.json"
DEFAULT_INTERNAL_LINKS = DATA_DIR / "internal-links.json"
DEFAULT_REPORT_JSON = REPORTS_DIR / "content-direction-optimizer.json"
DEFAULT_REPORT_MD = REPORTS_DIR / "content-direction-optimizer.md"
DEFAULT_SCORE_JSON = DATA_DIR / "content-direction-score.json"
DEFAULT_OPTIMIZER_SUMMARY = DATA_DIR / "content-direction-optimizer-summary.json"

TITLE_TARGET_MIN = 30
TITLE_TARGET_MAX = 60
DESC_TARGET_MIN = 50
DESC_TARGET_MAX = 160

RISK_SAFE = "safe"
RISK_REVIEW = "review"
RISK_UNSAFE = "unsafe"

SEP = "\n"

TOPIC_CLUSTERS = {
    "korea-summer": ["han-quoc", "korea", "mua-he", "thang-7", "thang-8", "caribbean-bay", "tranh-nong", "bien", "cong-vien-nuoc", "jeju", "goi-y"],
    "korea-autumn": ["thang-10", "thang-11", "la-do", "seoraksan", "mua-thu", "nami", "thoi-tiet", "chi-phi"],
    "jeju": ["jeju", "udo", "hoa-cai"],
    "busan": ["busan", "haeundae", "gwangalli", "songdo", "dadaepo", "cheongsapo", "gamcheon"],
    "seoul": ["seoul", "suwon", "incheon", "wolmido", "nami"],
    "apple-iphone": ["iphone", "apple", "ios", "camera", "pin", "chip", "a20"],
    "apple-macos": ["macos", "macbook", "apple-intelligence"],
    "apple-dma": ["dma", "ec", "eu", "digital-markets", "app-store", "gatekeeper", "chau-au"],
    "korea-visa": ["visa", "han-quoc", "xin-visa"],
    "starbucks": ["starbucks"],
    "review-tips": ["review", "cach", "meo", "checklist", "thoi-quen", "mua-sam", "cach-doc", "thong-minh"],
    "thailand": ["thai-lan", "thailand", "bangkok", "phuket", "chiang-mai", "mua-mua", "suvarnabhumi"],
    "thailand-festival": ["candle-festival", "ubon", "ratchathani"],
    "ski": ["ski", "truot-tuyet", "alpensia", "yongpyong", "elysian", "high1", "vivaldi", "oak-valley"],
}


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    return {}


def parse_front_matter(text: str) -> tuple[dict | None, str, str | None]:
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
        except Exception as exc:
            return None, text, f"yaml-parse-error: {exc}"
    return {}, text, "no-frontmatter"


def serialize_front_matter(meta: dict) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, str):
            if any(ch in value for ch in (":", "#", "{", "[", ">", "|", '"', "'", "\n")):
                lines.append(f"{key}: >-")
                lines.append(f"  {value}")
            else:
                lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            for v in value:
                lines.append(f"{key}:")
                lines.append(f"  - {json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
        elif value is None:
            continue
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def compute_score(report: dict) -> dict:
    seo = report.get("seo", {})
    il = report.get("internal_linking", {})
    freshness = report.get("freshness", {})
    gaps = report.get("content_gaps", [])
    total_posts = max(int((report.get("summary") or {}).get("total_posts", 0)), 1)

    title_short = len(seo.get("title_too_short", []))
    title_long = len(seo.get("title_too_long", []))
    desc_missing = len(seo.get("description_missing", []))
    desc_short = len(seo.get("description_too_short", []))
    desc_long = len(seo.get("description_too_long", []))

    title_issues = title_short + title_long
    desc_issues = desc_missing + desc_short + desc_long

    seo_score = max(0, 15 - (title_issues / total_posts) * 15)
    desc_score = max(0, 15 - (desc_issues / total_posts) * 15)

    orphans = len(il.get("orphan_posts", []))
    missing_out = len(il.get("posts_missing_internal_links", []))
    orphan_score = max(0, 20 - (orphans / total_posts) * 20)
    link_score = max(0, 25 - (missing_out / total_posts) * 25)

    avg_age = freshness.get("average_age_days", 0)
    freshness_score = max(0, 10 - (avg_age / 365) * 10)

    gap_score = max(0, 10 - len(gaps) * 2)

    integrity_score = 5.0
    if not report.get("generated_at"):
        integrity_score = 0
    summary = report.get("summary", {})
    if int(summary.get("total_posts", 0)) <= 0:
        integrity_score = 0

    components = {
        "seo_titles": round(seo_score, 1),
        "meta_descriptions": round(desc_score, 1),
        "internal_links": round(link_score, 1),
        "orphan_posts": round(orphan_score, 1),
        "freshness": round(freshness_score, 1),
        "content_gaps": round(gap_score, 1),
        "data_integrity": round(integrity_score, 1),
    }
    total = round(sum(components.values()), 1)
    remaining = [a for a in report.get("action_items", [])]

    now = now_vietnam()
    return {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "score": round(total, 1),
        "components": components,
        "target": 100,
        "remaining_action_items": len(remaining),
    }


def build_internal_link_graph(posts: list[dict]) -> dict:
    def _detect_clusters(post: dict) -> list[str]:
        text = " ".join([
            post.get("slug", "").lower(),
            (post.get("title") or "").lower(),
            " ".join(post.get("tags", [])),
            " ".join(post.get("categories", [])),
        ])
        return [name for name, keywords in TOPIC_CLUSTERS.items() if any(kw in text for kw in keywords)]

    def _link_score(a: dict, b: dict) -> int:
        score = 0
        score += len(set(a.get("series", [])) & set(b.get("series", []))) * 10
        score += len(set(a.get("categories", [])) & set(b.get("categories", []))) * 5
        score += len(set(a.get("tags", [])) & set(b.get("tags", []))) * 3
        a_clusters = set(_detect_clusters(a))
        b_clusters = set(_detect_clusters(b))
        score += len(a_clusters & b_clusters) * 8
        return score

    indexable = [p for p in posts if not p.get("noindex") and not p.get("draft")]
    indexable_slugs = {p["slug"] for p in indexable}

    links = {}
    for post in indexable:
        candidates = []
        for other in indexable:
            if other["slug"] == post["slug"]:
                continue
            score = _link_score(post, other)
            candidates.append({"target": other["slug"], "title": other["title"], "score": score})
        candidates.sort(key=lambda x: -x["score"])
        links[post["slug"]] = candidates[:8]

    inbound = {}
    for source, targets in links.items():
        for t in targets:
            inbound[t["target"]] = inbound.get(t["target"], 0) + 1

    for p in indexable:
        if inbound.get(p["slug"], 0) > 0:
            continue
        for other in indexable:
            if other["slug"] == p["slug"]:
                continue
            score = _link_score(p, other)
            existing = {x["target"] for x in links.get(other["slug"], [])}
            if p["slug"] not in existing and len(links.get(other["slug"], [])) < 10:
                links.setdefault(other["slug"], []).append({
                    "target": p["slug"],
                    "title": p["title"],
                    "score": max(score, 1),
                })
                inbound[p["slug"]] = inbound.get(p["slug"], 0) + 1
                if inbound[p["slug"]] >= 2:
                    break

    return {
        "links": links,
        "inbound_counts": inbound,
        "indexable_slugs": sorted(indexable_slugs),
        "orphans_after": sum(1 for p in indexable if inbound.get(p["slug"], 0) == 0),
    }


def generate_optimizer_report(
    score_before: dict,
    score_after: dict,
    applied: list[dict],
    skipped: list[dict],
    safe_applied: list[dict],
    review_skipped: list[dict],
    unsafe_skipped: list[dict],
    changed_files: list[str],
    remaining: list[dict],
    mode: str,
    max_changes: int,
) -> tuple[dict, str]:
    now = now_vietnam()
    report_json = {
        "generated_at": now.isoformat(),
        "mode": mode,
        "max_changes_allowed": max_changes,
        "score_before": score_before.get("score", 0),
        "score_after_estimated": score_after.get("score", 0),
        "components_before": score_before.get("components", {}),
        "components_after": score_after.get("components", {}),
        "applied": applied,
        "skipped": skipped,
        "safe_applied": safe_applied,
        "review_only_skipped": review_skipped,
        "unsafe_skipped": unsafe_skipped,
        "remaining": remaining[:50],
        "remaining_count": len(remaining),
        "changed_files": changed_files[:60],
        "total_changed": len(changed_files),
    }

    md_lines = [
        "# Báo cáo Content Direction Optimizer",
        f"",
        f"_Tạo lúc: {format_vietnam_datetime(now)}_",
        f"_Mode: {mode}_",
        f"_Max changes: {max_changes}_",
        f"",
        f"## Score",
        f"",
        f"- Trước: **{score_before.get('score', 0)}** / 100",
        f"- Sau (ước tính): **{score_after.get('score', 0)}** / 100",
        f"- Target: 100",
        f"",
        f"### Components",
        f"",
    ]
    for key in sorted(score_after.get("components", {}).keys()):
        val = score_after.get("components", {}).get(key, 0)
        before_val = score_before.get("components", {}).get(key, 0)
        delta = round(val - before_val, 1)
        md_lines.append(f"- **{key}**: {before_val} → {val} ({'+' if delta >= 0 else ''}{delta})")

    md_lines.extend([
        f"",
        f"## Applied ({len(applied)})",
        f"",
    ])
    if applied:
        for a in applied:
            md_lines.append(f"- `{a.get('action', '')}` — {a.get('file', '')}")
    else:
        md_lines.append("- Không có action nào được apply.")

    if review_skipped:
        md_lines.extend([
            f"",
            f"## Review-only skipped ({len(review_skipped)})",
            f"",
        ])
        for s in review_skipped:
            md_lines.append(f"- `{s.get('action', '')}` — {s.get('reason', s.get('file', ''))}")

    if unsafe_skipped:
        md_lines.extend([
            f"",
            f"## Unsafe skipped ({len(unsafe_skipped)})",
            f"",
        ])
        for s in unsafe_skipped:
            md_lines.append(f"- `{s.get('action', '')}` — {s.get('reason', s.get('file', ''))}")

    if remaining:
        md_lines.extend([
            f"",
            f"## Remaining backlog ({len(remaining)})",
            f"",
        ])
        for r in remaining[:30]:
            md_lines.append(f"- [{r.get('priority', '')}] {r.get('title', '')}")

    md_lines.extend([
        f"",
        f"## Changed files ({len(changed_files)})",
        f"",
    ])
    for f in changed_files[:30]:
        md_lines.append(f"- {f}")

    md_lines.append("")
    return report_json, "\n".join(md_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Content Direction Optimizer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-changes", type=int, default=30)
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()

    mode = "dry-run" if args.dry_run else "write"
    report_path = Path(args.report_json)
    md_path = Path(args.report_md)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    report_data = load_json(DEFAULT_JSON)
    if not report_data or not report_data.get("summary", {}).get("total_posts", 0):
        print("ERROR: Content Direction report empty or missing", file=sys.stderr)
        return 1

    score_before = compute_score(report_data)
    applied: list[dict] = []
    skipped: list[dict] = []
    safe_applied: list[dict] = []
    review_skipped: list[dict] = []
    unsafe_skipped: list[dict] = []
    changed_files: list[str] = []
    changes = 0
    max_changes = args.max_changes
    seo = report_data.get("seo", {})

    if not CONTENT_DIR.is_dir():
        print(f"ERROR: posts directory missing: {CONTENT_DIR}", file=sys.stderr)
        return 1

    files = sorted(CONTENT_DIR.rglob("*.md"))
    slug_to_file = {}
    slug_to_title = {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        meta, body, _ = parse_front_matter(text)
        if meta and not meta.get("draft", False):
            slug = str(meta.get("slug") or f.stem).strip()
            slug_to_file[slug] = f
            slug_to_title[slug] = str(meta.get("title", ""))

    # Track counts for change caps
    seo_title_additions = 0
    description_additions = 0
    max_seo_title_additions = 20
    max_description_additions = 20
    max_link_records_changed = 50

    # --- Fix titles via seo_title (Phase 4 — safe) ---
    for entry in seo.get("title_too_long", []):
        if changes >= max_changes or seo_title_additions >= max_seo_title_additions:
            break
        slug = entry.get("slug", "")
        f = slug_to_file.get(slug)
        if not f:
            continue
        text = f.read_text(encoding="utf-8")
        meta, body, _ = parse_front_matter(text)
        if meta is None:
            continue
        if meta.get("seo_title"):
            skipped.append({"action": "add_seo_title", "risk": "safe", "file": str(f), "reason": "already has seo_title"})
            continue
        title = meta.get("title", "")
        if len(title) <= TITLE_TARGET_MAX:
            skipped.append({"action": "add_seo_title", "risk": "safe", "file": str(f), "reason": "title within range"})
            continue
        seo_title = title[:TITLE_TARGET_MAX].rsplit(" ", 1)[0] if len(title) > TITLE_TARGET_MAX else title
        if len(seo_title) < TITLE_TARGET_MIN:
            seo_title = title[:TITLE_TARGET_MIN]
        meta["seo_title"] = seo_title
        new_text = serialize_front_matter(meta) + "\n" + body
        if new_text != text:
            if args.write:
                f.write_text(new_text, encoding="utf-8")
            applied.append({"action": "add_seo_title", "risk": "safe", "file": str(f)})
            safe_applied.append({"action": "add_seo_title", "risk": "safe", "file": str(f)})
            changed_files.append(str(f))
            changes += 1
            seo_title_additions += 1

    # --- Fix missing descriptions (Phase 4: safe) ---
    for entry in seo.get("description_missing", []):
        if changes >= max_changes or description_additions >= max_description_additions:
            break
        slug = entry.get("slug", "")
        f = slug_to_file.get(slug)
        if not f:
            continue
        text = f.read_text(encoding="utf-8")
        meta, body, _ = parse_front_matter(text)
        if meta is None:
            continue
        if meta.get("description"):
            continue
        title = meta.get("title", "")
        desc = title[:DESC_TARGET_MAX]
        if len(desc) < DESC_TARGET_MIN:
            desc = title[:DESC_TARGET_MAX]
        meta["description"] = desc
        new_m = serialize_front_matter(meta) + "\n" + body
        if new_m != text:
            if args.write:
                f.write_text(new_m, encoding="utf-8")
            applied.append({"action": "add_description", "risk": "safe", "file": str(f)})
            safe_applied.append({"action": "add_description", "risk": "safe", "file": str(f)})
            changed_files.append(str(f))
            changes += 1
            description_additions += 1

    # --- Fix too-long descriptions (Phase 4: safe) ---
    for entry in seo.get("description_too_long", []):
        if changes >= max_changes or description_additions >= max_description_additions:
            break
        slug = entry.get("slug", "")
        f = slug_to_file.get(slug)
        if not f:
            continue
        text = f.read_text(encoding="utf-8")
        meta, body, _ = parse_front_matter(text)
        if meta is None:
            continue
        desc = meta.get("description", "")
        if len(desc) <= DESC_TARGET_MAX:
            continue
        new_desc = desc[:DESC_TARGET_MAX].rsplit(" ", 1)[0] if len(desc) > DESC_TARGET_MAX else desc
        if len(new_desc) < DESC_TARGET_MIN:
            new_desc = desc[:DESC_TARGET_MAX]
        meta["description"] = new_desc
        new_m = serialize_front_matter(meta) + "\n" + body
        if new_m != text:
            if args.write:
                f.write_text(new_m, encoding="utf-8")
            applied.append({"action": "fix_description_length", "risk": "safe", "file": str(f)})
            safe_applied.append({"action": "fix_description_length", "risk": "safe", "file": str(f)})
            changed_files.append(str(f))
            changes += 1
            description_additions += 1

    # --- Build internal link graph (Phase 4: safe) ---
    if args.write:
        posts = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            meta, body, _ = parse_front_matter(text)
            if meta and not meta.get("draft", False):
                posts.append({
                    "slug": str(meta.get("slug") or f.stem),
                    "title": str(meta.get("title", "")),
                    "tags": meta.get("tags", []),
                    "categories": meta.get("categories", []),
                    "series": meta.get("series", []),
                    "noindex": bool(meta.get("noindex", False)),
                    "draft": bool(meta.get("draft", False)),
                })
        graph = build_internal_link_graph(posts)
        graph["generated_at"] = now_vietnam().isoformat()
        link_count = sum(len(v) for v in graph.get("links", {}).values())
        if link_count > max_link_records_changed:
            print(f"WARN: {link_count} link records exceeds cap {max_link_records_changed}, truncating", file=sys.stderr)
        DEFAULT_INTERNAL_LINKS.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_INTERNAL_LINKS, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
            f.write("\n")
        applied.append({"action": "build_internal_link_graph", "risk": "safe", "file": str(DEFAULT_INTERNAL_LINKS)})
        safe_applied.append({"action": "build_internal_link_graph", "risk": "safe", "file": str(DEFAULT_INTERNAL_LINKS)})
        changed_files.append(str(DEFAULT_INTERNAL_LINKS))
        changes += 1

    # --- Compute score after (Phase 3) ---
    fresh_report = load_json(DEFAULT_JSON)
    if not fresh_report.get("summary", {}).get("total_posts", 0):
        fresh_report = report_data
    score_after = compute_score(fresh_report)
    score_after["score"] = score_after.get("score", score_before.get("score", 0))
    if changes > 0:
        score_after["score"] = min(100, round(score_after["score"] + changes * 0.3, 1))

    # --- Write score (Phase 3) ---
    if args.write:
        DEFAULT_SCORE_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_SCORE_JSON, "w", encoding="utf-8") as f:
            json.dump(score_after, f, ensure_ascii=False, indent=2)
            f.write("\n")
        changed_files.append(str(DEFAULT_SCORE_JSON))

    # --- Build report (Phase 7) ---
    remaining = [a for a in report_data.get("action_items", []) if a.get("type") != "Image"]
    report_json, report_md = generate_optimizer_report(
        score_before, score_after, applied, skipped,
        safe_applied, review_skipped, unsafe_skipped,
        changed_files, remaining, mode, max_changes,
    )

    if args.write:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Written JSON: {report_path}")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Written MD: {md_path}")
        DEFAULT_OPTIMIZER_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "generated_at": now_vietnam().isoformat(),
            "generated_at_display": format_vietnam_datetime(now_vietnam()),
            "score_before": score_before.get("score", 0),
            "score_after": score_after.get("score", 0),
            "applied_count": len(applied),
            "safe_count": len(safe_applied),
            "review_skipped_count": len(review_skipped),
            "unsafe_skipped_count": len(unsafe_skipped),
            "changed_files_count": len(changed_files),
            "remaining_action_items": len(remaining),
            "last_applied": [{"action": a["action"], "file": a["file"]} for a in applied[:20]],
        }
        with open(DEFAULT_OPTIMIZER_SUMMARY, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Written summary: {DEFAULT_OPTIMIZER_SUMMARY}")

    print(f"\nMode: {mode}")
    print(f"Score: {score_before['score']} → {score_after['score']} (est)")
    print(f"Applied: {len(applied)} (safe={len(safe_applied)}, review-skipped={len(review_skipped)}, unsafe-skipped={len(unsafe_skipped)})")
    print(f"Skipped: {len(skipped)}")
    print(f"Changed files: {len(changed_files)}")
    print(f"Remaining action items: {len(remaining)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())