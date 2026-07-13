+++
title = "Quỹ đầu tư dùng toán học như thế nào? Từ lợi suất, beta đến tối ưu danh mục"
description = "Quỹ đầu tư tính lợi suất, rủi ro và tương quan cổ phiếu bằng toán học: expected return, volatility, correlation, efficient frontier, Sharpe ratio và CAPM."
date = "2026-07-10T11:15:00+07:00"
slug = "quy-dau-tu-dung-toan-hoc-nhu-the-nao"
aliases = ["/posts/quỹ-đầu-tư-dùng-toán-học-như-thế-nào-từ-lợi-suất-beta-đến-tối-ưu-danh-mục/"]
commit = "f576fac5"
lastmod = "2026-07-10T11:15:00+07:00"
seo_title = "Quỹ đầu tư dùng toán học: Sharpe ratio, CAPM, beta"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["quỹ đầu tư", "portfolio optimization", "Sharpe ratio", "CAPM", "efficient frontier", "beta", "correlation"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 3
image = "images/posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao.webp"
date_display = "10-07-2026 11:15:00 GMT +7"
lastmod_display = "10-07-2026 11:15:00 GMT +7"
thumbnail = "images/posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/gold-round-coins-on-black-surface-8442324/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Zlaťáky.cz"
image_creator_url = "https://www.pexels.com/@zlataky-cz-61823415"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T17:30:39+07:00"
draft = false

[ai_summary]
items = ["Quỹ đầu tư đo lợi suất bằng expected return E[R] và rủi ro bằng volatility (σ)", "Correlation và covariance giữa cổ phiếu: khi một tăng có nhất thiết cái khác phải tăng không?", "Efficient frontier: tập hợp danh mục có lợi suất cao nhất với rủi ro nhỏ nhất", "Sharpe ratio = (Expected Return - Risk-Free Rate) / Volatility — cách so sánh danh mục công bằng", "CAPM (Capital Asset Pricing Model): E[R] = Rf + β(Rm - Rf) — liên hệ giữa rủi ro và lợi suất kỳ vọng", "Beta (β): rủi ro hệ thống của tài sản, đo độ nhạy với thị trường chung", "Ví dụ: danh mục cổ phiếu-trái phiếu-vàng, cách tính expected return, volatility, Sharpe ratio"]
draft = false

[[internal_links]]
ref = "posts/blackrock-dung-toan-hoc-va-du-lieu-quan-ly-danh-muc.md"
title = "BlackRock dùng toán học và dữ liệu như thế nào? Quản lý danh mục khổng lồ"

[[internal_links]]
ref = "posts/cfa-dung-toan-hoc-gi.md"
title = "CFA dùng toán học gì? Những công thức quản lý tài sản"

[[internal_links]]
ref = "posts/cong-ty-bao-hiem-dung-toan-hoc-tinh-phi-rui-ro.md"
title = "công ty bảo hiểm dùng toán học đỉnh cao như thế nào để tính phí và rủi ro?"
+++

Khi bạn cho 10 triệu vào một quỹ đầu tư, quỹ sẽ dùng **toán học gì** để quyết định mua cổ phiếu, trái phiếu, vàng hay gì?

Giới quản lý quỹ không chỉ dựa vào "cảm giác thị trường". Họ dùng:
- **Expected return** (lợi suất kỳ vọng)
- **Volatility** (độ biến động/rủi ro)
- **Correlation** (tương quan giữa tài sản)
- **Efficient frontier** (biên giới tối ưu)
- **Sharpe ratio** (tỉ lệ rủi ro-lợi suất)
- **CAPM & Beta** (model định giá)

Bài này giải thích cách quỹ dùng toán học để **tối ưu danh mục** (portfolio optimization).

---

## Phép đo: lợi suất & rủi ro


![Minh họa nội dung quy dau tu dung toan hoc nhu the nao — nguồn Pexels](/images/posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao-inline.webp)

*Nguồn: Pexels / cottonbro studio*


### Expected Return (lợi suất kỳ vọng)

```
E[R] = p1 × R1 + p2 × R2 + ... + pn × Rn
```

**Ký hiệu:**
- E[R] = lợi suất kỳ vọng
- p = xác suất
- R = lợi suất theo kịch bản

**Ví dụ: Cổ phiếu VietcomBank**
```
Kịch bản tốt (xác suất 40%): +15%
Kịch bản bình thường (xác suất 50%): +5%
Kịch bản xấu (xác suất 10%): -10%

E[R] = 0.4 × 15% + 0.5 × 5% + 0.1 × (-10%)
     = 6% + 2.5% - 1%
     = 7.5% lợi suất kỳ vọng
```

### Volatility (Độ biến động/rủi ro)

```
σ = √[ p1(R1 - E[R])² + p2(R2 - E[R])² + ... + pn(Rn - E[R])² ]
```

**Diễn giải:** Volatility đo mức độ "lắc lư" xung quanh lợi suất kỳ vọng.

**Ví dụ:** Cổ phiếu A có σ = 20% (lắc lư nhiều) vs cổ phiếu B có σ = 5% (ổn định).

---

## Correlation & Covariance

Nếu cổ phiếu A tăng 10%, có nhất thiết cổ phiếu B phải tăng không?

**Không luôn luôn.** Mối quan hệ này gọi là **correlation (tương quan)**.

```
Correlation ρ(A,B) = -1  (ngược chiều hoàn toàn)
Correlation ρ(A,B) = 0   (độc lập hoàn toàn)
Correlation ρ(A,B) = +1  (cùng chiều hoàn toàn)
```

**Ví dụ:**
- Cổ phiếu công nghệ vs cổ phiếu ngân hàng: ρ ≈ 0.3 (yếu)
- Vàng vs cổ phiếu: ρ ≈ -0.2 (âm—vàng tăng khi cổ phiếu giảm)
- Bitcoin vs Ethereum: ρ ≈ 0.7 (mạnh)

**Covariance (hiệp phương sai):** Cov(A,B) = ρ × σA × σB

---

## Efficient Frontier (Biên giới tối ưu)

**Câu hỏi:** Trong tất cả danh mục có thể xây dựng từ N tài sản, danh mục nào **tốt nhất**?

**Tiêu chí:** lợi suất cao nhất với rủi ro **thấp nhất** (hay rủi ro đó là thấp nhất với lợi suất kỳ vọng đó).

**Efficient frontier** là đường cong nối các danh mục "tối ưu Pareto" này. Quỹ sẽ xây dựng danh mục nằm **trên** efficient frontier, không dưới.

**Biểu đồ:**
```
E[R]
  |     ● danh mục tối ưu (trên efficient frontier)
  |    /|
  |   / |
  |  /  | danh mục kém (dưới efficient frontier, rủi ro cao nhưng lợi suất thấp)
  | /   |
  |/____|___ σ (rủi ro)
```

---

## Sharpe Ratio (Tỉ lệ Sharpe)

Cách công bằng so sánh danh mục A vs B:

```
Sharpe Ratio = (E[R] - Rf) / σ
```

**Ký hiệu:**
- E[R] = lợi suất kỳ vọng danh mục
- Rf = lãi suất phi rủi ro (ví dụ: lãi trái phiếu chính phủ 3%)
- σ = volatility danh mục

**Diễn giải:** Cứ mỗi đơn vị rủi ro, bạn nhận được bao nhiêu lợi suất vượt trên mức an toàn (Rf)?

**Ví dụ:**
```
danh mục A: E[R] = 10%, σ = 15%, Rf = 3%
Sharpe = (10% - 3%) / 15% = 0.47

danh mục B: E[R] = 12%, σ = 25%, Rf = 3%
Sharpe = (12% - 3%) / 25% = 0.36

→ danh mục A tốt hơn (0.47 > 0.36): lợi suất cao hơn ít nhưng rủi ro kém lớn hơn
```

---

## CAPM & Beta

### Capital Asset Pricing Model (CAPM)

```
E[R] = Rf + β(Rm - Rf)
```

**Ký hiệu:**
- E[R] = lợi suất kỳ vọng tài sản
- Rf = lãi suất phi rủi ro
- β = beta (rủi ro hệ thống)
- Rm = lợi suất kỳ vọng thị trường chung
- (Rm - Rf) = risk premium (phần trăm thêm do rủi ro)

### Beta (β)

Beta đo **độ nhạy** của tài sản với thị trường chung:
```
β = 1: tài sản biến động cùng thị trường
β > 1: tài sản biến động MỨC hơn thị trường (rủi ro cao hơn)
β < 1: tài sản biến động ÍT hơn thị trường (rủi ro thấp hơn)
β < 0: tài sản chuyển động ngược thị trường (hiếm, ví dụ: vàng)
```

**Ví dụ:**
```
Lãi suất phi rủi ro (Rf) = 3%/năm
lợi suất thị trường (Rm) = 10%/năm
Risk premium = 10% - 3% = 7%

Cổ phiếu A có β = 1.5
E[R] = 3% + 1.5 × 7% = 3% + 10.5% = 13.5%

Cổ phiếu B có β = 0.8
E[R] = 3% + 0.8 × 7% = 3% + 5.6% = 8.6%
```

**Diễn giải:** Cổ phiếu A rủi ro hơn (β > 1) nên lợi suất kỳ vọng cũng cao hơn (13.5% vs 8.6%).

---

## Ví dụ: danh mục cổ phiếu-trái phiếu-vàng

**danh mục gồm:**
- 60% cổ phiếu (E[R] = 12%, σ = 18%)
- 30% trái phiếu (E[R] = 5%, σ = 4%)
- 10% vàng (E[R] = 4%, σ = 12%)

**lợi suất kỳ vọng danh mục:**
```
E[Rp] = 0.60 × 12% + 0.30 × 5% + 0.10 × 4%
      = 7.2% + 1.5% + 0.4%
      = 9.1%
```

**Volatility danh mục** (cần correlation matrix, phức tạp hơn):
```
σp ≈ 10.5% (ví dụ, thấp hơn 60% × 18% = 10.8% do diversification)
```

**Sharpe ratio:**
```
Sharpe = (9.1% - 3%) / 10.5% = 0.58
```

---

## Tại sao quỹ tối ưu danh mục?

✅ **Giảm rủi ro** (diversification): correlation giữa tài sản giúp giảm volatility  
✅ **Tối ưu lợi suất:** Efficient frontier giúp chọn danh mục "tốt nhất"  
✅ **So sánh công bằng:** Sharpe ratio so sánh danh mục độc lập với quy mô  
✅ **Đo rủi ro hệ thống:** Beta giúp hiểu đến đâu rủi ro từ thị trường vs từ tài sản  

---

## Checklist

✅ Expected return = Σ p × R  
✅ Volatility = độ lệch chuẩn từ expected return  
✅ Correlation: -1 (ngược) → 0 (độc lập) → +1 (cùng)  
✅ Efficient frontier: danh mục tối ưu Pareto  
✅ Sharpe ratio = (E[R] - Rf) / σ → so sánh công bằng  
✅ CAPM: E[R] = Rf + β(Rm - Rf)  
✅ Beta > 1 = rủi ro cao hơn thị trường  

---

## Kết luận: Bài 4 & 5

**Quỹ đầu tư dùng toán học để không chỉ kiếm tiền mà còn quản lý rủi ro.**

Tiếp theo: **"công ty bảo hiểm dùng toán học đỉnh cao như thế nào?"** — nơi xác suất meets actuarial science, survival models, và định giá rủi ro.

(Bài 5: CFA — những công cụ tài chính chuẩn mực)
