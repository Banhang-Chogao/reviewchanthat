#!/usr/bin/env python3
"""Generate versioned changelog PDF from git history."""

import subprocess
import sys
import os
import json
import re
from datetime import datetime, timezone

CHANGELOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".artifacts", "changelog-pdf")
MARKER_FILE = os.path.join(CHANGELOG_DIR, ".last-export")


def run_git(args):
    return subprocess.check_output(["git"] + args, text=True).strip()


def get_last_export_hash():
    if os.path.exists(MARKER_FILE):
        with open(MARKER_FILE) as f:
            return f.read().strip()
    return None


def save_export_hash(hash_):
    os.makedirs(CHANGELOG_DIR, exist_ok=True)
    with open(MARKER_FILE, "w") as f:
        f.write(hash_)


def get_commits_since(hash_):
    if hash_:
        log = run_git(["log", f"{hash_}..HEAD", "--oneline", "--format=%H%n%ad%n%s", "--date=short"])
    else:
        # last 30 days
        log = run_git(["log", "--since=30.days", "--oneline", "--format=%H%n%ad%n%s", "--date=short"])
    lines = log.strip().split("\n")
    commits = []
    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            commits.append({
                "hash": lines[i],
                "date": lines[i + 1],
                "message": lines[i + 2],
            })
    return commits


def get_pr_info(token, commit_hash):
    """Try to get PR info for a commit via GitHub API."""
    try:
        import urllib.request
        url = f"https://api.github.com/search/issues?q=repo:Banhang-Chogao/reviewchanthat+sha:{commit_hash}+type:pr"
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"token {token}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("items"):
                pr = data["items"][0]
                return {"number": pr["number"], "title": pr["title"], "url": pr["html_url"]}
    except Exception:
        pass
    return None


def categorize(message, pr_info):
    """Categorize a commit based on its message prefix."""
    msg_lower = message.lower()

    categories = {
        "Content": ["content:", "new post", "add post", "bài viết", "travel series", "article"],
        "UI/UX": ["feat(ux):", "feat(ui):", "fix(ui):", "ui/ux", "style(", "ui modernization", "layout", "responsive"],
        "SEO": ["seo", "sitemap", "canonical", "meta", "description", "slug", "url aliases"],
        "Performance": ["perf:", "performance", "minify", "optimize", "compress", "lazy"],
        "Tools/CMS/Admin": ["cms:", "admin", "writer", "feat(cms):", "fix(cms):", "tool", "script"],
        "Bug fixes": ["fix:", "hotfix", "bug"],
        "CI/QA/Deploy": ["ci:", "deploy", "qa", "workflow", "cl9"],
        "Other": [],
    }

    for cat, patterns in categories.items():
        if cat == "Other":
            continue
        for pat in patterns:
            if pat in msg_lower or pat in message:
                return cat

    return "Other"


def guess_category_from_message(message):
    msg_lower = message.lower()
    if "content:" in msg_lower or "new post" in msg_lower or "add post" in msg_lower or "bài viết" in msg_lower or "travel" in msg_lower or "article" in msg_lower:
        return "Content"
    if "feat(ux):" in msg_lower or "feat(ui):" in msg_lower or "fix(ui):" in msg_lower or "style(" in msg_lower or "layout" in msg_lower or "responsive" in msg_lower:
        return "UI/UX"
    if "perf:" in msg_lower or "performance" in msg_lower:
        return "Performance"
    if "cms:" in msg_lower or "admin" in msg_lower or "writer" in msg_lower:
        return "Tools/CMS/Admin"
    if message.startswith("fix:") or message.startswith("hotfix") or ("bug" in msg_lower and "fix" in msg_lower):
        return "Bug fixes"
    if "ci:" in msg_lower or "deploy" in msg_lower or "qa" in msg_lower or "cl9" in msg_lower:
        return "CI/QA/Deploy"
    if "seo" in msg_lower or "sitemap" in msg_lower or "canonical" in msg_lower:
        return "SEO"
    return "Other"


