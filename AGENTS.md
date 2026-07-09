# Coding Rules

- Khi deploy tính năng mới, QA chỉ bắt tính năng đó, không bắt toàn site dẫn đến failed không cần thiết.
- Mỗi bài viết phải có tối thiểu 2 ảnh: 1 ảnh hero (cover) + ít nhất 1 ảnh minh họa nội dung. Bài kỹ thuật cũng không ngoại lệ.
- Deploy GitHub Pages chạy xong mới tới Deploy Content Direction (content direction chạy sau deploy).

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
