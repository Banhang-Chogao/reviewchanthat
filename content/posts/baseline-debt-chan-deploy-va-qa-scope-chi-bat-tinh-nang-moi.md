+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:25:00+07:00"
commit = "9008aff"
description = "| Code | Safety | Mô tả | |------|--------|--------| | baselinedebtblockingunrelateddeploy | unsafe | Nợ QA/image cũ fail full-site, chặn deploy feature mới | |"
draft = false
image = "images/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi.webp"
image_alt = "Ảnh minh họa Baseline debt chặn deploy và QA scope: chỉ bắt tính năng mới — nguồn Pexels"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Monstera Production"
image_creator_id = "3372733"
image_creator_url = "https://www.pexels.com/@gabby-k"
image_license = "Pexels License"
image_license_url = ""
image_owner = "external"
image_provider = "pexels"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/illustration-with-hands-of-debtor-with-tied-hands-6289036/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url", "hugo-build-duplicate-yaml-ai-summary-va-template-regression"]
series = "ci-cd-root-cause-lessons"
series_order = 5
series_title = "CI/CD Root Cause Lessons"
slug = "baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi"
tags = ["QA", "baseline debt", "CI/CD", "GitHub Pages", "unsafe"]
thumbnail = "images/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi.webp"
title = "Baseline debt chặn deploy và QA scope: chỉ bắt tính năng mới"
date_display = "10-07-2026 04:25:00 GMT +7"

[ai_summary]
collapsed = false
disclaimer = "Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi repo cần điều chỉnh policy theo rủi ro riêng."
enabled = true
items = ["Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).", "Nhiều failure không phải bug code: runner queue, platform incident, rate limit, Pages CDN lag.", "Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng feature không."]
title = "Tóm tắt nhanh"
image_attribution_checked_at = "2026-07-11T17:30:31+07:00"
image_query = "baseline debt chặn deploy qa"
+++

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
<!-- thin-expand:v1 -->

## So sánh full-site QA vs scoped QA

| Chế độ | Ưu | Nhược | Dùng khi |
|--------|----|-------|----------|
| Full-site | Bắt hết debt | Chặn PR không liên quan | Nightly / audit |
| Diff-scoped | Ship feature nhanh | Có thể sót debt cũ | PR tính năng/UI |
| Hybrid | Gate cứng full + debt report | Cần thiết kế pipeline | Production blog này |

Rule trong AGENTS: **deploy tính năng mới → QA chỉ bắt tính năng đó**.

## Case: branding/CSS bị chặn

Diff chỉ `main.css` nhưng CI fail vì:

- Post cũ duplicate description  
- AI summary hỏng  
- Ảnh thiếu từ tuần trước  

→ UI không lên live. Đúng hướng: tách **gate cứng** (Hugo build, critical path) khỏi **debt report** (full image audit).

## Cách cấu hình gợi ý

1. `git diff --name-only` → danh sách file → QA map theo loại (content / layout / workflow).
2. Content QA chỉ trên `content/posts/*` trong diff.
3. Full audit: schedule riêng, mở issue, không `exit 1` trên PR CSS.
4. Baseline debt: ticket + autofix riêng (`rule.py`, image batch), không gánh PR màu footer.

## FAQ

**Hỏi: Scoped QA có che giấu lỗi production?**  
Trả lời: Có rủi ro nếu không có nightly. Hybrid: PR scope + nightly full + alert.

**Hỏi: Nợ ảnh 10 bài thin có được fail PR docs?**  
Trả lời: Không trên PR không đụng 10 bài đó. Nightly/content-direction action P0 theo dõi riêng.

**Hỏi: `continue-on-error` có phải giải pháp?**  
Trả lời: Chỉ cho debt đã phân loại. Không cho Hugo assemble error hay test critical.

**Hỏi: Ai quyết safe/unsafe?**  
Trả lời: Deployment Doctor knowledge + playbook. Baseline debt blocking = unsafe cho “sửa bằng commit rỗng”; safe direction là sửa scope QA.

## Checklist PR feature

- [ ] QA list file từ diff  
- [ ] Không bật full image audit fail-on-error  
- [ ] Hugo build vẫn hard-fail  
- [ ] Debt cũ có issue, không block  
