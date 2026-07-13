+++
draft = false
title = "Dọn Mac đúng cách: tối ưu dung lượng và hiệu năng mà không cần cài lại macOS"
seo_title = "Dọn Mac đúng cách: tối ưu dung lượng và tăng tốc MacBook"
description = "Cách dọn Mac sạch — giải phóng bộ nhớ, tối ưu macOS, tăng tốc MacBook không cần cài lại. Hướng dẫn chi tiết cho người Việt dùng Mac."
date = "2026-07-10T18:57:10+07:00"
commit = "f45b70cd"
lastmod = "2026-07-10T18:57:10+07:00"
date_display = "10-07-2026 18:57:10 GMT +7"
lastmod_display = "10-07-2026 18:57:10 GMT +7"
authors = ["Minh Hoàng"]
categories = ["doi-song"]
tags = ["dọn Mac", "tối ưu macOS", "Mac storage", "giải phóng bộ nhớ Mac", "tăng tốc MacBook", "series cuộc sống số"]
series = "cuoc-song-so"
series_order = 9
series_title = "Cuộc sống số"
slug = "don-mac-dung-cach-toi-uu-dung-luong-va-hieu-nang-ma-khong-can-cai-lai-macos"
image = "images/posts/don-mac-dung-cach-toi-uu-dung-luong-va-hieu-nang-ma-khong-can-cai-lai-macos.webp"
thumbnail = "images/posts/don-mac-dung-cach-toi-uu-dung-luong-va-hieu-nang-ma-khong-can-cai-lai-macos.webp"
image_alt = "Ảnh minh họa Dọn Mac đúng cách: tối ưu dung lượng và hiệu năng mà không cần cài lại macOS — nguồn Pixabay"
image_source = "Pixabay"
image_source_url = "https://pixabay.com/photos/windmills-consuegra-toledo-spain-4278679/"
image_license = "Pixabay Content License"
image_commercial_use = true
image_owner = "external"
image_creator = "javierAlamo"
image_creator_url = "https://pixabay.com/photos/windmills-consuegra-toledo-spain-4278679/"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pixabay_api"
image_license_url = ""
image_status = "verified"
image_provider = "pixabay"

[ai_summary]
collapsed = false
enabled = true
title = "Tóm tắt bài viết"
items = ["Mac đầy bộ nhớ là vấn đề phổ biến — file rác trong ~/Library/Caches, Trash chưa dọn, iOS backups cũ, ngôn ngữ không dùng và cache từ app là những thủ phạm chính.", "7 bước dọn Mac: dọn Trash + Downloads, tối ưu iCloud, xóa cache và temp files, dọn language files, gỡ app bằng AppCleaner, xóa iOS backups cũ + Mail Downloads, dọn Desktop.", "Bảng so sánh 5 công cụ dọn Mac: CleanMyMac X ($35/năm), DaisyDisk ($9.99), AppCleaner (miễn phí), Onyx (miễn phí), GrandPerspective (miễn phí) — kèm đánh giá chi tiết.", "Tips thực hành: giới hạn Desktop tối đa 10 file, dùng Terminal để chạy bảo trì macOS (periodic daily weekly monthly), tắt app tự khởi động cùng Mac để tăng tốc boot.", "Bài này là bài thứ 9 và cũng là bài cuối của series Cuộc sống số — tổng kết hành trình số gọn gàng từ thói quen đến vệ sinh thiết bị."]

[attribution]
copyright = "© 2026 Review Chân Thật. Bài viết tham khảo hướng dẫn từ Apple Support, MacPaw blog, cộng đồng r/Mac, và trải nghiệm thực tế khi dùng MacBook Pro M1 và MacBook Air M3."
source_note = "Tham khảo hướng dẫn 'Free up storage on Mac' từ Apple Support, bài viết của MacPaw về CleanMyMac, và thảo luận từ r/Mac về các công cụ bảo trì macOS."

