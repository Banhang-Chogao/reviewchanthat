+++
noindex = true
author = "Minh Hoàng"
categories = ["cong-nghe"]
date = "2026-07-10T04:50:00+07:00"
commit = "e1b87c29"
description = "Xử lý lỗi baseURL routing bỏ prefix subpath, lệch noindex giữa front matter và sitemap, và series URL hardcode trên GitHub Project Pages."
draft = false
image = "images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url.webp"
image_alt = "Ảnh minh họa BaseURL, sitemap noindex và series hardcoded URL trên GitHub project Pages — nguồn Pexels"
image_attribution_source = "pexels_api"
image_attribution_verified = true
image_commercial_use = true
image_creator = "RDNE Stock project"
image_creator_id = "3149039"
image_creator_url = "https://www.pexels.com/@rdne"
image_license = "Pexels License"
image_license_url = ""
image_owner = "external"
image_provider = "pexels"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/a-graph-in-close-up-photography-7947635/"
image_status = "verified"
related_posts = ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "live-deploy-khong-phan-anh-va-pages-serving-old-artifact", "hugo-build-duplicate-yaml-ai-summary-va-template-regression"]
seo_title = "BaseURL, sitemap noindex và series hardcoded URL trên GitHub"
series = "ci-cd-root-cause-lessons"
series_order = 10
series_title = "CI/CD Root Cause Lessons"
slug = "baseurl-sitemap-noindex-va-series-hardcoded-url"
tags = ["baseURL", "sitemap", "SEO", "Hugo", "GitHub Pages"]
thumbnail = "images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url.webp"
title = "BaseURL, sitemap noindex và series hardcoded URL trên GitHub project Pages"
date_display = "10-07-2026 04:50:00 GMT +7"

[ai_summary]
collapsed = false
disclaimer = "Bài viết tổng hợp kinh nghiệm vận hành blog Hugo + GitHub Pages; mỗi repo cần điều chỉnh policy theo rủi ro riêng."
enabled = true
items = ["Phân biệt lỗi safe (được autofix) và unsafe (chỉ báo cáo, không hotfix mù).", "Nhiều failure không phải bug code: runner queue, platform incident, rate limit, Pages CDN lag.", "Checklist chẩn đoán: job đã start chưa, SHA live khớp chưa, QA scope có đúng feature không."]
title = "Tóm tắt nhanh"
image_attribution_checked_at = "2026-07-14T00:08:15+07:00"
image_query = "baseurl sitemap noindex series hardcoded"

[[faq]]
question = "Hỏi: Vì sao local không lỗi nhưng production gãy CSS?"
answer = "Trả lời: Local Hugo thường serve tại `/` hoặc port không có subpath. Production GitHub project Pages luôn có prefix repo name. Absolute path `/css/...` bỏ prefix → 404."

[[faq]]
question = "Hỏi: Có nên dùng `canonifyURLs = true`?"
answer = "Trả lời: Có thể giúp một số link, nhưng không thay cho việc viết template đúng (`relURL`). Blog này ưu tiên helper + QA thay vì dựa một flag “magic”."

[[faq]]
question = "Hỏi: Series hardcode `/series/foo/` sửa thế nào?"
answer = "Trả lời: Dùng `.Permalink`, `relLangURL`, hoặc `site.GetPage`. Mọi chuỗi path tĩnh trong layout đều là debt."

[[faq]]
question = "Hỏi: Sitemap vẫn còn trang admin?"
answer = "Trả lời: Kiểm tra `_build.list`, `noindex`, và script gen sitemap. Lệch hai nguồn sự thật → fail `sitemap_noindex_mismatch`."
+++

## Root cause

| Code | Safety | Mô tả |
|------|--------|--------|
| `baseurl_routing_error` | safe | Path absolute bỏ prefix `/reviewchanthat/` |
| `sitemap_noindex_mismatch` | safe | Trang noindex vẫn nằm trong sitemap |
| `series_hardcoded_url` | safe | Hardcode `/series/` vỡ khi site là project Pages |

![Sơ đồ routing baseURL project Pages](/images/posts/baseurl-sitemap-noindex-va-series-hardcoded-url-diagram.webp)

## BaseURL

Site: `https://banhang-chogao.github.io/reviewchanthat/`.

```html
<!-- SAI -->
<link href="/css/main.css">
<a href="/posts/hello/">

<!-- ĐÚNG: dùng relURL / absURL / site.BaseURL trong template -->
```

Trong markdown ảnh: ưu tiên shortcode/partial resolve; tránh hardcode host.

## Sitemap vs noindex

Trang `branding-ci`, admin, một số landing: `noindex: true` **và** `_build.list: false` / loại khỏi sitemap. QA `sitemap_noindex_mismatch` bắt khi hai nguồn sự thật lệch.

## Series URL

Dùng `relLangURL` / `permalink` thay vì chuỗi `"/series/foo/"`. Hardcode phá cả local `localhost` lẫn project base path.

Xem: [Live verify](/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact/), [Playbook](/posts/ci-cd-root-cause-playbook-safe-vs-unsafe-autofix/).
<!-- thin-expand:v1 -->

## So sánh: absolute path vs helper Hugo

| Cách viết | Local `hugo server` | Project Pages `/reviewchanthat/` | Custom domain root |
|-----------|---------------------|----------------------------------|--------------------|
| `href="/css/main.css"` | Thường “may mắn” OK | **Gãy** (trỏ về `github.io/css/...`) | OK nếu site ở root |
| `relURL` / `absURL` | OK | OK | OK |
| Hardcode host full URL | Sai môi trường staging | Sai khi đổi domain | Khó migrate |

Quy tắc thực tế trên blog này: **không hardcode** path bắt đầu bằng `/` trong template nếu path đó thuộc site (CSS, permalink series, link nội bộ). Ảnh trong markdown cũng nên qua partial/`relURL` thay vì host tuyệt đối.

## Checklist QA trước merge

1. Bật site project Pages (baseURL có subpath) trên preview nếu có.
2. Mở DevTools → Network: CSS/JS 200, không 404 về root host.
3. So sitemap: URL nào có `noindex` trong front matter thì **không** được nằm trong `sitemap.xml`.
4. Trang series: click từ card series → URL vẫn giữ prefix `/reviewchanthat/`.
5. So với [live deploy verify](/posts/live-deploy-khong-phan-anh-va-pages-serving-old-artifact/) sau khi merge.

## Gợi ý vận hành

Khi thêm layout mới (dashboard, doctor, admin), thêm test nhanh: “URL trong HTML có chứa base path không?” và “trang private có lọt sitemap không?”. Một lần quên hardcode series đủ để cả cụm link series vỡ trên production dù CI local xanh.
