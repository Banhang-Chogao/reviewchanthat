#!/usr/bin/env python3
"""
Generate AI-style extractive summaries for Hugo blog posts.

Scans content/posts/*.md, parses front matter, generates bullet-point
summaries from body text using local extractive methods (no API required).

Usage:
  python scripts/generate_summaries.py              # process new posts only
  python scripts/generate_summaries.py --force      # regenerate all
  python scripts/generate_summaries.py --dry-run    # preview only
"""

import argparse
import glob
import os
import re
import sys

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(1)

POSTS_GLOB = "content/posts/**/*.md"
SUMMARY_KEY = "ai_summary"
SUMMARY_TITLE = "Tóm tắt bài viết"
DISCLAIMER = (
    "Nội dung này được tóm tắt bằng AI và có thể chứa thông tin không chính xác"
)
MIN_BODY_LENGTH = 100
MAX_ITEMS = 4
MIN_ITEMS = 1


def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def sanitize_summary_item(text):
    text = clean_text(text)
    text = re.sub(r"^[-•*]\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def dict_to_string(item):
    if not item:
        return ""
    if len(item) == 1:
        key, value = next(iter(item.items()))
        key = clean_text(str(key))
        value = clean_text(str(value))
        if key and value:
            return f"{key}: {value}"
        return key or value
    parts = []
    for key, value in item.items():
        key = clean_text(str(key))
        value = clean_text(str(value))
        if key and value:
            parts.append(f"{key}: {value}")
        else:
            parts.append(key or value)
    return "; ".join(parts)


def item_to_string(item):
    if isinstance(item, str):
        return sanitize_summary_item(item)
    if isinstance(item, dict):
        return sanitize_summary_item(dict_to_string(item))
    if isinstance(item, (list, tuple)):
        return sanitize_summary_item(
            " ".join(part for part in (item_to_string(entry) for entry in item) if part)
        )
    return sanitize_summary_item(str(item))


def ensure_summary_items(items):
    """Coerce summary bullets to plain strings for YAML/Hugo front matter."""
    normalized = []
    for item in items or []:
        text = item_to_string(item)
        if text and "map[" not in text:
            normalized.append(text)
    return normalized


def clean_body(body):
    """Remove headings, images, shortcodes, HTML tags, horizontal rules, links."""
    text = body
    text = re.sub(r"^#{1,6}\s.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"{{<.*?>}}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\*.*?\*\*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"^\s*[-*]\s", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text):
    """Split text into sentences, handling Vietnamese gracefully."""
    text = re.sub(r"\n+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 20:
            result.append(sentence)
    return result


def score_sentence(sentence, index, total, keywords):
    """Score a sentence for extractive summarization."""
    score = 0.0
    if total > 0:
        score += max(0, 1.0 - (index / total) * 0.6)
    words = len(sentence.split())
    if 10 <= words <= 40:
        score += 0.3
    elif words < 5:
        score -= 0.5
    if keywords:
        kw_found = sum(1 for kw in keywords if kw.lower() in sentence.lower())
        score += kw_found * 0.15
    if not sentence.strip().endswith("?"):
        score += 0.1
    if words < 8:
        score -= 0.2
    return score


def extract_keywords(text, top_n=5):
    """Simple keyword extraction by word frequency (Vietnamese-aware)."""
    stop_words = {
        "và", "của", "có", "là", "một", "những", "được", "các", "cho",
        "trong", "với", "không", "người", "bạn", "khi", "sẽ", "đã",
        "đang", "này", "đó", "hơn", "như", "cũng", "vào", "ra", "về",
        "lên", "xuống", "qua", "lại", "nên", "phải", "từ", "ở", "đi",
        "lại", "rất", "nhiều", "ít", "thì", "để", "mà", "bị", "được",
        "sau", "trước", "trên", "dưới", "giữa", "mỗi", "mọi", "tất cả",
        "hay", "hoặc", "nếu", "thì", "vì", "nên", "tuy", "nhưng",
    }
    words = re.findall(
        r"[a-zA-Zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+",
        text.lower(),
    )
    freq = {}
    for word in words:
        if word not in stop_words and len(word) > 2:
            freq[word] = freq.get(word, 0) + 1
    sorted_kw = sorted(freq.items(), key=lambda x: -x[1])
    return [kw for kw, _ in sorted_kw[:top_n]]


def generate_summary(body):
    """Generate bullet-point summary from body text."""
    cleaned = clean_body(body)
    if len(cleaned) < MIN_BODY_LENGTH:
        return None
    sentences = split_sentences(cleaned)
    if len(sentences) < 2:
        return None
    keywords = extract_keywords(cleaned)
    scored = []
    for i, sent in enumerate(sentences):
        score = score_sentence(sent, i, len(sentences), keywords)
        scored.append((score, sent))
    scored.sort(key=lambda x: -x[0])
    num_items = min(MAX_ITEMS, max(MIN_ITEMS, len(sentences) // 3))
    num_items = min(num_items, len(scored))
    selected = [s[1] for s in scored[:num_items]]
    selected.sort(key=lambda s: sentences.index(s) if s in sentences else 0)
    bullets = []
    for sentence in selected:
        sentence = re.sub(r"^\*\*|\*\*$", "", sentence)
        sentence = sanitize_summary_item(sentence)
        sentence = sentence.rstrip(".,;:") + "."
        if len(sentence) > 200:
            sentence = sentence[:197] + "..."
        bullets.append(sentence)
    return ensure_summary_items(bullets)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI-style summaries for Hugo blog posts"
    )
    parser.add_argument("--force", action="store_true",
                        help="Regenerate summaries even if already present")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    args = parser.parse_args()

    posts = glob.glob(POSTS_GLOB, recursive=True)
    if not posts:
        print("No posts found in content/posts/")
        sys.exit(1)

    for filepath in sorted(posts):
        with open(filepath, "r", encoding="utf-8") as handle:
            try:
                post = frontmatter.load(handle)
            except Exception as exc:
                print(f"  [SKIP] Cannot parse {filepath}: {exc}")
                continue

        body = post.content
        if not body or len(body.strip()) < MIN_BODY_LENGTH:
            print(f"  [SKIP] {filepath}: body too short")
            continue

        meta = post.metadata
        existing = meta.get(SUMMARY_KEY, {})

        if not args.force and existing and existing.get("items"):
            existing_items = ensure_summary_items(existing.get("items", []))
            if existing_items != existing.get("items", []):
                if args.dry_run:
                    print(f"  [DRY]  {filepath}: would normalize existing summary items")
                else:
                    existing["items"] = existing_items
                    meta[SUMMARY_KEY] = existing
                    post.metadata = meta
                    with open(filepath, "w", encoding="utf-8") as handle:
                        frontmatter.dump(post, handle)
                    print(f"  [FIX]  {filepath}: normalized existing summary items")
            else:
                print(f"  [OK]   {filepath}: summary exists (use --force to regenerate)")
            continue

        bullets = generate_summary(body)
        if not bullets:
            print(f"  [SKIP] {filepath}: could not generate summary")
            continue

        summary_data = {
            "enabled": True,
            "title": SUMMARY_TITLE,
            "collapsed": False,
            "disclaimer": DISCLAIMER,
            "items": bullets,
        }

        if args.dry_run:
            print(f"  [DRY]  {filepath}:")
            for bullet in bullets:
                print(f"         • {bullet}")
            continue

        meta[SUMMARY_KEY] = summary_data
        post.metadata = meta

        with open(filepath, "w", encoding="utf-8") as handle:
            frontmatter.dump(post, handle)

        print(f"  [OK]   {filepath}: {len(bullets)} items")

    print("Done.")


if __name__ == "__main__":
    main()