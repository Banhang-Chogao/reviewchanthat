#!/usr/bin/env python3
"""autobot_fixer_I — nightly 00:00 GMT+7 safe optimization runner.

Orchestrates Content Direction scan + optimizer into one pipeline:
  1. Generate content-direction.json + report
  2. Compute score
  3. Apply safe autofixes (seo_title, description, internal link graph)
  4. Generate optimizer report
  5. QA checks

Usage:
  python scripts/autobot_fixer_I.py --dry-run
  python scripts/autobot_fixer_I.py --write
  python scripts/autobot_fixer_I.py --write --max-changes 30
  python scripts/autobot_fixer_I.py --write --skip-content-direction
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"


def _run_py(script: str, *args: str) -> subprocess.CompletedProcess:
    script_path = SCRIPTS_DIR / script
    if not script_path.exists():
        print(f"  Script not found: {script_path}", file=sys.stderr)
        return subprocess.CompletedProcess(args=[], returncode=1, stderr=f"Script not found: {script_path}".encode())
    cmd = [sys.executable, str(script_path)] + list(args)
    print(f"  >> {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=False, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="autobot_fixer_I - nightly safe optimizer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-changes", type=int, default=30)
    parser.add_argument("--skip-content-direction", action="store_true",
                        help="Skip re-scanning content direction (use existing data)")
    args = parser.parse_args()

    mode = "write" if args.write else "dry-run"
    print(f"=== autobot_fixer_I: {mode} ===")
    print()

    # Step 1: Content Direction scan
    if args.skip_content_direction:
        print("[1/5] SKIP content_direction.py (--skip-content-direction)")
    else:
        print("[1/5] Content Direction scan...")
        r = _run_py("content_direction.py",
                     "--json", str(DATA_DIR / "content-direction.json"),
                     "--md", str(REPORTS_DIR / "content-direction-report.md"))
        if r.returncode != 0:
            print(f"  FAILED (rc={r.returncode})", file=sys.stderr)
            return r.returncode
        print("  OK")

    # Step 2: QA Content Direction
    print("[2/5] QA Content Direction...")
    r = _run_py("qa_content_direction.py")
    if r.returncode != 0:
        print(f"  FAILED (rc={r.returncode})", file=sys.stderr)
        return r.returncode
    print("  OK")

    # Step 3: Optimizer
    print(f"[3/5] Content Direction Optimizer (max_changes={args.max_changes})...")
    r = _run_py("content_direction_optimizer.py",
                "--write" if args.write else "--dry-run",
                "--max-changes", str(args.max_changes),
                "--report-json", str(REPORTS_DIR / "content-direction-optimizer.json"),
                "--report-md", str(REPORTS_DIR / "content-direction-optimizer.md"))
    if r.returncode != 0:
        print(f"  FAILED (rc={r.returncode})", file=sys.stderr)
        return r.returncode
    print("  OK")

    # Step 4: QA autobot_fixer_I
    print("[4/5] QA autobot_fixer_I...")
    r = _run_py("qa_autobot_fixer_I.py")
    if r.returncode != 0:
        print(f"  FAILED (rc={r.returncode})", file=sys.stderr)
        return r.returncode
    print("  OK")

    # Step 5: Detect changed files
    print("[5/5] Detect changed files...")
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    changed = [line.strip() for line in r.stdout.strip().split("\n") if line.strip()] if r.stdout.strip() else []
    print(f"  Changed files: {len(changed)}")
    for f in changed:
        print(f"    {f}")

    print()
    print(f"=== autobot_fixer_I: {mode} completed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())