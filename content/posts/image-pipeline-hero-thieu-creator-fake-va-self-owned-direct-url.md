+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:30:00+07:00"
commit = "4bbb7284"
description = "| Code | Safety | Mô tả | |------|--------|--------| | changedpostimagemissing | safe | Post mới/đổi thiếu hero đã verify | | selfownedimagedirecturl | safe |"
draft = false
image = "images/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url.webp"
image_alt = "Ảnh minh họa Image pipeline: hero thiếu, self-owned direct_url, creator rỗng hợp lệ và creator giả — nguồn Pexels"
image_attribution_checked_at = "2026-07-11T17:30:32+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Wolfgang Weiser"
image_creator_id = "467045605"
image_creator_url = "https://www.pexels.com/@wolfgang-weiser-467045605"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "image pipeline hero thiếu self-owned"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/view-of-pipelines-in-a-forest-18784617/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi", "hugo-build-duplicate-yaml-ai-summary-va-template-regression"]
seo_title = "Image pipeline: hero thiếu, self-owned direct_url, creator"
series = "ci-cd-root-cause-lessons"
series_order = 6
series_title = "CI/CD Root Cause Lessons"
slug = "image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url"
tags = ["images", "attribution", "hero image", "CI/CD", "compliance"]
thumbnail = "images/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url.webp"
title = "Image pipeline: hero thiếu, self-owned direct_url, creator rỗng hợp lệ và creator giả"
date_display = "10-07-2026 04:30:00 GMT +7"

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
| `changed_post_image_missing` | safe | Post mới/đổi thiếu hero đã verify |
| `self_owned_image_direct_url` | safe | process_images cần direct_url cho ảnh self-owned/generated |
| `verified_creator_unavailable` | safe | Creator rỗng OK khi license/source đã verify |
| `fake_image_creator` | **unsafe** | Creator giả/blocked → policy fatal |
| `image_asset_missing` | safe | File không có dưới `static/images/posts/` |

Rule nội dung: **mỗi bài ≥ 2 ảnh** (1 hero + ≥1 minh họa). Bài kỹ thuật không ngoại lệ.

![Bảng truth attribution: creator rỗng vs creator giả](/images/posts/image-pipeline-hero-thieu-creator-fake-va-self-owned-direct-url-diagram.webp)

## Checklist trước khi merge bài mới

1. Có `image` + `thumbnail` trỏ file **tồn tại**?
2. Hero + ít nhất 1 ảnh trong body?
3. Self-generated: `image_owner: self`, source/license đúng, **không** bịa tên photographer?
4. Stock: creator thật từ API; nếu API không trả creator → để rỗng + `verified_creator_unavailable`, **không** điền "John Doe".
5. `process_images` với self-owned cần `direct_url`/`image_source_url` hợp lệ trỏ asset của mình.

## Vì sao fake creator là unsafe/fatal

Attribution giả = rủi ro pháp lý + phá trust. Autofix **không** được "bịa creator cho qua gate". Chỉ block + yêu cầu người sửa.

Liên hệ: [Baseline debt](/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).
<!-- thin-expand:v1 -->

## So sánh attribution hợp lệ vs vi phạm

| Tình huống | `image_creator` | `image_attribution_verified` | Deploy |
|------------|-----------------|------------------------------|--------|
| Pexels trả photographer | Tên thật từ API | `true` | OK |
| API không có tên | `""` rỗng | `false` / unavailable | OK nếu license/source đúng |
| Tự điền “John Doe” / tên bịa | Fake | — | **Fatal** |
| Self-owned / editorial | “Review Chân Thật” (đúng owner) | `true` + source self | OK nếu file tồn tại |
| Hero thiếu file | — | — | Fail image gate |

Rule blog: **≥ 2 ảnh/bài** (hero + minh họa). Bài kỹ thuật **không** được miễn.

## Checklist merge content (thực chiến)

1. `image` + `thumbnail` trỏ file có dưới `static/images/posts/`.
2. Body có ≥1 ảnh inline (markdown hoặc shortcode).
3. Stock: chỉ Pexels/Pixabay; watermark attribution.
4. Không fake creator; không placeholder tự vẽ khi policy cấm.
5. Self-owned: `direct_url` / path hợp lệ cho `process_images`.
6. QA scope: chỉ bắt ảnh bài trong diff — tránh baseline debt chặn PR CSS.

## FAQ

**Hỏi: Creator rỗng có bị coi là lỗi?**  
Trả lời: Không nếu đã verify license/source và ghi nhận unavailable. Lỗi là **bịa** tên.

**Hỏi: WebP bị gitignore thì sao?**  
Trả lời: Force-add file cần ship, hoặc đảm bảo pipeline generate trên CI trước publish. Blog hiện force-add hero đã verify.

**Hỏi: Ảnh lệch chủ đề (QR Alipay cho bài toán e) có pass gate không?**  
Trả lời: Có thể pass “có file + attribution” nhưng **fail chất lượng nội dung**. Nên chọn query đúng topic (series finance đã fix theo hướng này).

**Hỏi: Có được Unsplash?**  
Trả lời: Policy hiện tại: **Pexels + Pixabay only**.

## Gợi ý cho series dài

Batch script theo series (query riêng từng bài) + dedupe URL ảnh giữa các bài. Tránh 15 hero giống một stock “laptop generic”.
