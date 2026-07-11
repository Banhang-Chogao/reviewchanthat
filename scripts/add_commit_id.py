"""
scripts/add_commit_id.py
Gắn commit hash cuối cùng vào front matter của mỗi bài blog (TOML format).
Dòng `commit = "<7-ky-tu>"` được thêm ngay sau title, trước date.
"""

import os
import re
import subprocess

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


def main():
    updated = 0
    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith('.md') or fname.endswith('.meta.json'):
            continue
        fpath = os.path.join(POSTS_DIR, fname)
        relpath = os.path.relpath(fpath, REPO_ROOT)
        commit_hash = get_last_commit(relpath)
        if not commit_hash:
            print(f"  SKIP {fname}: no git commit found")
            continue

        with open(fpath) as f:
            content = f.read()

        new_content = ensure_commit_field(content, commit_hash)
        if new_content != content:
            with open(fpath, 'w') as f:
                f.write(new_content)
            print(f"  UPDATED {fname} -> commit: {commit_hash}")
            updated += 1
        else:
            print(f"  OK    {fname} (already has commit: {commit_hash})")

    print(f"\nDone. Updated {updated} post(s).")


if __name__ == "__main__":
    main()
