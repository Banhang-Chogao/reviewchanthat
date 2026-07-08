#!/usr/bin/env python3
"""
Add tom_tat_nhanh frontmatter to all 38 blog posts.
For posts with existing "## Tóm tắt nhanh" tables, extract data from the table.
For posts without, create appropriate data based on content.
Remove the manual "## Tóm tắt nhanh" table from the body.
"""

import re
from pathlib import Path

POSTS_DIR = Path("/Users/duynguyen/Desktop/reviewchanthat/content/posts")

WITH_TABLE_FILES = {
    "bien-dep-o-jeju-hamdeok-hyeopjae-va-cach-chon-khu-nghi-ven-bien.md",
    "caribbean-bay-yongin-cong-vien-nuoc-lon-gan-seoul-nen-di-ngay-nao.md",
    "cheongsapo-busan-bien-trong-lang-ven-bien-va-lich-trinh-ket-hop-blue-line-park.md",
    "cho-dia-phuong-han-quoc-an-gi-o-seoul-busan-va-jeju.md",
    "club-d-oasis-busan-infinity-pool-spa-va-lua-chon-tranh-nong-kieu-nghi-duong.md",
    "day-trip-suwon-gan-seoul-hwaseong-haenggung-va-korean-folk-village-trong-mot-ngay.md",
    "di-choi-gan-seoul-incheon-chinatown-wolmido-va-caribbean-bay-nen-chon-diem-nao.md",
    "dia-diem-quay-phim-han-quoc-o-seoul-di-theo-dau-k-drama-ma-khong-bi-qua-touristic.md",
    "gwangalli-beach-busan-bai-bien-ngam-cau-gwangan-dep-nhat-hop-di-chieu-toi.md",
    "haeundae-beach-busan-di-bien-mua-he-the-nao-de-khong-qua-dong.md",
    "jjimjilbang-han-quoc-sauna-kieu-han-o-seoul-va-aquafield-goyang-co-gi-hay.md",
    "jungmun-beach-jeju-bai-bien-cho-nguoi-thich-song-anh-dep-va-hoat-dong-nuoc.md",
    "nami-island-mua-he-day-trip-gan-seoul-de-tranh-nong-duoi-bong-cay-va-gio-song.md",
    "ngam-binh-minh-o-jeju-seongsan-seopjikoji-va-lich-trinh-sang-som-o-seogwipo.md",
    "shinhwa-theme-park-jeju-water-slides-va-diem-choi-nuoc-cho-gia-dinh-o-jungmun.md",
    "thue-hanbok-o-seoul-di-cung-dien-lang-hanok-va-chup-anh-sao-cho-dang-tien.md",
    "trai-nghiem-k-beauty-o-seoul-makeup-personal-color-va-lich-trinh-cho-nguoi-me-lam-dep.md",
    "udo-jeju-dao-nho-bien-da-den-hai-dang-trang-va-cach-tranh-nong-nua-ngay.md",
    "wolmido-incheon-bien-boardwalk-va-diem-choi-gan-seoul-cho-gia-dinh.md",
    "wwdc26-da-qua-nhan-dinh-sau-su-kien-ve-siri-ai-ios-27-va-nhung-gi-apple-chua-noi.md",
    "xem-musical-va-show-o-seoul-trai-nghiem-buoi-toi-dang-thu-khi-du-lich-han-quoc.md",
}

# Files that have tables but should use custom data (non-standard table formats)
USE_CUSTOM_FOR_TABLE = {
    "di-choi-gan-seoul-incheon-chinatown-wolmido-va-caribbean-bay-nen-chon-diem-nao.md",
}

