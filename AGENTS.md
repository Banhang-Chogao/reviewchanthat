# Coding Rules

- Khi deploy tính năng mới, QA chỉ bắt tính năng đó, không bắt toàn site dẫn đến failed không cần thiết.
- Mỗi bài viết phải có tối thiểu 2 ảnh: 1 ảnh hero (cover) + ít nhất 1 ảnh minh họa nội dung. Bài kỹ thuật cũng không ngoại lệ.
- Content Direction workflow: auto mỗi 24 giờ (cron 22:47 UTC ≈ 05:47 Asia/Ho_Chi_Minh, mốc từ 2026-07-10). Không chạy sau mỗi post/deploy. Manual `workflow_dispatch` luôn được phép và không ảnh hưởng chu kỳ auto.
- Sau mỗi lần commit bài viết blog lên `main`, phải thêm commit hash đó vào nội dung bài viết (dòng đầu tiên bên dưới `+++` front matter, sau title, trước date). Format: `commit: <7-ký-tự-đầu-của-hash>`. Ví dụ: `commit: 89bkasj`. Dùng `git rev-parse --short HEAD` để lấy hash. Nếu chưa thêm thì push sau đó sửa lại.

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
- QA blog trước deploy phải chạy kiểm tra ảnh cho bài trong scope thay đổi. Nếu bài thiếu/bể `image` hoặc `thumbnail`, phải gọi Pexels/Pixabay API để chọn ảnh thật, xử lý WebP + watermark attribution, cập nhật front matter/manifest, rồi mới accept deploy. Nếu không có key hoặc không tìm được ảnh hợp lệ thì fail deploy, không dùng fallback/self-generated.
- Source of truth trước deploy là `python scripts/rule.py --fix`: front matter bài viết phải là TOML (`+++`), date lưu canonical ISO `+07:00` cho Hugo, display date dùng `dd-mm-yyyy hh:mm:ss GMT +7`, mọi future date là fake và phải sửa về thời gian thật Asia/Ho_Chi_Minh trước deploy.

# Deployment Rule (từ 2026-07-10)

- **1 change = 1 branch = 1 deploy.** Mỗi tính năng / thay đổi phải được phát triển trên một nhánh riêng, tách biệt hoàn toàn với các nhánh tính năng khác.
- Không gộp chung nhiều tính năng vào cùng một nhánh deploy. Khi merge, chỉ merge đúng 1 nhánh tính năng duy nhất vào `main`.
- Deploy chỉ kích hoạt khi push commit tính năng lên `main`. Đảm bảo mỗi lần deploy chỉ mang đúng 1 thay đổi, tránh lẫn blog post, ảnh, hay bất kỳ file nào ngoài scope.
