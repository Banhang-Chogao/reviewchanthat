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
date: "2026-07-10 04:25:00+07:00"
description: 'Phân tích baseline_debt_blocking_unrelated_deploy (unsafe) và qa_expectation_mismatch
  (safe): nợ QA/image cũ fail full-site, chặn PR không liên quan — cách scope QA theo
  feature.'
draft: false
image: images/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi.webp
image_alt: 'Ảnh minh họa Baseline debt chặn deploy và QA scope: chỉ bắt tính năng
  mới — nguồn Pexels'
image_attribution_checked_at: '2026-07-10T04:52:56+07:00'
image_attribution_source: pexels_api
image_attribution_verified: true
image_commercial_use: true
image_creator: Monstera Production
image_creator_id: ''
image_creator_url: https://www.pexels.com/@gabby-k
image_generation_method: context_aware_programmatic_pillow
image_license: Pexels License
image_license_url: ''
image_owner: external
image_provider: pexels
image_query: baseline debt chặn deploy qa
image_source: Pexels
image_source_url: https://www.pexels.com/photo/illustration-with-hands-of-debtor-with-tied-hands-6289036/
image_status: verified
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url
- hugo-build-duplicate-yaml-ai-summary-va-template-regression
series: ci-cd-root-cause-lessons
series_order: 5
series_title: CI/CD Root Cause Lessons
slug: baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi
tags:
- QA
- baseline debt
- CI/CD
- GitHub Pages
- unsafe
thumbnail: images/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi.webp
title: 'Baseline debt chặn deploy và QA scope: chỉ bắt tính năng mới'
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `baseline_debt_blocking_unrelated_deploy` | **unsafe** | Nợ QA/image cũ fail full-site, chặn deploy feature mới |
| `qa_expectation_mismatch` | **safe** | QA kỳ vọng footer/element mà product đã cố ý gỡ |

Rule vận hành blog: **khi ship tính năng mới, QA chỉ bắt tính năng đó** — không quét toàn site gây fail không cần thiết.

![Full-site QA vs feature-scoped QA](/images/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi-diagram.webp)

## Case thật: đổi màu branding bị chặn

PR chỉ đụng `main.css` + branding layout nhưng pipeline fail vì:

- `normalize_ai_summaries` parse fail trên post cũ
- duplicate `description:` ở bài travel
- post thiếu hero từ tuần trước

Kết quả: **UI xanh không lên live** dù diff không liên quan content.

## Cách làm đúng

1. **QA path filter:** chỉ lint/test file trong diff (`git diff --name-only`).
2. Tách **gate cứng** (build Hugo, link critical) khỏi **debt report** (image audit toàn site → không fail deploy).
3. `continue-on-error` có chọn lọc cho debt, **không** cho Hugo assemble error thật.
4. Baseline debt có ticket/autofix riêng — không gánh trên PR branding.

## qa_expectation_mismatch

Khi product gỡ footer AdSense/macro cũ, QA vẫn assert selector → fail. Fix: cập nhật test cho khớp product, không "thêm lại UI chỉ để test xanh".

Xem thêm: [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/), [Image pipeline](/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url/).