CUSTOM_TOM_TAT_NHANH = {
    "10-diem-tranh-nong-duoi-nuoc-o-han-quoc-mua-he-bien-dao-cong-vien-nuoc-va-day-trip-de-di.md": [
        ("Nội dung", "Top 10 điểm tránh nóng mùa hè Hàn Quốc: biển Jeju, bãi biển Busan, công viên nước, day trip gần Seoul"),
        ("Số lượng điểm", "10 điểm chia làm 3 nhóm (Jeju, Busan, gần Seoul)"),
        ("Hợp với", "Người đi Hàn Quốc mùa hè, gia đình, cặp đôi"),
        ("Thời gian đọc", "5–7 phút"),
    ],
    "alpensia-ski-resort-trai-nghiem-truot-tuyet-mua-dong-o-pyeongchang.md": [
        ("Khu vực", "Daegwallyeong, Pyeongchang (Gangwon-do)"),
        ("Loại trải nghiệm", "Trượt tuyết, nghỉ dưỡng, water park"),
        ("Hợp với", "Gia đình, người mới bắt đầu, người muốn nghỉ dưỡng"),
        ("Thời gian nên dành", "1–2 ngày (nên ở lại qua đêm)"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2)"),
        ("Có cần đặt trước không", "Có (resort, vé trượt tuyết)"),
    ],
    "cach-doc-mot-bai-review-de-khong-bi-dat-mui.md": [
        ("Chủ đề", "Kỹ năng đọc review, phân biệt review thật và quảng cáo"),
        ("Mục đích", "Giúp người tiêu dùng không bị lừa khi đọc review"),
        ("Hợp với", "Người thường xuyên mua sắm online, người đọc review"),
        ("Mẹo quan trọng", "Kiểm tra động cơ người viết, đọc ít nhất 3–5 nguồn"),
    ],
    "cach-xay-dung-thoi-quen-mua-sam-thong-minh.md": [
        ("Chủ đề", "Xây dựng thói quen mua sắm thông minh, có kế hoạch"),
        ("Mục đích", "Giảm mua sắm bốc đồng, tối ưu chi tiêu"),
        ("Hợp với", "Người muốn kiểm soát chi tiêu, mua sắm có trách nhiệm"),
        ("Điểm chính", "Lên danh sách trước khi mua, đợi 24h trước khi quyết định"),
    ],
    "di-choi-gan-seoul-incheon-chinatown-wolmido-va-caribbean-bay-nen-chon-diem-nao.md": [
        ("Nội dung", "So sánh 5 điểm đi chơi gần Seoul: Gwangmyeong Cave, Songwol-dong, Incheon Chinatown, Wolmido, Caribbean Bay"),
        ("Số lượng điểm", "5 điểm đến trong top 20 hoạt động du lịch Hàn Quốc 2026"),
        ("Hợp với", "Người muốn day trip từ Seoul, gia đình, nhóm bạn"),
        ("Thời gian đọc", "5–7 phút"),
    ],
    "checklist-truoc-khi-mua-mot-san-pham-online.md": [
        ("Chủ đề", "Checklist kiểm tra trước khi mua hàng online"),
        ("Mục đích", "Tránh mua phải hàng kém chất lượng, hối hận sau khi mua"),
        ("Hợp với", "Người thường xuyên mua sắm online, người muốn tiêu tiền thông minh"),
        ("Điểm chính", "Kiểm tra người bán, chính sách đổi trả, đọc kỹ mô tả sản phẩm"),
    ],
    "elysian-gangchon-ski-khu-truot-tuyet-gan-seoul-cho-nguoi-moi-bat-dau.md": [
        ("Khu vực", "Gangchon, Gangwon-do (75 km từ Seoul)"),
        ("Loại trải nghiệm", "Trượt tuyết trong ngày, ski school"),
        ("Hợp với", "Người mới bắt đầu, day trip từ Seoul"),
        ("Thời gian nên dành", "Trong ngày hoặc 1 đêm"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2)"),
        ("Có cần đặt trước không", "Có (shuttle bus, thuê đồ, vé)"),
    ],
    "high1-ski-resort-khu-truot-tuyet-cho-nguoi-muon-nghi-duong-mua-dong-o-han-quoc.md": [
        ("Khu vực", "Jeongseon, Gangwon-do (200 km từ Seoul)"),
        ("Loại trải nghiệm", "Trượt tuyết, nghỉ dưỡng, casino, spa"),
        ("Hợp với", "Người muốn nghỉ dưỡng kết hợp trượt tuyết, gia đình"),
        ("Thời gian nên dành", "2–3 ngày"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2)"),
        ("Có cần đặt trước không", "Có (resort, vé trượt tuyết)"),
    ],
    "oak-valley-khu-truot-tuyet-nhe-nang-cho-nguoi-moi-o-wonju.md": [
        ("Khu vực", "Wonju, Gangwon-do (100 km từ Seoul)"),
        ("Loại trải nghiệm", "Trượt tuyết beginner, nghỉ dưỡng nhẹ"),
        ("Hợp với", "Người mới bắt đầu, gia đình có trẻ nhỏ, người thích yên tĩnh"),
        ("Thời gian nên dành", "Trong ngày hoặc 1 đêm"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2)"),
        ("Có cần đặt trước không", "Có (shuttle bus, vé)"),
    ],
    "review-cong-nghe-nen-tin-benchmark-hay-trai-nghiem-that.md": [
        ("Chủ đề", "Benchmark vs trải nghiệm thực tế khi review công nghệ"),
        ("Mục đích", "Giúp người đọc hiểu điểm mạnh/yếu của từng loại review"),
        ("Hợp với", "Người quan tâm công nghệ, người đọc review sản phẩm"),
        ("Điểm chính", "Benchmark đo hiệu năng thuần, trải nghiệm thật mới phản ánh dùng hàng ngày"),
    ],
    "so-sanh-gia-bao-hanh-va-trai-nghiem-yeu-to-nao-quan-trong-nhat.md": [
        ("Chủ đề", "So sánh giá, bảo hành và trải nghiệm khi mua sản phẩm"),
        ("Mục đích", "Giúp người tiêu dùng quyết định yếu tố nào quan trọng nhất"),
        ("Hợp với", "Người đang cân nhắc mua sản phẩm, người muốn tiêu tiền đúng"),
        ("Điểm chính", "Trải nghiệm thực tế quan trọng hơn giá rẻ nếu không dùng được lâu dài"),
    ],
    "top-20-hoat-dong-khi-du-lich-han-quoc-2026-choi-gi-o-seoul-busan-jeju-va-gan-seoul.md": [
        ("Nội dung", "20 hoạt động du lịch Hàn Quốc 2026 theo Trip.Best Trip.com"),
        ("Số lượng điểm", "20 hoạt động chia 4 nhóm (Seoul, Busan, Jeju, gần Seoul)"),
        ("Hợp với", "Người lần đầu đi Hàn Quốc, cặp đôi, gia đình, bạn bè"),
        ("Thời gian đọc", "8–10 phút"),
    ],
    "top-dia-diem-truot-tuyet-o-han-quoc-mua-dong-nen-di-khu-nao-neu-lan-dau-truot-tuyet.md": [
        ("Nội dung", "So sánh 6 ski resort Hàn Quốc cho người mới bắt đầu"),
        ("Số lượng điểm", "6 resort tại Gangwon-do"),
        ("Hợp với", "Người lần đầu trượt tuyết, gia đình, day trip từ Seoul"),
        ("Thời gian đọc", "5–7 phút"),
    ],
    "veritable-content-buc-tranh-tong-the-ve-giao-dien-content-va-kien-truc-cong-nghe-phia-sau-blog.md": [
        ("Chủ đề", "Tổng quan về giao diện, content và kiến trúc công nghệ blog Veritable Content"),
        ("Mục đích", "Giải thích triết lý thiết kế, lựa chọn công nghệ và quy trình vận hành blog"),
        ("Hợp với", "Người làm blog, quan tâm Hugo, Flat Design, content architecture"),
        ("Điểm chính", "Text-first, Hugo + Python + GitHub Actions, Flat Design, không JavaScript nặng"),
    ],
    "vi-sao-review-dai-chua-chac-da-dang-tin.md": [
        ("Chủ đề", "Review dài chưa chắc đã đáng tin — dấu hiệu nhận biết content marketing"),
        ("Mục đích", "Cảnh giác người đọc trước các bài review dài nhưng thiếu trung thực"),
        ("Hợp với", "Người thường xuyên đọc review trước khi mua hàng"),
        ("Điểm chính", "Review thật có cả ưu và nhược điểm, ngôn ngữ tự nhiên, không tập trung link mua hàng"),
    ],
    "vivaldi-park-ski-world-co-dang-di-truot-tuyet-tu-seoul-trong-ngay-khong.md": [
        ("Khu vực", "Hongcheon, Gangwon-do (khoảng 1,5–2 giờ từ Seoul)"),
        ("Loại trải nghiệm", "Trượt tuyết, công viên nước, nghỉ dưỡng"),
        ("Hợp với", "Gia đình, nhóm bạn, người muốn day trip hoặc nghỉ qua đêm"),
        ("Thời gian nên dành", "Trong ngày hoặc 1–2 đêm"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2) — Ocean World mở cửa hè"),
        ("Có cần đặt trước không", "Có (shuttle bus, vé, thuê đồ)"),
    ],
    "wwdc26-phan-tich-nhung-tinh-nang-ios-27-va-macos-27-apple-mang-len-san-khau.md": [
        ("Chủ đề", "WWDC26 phân tích tính năng iOS 27 và macOS 27"),
        ("Mục đích", "Tổng hợp kỳ vọng, tin đồn và thông tin Apple xác nhận trước sự kiện"),
        ("Hợp với", "Người quan tâm Apple, công nghệ, hệ sinh thái Apple"),
        ("Điểm chính", "Siri AI, iOS 27, macOS Golden Gate 27, iPhone gập không xuất hiện"),
    ],
    "yongpyong-ski-resort-resort-truot-tuyet-noi-tieng-o-pyeongchang-co-hop-voi-du-khach-viet.md": [
        ("Khu vực", "Daegwallyeong, Pyeongchang (Gangwon-do, 200 km từ Seoul)"),
        ("Loại trải nghiệm", "Trượt tuyết chuyên sâu, nghỉ dưỡng"),
        ("Hợp với", "Người trượt trung bình–cao cấp, người muốn resort lớn"),
        ("Thời gian nên dành", "1–2 ngày (nên ở lại qua đêm)"),
        ("Đi mùa nào hợp", "Mùa đông (tháng 12–2)"),
        ("Có cần đặt trước không", "Có (resort, vé trượt tuyết)"),
    ],
}