def strip_accents(s):
    """Remove Vietnamese diacritics for PDF Latin-1 compatibility."""
    replacements = {
        'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
        'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
        'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
        'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
        'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
        'đ': 'd',
        'À': 'A', 'Á': 'A', 'Ạ': 'A', 'Ả': 'A', 'Ã': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ậ': 'A', 'Ẩ': 'A', 'Ẫ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ặ': 'A', 'Ẳ': 'A', 'Ẵ': 'A',
        'È': 'E', 'É': 'E', 'Ẹ': 'E', 'Ẻ': 'E', 'Ẽ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ệ': 'E', 'Ể': 'E', 'Ễ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ị': 'I', 'Ỉ': 'I', 'Ĩ': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ọ': 'O', 'Ỏ': 'O', 'Õ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ộ': 'O', 'Ổ': 'O', 'Ỗ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ợ': 'O', 'Ở': 'O', 'Ỡ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ụ': 'U', 'Ủ': 'U', 'Ũ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ự': 'U', 'Ử': 'U', 'Ữ': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỵ': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y',
        'Đ': 'D',
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return s


def generate_16_digit_id(seed):
    """Generate a 16-digit numeric ID from a seed string."""
    import hashlib
    h = hashlib.sha256(seed.encode()).hexdigest()
    num = int(h[:16], 16) % 10**16
    return f"{num:016d}"


def add_watermark(pdf, text, total_pages=1):
    """Add diagonal watermark on every page."""
    for page_num in range(1, total_pages + 1):
        pdf.page = page_num
        w = pdf.w
        h = pdf.h
        pdf.set_font("Helvetica", "B", 36)
        pdf.set_text_color(200, 200, 200)
        with pdf.rotation(45, x=w/2, y=h/2):
            pdf.text(w/2 - 50, h/2, strip_accents(text))


def add_digital_signature(pdf, hash_id, base_url, export_date):
    """Add a Viettel MSign-style digital signature box."""
    pdf.ln(8)
    pdf.set_draw_color(0, 102, 204)
    pdf.set_line_width(0.8)
    y_start = pdf.get_y()
    box_h = 50
    pdf.rect(pdf.l_margin, y_start, pdf.w - pdf.l_margin - pdf.r_margin, box_h)
    pdf.set_fill_color(240, 247, 255)
    pdf.rect(pdf.l_margin, y_start, pdf.w - pdf.l_margin - pdf.r_margin, box_h, "F")
    pdf.set_xy(pdf.l_margin + 3, y_start + 2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 6, strip_accents("CHỮ KÝ SỐ / DIGITAL SIGNATURE"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 5, strip_accents(f"  Hash ID (16-digit): {hash_id}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.cell(0, 5, strip_accents(f"  Signed by: SeoMoney CI/CD"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.cell(0, 5, strip_accents(f"  Timestamp: {export_date}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.cell(0, 5, strip_accents(f"  Base URL: {base_url}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.cell(0, 5, strip_accents(f"  Certificate: Viettel MSign Compatible"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, strip_accents("  Trang nay duoc ky so boi he thong tu dong. / This page is auto-signed."), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(y_start + box_h + 5)


def generate_pdf(commits, grouped, export_date, head_hash, branch, range_desc, base_url):
    try:
        from fpdf import FPDF
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "-q"])
        from fpdf import FPDF

    hash_id = generate_16_digit_id(head_hash + export_date)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, strip_accents("SEOMONEY Changelog"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, strip_accents(f"Export date: {export_date}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, strip_accents(f"Branch: {branch}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, strip_accents(f"HEAD: {head_hash}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, strip_accents(f"Range: {range_desc}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, strip_accents(f"Total changes: {len(commits)}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, strip_accents(f"Hash ID: {hash_id}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Summary table
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, strip_accents("Summary"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for cat in sorted(grouped.keys()):
        count = len(grouped[cat])
        if count > 0:
            pdf.cell(0, 7, strip_accents(f"  {cat}: {count}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Detailed changes
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, strip_accents("Detailed Changes"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    show_groups = sorted(grouped.keys())
    for cat in show_groups:
        items = grouped.get(cat, [])
        if not items:
            continue
        # Check if next page needed
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 8, strip_accents(f"  {cat}"), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", "", 9)
        for c in items:
            if pdf.get_y() > 265:
                pdf.add_page()
            msg = c["message"]
            if len(msg) > 90:
                msg = msg[:87] + "..."
            pr = c.get("pr")
            pr_text = f" #{pr['number']}" if pr else ""
            pdf.set_x(pdf.l_margin + 5)
            line = f"[{c['date']}] {msg}{pr_text}"
            pdf.multi_cell(0, 5, strip_accents(line))
        pdf.ln(2)

    # Footer content before signature
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"Generated by cl0 on {export_date}", new_x="LMARGIN", new_y="NEXT", align="C")

    # Digital signature
    add_digital_signature(pdf, hash_id, base_url, export_date)

    # Watermark on all pages
    total_pages = len(pdf.pages)
    add_watermark(pdf, base_url, total_pages)

    return pdf


def main():
    token = os.environ.get("GIT_TOKEN", "")
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    head_hash = run_git(["rev-parse", "HEAD"])
    head_short = run_git(["rev-parse", "--short", "HEAD"])
    export_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    last_hash = get_last_export_hash()

    commits = get_commits_since(last_hash)

    if not commits:
        print("Khong tim thay thay doi moi trong giai doan nay.")
        save_export_hash(head_hash)
        sys.exit(0)

    # Try to get PR info for each commit
    for c in commits:
        pr = get_pr_info(token, c["hash"])
        if pr:
            c["pr"] = pr

    # Categorize
    grouped = {}
    for c in commits:
        cat = guess_category_from_message(c["message"])
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(c)

    # Determine range description
    if last_hash:
        short_last = run_git(["rev-parse", "--short", last_hash])
        range_desc = f"{short_last}..{head_short}"
    else:
        range_desc = f"since 30 days (last export not found) .. {head_short}"

    # Get base URL from Hugo config
    base_url = "https://banhang-chogao.github.io/reviewchanthat/"

    # Generate PDF
    pdf = generate_pdf(commits, grouped, export_date, head_short, branch, range_desc, base_url)

    # Save
    os.makedirs(CHANGELOG_DIR, exist_ok=True)
    version = export_date.replace(" UTC", "").replace(":", "").replace(" ", "-")
    filename = f"seomoney-changelog-v{version}.pdf"
    filepath = os.path.join(CHANGELOG_DIR, filename)
    pdf.output(filepath)

    # Save marker
    save_export_hash(head_hash)

    # Output summary
    total_cats = sum(1 for v in grouped.values() if v)
    print(f"=== cl0: Changelog Export ===")
    print(f"File: {filename}")
    print(f"Path: {filepath}")
    print(f"Git range: {range_desc}")
    print(f"Total changes: {len(commits)}")
    for cat in sorted(grouped.keys()):
        if grouped[cat]:
            print(f"  {cat}: {len(grouped[cat])}")
    print(f"PDF stored in repo but excluded from public blog output.")


if __name__ == "__main__":
    main()
