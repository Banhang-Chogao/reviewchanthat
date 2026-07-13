+++
noindex = true
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:45:00+07:00"
commit = "f45b70cd"
description = "Vì sao merge OK nhưng live vẫn phục vụ artifact cũ, vai trò của build-info.json và cách verify GitHub Pages đã serve đúng bản mới."
draft = false
image = "images/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact.webp"
image_alt = "Ảnh minh họa Live deploy không phản ánh: build-info.json và GitHub Pages serving old artifact — nguồn Pexels"
image_attribution_checked_at = "2026-07-11T17:30:32+07:00"
image_attribution_source = "pexels_manifest"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Thien Le Duy"
image_creator_id = ""
image_creator_url = "https://www.pexels.com/@thienleduyphoto"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "live deploy phản ánh build-info"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/illuminated-landmark-81-tower-at-night-31194682/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code", "workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress"]
seo_title = "Live deploy không phản ánh: build-info.json và GitHub Pages"
series = "ci-cd-root-cause-lessons"
series_order = 9
series_title = "CI/CD Root Cause Lessons"
slug = "live-deploy-khong-phan-anh-va-pages-serving-old-artifact"
tags = ["GitHub Pages", "CDN", "deploy verification", "build-info", "CI/CD"]
thumbnail = "images/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact.webp"
title = "Live deploy không phản ánh: build-info.json và GitHub Pages serving old artifact"
date_display = "10-07-2026 04:45:00 GMT +7"

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
| `live_deploy_not_reflected` | safe | Merge OK nhưng live vẫn artifact cũ — thường verify/process |
| `github_pages_serving_old_artifact` | **unsafe** | Pages vẫn serve bản trước sau khi deploy job success |

![Đối chiếu SHA deploy với build-info.json trên production](/images/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact-diagram.webp)

## Quy trình verify 2 phút

1. Mở Actions → Deploy → ghi **commit SHA**.
2. Mở `/build-info.json` trên site → so `sha` / `short_sha`.
3. Soft-fail nếu mismatch < 5–10 phút (CDN); hard-investigate nếu > 30 phút.
4. Kiểm tra CSS fingerprint (`main.min.<hash>.css`) có đổi với feature UI không.
5. Hard refresh / cửa sổ ẩn danh để loại cache trình duyệt.

## Khi nào unsafe?

Khi deploy job **xanh** nhưng Pages vẫn SHA cũ lâu: có thể publish step no-op, environment protection, hoặc platform lag. **Không** kết luận "code sai" vội — và **không** spam redeploy 20 lần (rate limit).

Xem: [Runner/platform](/posts/github-hosted-runner-delay-va-platform-incident-khong-phai-bug-code/), [Fan-out](/posts/workflow-fanout-sau-merge-concurrency-group-va-cancel-in-progress/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).
<!-- thin-expand:v1 -->

## So sánh các lớp “đã deploy”

| Lớp | Ý nghĩa | Cách kiểm |
|-----|---------|-----------|
| Git `main` SHA | Code đã merge | `git rev-parse origin/main` |
| Actions Deploy success | Workflow xong | Tab Actions |
| Artifact upload | Bundle Hugo đã đóng gói | Step “Upload Pages artifact” |
| Pages serving | CDN/host đang trả HTML | `/build-info.json` trên live |
| Trình duyệt | Cache local | Soft refresh / ẩn danh |

Job **xanh** chỉ chứng minh pipeline chạy xong — **chưa** chứng minh user đang xem đúng SHA.

## Quy trình điều tra 10 phút

1. Ghi SHA commit vừa merge.
2. Mở `https://…/build-info.json` → so `sha`.
3. Nếu khớp: feature “không thấy” có thể do CSS cache, feature flag, hoặc selector QA sai.
4. Nếu lệch < 10 phút: chờ CDN; kiểm tra lại.
5. Nếu lệch > 30 phút + deploy xanh: nghi publish no-op / environment protection / platform lag — **không** spam 20 lần redeploy.
6. Xem [rate limit](/posts/github-api-va-pages-rate-limit-cach-doc-va-giam-tai/) nếu bị 429 khi retry.

## FAQ

**Hỏi: build-info đúng SHA nhưng UI cũ?**  
Trả lời: Hard refresh; so hash file CSS `main.min.<hash>.css`. Có thể partials HTML đúng nhưng asset cache.

**Hỏi: Có nên force-push để “ép” Pages?**  
Trả lời: Không. Force-push không thay cho chẩn đoán publish path và dễ làm rối history.

**Hỏi: Autofix có giúp khi Pages serve artifact cũ?**  
Trả lời: Thường **không** — đây là unsafe/platform. Autofix content không đổi cách Pages chọn artifact.

**Hỏi: Làm sao chứng minh với team?**  
Trả lời: Screenshot Actions SHA + JSON `build-info` + thời điểm UTC/VN. Deployment Doctor nên ghi pattern `github_pages_serving_old_artifact`.

## Gợi ý vận hành

Mỗi deploy ghi `build-info.json` (đã có trên blog). QA live chỉ cần so một field — rẻ hơn full visual regression khi nghi “deploy không lên”.