WWDC26_DA_QUA_TOM_TAT = [
    ("Chủ đề", "WWDC26 nhận định sau sự kiện — Siri AI, iOS 27 và những gì Apple chưa nói"),
    ("Sản phẩm chính", "Siri AI, iOS 27, macOS Golden Gate 27"),
    ("Tính năng đáng chú ý", "Siri AI hội thoại đa lượt, cải thiện hiệu năng, gói an toàn trẻ em"),
    ("Mức độ hoàn thiện", "Beta tuần đầu: Siri AI còn giới hạn ngôn ngữ, hiệu năng shell khả quan"),
    ("Hợp với", "Người dùng Apple, người quan tâm công nghệ"),
]


def parse_table_rows_from_body(body):
    """Parse table rows from a markdown table in the body. Returns list of (label, value) tuples."""
    lines = body.strip().split('\n')
    rows = []
    after_separator = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            if after_separator:
                break
            continue
        # Skip separator lines (only dashes, pipes, colons, spaces between pipes)
        if re.match(r'^\|[\s\-:]+(\|[\s\-:]+)*\|$', stripped):
            after_separator = True
            continue
        if after_separator:
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if len(cells) >= 2:
                rows.append((cells[0], '|'.join(cells[1:]).strip()))
    return rows


def remove_table_from_body(body):
    """Remove the Tóm tắt nhanh section (heading + table) from the body.
    Handles both compact (heading directly followed by table) and spaced formats."""
    lines = body.split('\n')
    result = []
    skipping = False
    marker_found = False
    seen_content_after = False

    for line in lines:
        if '## Tóm tắt nhanh' in line and not marker_found:
            skipping = True
            marker_found = True
            continue
        if skipping:
            stripped = line.strip()
            # Skip table lines, separator lines, and blank lines between heading and table
            if stripped.startswith('|') or stripped.startswith('|---') or stripped == '':
                continue
            # If we hit a new heading, stop skipping and include it
            if stripped.startswith('## '):
                skipping = False
                result.append(line)
                continue
            # If we hit regular content, stop skipping and include it
            skipping = False
            result.append(line)
            continue
        result.append(line)

    return '\n'.join(result)


