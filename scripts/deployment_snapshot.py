#!/usr/bin/env python3
"""Collect deployment snapshots from GitHub Actions workflow runs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from dates import format_vietnam_datetime

WORKFLOW_NAMES = [
    "Deploy to GitHub Pages",
    "PR Check",
    "Post-Merge Autofix",
    "PR Autofix",
]

ROOTCAUSE_PATTERNS = {
    "hugo_build": r"(hugo.*failed|build failed|error compiling)",
    "qa_dates": r"(date.*invalid|date.*format|qa.*date)",
    "qa_sitemap": r"(sitemap.*failed|qa.*sitemap)",
    "image_attribution": r"(image.*attribution|image.*credit|missing.*credit)",
    "image_relevance": r"(image.*relevance|image.*not.*relevant)",
    "compliance": r"(compliance.*failed|restricted.*content)",
    "github_pages": r"(github.*pages.*failed|pages.*deployment)",
    "merge_conflict": r"(conflict|merge.*failed|rebase.*failed)",
}


@dataclass
class DeploymentItem:
    pr_number: int | None
    pr_title: str
    pr_url: str
    pr_status: str
    merge_sha: str
    deploy_id: str
    deploy_run_url: str
    deploy_status: str
    deploy_conclusion: str
    workflow_name: str
    created_at: str
    updated_at: str
    rootcause: str
    action_items: list[str]
    remark: str
    created_at_display: str = field(default="")
    updated_at_display: str = field(default="")


def run_gh(args: list[str]) -> str | None:
    """Run gh command and return output, or None if failed."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# Cache PR lookups by commit SHA to avoid repeat gh calls.
_PR_BY_SHA: dict[str, dict[str, Any] | None] = {}


def get_pr_for_sha(sha: str) -> dict[str, Any] | None:
    """Best-effort: find the PR associated with a commit SHA.

    `gh run list` does not expose a pullRequests field, so correlate
    separately. Any failure returns None (PR column just shows "—").
    """
    if not sha:
        return None
    if sha in _PR_BY_SHA:
        return _PR_BY_SHA[sha]

    pr = None
    output = run_gh([
        "pr", "list",
        "--state", "all",
        "--search", sha,
        "--json", "number,title,url,state",
        "--limit", "1",
    ])
    if output:
        try:
            data = json.loads(output)
            if data:
                pr = data[0]
        except json.JSONDecodeError:
            pr = None

    _PR_BY_SHA[sha] = pr
    return pr


def parse_rootcause(logs: str) -> str:
    """Infer rootcause from logs."""
    if not logs:
        return ""
    logs_lower = logs.lower()
    for cause, pattern in ROOTCAUSE_PATTERNS.items():
        if re.search(pattern, logs_lower):
            return cause
    return "unknown"


def get_deployment_logs(run_id: str) -> str | None:
    """Get logs for a workflow run."""
    output = run_gh(["run", "view", run_id, "--log"])
    return output if output else None


def extract_pr_from_logs(logs: str) -> int | None:
    """Extract PR number from commit message or logs."""
    if not logs:
        return None
    match = re.search(r"#(\d+)", logs)
    return int(match.group(1)) if match else None


