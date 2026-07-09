+++
title = "Deployment Doctor: cách blog tự chẩn đoán lỗi deploy, gom root cause và tự sửa bug mà không cần thức đêm"
date = 2026-07-09T23:30:00+07:00
description = "Deployment Doctor là cách Review Chân Thật gom failed builds, phân loại root cause, lưu kinh nghiệm hệ thống và tự autofix lỗi deploy an toàn để giảm việc phải sửa bug thủ công."
slug = "deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix"
categories = ["cong-nghe"]
tags = ["Deployment Doctor", "GitHub Actions", "CI/CD", "autofix", "deployment", "DevOps", "Hugo"]
author = "Minh Hoàng"
image = "images/posts/deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix.webp"
thumbnail = "images/posts/deployment-doctor-tu-chan-doan-loi-deploy-root-cause-autofix.webp"
image_alt = "Minh họa editorial Deployment Doctor: pipeline Collect → Diagnose → Decide → Report với tone teal, biểu tượng chẩn đoán CI/CD và trạng thái fail/safe/autofix."
image_status = "verified"
image_provider = "self-generated"
image_source = "Review Chân Thật"
image_source_url = "https://banhang-chogao.github.io/reviewchanthat/"
image_license = "Original self-hosted editorial illustration by Review Chân Thật"
image_license_url = "https://banhang-chogao.github.io/reviewchanthat/branding-ci/"
image_commercial_use = true
image_owner = "self"
image_creator = "Review Chân Thật"
image_creator_url = "https://banhang-chogao.github.io/reviewchanthat/"
image_creator_id = "review-chan-that-generated"
image_attribution_verified = true
image_attribution_source = "self_generated"
image_generation_method = "context_aware_programmatic_pillow"
draft = false
related_posts = [
  "github-actions-run-start-delays-july-9-2026-ci-cd-protection",
  "github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident",
  "workflow-failures-audit-recent-ci-cd-root-causes-action-items"
]

[ai_summary]
enabled = true
title = "Tóm tắt nhanh"
collapsed = false
disclaimer = "Bài viết chia sẻ kinh nghiệm kỹ thuật từ quá trình vận hành blog; mỗi hệ thống CI/CD cần điều chỉnh theo cấu trúc repo và mức độ rủi ro riêng."
items = [
  "Deployment Doctor là lớp chẩn đoán deployment tự động: gom failed runs, đọc log, phân loại root cause và đề xuất action items.",
  "Điểm quan trọng không phải là tự sửa mọi thứ, mà là biết lỗi nào an toàn để autofix và lỗi nào phải chỉ báo cáo.",
  "Các lỗi như runner queue, GitHub outage hoặc rate limit không nên tạo hotfix code; hệ thống chỉ nên chờ, retry có kiểm soát hoặc cancel run cũ.",
  "Các lỗi có scope rõ như date-only, self-owned image thiếu direct_url, content direction rỗng hoặc URL hardcode có thể được autofix bằng script nhỏ, có retry cap và QA sau fix."
]
+++

Có những đêm CI/CD đỏ hàng loạt: Deploy fail, QA debt fail, Content Direction fail — mỗi cái một commit, mỗi cái một log. Nếu cứ mở từng run, đoán root cause, vá tay rồi push lại, bạn sẽ kiệt sức trước cả khi blog ổn định.

**Deployment Doctor** ra đời từ đúng nỗi đau đó. Đây không phải “AI thần thánh tự sửa mọi bug”. Đây là một **lớp văn hoá deployment**: gom failed builds, phân loại root cause, lưu kinh nghiệm hệ thống, **chỉ autofix khi an toàn**, và đưa report ra dashboard để owner không phải sống trong GitHub Actions.

Trang báo cáo nội bộ của blog: [Deployment Doctor]({{< relref "/deployment-doctor/" >}}).

## Vấn đề thật: fail không phải luôn do code của bạn

Trong vài ngày vận hành Review Chân Thật trên GitHub Actions + GitHub Pages, chúng tôi thấy rõ ba nhóm lỗi **không cùng một cách xử lý**:

| Nhóm | Ví dụ | Có nên viết code hotfix ngay? |
|------|--------|-------------------------------|
| Platform / runner | `Waiting for a hosted runner…`, Actions delayed start, Pages incident | **Không** — chờ recovery, cancel run cũ, rerun latest |
| QA debt / baseline | Post cũ thiếu image metadata, creator rỗng sai policy | **Không chặn deploy tính năng mới** — batch debt riêng |
| Lỗi scope rõ | date-only, self-owned image bắt `direct_url`, report rỗng, hardcode `/series/` | **Có thể autofix** nếu script nhỏ + QA + retry cap |