def yaml_quote(val):
    """Quote YAML scalar value if it contains special characters."""
    if any(c in val for c in (':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`')):
        return repr(val)
    return val

def build_tom_tat_yaml(rows):
    """Build the YAML string for tom_tat_nhanh from list of (label, value) tuples."""
    lines = ["tom_tat_nhanh:"]
    for label, value in rows:
        lines.append(f"  - label: {yaml_quote(label)}")
        lines.append(f"    value: {yaml_quote(value)}")
    return '\n'.join(lines)


def insert_tom_tat_in_frontmatter(frontmatter_text, tom_tat_yaml):
    """Insert tom_tat_nhanh YAML into the frontmatter text (without the --- delimiters).
    If tom_tat_nhanh already exists, replace it. Otherwise insert before ai_summary."""
    lines = frontmatter_text.split('\n')
    
    # Check if tom_tat_nhanh already exists
    ttn_start = None
    ttn_end = None
    for i, line in enumerate(lines):
        if line.strip() == 'tom_tat_nhanh:':
            ttn_start = i
            # Find the end of the tom_tat_nhanh block (next top-level key)
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('- '):
                    ttn_end = j
                    break
            if ttn_end is None:
                ttn_end = len(lines)
            break
    
    if ttn_start is not None:
        # Replace existing tom_tat_nhanh block
        new_lines = lines[:ttn_start] + [tom_tat_yaml] + lines[ttn_end:]
        return '\n'.join(new_lines)
    
    # Find ai_summary position for insertion
    insert_pos = len(lines)
    # Check for empty trailing lines
    while insert_pos > 0 and lines[insert_pos - 1].strip() == '':
        insert_pos -= 1
    
    for i, line in enumerate(lines):
        if line.strip() == 'ai_summary:':
            insert_pos = i
            break
    
    new_lines = lines[:insert_pos] + [tom_tat_yaml] + lines[insert_pos:]
    return '\n'.join(new_lines)


