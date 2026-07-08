#!/usr/bin/env python3
"""
Migrate travel (du-lich) posts from hardcoded sections to front-matter-driven data.

Removes hardcoded:
  - ## Câu hỏi thường gặp / ## FAQ
  - ## Liên kết bên trong
  - ## Nguồn tham khảo

Converts them to front-matter fields:
  - faq: [{question, answer}]
  - internal_links: [{title, url}]
  - external_links: [{title, url}]
  - attribution: {copyright, source_note}

The post-footer.html partial auto-renders these sections at build time.
"""

import os
import re
import sys
import yaml

POSTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "posts")



UNVERIFIED_CLAIMS = {
    "rất đông vào": "Cuối tuần và mùa cao điểm thường dễ đông hơn, nên cân nhắc đi sớm để tránh đông.",
    "Rất đông vào": "Cuối tuần và mùa cao điểm thường dễ đông hơn, nên cân nhắc đi sớm để tránh đông.",
    "nên đi trước 10:00": None,
    "nên đi trước 10:00.": None,
    "nên mua vé": "Nên kiểm tra tình trạng vé trên website chính thức trước khi đi.",
    "nên mua vé ferry": "Nên kiểm tra tình trạng vé ferry trên website chính thức trước khi đi.",
    "nên mua vé ferry hoặc combo tour trực tuyến trước": None,
    "Zipline có an toàn không?": None,
    "Có, nhưng cần đáp ứng yêu cầu về cân nặng và sức khỏe": None,
    "Có, đường đi bộ bằng phẳng, có xe điện cho người khó đi bộ.": None,
    "Có xe điện cho người khó đi bộ.": None,
    "KKday": None,
    "Klook": None,
}


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def is_travel_post(content):
    """Check if post belongs to du-lich category."""
    fm_text, body = parse_front_matter(content)
    if fm_text is None:
        return False
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        return False
    cats = fm.get("categories", [])
    if isinstance(cats, str):
        cats = [cats]
    return "du-lich" in cats


def parse_front_matter(content):
    """Manually split front matter and body."""
    content = content.lstrip()
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    fm_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    return fm_text, body


def parse_yaml_front_matter(fm_text):
    """Parse YAML front matter text to dict."""
    return yaml.safe_load(fm_text) or {}


