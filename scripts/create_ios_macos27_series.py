#!/usr/bin/env python3
"""Create iOS 27 and macOS 27 content series (18 posts)."""

import hashlib
import json
import os
import re
import textwrap

import frontmatter

ROOT = os.path.dirname(os.path.dirname(__file__))
POSTS_DIR = os.path.join(ROOT, "content", "posts")
SERIES_JSON = os.path.join(ROOT, "data", "series.json")
MANIFEST_JSON = os.path.join(ROOT, "data", "images.json")
DATE_BASE = "2026-07-08"
AUTHOR = "Minh Hoàng"
AVATAR = "https://api.dicebear.com/9.x/avataaars/svg?seed=MinhHoang"
DISCLAIMER = (
    "Tại thời điểm viết (tháng 7/2026), Apple đã preview iOS 27 và macOS Golden Gate 27 "
    "tại WWDC26; bản public release dự kiến mùa thu. Bài viết sẽ được cập nhật khi có "
    "thông tin chính thức bổ sung."
)

IOS_IMAGES = {
    "ios-27-co-gi-moi": ("48605", "white-apple-iphone-on-wooden-table-48605"),
    "ios-27-ho-tro-iphone-nao": ("18311094", "apple-smartphone-iphone-14-on-the-palmrest-of-macbook-pro-laptop-18311094"),
    "ios-27-apple-intelligence-iphone-cu": ("19060767", "close-up-of-a-person-holding-an-iphone-15-pro-19060767"),
    "ios-27-cai-thien-pin-iphone": ("8052289", "man-in-blue-shirt-holding-iphone-8052289"),
    "ios-27-camera-anh-video-iphone": ("26550485", "close-up-of-an-iphone-7-26550485"),
    "ios-27-co-nen-cap-nhat-ngay-khong": ("1092644", "black-iphone-4-on-white-book-1092644"),
    "ios-27-beta-co-nen-cai-khong": ("699122", "iphone-smartphone-desk-laptop-699122"),
    "ios-27-quyen-rieng-tu-iphone": ("788946", "iphone-ipad-laptop-788946"),
    "ios-27-so-voi-ios-26": ("6476589", "person-holding-black-iphone-6476589"),
}

MACOS_IMAGES = {
    "macos-27-co-gi-moi": ("92904", "macbook-pro-92904"),
    "macos-27-ho-tro-may-mac-nao": ("693859", "turned-on-macbook-pro-693859"),
    "macos-27-apple-intelligence-macbook": ("4974912", "person-coding-on-a-macbook-pro-4974912"),
    "macos-27-hieu-nang-pin-macbook": ("3888151", "workplace-with-modern-laptop-with-program-code-on-screen-3888151"),
    "macos-27-cho-van-phong-creator-lap-trinh-vien": ("574077", "person-using-macbook-pro-574077"),
    "macos-27-co-nen-nang-cap-ngay-khong": ("34803979", "modern-workspace-with-coding-laptop-and-coffee-34803979"),
    "macos-27-beta-co-nen-cai-khong": ("37085305", "macbook-pro-on-rooftop-with-code-editor-open-37085305"),
    "macos-27-so-voi-macos-26": ("18105", "macbook-on-table-18105"),
    "chuan-bi-macbook-truoc-khi-len-macos-27": ("39284", "macbook-air-on-desk-39284"),
}


def pexels_entry(slug, title, photo_id, slug_name):
    source_url = f"https://www.pexels.com/photo/{slug_name}/"
    direct_url = (
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg"
        f"?auto=compress&cs=tinysrgb&w=1920"
    )
    image_id = f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}"
    return {
        "slug": slug,
        "title": title,
        "image_id": image_id,
        "source_platform": "Pexels",
        "source_url": source_url,
        "direct_url": direct_url,
        "creator": "",
        "creator_url": "",
        "license": "Pexels License",
        "commercial_use": True,
        "local_source_path": f"static/images/posts-src/{slug}.jpg",
        "output_path": f"static/images/posts/{slug}.webp",
        "watermark_text": "Source: Pexels",
        "provider_used": "manual-curate",
    }


def link(slug, text):
    return f"[{text}](/posts/{slug}/)"


def make_ai_summary(items):
    return {
        "enabled": True,
        "title": "Tóm tắt bài viết",
        "collapsed": False,
        "items": items,
    }


