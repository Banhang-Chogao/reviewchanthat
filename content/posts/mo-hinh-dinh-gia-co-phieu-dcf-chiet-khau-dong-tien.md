+++
draft = true
title = "Mô hình định giá cổ phiếu: DCF, Comparable, PEG ratio"
description = "Định giá cổ phiếu dùng toán học nào? Học Discounted Cash Flow (DCF), P/E ratio, PEG, EV/EBITDA, terminal value, và so sánh tương đối."
date = "2026-07-10T13:16:14+07:00"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "Định giá cổ phiếu: DCF, P/E, terminal value, comparable valuation"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["định giá cổ phiếu", "DCF", "P/E ratio", "terminal value", "comparable valuation", "intrinsic value"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 10
image = "images/posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien.webp"
image_alt = "Ảnh minh họa Mô hình định giá cổ phiếu: DCF, Comparable, PEG ratio — nguồn Pixabay"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"

[ai_summary]
items = ["DCF (Discounted Cash Flow): Giá = Σ FCF_t × e^(-rt) + Terminal Value × e^(-rT)", "Terminal Value = Final Year FCF × Growth / (Discount Rate - Growth)", "P/E Ratio = Giá / Lợi nhuận (cách nhanh nhất để so sánh)", "PEG Ratio = P/E / Growth Rate (điều chỉnh cho tăng trưởng)", "EV/EBITDA = Enterprise Value / EBITDA (so sánh khác branch)", "Comparable Method: So sánh cổ phiếu tương tự, giá = Average P/E × Earnings", "Intrinsic Value vs Market Price: Nếu Market < Intrinsic → BUY, ngược lại SELL"]
thumbnail = "images/posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien.webp"
image_source = "Pixabay"
image_source_url = "https://pixabay.com/photos/bugs-loan-green-7408590/"
image_provider = "pixabay"
image_license = "Pixabay Content License"
image_license_url = ""
image_commercial_use = true
image_owner = "external"
image_creator = "jarino47"
image_creator_url = "https://pixabay.com/photos/bugs-loan-green-7408590/"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pixabay_api"
image_status = "verified"
image_attribution_checked_at = "2026-07-10T14:01:44+07:00"
image_query = "atm banking transaction"
+++

Làm sao biết cổ phiếu là **rẻ hay đắt**?

Dùng **toán học định giá**.

Bài này giải thích:
1. **DCF** (Discounted Cash Flow) — định giá fundamental
2. **Comparable Valuation** — so sánh tương đối
3. **Ratios** — P/E, PEG, EV/EBITDA

---

## DCF (Discounted Cash Flow)

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

### Ví dụ: Định giá VietcomBank

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

### Ví dụ: Định giá Vietinbank

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

## Checklist Định giá

✅ DCF = Σ FCF × e^(-rt) + Terminal Value  
✅ Terminal Value = FCF × (1+g) / (r-g)  
✅ Comparable: So sánh P/E peer group  
✅ P/E = Giá / EPS  
✅ PEG = P/E / Growth (điều chỉnh tăng trưởng)  
✅ EV/EBITDA = so sánh khác ngành  

---

## Tiếp theo: Black-Scholes

Bài 11: Black-Scholes la gì
