# Coding Rules

- Khi deploy tính năng mới, QA chỉ bắt tính năng đó, không bắt toàn site dẫn đến failed không cần thiết.
- Mỗi bài viết phải có tối thiểu 2 ảnh: 1 ảnh hero (cover) + ít nhất 1 ảnh minh họa nội dung. Bài kỹ thuật cũng không ngoại lệ.
- Content Direction workflow: auto mỗi 24 giờ (cron 22:47 UTC ≈ 05:47 Asia/Ho_Chi_Minh, mốc từ 2026-07-10). Không chạy sau mỗi post/deploy. Manual `workflow_dispatch` luôn được phép và không ảnh hưởng chu kỳ auto.
- Sau khi viết xong một bài blog (trên bất kỳ branch nào), phải chạy ngay `source .env && python3 scripts/select_images.py --post content/posts/<slug>.md --fix` để chọn ảnh từ Pexels/Pixabay API. Sau đó chạy script process/xử lý WebP, force-add file ảnh, cập nhật manifest. Không được bỏ qua bước này.
- **BẮT BUỘC:** Mọi bài viết trong `content/posts/` phải có trường `commit = "xxxxxxx"` trong front matter. Không có ngoại lệ. Kiểm tra trước khi push bằng lệnh: `grep -l "^commit" content/posts/*.md | wc -l` (phải == tổng số file .md). Nếu thiếu, chạy `python3 scripts/add_commit_id.py` rồi kiểm tra lại. Chạy script này ngay sau mỗi lần merge bài mới vào `main` — trước khi push commit tiếp theo. Format: `commit = "<7-ký-tự-đầu-của-hash>"` (TOML syntax, dùng dấu `=`, không dùng dấu `:`).

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
- QA blog trước deploy phải chạy kiểm tra ảnh cho bài trong scope thay đổi. Nếu bài thiếu/bể `image` hoặc `thumbnail`, phải gọi Pexels/Pixabay API để chọn ảnh thật, xử lý WebP + watermark attribution, cập nhật front matter/manifest, rồi mới accept deploy. Nếu không có key hoặc không tìm được ảnh hợp lệ thì fail deploy, không dùng fallback/self-generated.
- Source of truth trước deploy là `python scripts/rule.py --fix`: front matter bài viết phải là TOML (`+++`), date lưu canonical ISO `+07:00` cho Hugo, display date dùng `dd-mm-yyyy hh:mm:ss GMT +7`, mọi future date là fake và phải sửa về thời gian thật Asia/Ho_Chi_Minh trước deploy.

- Trước khi push code lên production (`main`), phải đọc lại toàn bộ quy tắc trong AGENTS.md và các quy tắc blog khác để đảm bảo tuân thủ đầy đủ.
- Bài viết không có ảnh (thiếu `image` hoặc `thumbnail` trong front matter) thì không được phép push lên `main` và deploy production.
- File `.webp` trong `static/images/posts/` bị `.gitignore` chặn. Sau khi tạo ảnh WebP cho bài viết mới, phải dùng `git add -f static/images/posts/<slug>.webp` để force-add trước khi commit. Kiểm tra `git status` và `git ls-files` để đảm bảo file ảnh WebP đã được track.
- **Không dùng YAML syntax (`key: value`) trong TOML front matter (`+++`).** Hugo dùng TOML parser. Sai syntax (ví dụ `commit: abc` thay vì `commit = "abc"`) sẽ làm parser fail tại dòng đó, khiến `rule.py --fix` không đọc được các field phía sau (categories, date, image...), dẫn đến deploy crash và date bị ghi đè thành thời gian chạy `rule.py`. Luôn dùng `key = "value"` (TOML) trong front matter.
- **Content Depth:** Mọi bài viết (cả VN và EN) phải có tối thiểu **3000 từ**. Sử dụng thước đo `wc -w` trên nội dung markdown (loại bỏ front matter) để kiểm tra. Internal links và external links là **optional** — không bắt buộc phải thêm vào. Nếu muốn thêm links:
  - External links: trỏ đến nguồn tham khảo uy tín bên ngoài để tăng giá trị SEO.
  - Internal links: chỉ thêm khi có bài viết thật trong blog, không tạo link placeholder/fake. Nếu không có bài cùng chủ đề, bỏ qua internal link.
- **TUYỆT ĐỐI CẤM `![[IMAGE_API_QUERY:...]]` markers trong nội dung bài viết.** Không được viết, không được giữ lại, không được coi là placeholder tạm thời. Đây là marker chết — không script nào xử lý, không tự động replace. Nếu marker còn sót trong file `.md` khi push, coi như lỗi nghiêm trọng, phải fix ngay. Ảnh minh họa inline chỉ được chèn bằng Markdown `![](...)` thủ công với URL ảnh thật.

# Deployment Rule (từ 2026-07-10)

- **1 change = 1 branch = 1 deploy.** Mỗi tính năng / thay đổi phải được phát triển trên một nhánh riêng, tách biệt hoàn toàn với các nhánh tính năng khác.
- Không gộp chung nhiều tính năng vào cùng một nhánh deploy. Khi merge, chỉ merge đúng 1 nhánh tính năng duy nhất vào `main`.
- Deploy chỉ kích hoạt khi push commit tính năng lên `main`. Đảm bảo mỗi lần deploy chỉ mang đúng 1 thay đổi, tránh lẫn blog post, ảnh, hay bất kỳ file nào ngoài scope.
- **Deploy FIFO — xếp hàng chờ, không chạy đồng loạt.** Các deploy phải cách nhau tối thiểu **30 giây**. Không push nhiều commit liên tiếp lên `main` trong cùng một khoảnh khắc. Dùng `git push` kèm kiểm tra GitHub Actions queue trước khi push commit tiếp theo. Tránh rate limit GitHub API, Pixabay/Pexels, và tránh concurrent build chồng chéo.