Nếu hệ thống **không phân biệt** ba nhóm này, mọi fail đều trông giống nhau: đỏ, và đều kích hoạt “sửa code gấp”. Đó là cách biến một sự cố runner thành một vòng lặp PR hotfix vô nghĩa.

## Deployment Doctor là gì?

**Deployment Doctor** là pipeline Python + workflow GitHub Actions + trang Hugo (noindex) giúp blog:

1. **Collect** — lấy danh sách run gần đây (`gh run list`), lọc failure / cancelled / timed_out / stuck queue.
2. **Sanitize logs** — lưu excerpt đã redact token/API key (không đưa secret ra frontend).
3. **Diagnose** — so khớp log với **knowledge base** root cause đã gặp.
4. **Decide** — `safe_to_autofix: true|false`, action items, có nên mở PR hay chỉ report.
5. **Autofix (có giới hạn)** — tối đa vài fix/lần, tối đa 2 attempt cho cùng `sha:failure_type`.
6. **Export dashboard** — `data/deployment-doctor.json` → trang `/deployment-doctor/`.

Tên “Doctor” mang nghĩa **chẩn đoán trước khi kê thuốc**. Không phải tự động mổ mọi thứ.

## Knowledge base: biến incident thành trí nhớ hệ thống

Mỗi lần fail “đã từng gặp” mà không ghi lại, lần sau team lại học lại từ đầu. Deployment Doctor giữ một knowledge base JSON với pattern kiểu:

- `runner_capacity_delay` — runner queue, **không** autofix code  
- `external_platform_incident` — GitHub Status / Actions delayed  
- `baseline_debt_blocking_unrelated_deploy` — nợ QA cũ chặn feature  
- `self_owned_image_direct_url` — ảnh self-generated không có `direct_url`  
- `content_direction_empty_report` — report 0 posts / empty fallback  
- `workflow_fanout` — một merge kích hoạt quá nhiều workflow song song  
- `table_layout_ux_regression`, `qa_expectation_mismatch`, …

Mỗi pattern có:

- **match strings** trong log  
- **safe_to_autofix**  
- **action items** rõ ràng  
- script gợi ý (nếu có)

Nhờ vậy, khi log hiện `No direct_url in manifest` trên ảnh `self-generated`, doctor **không** đề xuất “tải lại từ Pexels”. Nó đề xuất: bỏ yêu cầu `direct_url` với self-owned, kiểm tra file local dưới `static/images/posts/`.

## Quy tắc vàng: an toàn trước, tự động sau

### Những gì **không** được autofix

- Runner capacity / “waiting for hosted runner”  
- GitHub outage / rate limit Pages  
- Fake image creator (vi phạm policy attribution)  
- Unknown failure chưa có pattern đủ tin cậy  

Với các lỗi này, doctor **chỉ report**: owner thấy action item kiểu “đợi recovery rồi rerun latest deploy”, không có PR code lung tung lúc nửa đêm.

### Những gì **được** autofix (scope hẹp)

- Chuẩn hoá date timezone Việt Nam khi pattern rõ  
- Self-owned image: bỏ hard-fail `direct_url`  
- Creator empty hợp lệ khi `source_verified_creator_unavailable`  
- Content Direction: regenerate + guard không ghi JSON rỗng đè data thật  
- `build-info.json` để verify live SHA  
- paths-ignore / concurrency để giảm fan-out  

Mỗi lần fix:

- **Max 3 fixes / run doctor**  
- **Max 2 attempts / (SHA + failure_type)** — chống loop  
- Không rewrite full site content  
- Không mass-replace toàn bộ ảnh  
- Không mở PR rỗng  

## Loop guard và văn hoá “không tự bắn vào chân”

Một deployment culture lành mạnh phải chấp nhận: **autofix cũng có thể tạo fail mới**.

Deployment Doctor dùng ledger `data/deployment-doctor-attempts.json`. Nếu cùng `sha:failure_type` đã thử 2 lần → đánh dấu `needs_human_review`, không tạo PR thứ ba.

Commit message có marker:

- `[skip-autofix]`  
- `[deployment-doctor] [skip-report]`  

Deploy workflow **paths-ignore** các file report/doctor data để commit dashboard **không** kích hoạt deploy → doctor → commit → deploy… vô hạn.

