+++
noindex = true
title = "Deployment Doctor: cách blog tự chẩn đoán lỗi deploy, gom root cause và tự sửa bug mà không cần thức đêm"
date = "2026-07-09T23:30:00+07:00"
date_display = "09-07-2026 23:30:00 GMT +7"
commit = "0ee71da6"
slug = "deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix"
categories = ["cong-nghe"]
tags = ["Deployment Doctor", "GitHub Actions", "CI/CD", "autofix", "deployment", "DevOps", "Hugo"]
author = "Minh Hoàng"
image = "images/posts/deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix.webp"
thumbnail = "images/posts/deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix.webp"
image_alt = "Ảnh minh họa Deployment Doctor: cách blog tự chẩn đoán lỗi deploy, gom root cause và tự sửa bug mà không cần thức đêm — nguồn Pexels"
image_status = "verified"
image_provider = "pexels"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/female-soldier-saying-goodbye-to-her-son-putting-on-her-backpack-7983759/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "George Pak"
image_creator_url = "https://www.pexels.com/@george-pak"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pexels_api"
draft = false
related_posts = ["github-actions-run-start-delays-july-9-2026-ci-cd-protection", "github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident"]
seo_title = "Deployment Doctor: cách blog tự chẩn đoán lỗi deploy, gom"
description = "Một blog cá nhân trông “nhỏ”, nhưng pipeline có thể rất đông: Deploy, Content Direction, QA debt, autofix, snapshot, doctor… Chỉ cần một fail không được phân"

[ai_summary]
enabled = true
collapsed = false
disclaimer = "Bài viết chia sẻ kinh nghiệm kỹ thuật từ quá trình vận hành blog; mỗi hệ thống CI/CD cần điều chỉnh theo cấu trúc repo và mức độ rủi ro riêng."
items = ["Deployment Doctor là lớp chẩn đoán deployment tự động: gom failed runs, đọc log, phân loại root cause và đề xuất action items.", "Điểm quan trọng không phải là tự sửa mọi thứ, mà là biết lỗi nào an toàn để autofix và lỗi nào phải chỉ báo cáo.", "Các lỗi như runner queue, GitHub outage hoặc rate limit không nên tạo hotfix code; hệ thống chỉ nên chờ, retry có kiểm soát hoặc cancel run cũ.", "Các lỗi có scope rõ như date-only, self-owned image thiếu direct_url, content direction rỗng hoặc URL hardcode có thể được autofix bằng script nhỏ, có retry cap và QA sau fix."]
image_attribution_checked_at = "2026-07-12T08:48:50+07:00"
image_query = "deployment doctor cách blog tự"
+++
Một blog cá nhân trông “nhỏ”, nhưng pipeline có thể rất đông: Deploy, Content Direction, QA debt, autofix, snapshot, doctor… Chỉ cần **một** fail không được phân loại, cả dây chuyền dễ chạy vòng: bot sửa, bot report, bot deploy lại, runner xếp hàng, và chủ blog thức đêm mở log.

Vấn đề không phải “có lỗi”. Lỗi luôn có. Vấn đề là **lỗi không được gắn ngữ cảnh**: runner queue trông giống bug code; GitHub outage trông giống template hỏng; nợ QA bài cũ trông giống feature PR mới hỏng. Khi mọi thứ đều “đỏ”, phản xạ tự nhiên là commit hotfix — và đó thường là phản xạ sai.

**Deployment Doctor** ra đời để biến failed builds thành **dữ liệu có hành động**: gom run, đọc log đã sanitize, gắn root cause, quyết định `safe_to_autofix`, rồi hoặc mở PR nhỏ, hoặc chỉ ghi report. Dashboard nội bộ nằm tại [Deployment Doctor](/deployment-doctor/). Bài này kể triết lý và design thật mà Review Chân Thật đang dùng, dựa trên một cụm failed runs gần đây trên `main` (không bịa run ID tuyệt đối nếu không cần).

