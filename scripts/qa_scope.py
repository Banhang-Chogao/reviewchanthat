#!/usr/bin/env python3
"""QA scope: only check changed files, track baseline debt on old content."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
DATA_DIR = REPO_ROOT / "data"
BASELINE_DEBT_PATH = DATA_DIR / "qa-baseline-debt.json"


@dataclass
class QAScopeResult:
    changed_files: list[str]
    changed_posts: list[str]
    unchanged_posts: list[str]
    scope_mode: str  # "changed-only" or "full"
    total_posts: int
    baseline_debt_path: str = str(BASELINE_DEBT_PATH)


def run_git(args: list[str]) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print(f"Git error: {result.stderr}", file=sys.stderr)
            return ""
        return result.stdout.strip()
    except Exception as e:
        print(f"Git command failed: {e}", file=sys.stderr)
        return ""


def get_changed_files(base: str = "origin/main", head: str = "HEAD") -> list[str]:
    """Get list of changed files between base and head."""
    output = run_git(["diff", "--name-only", f"{base}...{head}"])
    if not output:
        return []
    return output.split("\n")


def get_changed_posts(changed_files: list[str]) -> list[str]:
    """Extract post filenames from changed files."""
    posts = []
    for f in changed_files:
        if f.startswith("content/posts/") and f.endswith(".md"):
            post_name = Path(f).stem
            posts.append(post_name)
    return posts


def get_all_posts() -> list[str]:
    """Get all post filenames."""
    if not CONTENT_DIR.exists():
        return []
    return [p.stem for p in CONTENT_DIR.glob("*.md") if p.is_file()]


def load_baseline_debt() -> dict[str, Any]:
    """Load baseline debt (known issues in old content)."""
    if not BASELINE_DEBT_PATH.exists():
        return {
            "known_issues": {},
            "created_at": "",
            "rationale": "Baseline for old content - doesn't block new deploys",
        }
    try:
        with open(BASELINE_DEBT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_baseline_debt(debt: dict[str, Any]) -> None:
    """Save baseline debt."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_DEBT_PATH, "w") as f:
        json.dump(debt, f, indent=2)


def detect_pr_context() -> tuple[str, str] | None:
    """Detect if running in GitHub PR context."""
    base = "origin/main"
    head = "HEAD"

    # Try GITHUB_BASE_REF/GITHUB_HEAD_REF (GitHub Actions)
    import os

    if os.getenv("GITHUB_BASE_REF") and os.getenv("GITHUB_HEAD_REF"):
        return (
            f"origin/{os.getenv('GITHUB_BASE_REF')}",
            f"origin/{os.getenv('GITHUB_HEAD_REF')}",
        )

    # Try git merge-base (local PR detection)
    output = run_git(["merge-base", base, head])
    if output:
        return (base, head)

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QA scope: determine what to check based on changed files"
    )
    parser.add_argument(
        "--base", default="origin/main", help="Base branch/commit"
    )
    parser.add_argument("--head", default="HEAD", help="Head branch/commit")
    parser.add_argument(
        "--github-pr",
        action="store_true",
        help="Auto-detect GitHub PR context",
    )
    parser.add_argument(
        "--out", default="reports/qa-scope.json", help="Output report path"
    )
    parser.add_argument(
        "--create-baseline",
        action="store_true",
        help="Create baseline debt from current state",
    )

    args = parser.parse_args()

    # Detect PR context if requested
    if args.github_pr:
        pr_context = detect_pr_context()
        if pr_context:
            args.base, args.head = pr_context

    # Get changed files and posts
    changed_files = get_changed_files(args.base, args.head)
    changed_posts = get_changed_posts(changed_files)
    all_posts = get_all_posts()
    unchanged_posts = [p for p in all_posts if p not in changed_posts]

    # Determine scope
    scope_mode = "changed-only" if changed_posts else "full"

    result = QAScopeResult(
        changed_files=changed_files,
        changed_posts=changed_posts,
        unchanged_posts=unchanged_posts,
        scope_mode=scope_mode,
        total_posts=len(all_posts),
    )

    # Output report
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "changed_files": result.changed_files,
        "changed_posts": result.changed_posts,
        "unchanged_posts": result.unchanged_posts,
        "scope_mode": result.scope_mode,
        "total_posts": result.total_posts,
        "message": (
            f"Check {len(changed_posts)} changed posts + {len(all_posts)} total"
            if changed_posts
            else "No post changes detected"
        ),
    }

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"QA Scope: {result.scope_mode}")
    print(f"  Changed posts: {len(changed_posts)}")
    print(f"  Unchanged posts: {len(unchanged_posts)}")
    print(f"  Report: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
