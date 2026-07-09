#!/usr/bin/env python3
import argparse, json, re, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import frontmatter

POSTS_DIR = "content/posts"
STOP_WORDS = {"va", "la", "co", "nen", "di", "dau", "gi", "nhu", "the", "nao",
              "cho", "nguoi", "mot", "cac", "o", "tu", "den", "trong", "khi",
              "de", "khong", "cua", "voi", "ve", "ra", "lam", "hon", "qua", "duoc"}

def slug_split(slug):
    return slug.replace("-", " ").split()

def detect_topic(slug, title, cats, tags, series):
    title_lower = (title or "").lower()
    slug_lower = slug.lower()
    cats_lower = [c.lower() for c in (cats or [])]
    tags_lower = [t.lower() for t in (tags or [])]
    series_lower = [s.lower() for s in (series or [])]
    all_text = " ".join([title_lower, slug_lower] + cats_lower + tags_lower + series_lower)

    if any(k in all_text for k in ["thai-lan", "bangkok", "phuket", "chiang-mai"]):
        return "thailand"
    if any(k in all_text for k in ["han-quoc", "korea", "seoul", "busan", "jeju"]):
        return "korea"
    if any(k in all_text for k in ["iphone", "apple", "macos", "ios", "macbook", "wwdc"]):
        return "apple"
    if any(k in all_text for k in ["starbucks"]):
        return "starbucks"
    if any(k in all_text for k in ["visa"]):
        return "visa"
    return "other"

def shorten_title(title, slug, cats, tags, series):
    topic = detect_topic(slug, title, cats, tags, series)
    length = len(title)
    if length <= 65:
        return None

    title_lower = title.lower()

    removals = [
        r" năm \d{4}", r" năm \d{4} ",
        r" gợi ý", r" tốt nhất",
        r" hợp nhất", r" tuyệt vời",
        r" đầy đủ", r" chi tiết",
        r" dành cho",
        r" theo kinh nghiệm",
        r" từ A đến Z",
        r" bạn cần biết",
        r" nên biết",
        r" có thể bạn chưa biết",
    ]

    candidate = title
    for pat in removals:
        candidate = re.sub(pat, "", candidate, flags=re.IGNORECASE).strip()
        candidate = re.sub(r"\s+", " ", candidate).strip()
        candidate = re.sub(r"[,;:]+$", "", candidate).strip()
        if len(candidate) <= 60:
            break

    if len(candidate) > 60:
        words = candidate.split()
        for i in range(len(words) - 1, -1, -1):
            if words[i].lower() in STOP_WORDS and len(words[i]) <= 3:
                continue
            test = " ".join(words[:i])
            if len(test) <= 60:
                candidate = test
                break

    candidate = candidate.strip().rstrip(",;:")
    if candidate.endswith(("?", "!")):
        pass

    if len(candidate) < 30 or len(candidate) >= len(title) - 5:
        return None

    candidate = candidate.strip()
    if candidate[0].islower():
        candidate = candidate[0].upper() + candidate[1:]

    return candidate

def process_post(filepath, dry_run):
    with open(filepath) as f:
        post = frontmatter.load(f)

    meta = post.metadata
    title = meta.get("title", "")
    slug = meta.get("slug", os.path.splitext(os.path.basename(filepath))[0])
    cats = meta.get("categories", [])
    tags = meta.get("tags", [])
    series = meta.get("series", [])

    if not title or len(title) <= 65:
        return None

    if meta.get("seo_title"):
        return None

    seo = shorten_title(title, slug, cats, tags, series)
    if not seo:
        return None

    result = {
        "file": filepath,
        "slug": slug,
        "title": title,
        "title_length": len(title),
        "seo_title": seo,
        "seo_title_length": len(seo),
    }

    if not dry_run:
        meta["seo_title"] = seo
        with open(filepath, "w") as f:
            frontmatter.dump(post, f)

    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--report", default="reports/seo-title-report.md")
    args = parser.parse_args()

    if not os.path.isdir(POSTS_DIR):
        print(f"Posts directory not found: {POSTS_DIR}")
        return

    posts = []
    for fname in os.listdir(POSTS_DIR):
        if fname.endswith(".md"):
            posts.append(os.path.join(POSTS_DIR, fname))

    results = []
    for fp in posts:
        r = process_post(fp, dry_run=args.dry_run)
        if r:
            results.append(r)

    results.sort(key=lambda x: -x["title_length"])

    if args.top and len(results) > args.top:
        results = results[:args.top]

    report_lines = [
        f"# SEO Title Optimization Report\n",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'WRITE'}\n",
        f"\n## Summary\n",
        f"- Posts with long titles (>65 chars): {len(results) + sum(1 for f in posts if len(frontmatter.load(f).metadata.get('title', '')) > 65)} total\n",
        f"- SEO titles generated: {len(results)}\n",
    ]

    if results:
        report_lines.append(f"\n## SEO Titles Added\n\n")
        report_lines.append("| Slug | Original Length | SEO Title | SEO Length |\n")
        report_lines.append("|------|----------------|-----------|------------|\n")
        for r in results:
            report_lines.append(f"| {r['slug']} | {r['title_length']} | {r['seo_title']} | {r['seo_title_length']} |\n")

    report = "".join(report_lines)
    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w") as f:
        f.write(report)

    print(f"\nSEO Title Report: {args.report}")
    print(f"SEO titles {'generated (dry-run)' if args.dry_run else 'written'}: {len(results)}")
    for r in results[:5]:
        print(f"  [{r['slug']}] {r['title_length']} → {r['seo_title_length']}: {r['seo_title']}")

if __name__ == "__main__":
    main()