## Deployment Doctor là gì?

Deployment Doctor là một lớp **“bác sĩ deployment”** — không phải AI thay engineer, mà là **quy trình có máy hỗ trợ**:

1. **Gom failed workflows** từ GitHub Actions (failure, cancelled, timed_out, hoặc queue bất thường).
2. **Đọc log đã sanitize** — redact token, API key, private key; không đưa secret ra frontend.
3. **Nhận diện root cause** bằng knowledge base (pattern log + heuristic).
4. **Gắn `safe_to_autofix: true|false`** cùng action items.
5. **Chạy script sửa lỗi nếu an toàn** và scope hẹp.
6. **Mở PR nhỏ** hoặc **chỉ report** nếu không an toàn.
7. **Lưu kinh nghiệm** vào knowledge base / attempt ledger để lần sau không “học lại từ zero”.

Nói cách khác: Doctor **chẩn đoán trước khi kê thuốc**. Tự động hoá không đồng nghĩa “cứ fail là sửa code”.

## Vì sao không nên auto-fix mọi lỗi?

Automation thiếu phân loại nguy hiểm hơn không có automation. Một vài lý do thực tế:

**Runner queue không phải code bug.** Log kiểu *Waiting for a hosted runner to come online* nghĩa là job chưa kịp checkout. Commit hotfix Hugo template lúc này chỉ tạo thêm run xếp hàng.

**GitHub outage / rate limit không phải lỗi repo.** Khi Actions/Pages degraded, “sửa blog” không làm platform xanh lại. Cần pause workflow phụ, cancel run superseded, rerun latest sau recovery.

**Old QA debt không nên block deploy tính năng mới.** Nếu mỗi PR nhỏ phải “chữa hết” metadata ảnh của hàng chục bài cũ, feature ship sẽ chết vì nợ không liên quan.

**Một số lỗi cần chờ / retry / cancel**, không cần commit. Deploy stale đôi khi chỉ cần rerun artifact mới nhất có kiểm soát.

**Auto-fix thiếu phân loại có thể làm site hỏng hơn:** bot “vá” sai file, tạo PR rỗng, hoặc loop commit report kích hoạt deploy vô hạn. Doctor cố tình **không** an toàn nếu không có pattern rõ.

## Những nhóm lỗi Deployment Doctor phải nhận diện

Bảng dưới là “bảng bệnh án” tối thiểu — tín hiệu nhận diện, có được autofix trong deploy chính hay không, và action item gợi ý.

| Nhóm lỗi | Tín hiệu nhận diện | Có nên autofix? | Action item |
|----------|--------------------|-----------------|-------------|
| Runner capacity delay | `Waiting for a runner…` / hosted runner chưa online | **Không** | Cancel run superseded; retry **latest** deploy sau khi hồi phục |
| External platform incident | GitHub Status degraded, Actions delayed start | **Không** | Pause workflow phụ; không hotfix code repo |
| Old QA debt blocking unrelated deploy | Bài cũ fail image/compliance dù PR không sửa bài đó | **Không** trong deploy chính | Baseline debt + batch PR riêng (`qa-debt-fix`) |
| Changed post compliance issue | Bài mới/sửa thiếu metadata, date, image | **Có**, scoped | Chỉ sửa file changed/new |
| Self-owned image `direct_url` | Ảnh self-generated fail vì không có provider `direct_url` | **Có** | Process local path dưới `static/images/posts/` |
| Content Direction empty report | Report 0 posts dù repo có content | **Có** | Fail nếu scan 0 posts; không ghi JSON rỗng đè data |
| Live deploy stale | Merge success nhưng live SHA cũ | **Có giới hạn** | `build-info.json` + verify live + rerun latest **một lần** |
| Workflow fan-out | Một merge kích hoạt quá nhiều workflow | **Có** | Concurrency + `paths-ignore` + report-only skip |

