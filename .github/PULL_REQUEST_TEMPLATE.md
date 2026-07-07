## Mô tả

<!-- Tóm tắt ngắn gọn PR này làm gì, tại sao cần thay đổi này -->

## Loại thay đổi

<!-- Chọn 1 (bỏ dòng không dùng): -->

- ✨ **feat** — Tính năng mới
- 🐛 **fix** — Sửa lỗi
- 📝 **docs** — Chỉ sửa tài liệu/README
- 🎨 **style** — CSS, theme, giao diện (không ảnh hưởng logic)
- ♻️ **refactor** — Code change không fix bug, không thêm feature
- ⚡ **perf** — Cải thiện hiệu năng
- 🧪 **test** — Thêm/sửa test
- 🔧 **chore** — Dependencies, config, CI/CD, scripts
- ⏪ **revert** — Revert commit trước đó

## Checklist

- [ ] Commit message theo chuẩn **Conventional Commits** (`feat:`, `fix:`, `chore:`, ...)
- [ ] Đã chạy `python scripts/qa_blog.py` — không có lỗi
- [ ] Đã chạy `hugo --minify` — build thành công
- [ ] Nếu thêm ảnh: đã chạy `python scripts/process_images.py`
- [ ] Nếu thêm bài viết mới: front matter đầy đủ (title, date, author, image, ...)

## Ảnh chụp màn hình (nếu có)

<!-- Kéo thả ảnh vào đây để minh họa thay đổi giao diện -->

## Ghi chú thêm

<!-- Bất kỳ điều gì reviewer cần biết -->
