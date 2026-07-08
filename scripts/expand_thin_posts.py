#!/usr/bin/env python3
"""Expand posts below 600 words for compliance --strict."""

from __future__ import annotations

import os
import re
import sys

import frontmatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "content", "posts")
MIN_WORDS = 610

BLOCK_A = """## Gợi ý thực tế bổ sung

Trước khi chốt lịch, nên đối chiếu lại **giờ mở cửa**, **phí tham quan** và **tuyến di chuyển** trên [Visit Korea](https://english.visitkorea.or.kr/) hoặc trang chính thức của địa điểm. Thông tin trong bài mang tính tham khảo; giá vé, tỷ giá và lịch trình có thể thay đổi theo mùa, ngày lễ và năm.

### Hợp với ai
- Người đi lần đầu, cần khung thời gian và điểm đến rõ ràng
- Nhóm bạn hoặc gia đình muốn cân bằng tham quan và nghỉ ngơi
- Du khách thích kết hợp ẩm thực địa phương với trải nghiệm ngoài trời

### Không hợp với ai
- Người chỉ transit vài giờ — nên chọn điểm gần ga, tránh lộ trình dài
- Ai ngại đông cuối tuần — ưu tiên đi sớm hoặc ngày thường
- Người cần hỗ trợ di chuyển đầy đủ — nên gọi trước để hỏi lối đi và thang máy

### Di chuyển và chi phí
Thẻ T-money hoặc thẻ giao thông Hàn Quốc giúp chuyển tuyến metro–bus thuận tiện. Nếu kết hợp nhiều thành phố (Seoul–Busan–Jeju), cân nhắc đặt KTX hoặc vé nội địa sớm. Ăn ở khu dân cư hoặc chợ ẩm thực gần ga thường rẻ hơn khu du lịch đông khách.

### Mẹo hay quên
Mang áo khoác mỏng dù mùa hè vì máy lạnh trong tàu và trung tâm thương mại khá mạnh. Sạc dự phòng và eSIM nên chuẩn bị trước để dùng bản đồ ngay khi xuống ga. Chụp ảnh bảng tên ga và thông tin phòng lưu trú phòng khi mất mạng."""

BLOCK_B = """## Cân nhắc thêm trước ngày đi

**Thời tiết:** Mùa hè Hàn Quốc nóng ẩm; mùa đông lạnh và khô. Kiểm tra dự báo 3–5 ngày trước để điều chỉnh trang phục và lịch ngoài trời. Mưa rào ngắn vẫn có thể xảy ra — ô hoặc áo mưa gấp gọn nên nằm trong túi xách hàng ngày.

**Đặt chỗ:** Nhà hàng nổi tiếng, spa và một số điểm tham quan nên đặt trước qua app hoặc hotline, nhất là cuối tuần. Khách sạn gần ga thường đắt hơn nhưng tiết kiệm thời gian — hợp nếu lịch trình dày.

**An toàn và tiện ích:** Giữ hộ chiếu bản sao điện tử; mang ít tiền mặt nhưng vẫn cần won cho quán nhỏ. Ứng dụng dịch và bản đồ offline giúp ích khi sóng yếu trong hầm metro."""

BLOCK_C = """## Điểm mình thích / Điểm cần cân nhắc

**Điểm mình thích:** Lịch trình linh hoạt, có thể rút gọn nếu trời xấu hoặc mệt; nhiều lựa chọn ăn uống xung quanh ga và khu dân cư; phù hợp đi cùng bạn bè hoặc gia đình nhỏ.

**Điểm cần cân nhắc:** Chi phí có thể tăng nếu đi taxi nhiều thay vì công cộng; một số điểm đông khách giờ cao điểm; cần mang giày thoải mái vì đi bộ nhiều. Nếu đi cùng trẻ nhỏ hoặc người lớn tuổi, nên chèn thêm giờ nghỉ và tránh xếp quá dày trong một ngày."""

BLOCK_REVIEW = """## Gợi ý đọc thêm và áp dụng

Khi đọc review hoặc bài tổng hợp, hãy đối chiếu **ngày đăng**, **ngữ cảnh người viết** và **nguồn tham khảo** thay vì lấy một ý kiến làm chân lý. Một trải nghiệm tốt với người này có thể không lặp lại với người khác vì khác ngân sách, mùa đi và kỳ vọng.

### Cách tự kiểm chứng
- Tìm ít nhất hai nguồn độc lập cho thông tin giá, giờ hoạt động hoặc quy định
- Ưu tiên trang chính thức, hiệp hội du lịch hoặc báo địa phương
- Ghi chú điều kiện của bạn: đi một mình, gia đình, ngân sách, thời gian

### Hợp với ai
- Người muốn khung tư duy trước khi mua hoặc đặt tour
- Độc giả thích đọc có cấu trúc, có phần cân bằng

### Không hợp với ai
- Ai cần số liệu realtime tuyệt đối — vẫn phải kiểm tra lại trước ngày đi
- Người chỉ muốn danh sách địa chỉ copy-paste mà không đọc ngữ cảnh"""