Trong một cụm failed/cancelled runs gần đây trên `main` (lấy bằng `gh run list --limit 30`), ta thấy xen kẽ Deployment Doctor, Content Direction và Deploy — đúng kiểu **fan-out + cancel** hơn là “một bug bí ẩn duy nhất”. Điều quan trọng là hệ thống **phân nhóm** trước khi quyết định commit.

## Kiến trúc đề xuất: 5 lớp

### 1. Collector

Gọi GitHub CLI / API, lấy run gần đây, lọc conclusion thú vị, tải log (nếu được), sanitize, lưu excerpt. Nếu không auth được `gh`, collector **không fail build** — ghi `github_api_unavailable` và vẫn export dashboard một phần.

### 2. Diagnosis engine

Map log + tên workflow → `failure_type` + `confidence` + `safe_to_autofix`. Ưu tiên đọc **nội dung log** hơn title commit (tránh false positive). Job chưa từng checkout → gần như chắc `runner_capacity_delay`.

### 3. Knowledge base

JSON pattern: match strings, summary, action items, script gợi ý. Mỗi lần gặp fail mới “lạ” mà lặp lại → bổ sung pattern. Knowledge base là **trí nhớ team**, không phải đống log chết.

### 4. Scoped autofix

Chỉ sửa khi:

- `safe_to_autofix == true`
- có script đăng ký
- attempt ledger chưa vượt cap (ví dụ max 2 lần / `sha:failure_type`)
- max N fixes mỗi lần chạy doctor

Không full-site rewrite. Không mass-replace ảnh. Không PR rỗng.

### 5. Dashboard

Trang noindex (không sitemap) cho owner: Summary luôn mở; các section dài gập mặc định. Action items P0/P1/P2. “What owner should do” thường trống — chỉ hiện khi cần secret, quyết định pháp lý, hoặc platform event.

Luồng tóm tắt:

```text
Failed runs
    → Collector (sanitize logs)
    → Diagnosis (knowledge base)
    → Safe autofix?
         ├─ yes → script scoped → QA → PR nhỏ (có cap)
         └─ no  → report-only / dashboard
    → Live verification (build-info + URL thật)
```

## Lỗi nào được autofix, lỗi nào chỉ report?

| Failure type | Autofix? | Vì sao | Ví dụ action |
|--------------|----------|--------|--------------|
| date-only / timezone | **Yes** | Pattern rõ, script `fix-obvious` | Chuẩn hoá `+07:00`, không rewrite ngày mơ hồ |
| self-owned image without `direct_url` | **Yes** | Ảnh local không cần provider URL | Skip hard-fail; verify file WebP local |
| changed post missing image metadata | **Yes (scoped)** | Chỉ bài mới/sửa | Bổ sung metadata self-generated cho đúng slug |
| Content Direction empty report | **Yes** | Guard + regenerate | Fail nếu 0 posts; chỉ commit `data/content-direction.json` |
| hardcoded `/series/` hoặc `/images/` | **Yes** | Lỗi baseURL project pages | `relURL` / path có base path project |
| runner queue | **No** | Không phải bug repo | Cancel + retry latest sau recovery |
| GitHub outage | **No** | Platform | Pause nonessential workflows |
| rate limit | **No** (hoặc backoff) | Platform | Backoff; giảm fan-out |
| old QA debt | **Separate PR** | Không chặn deploy chính | Batch debt, baseline ledger |
| unknown build error | **No** (trừ pattern đã biết) | rủi ro cao | Human review + thêm knowledge |

## Vì sao cần baseline debt?

Blog có nhiều bài cũ. Metadata ảnh, license, creator — chuẩn ngày nay gắt hơn lúc viết bài. Nếu **mọi deploy** chạy compliance full-site, một PR “sửa CSS table” có thể fail vì bài du lịch tháng trước thiếu `image_license_url`.

Cách đúng:

