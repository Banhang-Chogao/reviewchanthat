#!/usr/bin/env python3
"""
Content Controller for Review Chân Thật.
Depth-first quality control for blog posts.

Usage:
  python scripts/content_controller.py
  python scripts/content_controller.py --file content/posts/example.md
  python scripts/content_controller.py --changed-only
  python scripts/content_controller.py --ai          # optional AI layer
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

try:
    import frontmatter
    import yaml
except ImportError:
    print("python-frontmatter and pyyaml required. Run: pip install python-frontmatter pyyaml")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_GLOB = os.path.join(REPO_ROOT, "content/posts/**/*.md")
DATA_DIR = os.path.join(REPO_ROOT, "data")
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")

CATEGORY_CACHE = None

HARDCODED_SECTION_PATTERNS = [
    r"^##\s+Câu hỏi thường gặp",
    r"^##\s+FAQ$",
    r"^##\s+Liên kết bên trong\s*$",
    r"^##\s+Nguồn tham khảo\s*$",
]

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bLREM\b",
    r"\blorem ipsum\b",
    r"\b2099\b",
    r"\bfake date\b",
]

GENERIC_ANCHOR_PATTERNS = [
    r"xem thêm",
    r"click here",
    r"tại đây",
    r"ở đây",
    r"link này",
    r"bấm vào",
]

CATEGORY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEPTH_WEIGHTS = {
    "search_intent_clarity": 15,
    "practical_usefulness": 20,
    "original_angle": 15,
    "evidence_source_quality": 15,
    "structure_readability": 10,
    "decision_guidance": 15,
    "anti_padding": 10,
}


def load_categories():
    global CATEGORY_CACHE
    if CATEGORY_CACHE is not None:
        return CATEGORY_CACHE

    path = os.path.join(DATA_DIR, "categories.json")
    if not os.path.exists(path):
        CATEGORY_CACHE = {"items": [], "aliases": {}}
        return CATEGORY_CACHE

    try:
        with open(path, "r", encoding="utf-8") as f:
            CATEGORY_CACHE = json.load(f)
    except Exception:
        CATEGORY_CACHE = {"items": [], "aliases": {}}

    if not isinstance(CATEGORY_CACHE.get("items"), list):
        CATEGORY_CACHE["items"] = []
    if not isinstance(CATEGORY_CACHE.get("aliases"), dict):
        CATEGORY_CACHE["aliases"] = {}

    return CATEGORY_CACHE


def resolve_category_slug(raw_slug):
    cats = load_categories()
    for item in cats.get("items", []):
        if item.get("slug") == raw_slug:
            return item["slug"]
    alias = cats.get("aliases", {}).get(raw_slug.lower())
    if alias:
        return alias
    return None


def get_valid_category_slugs():
    cats = load_categories()
    slugs = set()
    for item in cats.get("items", []):
        s = item.get("slug", "").strip()
        if s:
            slugs.add(s)
    for alias, target in cats.get("aliases", {}).items():
        if target:
            slugs.add(target)
    return slugs


def get_category_label(slug):
    cats = load_categories()
    for item in cats.get("items", []):
        if item.get("slug") == slug:
            return item.get("label", slug)
    return slug


def extract_sections(body):
    lines = body.split("\n")
    sections = []
    current_type = None
    current_start = None
    section_heading = None

    section_map = {
        "mở đầu": "intro",
        "mở bài": "intro",
        "tóm tắt nhanh": "quick_summary",
        "có gì đáng": "analysis",
        "nên đi khi nào": "timing",
        "nên mua": "timing",
        "cách đi": "logistics",
        "cách lên lịch": "logistics",
        "lịch trình": "logistics",
        "lưu ý": "notes",
        "nên kết hợp": "recommendations",
        "kết luận": "conclusion",
        "tổng kết": "conclusion",
        "ai nên": "who",
        "không hợp": "who_not",
        "điểm mạnh": "pros",
        "điểm yếu": "cons",
        "so sánh": "comparison",
        "lợi ích": "pros",
        "hạn chế": "cons",
    }

    for i, line in enumerate(lines):
        stripped = line.strip()
        h2_match = re.match(r"^##\s+(.+)$", stripped)
        h3_match = re.match(r"^###\s+(.+)$", stripped)

        if h2_match:
            heading = h2_match.group(1).lower().strip()
            matched = None
            for key, value in section_map.items():
                if heading.startswith(key) or key.startswith(heading):
                    matched = value
                    break
            if matched:
                sections.append({"type": matched, "heading": h2_match.group(1), "line": i})
    return sections


def count_chinese_paragraphs(lines):
    long_lines = 0
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 300:
            long_lines += 1
    return long_lines


def word_count(text):
    return len(text.split())


def get_git_changed_md_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        if result.returncode != 0:
            return []
        files = [f for f in result.stdout.strip().split("\n") if f.endswith(".md") and f.startswith("content/posts/")]
        return [os.path.join(REPO_ROOT, f) for f in files]
    except Exception:
        return []


class ContentCheckResult:
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.depth_score = 0
        self.depth_breakdown = {}
        self.passed = True
        self.ai_feedback = None

    def add_error(self, msg):
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg):
        self.warnings.append(msg)

    def to_dict(self):
        return {
            "file": self.filepath,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "depth_score": self.depth_score,
            "depth_breakdown": self.depth_breakdown,
            "ai_feedback": self.ai_feedback,
        }


def check_front_matter(meta, body, result):
    title = meta.get("title", "")
    description = meta.get("description", "")
    categories = meta.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    date_val = meta.get("date")
    draft = meta.get("draft", True)

    # date checks
    if date_val:
        if isinstance(date_val, datetime):
            if date_val > datetime.now(timezone.utc):
                result.add_error(f"date is in the future: {date_val}")
            if date_val.year < 2024:
                result.add_error(f"date too old or fake: {date_val}")
        elif isinstance(date_val, str):
            fake_patterns = [r"2099", r"9999", r"fake", r"lorem"]
            for p in fake_patterns:
                if re.search(p, date_val, re.IGNORECASE):
                    result.add_error(f"date contains placeholder: {date_val}")
                    break
    else:
        result.add_error("missing date")

    # title
    if not title:
        result.add_error("missing title")
    elif any(p in title.lower() for p in ["todo", "fixme", "untitled", "lorem"]):
        result.add_error(f"title contains placeholder: '{title}'")

    # description
    if not description:
        result.add_warning("missing description")
    elif description and len(description) < 80:
        result.add_warning(f"description too short ({len(description)} chars, min 80)")

    # categories
    if not categories:
        result.add_error("missing categories")
    else:
        valid_slugs = get_valid_category_slugs()
        for cat in categories:
            resolved = resolve_category_slug(cat)
            if not resolved:
                result.add_error(f"category '{cat}' not found in canonical category mapping")
            elif resolved not in valid_slugs:
                result.add_warning(f"category '{cat}' resolves to '{resolved}' but not in items list")

    # tags
    if not tags:
        result.add_warning("no tags")
    elif len(tags) < 2:
        result.add_warning(f"only {len(tags)} tag(s), consider at least 2-3")

    # ai_summary presence
    ai_summary = meta.get("ai_summary", {})
    if not ai_summary or not ai_summary.get("enabled"):
        result.add_warning("ai_summary not enabled for this post")
    elif not ai_summary.get("items"):
        result.add_warning("ai_summary has no items")


def check_body(body, result):
    if not body or not body.strip():
        result.add_error("empty body")
        return

    body_lower = body.lower()
    lines = body.split("\n")

    # Hardcoded sections
    for i, line in enumerate(lines):
        stripped = line.strip()
        for pattern in HARDCODED_SECTION_PATTERNS:
            if re.match(pattern, stripped):
                result.add_error(
                    f"hardcoded repeated section at line {i+1}: '{stripped}'"
                    f" — must use front matter / macro rule"
                )

    # Placeholders
    for i, line in enumerate(lines):
        stripped = line.strip()
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                result.add_error(f"placeholder at line {i+1}: '{stripped[:60]}'")

    # Generic anchor text overuse
    total_links = len(re.findall(r"\[([^\]]+)\]\([^)]+\)", body))

    generic_count = 0
    for line in lines:
        for pattern in GENERIC_ANCHOR_PATTERNS:
            matches = re.findall(rf"\[([^\]]*{pattern}[^\]]*)\]", line, re.IGNORECASE)
            generic_count += len(matches)

    if total_links > 0 and generic_count / max(total_links, 1) > 0.3:
        result.add_warning(
            f"high proportion of generic anchor text ({generic_count}/{total_links})"
        )

    # check for contextual internal links
    internal_links = re.findall(r"\[([^\]]+)\]\((/[^)]+)\)", body)
    if not internal_links:
        result.add_warning("no internal links found in body")

    # word count
    wc = word_count(body)
    if wc < 300:
        result.add_error(f"body too short ({wc} words, min 300)")
    elif wc < 600:
        result.add_warning(f"body short ({wc} words), consider expanding")

    # structure sections
    sections = extract_sections(body)
    section_types = {s["type"] for s in sections}

    if "intro" not in section_types:
        result.add_warning("no introductory section (## Mở bài / Mở đầu)")
    if "conclusion" not in section_types:
        result.add_warning("no conclusion section (## Kết luận / Tổng kết)")
    if "notes" not in section_types:
        result.add_warning("no notes section (## Lưu ý)")


def check_front_matter_sections(meta, result):
    faq = meta.get("faq", [])
    if not faq:
        result.add_warning("no FAQ front matter field")

    internal_links = meta.get("internal_links", [])
    if not internal_links:
        result.add_warning("no internal_links front matter field")

    external_links = meta.get("external_links", [])
    if not external_links:
        result.add_warning("no external_links front matter field")

    attribution = meta.get("attribution", {})
    if not attribution:
        result.add_warning("no attribution front matter field")
    elif not attribution.get("copyright") or not attribution.get("source_note"):
        result.add_warning("attribution incomplete (missing copyright or source_note)")


def compute_depth_score(meta, body, result):
    scores = {}
    lines = body.split("\n") if body else []
    wc = word_count(body) if body else 0
    body_lower = body.lower() if body else ""

    # 1. Search intent clarity (15)
    title = meta.get("title", "")
    description = meta.get("description", "")
    has_problem_statement = bool(re.search(r"nên|hay|có nên|cách|làm sao|không|ai|khi nào|ở đâu", title.lower()))
    has_description = len(description) >= 80
    has_quick_summary = bool(re.search(r"tóm tắt", body_lower))
    intent_score = 0
    if has_problem_statement:
        intent_score += 6
    if has_description:
        intent_score += 5
    if has_quick_summary:
        intent_score += 4
    scores["search_intent_clarity"] = min(intent_score, 15)

    # 2. Practical usefulness (20)
    has_timing = bool(re.search(r"nên đi khi nào|thời gian|mùa|tháng", body_lower))
    has_logistics = bool(re.search(r"cách đi|cách lên lịch|phương tiện|di chuyển|tàu|xe buýt|taxi|máy bay", body_lower))
    has_budget = bool(re.search(r"chi phí|giá|tiền|vé|krw|usd|đồng|phí", body_lower))
    has_booking_advice = bool(re.search(r"đặt trước|mua vé|booking|reservation|klook|kkday|trip", body_lower))
    has_checklist = bool(re.search(r"\bchecklist\b|bảng|danh sách|lưu ý|cần nhớ|nên mang", body_lower))
    practical_score = 0
    if has_timing:
        practical_score += 4
    if has_logistics:
        practical_score += 4
    if has_budget:
        practical_score += 4
    if has_booking_advice:
        practical_score += 4
    if has_checklist:
        practical_score += 4
    scores["practical_usefulness"] = min(practical_score, 20)

    # 3. Original angle / honest voice (15)
    has_honest = bool(re.search(r"dễ thất vọng|không nên|bỏ qua|nếu lịch ngắn|đáng tiền|không đáng|overrated|đông|đắt", body_lower))
    has_personal = bool(re.search(r"tôi thấy|theo mình|mình nghĩ|thực tế|cá nhân|theo kinh nghiệm", body_lower))
    has_pros_cons = bool(re.search(r"điểm mạnh|điểm yếu|ưu điểm|nhược điểm|lợi.*hại|nên.*không nên", body_lower))
    has_comparison = bool(re.search(r"so sánh|thay vì|hơn.*nhưng|nhưng.*hơn|lựa chọn thay thế", body_lower))
    original_score = 0
    if has_honest:
        original_score += 5
    if has_personal:
        original_score += 4
    if has_pros_cons:
        original_score += 3
    if has_comparison:
        original_score += 3
    scores["original_angle"] = min(original_score, 15)

    # 4. Evidence and source quality (15)
    faq = meta.get("faq", [])
    external_links = meta.get("external_links", [])
    attribution = meta.get("attribution", {})
    internal_links_fm = meta.get("internal_links", [])

    evidence_score = 0
    if faq and len(faq) >= 2:
        evidence_score += 4
    if external_links and len(external_links) >= 1:
        evidence_score += 4
    if attribution and attribution.get("source_note"):
        evidence_score += 3
    if internal_links_fm and len(internal_links_fm) >= 1:
        evidence_score += 2
    if wc >= 800:
        evidence_score += 2
    scores["evidence_source_quality"] = min(evidence_score, 15)

    # 5. Structure and readability (10)
    sections = extract_sections(body)
    has_tables = len(re.findall(r"\|.+\|", body)) > 3
    has_bullets = body.count("- ") > 5 or body.count("* ") > 5
    has_subheadings = len(re.findall(r"^#{2,3}\s", body, re.MULTILINE)) >= 3
    has_short_paragraphs = count_chinese_paragraphs(lines) <= 3

    struct_score = 0
    if has_tables:
        struct_score += 3
    if has_bullets:
        struct_score += 2
    if has_subheadings:
        struct_score += 3
    if has_short_paragraphs:
        struct_score += 2
    scores["structure_readability"] = min(struct_score, 10)

    # 6. Decision guidance (15)
    has_who = bool(re.search(r"hợp với|phù hợp|dành cho|cho.*nào", body_lower))
    has_who_not = bool(re.search(r"không hợp|không phù hợp|nên bỏ qua|không nên", body_lower))
    has_why = bool(re.search(r"vì sao|lý do|tại sao|nguyên nhân", body_lower))
    has_recommendation = bool(re.search(r"nên chọn|gợi ý|khuyến nghị|đề xuất|recommend", body_lower))

    decision_score = 0
    if has_who:
        decision_score += 5
    if has_who_not:
        decision_score += 4
    if has_why:
        decision_score += 3
    if has_recommendation:
        decision_score += 3
    scores["decision_guidance"] = min(decision_score, 15)

    # 7. Anti-padding / low repetition (10)
    total_sentences = len(re.findall(r"[.!?]", body))
    unique_words_ratio = len(set(body_lower.split())) / max(wc, 1)

    padding_score = 0
    if wc >= 400:
        padding_score += 2
    if unique_words_ratio >= 0.4:
        padding_score += 4
    elif unique_words_ratio >= 0.3:
        padding_score += 2
    if has_checklist:
        padding_score += 2
    if has_tables:
        padding_score += 2
    scores["anti_padding"] = min(padding_score, 10)

    total = sum(scores.values())
    result.depth_score = total
    result.depth_breakdown = scores

    # Fail conditions
    if total < 75:
        result.add_error(
            f"depth score {total}/100 is below minimum (75)"
        )
    if scores.get("practical_usefulness", 0) < 12:
        result.add_error(
            f"practical usefulness score {scores['practical_usefulness']}/20 is below minimum (12)"
        )
    if scores.get("evidence_source_quality", 0) < 10:
        result.add_error(
            f"evidence/source quality score {scores['evidence_source_quality']}/15 is below minimum (10)"
        )

    return total


def run_ai_assessment(meta, body, filepath):
    api_key = os.environ.get("CONTENT_QA_AI_API_KEY", "")
    if not api_key:
        return None

    title = meta.get("title", "")
    description = meta.get("description", "")
    body_preview = body[:4000] if body else ""

    prompt = f"""You are a content quality assessor for a Vietnamese blog called "Review Chân Thật" (Honest Reviews). Evaluate this post and return JSON only.

