---
ai_summary:
  collapsed: false
  disclaimer: Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi
    repo cần điều chỉnh policy theo rủi ro riêng.
  enabled: true
  items:
  - Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).
  - 'Nhiều failure không phải bug code: runner queue, platform incident, rate limit,
    Pages CDN lag.'
  - 'Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng
    feature không.'
  title: Tóm tắt nhanh
author: Minh Hoàng
categories:
- cong-nghe
date: '2026-07-10 04:50:00+07:00'
description: '| Code | Safety | Mô tả | |------|--------|--------| | baseurlroutingerror
  | safe | Path absolute bỏ prefix /reviewchanthat/ | | sitemapnoindexmismatch | safe
  |'
draft: false
image: images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url.webp
image_alt: Ảnh minh họa BaseURL, sitemap noindex và series hardcoded URL trên GitHub
  project Pages — nguồn Pexels
image_attribution_checked_at: '2026-07-10T07:08:07+07:00'
image_attribution_source: pexels_api
image_attribution_verified: true
image_commercial_use: true
image_creator: RDNE Stock project
image_creator_id: '3149039'
image_creator_url: https://www.pexels.com/@rdne
image_license: Pexels License
image_license_url: https://www.pexels.com/license/
image_owner: external
image_provider: pexels
image_query: baseurl sitemap noindex series hardcoded
image_source: Pexels
image_source_url: https://www.pexels.com/photo/a-graph-in-close-up-photography-7947635/
image_status: verified
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- live-deploy-khong-phan-anh-va-pages-serving-old-artifact
- hugo-build-duplicate-yaml-ai-summary-va-template-regression
seo_title: BaseURL, sitemap noindex và series hardcoded URL trên GitHub
series: ci-cd-root-cause-lessons
series_order: 10
series_title: CI/CD Root Cause Lessons
slug: baseurl-sitemap-noindex-va-series-hardcoded-url
tags:
- baseURL
- sitemap
- SEO
- Hugo
- GitHub Pages
thumbnail: images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url.webp
title: BaseURL, sitemap noindex và series hardcoded URL trên GitHub project Pages
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `baseurl_routing_error` | safe | Path absolute bỏ prefix `/reviewchanthat/` |
| `sitemap_noindex_mismatch` | safe | Trang noindex vẫn nằm trong sitemap |
| `series_hardcoded_url` | safe | Hardcode `/series/` vỡ khi site là project Pages |

![Sơ đồ routing baseURL project Pages](/images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url-diagram.webp)

## BaseURL

Site: `https://banhang-chogao.github.io/reviewchanthat/`.

```html
<!-- SAI -->
<link href="/css/main.css">
<a href="/posts/hello/">

<!-- ĐÚNG: dùng relURL / absURL / site.BaseURL trong template -->
```

Trong markdown ảnh: ưu tiên shortcode/partial resolve; tránh hardcode host.

## Sitemap vs noindex

Trang `branding-ci`, admin, một số landing: `noindex: true` **và** `_build.list: false` / loại khỏi sitemap. QA `sitemap_noindex_mismatch` bắt khi hai nguồn sự thật lệch.

## Series URL

Dùng `relLangURL` / `permalink` thay vì chuỗi `"/series/foo/"`. Hardcode phá cả local `localhost` lẫn project base path.

Xem: [Live verify](/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).