Content Direction cũng được tách: **chỉ chạy sau khi Deploy success** (workflow_run), không đua runner với Deploy — giảm fail giả do queue/capacity.

## Dashboard: owner nhìn một trang, không đào log

Trang [Deployment Doctor]({{< relref "/deployment-doctor/" >}}) (noindex, không vào sitemap) hiển thị:

- **Summary** luôn mở: số run fail, số safe autofix, số unsafe/external  
- Các section còn lại **gập mặc định** (Recent failures, clusters, action items, lessons…) để UX không dài  
- Action items P0/P1/P2  
- “What owner should do” — thường trống; chỉ hiện khi cần secret, quyết định pháp lý, hoặc platform event  

Mục tiêu UX: **ban đêm chỉ cần lướt Summary**. Cần sâu thì mới bấm mở.

## Bài học từ fail thật của blog này

Dưới đây là vài “bệnh án” đã gặp và cách doctor hoá:

### 1. Runner queue / platform delay

Log: *Waiting for a runner to pick up this job*.  
**Thuốc sai:** sửa Hugo template.  
**Thuốc đúng:** không đổi code; cancel run superseded; rerun latest sau recovery.  
→ Pattern `runner_capacity_delay` / `external_platform_incident`.

### 2. Self-owned image + `direct_url`

Log: *FAIL: No direct_url in manifest*.  
**Thuốc sai:** gán URL Pexels giả.  
**Thuốc đúng:** self-generated không cần `direct_url`; verify file WebP local + metadata `image_owner=self`.  
→ Pattern `self_owned_image_direct_url`.

### 3. Content Direction rỗng / commit file gitignore

UI hiện 0 bài dù repo có posts; hoặc job `git add reports/` bị `.gitignore` chặn.  
**Thuốc đúng:** fail nếu scan 0 posts; không overwrite JSON rỗng; **chỉ commit** `data/content-direction.json`, không add `reports/**`.  
→ Pattern `content_direction_empty_report` + fix workflow vĩnh viễn.

### 4. Baseline debt chặn feature

Deploy feature nhỏ fail vì post cũ thiếu license/creator.  
**Thuốc đúng:** QA gate strict trên **changed/new**; debt cũ chạy batch workflow riêng.  
→ Pattern `baseline_debt_blocking_unrelated_deploy`.

## Kiến trúc tối giản bạn có thể copy

Nếu muốn dựng “Doctor” cho repo static site của mình, giữ pipeline **đơn giản và kiểm soát được**:

```text
Deploy (main) ──success──► Content Direction / Doctor collect
                              │
                              ▼
                     Diagnose vs knowledge base
                              │
              ┌───────────────┴───────────────┐
              │                               │
         unsafe/external                 safe + scoped
              │                               │
         report only                    autofix + QA
              │                               │
              └──────────► dashboard JSON ────┘
                              │
                              ▼
                     /deployment-doctor/ (noindex)
```

Nguyên tắc thiết kế:

1. **Knowledge-first** — không match pattern thì không tự sửa.  
2. **Scope-first** — chỉ đụng file liên quan.  
3. **Cap-first** — giới hạn attempt và số PR.  
4. **Report-first trên platform fail** — im lặng còn hơn hotfix sai.  
5. **Dashboard cho người** — machine-readable JSON + UI gập gọn.

## Kết luận

Deployment Doctor không thay thế engineer. Nó thay thế **thói quen phản xạ nửa đêm**: thấy đỏ là sửa lung tung.

Khi blog (và team) biết:

- fail nào là **platform**,  
- fail nào là **nợ cũ**,  
- fail nào là **bug scope rõ**,  

thì CI/CD trở thành hệ thống **học được**, không chỉ là đèn giao thông.

Nếu bạn đang xây Hugo + GitHub Actions: hãy bắt đầu bằng **gom failed runs + knowledge base + safe_to_autofix**. Autofix chỉ là bước sau — khi bạn đã đủ khiêm tốn để không để robot “chữa” những thứ không thuộc về code.

Đọc thêm trong cụm CI/CD của blog:

- [GitHub Actions run start delays (9/7/2026)]({{< relref "/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection/" >}})  
- [Pages recovered: checklist sau incident]({{< relref "/posts/github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident/" >}})  
- [Workflow failures audit: root causes & action items]({{< relref "/posts/workflow-failures-audit-recent-ci-cd-root-causes-action-items/" >}})  
