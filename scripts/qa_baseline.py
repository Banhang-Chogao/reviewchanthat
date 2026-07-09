#!/usr/bin/env python3
"""
QA Baseline Debt Classifier - separates baseline debt from new compliance issues.

Classifies compliance errors as:
  - BASELINE: known issues in old content (don't block deploy)
  - NEW: previously unreported issues (block deploy)
  - RESOLVED: previously baseline issues now gone

Usage:
  python scripts/qa_baseline.py
  python scripts/qa_baseline.py --baseline-json data/qa-baseline-debt.json
  python scripts/qa_baseline.py --compliance-report data/compliance-report.json
  python scripts/qa_baseline.py --out reports/qa-baseline-check.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_BASELINE_PATH = DATA_DIR / "qa-baseline-debt.json"
DEFAULT_COMPLIANCE_REPORT = DATA_DIR / "compliance-report.json"
DEFAULT_OUTPUT = REPORTS_DIR / "qa-baseline-check.json"


@dataclass
class IssueClassification:
    """Classification of a single issue."""
    code: str
    file: str
    severity: str
    message: str
    classification: str  # "baseline", "new", "resolved"
    reason: str = ""


@dataclass
class ClassificationReport:
    """Report of issue classifications."""
    baseline_issues: list[IssueClassification] = field(default_factory=list)
    new_issues: list[IssueClassification] = field(default_factory=list)
    resolved_issues: list[IssueClassification] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=lambda: {
        "total_compliance_errors": 0,
        "baseline_errors": 0,
        "new_errors": 0,
        "resolved_errors": 0,
        "blocks_deploy": False,
    })
    timestamp: str = ""
    baseline_path: str = ""
    compliance_report_path: str = ""


def load_json(path: Path | str, default: Any = None) -> Any:
    """Load JSON file, return default if not found."""
    path = Path(path)
    if not path.exists():
        return default or {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Error loading {path}: {exc}", file=sys.stderr)
        return default or {}


def normalize_issue_key(code: str, file: str) -> str:
    """Create normalized key for issue deduplication."""
    return f"{code}:{file}"


def extract_affected_posts_from_baseline(baseline: dict) -> dict[str, set[str]]:
    """Extract all posts affected by known issues from baseline debt."""
    affected: dict[str, set[str]] = {}
    known_issues = baseline.get("known_issues", {})
    for code, issue_info in known_issues.items():
        if isinstance(issue_info, dict):
            posts = issue_info.get("affected_posts", [])
            if posts:
                affected[code] = set(posts)
    return affected


def post_name_from_path(file_path: str) -> str:
    """Extract post name (slug) from file path."""
    # content/posts/post-name.md -> post-name
    if "/" in file_path:
        name = file_path.split("/")[-1]
    else:
        name = file_path
    return name.replace(".md", "").strip()


def is_baseline_issue(issue: dict, baseline_affected: dict[str, set[str]]) -> bool:
    """Check if an issue is in the baseline debt."""
    code = issue.get("code", "")
    file = issue.get("file", "")

    # Check if this code is a known baseline issue
    if code not in baseline_affected:
        return False

    # Check if this specific post is affected
    post_name = post_name_from_path(file)
    return post_name in baseline_affected[code]


def classify_issues(
    compliance_issues: list[dict],
    baseline_debt: dict,
) -> ClassificationReport:
    """Classify compliance issues as baseline, new, or resolved."""
    report = ClassificationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        baseline_path=str(DEFAULT_BASELINE_PATH),
        compliance_report_path=str(DEFAULT_COMPLIANCE_REPORT),
    )

    # Extract baseline affected posts by code
    baseline_affected = extract_affected_posts_from_baseline(baseline_debt)

    # Track which baseline issues we actually see in compliance report
    seen_baseline_posts: dict[str, set[str]] = {}

    # Classify each issue
    for issue in compliance_issues:
        severity = issue.get("severity", "WARN")
        code = issue.get("code", "UNKNOWN")
        file = issue.get("file", "")
        message = issue.get("message", "")

        # Only count ERRORs as potential blockers
        if severity != "ERROR":
            continue

        report.summary["total_compliance_errors"] += 1

        # Check if this is a baseline issue
        if is_baseline_issue(issue, baseline_affected):
            classification = "baseline"
            reason = f"Known issue in baseline debt (code={code})"
            report.baseline_issues.append(IssueClassification(
                code=code,
                file=file,
                severity=severity,
                message=message,
                classification=classification,
                reason=reason,
            ))
            report.summary["baseline_errors"] += 1

            # Track that we saw this post's issue
            post_name = post_name_from_path(file)
            seen_baseline_posts.setdefault(code, set()).add(post_name)
        else:
            classification = "new"
            reason = f"Not in baseline debt - NEW error (code={code})"
            report.new_issues.append(IssueClassification(
                code=code,
                file=file,
                severity=severity,
                message=message,
                classification=classification,
                reason=reason,
            ))
            report.summary["new_errors"] += 1

    # Check for resolved issues (in baseline but not in current report)
    for code, posts_set in baseline_affected.items():
        resolved_posts = posts_set - seen_baseline_posts.get(code, set())
        for post_name in resolved_posts:
            # Reconstruct file path for reporting
            file_path = f"content/posts/{post_name}.md"
            report.resolved_issues.append(IssueClassification(
                code=code,
                file=file_path,
                severity="ERROR",
                message=f"Previously {code}, now resolved",
                classification="resolved",
                reason="Issue no longer appears in compliance report",
            ))
            report.summary["resolved_errors"] += 1

    # Determine if deploy should be blocked
    # Block only on NEW errors, not baseline
    report.summary["blocks_deploy"] = report.summary["new_errors"] > 0

    return report


def print_report(report: ClassificationReport) -> None:
    """Print human-readable classification report."""
    print("\n" + "=" * 70)
    print("QA BASELINE DEBT CLASSIFICATION REPORT")
    print("=" * 70)

    summary = report.summary
    print(f"\nSummary:")
    print(f"  Total errors in compliance report: {summary['total_compliance_errors']}")
    print(f"  Baseline (known) errors:           {summary['baseline_errors']}")
    print(f"  New (unreported) errors:           {summary['new_errors']}")
    print(f"  Resolved (fixed) issues:           {summary['resolved_errors']}")
    print(f"\n  🚀 Deploy Status:                  ", end="")
    if summary["blocks_deploy"]:
        print("❌ BLOCKED - New errors found")
    else:
        print("✅ OK - Only baseline debt, no new errors")

    if report.new_issues:
        print(f"\n{'NEW ERRORS (BLOCK DEPLOY)':^70}")
        print("-" * 70)
        for issue in sorted(report.new_issues, key=lambda x: (x.file, x.code)):
            print(f"  [{issue.code}] {issue.file}")
            print(f"    Severity: {issue.severity}")
            print(f"    Message:  {issue.message}")
            print(f"    Reason:   {issue.reason}")
            print()

    if report.baseline_issues:
        print(f"\n{'BASELINE ISSUES (ACCEPTED DEBT)':^70}")
        print("-" * 70)
        # Group by code
        by_code = {}
        for issue in report.baseline_issues:
            by_code.setdefault(issue.code, []).append(issue)

        for code in sorted(by_code.keys()):
            issues = by_code[code]
            print(f"  {code}: {len(issues)} issue(s)")
            for issue in sorted(issues, key=lambda x: x.file):
                print(f"    - {issue.file}")

    if report.resolved_issues:
        print(f"\n{'RESOLVED ISSUES (FIXED)':^70}")
        print("-" * 70)
        for issue in sorted(report.resolved_issues, key=lambda x: (x.file, x.code)):
            print(f"  [{issue.code}] {issue.file} - now resolved ✓")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify compliance issues as baseline debt vs new errors"
    )
    parser.add_argument(
        "--baseline-json",
        default=str(DEFAULT_BASELINE_PATH),
        help="Path to baseline debt JSON",
    )
    parser.add_argument(
        "--compliance-report",
        default=str(DEFAULT_COMPLIANCE_REPORT),
        help="Path to compliance report JSON",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="Output classification report path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed report to console",
    )

    args = parser.parse_args()

    # Load input files
    baseline_debt = load_json(args.baseline_json, {})
    compliance_report = load_json(args.compliance_report, {})

    # Extract issues from compliance report
    compliance_issues = compliance_report.get("issues", [])

    if not compliance_issues:
        print("No compliance issues found in report")
        sys.exit(0)

    # Classify issues
    report = classify_issues(compliance_issues, baseline_debt)

    # Print summary
    if args.verbose:
        print_report(report)
    else:
        summary = report.summary
        print(f"Compliance analysis:")
        print(f"  Total errors: {summary['total_compliance_errors']}")
        print(f"  Baseline:     {summary['baseline_errors']}")
        print(f"  New:          {summary['new_errors']}")
        print(f"  Resolved:     {summary['resolved_errors']}")
        if summary["new_errors"] > 0:
            print(f"\n❌ Deploy blocked: {summary['new_errors']} new error(s)")
        else:
            print(f"\n✅ Deploy allowed: only baseline debt, no new errors")

    # Write JSON report
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report_data = {
        "timestamp": report.timestamp,
        "summary": report.summary,
        "baseline": [asdict(i) for i in report.baseline_issues],
        "new": [asdict(i) for i in report.new_issues],
        "resolved": [asdict(i) for i in report.resolved_issues],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nReport written: {out_path}")

    # Exit with error code only if there are NEW errors
    return 1 if report.summary["blocks_deploy"] else 0


if __name__ == "__main__":
    sys.exit(main())
