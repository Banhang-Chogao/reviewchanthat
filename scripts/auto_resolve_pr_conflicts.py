#!/usr/bin/env python3
"""Auto-resolve merge conflicts on an autobot PR branch by accepting main's version.

Usage:
  python scripts/auto_resolve_pr_conflicts.py <branch>

This is called by workflows when a PR has conflicts — it force-resolves
by checking out main's version for conflicted files.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        print(f"CMD FAILED: {' '.join(cmd)}", file=sys.stderr)
        print(r.stderr, file=sys.stderr)
    return r.stdout.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/auto_resolve_pr_conflicts.py <branch>", file=sys.stderr)
        return 1

    branch = sys.argv[1]

    # Verify branch exists
    branches = run(["git", "branch", "--list", branch])
    if not branches:
        print(f"Branch {branch} not found locally", file=sys.stderr)
        return 1

    run(["git", "fetch", "origin", "main"])
    merge_result = run(["git", "merge", "origin/main", "--no-edit"])

    if "CONFLICT" in merge_result:
        # Get conflicted files
        conflicted = run(["git", "diff", "--name-only", "--diff-filter=U"])
        if conflicted:
            files = conflicted.split("\n")
            print(f"Resolving {len(files)} conflicted files — keeping theirs (main)")
            run(["git", "checkout", "--theirs", "--"] + files)
            run(["git", "add", "--"] + files)

        run(["git", "commit", "--no-edit"])
        print("Conflicts resolved, committed")
    elif "Already up to date" in merge_result:
        print("Already up to date with main — no conflicts")
    else:
        print("Merge completed without conflicts")

    run(["git", "push", "-u", "origin", branch, "--force-with-lease"])
    print(f"Pushed {branch} — conflicts resolved")

    return 0


if __name__ == "__main__":
    sys.exit(main())