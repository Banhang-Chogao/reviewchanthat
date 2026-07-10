+++
author = "Minh Hoàng"
avatar = "https://api.dicebear.com/9.x/avataaars/svg?seed=MinhHoang"
categories = ["cong-nghe"]
date = "2026-07-08T13:40:00+07:00"
description = "Hướng dẫn chuẩn bị Mac trước khi cài macOS 27: Time Machine, dọn SSD,   kiểm tra app, RAM và kế hoạch rollback."
draft = false
image = "images/posts/chuan-bi-macbook-truoc-khi-len-macos-27.webp"
image_attribution_checked_at = "2026-07-10T18:56:35+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Field Engineer"
image_creator_id = "147254"
image_creator_url = "https://www.pexels.com/@field-engineer-147254"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/silver-macbook-on-brown-wooden-table-442150/"
seo_title = "Chuẩn bị MacBook trước khi lên macOS 27: dọn ổ, backup và"
series = "macos-27-co-gi-moi"
series_order = 9
series_title = "macOS 27 có gì mới"
slug = "chuan-bi-macbook-truoc-khi-len-macos-27"
tags = ["macOS 27", "chuẩn bị Mac", "backup Mac", "Time Machine", "nâng cấp macOS"]
thumbnail = "images/posts/chuan-bi-macbook-truoc-khi-len-macos-27.webp"
title = "Chuẩn bị MacBook trước khi lên macOS 27: dọn ổ, backup và kiểm tra app"
date_display = "08-07-2026 13:40:00 GMT +7"

[ai_summary]
collapsed = false
enabled = true
items = ["Backup Time Machine hoặc clone SSD là bước bắt buộc trước macOS 27 beta hoặc public release ngày đầu.", "Giải phóng 25–35GB SSD; beta và index Spotlight AI cần không gian tạm lớn.", "Kiểm tra app công việc, plugin và license trên trang nhà phát triển trước khi nâng cấp.", "Lập kế hoạch rollback: biết cách khôi phục từ backup nếu beta làm máy không boot được."]
title = "Tóm tắt bài viết"

[[tom_tat_nhanh]]
label = "Chủ đề"
value = "Chuẩn bị trước khi lên macOS 27"

[[tom_tat_nhanh]]
label = "Bắt buộc"
value = "Backup Time Machine hoặc clone"

[[tom_tat_nhanh]]
label = "Dung lượng"
value = "Trống ít nhất 25–35GB cho beta"

[[tom_tat_nhanh]]
label = "Hợp với"
value = "Ai sắp cài beta hoặc public release"
+++

Nâng cấp macOS mà không backup giống **đi du lịch không mang ví** — may mắn thì không sao, xui thì mất vài ngày làm lại máy. Golden Gate 27 còn thêm indexing Spotlight AI và dung lượng beta lớn — chuẩn bị trước sẽ tiết kiệm giờ (và nước mắt).

> Tại thời điểm viết (tháng 7/2026), Apple đã preview **macOS Golden Gate 27** tại WWDC26 (8/6/2026); public beta dự kiến tháng 7/2026 và bản chính thức mùa thu. Bài viết phân loại rõ thông tin Apple đã công bố, phản hồi beta và tin đồn; sẽ được cập nhật khi có thông tin chính thức bổ sung.

## Trước khi làm gì — xác nhận máy được hỗ trợ

[Kiểm tra danh sách tương thích](/posts/macos-27-ho-tro-may-mac-nao/). Mac Intel không có trong list chính thức — bài chuẩn bị này dành cho **Apple Silicon** sắp lên 27.

## Bước 1: Backup — không tùy chọn

**[phân tích]** Cách đáng tin nhất:

### Time Machine
- Ổ ngoài APFS/Mac OS Extended, dung lượng ≥ 2× data máy
- Backup full trước khi cài beta/stable ngày đầu
- Kiểm tra restore thử **một file** để chắc backup không hỏng

### Clone SSD (tùy chọn)
- Carbon Copy Cloner / SuperDuper — bootable backup
- Hữu ích rollback nhanh hơn Time Machine một số trường hợp

### Cloud
- iCloud Drive, Google Drive cho document quan trọng — **không** thay Time Machine cho system restore

## Bước 2: Giải phóng dung lượng

| Loại cài | Dung lượng trống khuyến nghị |
|---|---|
| Public beta | ≥ 25 GB |
| Developer beta | ≥ 35 GB |
| Stable ngày đầu | ≥ 20 GB |

**Dọn:**
- `About This Mac → Storage → Manage`
- Xóa Xcode Derived Data (dev có thể 20–50GB)
- Photos “Optimize Mac Storage” nếu library lớn
- Gỡ app không dùng

Beta + Spotlight reindex ăn **tạm** thêm 5–15GB.

## Bước 3: Cập nhật app và plugin

Mở từng app công việc → Check for Updates. Ghi lại:

- Microsoft Office / 365
- Adobe Creative Cloud
- Zoom, Teams, Slack
- VPN công ty
- Plugin âm thanh (UAD, Waves)

