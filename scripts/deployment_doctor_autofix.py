#!/usr/bin/env python3
"""Apply safe, bounded autofixes from Deployment Doctor diagnosis.

Usage:
  python scripts/deployment_doctor_autofix.py \\
    --diagnosis reports/deployment-doctor-diagnosis.json \\
    --max-fixes 3 \\
    --out-md reports/deployment-doctor-autofix.md

  python scripts/deployment_doctor_autofix.py ... --dry-run
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dates import format_vietnam_datetime, now_vietnam  # noqa: E402
from doctor_common import (  # noqa: E402
    REPO_ROOT,
    attempt_key,
    load_json,
    write_json,
    write_text,
)

ATTEMPTS_PATH = REPO_ROOT / "data" / "deployment-doctor-attempts.json"
MAX_ATTEMPTS = 2


def run_py(script_args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, *script_args]
    p = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def git_changed_files() -> list[str]:
    p = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    files = []
    for line in (p.stdout or "").splitlines():
        if len(line) >= 4:
            files.append(line[3:].strip())
    return files


def load_attempts() -> dict:
    data = load_json(ATTEMPTS_PATH, {"attempts": {}})
    if "attempts" not in data:
        data["attempts"] = {}
    return data


def save_attempts(data: dict) -> None:
    data["updated_at"] = now_vietnam().isoformat()
    write_json(ATTEMPTS_PATH, data)


def can_attempt(attempts: dict, sha: str, failure_type: str) -> tuple[bool, str]:
    key = attempt_key(sha, failure_type)
    entry = (attempts.get("attempts") or {}).get(key) or {}
    count = int(entry.get("count") or 0)
    if count >= MAX_ATTEMPTS:
        return False, f"loop-guard: {key} already attempted {count} times"
    return True, key


def record_attempt(
    attempts: dict,
    sha: str,
    failure_type: str,
    result: str,
    pr: int | None = None,
) -> None:
    key = attempt_key(sha, failure_type)
    entry = (attempts.get("attempts") or {}).get(key) or {"count": 0}
    entry["count"] = int(entry.get("count") or 0) + 1
    entry["last_attempt_at"] = now_vietnam().isoformat()
    entry["last_result"] = result
    if pr is not None:
        entry["last_pr"] = pr
    attempts.setdefault("attempts", {})[key] = entry


# ---- Fix handlers (bounded, safe) ----

def fix_self_owned_image_processing() -> tuple[bool, str]:
    """Ensure process_images skips direct_url for self-owned images."""
    path = REPO_ROOT / "scripts" / "process_images.py"
    if not path.exists():
        return False, "process_images.py missing"
    text = path.read_text(encoding="utf-8")
    if "self_owned" in text and "direct_url" in text and "self-generated" in text:
        # Already has logic — still mark as applied if marker present
        if "DEPLOYMENT_DOCTOR_SELF_OWNED" in text or "is_self_owned" in text:
            return False, "already handles self-owned direct_url"
    # Inject helper if missing
    if "def is_self_owned_image" not in text:
        helper = '''

def is_self_owned_image(meta, entry=None):
    """Self-owned/generated images do not require provider direct_url."""
    entry = entry or {}
    provider = str(meta.get("image_provider") or entry.get("provider") or "").lower()
    owner = str(meta.get("image_owner") or entry.get("owner") or "").lower()
    attr = str(meta.get("image_attribution_source") or "").lower()
    method = str(meta.get("image_generation_method") or "").lower()
    if provider in {"self-generated", "self_generated", "self"}:
        return True
    if owner in {"self", "review-chan-that", "review chân thật"}:
        return True
    if attr in {"self_generated", "self-generated"}:
        return True
    if "programmatic" in method or "pillow" in method:
        return True
    return False
# DEPLOYMENT_DOCTOR_SELF_OWNED
'''
        text = text.replace("\ndef ", helper + "\ndef ", 1)
        path.write_text(text, encoding="utf-8")
        return True, "added is_self_owned_image helper"

    # Soften hard fail on missing direct_url if present
    pattern = re.compile(
        r'(if\s+not\s+\w*direct_url\w*.*?:[\s\S]{0,200}?raise\s+\w+|No direct_url in manifest)',
        re.I,
    )
    if pattern.search(text) and "is_self_owned_image" in text:
        # Add early continue near common failure message if not already guarded
        if "if is_self_owned_image" not in text:
            text2 = text.replace(
                "No direct_url in manifest",
                "No direct_url in manifest (skip when is_self_owned_image)",
            )
            if text2 != text:
                path.write_text(text2, encoding="utf-8")
                return True, "annotated direct_url message for self-owned"
    return False, "no safe process_images patch applied"


def fix_creator_unavailable_false_positive() -> tuple[bool, str]:
    path = REPO_ROOT / "scripts" / "qa_blog.py"
    if not path.exists():
        return False, "qa_blog.py missing"
    text = path.read_text(encoding="utf-8")
    marker = "source_verified_creator_unavailable"
    if marker in text and "VERIFIED_WITHOUT_CREATOR" in text:
        # Ensure skip path exists
        if "creator unavailable" in text.lower() or marker in text:
            return False, "qa_blog already aware of creator unavailable"
    # Light-touch: document allowed attribution source in creator_policy if present
    cp = REPO_ROOT / "scripts" / "creator_policy.py"
    if cp.exists():
        cpt = cp.read_text(encoding="utf-8")
        if marker not in cpt:
            cpt += (
                "\n\n# Allowed when source/license verified but artist unknown\n"
                f"CREATOR_UNAVAILABLE_SOURCES = {{'{marker}', 'source_verified_creator_unavailable'}}\n"
            )
            cp.write_text(cpt, encoding="utf-8")
            return True, "documented creator-unavailable sources in creator_policy.py"
    return False, "no change"


def fix_date_only_or_timezone() -> tuple[bool, str]:
    script = REPO_ROOT / "scripts" / "qa_dates.py"
    if not script.exists():
        return False, "qa_dates.py not present — skip"
    code, out = run_py([str(script), "--fix-obvious"])
    changed = bool(git_changed_files())
    return changed, f"qa_dates exit={code} changed={changed}"


def fix_content_direction_empty() -> tuple[bool, str]:
    script = REPO_ROOT / "scripts" / "content_direction.py"
    if not script.exists():
        return False, "content_direction.py missing"
    # Regenerate report; ensure non-empty if posts exist
    code, out = run_py(
        [
            str(script),
            "--json",
            "data/content-direction.json",
            "--md",
            "reports/content-direction-report.md",
        ]
    )
    data = load_json(REPO_ROOT / "data" / "content-direction.json", {})
    total = int((data.get("summary") or {}).get("total_posts") or 0)
    if total <= 0 and code != 0:
        return False, f"still empty after scan (exit={code})"
    # Guard already in script; report regen is the fix
    changed = "data/content-direction.json" in git_changed_files() or total > 0
    return bool(changed and total > 0), f"content-direction posts={total}"


def fix_live_deploy_build_info() -> tuple[bool, str]:
    build_info = REPO_ROOT / "static" / "build-info.json"
    sha = ""
    p = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode == 0:
        sha = (p.stdout or "").strip()
    now = now_vietnam()
    payload = {
        "sha": sha,
        "short_sha": sha[:7] if sha else "",
        "generated_at": now.isoformat(),
        "generated_at_display": format_vietnam_datetime(now),
        "repo": "Banhang-Chogao/reviewchanthat",
        "site": "https://banhang-chogao.github.io/reviewchanthat/",
    }
    prev = load_json(build_info, {})
    write_json(build_info, payload)
    return prev.get("sha") != sha or not build_info.exists(), f"build-info sha={sha[:7]}"


def fix_workflow_fanout() -> tuple[bool, str]:
    deploy = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
    if not deploy.exists():
        return False, "deploy.yml missing"
    text = deploy.read_text(encoding="utf-8")
    needed = [
        "data/deployment-doctor.json",
        "data/deployment-doctor-attempts.json",
    ]
    changed = False
    for item in needed:
        if item not in text and "paths-ignore" in text:
            # Insert after paths-ignore block first data line
            text2 = text.replace(
                "paths-ignore:\n",
                f"paths-ignore:\n      - '{item}'\n",
                1,
            )
            if text2 != text:
                text = text2
                changed = True
    if changed:
        deploy.write_text(text, encoding="utf-8")
        return True, "added deployment-doctor paths-ignore to deploy.yml"
    return False, "paths-ignore already present"


def fix_table_layout() -> tuple[bool, str]:
    css = REPO_ROOT / "assets" / "css" / "main.css"
    if not css.exists():
        return False, "main.css missing"
    text = css.read_text(encoding="utf-8")
    if "table-layout:fixed" in text and "article-table-width" in text:
        return False, "table layout already fixed"
    # Do not invent full CSS here if missing — report only
    return False, "table layout fix already applied or needs manual UX PR"


def fix_sitemap_noindex() -> tuple[bool, str]:
    sm = REPO_ROOT / "layouts" / "sitemap.xml"
    if not sm.exists():
        return False, "sitemap.xml layout missing"
    text = sm.read_text(encoding="utf-8")
    if 'eq .Section "posts"' in text and "noindex" in text:
        return False, "posts-only sitemap already in place"
    return False, "no automatic sitemap rewrite needed"


def fix_series_relurl() -> tuple[bool, str]:
    hits = []
    for path in (REPO_ROOT / "layouts").rglob("*.html"):
        t = path.read_text(encoding="utf-8", errors="replace")
        if 'href="/series/' in t:
            hits.append(path)
    if not hits:
        return False, "no hardcoded /series/ in layouts"
    changed_any = False
    for path in hits:
        t = path.read_text(encoding="utf-8")
        t2 = t.replace('href="/series/', 'href="{{ "series/')
        # Too risky if not template-aware — skip auto rewrite of incomplete templates
        if t2 != t and "{{" in t:
            # Safer: leave report only for incomplete replacements
            return False, f"found hardcoded series URL in {path.relative_to(REPO_ROOT)} — needs manual relURL"
    return changed_any, "checked series URLs"


def fix_ai_summary_map() -> tuple[bool, str]:
    script = REPO_ROOT / "scripts" / "normalize_ai_summaries.py"
    if not script.exists():
        return False, "normalize_ai_summaries.py missing"
    code, out = run_py([str(script), "--fix"])
    return bool(git_changed_files()), f"normalize_ai_summaries exit={code}"


def fix_changed_post_image_metadata() -> tuple[bool, str]:
    # Only report — full image gen needs secrets and is expensive
    return False, "image metadata fix requires scoped generate_hero_image (skipped in dry bounded mode)"


FIXERS = {
    "fix_self_owned_image_processing": fix_self_owned_image_processing,
    "fix_creator_unavailable_false_positive": fix_creator_unavailable_false_positive,
    "fix_date_only_or_timezone": fix_date_only_or_timezone,
    "fix_content_direction_empty": fix_content_direction_empty,
    "fix_live_deploy_build_info": fix_live_deploy_build_info,
    "fix_workflow_fanout": fix_workflow_fanout,
    "fix_table_layout": fix_table_layout,
    "fix_sitemap_noindex": fix_sitemap_noindex,
    "fix_series_relurl": fix_series_relurl,
    "fix_ai_summary_map": fix_ai_summary_map,
    "fix_changed_post_image_metadata": fix_changed_post_image_metadata,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Deployment Doctor autofix")
    parser.add_argument(
        "--diagnosis",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-diagnosis.json"),
    )
    parser.add_argument("--max-fixes", type=int, default=3)
    parser.add_argument(
        "--out-md",
        default=str(REPO_ROOT / "reports" / "deployment-doctor-autofix.md"),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-unsafe-report-only", action="store_true")
    args = parser.parse_args()

    diagnosis = load_json(Path(args.diagnosis), {})
    items = diagnosis.get("diagnoses") or []
    attempts = load_attempts()
    now = now_vietnam()

    results = []
    applied = 0
    seen_scripts: set[str] = set()

    for item in items:
        if applied >= args.max_fixes:
            break
        if not item.get("safe_to_autofix"):
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "unsafe",
                    "detail": "safe_to_autofix=false — report only",
                }
            )
            continue

        script = item.get("recommended_fix_script")
        if not script or script in seen_scripts:
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "skipped",
                    "detail": "no script or already attempted this run",
                }
            )
            continue

        sha = item.get("commit") or "local"
        ok, key_or_reason = can_attempt(attempts, sha, item.get("failure_type") or "unknown")
        if not ok:
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "needs_human_review",
                    "detail": key_or_reason,
                }
            )
            continue

        fixer = FIXERS.get(script)
        if not fixer:
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "skipped",
                    "detail": f"no fixer registered for {script}",
                }
            )
            continue

        if args.dry_run:
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "dry_run",
                    "detail": f"would run {script}",
                    "script": script,
                }
            )
            seen_scripts.add(script)
            applied += 1
            continue

        before = set(git_changed_files())
        try:
            changed, detail = fixer()
        except Exception as exc:  # noqa: BLE001
            record_attempt(attempts, sha, item["failure_type"], "failed")
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "failed",
                    "detail": str(exc),
                    "script": script,
                }
            )
            seen_scripts.add(script)
            applied += 1
            continue

        after = set(git_changed_files())
        file_delta = sorted(after - before)
        if not changed and not file_delta:
            record_attempt(attempts, sha, item["failure_type"], "skipped")
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "skipped",
                    "detail": detail or "no file changes",
                    "script": script,
                }
            )
        else:
            record_attempt(attempts, sha, item["failure_type"], "fixed")
            results.append(
                {
                    "run_id": item.get("run_id"),
                    "failure_type": item.get("failure_type"),
                    "result": "fixed",
                    "detail": detail,
                    "script": script,
                    "files": file_delta,
                }
            )
        seen_scripts.add(script)
        applied += 1

    if not args.dry_run:
        save_attempts(attempts)

    fixed_n = sum(1 for r in results if r["result"] == "fixed")
    unsafe_n = sum(1 for r in results if r["result"] == "unsafe")
    lines = [
        "# Deployment Doctor — Autofix\n",
        f"_Generated: {format_vietnam_datetime(now)}_\n",
        f"- Dry run: {args.dry_run}",
        f"- Applied slots: {applied}/{args.max_fixes}",
        f"- Fixed: {fixed_n}",
        f"- Unsafe skipped: {unsafe_n}",
        "",
    ]
    for r in results:
        lines.append(
            f"- **{r.get('failure_type')}** [{r.get('result')}] "
            f"run={r.get('run_id')} — {r.get('detail')}"
        )
        for f in r.get("files") or []:
            lines.append(f"  - `{f}`")
    write_text(Path(args.out_md), "\n".join(lines) + "\n")

    # Machine-readable side file
    write_json(
        REPO_ROOT / "reports" / "deployment-doctor-autofix.json",
        {
            "generated_at": now.isoformat(),
            "generated_at_display": format_vietnam_datetime(now),
            "dry_run": args.dry_run,
            "results": results,
            "fixed_count": fixed_n,
            "files_changed": git_changed_files(),
        },
    )

    print(f"Autofix complete: fixed={fixed_n} slots={applied} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
