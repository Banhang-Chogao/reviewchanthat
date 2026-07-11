+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:55:00+07:00"
commit = "f8496fd"
description = "| Code | Safety | Mô tả | |------|--------|--------| | hugobuilderror | unsafe | Build/render fail — cần đọc log, không đoán | | deploynotcompleted | unsafe |"
draft = false
image = "images/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression.webp"
image_alt = "Ảnh minh họa Hugo build error: duplicate YAML, ai_summary map[], template regression và deploy không complete — nguồn Pexels"
image_attribution_checked_at = "2026-07-11T16:20:34+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Stanislav Kondratiev"
image_creator_id = "1497515"
image_creator_url = "https://www.pexels.com/@technobulka"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "hugo build error duplicate yaml"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/screen-with-code-10816120/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi", "content-direction-empty-report-va-optimizer-frontmatter"]
seo_title = "Hugo build error: duplicate YAML, ai_summary map[], template"
series = "ci-cd-root-cause-lessons"
series_order = 11
series_title = "CI/CD Root Cause Lessons"
slug = "hugo-build-duplicate-yaml-ai-summary-va-template-regression"
tags = ["Hugo", "YAML", "ai_summary", "template", "CI/CD", "duplicate keys"]
thumbnail = "images/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression.webp"
title = "Hugo build error: duplicate YAML, ai_summary map[], template regression và deploy không complete"
date_display = "10-07-2026 04:55:00 GMT +7"

[ai_summary]
collapsed = false
disclaimer = "Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi repo cần điều chỉnh policy theo rủi ro riêng."
enabled = true
items = ["Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).", "Nhiều failure không phải bug code: runner queue, platform incident, rate limit, Pages CDN lag.", "Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng feature không."]
title = "Tóm tắt nhanh"
+++

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
<!-- thin-expand:v1 -->

## So sánh lớp lỗi build

| Lỗi | Giai đoạn | Safe autofix? |
|-----|-----------|---------------|
| Duplicate YAML/TOML key | Assemble | Có — dedupe |
| `ai_summary` map/string | Render template | Có — normalize |
| Partial nil pointer | Render | Thường **không** đoán — đọc stack |
| Minify/assets | Post-render | Tùy |
| Deploy not completed | Actions | Unsafe nếu platform |

Nguyên tắc: **đọc log Hugo**, không đoán “chắc do cache”.

## Case study ngắn

1. **Duplicate `description`:** script SEO append dòng mới thay vì replace → assemble die. Fix: một key duy nhất.
2. **`range` ai_summary:** items thành JSON string → normalize list string.
3. **Partial AI summary đổi cấu trúc:** thiếu `with`/`default` → nil. Fix template + fixture.
4. **Bảng quá rộng:** UX safe fix CSS scroll; không phải build-breaker nhưng Doctor có thể gắn `table_layout_ux_regression`.

## FAQ

**Hỏi: Local `hugo` xanh, CI đỏ?**  
Trả lời: Khác version Hugo extended, khác env `GA_MEASUREMENT_ID`, hoặc CI có step normalize trước build. So version trong workflow.

**Hỏi: TOML có duplicate key không?**  
Trả lời: Parser khác YAML; vẫn tránh hai `draft =` / field lặp. `rule.py` dump lại front matter giúp canonical.

**Hỏi: Có nên `continue-on-error` trên Hugo build?**  
Trả lời: **Không.** Build fail = không publish. Debt khác (image audit full site) mới tách report.

**Hỏi: Liên quan Content Direction optimizer?**  
Trả lời: Optimizer ghi front matter hỏng → build/render fail. Dry-run + normalize trước batch.

## Checklist sau khi đụng template

1. `hugo --minify` local cùng version CI.
2. Mở 1 trang post + homepage + series.
3. Trang có `ai_summary` và trang không có.
4. Không introduce absolute path gãy baseURL.
