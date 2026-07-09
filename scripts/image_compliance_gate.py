#!/usr/bin/env python3
"""Compliance gate for image publishing.

Enforces image quality/compliance before allowing post to be published.

Hard rules (block publish):
1. Image file must exist
2. Image must be valid (not corrupted)
3. Compliance score ≥ 0.70
4. Relevance score ≥ 0.60
5. No critical compliance issues

Usage:
  python3 scripts/image_compliance_gate.py \
    --post content/posts/example.md \
    --fail-on-missing

  python3 scripts/image_compliance_gate.py \
    --post content/posts/example.md \
    --report reports/gate-decisions.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from audit_generated_images import audit_image, ImageAuditResult
from analyze_post_for_image import analyze_post

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"


@dataclass
class GateDecision:
    """Gate decision result."""
    slug: str
    decision: str  # "ALLOW" | "BLOCK" | "REVIEW"
    reason: str
    audit_result: ImageAuditResult | None = None
    human_review_needed: bool = False


# Gate thresholds
COMPLIANCE_THRESHOLD = 0.70
RELEVANCE_THRESHOLD = 0.60


def make_gate_decision(
    audit_result: ImageAuditResult,
    fail_on_missing: bool = False,
) -> GateDecision:
    """Make publish/block decision based on audit.

    Returns:
        GateDecision with ALLOW | BLOCK | REVIEW
    """
    slug = audit_result.slug

    # Rule 1: Image must exist
    if not audit_result.exists:
        reason = "Image file does not exist"
        return GateDecision(
            slug=slug,
            decision="BLOCK",
            reason=reason,
            audit_result=audit_result,
        )

    # Rule 2: Image must be valid
    if not audit_result.is_valid:
        reason = "Image file is corrupted or invalid"
        return GateDecision(
            slug=slug,
            decision="BLOCK",
            reason=reason,
            audit_result=audit_result,
        )

    # Rule 3: Compliance check
    if audit_result.compliance_score < COMPLIANCE_THRESHOLD:
        reason = f"Compliance score too low: {audit_result.compliance_score*100:.0f}% (need ≥{COMPLIANCE_THRESHOLD*100:.0f}%)"
        decision = "BLOCK" if fail_on_missing else "REVIEW"
        return GateDecision(
            slug=slug,
            decision=decision,
            reason=reason,
            audit_result=audit_result,
            human_review_needed=(decision == "REVIEW"),
        )

    # Rule 4: Relevance check
    if audit_result.relevance_score < RELEVANCE_THRESHOLD:
        reason = f"Relevance score too low: {audit_result.relevance_score*100:.0f}% (need ≥{RELEVANCE_THRESHOLD*100:.0f}%)"
        decision = "REVIEW"
        return GateDecision(
            slug=slug,
            decision=decision,
            reason=reason,
            audit_result=audit_result,
            human_review_needed=True,
        )

    # Rule 5: Critical compliance issues
    critical_issues = [
        issue for issue in audit_result.compliance_issues
        if any(keyword in issue.lower() for keyword in ["fake", "trademark", "forbidden"])
    ]

    if critical_issues:
        reason = f"Critical compliance issues: {'; '.join(critical_issues[:2])}"
        return GateDecision(
            slug=slug,
            decision="BLOCK",
            reason=reason,
            audit_result=audit_result,
        )

    # All checks passed
    return GateDecision(
        slug=slug,
        decision="ALLOW",
        reason=f"✓ Compliance {audit_result.compliance_score*100:.0f}%, Relevance {audit_result.relevance_score*100:.0f}%",
        audit_result=audit_result,
    )


def apply_gate(
    post_path: Path,
    fail_on_missing: bool = False,
) -> GateDecision:
    """Apply compliance gate to a post."""
    post = analyze_post(post_path)
    if not post:
        return GateDecision(
            slug=str(post_path.stem),
            decision="BLOCK",
            reason="Failed to analyze post",
        )

    from dataclasses import asdict
    analysis = asdict(post)

    audit = audit_image(analysis=analysis)
    if not audit:
        return GateDecision(
            slug=post.slug,
            decision="BLOCK",
            reason="Failed to audit image",
        )

    return make_gate_decision(audit, fail_on_missing=fail_on_missing)


def batch_apply_gate(
    fail_on_missing: bool = False,
    limit: int | None = None,
) -> list[GateDecision]:
    """Apply gate to multiple posts."""
    from batch_analyze_posts_for_image import CONTENT_DIR
    posts = sorted([p for p in CONTENT_DIR.glob("*.md") if p.is_file()])

    if limit:
        posts = posts[:limit]

    decisions = []
    for idx, post_path in enumerate(posts, 1):
        try:
            decision = apply_gate(post_path, fail_on_missing=fail_on_missing)
            decisions.append(decision)
            if idx % 20 == 0:
                print(f"  {idx}/{len(posts)}")
        except Exception as e:
            decisions.append(GateDecision(
                slug=post_path.stem,
                decision="BLOCK",
                reason=f"Gate error: {e}",
            ))

    return decisions


def write_gate_report(decisions: list[GateDecision], output_path: Path) -> None:
    """Write gate decisions to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "decisions": [
            {
                "slug": d.slug,
                "decision": d.decision,
                "reason": d.reason,
                "needs_review": d.human_review_needed,
            }
            for d in decisions
        ],
        "summary": {
            "total": len(decisions),
            "allowed": sum(1 for d in decisions if d.decision == "ALLOW"),
            "blocked": sum(1 for d in decisions if d.decision == "BLOCK"),
            "review": sum(1 for d in decisions if d.decision == "REVIEW"),
        },
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Wrote: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Image compliance gate")
    parser.add_argument("--post", help="Post path")
    parser.add_argument("--batch", action="store_true", help="Check all posts")
    parser.add_argument("--limit", type=int, help="Batch limit")
    parser.add_argument("--fail-on-missing", action="store_true",
                       help="Block instead of review if compliance low")
    parser.add_argument("--report", help="Write decisions JSON")

    args = parser.parse_args()

    decisions = []

    if args.batch:
        decisions = batch_apply_gate(
            fail_on_missing=args.fail_on_missing,
            limit=args.limit,
        )
    elif args.post:
        decision = apply_gate(Path(args.post), fail_on_missing=args.fail_on_missing)
        decisions = [decision]
    else:
        parser.print_help()
        return 1

    # Report
    if args.report:
        write_gate_report(decisions, Path(args.report))

    # Print summary
    allowed = sum(1 for d in decisions if d.decision == "ALLOW")
    blocked = sum(1 for d in decisions if d.decision == "BLOCK")
    review = sum(1 for d in decisions if d.decision == "REVIEW")

    print(f"\n📊 Gate decision: {allowed} ALLOW, {blocked} BLOCK, {review} REVIEW")

    if len(decisions) == 1:
        d = decisions[0]
        print(f"{d.decision}: {d.reason}")
        return 0 if d.decision == "ALLOW" else 1

    return 0 if blocked == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
