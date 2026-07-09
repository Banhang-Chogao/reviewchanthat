#!/usr/bin/env python3
"""Export dashboard payload for Hugo page data/deployment-doctor.json."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam  # noqa: E402
from doctor_common import REPO_ROOT, load_json, write_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "deployment-doctor.json"))
    parser.add_argument(
        "--runs", default=str(REPO_ROOT / "reports" / "deployment-doctor-runs.json")
    )
    parser.add_argument(
        "--diagnosis",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-diagnosis.json"),
    )
    parser.add_argument(
        "--autofix",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-autofix.json"),
    )
    parser.add_argument(
        "--knowledge",
        default=str(REPO_ROOT / "data" / "deployment-doctor-knowledge.json"),
    )
    parser.add_argument(
        "--attempts",
        default=str(REPO_ROOT / "data" / "deployment-doctor-attempts.json"),
    )
    args = parser.parse_args()

    now = now_vietnam()
    runs = load_json(Path(args.runs), {})
    diagnosis = load_json(Path(args.diagnosis), {})
    autofix = load_json(Path(args.autofix), {})
    knowledge = load_json(Path(args.knowledge), {})
    attempts = load_json(Path(args.attempts), {})

    diags = diagnosis.get("diagnoses") or []
    by_type = Counter(d.get("failure_type") for d in diags)
    safe = [d for d in diags if d.get("safe_to_autofix")]
    unsafe = [d for d in diags if not d.get("safe_to_autofix")]

    clusters = {
        "runner_platform": [],
        "qa_debt": [],
        "image_pipeline": [],
        "content_direction": [],
        "deploy_live": [],
        "ux_layout": [],
        "other": [],
    }
    cluster_map = {
        "external": "runner_platform",
        "ci": "runner_platform",
        "qa_debt": "qa_debt",
        "image_pipeline": "image_pipeline",
        "content_direction": "content_direction",
        "deploy_live": "deploy_live",
        "ux_layout": "ux_layout",
        "seo": "other",
        "content": "other",
        "build": "other",
        "unknown": "other",
    }
    for d in diags:
        bucket = cluster_map.get(d.get("severity") or "unknown", "other")
        clusters[bucket].append(
            {
                "failure_type": d.get("failure_type"),
                "run_id": d.get("run_id"),
                "rootcause": d.get("rootcause"),
                "safe_to_autofix": d.get("safe_to_autofix"),
            }
        )

    action_items = []
    for d in diags:
        prio = "P0" if d.get("safe_to_autofix") and d.get("confidence") == "high" else (
            "P1" if d.get("safe_to_autofix") else "P2"
        )
        owner = "system" if d.get("safe_to_autofix") else "owner"
        for a in d.get("action_items") or []:
            action_items.append(
                {
                    "priority": prio,
                    "owner": owner,
                    "failure_type": d.get("failure_type"),
                    "title": a,
                    "expected_result": "Unblock deploy / prevent recurrence",
                }
            )
    # Dedup by title
    seen = set()
    deduped = []
    for a in action_items:
        k = (a["priority"], a["title"])
        if k in seen:
            continue
        seen.add(k)
        deduped.append(a)

    lessons = []
    for p in knowledge.get("patterns") or []:
        if p.get("id") == "unknown":
            continue
        lessons.append(
            {
                "id": p.get("id"),
                "summary": p.get("summary"),
                "safe_to_autofix": p.get("safe_to_autofix"),
                "severity": p.get("severity"),
            }
        )

    loop_guarded = [
        {"key": k, **v}
        for k, v in (attempts.get("attempts") or {}).items()
        if int(v.get("count") or 0) >= 2
    ]

    owner_todos = []
    for d in unsafe:
        if d.get("failure_type") in {
            "external_platform_incident",
            "runner_capacity_delay",
            "github_rate_limit",
            "fake_image_creator",
        }:
            owner_todos.append(
                {
                    "failure_type": d.get("failure_type"),
                    "detail": d.get("rootcause"),
                    "action": (d.get("action_items") or ["Wait / review secrets or policy"])[0],
                }
            )

    payload = {
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "live": {
            "site": "https://banhang-chogao.github.io/reviewchanthat/",
            "doctor_url": "https://banhang-chogao.github.io/reviewchanthat/deployment-doctor/",
            "note": "Live SHA verification uses static/build-info.json when present.",
        },
        "summary": {
            "failed_runs_scanned": int(
                (runs.get("interesting_count") if runs else None)
                or len(runs.get("runs") or [])
                or len(diags)
            ),
            "safe_autofixes_available": len(safe),
            "unsafe_external_failures": len(unsafe),
            "open_action_items": len(deduped),
            "loop_guarded_attempts": len(loop_guarded),
            "by_type": dict(by_type.most_common()),
        },
        "recent_failures": [
            {
                "run_id": d.get("run_id"),
                "workflow": d.get("workflow"),
                "commit": (d.get("commit") or "")[:7],
                "status": d.get("conclusion"),
                "rootcause": d.get("failure_type"),
                "safe_to_autofix": d.get("safe_to_autofix"),
                "action": (d.get("action_items") or [""])[0],
                "url": d.get("url"),
            }
            for d in diags[:30]
        ],
        "clusters": clusters,
        "action_items": deduped[:40],
        "lessons_learned": lessons,
        "autofix_history": autofix.get("results") or [],
        "loop_guarded": loop_guarded,
        "owner_should_do": owner_todos[:10],
        "api": {
            "github_api_unavailable": bool(runs.get("github_api_unavailable")),
            "source": runs.get("source"),
        },
    }
    write_json(Path(args.out), payload)
    print(f"Exported dashboard data → {args.out}")
    print(
        f"scanned={payload['summary']['failed_runs_scanned']} "
        f"safe={payload['summary']['safe_autofixes_available']} "
        f"unsafe={payload['summary']['unsafe_external_failures']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