def make_post(meta, body):
    post = frontmatter.Post(body.strip() + "\n")
    post.metadata = meta
    return post


IOS_POSTS = [
    {
        "slug": "ios-27-co-gi-moi",
        "title": "iOS 27 có gì mới? Những thay đổi đáng chờ nhất cho iPhone",
        "description": "Tổng quan iOS 27 sau WWDC26: Siri AI, Apple Intelligence, hiệu năng, quyền riêng tư và timeline beta/public cho người dùng iPhone tại Việt Nam.",
        "series_order": 1,
        "hour": 8,
        "tags": ["iOS 27", "iOS 27 có gì mới", "Siri AI", "Apple Intelligence", "iPhone", "WWDC26"],
        "tom_tat": [
            ("Chủ đề", "Tổng quan iOS 27 cho iPhone"),
            ("Ra mắt", "Preview WWDC26, public mùa thu 2026"),
            ("Điểm nổi bật", "Siri AI, AI Photos, hiệu năng, an toàn trẻ em"),
            ("Hợp với", "Người dùng iPhone muốn biết có nên nâng cấp"),
        ],
        "ai": [
            "Apple đã preview iOS 27 tại WWDC26 (8/6/2026) với Siri AI, Apple Intelligence thế hệ mới và cải thiện hiệu năng hệ thống.",
            "Theo trang chính thức Apple, app mở nhanh hơn tới 30%, ảnh mới load nhanh hơn tới 70% và AirDrop nhanh hơn tới 80%.",
            "iOS 27 hỗ trợ từ iPhone 11 trở lên; Apple Intelligence yêu cầu iPhone 16 trở lên hoặc iPhone 15 Pro/Pro Max.",
            "Public beta dự kiến tháng 7/2026, bản chính thức mùa thu; người dùng Việt Nam có tiếng Việt trong danh sách ngôn ngữ Apple Intelligence.",
        ],
        "body": """
Mỗi năm, câu hỏi lặp lại trên group iPhone Việt Nam vẫn giống nhau: **có đáng lên iOS mới không, hay cứ ở bản cũ cho yên ổn?** Sau WWDC26, Apple đã trả lời phần nào bằng iOS 27 — nhưng câu trả lời không đơn giản là “có” hay “không” cho tất cả mọi người.

Theo [Apple Newsroom](https://www.apple.com/newsroom/2026/06/apple-unveils-next-generation-of-apple-intelligence-siri-ai-and-more/), iOS 27 tập trung vào ba trụ cột: **Siri AI**, **Apple Intelligence thế hệ mới** và **cải thiện hiệu năng/thiết kế Liquid Glass**. Đây không phải bản cập nhật “vá lỗi nhẹ” — mà là lần Apple cố gắng chứng minh AI trên thiết bị vẫn có lợi thế so với chatbot web.

> {disclaimer}

## Bảng tóm tắt nhanh

| Hạng mục | Thông tin chính thức / đáng tin |
|---|---|
| Sự kiện | WWDC26, 8/6/2026 |
| Tên hệ điều hành | iOS 27 |
| Beta developer | Có từ 8/6/2026 |
| Public beta | Apple nói “next month” (khoảng tháng 7/2026) |
| Bản chính thức | “This fall” (mùa thu 2026) |
| iPhone hỗ trợ | iPhone 11 trở lên (theo [apple.com/os/ios](https://www.apple.com/os/ios/)) |
| Apple Intelligence | iPhone 16 trở lên + iPhone 15 Pro/Pro Max |

## 1. Siri AI — thay đổi lớn nhất cho người dùng phổ thông

Siri từng bị chê vì hiểu câu hỏi kém và không “nhớ” ngữ cảnh. **Siri AI** (theo Apple) là phiên bản mới với khả năng:

- Hiểu nội dung trên màn hình
- Tìm kiếm xuyên Messages, Mail, Photos
- Trả lời dựa trên kiến thức web cập nhật
- Có app Siri riêng, đồng bộ lịch sử qua iCloud

Với người dùng Việt Nam, điểm cần theo dõi là **mức hỗ trợ tiếng Việt thực tế** khi public release. Apple liệt kê tiếng Việt trong nhóm ngôn ngữ Apple Intelligence, nhưng một số tính năng (như Suggestions trong Messages) vẫn ghi “Coming in English” trên trang sản phẩm.

## 2. Apple Intelligence thế hệ mới

Apple nhấn mạnh AI đi sâu vào app hệ thống thay vì chỉ là widget rời rạc:

| Ứng dụng | Tính năng Apple đã preview |
|---|---|
| Photos | Spatial Reframing, Clean Up nâng cấp, Extend |
| Messages/Mail | Gợi ý hành động một chạm (Coming in English) |
| Safari | Nhóm tab theo chủ đề, Notify Me theo dõi thay đổi trang |
| Image Playground | Thêm style photorealistic |
| Passwords | Tự sửa mật khẩu yếu/lộ |

Nếu bạn từng thử Apple Intelligence đợt đầu mà thấy “có nhưng không dùng hàng ngày”, iOS 27 là lần Apple cố gắng biến AI thành thói quen — ít nhất trên máy đủ điều kiện.

## 3. Camera và Visual Intelligence

Apple preview **Siri mode in Camera**: nhận diện vật thể, landmark, thông tin dinh dưỡng ngay từ viewfinder. Đây là hướng đi hợp lý cho người hay du lịch hoặc chụp đồ ăn, nhưng hiệu năng thực tế trên iPhone cũ hơn 15 Pro vẫn cần chờ beta/public để đánh giá.

## 4. An toàn trẻ em và Screen Time

iOS 27 mở rộng parental controls: Setup Assistant chọn app cho trẻ, Ask to Browse, Communication Safety chặn cả nội dung bạo lực, Time Allowances theo nhóm app. Với phụ huynh Việt Nam cho con dùng iPhone/iPad, đây có thể là lý do nâng cấp thực tế hơn AI.

## 5. Hiệu năng và Liquid Glass

Theo Apple, iOS 27 cải thiện:

- Mở app nhanh hơn tới **30%**
- Ảnh mới trong Photos load nhanh hơn tới **70%**
- AirDrop nhanh hơn tới **80%**
- Chuyển mạng Wi‑Fi/cellular mượt hơn

Liquid Glass có slider tùy chỉnh từ ultraclear đến fully tinted — hữu ích nếu bạn hay đọc ngoài trời hoặc không thích hiệu ứng kính quá trong suốt.

## 6. iPhone nào được hỗ trợ?

Theo trang chính thức, iOS 27 tương thích **từ iPhone 11 đến iPhone 17 series** (và iPhone SE thế hệ 2 trở lên). Tuy nhiên, **Apple Intelligence** yêu cầu phần cứng mạnh hơn — chi tiết trong bài {link_compat}.

## 7. Timeline: khi nào có bản ổn định?

| Mốc | Dự kiến |
|---|---|
| Developer beta | Từ 8/6/2026 |
| Public beta | Tháng 7/2026 (theo Apple) |
| GM / public release | Mùa thu 2026, cùng iPhone mới |

Nếu bạn dùng iPhone làm máy chính, **không nên cài beta sớm** trừ khi đã backup và chấp nhận lỗi app/ngân hàng. Xem checklist tại {link_update} và {link_beta}.

## Ai nên nâng cấp iOS 27?

**Nên (khi bản chính thức ổn định):**
- iPhone 16/17 series muốn tận dụng Siri AI và Apple Intelligence
- Phụ huynh cần parental controls mới
- Người hay chỉnh ảnh, dùng AirDrop, cần hiệu năng hệ thống

**Cân nhắc hoặc chờ:**
- iPhone 11–14 chỉ cần bảo mật, không cần AI
- Máy pin yếu, storage gần đầy
- App ngân hàng/công việc chưa tương thích beta

## Kết luận

iOS 27 là bản cập nhật “đặt cược AI” của Apple sau một năm Apple Intelligence chưa thuyết phục hết. Với người dùng Việt Nam, giá trị thực sẽ phụ thuộc **mức hỗ trợ tiếng Việt** và **danh sách máy đủ chip Neural Engine**. Hãy theo dõi public beta tháng 7, đọc thêm {link_ai}, {link_pin}, {link_camera} trong series này trước khi bấm Update.
""",
    },
    # Additional posts will be in the script - truncated for file size, I'll continue in the write
]