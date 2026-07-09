#!/usr/bin/env python3
"""Simple deployment snapshot: failed runs → check if fixed → action items."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from dates import format_vietnam_datetime


WORKFLOWS = ["Deploy to GitHub Pages", "PR Check", "Post-Merge Autofix", "PR Autofix"]
ACTIONS_BY_WORKFLOW = {
    "Deploy to GitHub Pages": ["Check build logs", "Review deployment config"],
    "PR Check": ["Fix linting/tests", "Review PR changes"],
    "Post-Merge Autofix": ["Manual fix or revert", "Review autofix logs"],
    "PR Autofix": ["Review and merge fix PR", "Check autofix branch"],
}


@dataclass
class DeploymentItem:
    pr_number: int | None
    pr_title: str
    pr_url: str
    pr_status: str
    deploy_id: str
    deploy_run_url: str
    deploy_status: str
    workflow_name: str
    created_at: str
    updated_at: str
    is_fixed: bool
    action_items: list[str]
    created_at_display: str = field(default="")
    updated_at_display: str = field(default="")


def run_gh(args: list[str]) -> str | None:
    """Run gh command, return output or None."""
    try:
        result = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_recent_runs(workflow: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get recent workflow runs, both failed and successful."""
    output = run_gh([
        "run", "list",
        "--workflow", workflow,
        "--limit", str(limit),
        "--json", "databaseId,conclusion,createdAt,updatedAt,headBranch,headSha,url,event",
    ])
    return json.loads(output) if output else []


def get_pr_for_sha(sha: str) -> dict[str, Any] | None:
    """Find PR by commit SHA."""
    if not sha:
        return None
    output = run_gh([
        "pr", "list",
        "--state", "all",
        "--search", sha,
        "--json", "number,title,url,state",
        "--limit", "1",
    ])
    if output:
        data = json.loads(output)
        return data[0] if data else None
    return None


def is_fixed_after(failed_run: dict, successful_runs: list[dict]) -> bool:
    """Check if there's a successful run after the failed one."""
    failed_time = datetime.fromisoformat(failed_run["updatedAt"].replace("Z", "+00:00"))
    for run in successful_runs:
        if run["conclusion"] == "success":
            success_time = datetime.fromisoformat(run["updatedAt"].replace("Z", "+00:00"))
            if success_time > failed_time:
                return True
    return False


def collect_failed_runs(limit: int = 10) -> list[DeploymentItem]:
    """Collect recent failed runs only."""
    items = []

    for workflow in WORKFLOWS:
        runs = get_recent_runs(workflow, limit=limit * 2)
        if not runs:
            continue

        # Separate failed and successful
        failed = [r for r in runs if r.get("conclusion") == "failure"]
        successful = [r for r in runs if r.get("conclusion") == "success"]

        for run in failed[:limit]:
            run_id = run["databaseId"]
            sha = run.get("headSha", "")
            created_at = run.get("createdAt", "")
            updated_at = run.get("updatedAt", "")

            pr = get_pr_for_sha(sha)
            pr_number = pr["number"] if pr else None
            pr_title = pr["title"] if pr else ""
            pr_url = pr["url"] if pr else ""

            is_fixed = is_fixed_after(run, successful)

            item = DeploymentItem(
                pr_number=pr_number,
                pr_title=pr_title,
                pr_url=pr_url,
                pr_status=pr.get("state", "") if pr else "",
                deploy_id=run_id,
                deploy_run_url=run["url"],
                deploy_status="fixed" if is_fixed else "failed",
                workflow_name=workflow,
                created_at=created_at,
                updated_at=updated_at,
                is_fixed=is_fixed,
                action_items=ACTIONS_BY_WORKFLOW.get(workflow, ["Review logs"]),
                created_at_display=format_vietnam_datetime(created_at) if created_at else "",
                updated_at_display=format_vietnam_datetime(updated_at) if updated_at else "",
            )
            items.append(item)

    return sorted(items, key=lambda x: x["updated_at"], reverse=True)[:limit]


def write_snapshot(items: list[DeploymentItem], out_path: str) -> None:
    """Write snapshot to JSON."""
    from datetime import timedelta
    tz = timezone(timedelta(hours=7))
    now = datetime.now(tz).isoformat()

    data = {
        "generated_at": now,
        "generated_at_display": format_vietnam_datetime(now),
        "site": "Review Chân Thật",
        "base_url": "https://banhang-chogao.github.io/reviewchanthat/",
        "summary": {
            "total_items": len(items),
            "failed": sum(1 for i in items if not i["is_fixed"]),
            "fixed": sum(1 for i in items if i["is_fixed"]),
        },
        "items": [asdict(item) for item in items],
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Snapshot: {out_path} ({len(items)} items)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple deployment snapshot")
    parser.add_argument("--limit", type=int, default=10, help="Max items")
    parser.add_argument("--out", default="data/deployment-snapshot.json")

    args = parser.parse_args()

    if not run_gh(["auth", "status"]):
        print("Error: gh auth failed", file=sys.stderr)
        return 1

    items = collect_failed_runs(limit=args.limit)
    write_snapshot(items, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
