+++
draft = false
title = "Mô hình định giá cổ phiếu: DCF, Comparable, PEG ratio"
description = "định giá cổ phiếu dùng toán học nào? Học Discounted Cash Flow (DCF), P/E ratio, PEG, EV/EBITDA, terminal value, và so sánh tương đối."
date = "2026-07-10T13:16:14+07:00"
slug = "mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien"
aliases = ["/posts/mô-hình-định-giá-cổ-phiếu-dcf-comparable-peg-ratio/"]
commit = "e1b87c29"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "định giá cổ phiếu: DCF, P/E, PEG và comparable valuation"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["định giá cổ phiếu", "DCF", "P/E ratio", "terminal value", "comparable valuation", "intrinsic value"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 10
image = "images/posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien.webp"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"
thumbnail = "images/posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/gray-laptop-on-the-table-7693142/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Yan Krukau"
image_creator_url = "https://www.pexels.com/@yankrukov"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T17:30:39+07:00"

[ai_summary]
items = ["DCF (Discounted Cash Flow): Giá = Σ FCF_t × e^(-rt) + Terminal Value × e^(-rT)", "Terminal Value = Final Year FCF × Growth / (Discount Rate - Growth)", "P/E Ratio = Giá / Lợi nhuận (cách nhanh nhất để so sánh)", "PEG Ratio = P/E / Growth Rate (điều chỉnh cho tăng trưởng)", "EV/EBITDA = Enterprise Value / EBITDA (so sánh khác branch)", "Comparable Method: So sánh cổ phiếu tương tự, giá = Average P/E × Earnings", "Intrinsic Value vs Market Price: Nếu Market < Intrinsic → BUY, ngược lại SELL"]

[[internal_links]]
ref = "posts/cong-ty-bao-hiem-dung-toan-hoc-tinh-phi-rui-ro.md"
title = "công ty bảo hiểm dùng toán học đỉnh cao như thế nào để tính phí và rủi ro?"

[[internal_links]]
ref = "posts/blackrock-dung-toan-hoc-va-du-lieu-quan-ly-danh-muc.md"
title = "BlackRock dùng toán học và dữ liệu như thế nào? Quản lý danh mục khổng lồ"

[[internal_links]]
ref = "posts/renaissance-technologies-quantitative-finance-toan-hoc-dau-tu.md"
title = "Renaissance Technologies: Lão phố Wall dùng toán học để kiếm tiền"

[[internal_links]]
ref = "posts/ai-trong-tai-chinh-dung-toan-hoc-gi.md"
title = "AI trong tài chính: Deep learning, NLP, và reinforcement learning"

[[internal_links]]
ref = "posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao.md"
title = "Quỹ đầu tư dùng toán học như thế nào? Từ lợi suất, beta đến tối ưu danh mục"

[[internal_links]]
ref = "posts/goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao.md"
title = "Goldman Sachs & JPMorgan dùng toán học như thế nào? High-frequency trading & derivatives"

[[internal_links]]
ref = "posts/risk-management-trong-tai-chinh-dung-toan-hoc.md"
title = "Risk Management trong tài chính: Từ VaR đến stress testing"

[[internal_links]]
ref = "posts/frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh.md"
title = "FRM dùng toán học gì? VaR, Expected Shortfall, và quản trị rủi ro"
+++
Làm sao biết cổ phiếu là **rẻ hay đắt**?

Dùng **toán học định giá**.

Bài này giải thích:
1. **DCF** (Discounted Cash Flow) — định giá fundamental
2. **Comparable Valuation** — so sánh tương đối
3. **Ratios** — P/E, PEG, EV/EBITDA

---

## DCF (Discounted Cash Flow)


![Minh họa nội dung mo hinh dinh gia co phieu dcf chiet khau dong tien — nguồn Pexels](/images/posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien-inline.webp)

*Nguồn: Pexels / www.kaboompics.com*


### Công thức cơ bản

```
Stock Price = Σ(t=1 to T) FCF_t × e^(-rt) + Terminal Value × e^(-rT)
```

**Ký hiệu:**
- FCF_t = free cash flow năm t
- r = discount rate (WACC)
- T = cuối giai đoạn dự báo (thường 5-10 năm)
- Terminal Value = giá trị sau T năm

### Terminal Value

```
Terminal Value = FCF_T × (1 + g) / (r - g)
```

**Ký hiệu:**
- g = tăng trưởng perpetual (2-3%)
- r = discount rate

### Ví dụ: định giá VietcomBank

Giả định:
- FCF Năm 1-5: 1 tỷ/năm
- FCF Năm 6-10: 1.2 tỷ/năm
- g = 3%, r = 8%

```
TV = 1.2 tỷ × 1.03 / (0.08 - 0.03) = 24.72 tỷ VND

PV(FCF Năm 1-5) = 1×e^(-0.08) + 1×e^(-0.16) + ... ≈ 4 tỷ
PV(TV) = 24.72 × e^(-0.4) ≈ 16.5 tỷ

Total = 4 + 16.5 = 20.5 tỷ VND
```

**Giá cổ phiếu = 20.5 tỷ / (số cổ phiếu)**

---

## Comparable Valuation

Thay vì dự báo future cash flow, so sánh với công ty **tương tự**:

```
Target Stock Price = Target Earnings × Average P/E (peer group)
```

### Ví dụ: định giá Vietinbank

Cổ phiếu ngân hàng tương tự (P/E):
- VietcomBank: P/E = 15
- Techcombank: P/E = 12
- TP Bank: P/E = 14
- **Average = 13.67**

Vietinbank:
- Earnings = 2 tỷ
- **Target Price = 2 tỷ × 13.67 = 27.34 tỷ**

---

## P/E Ratio

### Định nghĩa

```
P/E = Stock Price / Earnings Per Share
```

**Diễn giải:** Bạn phải trả bao nhiêu tiền cho mỗi đôi 1 VND lợi nhuận?

- **P/E = 15:** Trả 15 VND cho 1 VND earnings
- **P/E = 20:** Trả 20 VND cho 1 VND earnings (đắt hơn)

### Ví dụ

VietcomBank:
- Giá = 150,000 VND
- EPS = 10,000 VND
- P/E = 15

→ Bạn trả 150k VND cho 10k earnings/năm.

---

## PEG Ratio

**P/E Growth Ratio** — điều chỉnh cho tăng trưởng:

```
PEG = P/E / Earnings Growth Rate (%)
```

**Giải thích:**
- **PEG < 1:** Rẻ (giá thấp so với tăng trưởng)
- **PEG = 1:** Fair value
- **PEG > 1:** Đắt (giá cao so với tăng trưởng)

### Ví dụ

Cổ phiếu A:
- P/E = 20
- Growth = 25%/năm
- **PEG = 20 / 25 = 0.8** ← Rẻ!

Cổ phiếu B:
- P/E = 20
- Growth = 10%/năm
- **PEG = 20 / 10 = 2.0** ← Đắt!

(Cùng P/E, nhưng B đắt hơn vì tăng trưởng thấp)

---

## EV/EBITDA

**Enterprise Value / EBITDA** — so sánh khác ngành:

```
EV = Market Cap + Debt - Cash
EBITDA = Earnings Before Interest, Tax, Depreciation, Amortization
```

**Ưu điểm:** Không bị ảnh hưởng cấu trúc vốn (debt vs equity).

---

## Intrinsic vs Market Price

```
If Intrinsic Value > Market Price → UNDERVALUED (BUY)
If Intrinsic Value < Market Price → OVERVALUED (SELL)
If Intrinsic Value ≈ Market Price → FAIR VALUE (HOLD)
```

---

## Checklist định giá

✅ DCF = Σ FCF × e^(-rt) + Terminal Value  
✅ Terminal Value = FCF × (1+g) / (r-g)  
✅ Comparable: So sánh P/E peer group  
✅ P/E = Giá / EPS  
✅ PEG = P/E / Growth (điều chỉnh tăng trưởng)  
✅ EV/EBITDA = so sánh khác ngành  

---

## Tiếp theo: Black-Scholes

### Bài viết liên quan

- [công ty bảo hiểm dùng toán học đỉnh cao như thế nào để tính phí và rủi ro?](/posts/cong-ty-bao-hiem-dung-toan-hoc-tinh-phi-rui-ro/)
- [BlackRock dùng toán học và dữ liệu như thế nào? Quản lý danh mục khổng lồ](/posts/blackrock-dung-toan-hoc-va-du-lieu-quan-ly-danh-muc/)
- [Renaissance Technologies: Lão phố Wall dùng toán học để kiếm tiền](/posts/renaissance-technologies-quantitative-finance-toan-hoc-dau-tu/)
- [AI trong tài chính: Deep learning, NLP, và reinforcement learning](/posts/ai-trong-tai-chinh-dung-toan-hoc-gi/)
- [Quỹ đầu tư dùng toán học như thế nào? Từ lợi suất, beta đến tối ưu danh mục](/posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao/)
- [Goldman Sachs & JPMorgan dùng toán học như thế nào? High-frequency trading & derivatives](/posts/goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao/)
- [Risk Management trong tài chính: Từ VaR đến stress testing](/posts/risk-management-trong-tai-chinh-dung-toan-hoc/)
- [FRM dùng toán học gì? VaR, Expected Shortfall, và quản trị rủi ro](/posts/frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh/)

Bài 11: Black-Scholes la gì