def collect_runs(limit: int = 20, from_run_id: str | None = None) -> list[DeploymentItem]:
    """Collect recent workflow runs."""
    items = []

    for workflow in WORKFLOW_NAMES:
        output = run_gh([
            "run",
            "list",
            "--workflow",
            workflow,
            "--limit",
            str(limit * 2),
            "--json",
            "databaseId,headBranch,headSha,name,conclusion,status,createdAt,updatedAt,url",
        ])

        if not output:
            continue

        try:
            runs = json.loads(output)
        except json.JSONDecodeError:
            continue

        for run in runs:
            run_id = str(run.get("databaseId", ""))
            if not run_id:
                continue

            if from_run_id and run_id != from_run_id:
                continue

            status = run.get("status", "unknown").lower()
            conclusion = run.get("conclusion", "unknown").lower()
            created_at = run.get("createdAt", "")
            updated_at = run.get("updatedAt", "")

            pr_number = None
            pr_title = ""
            pr_url = ""
            pr_status = "unknown"

            pr = get_pr_for_sha(run.get("headSha", ""))
            if pr:
                pr_number = pr.get("number")
                pr_title = pr.get("title", "")
                pr_url = pr.get("url", "")
                pr_status = str(pr.get("state", "unknown")).lower()

            deploy_status = "queued" if status == "queued" else status
            if conclusion == "success":
                deploy_status = "success"
            elif conclusion == "failure":
                deploy_status = "failed"
            elif conclusion == "cancelled":
                deploy_status = "cancelled"

            rootcause = ""
            action_items = []
            remark = "In progress"

            if deploy_status == "success":
                rootcause = ""
                remark = "Live OK"
            elif deploy_status == "failed":
                logs = get_deployment_logs(run_id)
                rootcause = parse_rootcause(logs or "")
                if rootcause == "merge_conflict":
                    action_items = ["Auto-resolve merge conflict"]
                    remark = "Blocked by conflict"
                elif rootcause in ("hugo_build", "compliance", "image_attribution"):
                    action_items = ["Review logs and fix", "Retry after fix"]
                    remark = "Manual review needed"
                else:
                    action_items = ["Investigate failure in Actions"]
                    remark = "Check logs"

            item = DeploymentItem(
                pr_number=pr_number,
                pr_title=pr_title,
                pr_url=pr_url,
                pr_status=pr_status,
                merge_sha=run.get("headSha", ""),
                deploy_id=run_id,
                deploy_run_url=run.get("url", ""),
                deploy_status=deploy_status,
                deploy_conclusion=conclusion,
                workflow_name=workflow,
                created_at=created_at,
                updated_at=updated_at,
                rootcause=rootcause,
                action_items=action_items,
                remark=remark,
                created_at_display=format_vietnam_datetime(created_at) if created_at else "",
                updated_at_display=format_vietnam_datetime(updated_at) if updated_at else "",
            )
            items.append(item)

    return items[:limit]


def compute_summary(items: list[DeploymentItem]) -> dict[str, Any]:
    """Compute summary stats."""
    summary = {
        "total_items": len(items),
        "success": sum(1 for i in items if i.deploy_status == "success"),
        "failed": sum(1 for i in items if i.deploy_status == "failed"),
        "in_progress": sum(1 for i in items if i.deploy_status == "in_progress"),
        "latest_status": items[0].deploy_status if items else "unknown",
        "latest_pr": items[0].pr_number if items else None,
        "latest_deploy_id": items[0].deploy_id if items else None,
    }
    return summary


def write_snapshot(items: list[DeploymentItem], out_path: str) -> None:
    """Write snapshot to JSON file."""
    from datetime import timedelta
    tz = timezone(timedelta(hours=7))
    now = datetime.now(tz).isoformat()

    data = {
        "generated_at": now,
        "generated_at_display": format_vietnam_datetime(now),
        "site": "Review Chân Thật",
        "base_url": "https://banhang-chogao.github.io/reviewchanthat/",
        "summary": compute_summary(items),
        "items": [asdict(item) for item in items],
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Snapshot written: {out_path} ({len(items)} items)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect deployment snapshots")
    parser.add_argument("--limit", type=int, default=10, help="Max items to collect")
    parser.add_argument("--out", default="data/deployment-snapshot.json", help="Output file")
    parser.add_argument("--from-run-id", help="Filter by specific run ID")

    args = parser.parse_args()

    gh_status = run_gh(["auth", "status"])
    if not gh_status:
        print("Warning: gh auth failed, using cached data if available", file=sys.stderr)
        if os.path.isfile(args.out):
            print(f"Using existing {args.out}")
            return 0
        print("Error: no authentication and no cached data", file=sys.stderr)
        return 1

    items = collect_runs(limit=args.limit, from_run_id=args.from_run_id)
    write_snapshot(items, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