[[faq]]
question = "Xóa cache trong ~/Library/Caches có an toàn không?"
answer = "Có, miễn là bạn chỉ xóa thư mục con bên trong thư mục Caches, không xóa thư mục Caches gốc. Cache là dữ liệu tạm mà app tự tạo ra để chạy nhanh hơn — xóa đi app sẽ tự tạo lại khi cần. Tuy nhiên, sau khi xóa cache, lần đầu mở app sẽ chậm hơn một chút. Tuyệt đối không xóa thư mục Caches của các app quan trọng (Photos, Mail, Safari) nếu bạn không rành — vì có thể mất dữ liệu chưa sync."

[[faq]]
question = "CleanMyMac X có đáng tiền không?"
answer = "Với người không rành kỹ thuật và muốn dọn Mac bằng một nút bấm: có. CleanMyMac làm tốt việc dọn cache, tìm file rác, xóa app sạch sẽ và có tính năng Malware Removal. Các tính năng mạnh nhất: System Junk (dọn cache hệ thống), Large & Old Files (tìm file lớn), và Application Uninstaller (gỡ app sạch). Nếu bạn thoải mái dùng Terminal và dọn thủ công, bạn không cần CleanMyMac — nhưng nếu bạn muốn tiết kiệm thời gian và không muốn đụng đến dòng lệnh, $35/năm là hợp lý."

[[faq]]
question = "Tôi có Mac 256GB, nên dùng công cụ nào?"
answer = "Với 256GB, mỗi GB đều quý. Kết hợp: DaisyDisk ($9.99 mua một lần) để trực quan hóa ổ cứng — xem ngay thư mục/file nào đang ăn nhiều dung lượng nhất. AppCleaner (miễn phí) để gỡ app — không để sót file rác. GrandPerspective (miễn phí) là bản alternative cho DaisyDisk. Không cần CleanMyMac nếu bạn biết dọn thủ công."

[[faq]]
question = "Làm sao để xóa iOS backups cũ trên Mac?"
answer = "Mở Finder (không phải iTunes) → kết nối iPhone → tab Chung → Quản lý Backup → chọn bản backup cũ → Xóa. Nếu không kết nối iPhone, bạn có thể xóa thủ công qua Terminal: mở Finder → menu Go → Go to Folder → gõ ~/Library/Application Support/MobileSync/Backup/ — xóa thư mục backup cũ (mỗi backup khoảng 20–40GB tùy dung lượng iPhone). Luôn giữ bản backup mới nhất, xóa các bản còn lại."

[[faq]]
question = "Tại sao Desktop nhiều file làm Mac chậm?"
answer = "macOS render từng icon trên Desktop như một cửa sổ Finder riêng — mỗi icon là một process thumbnail nhỏ. Với 50–100 file trên Desktop, macOS phải duy trì hàng chục thumbnail cùng lúc, tiêu tốn CPU và RAM, đặc biệt là file ảnh/video lớn (vì macOS phải tạo preview). Desktop lý tưởng: dưới 10 file. Số còn lại nên cho vào thư mục Documents hoặc Downloads. Bạn vẫn có thể truy cập nhanh qua Finder sidebar hoặc Spotlight."

[[internal_links]]
ref = "posts/cuoc-song-so-nam-2026-30-thoi-quen-giup-ban-song-gon-gang-an-toan-va-hieu-qua-hon.md"
title = "Cuộc sống số năm 2026: 30 thói quen"

[[internal_links]]
ref = "posts/don-iphone-nhu-the-nao-de-may-luon-muot-va-con-nhieu-bo-nho.md"
title = "Dọn iPhone như thế nào để máy luôn mượt"
image_attribution_checked_at = "2026-07-12T08:49:00+07:00"
image_query = "dọn mac đúng cách tối"
+++

Bạn mở "About This Mac" → tab Storage — và con số hiện ra: **23GB còn trống trên 256GB**. Bạn tự hỏi: "Rõ ràng mình không lưu gì nhiều, sao ổ cứng đầy thế?"

