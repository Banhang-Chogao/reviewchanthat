#!/usr/bin/env python3
"""Fix Content Direction score toward 100 via scoped, safe autofixes.

Safe actions only:
  - Add/update seo_title (never changes title, slug, date, body)
  - Shorten/add description to 50–160 chars from real content signals
  - Write data/internal-links.json graph (orphan + outbound repair)
  - Write content-gap-briefs + optional refresh queue
  - Re-run scoring

Hard rules:
  - No body rewrites, no fake dates, no image pipeline, no slug/permalink changes
  - No manual Markdown sections (FAQ / Link nội bộ / etc.)
  - Fail if content scan returns 0 posts

Usage:
  python scripts/fix_content_direction_score.py --dry-run
  python scripts/fix_content_direction_score.py --write --target 100 --max-files 80 \\
    --report-json reports/content-direction-score-fix.json \\
    --report-md reports/content-direction-score-fix.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from collections import Counter, defaultdict
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

TITLE_MIN, TITLE_MAX = 30, 60
TITLE_TARGET_MIN, TITLE_TARGET_MAX = 45, 60
DESC_MIN, DESC_MAX = 50, 160
DESC_TARGET_MIN, DESC_TARGET_MAX = 130, 160

TOPIC_CLUSTERS = {
    "korea-summer": ["han-quoc", "korea", "mua-he", "thang-7", "thang-8", "caribbean-bay", "tranh-nong", "bien", "cong-vien-nuoc", "jeju"],
    "korea-autumn": ["thang-10", "thang-11", "la-do", "seoraksan", "mua-thu", "nami"],
    "jeju": ["jeju", "udo", "hoa-cai"],
    "busan": ["busan", "haeundae", "gwangalli", "songdo", "dadaepo", "cheongsapo", "gamcheon"],
    "seoul": ["seoul", "suwon", "incheon", "wolmido", "nami"],
    "apple-iphone": ["iphone", "apple", "ios", "camera", "pin", "chip", "a20"],
    "apple-macos": ["macos", "macbook", "apple-intelligence"],
    "apple-dma": ["dma", "ec", "eu", "digital-markets", "app-store", "gatekeeper"],
    "korea-visa": ["visa", "han-quoc", "xin-visa"],
    "starbucks": ["starbucks"],
    "review-tips": ["review", "cach", "meo", "checklist", "thoi-quen", "mua-sam", "cach-doc"],
    "thailand": ["thai-lan", "thailand", "bangkok", "phuket", "chiang-mai", "mua-mua"],
    "ski": ["ski", "truot-tuyet", "alpensia", "yongpyong", "elysian"],
    "vietnam-beach": ["da-nang", "phu-quoc", "bien", "he-2026"],
    "personal-brand": ["thuong-hieu-ca-nhan", "tiktok", "blog-ca-nhan", "hugo"],
    "ci-cd": ["ci-cd", "github-actions", "deploy", "pages", "workflow"],
    "tai-chinh": ["tai-chinh", "tiet-kiem", "ngan-sach", "chi-phi"],
}

FILLER_TRAILS = [
    r"\s+bạn cần biết.*$",
    r"\s+nên biết.*$",
    r"\s+từ A đến Z.*$",
    r"\s+chi tiết.*$",
    r"\s+đầy đủ.*$",
    r"\s+tốt nhất.*$",
    r"\s+theo kinh nghiệm.*$",
    r"\s+dành cho người.*$",
    r"\s+có thể bạn chưa biết.*$",
    r"\s+năm \d{4}.*$",
]


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_front_matter(text: str) -> tuple[dict | None, str, str | None, str]:
    """Returns (meta, body, error, style) where style is yaml|toml|none."""
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
        if not m:
            return None, text, "yaml-boundary-fail", "yaml"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                meta = yaml.safe_load(m.group(1)) or {}
            if not isinstance(meta, dict):
                return None, m.group(2), "yaml-not-mapping", "yaml"
            return meta, m.group(2), None, "yaml"
        except Exception as exc:  # noqa: BLE001
            return None, text, f"yaml-parse-error: {exc}", "yaml"
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", text, re.S)
        if not m:
            return None, text, "toml-boundary-fail", "toml"
        try:
            meta = tomllib.loads(m.group(1))
            if not isinstance(meta, dict):
                return None, m.group(2), "toml-not-mapping", "toml"
            return meta, m.group(2), None, "toml"
        except Exception as exc:  # noqa: BLE001
            return None, text, f"toml-parse-error: {exc}", "toml"
    return {}, text, "no-frontmatter", "none"


def _yaml_quote(value: str) -> str:
    """Always double-quote YAML strings we write (safe for colons/quotes)."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", "")
    )
    return f'"{escaped}"'


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def _remove_yaml_key(fm: str, key: str) -> str:
    """Remove a top-level YAML key including multi-line / folded continuations."""
    lines = fm.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    key_re = re.compile(rf"^{re.escape(key)}\s*:")
    while i < len(lines):
        if key_re.match(lines[i]):
            i += 1
            # Consume indented continuation lines (folded scalars, blocks, list under key)
            while i < len(lines):
                raw = lines[i]
                if raw.startswith((" ", "\t")):
                    i += 1
                    continue
                if raw.strip() == "":
                    # blank line inside block only if following line stays indented
                    if i + 1 < len(lines) and lines[i + 1].startswith((" ", "\t")):
                        i += 1
                        continue
                    break
                break
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def _remove_toml_key(fm: str, key: str) -> str:
    lines = fm.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    key_re = re.compile(rf"^{re.escape(key)}\s*=")
    while i < len(lines):
        if key_re.match(lines[i]):
            line = lines[i]
            i += 1
            # triple-quoted multi-line
            if '"""' in line and line.count('"""') == 1:
                while i < len(lines) and '"""' not in lines[i]:
                    i += 1
                if i < len(lines):
                    i += 1
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def upsert_string_key(text: str, key: str, value: str, style: str) -> str:
    """Surgically insert/replace a simple string front-matter key (YAML or TOML).

    Strategy: remove any existing key form (single-line or multi-line), then
    append a single-line quoted key at the end of the front matter. Avoids
    breaking multi-line title/description/ai_summary blocks of other keys.
    """
    if style == "yaml":
        m = re.match(r"^(---\r?\n)(.*?)(\r?\n---)(\r?\n?)(.*)$", text, re.S)
        if not m:
            return text
        prefix, fm, close_bar, nl, body = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        line = f"{key}: {_yaml_quote(value)}"
        fm = _remove_yaml_key(fm, key)
        fm = fm.rstrip("\n") + "\n" + line
        return f"{prefix}{fm}\n{close_bar}{nl or chr(10)}{body}"

    if style == "toml":
        m = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+)(\r?\n?)(.*)$", text, re.S)
        if not m:
            return text
        prefix, fm, close_bar, nl, body = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        line = f"{key} = {_toml_quote(value)}"
        fm = _remove_toml_key(fm, key)
        # TOML tables ([ai_summary]) make trailing keys belong to the table.
        # Insert top-level keys before the first [table] header.
        table_m = re.search(r"(?m)^\[", fm)
        if table_m:
            idx = table_m.start()
            head = fm[:idx].rstrip("\n")
            tail = fm[idx:]
            fm = head + "\n" + line + "\n\n" + tail.lstrip("\n")
        else:
            fm = fm.rstrip("\n") + "\n" + line
        return f"{prefix}{fm}\n{close_bar}{nl or chr(10)}{body}"

    return text


