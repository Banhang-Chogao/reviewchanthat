+++
noindex = true
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:15:00+07:00"
commit = "0ee71da6"
description = "Hướng dẫn xử lý github_rate_limit và github_pages_rate_limit (unsafe): nhận diện 403/429, backoff, gom API call, tránh spam publish Pages."
draft = false
image = "images/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai.webp"
image_alt = "Ảnh minh họa GitHub API rate limit và Pages rate limit: đọc log, backoff, giảm fan-out — nguồn Pexels"
image_attribution_checked_at = "2026-07-11T17:30:32+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "RealToughCandy.com"
image_creator_id = "2238606"
image_creator_url = "https://www.pexels.com/@realtoughcandy"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "github api rate limit pages"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/person-holding-a-black-and-white-paper-with-message-11035544/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code", "workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress"]
seo_title = "GitHub API rate limit và Pages rate limit: đọc log, backoff"
series = "ci-cd-root-cause-lessons"
series_order = 3
series_title = "CI/CD Root Cause Lessons"
slug = "github-api-va-pages-rate-limit-cach-doc-va-giam-tai"
tags = ["GitHub API", "rate limit", "GitHub Pages", "CI/CD", "unsafe"]
thumbnail = "images/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai.webp"
title = "GitHub API rate limit và Pages rate limit: đọc log, backoff, giảm fan-out"
date_display = "10-07-2026 04:15:00 GMT +7"

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
| `github_rate_limit` | **unsafe** | REST/GraphQL API chạm hạn mức |
| `github_pages_rate_limit` | **unsafe** | Publish/build Pages bị throttle |

Đây là **ràng buộc nền tảng**. Script càng "chăm" gọi API (doctor, autofix, content bots) càng dễ tự bắn vào rate limit.

![Minh họa throttle API và cửa sổ backoff](/images/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai-diagram.webp)

## Dấu hiệu

- HTTP **403/429** kèm header `X-RateLimit-Remaining: 0`.
- Log: `API rate limit exceeded` / `secondary rate limit`.
- Pages: publish fail dù artifact build local OK.
- Nhiều workflow song song cùng `gh api` / `actions/github-script`.

## Cách xử lý an toàn

1. **Dừng fan-out** tạm thời: disable bot không cần thiết trong cửa sổ nóng.
2. **Backoff + jitter** khi retry; không retry 1s một lần.
3. Cache kết quả `gh run list` / GraphQL trong job thay vì gọi lặp.
4. Gộp bước: một job collect log thay vì 5 job song song.
5. Với Pages rate limit: chờ cửa sổ reset; xác minh bằng `build-info.json` sau khi publish được.

## Liên hệ

Fan-out làm nặng rate limit: [Workflow fan-out](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/).  
Playbook: [Root cause playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).
<!-- thin-expand:v1 -->

## So sánh loại limit

| Loại | Dấu hiệu | Có fix bằng code repo? |
|------|----------|-------------------------|
| Primary REST rate limit | 403 + Remaining 0 | Giảm gọi, cache, PAT hợp lý |
| Secondary rate limit | 403/429 “secondary” | Backoff mạnh, bớt parallel |
| Pages publish throttle | Publish fail dù build OK | Chờ cửa sổ; giảm spam deploy |
| Runner queue (khác limit API) | Queued lâu, chưa checkout | Platform capacity |

Nhầm secondary limit với “bug script” dẫn tới retry càng dày → càng bị khóa.

## Cách giảm tải thực tế trên blog

1. Gộp collect log Deployment Doctor thành **một** job.
2. Cache `gh run list` trong step thay vì mỗi script tự gọi.
3. Nightly bots staggered (không cùng phút).
4. Tắt tạm bot không critical khi đang nóng rate limit.
5. Sau publish: verify bằng `build-info.json`, không redeploy “cho chắc” 10 lần.

## FAQ

**Hỏi: Dùng PAT riêng có hết rate limit?**  
Trả lời: Tăng trần theo account/app, **không** vô hạn. Vẫn cần backoff và giảm fan-out.

**Hỏi: GraphQL có “rẻ” hơn REST?**  
Trả lời: Có thể lấy nhiều field một request — tốt nếu thiết kế query gọn. Lạm dụng vẫn cháy quota.

**Hỏi: Khi nào coi là unsafe autofix?**  
Trả lời: Khi root cause là platform throttle — **không** sinh commit “sửa code” giả. Ghi Doctor knowledge: unsafe.

**Hỏi: Liên hệ fan-out?**  
Trả lời: Trực tiếp — xem [workflow fan-out](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/). Một merge 6 workflow × nhiều `gh api` = công thức 429.

## Checklist khi log có 429

1. Đọc header reset time.
2. Dừng bot không cần.
3. Backoff + jitter.
4. Xác minh Pages bằng build-info sau khi hết cửa sổ.
5. Chỉ bật lại fan-out khi Remaining ổn định.
