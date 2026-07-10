#!/usr/bin/env python3
"""
Re-run the image pipeline for external posts:
audit -> Pexels/Pixabay selection -> process -> self-owned verify -> attribution QA
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import frontmatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, "content", "posts")
SELF_SOURCE_VALUES = {"self", "self-owned"}


def python_bin() -> str:
    venv_py = os.path.join(ROOT, ".venv", "bin", "python")
    return venv_py if os.path.exists(venv_py) else sys.executable


def run_step(cmd: list[str]) -> None:
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_api_keys() -> None:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from image_providers import load_dotenv

    load_dotenv()
    has_key = any(os.environ.get(k) for k in ("PEXELS_API_KEY", "PIXABAY_API_KEY"))
    if not has_key:
        print("ERROR: No image API keys found.")
        print("Create .env from .env.example with at least PEXELS_API_KEY or PIXABAY_API_KEY.")
        raise SystemExit(2)


def mark_self_owned_verified() -> int:
    count = 0
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        post = frontmatter.load(fpath)
        meta = post.metadata
        owner = str(meta.get("image_owner", "")).strip().lower()
        source = str(meta.get("image_source", "")).strip().lower()
        if owner != "self" and source not in SELF_SOURCE_VALUES:
            continue
        if not meta.get("image"):
            continue
        meta["image_status"] = "verified"
        meta.pop("image_reject_reason", None)
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))
        count += 1
        print(f"  self-owned verified: {meta.get('slug', fname)}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh all post images (Pexels/Pixabay API-first)")
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--skip-process", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Only audit + key check")
    parser.add_argument("--force", action="store_true", help="Force reprocess all images")
    args = parser.parse_args()

    py = python_bin()
    ensure_api_keys()

    if not args.skip_audit:
        print(">>> Running image audit...")
        run_step([py, "scripts/audit_post_images.py"])

    if args.dry_run:
        print("\nDry run: auditing only. Use without --dry-run to actually select and process images.")
        return 0

    print("\n>>> Selecting images (Pexels/Pixabay API-first)...")
    run_step([py, "scripts/select_images.py", "--all", "--fix", "--api-first", "--only-missing-or-bad"])

    if not args.skip_process:
        print("\n>>> Processing images (download/crop/watermark)...")
        cmd = [py, "scripts/process_images.py"]
        if args.force:
            cmd.append("--force")
        run_step(cmd)

    verified_self = mark_self_owned_verified()
    print(f"\nSelf-owned posts marked verified: {verified_self}")

    print("\n>>> Resolving missing creator attribution...")
    run_step([py, "scripts/image_author_resolver.py", "--all", "--write"])

    print("\n>>> Checking image attribution...")
    run_step([py, "scripts/check_image_attribution.py"])

    print("\nRefresh all images: DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