Câu trả lời: macOS có một tài năng đặc biệt — **giấu rác rất tài tình**. File cache nằm sâu trong ~/Library, iOS backups cũ không ai nhớ, file ngôn ngữ 50MB cho 20 thứ tiếng bạn không bao giờ dùng, và hàng tá app cài từ thời đại học vẫn nằm đó.

Tin tốt: bạn không cần cài lại macOS để lấy lại 30–50GB. Chỉ cần dọn đúng cách.

---

## Kiểm tra dung lượng Mac

Trước khi bắt đầu, hãy xem xét tình hình:

1. Click logo Apple (góc trên bên trái) → About This Mac
2. Tab **Storage** — xem thanh màu phân bổ dung lượng
3. Chuột vào từng phần màu để xem chi tiết: Apps, Photos, Messages, System Data...

**Con số đáng chú ý nhất là System Data** (thường hiển thị màu xám) — đây là thùng rác chứa cache, temp files, iOS backups, log files, và đủ thứ linh tinh khác. Nếu System Data chiếm trên 50GB, bạn đang có vấn đề.

---

## 7 bước dọn Mac

### Bước 1: Dọn Thùng rác và Downloads (5 phút)

Nghe có vẻ cơ bản, nhưng bạn sẽ ngạc nhiên khi thấy bao nhiêu người bỏ qua bước này.

**Thùng rác (Trash):**
1. Click biểu tượng Trash trên Dock → giữ hoặc nhấp phải → **Empty Trash**
2. Hoặc: Finder → menu Finder → Empty Trash (hoặc Empty Trash Securely nếu có dữ liệu nhạy cảm)

**Downloads:**
1. Mở Finder → Downloads (hoặc Cmd + Shift + L)
2. Sắp xếp theo kích thước (View → Show View Options → Size)
3. Xóa file lớn không dùng: file DMG đã cài app, file ZIP đã giải nén, file PDF đã đọc xong, file ảnh đã chuyển đi
4. Giữ lại tối đa 10 file cần thiết

**Lượng giải phóng:** 2–10GB tùy vào độ "lười" dọn Downloads của bạn.

### Bước 2: Tối ưu iCloud (5 phút)

Giống iPhone, Mac cũng có tính năng tối ưu iCloud.

**Cách làm:**
1. System Settings → [Tên bạn] → iCloud
2. Click **iCloud Drive** → bật **Optimize Mac Storage**
3. Click **Photos** → bật **Optimize Mac Storage**

Khi bật:
- File và ảnh chỉ được giữ bản nén trên máy
- Bản gốc ở iCloud — tải về khi bạn mở
- Tiết kiệm 20–40GB tùy vào kích thước thư viện ảnh và iCloud Drive

**Quan trọng:** Cần có đủ dung lượng iCloud. Nếu gói iCloud 200GB hoặc 2TB của bạn đã gần đầy, tính năng này không có tác dụng — vì không còn chỗ trên cloud để chứa bản gốc.

### Bước 3: Xóa cache và temp files (15 phút)

Đây là bước mang lại kết quả lớn nhất — cache trên Mac có thể lên tới 20–30GB.

**Cache ứng dụng (~/Library/Caches):**
1. Mở Finder → menu Go → Go to Folder (hoặc Cmd + Shift + G)
2. Gõ: `~/Library/Caches`
3. Bạn sẽ thấy thư mục cache của từng app
4. Xóa nội dung bên trong từng thư mục (giữ lại thư mục rỗng — không xóa thư mục gốc)

**Cache cụ thể có thể xóa an toàn:**
- `com.apple.Safari` — cache Safari
- `com.apple.AppStore` — cache App Store
- `com.spotify.client` — cache Spotify (có thể 2–5GB)
- `com.google.Chrome` — cache Chrome (có thể 3–8GB)
- `com.microsoft.teams` — cache Teams (có thể 1–3GB nếu bạn dùng nhiều)
- `com.adobe.AdobePhotoshop*` — cache Photoshop

**Log files (~/Library/Logs):**
1. Go to Folder: `~/Library/Logs`
2. Xóa toàn bộ nội dung — log files cũ không cần thiết

