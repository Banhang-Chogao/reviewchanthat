+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:10:00+07:00"
commit = "45c0695c"
description = "Khi job CI đỏ vì GitHub-hosted runner thiếu capacity hoặc platform incident chứ không phải bug code, và cách phân biệt để không autofix nhầm."
draft = false
noindex = true
image = "images/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code.webp"
image_alt = "Ảnh minh họa Runner capacity delay và platform incident: khi job đỏ không phải vì bug code — nguồn Pixabay"
image_attribution_checked_at = "2026-07-11T17:30:32+07:00"
image_attribution_source = "pixabay_manifest"
image_attribution_verified = true
image_commercial_use = true
image_creator = "HeckiMG"
image_creator_id = ""
image_creator_url = "https://pixabay.com/photos/wooden-bench-seat-sea-ocean-water-7110299/"
image_license = "Pixabay Content License"
image_license_url = "https://pixabay.com/service/license-summary/"
image_owner = "external"
image_provider = "pixabay"
image_query = "runner capacity delay platform incident"
image_source = "Pixabay"
image_source_url = "https://pixabay.com/photos/wooden-bench-seat-sea-ocean-water-7110299/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "github-api-va-pages-rate-limit-cach-doc-va-giam-tai", "live-deploy-khong-phan-anh-va-pages-serving-old-artifact"]
seo_title = "Runner capacity delay và platform incident: khi job đỏ không"
series = "ci-cd-root-cause-lessons"
series_order = 2
series_title = "CI/CD Root Cause Lessons"
slug = "github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code"
tags = ["GitHub Actions", "runner", "platform incident", "CI/CD", "unsafe"]
thumbnail = "images/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code.webp"
title = "Runner capacity delay và platform incident: khi job đỏ không phải vì bug code"
date_display = "10-07-2026 04:10:00 GMT +7"

[ai_summary]
collapsed = false
disclaimer = "Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi repo cần điều chỉnh policy theo rủi ro riêng."
enabled = true
items = ["Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).", "Nhiều failure không phải bug code: runner queue, platform incident, rate limit, Pages CDN lag.", "Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng feature không."]
title = "Tóm tắt nhanh"

[[faq]]
question = "Hỏi: Làm sao phân biệt runner delay và script hang?"
answer = "Trả lời: Script hang thường đã qua Checkout/Setup, log có timestamp step. Runner delay: chưa có step nào chạy."

[[faq]]
question = "Hỏi: Self-hosted runner có phải lời giải?"
answer = "Trả lời: Có thể cho team lớn; với blog cá nhân/gh-pages tradeoff vận hành cao. Ưu tiên giảm fan-out trước."

[[faq]]
question = "Hỏi: Incident 9/7/2026 học được gì?"
answer = "Trả lời: Document trong series CI — verify bằng status + build-info, không đổ lỗi content random."

[[faq]]
question = "Hỏi: Doctor có được mở PR “fix delay”?"
answer = "Trả lời: Không. Pattern unsafe: chỉ quan sát, alert, có thể tạm disable bot gây queue."
+++

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `runner_capacity_delay` | **unsafe** | GitHub-hosted runner thiếu capacity; job chờ lâu trước khi start |
| `external_platform_incident` | **unsafe** | Incident GitHub Actions/Pages (start delays, degraded availability) |

Hai lỗi này **không nên kích hoạt autofix code**. Không có diff nào trong repo sửa được việc runner toàn cầu đang full.

![Sơ đồ queued job vs failed step: platform delay không qua checkout](/images/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code-diagram.webp)

## Dấu hiệu nhận biết

1. Workflow **Queued / Waiting for a runner** hàng chục phút.
2. Log **không có** step `Checkout` / `Setup Hugo` — job chưa chạy.
3. GitHub Status báo degraded Actions/Pages (ví dụ sự cố 9/7/2026).
4. Cùng lúc nhiều repo khác cũng queue — gợi ý platform, không phải 1 commit.

## Việc nên làm

- Đọc [GitHub Status](https://www.githubstatus.com/).
- **Không** push commit rỗng "để kích deploy".
- Bật concurrency `cancel-in-progress` để job mới không xếp hàng vô hạn sau recovery.
- Retry **có kiểm soát** sau khi status xanh; hủy run cũ còn kẹt.
- Ghi nhận trong Deployment Doctor là *unsafe external* — chỉ report.

## Việc không nên làm

- Hotfix content/CSS "cho có thay đổi".
- Tắt toàn bộ QA vì "deploy không lên".
- Force merge khi chưa có evidence job từng chạy build.

## Liên hệ bài trụ

Xem taxonomy full: [CI/CD Root Cause Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).

Khi runner đã start mà fail ở Hugo/YAML → chuyển sang [Hugo build & YAML](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/).
<!-- thin-expand:v1 -->

## So sánh queued vs failed step

| Triệu chứng | Job đã start? | Hướng xử lý |
|-------------|---------------|-------------|
| Waiting for runner 40 phút | Chưa | Platform capacity — chờ/status |
| Fail tại step test sau 2 phút | Rồi | Đọc log — có thể bug code |
| Mọi repo đều queue | Chưa | Incident rộng |
| Chỉ 1 workflow queue | Chưa | Có thể concurrency group no-op / label runner |

**Không** có patch trong `content/` hay `layouts/` sửa được việc GitHub hết runner.

## Việc nên / không nên

**Nên:** đọc [GitHub Status](https://www.githubstatus.com/); hủy run kẹt; bật concurrency hợp lý; retry sau khi status xanh; ghi Doctor *unsafe*.

**Không nên:** push commit rỗng “để kích”; autofix front matter; force-push; spam `workflow_dispatch` 20 lần (dễ dính rate limit).

## Checklist khi queue bất thường

1. Mở githubstatus.com  
2. Xem job đã có step chưa  
3. So multi-repo  
4. Không commit rỗng  
5. Giảm fan-out nếu đang bão  
6. Retry có kiểm soát sau recovery
