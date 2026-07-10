+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:10:00+07:00"
description = "| Code | Safety | Mô tả | |------|--------|--------| | runnercapacitydelay | unsafe | GitHub-hosted runner thiếu capacity; job chờ lâu trước khi start | |"
draft = false
image = "images/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code.webp"
image_alt = "Ảnh minh họa Runner capacity delay và platform incident: khi job đỏ không phải vì bug code — nguồn Pixabay"
image_attribution_checked_at = "2026-07-10T14:01:38+07:00"
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