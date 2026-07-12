#!/usr/bin/env python3
"""QA: inline body images across all posts.

Two failure classes for inline markdown images (![](...images/posts/x.webp)):

  1. baseURL/subpath: the site is served under /reviewchanthat/. A root-absolute
     src like /images/posts/x.webp keeps that bare path and 404s on GitHub Pages.
     Root-cause fix is a render hook (layouts/_default/_markup/render-image.html)
     that trims the leading slash then relURL. This script ensures the hook exists
     (recreates it with --fix). It does NOT rewrite post bodies — the hook handles
     resolution for every post at build time, so bodies can keep /images/... paths.

  2. missing asset: an inline image references a webp that does not exist on disk.
     The hook cannot help here — the image is genuinely broken. Reported per post.

Usage:
  python3 scripts/qa_inline_images.py          # scan + report, exit 1 if broken
  python3 scripts/qa_inline_images.py --fix     # also recreate the hook if missing
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
STATIC_DIR = ROOT / "static"
HOOK_PATH = ROOT / "layouts" / "_default" / "_markup" / "render-image.html"

HOOK_CONTENT = """{{- /*
  Markdown image render hook.
  Fixes inline images that use root-absolute paths like /images/posts/x.webp:
  the site is served under a baseURL subpath (/reviewchanthat/), so a bare
  root-absolute src 404s on GitHub Pages. relURL only prepends the baseURL path
  for paths WITHOUT a leading slash, so we trim a leading "/" first, then relURL —
  giving /reviewchanthat/images/... in production and /images/... in local dev.
  Remote (http/https/protocol-relative) and data: URLs are left untouched.
*/ -}}
{{- $dest := .Destination -}}
{{- $isRemote := or (hasPrefix $dest "http://") (hasPrefix $dest "https://") (hasPrefix $dest "//") (hasPrefix $dest "data:") -}}
{{- $src := $dest -}}
{{- if not $isRemote -}}
  {{- $src = $dest | strings.TrimPrefix "/" | relURL -}}
{{- end -}}
<img src="{{ $src }}" alt="{{ .Text }}"{{ with .Title }} title="{{ . }}"{{ end }} loading="lazy" decoding="async">
"""

INLINE_RE = re.compile(r"!\[[^\]]*\]\((/?images/posts/[^)]+?\.webp)\)")


def check_hook(fix: bool) -> tuple[bool, str]:
    if HOOK_PATH.exists():
        return True, "render-image hook: present"
    if fix:
        HOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
        HOOK_PATH.write_text(HOOK_CONTENT, encoding="utf-8")
        return True, "render-image hook: MISSING -> recreated"
    return False, "render-image hook: MISSING (run with --fix to recreate)"


def scan_posts() -> tuple[int, int, list[tuple[str, str]]]:
    posts = sorted(POSTS_DIR.glob("*.md"))
    total_refs = 0
    posts_with_inline = set()
    broken: list[tuple[str, str]] = []
    for p in posts:
        text = p.read_text(encoding="utf-8")
        body = text.split("+++", 2)[-1]
        for m in INLINE_RE.finditer(body):
            ref = m.group(1)
            total_refs += 1
            posts_with_inline.add(p.name)
            disk = STATIC_DIR / ref.lstrip("/")
            if not disk.exists():
                broken.append((p.name, ref))
    return len(posts_with_inline), total_refs, broken


def main() -> int:
    ap = argparse.ArgumentParser(description="QA inline body images")
    ap.add_argument("--fix", action="store_true", help="Recreate the render-image hook if missing")
    args = ap.parse_args()

    hook_ok, hook_msg = check_hook(args.fix)
    print(f"  {hook_msg}")

    n_posts, n_refs, broken = scan_posts()
    print(f"  posts with inline images: {n_posts} | total inline refs: {n_refs} | broken (missing file): {len(broken)}")
    for name, ref in broken:
        print(f"  BROKEN {name} -> {ref}")

    if hook_ok and not broken:
        print("qa_inline_images: PASS — hook present, all inline images resolve to real files")
        return 0
    print("qa_inline_images: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
