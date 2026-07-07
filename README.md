# Review Chân Thật

Blog review sản phẩm và dịch vụ trung thực, khách quan. Xây dựng bằng **Hugo** + **Python**.

## Yêu cầu

- [Hugo](https://gohugo.io/) v0.157+ (extended)
- Python 3.11+
- `pip install pyyaml`

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

## Build

```bash
hugo --minify
```

Kết quả xuất ra thư mục `public/`.

## GitHub Pages

Repo đã tích hợp sẵn GitHub Actions. Mỗi lần push lên nhánh `main`:

1. Chạy QA script.
2. Build Hugo site.
3. Build search index.
4. Deploy lên GitHub Pages.

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
