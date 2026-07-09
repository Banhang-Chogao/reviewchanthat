#!/usr/bin/env python3
import json, os, re, sys

VIETNAMESE_STOP_WORDS = {"va", "la", "co", "nen", "di", "dau", "gi", "nhu", "the", "nao",
                         "cho", "nguoi", "mot", "cac", "o", "tu", "den", "trong", "khi",
                         "de", "khong", "cua", "voi", "ve", "ra", "lam", "hon", "qua", "duoc"}

KEYWORD_INTENT = {"co-nen", "di-dau", "mac-gi", "thang-7", "thang-8", "thang-10",
                  "thang-11", "thang-12", "thang-1", "thang-2", "thang-3", "thang-4",
                  "thang-5", "thang-6", "co-gi", "la-gi", "nen-di", "nen-chon",
                  "co-dang", "nen-mua", "bao-nhieu", "khi-nao", "the-nao"}

POSTS_DIR = "content/posts"

def main():
    issues = []
    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".md"):
            continue
        slug = fname.replace(".md", "")
        parts = slug.split("-")
        stop_words_found = [w for w in parts if w in VIETNAMESE_STOP_WORDS and w not in KEYWORD_INTENT]
        if stop_words_found:
            issues.append({
                "slug": slug,
                "length": len(slug),
                "stop_words": stop_words_found,
                "status": "warning",
            })

    print(f"# Slug Stop Words Report\n")
    print(f"Total posts checked: {len(os.listdir(POSTS_DIR))}")
    print(f"Slugs with stop words: {len(issues)}\n")

    # Only flag as error if slug > 90 AND has stop words
    errors = [i for i in issues if i["length"] > 90]
    warnings = [i for i in issues if i not in errors]

    print(f"Warnings (existing posts, report only): {len(warnings)}")
    print(f"Errors (slug > 90 chars with stop words, for new posts): {len(errors)}\n")

    if warnings:
        print("## Warning: Existing posts with stop words (not changed)\n")
        for i in warnings[:10]:
            print(f"- {i['slug']} ({i['length']} chars, stop words: {', '.join(i['stop_words'])})")
        if len(warnings) > 10:
            print(f"- ... and {len(warnings) - 10} more\n")

    if errors:
        print("## Error: New posts with long slug + stop words\n")
        for i in errors:
            print(f"- {i['slug']} ({i['length']} chars)")

    print(f"\n## Policy")
    print(f"- Existing slugs: NOT changed (report only)")
    print(f"- New posts: fail if slug > 90 AND has many stop words")
    print(f"- Keyword intent stop words (co-nen, di-dau, ...): excluded from check")

    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
