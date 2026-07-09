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
date: "2026-07-10 04:35:00+07:00"
description: 'Hướng dẫn date_only_or_wrong_timezone (safe): luôn gắn +07:00, không
  dùng date-only UTC khiến QA STALE_DATE và thứ tự bài sai.'
draft: false
image: "images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date.webp"
image_alt: "Ảnh minh họa — Pexels / Daniil Komov"
image_attribution_checked_at: '2026-07-10T04:53:00+07:00'
image_attribution_source: "pexels_api"
image_attribution_verified: true
image_commercial_use: true
image_creator: "Daniil Komov"
image_creator_id: "133960344"
image_creator_url: "https://www.pexels.com/@dkomov"
image_license: "Pexels License"
image_license_url: "https://www.pexels.com/license/"
image_owner: "external"
image_provider: "pexels"
image_query: post date timezone việt nam
image_source: "Pexels"
image_source_url: "https://www.pexels.com/photo/laptop-with-code-displayed-and-coffee-mug-nearby-34803976/"
image_status: "verified"
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- hugo-build-duplicate-yaml-ai-summary-va-template-regression
- content-direction-empty-report-va-optimizer-frontmatter
series: ci-cd-root-cause-lessons
series_order: 7
series_title: CI/CD Root Cause Lessons
slug: post-date-timezone-vietnam-gmt7-tranh-stale-date
tags:
- timezone
- Vietnam
- front matter
- Hugo
- safe
thumbnail: "images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date.webp"
title: 'Post date timezone Việt Nam (GMT+7): tránh stale_date và lệch homepage'
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `date_only_or_wrong_timezone` | **safe** | Date thiếu timezone hoặc stamp UTC thay vì giờ Việt Nam |

Safe vì có thể chuẩn hóa bằng script (`qa_dates.py --fix-obvious`) khi quy tắc rõ.

![So sánh date UTC vs GMT+7 trong front matter](/images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date-diagram.webp)

## Pattern sai / đúng

```yaml
# SAI — date-only, parser coi UTC midnight
date: 2026-07-10

# SAI — có giờ nhưng không offset
date: 2026-07-10 09:00:00

# ĐÚNG — giờ Việt Nam
date: "2026-07-10 04:33:00+07:00"
```

## Hậu quả

- QA `STALE_DATE`: date "ngày hôm qua" so với ngày tạo file theo VN.
- Homepage sort lệch buổi tối/sáng.
- Content Direction đánh giá freshness sai.

## Fix

- Chuẩn hóa toàn bộ front matter sang `+07:00`.
- Generator/autobot luôn dùng `now_vietnam()` thay vì `datetime.utcnow()`.
- CI chỉ fail date trên **file trong diff**, không quét 150 bài mỗi PR UI.

Xem: [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/), [Hugo YAML](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/).