#!/usr/bin/env python3
"""
QA natural — phát hiện nội dung có mùi AI, gợi ý sửa để viết tự nhiên hơn.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

AI_PATTERNS = [
    (r'(?i)trong thời đại (công nghệ|số|4\.0|hiện nay)', 'Mở bài sáo rỗng "Trong thời đại..." — viết như con người đang kể chuyện'),
    (r'(?i)với sự phát triển (không ngừng|vũ bão|nhanh chóng)', 'Mở bài kiểu luận văn — hãy vào thẳng câu chuyện'),
    (r'(?i)không thể phủ nhận (rằng|được)', 'Câu khẳng định vô thưởng vô phạt'),
    (r'(?i)có thể nói (rằng|được)', 'Câu đệm yếu, không có thông tin'),
    (r'(?i)nói (một cách|tóm lại) (thì|, )', 'Câu kết luận sáo rỗng'),
    (r'(?i)bài viết này sẽ (giúp|phân tích|đề cập|trình bày)', 'Cam kết thiếu cá tính — "Bài viết này sẽ..." là AI writing'),
    (r'(?i)trong bối cảnh (đó|này|hiện nay)', 'Mở đầu hàn lâm, người thật không nói thế'),
    (r'(?i)không chỉ .{5,30} mà còn', 'Cấu trúc "không chỉ...mà còn" quá công thức'),
    (r'(?i)bên cạnh đó', 'Chuyển đoạn cơ học — "Bên cạnh đó" AI ưa dùng'),
    (r'(?i)bài viết (này|trên đây) (đã|vừa) (cung cấp|giới thiệu|phân tích)', 'Kết bài AI formula - không như người thật nói'),
    (r'(?i)(hy vọng|mong rằng) bài viết (này|trên) (đã|sẽ) (giúp|cung cấp|mang lại)', 'Kết bài khiêm tốn giả tạo — hãy nói thẳng cảm xúc thật'),
    (r'(?i)nếu bạn (đang|muốn|có) .{0,20} (thì|hãy|đừng ngần ngại)', 'Giọng tư vấn chung chung thiếu cá tính'),
    (r'(?i)(về cơ bản|về tổng quan|nhìn chung)', 'Từ đệm làm yếu câu — người thật ít dùng'),
    (r'(?i)(tuy nhiên|tuy vậy),?\s*(không chỉ|bên cạnh|ngoài ra)', 'Chuyển ý AI điển hình'),
    (r'(?i)với .{3,30} (bạn|người dùng|khách hàng) (có thể|sẽ|hãy)', 'Đặt câu kiểu công thức quảng cáo'),
]

LONG_SENTENCE_PATTERN = re.compile(r'[^.!?]+[.!?]')

def check_sentence_length(body: str):
    issues = []
    for i, line in enumerate(body.split('\n'), 1):
        if line.strip() and not line.startswith('#'):
            for sent in LONG_SENTENCE_PATTERN.findall(line):
                words = len(sent.split())
                if words > 45:
                    issues.append((i, f'Câu quá dài ({words} từ) — nên ngắt thành 2-3 câu ngắn'))
    return issues

def check_repetitive_openers(body: str):
    lines = [l.strip() for l in body.split('\n') if l.strip() and not l.startswith('#') and not l.startswith('- ') and not l.startswith('![')]
    opener_counts = {}
    for line in lines:
        m = re.match(r'^([A-ZĐÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ]+)\b', line)
        if m:
            word = m.group(1)
            opener_counts[word] = opener_counts.get(word, 0) + 1
    issues = []
    for word, count in opener_counts.items():
        if count >= 4:
            issues.append(f'Từ "{word}" mở đầu câu {count} lần — đa dạng hoá cách mở câu')
    return issues

def scan_post(fpath: Path):
    content = fpath.read_text(encoding='utf-8')
    m = re.match(r'^(\+{3}\s*$\n?)(.*?)(\n\+{3}\s*$\n?)(.*)$', content, re.MULTILINE | re.DOTALL)
    if not m:
        return None, None
    fm_text = m.group(2)
    body = m.group(4)
    issues = []
    title_m = re.search(r'^title\s*=\s*"([^"]+)"', fm_text, re.MULTILINE)
    title = title_m.group(1) if title_m else fpath.stem
    for pattern, message in AI_PATTERNS:
        for match in re.finditer(pattern, body):
            line_no = body[:match.start()].count('\n') + 1
            context = body[max(0, match.start()-40):match.end()+40].replace('\n', ' ')
            issues.append((line_no, f'{message}:\n   "...{context}..."'))
    issues.extend(check_sentence_length(body))
    ro_issues = check_repetitive_openers(body)
    for i in ro_issues:
        issues.append((0, i))
    return title, issues

def main():
    fix_mode = '--fix' in sys.argv
    all_issues = 0
    all_posts = 0
    for fpath in sorted(POSTS.glob('*.md')):
        title, issues = scan_post(fpath)
        if title is None or not issues:
            continue
        all_posts += 1
        all_issues += len(issues)
        print(f'\n=== {fpath.stem} ({len(issues)} vấn đề) ===')
        print(f'  Tiêu đề: {title}')
        for line_no, issue in issues:
            print(f'  L{line_no}: {issue}')
    print(f'\n---\nTổng: {all_posts} bài có vấn đề, {all_issues} vấn đề')

if __name__ == '__main__':
    main()