Nếu nhà phát triển chưa xác nhận macOS 27 — **hoãn** nâng cấp. Xem [workflow theo nghề](/posts/macos-27-cho-van-phong-creator-lap-trinh-vien/).

## Bước 4: Ghi lại cấu hình quan trọng

- Danh sách app đăng nhập (1Password export, license key)
- Wi‑Fi enterprise profile
- Printer scanner driver
- `/etc/hosts`, `~/.zshrc`, SSH keys — dev backup riêng

## Bước 5: Pin và nguồn

Cài update lớn **cắm sạc**, không dựa pin. MacBook đóng nắp không sleep giữa chừng (Settings → Energy).

## Bước 6: Thời điểm cài

**[phân tích]**

- Cuối tuần hoặc ngày nghỉ — rollback mất vài giờ
- Tránh trước deadline, họp ký, go-live
- Stable: chờ 1–2 tuần sau release nếu không cần ngày một — [checklist](/posts/macos-27-co-nen-nang-cap-ngay-khong/)

## Bước 7: Sau khi cài xong

1. Để máy **index Spotlight** 30–60 phút cắm nguồn
2. Mở app công việc lần lượt — đừng làm việc ngay
3. Kiểm tra pin, fan, Wi‑Fi 24h đầu
4. Nếu beta: góp feedback Apple, không dùng máy chính

## Bước 8: Kế hoạch rollback

Biết trước:

- Recovery (⌘R khi boot) → Restore Time Machine
- Hoặc giữ **bootable clone** macOS 26

Đọc [rủi ro beta](/posts/macos-27-beta-co-nen-cai-khong/) nếu cài sớm.

## Checklist một trang (in ra hoặc note)

- [ ] Time Machine backup xong
- [ ] Trống ≥ 25GB SSD
- [ ] Model trong list [tương thích](/posts/macos-27-ho-tro-may-mac-nao/)
- [ ] App công việc OK
- [ ] License / password export
- [ ] Cắm sạc khi cài
- [ ] Biết cách Recovery restore
- [ ] Đã đọc [tổng quan 27](/posts/macos-27-co-gi-moi/)


## File và thư mục nên dọn trước update

- `~/Library/Caches` — xóa cache app (không xóa bừa `Application Support`)
- Downloads cũ > 1 năm
- DMG installer app đã cài
- iOS device backup cũ trong Finder nếu không cần
- Mail attachment local nếu dùng IMAP và đã sync cloud

**Cảnh báo:** Không xóa `~/Library/Application Support` của app đang dùng — mất license hoặc database.

## Kiểm tra sức khỏe phần cứng trước OS mới

1. **Disk Utility → First Aid** trên internal disk
2. **Battery cycle count** — About This Mac → System Report → Power (MacBook)
3. **SMART status** ổ ngoài backup — tránh restore từ ổ sắp hỏng
4. Nếu máy đã **kernel panic** trên 26 — fix hardware hoặc clean install 26 trước khi 27

## Tài khoản và đăng nhập

- Đăng xuất Apple ID trên máy **bán/cho** trước khi ai đó nâng cấp 27
- Bật **Two-Factor** — restore iCloud sau reinstall cần thiết bị tin cậy
- Ghi lại **FileVault recovery key** — update lớn đôi khi kích hoạt lại encryption check

## Mạng và proxy doanh nghiệp

Nếu công ty dùng **proxy SSL inspect**, beta có thể không trust certificate cũ — liên hệ IT trước update. Đừng tự beta trên laptop có VPN bắt buộc compliance.

## Sau stable release — “ngày vàng” nên cài

**[phân tích]** Tránh:

- Ngày Apple Event (server CDN chậm)
- Đêm không ngủ để cài — máy lỗi giữa đêm không có support

Nên:

- Sáng cuối tuần, cắm mạng ổn định, có 2–3 giờ dự phòng
- Đọc **r/macOS** hoặc forum VN 24h đầu xem bug phổ biến model của bạn

## Liên kết nhanh series

Sau chuẩn bị xong, quyết định cuối cùng nằm ở checklist nâng cấp và (nếu thử sớm) bài beta — ba bài tạo thành “bộ tam” trước mọi lần bấm Software Update.

## Phụ kiện và ngoại vi

Trước update lớn, kiểm tra driver cho **máy in**, **scanner**, **audio interface**, **dock Thunderbolt**. macOS 27 beta đôi khi reset permission Privacy — bạn sẽ phải cấp lại quyền mic/camera cho Zoom, OBS, DAW. Dành 15 phút sau cài để bật lại từng app, tránh họp sáng hôm sau mic câm.

## Kết luận

Chuẩn bị không sexy nhưng quyết định **có mất dữ liệu hay không**. Làm đủ 8 bước trên, bạn có thể thử beta hoặc lên stable với rủi ro thấp. Tiếp theo: [có nên nâng cấp](/posts/macos-27-co-nen-nang-cap-ngay-khong/) hoặc [cài beta](/posts/macos-27-beta-co-nen-cai-khong/).