1. **Changed/new content: strict** — bài mới không được nợ.
2. **Old debt → baseline** — ghi nhận, không chặn feature.
3. **Batch PR** theo lịch / workflow tay — sửa dần.
4. **Không hạ chuẩn** cho bài mới để “cho lẹ”.

Đây là điểm văn hoá: **strict ≠ trừng phạt quá khứ trong mọi PR**.

## Vì sao cần live verification?

Merge xanh trên GitHub **chưa chắc** live đã cập nhật. Deploy job success **chưa chắc** đúng artifact mới. Pages có thể serve bản cũ, cancel giữa chừng, hoặc rate-limit publish.

Thực tế cần:

- `static/build-info.json` (hoặc tương đương) ghi SHA lúc build
- Kiểm tra live URL / `build-info` sau deploy
- Nếu stale: **rerun latest deploy một lần**, không spam

Tin badge workflow hơn live URL là cách hay để tự lừa mình.

## Vì sao ảnh tự vẽ cũng cần được Deployment Doctor hiểu?

Review Chân Thật chuyển sang **self-generated / self-hosted hero**. Ảnh không còn `direct_url` kiểu Pexels/Unsplash. Pipeline cũ từng fail:

```text
FAIL: No direct_url in manifest for <slug>
```

Đó là **false positive** với self-owned. Doctor (và `process_images`) phải hiểu:

- `image_provider = self-generated`
- `image_owner = self`
- `image_creator = Review Chân Thật` (self, không bịa nghệ sĩ)
- `image_attribution_source = self_generated`
- file nằm dưới `static/images/posts/`

**Không được fail chỉ vì thiếu external `direct_url`.** Cũng không được “vá” bằng creator giả hay fallback generic. Context-aware generation: đọc bài → prompt/visual brief → vẽ → metadata khớp content.

## Bài học rút ra

1. **Đừng để automation tự sửa mọi thứ.** Sửa sai đắt hơn fail có chủ đích.
2. **Đừng để lỗi cũ block deploy mới.** Baseline debt + batch riêng.
3. **Đừng xem mọi failed workflow là lỗi code.** Runner và platform tồn tại.
4. **Đừng tin deploy badge hơn live URL.** Verify artifact/SHA.
5. **Hãy lưu kinh nghiệm thành knowledge base.** Pattern lặp lại phải rẻ hơn lần đầu.
6. **Hãy để bot làm việc lặp lại; con người quyết định mơ hồ.** Unknown = human review.
7. **Giới hạn attempt và fan-out.** Loop guard, concurrency, paths-ignore report-only.
8. **Content Direction / doctor không đua runner với Deploy.** Chạy sau success giảm fail giả.

## Nhận xét của Review Chân Thật

Deployment Doctor **không phải để che lỗi**. Nó làm lỗi **rõ hơn, có ngữ cảnh hơn**, và ít đánh thức chủ blog hơn.

Một deployment culture tốt, ít nhất với static site + GitHub Actions, cần ba thứ:

1. **Root cause rõ** — không gộp mọi đỏ thành một
2. **Autofix có giới hạn** — scope, cap, ledger
3. **Live verification sau deploy** — SHA thật trên site

Với blog cá nhân / indie / Hugo: automation nên **hỗ trợ con người**, không tạo thêm ca trực. Doctor là công cụ để ban đêm chỉ cần mở Summary dashboard — còn bot chỉ đụng những vết thương đã biết cách băng.

Nếu bạn đang dựng pipeline tương tự, hãy bắt đầu bằng collector + knowledge base + `safe_to_autofix`. Autofix là bước sau, khi bạn đủ khiêm tốn để không để robot “chữa” những thứ không thuộc về code.

Đọc thêm các bài cùng cụm vận hành CI/CD trên blog: bảo vệ pipeline khi [GitHub Actions chậm start runner](/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection/), checklist sau khi [Pages/Actions hồi phục](/posts/github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident/).
