+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:05:00+07:00"
description = "Khi một blog tĩnh (Hugo) publish qua GitHub Actions + GitHub Pages, màn hình đỏ không tự nói \"đây là bug code\". Nhiều lần job fail vì runner chưa kịp start, API"
draft = false
image = "images/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix.webp"
image_alt = "Ảnh minh họa CI/CD Root Cause Playbook: safe vs unsafe autofix cho blog Hugo trên GitHub Pages — nguồn Pexels"
image_attribution_checked_at = "2026-07-10T14:01:38+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Zulfugar Karimov"
image_creator_id = "2150928041"
image_creator_url = "https://www.pexels.com/@zulfugarkarimov"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "ci cd root cause playbook"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/person-holding-a-reflective-cd-disc-in-hand-37028744/"
image_status = "verified"
related_posts = ["github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code", "github-api-va-pages-rate-limit-cach-doc-va-giam-tai", "workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress", "baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi", "image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url", "post-date-timezone-vietnam-gmt7-tranh-stale-date", "content-direction-empty-report-va-optimizer-frontmatter", "live-deploy-khong-phan-anh-va-pages-serving-old-artifact", "baseurl-sitemap-noindex-va-series-hardcoded-url", "hugo-build-duplicate-yaml-ai-summary-va-template-regression", "deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix"]
seo_title = "CI/CD Root Cause Playbook: safe vs unsafe autofix cho blog"
series = "ci-cd-root-cause-lessons"
series_order = 1
series_title = "CI/CD Root Cause Lessons"
slug = "ci-cd-root-cause-playbook-safe-vs-unsafe-autofix"
tags = ["CI/CD", "GitHub Actions", "GitHub Pages", "root cause", "autofix", "Deployment Doctor", "Hugo", "DevOps"]
thumbnail = "images/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix.webp"
title = "CI/CD Root Cause Playbook: safe vs unsafe autofix cho blog Hugo trên GitHub Pages"
date_display = "10-07-2026 04:05:00 GMT +7"

[ai_summary]
collapsed = false
disclaimer = "Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi repo cần điều chỉnh policy theo rủi ro riêng."
enabled = true
items = ["Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).", "Nhiều failure không phải bug code: runner queue, platform incident, rate limit, Pages CDN lag.", "Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng feature không."]
title = "Tóm tắt nhanh"
+++

## Vì sao cần playbook root cause?

Khi một blog tĩnh (Hugo) publish qua GitHub Actions + GitHub Pages, màn hình đỏ không tự nói "đây là bug code". Nhiều lần job fail vì **runner chưa kịp start**, **API rate limit**, **QA full-site bắt nợ cũ**, hoặc **front matter YAML trùng key**. Nếu team luôn "hotfix code" mỗi khi đỏ, sẽ tạo thêm fan-out workflow, làm Pages lag, và nợ kỹ thuật phình ra.

Bài trụ này gom **taxonomy** các root cause đã học được khi vận hành Review Chân Thật: cái nào **safe** (được autofix / script sửa), cái nào **unsafe** (chỉ quan sát, retry, hoặc sửa tay có kiểm soát). Mười bài vệ tinh đi sâu từng cụm lỗi.

![Bản đồ taxonomy root cause CI/CD: platform, content, build, live](/images/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix-diagram.webp)

## Safe vs unsafe: quy tắc vàng

| Nhãn | Ý nghĩa vận hành | Ví dụ |
|------|------------------|--------|
| **safe** | Có thể autofix hoặc script hóa với blast radius nhỏ | `duplicate_yaml_keys`, `workflow_fanout`, `date_only_or_wrong_timezone` |
| **unsafe** | Không được "sửa code mù"; cần chờ platform, đổi policy, hoặc review tay | `runner_capacity_delay`, `github_rate_limit`, `baseline_debt_blocking_unrelated_deploy`, `hugo_build_error` |

**Unsafe không có nghĩa là "bỏ qua".** Unsafe nghĩa là: *đừng tạo PR ngẫu nhiên*, *đừng force-push production*, *đừng để autofix spam*. Hãy log, classify, và có action có chủ đích.

## Bản đồ 4 vùng lỗi

