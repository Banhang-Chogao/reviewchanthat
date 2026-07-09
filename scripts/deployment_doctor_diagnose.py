#!/usr/bin/env python3
"""Diagnose collected workflow runs against Deployment Doctor knowledge base.

Usage:
  python scripts/deployment_doctor_diagnose.py \\
    --runs reports/deployment-doctor-runs.json \\
    --knowledge data/deployment-doctor-knowledge.json \\
    --out-json reports/deployment-doctor-diagnosis.json \\
    --out-md reports/deployment-doctor-diagnosis.md
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam  # noqa: E402
from doctor_common import REPO_ROOT, load_json, write_json, write_text  # noqa: E402

CHECKOUT_MARKERS = (
    "actions/checkout",
    "Syncing repository",
    "Initialized empty Git repository",
    "Checking out the ref",
)


def read_log(run: dict) -> str:
    path = run.get("log_path") or ""
    if path:
        p = REPO_ROOT / path
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
    return ""


def match_pattern(log: str, haystack: str, pattern: dict) -> int:
    """Return match score (higher is better)."""
    score = 0
    for needle in pattern.get("match") or []:
        if not needle:
            continue
        if needle.lower() in log.lower() or needle.lower() in haystack.lower():
            score += 2 if len(needle) > 12 else 1
    return score


def classify(run: dict, patterns: list[dict]) -> dict:
    log = read_log(run)
    hay = " ".join(
        [
            run.get("workflow") or "",
            run.get("name") or "",
            run.get("display_title") or "",
            run.get("conclusion") or "",
            run.get("status") or "",
        ]
    )
    conclusion = (run.get("conclusion") or "").lower()
    status = (run.get("status") or "").lower()

    # Job never reached checkout → runner capacity
    if log and not any(m.lower() in log.lower() for m in CHECKOUT_MARKERS):
        if any(
            s in log
            for s in (
                "Waiting for a runner",
                "hosted runner to come online",
                "Queued",
            )
        ) or status in {"queued", "waiting", "pending"}:
            pat = next((p for p in patterns if p["id"] == "runner_capacity_delay"), None)
            if pat:
                return _result(run, pat, "high", "Job never reached checkout; runner queue/capacity.")

    best = None
    best_score = 0
    for pat in patterns:
        if pat.get("id") == "unknown":
            continue
        # Prefer log body over workflow name/title to reduce false positives
        score = match_pattern(log, hay if not log else "", pat)
        if not log:
            score = match_pattern("", hay, pat)
        if score > best_score:
            best_score = score
            best = pat

    # Require stronger evidence when matching only titles (no logs)
    min_score = 1 if log else 2
    if best and best_score >= min_score:
        confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"
        return _result(run, best, confidence, best.get("summary") or "")

    # Heuristics without strong pattern hit
    if conclusion in {"cancelled", "timed_out"}:
        pat = next((p for p in patterns if p["id"] == "workflow_fanout"), None)
        if pat:
            return _result(run, pat, "low", "Cancelled/timed out — possible fan-out/supersede.")

    if "Deploy" in (run.get("workflow") or "") and conclusion == "failure":
        pat = next((p for p in patterns if p["id"] == "deploy_not_completed"), None)
        if pat:
            return _result(run, pat, "low", "Deploy workflow failed without stronger match.")

    unknown = next((p for p in patterns if p["id"] == "unknown"), {
        "id": "unknown",
        "safe_to_autofix": False,
        "action_items": ["Needs human review"],
        "recommended_fix_script": None,
        "should_retry_deploy": False,
        "should_pause_workflows": False,
        "summary": "Unknown",
    })
    return _result(run, unknown, "low", "No knowledge pattern matched.")


def _result(run: dict, pat: dict, confidence: str, rootcause: str) -> dict:
    safe = bool(pat.get("safe_to_autofix"))
    return {
        "run_id": str(run.get("run_id") or ""),
        "workflow": run.get("workflow") or "",
        "commit": run.get("commit") or "",
        "branch": run.get("branch") or "",
        "conclusion": run.get("conclusion") or run.get("status") or "",
        "url": run.get("url") or "",
        "failure_type": pat.get("id") or "unknown",
        "confidence": confidence,
        "safe_to_autofix": safe,
        "scope": {
            "changed_files": [],
            "changed_posts": [],
            "global": not safe,
        },
        "rootcause": rootcause or pat.get("summary") or "",
        "action_items": list(pat.get("action_items") or []),
        "recommended_fix_script": pat.get("recommended_fix_script"),
        "should_open_pr": bool(safe and pat.get("recommended_fix_script")),
        "should_retry_deploy": bool(pat.get("should_retry_deploy")),
        "should_pause_workflows": bool(pat.get("should_pause_workflows")),
        "severity": pat.get("severity") or "unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Deployment Doctor runs")
    parser.add_argument(
        "--runs",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-runs.json"),
    )
    parser.add_argument(
        "--knowledge",
        default=str(REPO_ROOT / "data" / "deployment-doctor-knowledge.json"),
    )
    parser.add_argument(
        "--out-json",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-diagnosis.json"),
    )
    parser.add_argument(
        "--out-md",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-diagnosis.md"),
    )
    args = parser.parse_args()

    runs_payload = load_json(Path(args.runs), {})
    knowledge = load_json(Path(args.knowledge), {})
    patterns = knowledge.get("patterns") or []
    runs = runs_payload.get("runs") or []

    diagnoses = [classify(r, patterns) for r in runs]
    # Prefer unique failure types for autofix order: high confidence safe first
    diagnoses.sort(
        key=lambda d: (
            0 if d["safe_to_autofix"] else 1,
            0 if d["confidence"] == "high" else 1 if d["confidence"] == "medium" else 2,
            d["failure_type"],
        )
    )

    counts = Counter(d["failure_type"] for d in diagnoses)
    safe_n = sum(1 for d in diagnoses if d["safe_to_autofix"])
    unsafe_n = len(diagnoses) - safe_n
    now = now_vietnam()

    payload = {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "summary": {
            "total": len(diagnoses),
            "safe_to_autofix": safe_n,
            "unsafe": unsafe_n,
            "by_type": dict(counts.most_common()),
        },
        "diagnoses": diagnoses,
    }
    write_json(Path(args.out_json), payload)

    lines = [
        "# Deployment Doctor — Diagnosis\n",
        f"_Generated: {payload['generated_at_display']}_\n",
        f"- Total: {len(diagnoses)}",
        f"- Safe autofix: {safe_n}",
        f"- Unsafe/external: {unsafe_n}",
        "",
        "## Clusters\n",
    ]
    for k, v in counts.most_common():
        lines.append(f"- **{k}**: {v}")
    lines.append("\n## Items\n")
    for d in diagnoses[:50]:
        lines.append(
            f"- `{d['failure_type']}` ({d['confidence']}) "
            f"run={d['run_id']} safe={d['safe_to_autofix']} — {d['rootcause']}"
        )
        for a in d["action_items"][:3]:
            lines.append(f"  - {a}")
    write_text(Path(args.out_md), "\n".join(lines) + "\n")

    print(
        f"Diagnosed {len(diagnoses)} runs "
        f"(safe={safe_n}, unsafe={unsafe_n})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
