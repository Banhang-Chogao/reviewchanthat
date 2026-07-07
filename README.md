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
# 📋 Kiểm tra front matter
python scripts/normalize_frontmatter.py

# 🔎 QA tổng thể (draft, date, slug, ảnh, link hỏng)
python scripts/qa_blog.py

# 🏗️ Build search index
hugo && python scripts/build_search_index.py
```

---

## 🖼️ Image Pipeline (xịn xò)

Blog này có một pipeline xử lý ảnh tự động cực kỳ pro:

```
                     ┌─────────────┐
  Ảnh gốc (JPEG/PNG) │  Python +   │  WebP 800×450 (hero)
 ───────────────────►│   Pillow    ├──► WebP 220×165 (card)
                     │             │  Watermark (self-owned)
                     └─────────────┘  Manifest JSON
```

| Tính năng | Mô tả |
|:---|---:|
| 🔄 **Resize + Crop** | Center-fit theo preset: hero 800×450, card 220×165 |
| 🎨 **WebP** | Chuyển sang WebP — nhẹ hơn, trong hơn |
| 💧 **Watermark** | Tự động đóng watermark cho ảnh tự sở hữu (góc phải dưới, opacity 50%) |
| 🛡️ **Bảo vệ** | Ảnh external không bị watermark |
| 📦 **Manifest** | Sinh file `data/images.json` để template dùng |

### Cách dùng

```bash
# Đặt ảnh gốc vào static/images/posts-src/
# Ảnh external cần file metadata kèm .meta.json

# Chạy pipeline:
pip install -r requirements.txt
python scripts/process_images.py
```

---

## 🏗️ Build sản phẩm

```bash
hugo --minify
```

📂 Kết quả xuất ra thư mục `public/` — sẵn sàng deploy.

---

## 🚀 Deploy (GitHub Actions)

Mỗi lần push lên `main`, robot tự động:

1. 🖼️ **Xử lý ảnh** → resize, crop, WebP, watermark
2. 🧪 **Chạy QA** → kiểm tra toàn bộ bài viết
3. 🏗️ **Build Hugo** → `hugo --minify`
4. 🔍 **Build search index**
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
 ┣ 📂 scripts              # 🐍 Python scripts
 ┣ 📂 static               # 📎 File tĩnh
 ┣ 📂 .github/workflows    # 🤖 CI/CD
 ┣ 📜 hugo.toml            # ⚙️ Config
 ┗ 📜 requirements.txt     # 📦 Python deps
```

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