**System cache (/Library/Caches):**
1. Go to Folder: `/Library/Caches`
2. Cần quyền admin — xóa nội dung thư mục không quan trọng

**User temp files:**
1. Go to Folder: `~/Library/Application Support` — một số app lưu cache ở đây
2. Chỉ xóa thư mục cache của app bạn chắc chắn không cần

**Lượng giải phóng:** 5–20GB.

### Bước 4: Dọn Language Files (10 phút)

Khi bạn cài macOS và các app, nó cài kèm **20–30 ngôn ngữ** — trong khi bạn chỉ dùng tiếng Việt và tiếng Anh. Mỗi ngôn ngữ ~50MB, tổng thiệt hại: 1–1.5GB.

**Cách thủ công (dùng Terminal — cẩn thận):**
```bash
# Xem dung lượng ngôn ngữ các app (cần sudo)
sudo du -sh /Applications/*.app/Contents/Resources/*.lproj 2>/dev/null | sort -hr | head -20
```

**Cách an toàn hơn — dùng CleanMyMac:**
- Mở CleanMyMac → System Junk → Language Files → chọn ngôn ngữ cần xóa (chỉ giữ "vi" và "en")

**Cách thủ công — từng app:**
1. Vào Applications → chuột phải app → Show Package Contents
2. Vào Contents/Resources/
3. Xóa thư mục `.lproj` không dùng (vd: `ja.lproj`, `ko.lproj`, `de.lproj`, `fr.lproj`...)
4. Làm với các app nặng: Pages, Keynote, Numbers, GarageBand, iMovie, Microsoft Office

**Quan trọng:** Không xóa `Base.lproj`, `en.lproj`, `vi.lproj`. Nếu không rành, đừng làm thủ công — dùng CleanMyMac hoặc skip bước này (1.5GB không phải là thảm họa).

### Bước 5: Gỡ ứng dụng không dùng (15 phút)

**Cách làm:**
1. Mở Applications folder — xem danh sách app
2. Xóa app không dùng: kéo vào Trash, hoặc chuột phải → Move to Trash

**Nhưng kéo vào Trash không xóa sạch!**
Apple gợi ý kéo app vào Trash — nhưng cách này để lại hàng tá file rác trong ~/Library (Preferences, Application Support, Caches, Containers).

