"""TOML frontmatter read/write helpers for posts that use +++ frontmatter.

python-frontmatter library doesn't support TOML, so we need text-level manipulation.
"""

import re
from typing import Any


def toml_val(v):
    """Format a Python value as a TOML literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def set_field(fm_text: str, key: str, value: Any) -> str:
    """Set key = value in TOML frontmatter text. Adds line if missing."""
    pattern = re.compile(rf'^{re.escape(key)}\s*=.*$', re.MULTILINE)
    if pattern.search(fm_text):
        return pattern.sub(f'{key} = {toml_val(value)}', fm_text)
    return fm_text.rstrip() + f'\n{key} = {toml_val(value)}'


def remove_key(fm_text: str, key: str) -> str:
    """Remove a key=value line from TOML frontmatter text."""
    return re.sub(rf'^{re.escape(key)}\s*=.*\n?', '', fm_text, flags=re.MULTILINE)


def read_fm(text: str) -> tuple[str, str, str] | None:
    """Extract frontmatter block from TOML (+++) post text.
    Returns (before, fm_text, after) where before = '+++\\n', after = '\\n+++...'.
    """
    m = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+)", text, re.S)
    if m:
        return m.group(1), m.group(2), text[m.end():]
    return None


def has_toml_fm(text: str) -> bool:
    return text.lstrip().startswith("+++")


def update_post_file(fpath: str, updates: dict[str, Any], removes: list[str] | None = None) -> bool:
    """Update TOML frontmatter fields in a post file. Handles both TOML and YAML.

    For TOML: uses text manipulation.
    For YAML: would need frontmatter library (not handled here).
    Returns True if updated, False on error.
    """
    try:
        text = open(fpath, encoding="utf-8").read()
    except Exception as e:
        print(f"    ERROR reading {fpath}: {e}")
        return False

    if not has_toml_fm(text):
        return False  # not TOML, caller should handle

    parts = read_fm(text)
    if not parts:
        print(f"    ERROR: Invalid TOML frontmatter in {fpath}")
        return False

    before, fm_text, after = parts

    if removes:
        for k in removes:
            fm_text = remove_key(fm_text, k)

    for k, v in updates.items():
        fm_text = set_field(fm_text, k, v)

    new_text = before + fm_text.strip() + "\n" + after
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_text)
        return True
    except Exception as e:
        print(f"    ERROR writing {fpath}: {e}")
        return False


def find_post_by_slug(slug: str, content_dir: str) -> str | None:
    """Find post file by slug. Handles TOML and YAML frontmatter."""
    import os
    import tomllib
    import yaml

    for fname in os.listdir(content_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(content_dir, fname)
        try:
            text = open(fpath, encoding="utf-8").read()
            if has_toml_fm(text):
                parts = read_fm(text)
                if parts:
                    meta = tomllib.loads(parts[1])
                    if meta.get("slug") == slug:
                        return fpath, "toml", text, parts
            else:
                import frontmatter
                post = frontmatter.load(fpath)
                if post.metadata.get("slug") == slug:
                    return fpath, "yaml", text, None
        except Exception:
            continue
    return None
