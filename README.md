# Review Chân Thật

Blog review sản phẩm và dịch vụ trung thực, khách quan. Xây dựng bằng **Hugo** + **Python**.

## Yêu cầu

- [Hugo](https://gohugo.io/) v0.157+ (extended)
- Python 3.11+
- `pip install -r requirements.txt`

## Chạy local

```bash
hugo server
```

Mở trình duyệt tại http://localhost:1313/.

## Tạo bài viết mới

```bash
python scripts/new_post.py "Tiêu đề bài viết" \
  --author "Tên tác giả" \
  --category "review" \
  --tag "tag1" \
  --tag "tag2" \
  --description "Mô tả ngắn" \
  --image "https://example.com/image.jpg"
```

Có thể thay `--category` hoặc `--tag` nhiều lần để thêm nhiều nhóm/tag.

## Kiểm tra chất lượng

```bash
# Kiểm tra front matter
python scripts/normalize_frontmatter.py

# QA tổng thể (draft, date, slug, ảnh, link)
python scripts/qa_blog.py

# Build search index
hugo && python scripts/build_search_index.py
```

## Image Policy

Tất cả ảnh bài blog phải tuân thủ:

- **Nguồn cho phép commercial use** — ưu tiên [Pixabay](https://pixabay.com/images/search/commercial%20use/). Không dùng ảnh không rõ license, có logo/trademark, hoặc người nhận diện rõ mà không có model release.
- **Tuân thủ Pixabay Content License**: dùng miễn phí, không bắt buộc attribution, được chỉnh sửa/adapt. Không bán/phân phối standalone, không dùng trademark cho mục đích thương mại, không gây hiểu nhầm/deceptive.
- **Front matter bắt buộc**:
  ```yaml
  image: "images/posts/example-hero.webp"
  image_source: "Pixabay"
  image_source_url: "https://pixabay.com/..."
  image_license: "Pixabay Content License"
  image_commercial_use: true
  image_owner: "external"  # hoặc "self"
  ```

  *Lưu ý: `image` không có `/` ở đầu — Hugo cần path relative (không leading slash) để `relURL`/`absURL` xử lý đúng baseURL path.*

### Xử lý ảnh tự động

1. Đặt ảnh tự sở hữu vào `static/images/posts-src/`.
2. Với ảnh external, tạo file metadata kèm theo: `ten-anh.jpg.meta.json`
   ```json
   {
     "source": "external",
     "source_url": "https://pixabay.com/...",
     "license": "Pixabay Content License",
     "commercial_use": true
   }
   ```
3. Chạy pipeline:
   ```bash
   pip install -r requirements.txt
   python scripts/process_images.py
   ```
4. Dùng path output trong front matter (ví dụ: `images/posts/example-hero.webp`).

Pipeline tự động:
- Resize/crop center-fit theo preset (hero 800×450, card 220×165).
- Chuyển sang WebP.
- Đóng watermark cho ảnh self-owned (`16digits_https://banhang-chogao.github.io/reviewchanthat/` ở góc dưới phải, opacity 50%).
- External ảnh không bị watermark.
- Sinh manifest `data/images.json`.

## Build

```bash
hugo --minify
```

Kết quả xuất ra thư mục `public/`.

## GitHub Pages

Repo đã tích hợp sẵn GitHub Actions. Mỗi lần push lên nhánh `main`:

1. Xử lý ảnh (resize, crop, WebP, watermark).
2. Chạy QA script.
3. Build Hugo site.
4. Build search index.
5. Deploy lên GitHub Pages.

**Cần bật GitHub Pages trong repo Settings → Pages → Source: GitHub Actions.**

## Cấu trúc thư mục

```
.
├── hugo.toml
├── content/
│   └── posts/          # Bài viết Markdown
├── layouts/            # Hugo templates
│   ├── _default/
│   ├── partials/
│   └── posts/
├── assets/css/         # CSS (Hugo Pipes)
├── scripts/            # Python hỗ trợ
├── static/             # File tĩnh
└── .github/workflows/  # CI/CD
```

## License

MIT

