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
date: '2026-07-10 11:50:00+07:00'
description: Gom hugo_build_error, deploy_not_completed, template_or_render_regression,
  ai_summary_map_artifact, table_layout_ux_regression, duplicate_yaml_keys — cách
  đọc log assemble và fix an toàn.
draft: false
image: images/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression.webp
image_alt: 'Ảnh minh họa Hugo build error: duplicate YAML, ai_summary map[], template
  regression và deploy không complete — nguồn Pexels'
image_attribution_checked_at: '2026-07-10T04:52:58+07:00'
image_attribution_source: pexels_api
image_attribution_verified: true
image_commercial_use: true
image_creator: Stanislav Kondratiev
image_creator_id: ''
image_creator_url: https://www.pexels.com/@technobulka
image_generation_method: context_aware_programmatic_pillow
image_license: Pexels License
image_license_url: ''
image_owner: external
image_provider: pexels
image_query: hugo build error duplicate yaml
image_source: Pexels
image_source_url: https://www.pexels.com/photo/screen-with-code-10816120/
image_status: verified
related_posts:
- ci-cd-root-cause-playbook-safe-vs-unsafe-autofix
- baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi
- content-direction-empty-report-va-optimizer-frontmatter
series: ci-cd-root-cause-lessons
series_order: 11
series_title: CI/CD Root Cause Lessons
slug: hugo-build-duplicate-yaml-ai-summary-va-template-regression
tags:
- Hugo
- YAML
- ai_summary
- template
- CI/CD
- duplicate keys
thumbnail: images/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression.webp
title: 'Hugo build error: duplicate YAML, ai_summary map[], template regression và
  deploy không complete'
---

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `hugo_build_error` | **unsafe** | Build/render fail — cần đọc log, không đoán |
| `deploy_not_completed` | **unsafe** | Workflow deploy không complete |
| `template_or_render_regression` | **unsafe** | Layout/partial gãy |
| `ai_summary_map_artifact` | safe | `ai_summary` chứa artifact `map[]` / items không phải list |
| `table_layout_ux_regression` | safe | Bảng quá rộng / scroll desktop kém |
| `duplicate_yaml_keys` | safe | Trùng key front matter (`description:` hai lần…) |

![Gallery lỗi assemble: duplicate key và map artifact](/images/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression-diagram.webp)

## Case: `mapping key "description" already defined`

```yaml
description: "Một mô tả..."
description: "Một mô tả..."  # ← Hugo assemble chết
```

**Fix safe:** dedupe giữ key đầu; cấm script "quote description" append thêm dòng.

## Case: `range can't iterate over` ai_summary

`items` bị dump thành **string JSON** thay vì list YAML → template `range` fail.  
**Fix:** `normalize_ai_summaries.py` coerce JSON string → list string sạch.

## Case: template regression

Đổi partial `ai-summary.html` / `seo.html` làm vỡ toàn site.  
**Fix:** test `hugo --minify` local; QA chỉ assert feature đổi; snapshot HTML tối thiểu.

## Case: table UX

Bảng wide trong article: bọc container scroll, giới hạn width token CSS (`--article-table-width`).

## deploy_not_completed

Job cancel giữa chừng (fan-out) hoặc fail step sớm. Xem concurrency + log step đỏ — đừng mark "fixed" khi chưa có artifact Pages mới.

Liên hệ: [QA scope](/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi/), [Content Direction](/posts/content-direction-empty-report-va-optimizer-frontmatter/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).