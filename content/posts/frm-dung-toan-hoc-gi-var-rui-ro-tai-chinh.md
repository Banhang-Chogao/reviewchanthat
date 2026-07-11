+++
draft = false
title = "FRM dùng toán học gì? VaR, Expected Shortfall, và quản trị rủi ro"
description = "FRM (Financial Risk Manager) dùng toán học nào? Học VaR (Value at Risk), Expected Shortfall (CVaR), extreme value theory, stress testing, backtesting, và mon itor rủi ro."
date = "2026-07-10T13:16:14+07:00"
commit = "9008aff"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "FRM: VaR, Expected Shortfall, quản trị rủi ro tài chính"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["FRM", "VaR", "Expected Shortfall", "rủi ro tài chính", "backtesting", "stress test"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 6
image = "images/posts/frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh.webp"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"
thumbnail = "images/posts/frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/a-person-holding-a-report-paper-7876387/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "www.kaboompics.com"
image_creator_url = "https://www.pexels.com/@karola-g"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T16:20:39+07:00"

[ai_summary]
items = ["FRM = Financial Risk Manager, chứng chỉ về quản trị rủi ro tài chính", "VaR (Value at Risk): Mất tối đa $ với xác suất X% trong 1 ngày", "VaR = Portfolio Value × |Z| × Volatility (với Z là z-score 1%, 5%, etc)", "Expected Shortfall (CVaR) = mất lỗ trung bình trong các trường hợp tồi tệ", "Lịch sử: Dùng log-return lịch sử để ước lượng VaR (Historical Simulation)", "Monte Carlo: Mô phỏng 10k+ kịch bản để tính VaR", "Backtesting: Kiểm tra VaR model có chính xác không (exceptions test)"]
+++

FRM (Financial Risk Manager) là chứng chỉ quản trị rủi ro của GARP. FRMs dùng **toán học xác suất cao cấp** để:

1. Ước lượng **mất lỗ tối đa** (VaR)
2. Tính **rủi ro đuôi phân phối** (extreme events)
3. Kiểm tra mô hình rủi ro (backtesting)

Bài này giải thích **FRM mathematics**.

---

## VaR (Value at Risk)


![Minh họa nội dung frm dung toan hoc gi var rui ro tai chinh — nguồn Pexels](/images/posts/frm-dung-toan-hoc-gi-var-rui-ro-tai-chinh-inline.webp)

*Nguồn: Pexels / Yan Krukau*


### Định nghĩa

```
VaR_α = giá trị (tổn thất) tối đa ở mức tin cậy α%
```

**Ví dụ:** VaR_99% = $1 triệu với 1 ngày

→ Có 99% xác suất mất ≤ $1 triệu trong 1 ngày  
→ Có 1% xác suất mất > $1 triệu

### Công thức (Parametric VaR)

```
VaR = Portfolio Value × |Z_α| × σ
```

**Ký hiệu:**
- Z_α = z-score (1.645 cho 95%, 2.326 cho 99%)
- σ = volatility (độ lệch chuẩn log-return)
- Portfolio Value = tổng giá trị danh mục

### Ví dụ: danh mục 100 tỷ VND

Giả định:
- danh mục = 100 tỷ VND
- Volatility = 15%/năm = 0.95%/ngày (15% / √252)
- Mức tin cậy = 99%

```
VaR_99% = 100 tỷ × 2.326 × 0.95%
        = 100 tỷ × 2.326 × 0.0095
        ≈ 2.2 tỷ VND
```

**Diễn giải:** Có 99% xác suất mất ≤ 2.2 tỷ VND trong 1 ngày.

---

## Expected Shortfall (CVaR)

### Công thức

```
ES_α = E[Loss | Loss > VaR_α]
```

**Diễn giải:** Mất lỗ **trung bình** khi vượt quá VaR.

### Ví dụ

Nếu VaR_99% = 2.2 tỷ VND, Expected Shortfall _99% có thể là **2.8 tỷ VND**.

→ Khi xảy ra sự kiện 1% (tồi tệ), mất lỗ trung bình ~2.8 tỷ VND (không phải 2.2).

---

## Historical Simulation

FRMs thường dùng lịch sử để ước lượng VaR:

1. Thu thập log-return hàng ngày (250 ngày)
2. Sắp xếp từ tồi nhất đến tốt nhất
3. VaR_99% = return ở vị trí 2-3 tồi nhất (1% của 250 days)

### Ví dụ

250 ngày, sắp xếp return:
- Tồi nhất: -3.5%
- Thứ 2: -3.2%
- Thứ 3: -2.9%

VaR_99% ≈ -3.2% (giả định 1 ngày)

---

## Monte Carlo

FRMs cũng dùng **Monte Carlo** để mô phỏng rủi ro:

1. Sinh 10,000+ kịch bản random (theo phân phối chuẩn, log-return lịch sử)
2. Tính portfolio return cho mỗi kịch bản
3. Sắp xếp → VaR_99% = 1% tồi nhất

**Ưu điểm:** Bắt được **rủi ro phi tuyến** (ví dụ: derivatives, options).

---

## Backtesting

FRMs phải **kiểm tra mô hình VaR có chính xác không**.

### Phương pháp

Dùng dữ liệu quá khứ 1 năm:
- Tính VaR_99% mỗi ngày
- Đếm số lần thực tế thua > VaR_99%
- Kỳ vọng: 2-3 lần/năm (1% của 252 ngày)

**Nếu > 4-5 lần:** Mô hình thiếu tin cậy → cần điều chỉnh.

---

## Stress Testing

Ngoài VaR, FRMs chạy **stress test**:

```
Stress Test = Kiểm tra portfolio trong các kịch bản cực đoan
```

**Ví dụ:**
- "Nếu lãi suất tăng 2% ngay hôm nay?"
- "Nếu thị trường rơi 30% như 2008?"
- "Nếu VN-Index -5% và VND mất 10% so USD?"

---

## Liquidity Risk

FRMs cũng lo **rủi ro thanh khoản**:

```
Liquidity VaR = VaR + Spread Cost + Time to Exit
```

**Ví dụ:** 
- VaR thống kê = 1 tỷ
- Nhưng bán ra trên thị trường → mất thêm spread 0.5 tỷ
- Liquidity VaR = 1.5 tỷ

---

## Checklist FRM

✅ VaR = Portfolio × Z_α × σ  
✅ Expected Shortfall = mất lỗ trung bình trong 1% tồi tệ  
✅ Historical Simulation = từ lịch sử log-return  
✅ Monte Carlo = mô phỏng 10k+ kịch bản  
✅ Backtesting = kiểm tra mô hình  
✅ Stress Test = kịch bản cực đoan  

---

## Tiếp theo: Goldman Sachs & JPMorgan

Bài 7: Goldman Sachs, JPMorgan dùng toán học như thế nào