### 1) Platform & capacity (thường unsafe)
- `runner_capacity_delay` — job kẹt queue hosted runner
- `external_platform_incident` — GitHub Actions/Pages degraded
- `github_rate_limit` / `github_pages_rate_limit` — API/Pages publish throttle

→ Chi tiết: [Runner delay & platform incident](/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code/), [Rate limit](/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai/)

### 2) Orchestration & QA policy (safe/unsafe tùy case)
- `workflow_fanout` (safe) — một merge kích hoạt quá nhiều workflow
- `baseline_debt_blocking_unrelated_deploy` (unsafe) — QA full-site chặn feature không liên quan

→ [Workflow fan-out](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/), [Baseline debt & QA scope](/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi/)

### 3) Content & image pipeline (safe, trừ fake creator)
- Hero thiếu, self-owned URL, creator rỗng hợp lệ, creator giả (fatal)
- Date thiếu timezone / UTC nhầm GMT+7
- Content Direction empty / optimizer fail

→ [Image pipeline](/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url/), [Timezone VN](/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date/), [Content Direction](/posts/content-direction-empty-report-va-optimizer-frontmatter/)

### 4) Build, routing & live verification
- Hugo assemble: duplicate YAML, `map[]` ai_summary, template regression
- Live SHA không khớp artifact; baseURL/sitemap/series path sai

→ [Live vs Pages artifact](/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact/), [BaseURL & sitemap](/posts/baseurl-sitemap-noindex-va-series-hardcoded-url/), [Hugo build & YAML](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/)

## Checklist 90 giây khi thấy đỏ

1. **Job đã start step chưa?** Nếu vẫn *Queued* → nghi platform/runner, không sửa content.
2. **Log line đầu tiên fail ở đâu?** `Normalize AI summaries` / `Hugo build` / `QA` / `Upload Pages`?
3. **Có duplicate key / YAML parse?** → chạy dedupe front matter (safe).
4. **Fail có phải file vừa đổi không?** Nếu fail ở post 6 tháng trước → baseline debt, thu hẹp QA scope.
5. **Deploy success nhưng site cũ?** Đọc `build-info.json` so SHA — có thể CDN/Pages lag.
6. **Safe hay unsafe?** Chỉ autofix khi root cause nằm whitelist safe.

## Bài học hệ thống (không chỉ "sửa 1 file")

- **Classify trước, patch sau.** Deployment Doctor hữu ích vì nó tách *safe autofix* khỏi *unsafe external*.
- **QA theo feature khi ship UI.** Full-site image/date debt không được chặn PR đổi màu CSS.
- **Thứ tự pipeline:** GitHub Pages deploy xong rồi mới Content Direction (tránh race + fan-out).
- **Front matter là API của build.** Duplicate `description:`, `ai_summary.items` dạng string JSON, date thiếu `+07:00` — đều là "code" dù nằm trong markdown.
- **Live verification bắt buộc:** `build-info.json` + CSS fingerprint + 1 URL feature.

## Bộ 10 bài vệ tinh

1. [Runner delay & platform incident](/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code/)
2. [GitHub API & Pages rate limit](/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai/)
3. [Workflow fan-out & concurrency](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/)
4. [Baseline debt & QA scope](/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi/)
5. [Image pipeline: hero, creator, self-owned](/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url/)
6. [Timezone Việt Nam cho post date](/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date/)
7. [Content Direction empty & optimizer](/posts/content-direction-empty-report-va-optimizer-frontmatter/)
8. [Live deploy không phản ánh / old artifact](/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact/)
9. [BaseURL, sitemap noindex, series URL](/posts/baseurl-sitemap-noindex-va-series-hardcoded-url/)
10. [Hugo build, YAML trùng, AI summary map[]](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/)

## Kết luận

Playbook root cause không thay thế kỹ năng debug, nhưng **ngăn phản xạ sai**: sửa code khi platform đang chậm, hoặc nới QA toàn site mỗi lần fail. Gắn nhãn **safe/unsafe** giúp bot autofix hữu ích thay vì nguy hiểm. Đọc tiếp các bài vệ tinh theo đúng loại log bạn đang thấy.

> Liên quan: [Deployment Doctor](/posts/deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix/), [Workflow failures audit](/posts/workflow-failures-audit-recent-ci-cd-root-causes-action-items/), [GitHub Actions delays July 9](/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection/).