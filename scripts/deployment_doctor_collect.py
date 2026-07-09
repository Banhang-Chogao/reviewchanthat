#!/usr/bin/env python3
"""Collect recent GitHub Actions runs for Deployment Doctor.

Usage:
  python scripts/deployment_doctor_collect.py --limit 80 \\
    --out-json reports/deployment-doctor-runs.json \\
    --out-md reports/deployment-doctor-runs.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam  # noqa: E402
from doctor_common import (  # noqa: E402
    DOCTOR_LOGS_DIR,
    REPO_ROOT,
    redact_secrets,
    truncate_log,
    write_json,
    write_text,
)

INTERESTING_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "startup_failure",
    "action_required",
}


def run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def gh_available() -> bool:
    if not shutil.which("gh"):
        return False
    code, out, _ = run_cmd(["gh", "auth", "status"], timeout=20)
    return code == 0 or "Logged in" in out


def list_runs(limit: int) -> tuple[list[dict], str | None]:
    if not gh_available():
        return [], "github_api_unavailable"
    code, out, err = run_cmd(
        [
            "gh",
            "run",
            "list",
            "--limit",
            str(limit),
            "--json",
            "databaseId,name,workflowName,displayTitle,headSha,headBranch,"
            "status,conclusion,createdAt,updatedAt,url,event",
        ],
        timeout=90,
    )
    if code != 0:
        return [], f"github_api_error: {redact_secrets(err or out)[:300]}"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return [], "github_api_json_error"
    return data if isinstance(data, list) else [], None


def is_interesting(run: dict) -> bool:
    conclusion = (run.get("conclusion") or "").lower()
    status = (run.get("status") or "").lower()
    if conclusion in INTERESTING_CONCLUSIONS:
        return True
    if status in {"queued", "waiting", "pending", "in_progress"}:
        # Long-running / stuck signal — include for diagnosis
        created = run.get("createdAt") or ""
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_min = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
            return age_min >= 25
        except Exception:  # noqa: BLE001
            return status in {"queued", "waiting"}
    return False


def fetch_log(run_id: int | str) -> str:
    code, out, err = run_cmd(["gh", "run", "view", str(run_id), "--log"], timeout=180)
    if code != 0:
        # Fallback: attempt failed logs only
        code2, out2, err2 = run_cmd(
            ["gh", "run", "view", str(run_id), "--log-failed"], timeout=120
        )
        if code2 != 0:
            return redact_secrets((err or err2 or out or out2 or "")[:4000])
        out = out2
    return truncate_log(redact_secrets(out))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect failed/stuck workflow runs")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument(
        "--out-json", default=str(REPO_ROOT / "reports" / "deployment-doctor-runs.json")
    )
    parser.add_argument(
        "--out-md", default=str(REPO_ROOT / "reports" / "deployment-doctor-runs.md")
    )
    parser.add_argument("--skip-logs", action="store_true")
    args = parser.parse_args()

    now = now_vietnam()
    runs, err = list_runs(args.limit)
    interesting = [r for r in runs if is_interesting(r)]

    DOCTOR_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for run in interesting:
        run_id = run.get("databaseId")
        log_excerpt = ""
        log_path = ""
        if run_id and not args.skip_logs and not err:
            # Only fetch logs for failed-like conclusions to save API
            conclusion = (run.get("conclusion") or "").lower()
            if conclusion in INTERESTING_CONCLUSIONS or (run.get("status") or "") in {
                "queued",
                "waiting",
                "in_progress",
            }:
                log_excerpt = fetch_log(run_id)
                log_path = str(
                    (DOCTOR_LOGS_DIR / f"{run_id}.log.txt").relative_to(REPO_ROOT)
                )
                write_text(REPO_ROOT / log_path, log_excerpt)

        items.append(
            {
                "run_id": str(run_id) if run_id is not None else "",
                "name": run.get("name") or "",
                "workflow": run.get("workflowName") or run.get("name") or "",
                "display_title": run.get("displayTitle") or "",
                "commit": run.get("headSha") or "",
                "branch": run.get("headBranch") or "",
                "status": run.get("status") or "",
                "conclusion": run.get("conclusion") or "",
                "created_at": run.get("createdAt") or "",
                "updated_at": run.get("updatedAt") or "",
                "url": run.get("url") or "",
                "event": run.get("event") or "",
                "log_path": log_path,
                "log_excerpt_chars": len(log_excerpt),
            }
        )

    payload = {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "source": "gh" if not err else err,
        "limit": args.limit,
        "total_listed": len(runs),
        "interesting_count": len(items),
        "github_api_unavailable": err == "github_api_unavailable",
        "error": err,
        "runs": items,
    }
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    write_json(out_json, payload)

    lines = [
        "# Deployment Doctor — Collected Runs\n",
        f"_Generated: {payload['generated_at_display']}_\n",
        f"- Listed: {len(runs)}",
        f"- Interesting/failed/stuck: {len(items)}",
        f"- Source: {payload['source']}",
        "",
        "| Run | Workflow | Branch | Conclusion | Commit |",
        "|-----|----------|--------|------------|--------|",
    ]
    for r in items[:80]:
        lines.append(
            f"| [{r['run_id']}]({r['url']}) | {r['workflow']} | {r['branch']} | "
            f"{r['conclusion'] or r['status']} | `{(r['commit'] or '')[:7]}` |"
        )
    if err:
        lines.append(f"\n> API note: {err}\n")
    write_text(out_md, "\n".join(lines) + "\n")

    print(
        f"Collected {len(items)} interesting runs "
        f"(listed={len(runs)}, source={payload['source']})"
    )
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