def dump_yaml_front_matter(fm_dict):
    """Dump dict to YAML front matter string."""
    return yaml.dump(fm_dict, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()


def find_sections(body):
    lines = body.split("\n")
    sections = []
    faq_patterns = [
        r"^##\s+Câu hỏi thường gặp(?:\s*\(.*?\))?\s*$",
        r"^##\s+Câu hỏi thường gìp(?:\s*\(.*?\))?\s*$",
        r"^##\s+FAQ\s*$",
    ]
    intl_patterns = [r"^##\s+Liên kết bên trong\s*$"]
    src_patterns = [r"^##\s+Nguồn tham khảo\s*$"]

    for i, line in enumerate(lines):
        stripped = line.strip()
        for p in faq_patterns:
            if re.match(p, stripped):
                sections.append((i, "faq"))
                break
        for p in intl_patterns:
            if re.match(p, stripped):
                sections.append((i, "internal_links"))
                break
        for p in src_patterns:
            if re.match(p, stripped):
                sections.append((i, "sources"))
                break

    return sections


def parse_faq_section(lines, start_idx):
    """Parse FAQ section: extract Q&A pairs from h3 + answer paragraphs."""
    faqs = []
    i = start_idx + 1  # Skip the heading

    current_q = None
    current_a_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # End of section (next h2 or end of file)
        if re.match(r"^##\s", stripped):
            break

        # FAQ question (h3)
        h3_match = re.match(r"^###\s+(.+)$", stripped)
        if h3_match:
            # Save previous Q&A if exists
            if current_q:
                answer = " ".join(current_a_lines).strip()
                if answer:
                    faqs.append({"question": current_q, "answer": answer})
                current_a_lines = []
            current_q = h3_match.group(1).strip()
            i += 1
            continue

        # Answer text
        if current_q and stripped:
            current_a_lines.append(stripped)
        elif current_q and not stripped and current_a_lines:
            current_a_lines.append("")

        i += 1

    # Save last Q&A
    if current_q:
        answer = " ".join(current_a_lines).strip()
        if answer:
            faqs.append({"question": current_q, "answer": answer})

    return faqs, i


def parse_internal_links_section(lines, start_idx):
    """Parse internal links section: extract markdown links."""
    links = []
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if re.match(r"^##\s", stripped):
            break

        # Match markdown links: [title](url)
        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", stripped)
        for title, url in link_matches:
            if url.startswith("/") or url.startswith("http"):
                title = title.strip()
                # Clean trailing punctuation from title
                title = re.sub(r"\s*[.!?:]+$", "", title)
                links.append({"title": title, "url": url.strip()})

        i += 1

    return links, i


def parse_sources_section(lines, start_idx):
    """Parse sources section: extract external links + create attribution."""
    external_links = []
    source_notes = []
    has_kkday = False
    has_klook = False
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if re.match(r"^##\s", stripped):
            break

        # Match markdown links: [title](url) or plain URLs
        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", stripped)
        url_matches = re.findall(r"https?://[^\s)]+", stripped)

        for title, url in link_matches:
            title = title.strip()
            title = re.sub(r"\s*[.!?:]+$", "", title)
            url = url.strip()

            # Remove KKday/Klook links
            if "kkday" in url.lower() or "klook" in url.lower():
                has_kkday = "kkday" in url.lower()
                has_klook = "klook" in url.lower()
                source_notes.append(f"(Removed: {title})")
                continue

            external_links.append({"title": title, "url": url})
            # Add to source notes
            source_notes.append(f"{title}")

        for url in url_matches:
            url = url.strip().rstrip(".)")
            if not any(link["url"] == url for link in external_links):
                if "kkday" in url.lower() or "klook" in url.lower():
                    continue
                external_links.append({"title": url, "url": url})
                source_notes.append(url)

        i += 1

    # Build attribution
    copyright_text = f"© 2026 Review Chân Thật. Bài viết tham khảo và tổng hợp từ các nguồn du lịch uy tín."

    attribution = {
        "copyright": copyright_text,
        "source_note": "Bài viết tham khảo từ các nguồn: "
        + ", ".join(source_notes[:5])
        + (" và các nguồn khác." if len(source_notes) > 5 else ".")
    }

    return external_links, attribution, i, has_kkday, has_klook


def sanitize_claims(faqs):
    safe_faqs = []
    for faq in faqs:
        q = faq["question"]
        a = faq["answer"]

        if "đông" in a.lower() and "tháng" not in a.lower():
            a = a  # no specific month claim, keep as-is

        a = re.sub(
            r"Rất đông vào\s*[^,.]+",
            "Khu vực này thường đông vào cuối tuần và mùa cao điểm",
            a,
        )
        a = re.sub(
            r"rất đông vào\s*[^,.]+",
            "thường đông vào cuối tuần và mùa cao điểm",
            a,
        )
        a = re.sub(
            r"[Nn]ên đi trước\s*\S+(?:\s+\S+)?",
            "nên cân nhắc đi sớm trong ngày",
            a,
        )
        a = re.sub(
            r"[Nn]ên mua vé\s*[^,.]*",
            "nên kiểm tra tình trạng vé trên website chính thức của điểm đến",
            a,
        )

        if "Zipline có an toàn không" in q and "Zipline" in q:
            a = "Zipline được vận hành theo tiêu chuẩn kỹ thuật. Bạn nên kiểm tra điều kiện sức khỏe và yêu cầu tham gia trên website chính thức trước khi trải nghiệm."

        if "xe điện" in a.lower():
            a = "Khu vực này có dịch vụ xe điện hỗ trợ, bạn nên kiểm tra thông tin chi tiết trên website chính thức."

        if "KKday" in a or "Klook" in a:
            a = re.sub(r"KKday[^.]*\.?\s*", "", a)
            a = re.sub(r"Klook[^.]*\.?\s*", "", a)
            a = a.strip(",;. ") or "Bạn có thể tham khảo các nền tảng đặt vé trực tuyến."

        safe_faqs.append({"question": q, "answer": a.strip()})

    return safe_faqs


def remove_sections(body, section_boundaries):
    """Remove sections from body given their line boundaries."""
    lines = body.split("\n")
    # Remove sections in reverse order to preserve line numbers
    section_boundaries.sort(key=lambda x: x[1], reverse=True)

    for start, end in section_boundaries:
        # Remove trailing blank lines before section
        while start > 0 and lines[start - 1].strip() == "":
            start -= 1
        del lines[start:end]

    # Clean up multiple consecutive blank lines
    result = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank

    return "\n".join(result).strip() + "\n"


def migrate_post(filepath):
    """Migrate a single travel post."""
    content = read_file(filepath)
    basename = os.path.basename(filepath)

    if not is_travel_post(content):
        return False

    # Parse front matter
    fm_text, body = parse_front_matter(content)
    if fm_text is None:
        print(f"  SKIP: no front matter found")
        return False

    fm = parse_yaml_front_matter(fm_text)
    if not fm:
        print(f"  SKIP: empty front matter")
        return False

    # Find sections
    lines = body.split("\n")
    sections = find_sections(body)

    if not sections:
        print(f"  SKIP: no hardcoded sections found")
        return False

    print(f"\n  Found {len(sections)} hardcoded sections in {basename}")

    # Process sections
    section_boundaries = []
    faqs = []
    internal_links = []
    external_links = []
    attribution = None
    removed_kkday = False
    removed_klook = False

    for line_idx, section_type in sorted(sections, reverse=True):
        if section_type == "faq":
            parsed_faqs, end_idx = parse_faq_section(lines, line_idx)
            faqs.extend(parsed_faqs)
            section_boundaries.append((line_idx, end_idx))
            print(f"    FAQ: {len(parsed_faqs)} Q&A pairs")

        elif section_type == "internal_links":
            parsed_links, end_idx = parse_internal_links_section(lines, line_idx)
            internal_links.extend(parsed_links)
            section_boundaries.append((line_idx, end_idx))
            print(f"    Internal links: {len(parsed_links)} links")

        elif section_type == "sources":
            parsed_links, parsed_attr, end_idx, has_kkday, has_klook = parse_sources_section(
                lines, line_idx
            )
            external_links.extend(parsed_links)
            attribution = parsed_attr
            section_boundaries.append((line_idx, end_idx))
            if has_kkday:
                removed_kkday = True
            if has_klook:
                removed_klook = True
            print(
                f"    Sources: {len(parsed_links)} links, attribution created"
                + (" (KKday removed)" if has_kkday else "")
                + (" (Klook removed)" if has_klook else "")
            )

    # Sanitize claims in FAQ
    if faqs:
        faqs = sanitize_claims(faqs)

    # Remove sections from body
    new_body = remove_sections(body, section_boundaries)

    # Update front matter
    if faqs:
        fm["faq"] = faqs
    if internal_links:
        fm["internal_links"] = internal_links
    if external_links:
        fm["external_links"] = external_links
    if attribution:
        fm["attribution"] = attribution

    # Remove empty tags
    tags = fm.get("tags", [])
    if tags and isinstance(tags, list):
        fm["tags"] = [t for t in tags if t.strip()]

    # Rebuild file
    new_fm_text = dump_yaml_front_matter(fm)
    new_content = f"---\n{new_fm_text}\n---\n\n{new_body}"

    write_file(filepath, new_content)
    print(f"  DONE: {basename}")
    return True


def main():
    files = sorted(os.listdir(POSTS_DIR))
    md_files = [f for f in files if f.endswith(".md")]

    migrated = 0
    skipped = 0
    errors = 0

    for filename in md_files:
        filepath = os.path.join(POSTS_DIR, filename)
        content = read_file(filepath)

        if not is_travel_post(content):
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {filename}")

        try:
            if migrate_post(filepath):
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")


if __name__ == "__main__":
    main()
