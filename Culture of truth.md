# Culture of Truth — Smart Deployment Logic

## Project Identity

| Field | Value |
|-------|-------|
| Blog name | Review Chân Thật |
| Tagline | Review thật, trải nghiệm thật, quyết định thông minh hơn. |
| Repo | https://github.com/Banhang-Chogao/reviewchanthat |
| Domain | https://banhang-chogao.github.io/reviewchanthat/ |
| Language | vi-vn |
| Stack | Hugo + Python 3.12+ |
| CSS | Thuần, system font, không npm/JS framework |

## Hugo Config (hugo.toml)

```toml
baseURL = "https://banhang-chogao.github.io/reviewchanthat/"  # trailing slash bắt buộc
languageCode = "vi-vn"
title = "Review Chân Thật"
paginate = 6
enableRobotsTXT = true

[permalinks]
posts = "/:slug/"          # bài viết ở root: /cach-doc-review/
categories = "/:slug/"     # category ở root: /review/, /cong-nghe/
tags = "/tags/:slug/"      # tag ở /tags/:slug/

[taxonomies]
category = "categories"
tag = "tags"
```

## URL Structure

```
/                               → Home
/:slug/                        → Post detail
/:slug/                        → Category listing (e.g. /review/, /cong-nghe/)
/tags/:slug/                   → Tag listing (e.g. /tags/benchmark/)
/about/                        → About page
```

**Không dùng** `/categories/` hoặc `/category/` trong URL.

## Navigation

Header links (6 items):
- Trang chủ → /
- Review → /review/
- Công nghệ → /cong-nghe/
- Đời sống → /doi-song/
- Tài chính → /tai-chinh/
- Về chúng tôi → /about/

## Card Layout (clone blog.eltondata.com)

Mỗi post card trên homepage:
```
[Categories/Tags badges]
[Title (large, bold, link)]
[Avatar 28px + Author name + Date (DD/MM/YYYY)]
[Excerpt 2-4 dòng]
[Thumbnail 200x133 ở cạnh phải desktop, full width mobile]
```

## Python Scripts

| Script | Usage |
|--------|-------|
| `scripts/new_post.py` | `python scripts/new_post.py "Title" [--author] [--category] [--tag] [--description] [--image]` |
| `scripts/normalize_frontmatter.py` | Validate front matter of all posts |
| `scripts/build_search_index.py` | Export `static/search-index.json` (run after `hugo`) |
| `scripts/qa_blog.py` | Check drafts, future dates, slug validity, image refs, internal links |

## GitHub Actions (deploy.yml)

- Trigger: push `main` + `workflow_dispatch`
- Steps: checkout → install Hugo → setup Python → `pip install pyyaml` → QA → `hugo --minify` → build search index → upload artifact → deploy
- GitHub Pages Source: **GitHub Actions** (Settings → Pages → Source)
- Important: `theme = ""` must NOT exist in hugo.toml (causes CI failure)

Required permissions in workflow:
```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

## Git & Push

Token push pattern (khi cần push gấp):
```bash
git remote set-url origin "https://Banhang-Chogao:<TOKEN>@github.com/Banhang-Chogao/reviewchanthat.git"
git push origin <branch>
git remote set-url origin "https://github.com/Banhang-Chogao/reviewchanthat.git"
```

PR creation pattern (khi main và feature branch cùng commit):
1. `git checkout -b feat/<name>`
2. Sửa nhẹ 1 file (e.g. README.md) để tạo diff
3. `git add . && git commit -m "trigger PR"`
4. `git push origin feat/<name>`
5. Tạo PR qua API hoặc `gh`

## Front Matter Template

```yaml
---
title: ""
date: 2026-01-01T10:00:00+07:00
description: ""
categories: [""]
tags: [""]
author: "Minh Hoàng"
avatar: "https://api.dicebear.com/9.x/avataaars/svg?seed=MinhHoang"
image: ""
draft: false
---
```

Required fields: `title`, `date`, `description`, `categories`, `tags`, `author`.

Date format: ISO 8601 with +07:00 timezone. Không dùng ngày tương lai.

## Visual Rules

- **Font**: system font stack (-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ...)
- **Không** Google Fonts remote
- **Không** JS framework
- **Không** dark theme mặc định
- **Nền**: trắng (#fff)
- **Text chính**: #1a1a2e
- **Link hover**: #2563eb
- **Category badge**: #2563eb text, #eef2ff background
- **Spacing**: rộng, thoáng, editorial style
- **Ảnh**: lazy-load, width/height set

## Deployment Checklist

- [ ] `hugo --minify` build thành công
- [ ] `python scripts/qa_blog.py` pass
- [ ] `python scripts/normalize_frontmatter.py` pass
- [ ] `python scripts/build_search_index.py` chạy sau hugo
- [ ] Không commit `public/` hoặc `.hugo_build.lock`
- [ ] GitHub Pages Source = GitHub Actions
- [ ] baseURL có trailing slash
- [ ] Category URLs không chứa /categories/

## Quick Commands

```bash
# Dev
hugo server

# Build
hugo --minify

# New post
python scripts/new_post.py "Title" --category review --tag "tag"

# QA
python scripts/qa_blog.py
python scripts/normalize_frontmatter.py

# Search index
hugo && python scripts/build_search_index.py
```

## Content Rules

- Tiếng Việt, không copy nội dung gốc từ bất kỳ nguồn nào
- Ảnh dùng Unsplash, DiceBear avatar, hoặc URL tuyệt đối
- `draft: false` cho bài public
- Slug tự động từ title, không chứa ký tự đặc biệt
