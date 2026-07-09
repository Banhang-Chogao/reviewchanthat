#!/usr/bin/env python3
"""QA: image relevance metadata and gate compliance across posts."""

from __future__ import annotations

import json
import os
import sys

import frontmatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, "content", "posts")
REPORT_JSON = os.path.join(ROOT, "reports", "image-relevance-report.json")
REPORT_MD = os.path.join(ROOT, "reports", "image-relevance-report.md")

FLOWER_TERMS = ("flower", "rose", "bouquet", "bloom")
LEAF_TERMS = ("autumn", "fallen leaves", "dry leaves", "lá rụng", "mùa thu", "foliage")


def scan_posts() -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []

    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        post = frontmatter.load(fpath)
        meta = post.metadata
        slug = meta.get("slug", fname.replace(".md", ""))
        title = meta.get("title", slug)
        status = meta.get("image_status", "")
        image = meta.get("image", "")
        reject_reason = meta.get("image_reject_reason", "")
        row = {
            "slug": slug,
            "title": title,
            "image_status": status,
            "image": image,
            "image_provider": meta.get("image_provider", ""),
            "image_query": meta.get("image_query", ""),
            "image_total_score": meta.get("image_total_score", ""),
            "image_reject_reason": reject_reason,
        }
        rows.append(row)

        if status in {"needs_review", "needs_image"} and image:
            errors.append(f"{slug}: image present while image_status={status}")

        if reject_reason and image and status != "verified":
            errors.append(f"{slug}: image_reject_reason set but image still assigned")

        if status == "verified":
            if not meta.get("image_source_url"):
                errors.append(f"{slug}: verified image missing image_source_url")
            score = meta.get("image_total_score")
            if score not in (None, "") and float(score) < 72:
                errors.append(f"{slug}: image_total_score below threshold ({score})")

        corpus = f"{title} {post.content[:1200]}".lower()
        if any(t in corpus for t in LEAF_TERMS):
            blob = " ".join(
                str(meta.get(k, "")) for k in (
                    "image_query", "image_alt", "image_source_url", "image_creator"
                )
            ).lower()
            if any(term in blob for term in FLOWER_TERMS):
                errors.append(f"{slug}: autumn/leaves topic but image metadata mentions flower")

    return rows, errors


def write_reports(rows: list[dict], errors: list[str]) -> None:
    os.makedirs(os.path.dirname(REPORT_JSON), exist_ok=True)
    payload = {"summary": {"posts": len(rows), "errors": len(errors)}, "posts": rows, "errors": errors}
    with open(REPORT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    lines = ["# Image Relevance Report", "", f"Posts scanned: {len(rows)}", f"Errors: {len(errors)}", ""]
    if errors:
        lines.append("## Errors")
        lines.extend(f"- {err}" for err in errors)
        lines.append("")
    lines.append("## Posts")
    for row in rows[:200]:
        lines.append(
            f"- `{row['slug']}` status={row.get('image_status') or 'legacy'} "
            f"score={row.get('image_total_score') or '-'} query={row.get('image_query') or '-'}"
        )
    with open(REPORT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    rows, errors = scan_posts()
    write_reports(rows, errors)
    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    if errors:
        print(f"FAIL: {len(errors)} image relevance issues")
        for err in errors[:20]:
            print(f"  - {err}")
        return 1
    print("PASS: image relevance checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())