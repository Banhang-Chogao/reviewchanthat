#!/usr/bin/env python3
"""QA for Deployment Doctor system.

Usage:
  python scripts/qa_deployment_doctor.py
  python scripts/qa_deployment_doctor.py --public
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQUIRED_PATTERNS = {
    "runner_capacity_delay",
    "external_platform_incident",
    "github_rate_limit",
    "github_pages_rate_limit",
    "workflow_fanout",
    "baseline_debt_blocking_unrelated_deploy",
    "changed_post_image_missing",
    "self_owned_image_direct_url",
    "verified_creator_unavailable",
    "fake_image_creator",
    "date_only_or_wrong_timezone",
    "content_direction_empty_report",
    "live_deploy_not_reflected",
    "github_pages_serving_old_artifact",
    "baseurl_routing_error",
    "sitemap_noindex_mismatch",
    "series_hardcoded_url",
    "ai_summary_map_artifact",
    "qa_expectation_mismatch",
    "table_layout_ux_regression",
    "hugo_build_error",
    "unknown",
}
SECRET_NEEDLES = (
    "BEGIN PRIVATE KEY",
    "GITHUB_TOKEN=",
    "GH_TOKEN=",
    "PEXELS_API_KEY=",
    "PIXABAY_API_KEY=",
    "UNSPLASH_ACCESS_KEY=",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def check_json(path: Path) -> tuple[dict | list | None, list[str]]:
    errors = []
    if not path.exists():
        return None, [f"missing {path.relative_to(REPO)}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"JSON parse error {path.name}: {exc}"]
    return data, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []

    knowledge, e = check_json(REPO / "data" / "deployment-doctor-knowledge.json")
    errors.extend(e)
    if isinstance(knowledge, dict):
        ids = {p.get("id") for p in knowledge.get("patterns") or []}
        missing = REQUIRED_PATTERNS - ids
        if missing:
            errors.append(f"knowledge missing patterns: {sorted(missing)}")
        else:
            ok(f"knowledge patterns={len(ids)}")

    attempts, e = check_json(REPO / "data" / "deployment-doctor-attempts.json")
    errors.extend(e)
    if isinstance(attempts, dict):
        for k, v in (attempts.get("attempts") or {}).items():
            if int(v.get("count") or 0) > 2:
                errors.append(f"attempt count > 2 for {k}")
        ok("attempts ledger OK")

    dashboard, e = check_json(REPO / "data" / "deployment-doctor.json")
    errors.extend(e)
    if isinstance(dashboard, dict):
        if "summary" not in dashboard:
            errors.append("dashboard missing summary")
        else:
            ok("dashboard data OK")

    # Optional diagnosis may not exist pre-collect
    diag_path = REPO / "reports" / "deployment-doctor-diagnosis.json"
    if diag_path.exists():
        _, e = check_json(diag_path)
        errors.extend(e)

    # Workflow concurrency + no infinite loops
    wf = REPO / ".github" / "workflows" / "deployment-doctor.yml"
    if not wf.exists():
        errors.append("missing .github/workflows/deployment-doctor.yml")
    else:
        text = wf.read_text(encoding="utf-8")
        if "concurrency:" not in text:
            errors.append("workflow missing concurrency")
        else:
            ok("workflow concurrency present")
        if "while true" in text.lower():
            errors.append("workflow contains while true")
        if re.search(r"sleep\s+3600|sleep\s+999", text):
            errors.append("workflow has huge sleep")

    # Scripts shouldn't spin forever
    for script in (REPO / "scripts").glob("deployment_doctor_*.py"):
        t = script.read_text(encoding="utf-8", errors="replace")
        if "while True" in t or "while true" in t:
            errors.append(f"{script.name} contains while True")

    # Secret scan on data/reports (not huge)
    for base in (REPO / "data", REPO / "reports"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.stat().st_size > 200_000 and "deployment-doctor" in str(path):
                errors.append(f"log/report too large (>200KB): {path.relative_to(REPO)}")
            if path.suffix.lower() not in {".json", ".md", ".txt", ".log"}:
                continue
            try:
                sample = path.read_text(encoding="utf-8", errors="replace")[:50000]
            except OSError:
                continue
            for needle in SECRET_NEEDLES:
                if needle in sample and "[REDACTED]" not in sample:
                    # allow knowledge match strings that mention key names without values
                    if path.name.endswith(".json") and "match" in sample and "=" not in sample.split(needle)[0][-20:]:
                        continue
                    if needle.endswith("=") or "BEGIN PRIVATE KEY" in needle:
                        errors.append(f"possible secret in {path.relative_to(REPO)}: {needle}")

    if args.public:
        page = REPO / "public" / "deployment-doctor" / "index.html"
        if not page.exists():
            errors.append("public/deployment-doctor/index.html missing — run hugo")
        else:
            html = page.read_text(encoding="utf-8", errors="replace")
            if "Deployment Doctor" not in html:
                errors.append("page missing Deployment Doctor title")
            else:
                ok("page title present")
            if "noindex" not in html:
                errors.append("page missing noindex")
            else:
                ok("noindex present")
        sm = REPO / "public" / "sitemap.xml"
        if sm.exists() and "deployment-doctor" in sm.read_text(encoding="utf-8", errors="replace"):
            errors.append("sitemap must not include deployment-doctor")
        elif sm.exists():
            ok("sitemap excludes deployment-doctor")

    if errors:
        for e in errors:
            fail(e)
        print(f"qa_deployment_doctor: {len(errors)} failure(s)", file=sys.stderr)
        return 1
    print("qa_deployment_doctor: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
