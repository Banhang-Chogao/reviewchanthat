#!/usr/bin/env python3
"""Remove [[internal_links]] from front matter if they're NOT mentioned in body.

The macro layouts/partials/post-footer.html renders these as
"Liên kết nội bộ được sử dụng trong bài viết" — they must actually
be referenced in the article body text or as markdown links.

Detection (strict — avoid false positives):
  - Markdown link `](...ref...)` in body
  - Exact slug substring in body (slug is long & unique)
  - Title text (anchor) in body (min 15 chars, after stripping Pillar: prefix)

Usage:
  python3 scripts/strip_unused_internal_links.py --write   # fix files
  python3 scripts/strip_unused_internal_links.py --dry-run # count only
"""
import tomllib, re, sys, argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "content" / "posts"


def check_link_in_body(link: dict, body: str) -> bool:
    """Return True if the internal link is referenced in the article body."""
    title = link.get("title", "")
    ref = link.get("ref", "")
    slug = ref.replace("posts/", "").replace(".md", "") if ref else ""

    # 1. Direct markdown link in body
    if ref and (f"](/{ref})" in body or f"] ({ref})" in body):
        return True

    # 2. Entire slug appears as text in body (very specific — no false positives)
    if slug and slug in body:
        return True

    # 3. Title (anchor text) appears in body
    if title:
        # Strip series prefixes like "Pillar:"
        tc = re.sub(r"^(Pillar|Series|Bài)\s*:\s*", "", title).strip()
        if len(tc) > 15 and tc in body:
            return True

    return False


def process_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Process a single post file. Returns (total_links, removed_links)."""
    content = path.read_text()
    m = re.search(r"^\+{3}\s*$(.*?)^\+{3}\s*$", content, re.MULTILINE | re.DOTALL)
    if not m:
        return 0, 0

    fm_raw = m.group(1)

    try:
        fm = tomllib.loads(fm_raw)
    except tomllib.TOMLDecodeError:
        return 0, 0

    links = fm.get("internal_links", [])
    if not links:
        return 0, 0

    body = content[m.end():]

    keep_list = [l for l in links if check_link_in_body(l, body)]
    remove_count = len(links) - len(keep_list)
    if remove_count == 0:
        return len(links), 0

    if dry_run:
        return len(links), remove_count

    # Split front matter into sections at lines starting with '['
    lines = fm_raw.split("\n")
    removed_refs = {l.get("ref", "") for l in links if l not in keep_list}
    removed_titles = {l.get("title", "") for l in links if l not in keep_list}

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("[["):
            section_lines = [line]
            j = i + 1
            while j < len(lines) and not lines[j].startswith("["):
                section_lines.append(lines[j])
                j += 1

            if line.startswith("[[internal_links]]"):
                sec_text = "\n".join(section_lines)
                ref_m = re.search(r'ref\s*=\s*"([^"]+)"', sec_text)
                title_m = re.search(r'title\s*=\s*"([^"]+)"', sec_text)
                ref_val = ref_m.group(1) if ref_m else ""
                title_val = title_m.group(1) if title_m else ""
                if ref_val in removed_refs or title_val in removed_titles:
                    i = j
                    continue

            new_lines.extend(section_lines)
            i = j

        elif line.startswith("["):
            section_lines = [line]
            j = i + 1
            while j < len(lines) and not lines[j].startswith("["):
                section_lines.append(lines[j])
                j += 1
            new_lines.extend(section_lines)
            i = j

        else:
            new_lines.append(line)
            i += 1

    new_fm = "\n".join(new_lines)
    new_fm = re.sub(r"\n{3,}", "\n\n", new_fm)

    new_content = content[:m.start()] + "+++\n" + new_fm.strip() + "\n+++" + content[m.end():]
    path.write_text(new_content)
    return len(links), remove_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip unused [[internal_links]] from front matter")
    parser.add_argument("--write", action="store_true", help="Actually fix files")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, no changes")
    args = parser.parse_args()

    total_links = 0
    total_removed = 0
    fixed_posts = 0

    for f in sorted(POSTS_DIR.glob("*.md")):
        t, r = process_file(f, dry_run=args.dry_run)
        if r > 0:
            fixed_posts += 1
            total_links += t
            total_removed += r
            if args.dry_run:
                print(f"  {f.stem}: {r} link(s) would be removed")

    if args.dry_run:
        print(f"\nWould fix {fixed_posts} post(s), remove {total_removed} link(s)")
    else:
        print(f"Fixed {fixed_posts} post(s), removed {total_removed} link(s)")

    return 0 if fixed_posts == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
