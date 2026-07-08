<div align="center">

# 🎭 Review Chân Thật

### *"Nói thật — không sợ mất lòng"*

[![Hugo](https://img.shields.io/badge/Hugo-v0.157%2B-FF4088?style=for-the-badge&logo=hugo&logoColor=white&labelColor=black)](https://gohugo.io/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=black)](https://python.org)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white&labelColor=black)](.github/workflows/)
[![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-222222?style=for-the-badge&logo=githubpages&logoColor=white&labelColor=black)](https://pages.github.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&labelColor=black)](LICENSE)
[![SEO Ready](https://img.shields.io/badge/SEO-Ready-00C853?style=for-the-badge&labelColor=black)](https://developer.mozilla.org/en-US/docs/Glossary/SEO)

---

> 🚀 **Blog review sản phẩm & dịch vụ** — trung thực, khách quan, có tâm.
>
> Tự động hóa bằng **Python**, siêu tốc bằng **Hugo**, deploy tự động bằng **GitHub Actions**.

<p align="center">
  <img src="https://img.shields.io/badge/⚡_Hiệu_năng-100_/_100-00E676?style=flat-square" />
  <img src="https://img.shields.io/badge/📱_Responsive-Có-2196F3?style=flat-square" />
  <img src="https://img.shields.io/badge/🔍_Search_Tích_hợp-Có-FF9800?style=flat-square" />
  <img src="https://img.shields.io/badge/🌙_Dark_Mode-Có-9C27B0?style=flat-square" />
</p>

</div>

---

## 🧠 Tech Stack — "Cỗ máy" đằng sau blog

| Thành phần | Công nghệ | Tác dụng |
|:---|:---|---:|
| ⚡ **Static Site Generator** | [![Hugo](https://img.shields.io/badge/Hugo-FF4088?logo=hugo&logoColor=white)](https://gohugo.io/) | Siêu tốc độ, build trong mili-giây |
| 🐍 **Scripting & Automation** | [![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://python.org) | Xử lý ảnh, QA, search index |
| 🎨 **CSS Pipeline** | Hugo Pipes + Custom CSS | Tối ưu, minify tự động |
| 🖼️ **Image Pipeline** | Python + Pillow | Resize, crop, WebP, watermark |
| 🤖 **CI/CD** | [![GitHub Actions](https://img.shields.io/badge/Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/) | Auto build & deploy |
| 🌐 **Hosting** | [![GitHub Pages](https://img.shields.io/badge/Pages-222222?logo=githubpages&logoColor=white)](https://pages.github.com/) | Free, nhanh, HTTPS |
| 📝 **Content** | Markdown + YAML Front Matter | Viết dễ, SEO chuẩn |
| 🧪 **Quality** | Python QA Scripts | Kiểm tra link, ảnh, metadata |

---

## 🎯 Tính năng nổi bật

<table>
<tr>
  <td align="center">⚡<br><b>Siêu tốc</b></td>
  <td>Trang load gần như tức thì — Hugo build &lt; 1s, không JavaScript nặng</td>
</tr>
<tr>
  <td align="center">🤖<br><b>Tự động hóa</b></td>
  <td>Script Python xử lý ảnh, tạo bài viết, QA, build search index — tất cả chỉ một cú pháp</td>
</tr>
<tr>
  <td align="center">🖼️<br><b>Image Pipeline</b></td>
  <td>Auto resize → crop → WebP → watermark. Ảnh self-owned có watermark, external thì không</td>
</tr>
<tr>
  <td align="center">🔍<br><b>Search</b></td>
  <td>Search index được build tự động, tìm kiếm real-time ngay trên blog</td>
</tr>
<tr>
  <td align="center">🌙<br><b>Dark Mode</b></td>
  <td>Giao diện tối/sáng tự động theo hệ thống</td>
</tr>
<tr>
  <td align="center">📱<br><b>Responsive</b></td>
  <td>Đẹp trên mọi thiết bị — desktop, tablet, mobile</td>
</tr>
<tr>
  <td align="center">🔗<br><b>SEO Chuẩn</b></td>
  <td>Open Graph, JSON-LD, meta tags đầy đủ. Social preview đẹp</td>
</tr>
<tr>
  <td align="center">🚀<br><b>CI/CD</b></td>
  <td>Push lên main → tự động xử lý ảnh → QA → build → deploy — zero touch</td>
</tr>
</table>

---

## 🛠️ Bắt đầu nhanh

### Yêu cầu

```bash
# 1. Cài Hugo extended
brew install hugo          # macOS
# hoặc: https://gohugo.io/installation/

# 2. Cài Python deps
pip install -r requirements.txt
```

### Chạy local — 1 câu lệnh

```bash
hugo server
```

👉 Mở trình duyệt tại **http://localhost:1313/**

### Tạo bài viết mới

```bash
python scripts/new_post.py "Tiêu đề bài viết" \
  --author "Tên tác giả" \
  --category "review" \
  --tag "tag1" \
  --tag "tag2" \
  --description "Mô tả ngắn" \
  --image "https://example.com/image.jpg"
```

💡 Có thể thêm `--category` hoặc `--tag` nhiều lần.

---

## 🧪 Quality Assurance

```bash
# 🖼️ Audit post images (thiếu ảnh, path sai, metadata, trùng)
python scripts/audit_post_images.py

# 🔎 Kiểm tra ảnh trùng
python scripts/image_dedupe.py

# ✅ QA tổng thể (draft, date, slug, ảnh, metadata, link)
python scripts/qa_blog.py
```

---

## 🖼️ Image Pipeline (AI-assisted + Deduplication)

Blog có pipeline ảnh khoa học gồm 4 giai đoạn:

```
                          ┌──────────────────┐
  content/posts/*.md ────►│ audit_post_images │──► data/image-audit-report.json
                          └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  select_images   │──► data/images.json (manifest)
                          │  (AI-assisted)   │──► data/image-source-cache.json
                          └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ process_images   │──► static/images/posts/*.webp
                          │ (resize + WebP   │──► frontmatter updated
                          │  + watermark)    │
                          └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  image_dedupe    │──► data/image-dedupe-report.json
                          └──────────────────┘
```

| Tính năng | Mô tả |
|:---|---:|
| 🔍 **Audit** | Scan toàn bộ post, phát hiện thiếu ảnh, path sai, thiếu metadata, ảnh trùng |
| 🤖 **AI Selection** | Sinh keywords từ nội dung, tra API Pixabay/Pexels/Unsplash (nếu có key), chấm điểm relevance |
| 🖼️ **Process** | Download → crop 16:9 → resize 800×450 → WebP → watermark attribution text |
| 🔄 **Dedupe** | Kiểm tra source_url trùng, perceptual hash, output file trùng |
| ✅ **QA** | FAIL nếu thiếu ảnh, license, source_url, commercial_use, path sai, ảnh trùng |

### Watermark attribution

- Góc dưới phải, text nhỏ, nền mờ
- Chỉ ghi: `"Source: Pixabay"`, `"Source: Unsplash / Photographer Name"`
- Không dùng logo nền tảng
- Ảnh external: attribution watermark theo source
- Fallback image: `static/images/posts/fallback.webp`

### Cách dùng pipeline

```bash
# 1. Audit post images
python scripts/audit_post_images.py

# 2. Select images (AI-assisted — yêu cầu API keys hoặc chạy chế độ suggest)
#    Cần env vars: UNSPLASH_ACCESS_KEY, PEXELS_API_KEY, PIXABAY_API_KEY
python scripts/select_images.py

# 3. Process images (resize + WebP + watermark)
python scripts/process_images.py

# 4. Check deduplication
python scripts/image_dedupe.py

# 5. QA blog
python scripts/qa_blog.py

# 6. Build
hugo
```

---

## 🏗️ Build sản phẩm

```bash
hugo --minify
```

📂 Kết quả xuất ra thư mục `public/` — sẵn sàng deploy.

---

## 🚀 Deploy (GitHub Actions)

Mỗi lần push lên `main`, CI tự động:

1. 🖼️ **Audit ảnh** → phát hiện thiếu/metadata/trùng
2. 🔎 **Dedupe check** → kiểm tra ảnh trùng
3. ✅ **QA** → fail nếu thiếu ảnh, license, source_url, path sai
4. 🏗️ **Build Hugo** → `hugo --minify`
5. 🌐 **Deploy lên GitHub Pages**

> ⚠️ **Cần bật GitHub Pages**: Settings → Pages → Source: **GitHub Actions**

---

## 📁 Cấu trúc thư mục

```
📦 reviewchanthat
 ┣ 📂 content/posts        # 📝 Bài viết Markdown
 ┣ 📂 layouts              # 🎨 Hugo templates
 ┃ ┣ 📂 _default
 ┃ ┣ 📂 partials
 ┃ ┗ 📂 posts
 ┣ 📂 assets/css           # 🎯 CSS (Hugo Pipes)
 ┣ 📂 scripts              # 🐍 Python scripts xử lý ảnh & QA
 ┣ 📂 data                 # 📊 Dữ liệu pipeline (manifest, report, cache)
 ┣ 📂 static/images/posts  # 🖼️ Ảnh đã xử lý (WebP, có watermark)
 ┣ 📂 static/images/posts-src # 📥 Ảnh gốc (chưa xử lý)
 ┣ 📂 .github/workflows    # 🤖 CI/CD
 ┣ 📜 hugo.toml            # ⚙️ Config
 ┗ 📜 requirements.txt     # 📦 Python deps
```

| File Pipeline | Chức năng |
|:---|---:|
| `scripts/audit_post_images.py` | Scan frontmatter ảnh, phát hiện thiếu/trùng/sai |
| `scripts/select_images.py` | AI-assisted chọn ảnh từ API Unsplash/Pexels/Pixabay |
| `scripts/process_images.py` | Download → crop → WebP → watermark → update frontmatter |
| `scripts/image_dedupe.py` | Detect ảnh trùng (URL, file, perceptual hash) |
| `scripts/qa_blog.py` | QA cứng: fail nếu thiếu image, thumbnail, source, license, path sai |
| `data/images.json` | Manifest ảnh của toàn bộ blog |
| `data/dupe-whitelist.json` | Danh sách URL ảnh được phép dùng nhiều bài |

---

## 📜 License

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/📜_MIT_License-FF6F00?style=for-the-badge&labelColor=black" />
  </a>
</p>

<p align="center">
  <b>Review Chân Thật</b> — Made with ❤️, ☕, and a lot of 🤖
</p>

