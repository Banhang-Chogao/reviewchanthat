#!/usr/bin/env python3
"""Batch analyze all blog posts for image context generation.

Usage:
  python3 scripts/batch_analyze_posts_for_image.py
  python3 scripts/batch_analyze_posts_for_image.py --limit 10  # Analyze first 10 posts
  python3 scripts/batch_analyze_posts_for_image.py --json reports/image-context-all.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from analyze_post_for_image import IMAGE_CONTEXT_DIR, analyze_post, write_json_report

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
REPORTS_DIR = REPO_ROOT / "reports"


def batch_analyze(limit: int | None = None) -> list[dict]:
    """Analyze all posts, optionally limited to N posts."""
    posts = sorted([p for p in CONTENT_DIR.glob("*.md") if p.is_file()])

    if limit:
        posts = posts[:limit]

    results = []
    errors = []

    print(f"Analyzing {len(posts)} posts...")

    for idx, post_path in enumerate(posts, 1):
        try:
            analysis = analyze_post(post_path)
            if analysis:
                results.append({
                    "slug": analysis.slug,
                    "title": analysis.title[:60],
                    "topic": analysis.primary_topic,
                    "confidence": round(analysis.topic_confidence, 2),
                    "tone": ",".join(analysis.tone),
                    "has_forbidden": analysis.has_forbidden_items,
                })

                # Write individual JSON
                output_json = IMAGE_CONTEXT_DIR / f"{analysis.slug}.json"
                write_json_report(analysis, output_json)

                if idx % 20 == 0:
                    print(f"  {idx}/{len(posts)} ✓")
        except Exception as e:
            errors.append(f"{post_path.name}: {e}")
            print(f"  ✗ {post_path.name}: {type(e).__name__}")

    return results, errors


def write_summary_report(results: list[dict], errors: list[str]) -> None:
    """Write summary report of all analyses."""
    output_json = REPORTS_DIR / "image-context-summary.json"
    output_md = REPORTS_DIR / "image-context-summary.md"

    # Group by topic
    by_topic = defaultdict(list)
    for result in results:
        by_topic[result["topic"]].append(result)

    summary = {
        "total_posts": len(results),
        "errors": len(errors),
        "by_topic": {
            topic: {
                "count": len(posts),
                "avg_confidence": round(sum(p["confidence"] for p in posts) / len(posts), 2),
                "samples": [p["slug"] for p in posts[:3]],
            }
            for topic, posts in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True)
        },
    }

    # Write JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✓ Wrote: {output_json}")

    # Write Markdown
    lines = [
        "# Image Context Analysis Summary",
        "",
        f"**Total posts analyzed:** {len(results)}",
        f"**Errors:** {len(errors)}",
        "",
        "## Topic Distribution",
        "",
    ]

    for topic, posts_list in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(posts_list)
        avg_conf = round(sum(p["confidence"] for p in posts_list) / count, 2)
        lines.append(f"### {topic.replace('_', ' ').title()} ({count} posts)")
        lines.append(f"- Avg confidence: {avg_conf*100:.0f}%")
        lines.append(f"- Samples: {', '.join(f'`{p['slug']}`' for p in posts_list[:3])}")
        lines.append("")

    if errors:
        lines.extend([
            "## Errors",
            "",
        ])
        for error in errors[:20]:
            lines.append(f"- {error}")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✓ Wrote: {output_md}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch analyze all posts for image context")
    parser.add_argument("--limit", type=int, help="Analyze only first N posts")
    parser.add_argument("--json", help="Write summary JSON to this path")

    args = parser.parse_args()

    results, errors = batch_analyze(limit=args.limit)

    # Write summary
    write_summary_report(results, errors)

    # Optional JSON output
    if args.json:
        output_path = Path(args.json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✓ Wrote: {output_path}")

    print(f"\n✓ Analysis complete: {len(results)} posts, {len(errors)} errors")
    if errors:
        print(f"First error: {errors[0]}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
