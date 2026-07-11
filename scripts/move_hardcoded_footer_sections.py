#!/usr/bin/env python3
"""Move HARD-CODED footer sections out of post bodies into front matter.

Rule (AGENTS.md): the four end-of-post sections
  - "Liên kết nội bộ được sử dụng trong bài viết"  (internal links)
  - "Liên kết bên ngoài được sử dụng trong bài viết" (external links)
  - "FAQ - Câu hỏi thường gặp"                        (faq)
  - "Bản quyền & Ghi nguồn"                           (attribution)
must be rendered ONLY by the macro `layouts/partials/post-footer.html`, which
reads the TOML front-matter fields `[[internal_links]]`, `[[external_links]]`,
`[[faq]]`, `[attribution]`. Regardless of category, these sections must never be
hard-coded in the markdown body.

If an author (or a generator) hard-codes such a section in the body, this script
detects it and MOVES the content into the matching front-matter field, then
strips the hard-coded section from the body so the macro is the single source of
truth.

Usage:
  python3 scripts/move_hardcoded_footer_sections.py            # scan + report only
  python3 scripts/move_hardcoded_footer_sections.py --fix      # move content into FM
  python3 scripts/move_hardcoded_footer_sections.py --post content/posts/foo.md --fix

Exit code is non-zero when hard-coded sections remain (scan mode) so it can gate
deploy alongside the other pre-deploy checks.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"

FM_RE = re.compile(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+\r?\n?)(.*)$", re.S)
HEADING_RE = re.compile(r"^(#{2,6})\s*(.+?)\s*$")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Section detectors: substring match on the accent-stripped, lowercased heading.
SECTION_MATCHERS: list[tuple[str, tuple[str, ...]]] = [
    ("internal_links", ("lien ket noi bo",)),
    ("external_links", ("lien ket ben ngoai",)),
    ("faq", ("faq", "cau hoi thuong gap")),
    ("attribution", ("ban quyen", "ghi nguon")),
]


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def classify_heading(heading_text: str) -> str | None:
    norm = strip_accents(heading_text)
    for section, needles in SECTION_MATCHERS:
        if any(n in norm for n in needles):
            return section
    return None


def toml_str(value: str) -> str:
    """Render a single-line TOML basic string; collapse internal whitespace."""
    collapsed = re.sub(r"\s+", " ", value).strip()
    escaped = collapsed.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


# ---------------------------------------------------------------------------
# Body scanning: find hard-coded footer sections
# ---------------------------------------------------------------------------
def find_sections(body: str) -> list[dict]:
    """Return hard-coded footer sections as dicts with heading, level, line span."""
    lines = body.splitlines()
    sections: list[dict] = []
    i = 0
    while i < len(lines):
        m = HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue
        level = len(m.group(1))
        section = classify_heading(m.group(2))
        if not section:
            i += 1
            continue
        # Capture until the next heading of same-or-higher level (or EOF).
        j = i + 1
        while j < len(lines):
            hm = HEADING_RE.match(lines[j])
            if hm and len(hm.group(1)) <= level:
                break
            j += 1
        sections.append(
            {
                "section": section,
                "heading": m.group(2),
                "level": level,
                "start": i,
                "end": j,  # exclusive
                "content": "\n".join(lines[i + 1 : j]),
            }
        )
        i = j
    return sections


# ---------------------------------------------------------------------------
# Extractors: turn raw section text into structured FM entries
# ---------------------------------------------------------------------------
def extract_links(content: str, *, want_internal: bool) -> list[dict]:
    entries: list[dict] = []
    for title, url in MD_LINK_RE.findall(content):
        title = title.strip()
        url = url.strip()
        is_internal = url.startswith("/") or "/posts/" in url and "://" not in url
        if want_internal:
            if not is_internal:
                continue
            slug_match = re.search(r"/posts/([^/#?]+)", url)
            if not slug_match:
                continue
            slug = slug_match.group(1)
            if not slug.endswith(".md"):
                slug = slug + ".md"
            entries.append({"ref": f"posts/{slug}", "title": title})
        else:
            if "://" not in url:
                continue
            entries.append({"url": url, "title": title})
    return entries


def extract_faq(content: str) -> list[dict]:
    """Best-effort Q/A extraction. A question is a bold line, a sub-heading, or a
    line ending with '?'. Following non-question text becomes the answer."""
    lines = [ln.rstrip() for ln in content.splitlines()]
    pairs: list[dict] = []
    question: str | None = None
    answer: list[str] = []

    def flush():
        nonlocal question, answer
        if question and answer:
            pairs.append({"question": question, "answer": " ".join(answer).strip()})
        question, answer = None, []

    def as_question(line: str) -> str | None:
        s = line.strip()
        if not s:
            return None
        hm = HEADING_RE.match(line)
        if hm:
            return hm.group(2).strip()
        bold = re.fullmatch(r"\*\*(.+?)\*\*:?", s)
        if bold:
            return bold.group(1).strip()
        # "- **Q:** ...?" style
        qprefix = re.match(r"^[-*]?\s*\*\*(?:Q|Câu hỏi)[:.]?\*\*\s*(.+)$", s, re.I)
        if qprefix:
            return qprefix.group(1).strip()
        if s.endswith("?"):
            return re.sub(r"^[-*]\s*", "", s).strip()
        return None

    for line in lines:
        q = as_question(line)
        if q is not None:
            flush()
            question = q
        elif question is not None:
            s = line.strip()
            if not s:
                continue
            s = re.sub(r"^[-*]?\s*\*\*(?:A|Đáp|Trả lời)[:.]?\*\*\s*", "", s, flags=re.I)
            answer.append(s)
    flush()
    return pairs


def extract_attribution(content: str) -> dict:
    text_lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    copyright_line = ""
    source_lines: list[str] = []
    for ln in text_lines:
        clean = re.sub(r"^[-*]\s*", "", ln)
        low = strip_accents(clean)
        if "©" in clean or low.startswith("copyright") or "ban quyen" in low:
            copyright_line = copyright_line or clean
        elif "nguon" in low or "source" in low or "http" in low:
            source_lines.append(clean)
        else:
            # Unlabelled prose → treat as copyright if none yet, else source note.
            if not copyright_line:
                copyright_line = clean
            else:
                source_lines.append(clean)
    out: dict = {}
    if copyright_line:
        out["copyright"] = copyright_line
    if source_lines:
        out["source_note"] = " ".join(source_lines)
    return out


# ---------------------------------------------------------------------------
# Front-matter append (string-level; new tables go at the END of the FM block)
# ---------------------------------------------------------------------------
def has_field(fm: str, field: str, *, array: bool) -> bool:
    token = f"[[{field}]]" if array else f"[{field}]"
    return any(ln.strip() == token for ln in fm.splitlines())


def render_array_tables(field: str, rows: list[dict]) -> str:
    chunks = []
    for row in rows:
        body = "\n".join(f"{k} = {toml_str(v)}" for k, v in row.items())
        chunks.append(f"[[{field}]]\n{body}")
    return "\n\n".join(chunks)


def render_table(field: str, row: dict) -> str:
    body = "\n".join(f"{k} = {toml_str(v)}" for k, v in row.items())
    return f"[{field}]\n{body}"


def append_fm_block(fm: str, block: str) -> str:
    return fm.rstrip("\n") + "\n\n" + block.strip("\n") + "\n"


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------
def process_file(path: Path, *, fix: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if not parts:
        return {"path": path, "found": [], "note": "no TOML front matter"}
    open_d, fm, close_d, body = parts

    sections = find_sections(body)
    if not sections:
        return {"path": path, "found": []}

    found = [s["section"] for s in sections]
    if not fix:
        return {"path": path, "found": found}

    new_fm = fm
    lines = body.splitlines()
    drop = set()
    moved: list[str] = []

    for sec in sections:
        section = sec["section"]
        content = sec["content"]
        appended = False
        if section == "internal_links":
            rows = extract_links(content, want_internal=True)
            if rows:
                if has_field(new_fm, "internal_links", array=True):
                    # keep FM authoritative, but still add non-dup refs
                    rows = [r for r in rows if r["ref"] not in new_fm]
                if rows:
                    new_fm = append_fm_block(new_fm, render_array_tables("internal_links", rows))
                appended = True
        elif section == "external_links":
            rows = extract_links(content, want_internal=False)
            if rows:
                rows = [r for r in rows if r["url"] not in new_fm]
                if rows:
                    new_fm = append_fm_block(new_fm, render_array_tables("external_links", rows))
                appended = True
        elif section == "faq":
            rows = extract_faq(content)
            if rows:
                rows = [r for r in rows if r["question"] not in new_fm]
                if rows:
                    new_fm = append_fm_block(new_fm, render_array_tables("faq", rows))
                appended = True
        elif section == "attribution":
            row = extract_attribution(content)
            if row and not has_field(new_fm, "attribution", array=False):
                new_fm = append_fm_block(new_fm, render_table("attribution", row))
                appended = True
            elif row:
                appended = True  # FM already owns attribution; just drop the dup body

        if appended:
            for k in range(sec["start"], sec["end"]):
                drop.add(k)
            moved.append(section)

    if not moved:
        return {"path": path, "found": found, "note": "detected but could not parse — left untouched"}

    new_body_lines = [ln for idx, ln in enumerate(lines) if idx not in drop]
    new_body = "\n".join(new_body_lines)
    new_body = re.sub(r"\n{3,}", "\n\n", new_body).rstrip() + "\n"

    path.write_text(open_d + new_fm + close_d + new_body, encoding="utf-8")
    return {"path": path, "found": found, "moved": moved}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true", help="move hard-coded sections into front matter")
    ap.add_argument("--post", help="limit to a single post path")
    args = ap.parse_args()

    if args.post:
        targets = [Path(args.post)]
    else:
        targets = sorted(POSTS_DIR.glob("*.md"))

    offenders = 0
    fixed = 0
    for path in targets:
        result = process_file(path, fix=args.fix)
        if not result["found"]:
            continue
        offenders += 1
        try:
            rel = path.resolve().relative_to(ROOT)
        except ValueError:
            rel = path
        if args.fix and result.get("moved"):
            fixed += 1
            print(f"MOVED  {rel}: {', '.join(result['moved'])} → front matter")
        elif result.get("note"):
            print(f"WARN   {rel}: {', '.join(result['found'])} — {result['note']}")
        else:
            print(f"HARDCODED {rel}: {', '.join(result['found'])}")

    if args.fix:
        print(f"\nDone. {fixed} file(s) fixed, {offenders} file(s) had hard-coded sections.")
        return 0
    if offenders:
        print(f"\n{offenders} post(s) hard-code macro-owned footer sections. Run with --fix to move them.")
        return 1
    print("OK — no hard-coded footer sections found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
