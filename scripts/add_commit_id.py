"""
scripts/add_commit_id.py
Gắn commit hash cuối cùng vào front matter của mỗi bài blog (TOML format).
Dòng `commit = "<7-ky-tu>"` được thêm ngay sau title, trước date.

Scope (mặc định khuyến nghị cho agent/commit/merge):
  python3 scripts/add_commit_id.py --post content/posts/<slug>.md
  python3 scripts/add_commit_id.py --post a.md --post b.md

Full-repo (chậm, chỉ khi debt-fix / CI full):
  python3 scripts/add_commit_id.py --all
"""

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"],
    text=True
).strip()

POSTS_DIR = os.path.join(REPO_ROOT, "content", "posts")


def get_last_commit(filepath):
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", filepath],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.stdout.strip()
    except Exception:
        return None


def ensure_commit_field(content, commit_hash):
    # Check if commit field already exists (both TOML and legacy formats)
    if re.search(r'^commit\s*[:=]\s*\S+', content, re.MULTILINE):
        content = re.sub(
            r'^commit\s*[:=]\s*\S+',
            f'commit = "{commit_hash}"',
            content,
            count=1,
            flags=re.MULTILINE
        )
        return content

    # Add after title line, before date line
    content = re.sub(
        r'^(title\s*=\s*"[^"]*")\n(date\s*=)',
        rf'\1\ncommit = "{commit_hash}"\n\2',
        content,
        count=1,
        flags=re.MULTILINE
    )
    return content


def resolve_posts(posts: list[str] | None, all_posts: bool) -> list[str]:
    """Return absolute paths of post .md files to process."""
    if posts:
        paths = []
        for p in posts:
            path = p if os.path.isabs(p) else os.path.join(REPO_ROOT, p)
            if not path.endswith(".md"):
                # allow bare slug
                path = os.path.join(POSTS_DIR, f"{os.path.basename(path)}.md")
            if not os.path.isfile(path):
                # try under content/posts/
                alt = os.path.join(POSTS_DIR, os.path.basename(path))
                if os.path.isfile(alt):
                    path = alt
                else:
                    print(f"  ERROR: post not found: {p}", file=sys.stderr)
                    raise SystemExit(2)
            paths.append(path)
        return paths

    if all_posts or not posts:
        # --all or legacy no-arg: whole tree (slow)
        return sorted(
            os.path.join(POSTS_DIR, f)
            for f in os.listdir(POSTS_DIR)
            if f.endswith(".md") and not f.endswith(".meta.json")
        )

    return []


def process_one(fpath: str) -> str:
    """Returns status: updated|ok|skip"""
    relpath = os.path.relpath(fpath, REPO_ROOT)
    fname = os.path.basename(fpath)
    commit_hash = get_last_commit(relpath)
    if not commit_hash:
        print(f"  SKIP {fname}: no git commit found")
        return "skip"

    with open(fpath) as f:
        content = f.read()

    new_content = ensure_commit_field(content, commit_hash)
    if new_content != content:
        with open(fpath, "w") as f:
            f.write(new_content)
        print(f"  UPDATED {fname} -> commit: {commit_hash}")
        return "updated"
    print(f"  OK    {fname} (already has commit: {commit_hash})")
    return "ok"


def main():
    parser = argparse.ArgumentParser(
        description="Gắn commit hash vào front matter (ưu tiên --post theo scope)"
    )
    parser.add_argument(
        "--post",
        action="append",
        dest="posts",
        metavar="PATH",
        help="Chỉ xử lý post này (lặp lại được). Khuyến nghị khi commit/merge.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Xử lý toàn bộ content/posts/ (chậm; chỉ debt-fix / CI full).",
    )
    args = parser.parse_args()

    if not args.posts and not args.all:
        # Legacy no-arg: keep full scan for CI, but warn agents
        print(
            "WARNING: no --post given → scanning ALL posts (slow). "
            "Prefer: python3 scripts/add_commit_id.py --post content/posts/<slug>.md",
            file=sys.stderr,
        )

    paths = resolve_posts(args.posts, args.all)
    updated = 0
    for fpath in paths:
        if process_one(fpath) == "updated":
            updated += 1

    print(f"\nDone. Updated {updated} post(s) (scoped={bool(args.posts)}, total_checked={len(paths)}).")


if __name__ == "__main__":
    main()