**Dùng AppCleaner (miễn phí):**
1. Tải AppCleaner từ [freemacsoft.net](https://freemacsoft.net/appcleaner/) (miễn phí, mã nguồn mở)
2. Kéo app cần xóa vào cửa sổ AppCleaner
3. AppCleaner quét toàn bộ file liên quan (Preferences, Support, Cache)
4. Click Delete — sạch sẽ, an toàn

**App thường bị bỏ quên:**
- GarageBand + âm thanh mẫu (1–5GB)
- iMovie (2–4GB)
- App thử nghiệm (Sketch, Figma, VS Code... nếu không dùng)
- App từ đại học (Matlab, SPSS, AutoCAD, SolidWorks...)
- Game từ Mac App Store
- App Adobe cũ (Adobe Creative Cloud tự chiếm 1–2GB)

**Số lượng app có thể xóa:** 10–30 app, giải phóng 15–30GB.

### Bước 6: Tối ưu storage — iOS Backups và Mail Downloads (10 phút)

**iOS backups cũ:**
Đây là kẻ ngốn dung lượng lớn nhất mà ít người biết đến. Mỗi lần bạn backup iPhone vào Mac, một bản sao ~20–40GB được lưu lại.

1. Mở Finder (không phải iTunes)
2. Kết nối iPhone qua cáp
3. Trong tab General → **Manage Backups**
4. Xem danh sách backup — giữ bản mới nhất, xóa các bản còn lại
5. Xác nhận xóa

Nếu không có iPhone trong tay:
1. Go to Folder: `~/Library/Application Support/MobileSync/Backup/`
2. Xóa thư mục backup cũ — mỗi thư mục là một bản backup của một iPhone

**Mail Downloads:**
1. Mở Mail app → Ứng dụng → Thư mục Tải xuống (Downloads)
2. Xóa file đính kèm cũ, file ảnh, PDF đã mở từ email
3. Hoặc: Go to Folder: `~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/`

**Lượng giải phóng:** 20–50GB — đây thường là bước cho kết quả lớn nhất.

### Bước 7: Dọn Desktop (5 phút)

Desktop càng nhiều file, Mac càng chậm. Đây không phải truyền thuyết — là sự thật:

- macOS render từng icon trên Desktop như một cửa sổ Finder riêng
- Mỗi file ảnh/video cần macOS tạo thumbnail (process riêng)
- 50 file trên Desktop = 50 process thumbnail âm thầm chạy

**Cách làm:**
1. Dọn Desktop xuống **tối đa 10 file**
2. File công việc → vào thư mục Documents
3. File tạm → vào thư mục Downloads
4. File cần xem sau → vào thư mục Desktop Temp (tạo thư mục mới)
5. Ảnh → vào thư mục Pictures

**Mẹo:** Dùng stack (chuột phải Desktop → Use Stacks) — macOS tự động gom file theo loại. Nhưng đây là giải pháp tạm — dọn sạch vẫn tốt hơn.

---

## Bảng so sánh: Công cụ dọn Mac

| Công cụ | Giá | Tính năng chính | Ưu điểm | Nhược điểm | Đánh giá |
|---|---|---|---|---|---|
| **CleanMyMac X** | $35/năm | Dọn cache, gỡ app, malware scan, tối ưu hóa | Giao diện đẹp, dễ dùng, tính năng toàn diện | Trả phí, có thể hơi nặng với Mac cũ | ★★★★★ |
| **DaisyDisk** | $9.99 (một lần) | Trực quan hóa ổ cứng dạng bánh rán | Nhìn thấy ngay file/thư mục nào đang ngốn dung lượng | Chỉ xem được, không tự động dọn — phải tự xóa | ★★★★☆ |
| **AppCleaner** | Miễn phí | Gỡ app + dọn sạch file rác | Nhẹ, miễn phí, mã nguồn mở, làm đúng một việc | Chỉ gỡ app — không dọn cache hay tìm file lớn | ★★★★★ |
| **Onyx** | Miễn phí | Bảo trì macOS chuyên sâu | Dọn cache hệ thống, rebuild database, chạy scripts | Giao diện hơi cũ, cần hiểu biết để dùng đúng | ★★★★☆ |
| **GrandPerspective** | Miễn phí | Trực quan hóa dung lượng dạng cây (treemap) | Miễn phí, nhẹ, mã nguồn mở | Giao diện thô, khó đọc hơn DaisyDisk | ★★★★☆ |
| **Terminal (thủ công)** | Miễn phí | Dọn cache, log, temp files | Hoàn toàn miễn phí, kiểm soát tuyệt đối | Dễ sai nếu không rành, không có UI | ★★★☆☆ |

**Kết luận:**
- **Người không rành kỹ thuật:** CleanMyMac X + AppCleaner → trả $35/năm cho sự an tâm.
- **Người muốn tiết kiệm:** DaisyDisk (mua một lần $9.99) + AppCleaner (miễn phí) → combo rẻ nhất, đủ dùng.
- **Người rành Terminal:** Onyx + GrandPerspective → hoàn toàn miễn phí, làm được mọi thứ.

---

## Tips thực hành để Mac luôn nhẹ

### Dọn Desktop — giới hạn tối đa 10 file

Đây là thói quen quan trọng nhất. Mỗi file trên Desktop là một gánh nặng cho macOS. Desktop chỉ nên chứa file **đang xử lý trong ngày** — cuối ngày dọn vào thư mục phù hợp.

### Dùng Terminal để chạy bảo trì macOS định kỳ

macOS có ba script bảo trì chạy ngầm: `daily`, `weekly`, `monthly`. Nhưng chúng chỉ chạy khi Mac ở chế độ sleep vào khung giờ cố định (3:00–5:00 sáng). Nếu bạn tắt Mac mỗi tối, các script này không bao giờ chạy.

**Cách chạy thủ công (1 lệnh, chạy 15 phút):**
```bash
sudo periodic daily weekly monthly
```
Nhập mật khẩu admin → đợi 15–20 phút → macOS tự dọn cache, xoay log, rebuild database.

### Tắt app tự khởi động cùng Mac

Nhiều app tự thêm mình vào danh sách khởi động cùng Mac — mỗi app làm chậm boot thêm vài giây và ngốn RAM.

**Cách kiểm tra:**
1. System Settings → General → Login Items
2. Xem danh sách app trong "Allow in the Background" và "Open at Login"
3. Tắt những app không cần: Zoom, Teams, Spotify, Adobe CC, Dropbox (nếu không cần sync liên tục), Google Drive, Steam, Microsoft AutoUpdate...

**App NÊN giữ:** Alfred, Bitwarden, ứng dụng đồng bộ ảnh, app điều khiển chuột/bàn phím.

### Xóa app bằng AppCleaner — không kéo vào Trash

Kéo app vào Trash là cách xóa "mất vệ sinh" nhất — để lại hàng trăm file rác. Dùng AppCleaner hoặc CleanMyMac để gỡ app sạch sẽ.

### Giữ ít nhất 15–20% dung lượng trống

macOS cần không gian trống để:
- Chạy Virtual Memory (swap)
- Cập nhật hệ thống
- Tạo file tạm cho app
- Ghi log

Dưới 10% dung lượng trống → Mac sẽ chậm đi rõ rệt, đặc biệt là khi mở nhiều app cùng lúc.

---

## Ai nên áp dụng?

- **Người dùng Mac 256GB:** dung lượng này là tối thiểu cho macOS hiện đại — cần dọn 2–3 tháng/lần.
- **Dân văn phòng làm việc trên Mac:** email, file, cache từ Teams/Zoom/Slack — tất cả tạo ra rác hàng ngày.
- **Người dùng nhiều app Adobe:** Adobe Creative Cloud để lại cache và temp files cực kỳ lớn — 10–20GB mỗi tháng nếu bạn dùng Photoshop/Illustrator hàng ngày.
- **Người hay cài/thử app mới:** mỗi lần cài và xóa app để lại file rác — AppCleaner là bạn tốt nhất.
- **Người chuẩn bị nâng cấp macOS:** trước khi nâng cấp lên macOS 27, dọn Mac sạch sẽ giúp giảm nguy cơ lỗi.

## Khi nào không cần?

- **Bạn có Mac với 512GB hoặc 1TB và chỉ dùng cho công việc cơ bản (duyệt web, email, office):** dung lượng dư dả, không cần dọn thường xuyên — 1 lần/năm là đủ.
- **Bạn đã dùng CleanMyMac hàng tháng và System Data dưới 30GB:** bạn đang làm tốt — chỉ cần duy trì.
- **Bạn mới mua Mac và dùng chưa đến 3 tháng:** chưa đủ thời gian để tích rác — hãy đọc bài này để biết cách phòng tránh, nhưng chưa cần dọn.
- **Bạn đã cài lại macOS trong vòng 1 tháng:** một bản cài macOS sạch sẽ không có rác — đợi ít nhất 3 tháng trước khi dọn.

---

## Sai lầm thường gặp

1. **Dùng CleanMyMac không kiểm tra.** CleanMyMac đề xuất xóa cache và file rác dựa trên thuật toán — nhưng đôi khi nó đề xuất xóa file bạn vẫn cần. Luôn review trước khi click "Clean."
2. **Không dọn Trash sau khi xóa app.** Bạn kéo app vào Trash, nhưng quên Empty Trash — file vẫn nằm trên ổ cứng. Sau khi xóa app, luôn Empty Trash ngay.
3. **Xóa app bằng cách kéo vào Trash.** Như đã nói — cách này để lại file rác. Dùng AppCleaner. Miễn phí. Không có lý do gì để không dùng.
4. **Cài app "dọn Mac" từ các nguồn không rõ ràng.** Có những app "Mac Cleaner" miễn phí trên mạng — một số là malware. Chỉ dùng: CleanMyMac (MacPaw), DaisyDisk, AppCleaner, Onyx, GrandPerspective. Những app còn lại: cẩn thận.
5. **Không backup trước khi dọn.** Trước khi xóa cache hệ thống, dùng Terminal, hoặc chạy CleanMyMac ở chế độ sâu: backup toàn bộ Mac bằng Time Machine. Nếu có gì sai, bạn có thể khôi phục. Backup mất 30 phút — nhưng đáng giá.

---

## Checklist dọn Mac

### Chuẩn bị (15 phút)
- [ ] Backup Mac bằng Time Machine (ổ cứng ngoài hoặc NAS)
- [ ] Tải AppCleaner (miễn phí)
- [ ] Kiểm tra dung lượng: About This Mac → Storage → ghi lại dung lượng trống

### Bước 1: Dọn Trash + Downloads (5 phút)
- [ ] Empty Trash
- [ ] Mở Downloads → xóa file không dùng (DMG, ZIP đã giải nén, PDF đã đọc)
- [ ] Giữ tối đa 10 file trong Downloads

### Bước 2: Tối ưu iCloud (5 phút)
- [ ] Bật Optimize Mac Storage cho iCloud Drive
- [ ] Bật Optimize Mac Storage cho Photos
- [ ] Kiểm tra dung lượng iCloud còn đủ không

### Bước 3: Xóa cache (15 phút)
- [ ] Go: ~/Library/Caches → xóa nội dung thư mục con
- [ ] Go: ~/Library/Logs → xóa toàn bộ log files
- [ ] Go: /Library/Caches → xóa nội dung (cần admin)

### Bước 4: Dọn Language Files (10 phút)
- [ ] Dùng CleanMyMac hoặc thủ công xóa .lproj không dùng
- [ ] Chỉ giữ vi + en

### Bước 5: Gỡ app không dùng (15 phút)
- [ ] Mở Applications → xác định app không dùng quá 30 ngày
- [ ] Dùng AppCleaner gỡ từng app
- [ ] Đặc biệt: GarageBand, iMovie, app thử nghiệm

### Bước 6: iOS Backups + Mail (10 phút)
- [ ] Finder → Manage Backups → xóa backup cũ (giữ bản mới nhất)
- [ ] Xóa Mail Downloads: ~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/

### Bước 7: Dọn Desktop (5 phút)
- [ ] Giữ tối đa 10 file trên Desktop
- [ ] File còn lại → Documents / Downloads / Pictures
- [ ] Nếu có nhiều file: tạo thư mục Desktop Temp

### Duy trì (10 phút/tháng)
- [ ] Dọn Desktop hàng tuần
- [ ] Chạy Terminal: `sudo periodic daily weekly monthly` (hàng tháng)
- [ ] Kiểm tra Login Items: System Settings → General → Login Items
- [ ] Xóa cache app (Chrome, Spotify, Teams) mỗi tháng
- [ ] Empty Trash sau mỗi lần xóa app

---

> **Bài trước:** [Dọn iPhone như thế nào để máy luôn mượt và còn nhiều bộ nhớ?](/posts/don-iphone-nhu-the-nao-de-may-luon-muot-va-con-nhieu-bo-nho/)

Dọn Mac không phải là một dự án lớn — nó là một thói quen. 10 phút mỗi tháng để Mac luôn nhanh, nhẹ và sẵn sàng cho công việc.

Và nếu sau tất cả các bước này, Mac vẫn chậm? Hãy cân nhắc nâng cấp lên macOS 27 — nhưng trước đó, hãy đọc bài [Chuẩn bị MacBook trước khi lên macOS 27](/posts/chuan-bi-macbook-truoc-khi-len-macos-27/) để không gặp lỗi.

Đây cũng là bài cuối trong series **Cuộc sống số**. Từ bài đầu tiên — 30 thói quen số gọn gàng — đến bài cuối — dọn Mac. Hy vọng bạn đã tìm thấy giá trị cho riêng mình.