Post title: {title}
Description: {description}
Body start: {body_preview[:2000]}

Rate the post on these criteria (0-100 scale):
1. Search intent clarity: Does the post clearly address a reader's search query?
2. Practical usefulness: Does it give actionable, real-world advice?
3. Original angle: Does it have an honest, non-generic voice?
4. Evidence/source quality: Are claims backed by credible sources?
5. Structure/readability: Is it well-organized, scannable?
6. Decision guidance: Does it help the reader decide what to do?
7. Anti-padding: Is there fluff or repetition?

Return JSON:
{{
  "depth_score": 0-100,
  "issues": [],
  "must_fix": [],
  "suggested_improvements": [],
  "pass": true/false
}}"""

    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500,
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"]
        # extract JSON from response
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        return {"error": str(e), "pass": True, "depth_score": 0}


def check_post(filepath):
    result = ContentCheckResult(filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
    except Exception as e:
        result.add_error(f"cannot parse front matter: {e}")
        return result

    meta = post.metadata
    body = post.content or ""

    check_front_matter(meta, body, result)
    check_body(body, result)
    check_front_matter_sections(meta, result)
    compute_depth_score(meta, body, result)

    return result


def generate_report(results, output_json=None, output_md=None):
    total = len(results)
    passed = sum(1 for r in results if r.passed and r.depth_score >= 75)
    failed = total - passed
    avg_depth = sum(r.depth_score for r in results) / max(total, 1)

    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_posts": total,
        "passed": passed,
        "failed": failed,
        "average_depth_score": round(avg_depth, 1),
        "results": [r.to_dict() for r in results],
    }

    os.makedirs(REPORTS_DIR, exist_ok=True)

    json_path = output_json or os.path.join(REPORTS_DIR, "content-quality-report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    md_lines = [
        f"# Content Quality Report",
        f"**Generated:** {report_data['timestamp']}",
        f"**Total:** {total} | **Passed:** {passed} | **Failed:** {failed} | **Avg Depth:** {avg_depth:.1f}/100",
        "",
        "## Summary",
        f"| Post | Pass | Depth Score | Errors | Warnings |",
        f"|------|------|-------------|--------|----------|",
    ]

    for r in results:
        status = "✅" if r.passed and r.depth_score >= 75 else "❌"
        md_lines.append(
            f"| {os.path.basename(r.filepath)} | {status} | {r.depth_score}/100 | {len(r.errors)} | {len(r.warnings)} |"
        )

    md_lines.extend(["", "## Depth Breakdown (failed posts)"])
    for r in results:
        if not r.passed:
            md_lines.extend([
                f"### {os.path.basename(r.filepath)}",
                f"Score: {r.depth_score}/100",
                f"Breakdown: {json.dumps(r.depth_breakdown, ensure_ascii=False)}",
            ])
            if r.errors:
                md_lines.append("Errors:")
                for e in r.errors:
                    md_lines.append(f"- {e}")
            if r.warnings:
                md_lines.append("Warnings:")
                for w in r.warnings:
                    md_lines.append(f"- {w}")
            md_lines.append("")

    md_path = output_md or os.path.join(REPORTS_DIR, "content-quality-report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


def print_results(results):
    print(f"\n{'='*70}")
    print(f"Content Controller Results — {len(results)} posts")
    print(f"{'='*70}")

    fail_count = 0
    for r in results:
        label = os.path.basename(r.filepath)
        status = "✅ PASS" if r.passed and r.depth_score >= 75 else "❌ FAIL"
        if r.passed and r.depth_score < 75:
            status = "⚠️  LOW SCORE"
            r.passed = False

        if not r.passed:
            fail_count += 1

        print(f"\n{status} | {label} | Score: {r.depth_score}/100")
        if r.depth_breakdown:
            bd = r.depth_breakdown
            print(
                f"    Intent:{bd.get('search_intent_clarity',0)} "
                f"Useful:{bd.get('practical_usefulness',0)} "
                f"Angle:{bd.get('original_angle',0)} "
                f"Evidence:{bd.get('evidence_source_quality',0)} "
                f"Struct:{bd.get('structure_readability',0)} "
                f"Decision:{bd.get('decision_guidance',0)} "
                f"NoPad:{bd.get('anti_padding',0)}"
            )
        for e in r.errors:
            print(f"    ❌ {e}")
        for w in r.warnings:
            print(f"    ⚠️  {w}")

    print(f"\n{'='*70}")
    print(f"Total: {len(results)} | Pass: {len(results)-fail_count} | Fail: {fail_count}")
    if fail_count > 0:
        print("❌ CONTROLLER FAILED")
        sys.exit(1)
    else:
        print("✅ CONTROLLER PASSED")


def main():
    parser = argparse.ArgumentParser(description="Content Controller — depth-first quality control")
    parser.add_argument("--file", help="Check a single file")
    parser.add_argument("--changed-only", action="store_true", help="Check only git-changed files")
    parser.add_argument("--ai", action="store_true", help="Optional AI layer (requires CONTENT_QA_AI_API_KEY)")
    parser.add_argument("--report", action="store_true", help="Generate report files")
    args = parser.parse_args()

    if args.file:
        files = [os.path.join(REPO_ROOT, args.file.lstrip("/"))]
    elif args.changed_only:
        files = get_git_changed_md_files()
        if not files:
            print("No changed markdown files detected.")
            return
    else:
        files = sorted(glob.glob(POSTS_GLOB, recursive=True))

    if not files:
        print("No files to check.")
        return

    results = []
    for filepath in files:
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        r = check_post(filepath)

        if args.ai:
            ai_result = run_ai_assessment(
                {"title": "", "description": ""},
                "",
                filepath,
            )
            if ai_result:
                r.ai_feedback = ai_result

        results.append(r)

    print_results(results)

    if args.report:
        generate_report(results)

    if args.ai:
        api_key = os.environ.get("CONTENT_QA_AI_API_KEY", "")
        if not api_key:
            print("\n⚠️  --ai requested but CONTENT_QA_AI_API_KEY not set; AI layer skipped")


if __name__ == "__main__":
    main()
