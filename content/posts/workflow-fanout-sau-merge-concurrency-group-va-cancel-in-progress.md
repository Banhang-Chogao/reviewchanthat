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
date: '2026-07-10 04:20:00+07:00'
description: 'Phân tích workflow_fanout (safe): một merge kích hoạt deploy + content-direction
  + snapshot + autofix — cách thiết kế concurrency để không tự DDoS pipeline.'
draft: false
image: images/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress.webp
image_alt: 'Ảnh minh họa Workflow fan-out sau merge: concurrency group, cancel-in-progress
  và vòng autofix — nguồn Pexels'
image_attribution_checked_at: '2026-07-10T06:15:17+07:00'
image_attribution_source: pexels_api
image_attribution_verified: true
image_commercial_use: true
image_creator: Christina Morillo
image_creator_id: '473730'
image_creator_url: https://www.pexels.com/@divinetechygirl
image_license: Pexels License
image_license_url: https://www.pexels.com/license/
image_owner: external
image_provider: pexels
image_query: workflow fan-out sau merge concurrency
image_source: Pexels
image_source_url: https://www.pexels.com/photo/white-dry-erase-board-with-red-diagram-1181311/
image_status: verified
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- github-api-va-pages-rate-limit-cach-doc-va-giam-tai
- live-deploy-khong-phan-anh-va-pages-serving-old-artifact
seo_title: 'Workflow fan-out sau merge: concurrency group'
series: ci-cd-root-cause-lessons
series_order: 4
series_title: CI/CD Root Cause Lessons
slug: workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress
tags:
- workflow fanout
- concurrency
- GitHub Actions
- CI/CD
- safe
thumbnail: images/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress.webp
title: 'Workflow fan-out sau merge: concurrency group, cancel-in-progress và vòng
  autofix'
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `workflow_fanout` | **safe** | Một merge/fan-out thành deploy + content-direction + doctor + autofix lặp |

Safe vì **có thể sửa bằng config workflow** (concurrency, `paths-ignore`, tách trigger) mà không đụng nội dung bài viết.

![Một merge kích hoạt nhiều workflow song song](/images/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress-diagram.webp)

## Vì sao nguy hiểm nếu bỏ mặc

- Tốn runner → dễ dính `runner_capacity_delay` và rate limit.
- Autofix fail → trigger lại deploy → vòng lặp.
- Content Direction chạy **trước** khi Pages xong → report lệch live.

## Pattern khuyến nghị

```yaml
concurrency:
  group: pages
  cancel-in-progress: false   # deploy: không hủy giữa chừng
```

```yaml
concurrency:
  group: content-direction
  cancel-in-progress: true    # report: job mới thay job cũ
```

- `paths-ignore` cho bot-only data (`reports/**`, dashboard JSON) để bot không tự deploy lại.
- Thứ tự: **Deploy Pages xong → Content Direction** (đúng rule vận hành blog).
- Autofix-on-deploy-fail: chỉ commit khi thực sự sửa được; tránh commit rỗng.

## Checklist PR workflow

- [ ] Có concurrency group theo loại job?
- [ ] Bot data có `paths-ignore` khỏi deploy?
- [ ] Autofix có điều kiện `if: failure()` và whitelist root cause?
- [ ] Có giới hạn `max-parallel` cho matrix?

Đọc tiếp: [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/), [Rate limit](/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai/).