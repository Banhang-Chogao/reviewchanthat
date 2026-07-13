+++
draft = false
title = "CFA dùng toán học gì? Những công thức quản lý tài sản"
description = "CFA dùng toán học gì? Tìm hiểu present value (PV), DCF, correlation, beta, tracking error, information ratio và performance attribution trong quản lý tài sản."
date = "2026-07-10T13:16:14+07:00"
slug = "cfa-dung-toan-hoc-gi"
aliases = ["/posts/cfa-dùng-toán-học-gì-những-công-thức-quản-lý-tài-sản/"]
commit = "25880a45"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "CFA: DCF, PV, beta, tracking error, information ratio"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["CFA", "DCF", "present value", "beta", "tracking error", "information ratio", "quản lý tài sản"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 5
image = "images/posts/cfa-dung-toan-hoc-gi.webp"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"
thumbnail = "images/posts/cfa-dung-toan-hoc-gi.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/a-man-in-corporate-attire-reading-a-book-on-a-couch-7821903/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "RDNE Stock project"
image_creator_url = "https://www.pexels.com/@rdne"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T17:30:38+07:00"

[ai_summary]
items = ["CFA Level 1: Tài chính cơ bản, DCF, PV = Σ CF_t × e^(-rt)", "Beta = Cov(Ra, Rm) / Var(Rm) — độ nhạy so với thị trường", "Tracking Error = σ(Return_fund - Return_benchmark)", "Information Ratio = (Return_fund - Return_benchmark) / Tracking Error", "CFA Level 2: Equity valuation (P/E, FCF), fixed income (duration, convexity)", "CFA Level 3: Portfolio management, constraints, risk budgeting", "Ứng dụng: phân tích cổ phiếu, quản lý danh mục, đánh giá quỹ"]

[[internal_links]]
ref = "posts/mo-hinh-dinh-gia-co-phieu-dcf-chiet-khau-dong-tien.md"
title = "Mô hình định giá cổ phiếu: DCF, Comparable, PEG ratio"

[[internal_links]]
ref = "posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao.md"
title = "Quỹ đầu tư dùng toán học như thế nào? Từ lợi suất, beta đến tối ưu danh mục"

[[internal_links]]
ref = "posts/ham-so-mu-e-trong-tai-chinh-la-gi.md"
title = "Hàm số mũ e trong tài chính là gì? Từ lãi kép đến định giá tài sản"
+++

CFA (Chartered Financial Analyst) là chứng chỉ cao nhất trong quản lý tài sản. CFAs dùng **toán học cao cấp** để:
1. phân tích giá trị công ty (DCF, PV)
2. Đo rủi ro danh mục (beta, tracking error)
3. Đánh giá hiệu suất quỹ (information ratio, attribution)

Bài này giải thích **CFA mathematics**.

---

## CFA là gì?


![Minh họa nội dung cfa dung toan hoc gi — nguồn Pexels](/images/posts/cfa-dung-toan-hoc-gi-inline.webp)

*Nguồn: Pexels / Tima Miroshnichenko*


**Chartered Financial Analyst** = chứng chỉ do CFA Institute cấp.

3 cấp:
- **Level 1:** Tài chính cơ bản, định giá, quản lý danh mục
- **Level 2:** phân tích sâu (equity, bond, derivatives), wording chuẩn
- **Level 3:** Portfolio management, performance attribution

---

## DCF & Present Value

### Công thức cơ bản

```
PV = Σ(t=1 to n) CF_t × e^(-rt)
```

**Hoặc:**

```
PV = CF_1 × e^(-r) + CF_2 × e^(-2r) + ... + CF_n × e^(-nr)
```

**Ký hiệu:**
- CF_t = dòng tiền năm t
- r = lãi suất chiết khấu
- t = năm
- e = số Euler

### Ví dụ: định giá công ty

công ty dự kiến dòng tiền tự do (FCF):
- Năm 1-5: 10 tỷ VND/năm
- Năm 6-10: 12 tỷ VND/năm
- Terminal value (năm 11+): 150 tỷ VND

Lãi suất chiết khấu: 8%/năm

```
PV = 10×e^(-0.08) + 10×e^(-0.16) + ... + 150×e^(-0.8)
   = 10×0.923 + 10×0.852 + ... + 150×0.449
   ≈ 95 tỷ VND
```

**giá trị công ty ≈ 95 tỷ VND**

---

## Beta và rủi ro Hệ thống

### Công thức

```
β = Cov(Ra, Rm) / Var(Rm)
```

**Ký hiệu:**
- β = beta (hệ số nhạy)
- Cov(Ra, Rm) = hiệp phương sai lợi suất tài sản với lợi suất thị trường
- Var(Rm) = phương sai lợi suất thị trường

### Diễn giải

- **β = 1:** Tài sản biến động bằng thị trường
- **β > 1:** Tài sản biến động hơn thị trường (rủi ro cao)
- **β < 1:** Tài sản ít biến động hơn thị trường (rủi ro thấp)

### Ví dụ: Cổ phiếu FPT (β = 1.2)

Nếu thị trường tăng 10%:
```
Kỳ vọng lợi suất FPT ≈ 1.2 × 10% = 12%
```

FPT rủi ro hơn thị trường → beta cao.

---

## Tracking Error

### Công thức

```
Tracking Error = σ(Return_fund - Return_benchmark)
```

**Diễn giải:** Độ lệch chuẩn giữa lợi suất quỹ và chỉ số.

### Ví dụ: Quỹ dùng lệch chỉ số (active management)

Quỹ theo dõi VN-Index nhưng cấu trúc danh mục khác:
- Nếu tracking error = 2%, quỹ lệch VN-Index ±2% (độ lệch cao → chủ động)
- Nếu tracking error = 0.3%, quỹ theo sát VN-Index (độ lệch thấp → bị động)

---

## Information Ratio

### Công thức

```
IR = (Return_fund - Return_benchmark) / Tracking Error
```

**Diễn giải:** Lợi nhuận thặng dư trên mỗi đơn vị rủi ro lệch.

### Ví dụ: Quỹ so với VN-Index

- Return_fund = 15%/năm
- Return_benchmark (VN-Index) = 12%/năm
- Tracking Error = 3%

```
IR = (15% - 12%) / 3% = 1.0
```

**IR = 1.0** = Quỹ sinh ra 1% lợi nhuận thặng dư trên mỗi 1% rủi ro lệch → tốt!

---

## Performance Attribution

CFA Level 3 dùng **attribution** để phân tích:

```
Excess Return = Allocation Effect + Selection Effect
```

**Allocation Effect:** Lựa chọn ngành sai so với benchmark  
**Selection Effect:** Chọn cổ phiếu tốt trong ngành

### Ví dụ

| Ngành | Weight (Fund) | Weight (Bench) | Return (Fund) | Return (Bench) |
|---|---|---|---|---|
| Ngân hàng | 40% | 35% | 12% | 10% |
| Bán lẻ | 30% | 40% | 8% | 7% |

**Allocation:** Bỏ thêm 5% vào ngân hàng (lợi nhuận) → **+0.1%**  
**Selection:** Chọn ngân hàng tốt hơn (+2%) → **+0.8%**

---

## Constraints & Risk Budgeting (Level 3)

CFA Level 3 dạy:

```
Risk Budget = Σ Beta_i × Allocation_i
```

CFAs phân bổ **rủi ro có sẵn** trên các bộ phận danh mục tối ưu.

---

## Checklist CFA

✅ DCF = định giá công ty bằng dòng tiền chiết khấu  
✅ PV = e^(-rt) (Bài 1 kết nối!)  
✅ Beta = Cov(Ra, Rm) / Var(Rm)  
✅ Tracking Error = độ lệch khỏi chỉ số  
✅ IR = lợi nhuận thặng dư / rủi ro  
✅ Attribution = phân tích allocation + selection  

---

## Tiếp theo: FRM

Bài 6: FRM dùng toán học gì