def process_file(filepath):
    """Process a single file."""
    filename = filepath.name
    print(f"\n=== {filename} ===")
    
    content = filepath.read_text(encoding='utf-8')
    
    # Split frontmatter and body
    if not content.startswith('---'):
        print("  ERROR: File does not start with ---")
        return
    
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        print("  ERROR: Could not split frontmatter")
        return
    
    frontmatter = parts[1]
    body = parts[2]
    
    has_table = filename in WITH_TABLE_FILES
    
    if has_table:
        if filename in USE_CUSTOM_FOR_TABLE:
            body = remove_table_from_body(body)
            tom_tat_data = CUSTOM_TOM_TAT_NHANH[filename]
            print(f"  Using custom data (table removed) ({len(tom_tat_data)} items)")
        elif filename == "wwdc26-da-qua-nhan-dinh-sau-su-kien-ve-siri-ai-ios-27-va-nhung-gi-apple-chua-noi.md":
            # WWDC26 has a 3-column comparison table, not label/value
            body = remove_table_from_body(body)
            tom_tat_data = WWDC26_DA_QUA_TOM_TAT
            print(f"  Using WWDC26 special data ({len(tom_tat_data)} items)")
        else:
            # Parse table from body
            rows = parse_table_rows_from_body(body)
            if rows:
                tom_tat_data = rows
                body = remove_table_from_body(body)
                print(f"  Parsed {len(rows)} rows from table:")
                for label, value in rows:
                    print(f"    {label}: {value[:60]}...")
            else:
                # Fallback: check if there are known tables for this file
                print(f"  WARNING: Could not parse table rows, skipping")
                return
    else:
        if filename not in CUSTOM_TOM_TAT_NHANH:
            print(f"  WARNING: No custom data defined, skipping")
            return
        tom_tat_data = CUSTOM_TOM_TAT_NHANH[filename]
        print(f"  Using custom data ({len(tom_tat_data)} items)")
    
    # Build tom_tat_nhanh YAML
    tom_tat_yaml = build_tom_tat_yaml(tom_tat_data)
    
    # Insert into frontmatter
    new_frontmatter = insert_tom_tat_in_frontmatter(frontmatter, tom_tat_yaml)
    
    # Reconstruct file
    new_content = '---\n' + new_frontmatter + '---\n' + body.lstrip('\n')
    
    # Clean up excessive blank lines
    new_content = re.sub(r'\n{4,}', '\n\n\n', new_content)
    
    filepath.write_text(new_content, encoding='utf-8')
    print(f"  ✓ Done")


def main():
    files = sorted(POSTS_DIR.glob('*.md'))
    processed = 0
    for filepath in files:
        if filepath.name.startswith('_'):
            continue
        process_file(filepath)
        processed += 1
    
    print(f"\n\n===== SUMMARY =====")
    print(f"Files processed: {processed}")

if __name__ == '__main__':
    main()
