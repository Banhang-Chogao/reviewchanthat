+++
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:35:00+07:00"
description = "Hướng dẫn date_only_or_wrong_timezone (safe): luôn gắn +07:00, không dùng date-only UTC khiến QA STALE_DATE và thứ tự bài sai."
draft = false
image = "images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date.webp"
image_alt = "Ảnh minh họa Post date timezone Việt Nam (GMT+7): tránh stale_date và lệch homepage — nguồn Pexels"
image_attribution_checked_at = "2026-07-10T18:56:44+07:00"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "Duy Nguyen"
image_creator_id = "489946968"
image_creator_url = "https://www.pexels.com/@duy-nguyen-489946968"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_owner = "external"
image_provider = "pexels"
image_query = "post date timezone việt nam"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/stunning-night-view-of-ho-chi-minh-city-skyline-30281995/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "hugo-build-duplicate-yaml-ai-summary-va-template-regression", "content-direction-empty-report-va-optimizer-frontmatter"]
seo_title = "Post date timezone Việt Nam (GMT+7): tránh stale_date và"
series = "ci-cd-root-cause-lessons"
series_order = 7
series_title = "CI/CD Root Cause Lessons"
slug = "post-date-timezone-vietnam-gmt7-tranh-stale-date"
tags = ["timezone", "Vietnam", "front matter", "Hugo", "safe"]
thumbnail = "images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date.webp"
title = "Post date timezone Việt Nam (GMT+7): tránh stale_date và lệch homepage"
date_display = "10-07-2026 04:35:00 GMT +7"

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
| `date_only_or_wrong_timezone` | **safe** | Date thiếu timezone hoặc stamp UTC thay vì giờ Việt Nam |

Safe vì có thể chuẩn hóa bằng script (`qa_dates.py --fix-obvious`) khi quy tắc rõ.

![So sánh date UTC vs GMT+7 trong front matter](/images/posts/post-date-timezone-vietnam-gmt7-tranh-stale-date-diagram.webp)

## Pattern sai / đúng

```yaml
# SAI — date-only, parser coi UTC midnight
date: 2026-07-10

# SAI — có giờ nhưng không offset
date: 2026-07-10 09:00:00

# ĐÚNG — giờ Việt Nam
date: "2026-07-10 04:33:00+07:00"
```

## Hậu quả

- QA `STALE_DATE`: date "ngày hôm qua" so với ngày tạo file theo VN.
- Homepage sort lệch buổi tối/sáng.
- Content Direction đánh giá freshness sai.

## Fix

- Chuẩn hóa toàn bộ front matter sang `+07:00`.
- Generator/autobot luôn dùng `now_vietnam()` thay vì `datetime.utcnow()`.
- CI chỉ fail date trên **file trong diff**, không quét 150 bài mỗi PR UI.

Xem: [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/), [Hugo YAML](/posts/hugo-build-duplicate-yaml-ai-summary-va-template-regression/).
<!-- thin-expand:v1 -->

## So sánh UTC vs Asia/Ho_Chi_Minh

| Nguồn “now” | Ví dụ 10/07/2026 01:30 VN | Date stamp nếu lỡ UTC |
|-------------|---------------------------|------------------------|
| `datetime.utcnow()` | ~09/07 18:30 UTC | Dễ ra **09-07** nếu chỉ lấy date |
| `now_vietnam()` (+07:00) | 10/07 01:30 +07 | **10-07** đúng lịch độc giả |
| Date-only `2026-07-10` | Midnight UTC | Lệch sort homepage theo múi máy runner |

Blog phục vụ độc giả Việt Nam: **mọi publish date phải quyết định theo GMT+7**, không theo múi của GitHub Actions (UTC).

## Pattern generator / autobot

- Gọi helper `scripts/lib/dates.py` (`now_vietnam`, `publish_datetime_iso`).
- Không dùng `date.today()` trên runner.
- Front matter lưu ISO có offset: `"2026-07-10T09:00:00+07:00"`.
- Field hiển thị (nếu có) dạng `dd-mm-yyyy hh:mm:ss GMT +7`.
- Pre-deploy: `python scripts/rule.py --fix` chuẩn hóa future/fake date.

## FAQ

**Hỏi: Date “hôm qua” nhưng vừa tạo bài?**  
Trả lời: Thường do stamp UTC gần nửa đêm VN, hoặc date-only bị parse UTC. So file `date` với giờ máy VN và log CI.

**Hỏi: Có cho phép future date?**  
Trả lời: Không — coi là fake. Rule pre-deploy fail hoặc kéo về “now” VN khi `--fix`.

**Hỏi: PR chỉ đổi CSS có bị fail date post cũ?**  
Trả lời: Nên **scope QA theo diff**. Quét 150 bài mỗi PR UI tạo baseline debt chặn deploy không liên quan — xem [baseline debt](/posts/baseline-debt-chan-deploy-va-qa-scope-chi-bat-tinh-nang-moi/).

**Hỏi: TOML vs YAML date?**  
Trả lời: Cùng quy tắc offset. Blog chuẩn hóa TOML (`+++`) + ISO `+07:00` qua `rule.py`.

## Checklist trước khi merge bài mới

1. `date` / `lastmod` có `+07:00`?
2. Không future hơn “now” VN quá tolerance nhỏ.
3. Generator không hardcode UTC.
4. CI date chỉ bắt file trong PR (trừ nightly full audit).
