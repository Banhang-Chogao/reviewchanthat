#!/usr/bin/env python3
"""
Audit recent workflow failures and diagnose root causes.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Root cause categories
CATEGORIES = {
    "qa_debt": "QA debt blocking unrelated feature deploy",
    "image_metadata": "Image metadata/attribution issue",
    "self_owned_image_direct_url": "Self-owned image missing direct_url check",
    "deploy_failed": "Deploy to GitHub Pages failed",
    "runner_capacity_delay": "Runner capacity/startup delay",
    "pages_deploy_issue": "Pages publish/artifact mismatch",
    "hugo_build": "Hugo build error",
    "compliance_changed_post": "Compliance check on new/changed post",
    "baseline_debt_blocking_unrelated_deploy": "Old QA debt blocking new deploy",
    "workflow_loop_or_fanout": "Workflow concurrency/loop issue",
    "unknown": "Unknown root cause",
}

def parse_log_for_signals(log_text):
    """Extract failure signals from log content."""
    signals = []

    if "No direct_url in manifest" in log_text:
        signals.append("self_owned_image_direct_url")
    if "FAIL:" in log_text:
        signals.append("qa_check_failed")
    if "Process completed with exit code 1" in log_text:
        signals.append("step_failed")
    if "deployment-snapshot" in log_text:
        signals.append("deployment_snapshot_link")
    if "Could not download from" in log_text:
        signals.append("download_failed")
    if "Process images" in log_text:
        signals.append("image_processing")

    return signals


def diagnose_failures(runs_json, logs_dir):
    """Diagnose root causes from failed runs."""

    with open(runs_json) as f:
        failed_runs = json.load(f)

    audit_items = []

    for run in failed_runs[:10]:  # Limit to 10 most recent
        run_id = run.get("databaseId")
        workflow = run.get("workflowName", "Unknown")
        commit = run.get("headSha", "")[:7]
        display_title = run.get("displayTitle", "")
        url = run.get("url", "")

        # Try to read log
        log_file = Path(logs_dir) / f"run-{run_id}.log.txt"
        log_content = ""
        if log_file.exists():
            with open(log_file) as f:
                log_content = f.read()

        # Detect signals
        signals = parse_log_for_signals(log_content)

        # Classify root cause
        root_cause = "unknown"
        confidence = "low"
        action_items = []
        remark = ""

        if "self_owned_image_direct_url" in signals:
            root_cause = "self_owned_image_direct_url"
            confidence = "high"
            action_items = [
                "Update process_images.py to skip direct_url check for self-owned images",
                "Verify image file exists under static/images/posts/",
                "Ensure image_provider='self-generated' or image_owner='self' in frontmatter",
            ]
            remark = "Self-owned image lacks direct_url, but should not require it."

        elif "image_processing" in signals and "FAIL:" in log_content:
            root_cause = "image_metadata"
            confidence = "high"
            action_items = [
                "Review image metadata in post frontmatter",
                "Verify image file exists",
                "Check image attribution fields",
            ]

        elif "deployment_snapshot_link" in signals and "Deploy to GitHub Pages" in workflow:
            root_cause = "baseline_debt_blocking_unrelated_deploy"
            confidence = "medium"
            action_items = [
                "Align QA expectations with product decision on footer/links",
                "Scope QA to changed files only for this deploy",
                "Keep old QA debt in baseline, not blocking new deploys",
            ]
            remark = "Footer link removed but QA still expects it; policy mismatch."

        elif ".github/workflows/qa-debt-fix.yml" in workflow:
            root_cause = "qa_debt"
            confidence = "medium"
            action_items = [
                "Review QA check configuration",
                "Consider scoping QA to changed files only",
                "Separate baseline debt from deploy gate",
            ]

        elif "Deploy to GitHub Pages" in workflow and "qa-debt" not in signals:
            root_cause = "deploy_failed"
            confidence = "medium"
            action_items = [
                "Check build logs for errors",
                "Verify artifact was published",
                "Check Pages deployment history",
            ]

        item = {
            "run_number_or_id": str(run_id),
            "workflow": workflow,
            "commit": commit,
            "display_title": display_title,
            "status": "failure",
            "rootcause": root_cause,
            "confidence": confidence,
            "action_items": action_items,
            "remark": remark,
            "url": url,
        }

        audit_items.append(item)

    return audit_items


def main():
    parser = argparse.ArgumentParser(description="Audit recent workflow failures")
    parser.add_argument("--runs", required=True, help="Path to failed runs JSON")
    parser.add_argument("--logs-dir", required=True, help="Directory with workflow logs")
    parser.add_argument("--out-json", help="Output audit JSON file")
    parser.add_argument("--out-md", help="Output audit markdown file")

    args = parser.parse_args()

    items = diagnose_failures(args.runs, args.logs_dir)

    # Summarize
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generated_at_display": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
        "summary": {
            "failed_runs": len(items),
            "deploy_failures": len([i for i in items if "Deploy" in i["workflow"]]),
            "qa_debt_failures": len([i for i in items if "qa-debt" in i["workflow"]]),
            "likely_root_causes": list(set(i["rootcause"] for i in items)),
        },
        "items": items,
    }

    # Write JSON
    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Audit JSON: {args.out_json}")

    # Write Markdown
    if args.out_md:
        with open(args.out_md, "w") as f:
            f.write("# Workflow Failures Audit\n\n")
            f.write(f"Generated: {summary['generated_at_display']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Failed runs: {summary['summary']['failed_runs']}\n")
            f.write(f"- Deploy failures: {summary['summary']['deploy_failures']}\n")
            f.write(f"- QA debt failures: {summary['summary']['qa_debt_failures']}\n")
            f.write(f"- Root causes: {', '.join(summary['summary']['likely_root_causes'])}\n\n")

            f.write("## Failed Runs\n\n")
            for item in items:
                f.write(f"### {item['workflow']} - {item['commit']}\n\n")
                f.write(f"- **Run**: {item['run_number_or_id']}\n")
                f.write(f"- **Commit**: {item['commit']}\n")
                f.write(f"- **Title**: {item['display_title']}\n")
                f.write(f"- **Root Cause**: {item['rootcause']} ({item['confidence']} confidence)\n")
                if item['remark']:
                    f.write(f"- **Note**: {item['remark']}\n")
                if item['action_items']:
                    f.write("- **Actions**:\n")
                    for action in item['action_items']:
                        f.write(f"  - {action}\n")
                f.write(f"- **URL**: [{item['run_number_or_id']}]({item['url']})\n\n")

        print(f"✓ Audit Markdown: {args.out_md}")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
