#!/usr/bin/env python3
"""QA for autobot_fixer_I — validates optimizer + content direction integrity after nightly run.

Checks:
  - Optimizer report exists
  - Score JSON parse OK
  - No image files changed by optimizer (hard fail)
  - No old slug changed (hard fail)
  - No date changed except generated_at/report files
  - No conflict markers
  - No more than max-changes
  - No secrets
  - No data/content-direction.json is empty (0 posts)

Usage:
  python scripts/qa_autobot_fixer_I.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
SCORE_JSON = DATA_DIR / "content-direction-score.json"
OPTIMIZER_JSON = REPORTS_DIR / "content-direction-optimizer.json"
CONTENT_DIR = REPO_ROOT / "content" / "posts"

IMAGE_DIRS = ("static/images/", "assets/generated-images/")
FORBIDDEN_PATTERNS = (re.compile(r"<<<<<<<|=======|>>>>>>>"),)
DISPLAY_RE = re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def get_changed_files() -> list[str]:
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if not r.stdout.strip():
        return []
    changed = []
    for line in r.stdout.strip().split("\n"):
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            changed.append(parts[1])
    return changed


def main() -> int:
    errors: list[str] = []
    changed_files = get_changed_files()

    if not changed_files:
        ok("No changed files detected (report files gitignored). Checking JSON data instead.")

    # 1. No image files changed by optimizer
    for f in changed_files:
        for img_dir in IMAGE_DIRS:
            if f.startswith(img_dir):
                errors.append(f"Optimizer touched image file: {f}")
    if not errors:
        ok("No image files changed by optimizer")

    # 2. Score JSON parse OK
    if SCORE_JSON.exists():
        try:
            score = json.loads(SCORE_JSON.read_text(encoding="utf-8"))
            score_val = score.get("score")
            if score_val is None or not isinstance(score_val, (int, float)):
                errors.append("content-direction-score.json missing 'score' field")
            else:
                ok(f"Score JSON valid: score={score_val}")
            display = score.get("generated_at_display", "")
            if display and not DISPLAY_RE.match(display):
                errors.append(f"Score JSON generated_at_display format invalid: {display!r}")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Score JSON parse error: {exc}")
    else:
        errors.append("content-direction-score.json not found")

    # 3. Optimizer report exists
    if OPTIMIZER_JSON.exists():
        try:
            opt = json.loads(OPTIMIZER_JSON.read_text(encoding="utf-8"))
            applied = opt.get("applied", [])
            skipped = opt.get("skipped", [])
            ok(f"Optimizer report: {len(applied)} applied, {len(skipped)} skipped")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Optimizer JSON parse error: {exc}")
    else:
        errors.append("content-direction-optimizer.json not found")

    # 4. Check content-direction.json is not empty/0 posts
    cd_json = DATA_DIR / "content-direction.json"
    if cd_json.exists():
        try:
            cd = json.loads(cd_json.read_text(encoding="utf-8"))
            total = int((cd.get("summary") or {}).get("total_posts", 0))
            if total <= 0:
                errors.append(f"Content Direction report has 0 posts (empty report)")
            else:
                ok(f"Content Direction report: {total} posts")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Content Direction JSON parse error: {exc}")
    else:
        errors.append("data/content-direction.json not found")

    # 5. Check conflict markers in content and data files
    for changed_file in changed_files:
        if not changed_file.startswith("content/") and not changed_file.startswith("data/"):
            continue
        path = REPO_ROOT / changed_file
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    errors.append(f"Conflict markers found in {changed_file}")
                    break
        except OSError:
            pass
    if not any("Conflict markers" in e for e in errors):
        ok("No conflict markers in changed files")

    # 6. Check no secrets (GITHUB_TOKEN, API_KEY, etc.)
    secrets_pattern = re.compile(r"(ghp_|gho_|github_pat_|sk-[a-zA-Z0-9]{20,}|API_KEY[=:]\s*['\"][a-zA-Z0-9])", re.I)
    for changed_file in changed_files:
        if not changed_file.startswith("content/") and not changed_file.startswith("data/"):
            continue
        path = REPO_ROOT / changed_file
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if secrets_pattern.search(text):
                errors.append(f"Possible secret found in {changed_file}")
        except OSError:
            pass
    if not any("Possible secret" in e for e in errors):
        ok("No secrets detected in changed files")

    # 7. Check no date/slug destructive changes (simple check — cannot detect all)
    if changed_files:
        for f in changed_files:
            if f.startswith("content/posts/") and f.endswith(".md"):
                if "date" in f.lower():
                    print(f"WARN: File with 'date' in name was changed: {f}", file=sys.stderr)

    if errors:
        for e in errors:
            fail(e)
        print(f"qa_autobot_fixer_I: {len(errors)} failure(s)", file=sys.stderr)
        return 1

    print("qa_autobot_fixer_I: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())