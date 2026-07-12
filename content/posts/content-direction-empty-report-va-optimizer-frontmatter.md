+++
noindex = true
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:40:00+07:00"
commit = "b6fb0a55"
description = "| Code | Safety | Mô tả | |------|--------|--------| | contentdirectionemptyreport | safe | Dashboard/report render rỗng (sai path/key/fallback) | |"
draft = false
image = "images/posts/content-direction-empty-report-va-optimizer-frontmatter.webp"
image_alt = "Ảnh minh họa Content Direction empty report và optimizer fail vì front matter — nguồn Pexels"
image_attribution_checked_at = "2026-07-11T17:30:32+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Lukas Blazek"
image_creator_id = "89898"
image_creator_url = "https://www.pexels.com/@goumbik"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "content direction empty report optimizer"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/person-holding-pen-pointing-at-graph-590020/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "post-date-timezone-vietnam-gmt7-tranh-stale-date", "hugo-build-duplicate-yaml-ai-summary-va-template-regression"]
seo_title = "Content Direction empty report và optimizer fail vì front"
series = "ci-cd-root-cause-lessons"
series_order = 8
series_title = "CI/CD Root Cause Lessons"
slug = "content-direction-empty-report-va-optimizer-frontmatter"
tags = ["Content Direction", "SEO", "front matter", "optimizer", "safe"]
thumbnail = "images/posts/content-direction-empty-report-va-optimizer-frontmatter.webp"
title = "Content Direction empty report và optimizer fail vì front matter"
date_display = "10-07-2026 04:40:00 GMT +7"

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
<!-- thin-expand:v1 -->

## So sánh empty report vs optimizer fail

| Hiện tượng | Nguyên nhân hay gặp | Safe fix? |
|------------|---------------------|-----------|
| Dashboard trống | JSON chưa generate / sai path template | Có — path & order job |
| Report JSON `{}` | Script crash sớm / exception nuốt | Có — đọc log, sửa script |
| Optimizer fail 1 file | Front matter vỡ (duplicate key, quote) | Có — sửa file đó |
| Metadata SEO fail hàng loạt | Autobot write không round-trip | Có — dry-run + normalize |

Empty UI **không** luôn nghĩa là “không có bài”. Hay gặp hơn: data không được copy vào `data/` trước Hugo, hoặc partial đọc key cũ sau khi schema đổi.

## Checklist khôi phục dashboard

1. Chạy local: `python scripts/content_direction.py` → có file JSON/MD trong `data/` và `reports/`.
2. So key template với schema hiện tại (`total_posts`, nested paths…).
3. Workflow: generate **trước** `hugo`, hoặc commit data nếu site đọc từ git.
4. Tránh race: Content Direction **sau** deploy live (rule vận hành).
5. `paths-ignore` bot data: đừng để bot tự trigger deploy loop — xem [fan-out](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/).

## FAQ

**Hỏi: Optimizer có được tự merge khi fail một bài?**  
Trả lời: Không batch “cứ chạy tiếp” che lỗi parse. Fail fast trên file lỗi; sửa front matter rồi chạy lại.

**Hỏi: Có liên quan thin posts?**  
Trả lời: Có gián tiếp — Content Direction đo word count và action “Mở rộng thin posts”. Report rỗng thì action P0 cũng biến mất khỏi dashboard dù debt vẫn còn.

**Hỏi: Sửa front matter tay hay script?**  
Trả lời: Script khi pattern rõ (duplicate key, AI summary map). Tay khi nội dung SEO cần biên tập. Luôn `rule.py`/normalize sau.

**Hỏi: Làm sao tránh tái phát?**  
Trả lời: Fixture test 1 post YAML/TOML tối thiểu trong CI; dry-run optimizer trên PR chỉ đụng content.