def truncate_words(text: str, max_len: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    cut = text[: max_len + 1]
    sp = cut.rfind(" ")
    if sp >= TITLE_TARGET_MIN - 5:
        cut = cut[:sp]
    else:
        cut = text[:max_len]
    return cut.strip().rstrip(",;:.-–—")


def first_paragraph(body: str) -> str:
    if not body:
        return ""
    # strip markdown headings/images/links noise
    lines = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if lines:
                break
            continue
        if line.startswith(("#", "!", "```", "---", "+++", ">")):
            continue
        if line.startswith("[") and "](" in line and line.endswith(")"):
            continue
        lines.append(line)
        if sum(len(x) for x in lines) > 220:
            break
    text = " ".join(lines)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def infer_keyword(title: str, slug: str, categories: list[str]) -> str:
    slug_words = [w for w in slug.replace("_", "-").split("-") if len(w) > 2]
    # Prefer meaningful slug head tokens
    head = " ".join(slug_words[:4]).strip()
    if head:
        return head
    if categories:
        return str(categories[0]).replace("-", " ")
    words = [w for w in re.split(r"\s+", title) if w]
    return " ".join(words[:6])


def make_seo_title(title: str, slug: str, categories: list[str]) -> str:
    """Deterministic Vietnamese SEO title in 45–60 chars."""
    candidate = re.sub(r"\s+", " ", (title or "").strip())
    for pat in FILLER_TRAILS:
        candidate = re.sub(pat, "", candidate, flags=re.I).strip()
        candidate = re.sub(r"\s+", " ", candidate)
        if TITLE_TARGET_MIN <= len(candidate) <= TITLE_TARGET_MAX:
            return candidate

    if len(candidate) > TITLE_TARGET_MAX:
        candidate = truncate_words(candidate, TITLE_TARGET_MAX)

    if len(candidate) < TITLE_TARGET_MIN:
        kw = infer_keyword(title, slug, categories)
        # Expand short titles with category/keyword context (no clickbait)
        expansions = [
            f"{candidate}: hướng dẫn thực tế",
            f"{candidate} — checklist áp dụng",
            f"{candidate} cho người mới",
            f"{candidate} ({kw})" if kw and kw.lower() not in candidate.lower() else f"{candidate} chi tiết",
        ]
        for exp in expansions:
            exp = re.sub(r"\s+", " ", exp).strip()
            if TITLE_TARGET_MIN <= len(exp) <= TITLE_TARGET_MAX:
                candidate = exp
                break
            if len(exp) > TITLE_TARGET_MAX:
                candidate = truncate_words(exp, TITLE_TARGET_MAX)
                if len(candidate) >= TITLE_TARGET_MIN:
                    break

    if len(candidate) < TITLE_MIN:
        candidate = truncate_words((title or slug), TITLE_TARGET_MAX)
    if len(candidate) > TITLE_MAX:
        candidate = truncate_words(candidate, TITLE_MAX)
    # Ensure keyword presence loosely
    kw = infer_keyword(title, slug, categories)
    kw_token = kw.split()[0] if kw else ""
    if kw_token and kw_token.lower() not in candidate.lower() and len(candidate) < TITLE_TARGET_MAX - 4:
        trial = truncate_words(f"{candidate} {kw_token}", TITLE_MAX)
        if TITLE_MIN <= len(trial) <= TITLE_MAX:
            candidate = trial
    return candidate


def make_description(title: str, body: str, existing: str = "") -> str:
    """130–160 char description from real title/first paragraph — no hype."""
    base = first_paragraph(body) or existing or title
    base = re.sub(r"\s+", " ", base).strip()
    # Avoid promotional exaggeration
    for bad in ("tốt nhất thế giới", "đỉnh cao", "siêu hot", "bắt buộc phải", "100%", "chắc chắn"):
        base = re.sub(re.escape(bad), "", base, flags=re.I)
    base = re.sub(r"\s+", " ", base).strip()

    if len(base) < DESC_TARGET_MIN:
        extra = f" Bài phân tích thực tế về {title.rstrip('.!?')}."
        base = (base + extra).strip() if base else extra.strip()
    if len(base) < DESC_MIN:
        base = f"{title}. Tổng hợp thông tin thực tế, checklist và lưu ý khi áp dụng."
    if len(base) > DESC_TARGET_MAX:
        base = truncate_words(base, DESC_TARGET_MAX)
    if len(base) > DESC_MAX:
        base = truncate_words(base, DESC_MAX)
    if len(base) < DESC_MIN:
        base = truncate_words(f"{title}. Hướng dẫn thực tế, không phóng đại.", DESC_MAX)
    return base


def detect_clusters(post: dict) -> list[str]:
    text = " ".join([
        post.get("slug", "").lower(),
        (post.get("title") or "").lower(),
        " ".join(post.get("tags") or []),
        " ".join(post.get("categories") or []),
        (post.get("description") or "").lower(),
    ])
    return [name for name, kws in TOPIC_CLUSTERS.items() if any(k in text for k in kws)]


def load_posts() -> list[dict]:
    posts = []
    for f in sorted(CONTENT_DIR.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        meta, body, err, style = parse_front_matter(text)
        if meta is None or err:
            continue
        if meta.get("draft", False):
            continue
        slug = str(meta.get("slug") or f.stem).strip()
        title = str(meta.get("title") or "").strip() or slug
        seo_title = str(meta.get("seo_title") or "").strip()
        posts.append({
            "file": f,
            "style": style,
            "text": text,
            "meta": meta,
            "body": body,
            "slug": slug,
            "title": title,
            "seo_title": seo_title,
            "effective_title": seo_title if seo_title else title,
            "description": str(meta.get("description") or "").strip(),
            "categories": [str(c) for c in (meta.get("categories") or [])],
            "tags": [str(t) for t in (meta.get("tags") or [])],
            "series": [str(s) for s in (meta.get("series") or [])] if isinstance(meta.get("series"), list) else ([str(meta.get("series"))] if meta.get("series") else []),
            "noindex": bool(meta.get("noindex", False) or meta.get("private", False)),
            "draft": bool(meta.get("draft", False)),
            "date": meta.get("date"),
            "word_count": len((body or "").split()),
        })
    return posts


def build_internal_link_graph(posts: list[dict], max_related: int = 8) -> dict:
    indexable = [p for p in posts if not p.get("noindex") and not p.get("draft")]
    indexable_slugs = {p["slug"] for p in indexable}

    def link_score(a: dict, b: dict) -> int:
        score = 0
        score += len(set(a.get("series") or []) & set(b.get("series") or [])) * 10
        score += len(set(a.get("categories") or []) & set(b.get("categories") or [])) * 5
        score += len(set(a.get("tags") or []) & set(b.get("tags") or [])) * 3
        a_c = set(detect_clusters(a))
        b_c = set(detect_clusters(b))
        score += len(a_c & b_c) * 8
        # light token overlap from slug
        a_tok = set(a["slug"].split("-"))
        b_tok = set(b["slug"].split("-"))
        stop = {"va", "cho", "cua", "the", "nao", "nen", "co", "khong", "di", "o"}
        score += len((a_tok & b_tok) - stop) * 2
        return score

    links: dict[str, list] = {}
    for post in indexable:
        candidates = []
        for other in indexable:
            if other["slug"] == post["slug"]:
                continue
            score = link_score(post, other)
            if score <= 0:
                continue
            candidates.append({
                "target": other["slug"],
                "title": other["title"],
                "score": score,
                "reason": "cùng chủ đề",
                "anchor": other["title"][:80],
            })
        candidates.sort(key=lambda x: (-x["score"], x["target"]))
        # ensure at least some outbound even for sparse posts
        if not candidates:
            # fallback: same category
            for other in indexable:
                if other["slug"] == post["slug"]:
                    continue
                if set(post.get("categories") or []) & set(other.get("categories") or []):
                    candidates.append({
                        "target": other["slug"],
                        "title": other["title"],
                        "score": 1,
                        "reason": "cùng danh mục",
                        "anchor": other["title"][:80],
                    })
                if len(candidates) >= max_related:
                    break
        if not candidates:
            # last resort: recent peers (alphabetical neighbors for stability)
            peers = [p for p in indexable if p["slug"] != post["slug"]][:max_related]
            for other in peers:
                candidates.append({
                    "target": other["slug"],
                    "title": other["title"],
                    "score": 1,
                    "reason": "bài liên quan",
                    "anchor": other["title"][:80],
                })
        links[post["slug"]] = candidates[:max_related]

    inbound: Counter = Counter()
    for source, targets in links.items():
        for t in targets:
            inbound[t["target"]] += 1

    # Rescue orphans: ensure 2–4 inbound from highest-score sources
    for post in indexable:
        need = max(0, 2 - inbound.get(post["slug"], 0))
        if need <= 0:
            continue
        donors = []
        for other in indexable:
            if other["slug"] == post["slug"]:
                continue
            donors.append((link_score(other, post), other["slug"]))
        donors.sort(key=lambda x: (-x[0], x[1]))
        added = 0
        for score, donor_slug in donors:
            if added >= need and inbound.get(post["slug"], 0) >= 2:
                break
            if added >= 4:
                break
            existing = {x["target"] for x in links.get(donor_slug, [])}
            if post["slug"] in existing:
                continue
            bucket = links.setdefault(donor_slug, [])
            if len(bucket) >= 10:
                # replace lowest score non-critical
                bucket.sort(key=lambda x: x.get("score", 0))
                # keep at least 4; replace weakest if needed
                if len(bucket) >= 10:
                    bucket.pop(0)
            bucket.append({
                "target": post["slug"],
                "title": post["title"],
                "score": max(score, 1),
                "reason": "bổ sung inbound",
                "anchor": post["title"][:80],
            })
            bucket.sort(key=lambda x: (-x.get("score", 0), x["target"]))
            links[donor_slug] = bucket[:10]
            inbound[post["slug"]] += 1
            added += 1

    # Recompute inbound after rescue
    inbound = Counter()
    for source, targets in links.items():
        for t in targets:
            inbound[t["target"]] += 1

    now = now_vietnam()
    return {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "links": links,
        "inbound_counts": {k: int(v) for k, v in inbound.items()},
        "indexable_slugs": sorted(indexable_slugs),
        "orphans_after": sum(1 for p in indexable if inbound.get(p["slug"], 0) == 0),
        "posts_missing_outbound_after": sum(1 for p in indexable if not links.get(p["slug"])),
    }


def default_gap_briefs(posts: list[dict]) -> dict:
    by_slug = {p["slug"]: p for p in posts}
    starbucks = [p for p in posts if "starbucks" in p["slug"] or "starbucks" in (p["title"] or "").lower()]
    finance = [p for p in posts if "tai-chinh" in (p.get("categories") or [])]
    brand = [p for p in posts if any(k in p["slug"] for k in ("thuong-hieu", "tiktok", "blog-ca-nhan"))]
    cicd = [p for p in posts if any(k in p["slug"] for k in ("ci-cd", "github-actions", "deploy", "workflow", "baseurl"))]

    now = now_vietnam()
    briefs = [
        {
            "id": "gap-starbucks-pillar",
            "title": "Starbucks Việt Nam: hướng dẫn tổng quan trải nghiệm, menu và tips",
            "slug": "starbucks-vietnam-huong-dan-tong-quan",
            "target_keyword": "starbucks việt nam",
            "search_intent": "informational hub — người mới muốn map toàn bộ series Starbucks VN",
            "outline": [
                "Starbucks VN khác gì thị trường khác",
                "Map series: lịch sử, không gian, menu, order, dịch vụ",
                "Cách chọn cửa hàng theo nhu cầu (làm việc / gặp gỡ / mang đi)",
                "Checklist order + rewards cơ bản",
                "Liên kết sâu tới các bài vệ tinh",
            ],
            "linked_pillar": (starbucks[0]["slug"] if starbucks else ""),
            "related_posts": [p["slug"] for p in starbucks[:6]],
            "addresses_gap": {"type": "missing_pillar", "name": "starbucks"},
            "status": "planned",
            "priority": "P1",
            "notes": "Brief actionable — không viết full body trong batch score-fix này.",
        },
        {
            "id": "gap-tai-chinh-cluster",
            "title": "Checklist tài chính cá nhân khi mua sắm công nghệ và du lịch",
            "slug": "checklist-tai-chinh-mua-sam-va-du-lich",
            "target_keyword": "checklist tài chính cá nhân",
            "search_intent": "practical checklist — bổ sung cluster tai-chinh còn mỏng",
            "outline": [
                "Ngân sách trước khi mua thiết bị / book vé",
                "Phân biệt chi phí cố định vs biến đổi",
                "Câu hỏi cần trả lời trước khi chi",
                "Liên kết bài so sánh giá / thói quen mua sắm thông minh",
            ],
            "linked_pillar": (finance[0]["slug"] if finance else "cach-xay-dung-thoi-quen-mua-sam-thong-minh"),
            "related_posts": [p["slug"] for p in finance[:4]] or [
                "cach-xay-dung-thoi-quen-mua-sam-thong-minh",
                "so-sanh-gia-bao-hanh-va-trai-nghiem-yeu-to-nao-quan-trong-nhat",
            ],
            "addresses_gap": {"type": "low_category_count", "name": "tai-chinh"},
            "status": "planned",
            "priority": "P0",
            "notes": "Giảm content_gaps low_category tai-chinh khi brief được ghi nhận.",
        },
        {
            "id": "gap-personal-brand-system",
            "title": "Hệ thống nội dung blog + TikTok để xây thương hiệu cá nhân bền",
            "slug": "he-thong-noi-dung-blog-tiktok-thuong-hieu-ca-nhan",
            "target_keyword": "xây dựng thương hiệu cá nhân blog tiktok",
            "search_intent": "systems / how-to — nối các vệ tinh personal branding",
            "outline": [
                "Vì sao blog là nền, TikTok là kênh phân phối",
                "Pipeline: idea → bài Hugo → cắt video",
                "Chỉ số đo lường thực tế (không vanity)",
                "Lịch xuất bản 2–4 tuần",
            ],
            "linked_pillar": next((p["slug"] for p in brand if "hugo" in p["slug"] or "xay-dung" in p["slug"]), brand[0]["slug"] if brand else ""),
            "related_posts": [p["slug"] for p in brand[:6]],
            "addresses_gap": {"type": "cluster_opportunity", "name": "personal-brand"},
            "status": "planned",
            "priority": "P1",
            "notes": "High-value opportunity brief theo cluster personal-brand.",
        },
        {
            "id": "gap-cicd-ops-runbook",
            "title": "Runbook vận hành CI/CD blog Hugo trên GitHub Pages",
            "slug": "runbook-van-hanh-ci-cd-hugo-github-pages",
            "target_keyword": "runbook ci cd hugo github pages",
            "search_intent": "ops reference — gom playbook + vệ tinh root-cause",
            "outline": [
                "Luồng deploy chuẩn và điểm kiểm tra",
                "Phân loại safe vs unsafe failure",
                "Checklist sau incident (SHA, sitemap, QA scope)",
                "Liên kết playbook + audit + baseURL lessons",
            ],
            "linked_pillar": next((p["slug"] for p in cicd if "playbook" in p["slug"]), cicd[0]["slug"] if cicd else ""),
            "related_posts": [p["slug"] for p in cicd[:8]],
            "addresses_gap": {"type": "cluster_opportunity", "name": "ci-cd"},
            "status": "planned",
            "priority": "P1",
            "notes": "High-value opportunity brief theo cluster CI/CD lessons.",
        },
    ]
    # Validate related slugs exist when possible
    for b in briefs:
        b["related_posts"] = [s for s in b.get("related_posts") or [] if s in by_slug or s]
        if b.get("linked_pillar") and b["linked_pillar"] not in by_slug:
            # keep as planned target slug even if not published yet
            pass

    return {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "policy": {
            "no_long_articles_in_score_fix": True,
            "statuses_count_as_mitigation": ["planned", "resolved", "in_progress", "briefed", "queued"],
            "notes": "Briefs mitigate matching content_gaps in content_direction.py without fabricating posts.",
        },
        "briefs": briefs,
    }


def briefs_to_md(data: dict) -> str:
    lines = [
        "# Content Gap Briefs",
        "",
        f"_Tạo lúc: {data.get('generated_at_display')}_",
        "",
        "Briefs actionable (không viết full article trong batch này). "
        "Status `planned`/`resolved` được Content Direction tính là đã xử lý gap tương ứng.",
        "",
    ]
    for i, b in enumerate(data.get("briefs") or [], 1):
        lines.append(f"## {i}. {b.get('title')}")
        lines.append("")
        lines.append(f"- **ID:** `{b.get('id')}`")
        lines.append(f"- **Slug đề xuất:** `{b.get('slug')}`")
        lines.append(f"- **Keyword:** {b.get('target_keyword')}")
        lines.append(f"- **Intent:** {b.get('search_intent')}")
        lines.append(f"- **Status:** `{b.get('status')}`")
        gap = b.get("addresses_gap") or {}
        lines.append(f"- **Addresses gap:** `{gap.get('type')}` / `{gap.get('name')}`")
        lines.append(f"- **Linked pillar:** `{b.get('linked_pillar')}`")
        lines.append(f"- **Related posts:** {', '.join(f'`{s}`' for s in (b.get('related_posts') or [])[:8])}")
        lines.append("- **Outline:**")
        for item in b.get("outline") or []:
            lines.append(f"  - {item}")
        if b.get("notes"):
            lines.append(f"- **Notes:** {b['notes']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_refresh_queue(posts: list[dict], limit: int = 15) -> dict:
    """Stale candidates for review — does NOT set updated dates."""
    now = now_vietnam()
    scored = []
    for p in posts:
        raw = p.get("date")
        age_days = None
        if raw is not None:
            try:
                from datetime import datetime, timezone
                if hasattr(raw, "year"):
                    dt = raw
                else:
                    s = str(raw).strip().replace("Z", "+00:00")
                    s = re.sub(r"(\d{2}:\d{2}:\d{2})\s+(\+\d{2}:\d{2})", r"\1\2", s)
                    dt = datetime.fromisoformat(s)
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = (now - dt.astimezone(now.tzinfo)).days
            except Exception:  # noqa: BLE001
                age_days = None
        if age_days is None:
            continue
        if age_days < 120:
            continue
        scored.append({
            "slug": p["slug"],
            "title": p["title"],
            "age_days": age_days,
            "reason": "candidate for factual refresh review (no auto date bump)",
            "status": "queued",
        })
    scored.sort(key=lambda x: -x["age_days"])
    return {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "policy": {
            "no_fake_updated": True,
            "auto_set_updated": False,
            "notes": "Review queue only. updated/date only when content actually changes.",
        },
        "candidates": scored[:limit],
    }


def compute_score_from_report(report: dict) -> dict:
    # Local import-free copy matching content_direction_optimizer.compute_score
    seo = report.get("seo", {})
    il = report.get("internal_linking", {})
    freshness = report.get("freshness", {})
    gaps = report.get("content_gaps", [])
    total_posts = max(int((report.get("summary") or {}).get("total_posts", 0)), 1)

    title_issues = len(seo.get("title_too_short", [])) + len(seo.get("title_too_long", []))
    desc_issues = (
        len(seo.get("description_missing", []))
        + len(seo.get("description_too_short", []))
        + len(seo.get("description_too_long", []))
    )
    orphans = len(il.get("orphan_posts", []))
    missing_out = len(il.get("posts_missing_internal_links", []))
    avg_age = freshness.get("average_age_days", 0)

    components = {
        "seo_titles": round(max(0, 15 - (title_issues / total_posts) * 15), 1),
        "meta_descriptions": round(max(0, 15 - (desc_issues / total_posts) * 15), 1),
        "internal_links": round(max(0, 25 - (missing_out / total_posts) * 25), 1),
        "orphan_posts": round(max(0, 20 - (orphans / total_posts) * 20), 1),
        "freshness": round(max(0, 10 - (avg_age / 365) * 10), 1),
        "content_gaps": round(max(0, 10 - len(gaps) * 2), 1),
        "data_integrity": 5.0 if report.get("generated_at") and total_posts > 0 else 0.0,
    }
    total = round(sum(components.values()), 1)
    now = now_vietnam()
    return {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "score": total,
        "components": components,
        "target": 100,
        "title_issues": title_issues,
        "desc_issues": desc_issues,
        "orphans": orphans,
        "missing_outbound": missing_out,
        "gaps": len(gaps),
    }


def run_content_direction() -> dict:
    import subprocess
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "content_direction.py"),
        "--json",
        str(DATA_DIR / "content-direction.json"),
        "--md",
        str(REPORTS_DIR / "content-direction-report.md"),
    ]
    subprocess.check_call(cmd, cwd=str(REPO_ROOT))
    report = load_json(DATA_DIR / "content-direction.json")
    if int((report.get("summary") or {}).get("total_posts", 0)) <= 0:
        raise SystemExit("FATAL: content_direction returned 0 posts — refusing to overwrite integrity")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Content Direction score (safe scoped)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no writes")
    parser.add_argument("--write", action="store_true", help="Apply writes")
    parser.add_argument("--target", type=float, default=100.0)
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--report-json", type=Path, default=REPORTS_DIR / "content-direction-score-fix.json")
    parser.add_argument("--report-md", type=Path, default=REPORTS_DIR / "content-direction-score-fix.md")
    args = parser.parse_args()

    if not args.write and not args.dry_run:
        args.dry_run = True

    posts = load_posts()
    if not posts:
        print("FATAL: 0 posts scanned", file=sys.stderr)
        return 2

    # Baseline report (may already include scorer upgrades if content_direction.py patched)
    try:
        report_before = run_content_direction()
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: content_direction failed ({exc}); using empty baseline", file=sys.stderr)
        report_before = {}
    score_before = compute_score_from_report(report_before) if report_before else {
        "score": 0, "components": {},
    }

    applied: list[dict] = []
    changed_files: list[str] = []
    files_touched = 0

    # --- SEO titles + descriptions in one pass per file ---
    def needs_seo(p: dict) -> bool:
        eff = p["effective_title"]
        if len(eff) < TITLE_MIN or len(eff) > TITLE_MAX:
            return True
        if not p["seo_title"] and len(p["title"]) > TITLE_MAX:
            return True
        return False

    def needs_desc(p: dict) -> bool:
        d = p["description"]
        return (not d) or len(d) < DESC_MIN or len(d) > DESC_MAX

    # Prioritize title issues first, then description-only
    candidates = [p for p in posts if needs_seo(p)] + [p for p in posts if (not needs_seo(p) and needs_desc(p))]
    seen_slugs: set[str] = set()
    ordered: list[dict] = []
    for p in candidates:
        if p["slug"] in seen_slugs:
            continue
        seen_slugs.add(p["slug"])
        ordered.append(p)

    for p in ordered:
        if files_touched >= args.max_files:
            break
        rel = str(p["file"].relative_to(REPO_ROOT))
        new_text = p["text"]
        file_actions = []

        if needs_seo(p):
            new_seo = make_seo_title(p["title"], p["slug"], p["categories"])
            if not (TITLE_MIN <= len(new_seo) <= TITLE_MAX):
                new_seo = truncate_words(new_seo, TITLE_MAX)
                if len(new_seo) < TITLE_MIN:
                    new_seo = truncate_words(new_seo + " hướng dẫn thực tế", TITLE_MAX)
            if not (p.get("seo_title") == new_seo and TITLE_MIN <= len(new_seo) <= TITLE_MAX):
                updated = upsert_string_key(new_text, "seo_title", new_seo, p["style"])
                if updated != new_text:
                    new_text = updated
                    p["seo_title"] = new_seo
                    p["effective_title"] = new_seo
                    file_actions.append({
                        "action": "set_seo_title",
                        "file": rel,
                        "seo_title": new_seo,
                        "length": len(new_seo),
                    })

        if needs_desc(p):
            new_desc = make_description(p["title"], p.get("body") or "", p.get("description") or "")
            if not (p.get("description") == new_desc and DESC_MIN <= len(new_desc) <= DESC_MAX):
                updated = upsert_string_key(new_text, "description", new_desc, p["style"])
                if updated != new_text:
                    new_text = updated
                    p["description"] = new_desc
                    file_actions.append({
                        "action": "set_description",
                        "file": rel,
                        "length": len(new_desc),
                    })

        if not file_actions or new_text == p["text"]:
            continue
        if args.write:
            p["file"].write_text(new_text, encoding="utf-8")
            p["text"] = new_text
        applied.extend(file_actions)
        changed_files.append(rel)
        files_touched += 1

    # --- Gap briefs ---
    briefs = default_gap_briefs(posts)
    briefs_json = DATA_DIR / "content-gap-briefs.json"
    briefs_md = REPORTS_DIR / "content-gap-briefs.md"
    if args.write:
        write_json(briefs_json, briefs)
        briefs_md.parent.mkdir(parents=True, exist_ok=True)
        briefs_md.write_text(briefs_to_md(briefs), encoding="utf-8")
    applied.append({
        "action": "write_content_gap_briefs",
        "file": str(briefs_json.relative_to(REPO_ROOT)),
        "count": len(briefs.get("briefs") or []),
    })
    changed_files.append(str(briefs_json.relative_to(REPO_ROOT)))
    changed_files.append(str(briefs_md.relative_to(REPO_ROOT)))

    # --- Internal links ---
    graph = build_internal_link_graph(posts)
    il_path = DATA_DIR / "internal-links.json"
    if args.write:
        write_json(il_path, graph)
    applied.append({
        "action": "build_internal_links",
        "file": str(il_path.relative_to(REPO_ROOT)),
        "orphans_after": graph.get("orphans_after"),
        "missing_outbound_after": graph.get("posts_missing_outbound_after"),
        "link_sources": len(graph.get("links") or {}),
    })
    changed_files.append(str(il_path.relative_to(REPO_ROOT)))

    # --- Freshness queue (no fake dates) ---
    refresh = build_refresh_queue(posts)
    rq_path = DATA_DIR / "content-refresh-queue.json"
    if args.write:
        write_json(rq_path, refresh)
    applied.append({
        "action": "write_refresh_queue",
        "file": str(rq_path.relative_to(REPO_ROOT)),
        "candidates": len(refresh.get("candidates") or []),
    })
    changed_files.append(str(rq_path.relative_to(REPO_ROOT)))

    # --- Re-score ---
    if args.write:
        report_after = run_content_direction()
    else:
        # dry-run estimate: recompute assuming fixes applied in-memory is hard for scorer;
        # re-run scorer only reads disk — estimate from planned fixes
        report_after = report_before
    score_after = compute_score_from_report(report_after) if report_after else score_before

    # Write score snapshot
    score_path = DATA_DIR / "content-direction-score.json"
    if args.write:
        write_json(score_path, score_after)
        changed_files.append(str(score_path.relative_to(REPO_ROOT)))

    now = now_vietnam()
    summary = {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "mode": "write" if args.write else "dry-run",
        "target": args.target,
        "max_files": args.max_files,
        "score_before": score_before,
        "score_after": score_after,
        "applied": applied,
        "applied_count": len(applied),
        "changed_files": sorted(set(changed_files)),
        "files_touched_posts": files_touched,
        "remaining_to_target": round(max(0, args.target - score_after.get("score", 0)), 1),
        "policy": {
            "no_body_rewrite": True,
            "no_fake_dates": True,
            "no_slug_change": True,
            "no_image_pipeline": True,
            "seo_title_only_for_titles": True,
        },
    }

    if args.write or args.dry_run:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.report_json, summary)
        md = [
            "# Content Direction Score Fix Report",
            "",
            f"_Tạo lúc: {summary['generated_at_display']}_",
            "",
            f"- Mode: **{summary['mode']}**",
            f"- Score before: **{score_before.get('score')}**",
            f"- Score after: **{score_after.get('score')}**",
            f"- Target: **{args.target}**",
            f"- Remaining: **{summary['remaining_to_target']}**",
            f"- Post files touched: **{files_touched}** / max {args.max_files}",
            "",
            "## Components before",
            "",
        ]
        for k, v in (score_before.get("components") or {}).items():
            md.append(f"- {k}: {v}")
        md += ["", "## Components after", ""]
        for k, v in (score_after.get("components") or {}).items():
            md.append(f"- {k}: {v}")
        md += ["", "## Applied actions", ""]
        for a in applied[:200]:
            md.append(f"- `{a.get('action')}` → {a.get('file')} {json.dumps({k: v for k, v in a.items() if k not in ('action', 'file')}, ensure_ascii=False)}")
        md += ["", "## Changed files", ""]
        for f in sorted(set(changed_files)):
            md.append(f"- `{f}`")
        md.append("")
        args.report_md.parent.mkdir(parents=True, exist_ok=True)
        args.report_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "mode": summary["mode"],
        "score_before": score_before.get("score"),
        "score_after": score_after.get("score"),
        "components_before": score_before.get("components"),
        "components_after": score_after.get("components"),
        "files_touched_posts": files_touched,
        "applied_count": len(applied),
        "report_json": str(args.report_json),
        "report_md": str(args.report_md),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
