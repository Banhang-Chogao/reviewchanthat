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
date: "2026-07-10 04:40:00+07:00"
description: 'Phân tích content_direction_empty_report, content_direction_optimizer_fail,
  metadata_optimizer_fail (safe): sai path/data key, parser front matter, seo_title/description
  lỗi.'
draft: false
image: "images/posts/content-direction-empty-report-va-optimizer-frontmatter.webp"
image_alt: "Ảnh minh họa — Pexels / Tima Miroshnichenko"
image_attribution_checked_at: '2026-07-10T04:52:57+07:00'
image_attribution_source: "pexels_api"
image_attribution_verified: true
image_commercial_use: true
image_creator: "Tima Miroshnichenko"
image_creator_id: "3088726"
image_creator_url: "https://www.pexels.com/@tima-miroshnichenko"
image_license: "Pexels License"
image_license_url: "https://www.pexels.com/license/"
image_owner: "external"
image_provider: "pexels"
image_query: content direction empty report optimizer
image_source: "Pexels"
image_source_url: "https://www.pexels.com/photo/close-up-photo-of-person-writing-on-a-paper-6170173/"
image_status: "verified"
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- post-date-timezone-vietnam-gmt7-tranh-stale-date
- hugo-build-duplicate-yaml-ai-summary-va-template-regression
series: ci-cd-root-cause-lessons
series_order: 8
series_title: CI/CD Root Cause Lessons
slug: content-direction-empty-report-va-optimizer-frontmatter
tags:
- Content Direction
- SEO
- front matter
- optimizer
- safe
thumbnail: "images/posts/content-direction-empty-report-va-optimizer-frontmatter.webp"
title: Content Direction empty report và optimizer fail vì front matter
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `content_direction_empty_report` | safe | Dashboard/report render rỗng (sai path/key/fallback) |
| `content_direction_optimizer_fail` | safe | Script optimizer fail — thường do parse front matter |
| `metadata_optimizer_fail` | safe | Lỗi khi tối ưu `seo_title` / `description` |

![Checklist path data Content Direction](/images/posts/content-direction-empty-report-va-optimizer-frontmatter-diagram.webp)

## Empty report — checklist

1. File JSON có được generate trước khi Hugo build page?
2. Template đọc đúng key (`$data.overview.total_posts` vs key cũ)?
3. Workflow có `paths-ignore` khiến data không commit?
4. Chạy Content Direction **sau** deploy (tránh race).

## Optimizer / metadata fail

- Description trùng key, quote hỏng, YAML multiline vỡ.
- `seo_title` chứa ký tự/colon không quote.
- Autobot ghi đè front matter không round-trip được.

**Fix:** parse → validate → write; dry-run trên 1 file; không batch 100 file khi parser đang gãy.

Liên hệ: [YAML/Hugo](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).