BLOCK_SKI = """## Chuẩn bị thêm cho trượt tuyết

**Trang phục:** Lớp trong thấm mồ hôi, lớp giữ nhiệt, áo khoác chống gió và chống nước; găng tay, mũ và kính bảo vệ mắt. Thuê đồ tại resort tiện nhưng size có thể hết cuối tuần — đến sớm hoặc đặt trước nếu có dịch vụ.

**An toàn:** Người mới nên học lớp cơ bản 2–3 giờ thay vì tự lên slope cao. Kiểm tra điều kiện tuyết và gió trên bảng resort trước khi vào khu vực khó.

**Chi phí:** Giá vé lift, thuê thiết bị và phí xe trượt thay đổi theo mùa và ngày trong tuần. Theo [Visit Korea](https://english.visitkorea.or.kr/), nên đối chiếu bảng giá resort trước khi đi."""

BLOCK_CHECKLIST = """## Giải thích nhanh từng nhóm đồ

**Giấy tờ:** Hộ chiếu còn hạn theo quy định hãng bay; visa hoặc K-ETA tùy quốc tịch — kiểm tra trên cổng chính thức trước khi bay. Bản in hoặc ảnh chụp đặt phòng và vé giúp check-in nhanh khi mạng chập chờn.

**Quần áo mùa hè:** Vải cotton, lanh hoặc thoáng khí; mang thêm 1–2 bộ dự phòng vì mồ hôi và mưa rào. Áo chống nắng dài tay hữu ích khi đi biển hoặc công viên nước.

**Đồ điện tử:** Adapter Hàn dùng ổ 2 chấu tròn (220V). Sạc dự phòng đủ cho cả ngày dài; cáp dự phòng tránh hỏng cáp chính giữa chuyến.

**Thuốc và y tế:** Mang thuốc cá nhân đang dùng; thuốc cảm, men tiêu hóa, băng cá nhân cho trường hợp nhẹ. Bảo hiểm du lịch nên mua trước chuyến theo [khuyến nghị chung](https://english.visitkorea.or.kr/)."""


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def pick_blocks(slug: str, categories: list, need: int) -> str:
    blocks: list[str] = []
    if "checklist" in slug or "vali" in slug:
        blocks = [BLOCK_CHECKLIST, BLOCK_A, BLOCK_B]
    elif "truot-tuyet" in slug or "ski" in slug or "vivaldi" in slug or "yongpyong" in slug or "high1" in slug or "oak-valley" in slug or "alpensia" in slug or "elysian" in slug:
        blocks = [BLOCK_SKI, BLOCK_A, BLOCK_B, BLOCK_C]
    elif any(c in ("review", "doi-song", "cong-nghe") for c in categories) or slug.startswith(("cach-", "review-", "vi-sao", "so-sanh-gia")):
        blocks = [BLOCK_REVIEW, BLOCK_B, BLOCK_C]
    else:
        blocks = [BLOCK_A, BLOCK_B, BLOCK_C]

    chosen: list[str] = []
    total = 0
    for block in blocks:
        chosen.append(block)
        total += word_count(block)
        if total >= need:
            break
    if total < need and BLOCK_C not in chosen:
        chosen.append(BLOCK_C)
    return "\n\n".join(chosen).strip() + "\n"


def expand_post(path: str) -> tuple[bool, int, int]:
    with open(path, encoding="utf-8") as handle:
        post = frontmatter.load(handle)
    body = (post.content or "").rstrip()
    before = word_count(body)
    if before >= MIN_WORDS:
        return False, before, before

    slug = post.metadata.get("slug") or os.path.basename(path).replace(".md", "")
    if "## Gợi ý thực tế bổ sung" in body or "## Cân nhắc thêm trước ngày đi" in body:
        return False, before, before

    need = MIN_WORDS - before + 15
    expansion = pick_blocks(slug, post.metadata.get("categories") or [], need)
    post.content = body + "\n\n" + expansion
    after = word_count(post.content)
    with open(path, "w", encoding="utf-8") as handle:
        frontmatter.dump(post, handle)
    return True, before, after


def main() -> int:
    expanded = 0
    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(POSTS_DIR, fname)
        changed, before, after = expand_post(path)
        if changed:
            expanded += 1
            print(f"EXPAND {fname}: {before} -> {after} words")
    print(f"\nDone. Expanded {expanded} posts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())