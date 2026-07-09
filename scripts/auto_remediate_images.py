#!/usr/bin/env python3
"""Automatic remediation for failed images.

If image fails gate, tries to fix:
1. Re-generate with different backend
2. Adjust parameters (size, style)
3. Create better placeholder
4. Queue for manual review

Usage:
  python3 scripts/auto_remediate_images.py --post content/posts/post.md
  python3 scripts/auto_remediate_images.py --batch --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_generated_images import audit_image
from generate_hero_image import generate_image, ImageGenerationConfig
from analyze_post_for_image import analyze_post
from image_compliance_gate import apply_gate

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"


@dataclass
class RemediationAttempt:
    """Record of remediation attempt."""
    slug: str
    original_reason: str
    attempt: int
    backend: str
    size: str
    result: str  # SUCCESS | FAILED | MANUAL_REVIEW


def remediate_image(post_path: Path, max_attempts: int = 3, dry_run: bool = False) -> RemediationAttempt | None:
    """Attempt to fix failed image."""
    post = analyze_post(post_path)
    if not post:
        return None

    from dataclasses import asdict
    analysis = asdict(post)
    slug = post.slug

    # Check if passes already
    gate = apply_gate(post_path)
    if gate.decision == "ALLOW":
        print(f"✓ {slug} already passes")
        return None

    print(f"\n🔧 Remediating {slug}: {gate.reason}")

    # Remediation strategy
    backends = ["placeholder", "dalle3"]
    sizes = ["1200x630", "1024x1024"]

    for attempt in range(1, max_attempts + 1):
        backend = backends[(attempt - 1) % len(backends)]
        size = sizes[(attempt - 1) % len(sizes)]

        print(f"  Attempt {attempt}: {backend}, size {size}")

        if dry_run:
            return RemediationAttempt(
                slug=slug,
                original_reason=gate.reason,
                attempt=attempt,
                backend=backend,
                size=size,
                result="DRY_RUN",
            )

        config = ImageGenerationConfig(
            backend=backend,
            size=size,
            quality="standard",
            style="natural",
        )

        # Generate new image
        result = generate_image(analysis, config)
        if not result:
            continue

        # Audit new image
        audit = audit_image(analysis=analysis)
        if audit and audit.passes_audit:
            print(f"  ✅ Remediation successful!")
            return RemediationAttempt(
                slug=slug,
                original_reason=gate.reason,
                attempt=attempt,
                backend=backend,
                size=size,
                result="SUCCESS",
            )

    # All attempts failed, queue for review
    print(f"  ⚠️  Queuing for manual review")
    return RemediationAttempt(
        slug=slug,
        original_reason=gate.reason,
        attempt=max_attempts,
        backend=backends[-1],
        size=sizes[-1],
        result="MANUAL_REVIEW",
    )


def batch_remediate(dry_run: bool = False, limit: int | None = None) -> list[RemediationAttempt]:
    """Remediate all failed images."""
    from batch_analyze_posts_for_image import CONTENT_DIR
    posts = sorted([p for p in CONTENT_DIR.glob("*.md") if p.is_file()])

    if limit:
        posts = posts[:limit]

    results = []
    for idx, post_path in enumerate(posts, 1):
        try:
            result = remediate_image(post_path, dry_run=dry_run)
            if result:
                results.append(result)
            if idx % 20 == 0:
                print(f"  {idx}/{len(posts)}")
        except Exception as e:
            print(f"  ✗ {post_path.stem}: {e}")

    return results


def write_remediation_report(results: list[RemediationAttempt], output_path: Path) -> None:
    """Write remediation results."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    successful = sum(1 for r in results if r.result == "SUCCESS")
    review = sum(1 for r in results if r.result == "MANUAL_REVIEW")

    data = {
        "summary": {
            "total": len(results),
            "successful": successful,
            "manual_review": review,
        },
        "results": [
            {
                "slug": r.slug,
                "original_reason": r.original_reason,
                "attempt": r.attempt,
                "backend": r.backend,
                "result": r.result,
            }
            for r in results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Report: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-remediate failed images")
    parser.add_argument("--post", help="Post path")
    parser.add_argument("--batch", action="store_true", help="Remediate all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--report", help="Write report JSON")

    args = parser.parse_args()

    results = []
    if args.batch:
        results = batch_remediate(dry_run=args.dry_run, limit=args.limit)
    elif args.post:
        result = remediate_image(Path(args.post), dry_run=args.dry_run)
        if result:
            results = [result]
    else:
        parser.print_help()
        return 1

    if args.report:
        write_remediation_report(results, Path(args.report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
