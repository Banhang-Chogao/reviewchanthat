#!/usr/bin/env python3
"""Migrate internal links to ref-based resolution so they resolve via the
actual Hugo page .RelPermalink (no guessed/hardcoded slugs, no URL changes).

- internal_links entries: `url: /x/` -> `ref: posts/<file>.md`
- body markdown/html links to internal posts -> `{{< ref "posts/<file>.md" >}}`
Handles both de-accented (filename) and accented (title-based) URL forms.
Does NOT modify slugs/urls of existing posts (SEO-safe).
"""
import os
import re
import sys
import json
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "posts")
OLD_MAP = os.path.join(ROOT, "reports", "_old_permalinks.json")

DRY = "--dry" in sys.argv


def file_slug(fname):
    base = fname[:-3] if fname.endswith(".md") else fname
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", base)
    return m.group(1) if m else base


def main():
    files = [os.path.basename(f) for f in glob.glob(os.path.join(CONTENT, "*.md"))]
    fmap = {file_slug(f): f for f in files}

    # accented (title-based) slug -> file, from captured old permalinks
    amap = {}
    if os.path.exists(OLD_MAP):
        for f, oldpath in json.load(open(OLD_MAP, encoding="utf-8")).items():
            acc = oldpath.split("/posts/", 1)[-1].strip("/")
            amap[acc] = f

    allmap = dict(fmap)
    allmap.update(amap)

    changed = []
    for f in files:
        path = os.path.join(CONTENT, f)
        text = open(path, encoding="utf-8").read()
        new_text = text

        # 1) internal_links: url: /x/ -> ref: posts/x.md
        def mig_block(block):
            out = []
            for line in block.split("\n"):
                mm = re.match(r"^(\s*)url:\s*['\"]?(/[^'\"]+)['\"]?\s*$", line)
                if mm:
                    uu = mm.group(2).strip("/")
                    uu = re.sub(r"^posts/", "", uu)
                    if uu in allmap:
                        out.append('%sref: posts/%s' % (mm.group(1), allmap[uu]))
                        continue
                out.append(line)
            return "\n".join(out)

        ilb = re.search(r"internal_links:(.*?)(\n[a-z_]+\s*:|(\n---))", new_text, re.DOTALL)
        if ilb:
            start, end = ilb.start(1), ilb.end(1)
            new_text = new_text[:start] + mig_block(new_text[start:end]) + new_text[end:]

        # 2) body links -> ref shortcodes
        def md_rep(m):
            url = m.group(2).strip("/")
            if url in allmap:
                return '%s{{< ref "posts/%s" >}}%s' % (m.group(1), allmap[url], m.group(3))
            return m.group(0)
        new_text = re.sub(r"(\[[^\]]*\]\()(/[^\s)]+?/)(\))", md_rep, new_text)

        def html_rep(m):
            url = m.group(1).strip("/")
            if url in allmap:
                return "[%s]({{< ref \"posts/%s\" >}})" % (m.group(2), allmap[url])
            return m.group(0)
        new_text = re.sub(r"<a\s+href=[\"'](/[^\"']+?)[\"']>([^<]+)</a>", html_rep, new_text)

        if new_text != text:
            changed.append(f)
            if not DRY:
                open(path, "w", encoding="utf-8").write(new_text)

    print(("DRY-RUN " if DRY else "") + "Changed %d files:" % len(changed))
    for c in changed:
        print("  ", c)


if __name__ == "__main__":
    main()
