+++
title = "Log tự nhiên trong đầu tư là gì? Vì sao giới tài chính dùng log-return?"
description = "Log-return là gì và vì sao quỹ đầu tư, AI tài chính dùng ln(Pt/Pt-1) thay vì simple return? Tìm hiểu công thức, ví dụ cổ phiếu và tính chất cộng dồn."
date = "2026-07-10T11:00:00+07:00"
slug = "log-tu-nhien-log-return-trong-dau-tu"
aliases = ["/posts/log-tự-nhiên-trong-đầu-tư-là-gì-vì-sao-giới-tài-chính-dùng-log-return/"]
commit = "53131412"
lastmod = "2026-07-10T11:00:00+07:00"
seo_title = "Log-return là gì: công thức ln(Pt/Pt-1) trong đầu tư"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["log-return", "log tự nhiên", "lợi suất logarit", "ln trong tài chính", "cổ phiếu", "machine learning tài chính"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 2
image = "images/posts/log-tu-nhien-log-return-trong-dau-tu.webp"
date_display = "10-07-2026 11:00:00 GMT +7"
lastmod_display = "10-07-2026 11:00:00 GMT +7"
thumbnail = "images/posts/log-tu-nhien-log-return-trong-dau-tu.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/stock-market-chart-displaying-bearish-trend-35118208/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Alex Luna"
image_creator_url = "https://www.pexels.com/@al3jandr0"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T17:30:38+07:00"
draft = false

[ai_summary]
items = ["Log tự nhiên (ln) là hàm ngược của e: nếu e^x = y thì ln(y) = x", "Log-return: R = ln(Pt/Pt-1) — cách tính lợi suất bằng logarit thay vì phần trăm thông thường", "So sánh: simple return (+10%, -5%) ≠ cộng = +4.5% nhưng log-return (+9.53%, -5.13%) ✓ cộng = +4.40%", "Tính chất cộng dồn: Rtotal = R1 + R2 + ... + Rn — đây là lý do giới định lượng dùng log-return", "Ví dụ thực tế: VietcomBank giá 100k → 110k → 104.5k (so sánh 2 cách tính)", "Ứng dụng: quỹ đầu tư tính volatility, machine learning forecast thị trường, quản trị rủi ro dùng log-return", "Vì sao: log-return đối xứng (50% rồi -33% = neutral), phân phối chuẩn, phù hợp time-series analysis"]
draft = false

[[internal_links]]
ref = "posts/ai-trong-tai-chinh-dung-toan-hoc-gi.md"
title = "AI trong tài chính: Deep learning, NLP, và reinforcement learning"

[[internal_links]]
ref = "posts/toan-hoc-dinh-cao-trong-tai-chinh.md"
title = "Toán học đỉnh cao trong tài chính - PILLAR tổng kết 15 bài"

[[internal_links]]
ref = "posts/quy-dau-tu-dung-toan-hoc-nhu-the-nao.md"
title = "Quỹ đầu tư dùng toán học như thế nào? Từ lợi suất, beta đến tối ưu danh mục"
+++

Khi bạn đầu tư vào cổ phiếu VietcomBank với giá 100,000 đồng, giá tăng lên 110,000 (+10%), rồi giảm xuống 104,500 (-5%), lợi suất cuối cùng là bao nhiêu?

Nếu bạn cộng đơn giản: 10% + (-5%) = 5%, nhưng lợi suất thực tế là (104,500 - 100,000) / 100,000 = **4.5%**. Chênh lệch 0.5%—tuy nhỏ nhưng lý thuyết sai.

Giới tài chính dùng **log-return** để giải quyết vấn đề này. Log-return không chỉ cho kết quả chính xác 4.4%, mà còn **cộng dồn hoàn hảo** (9.53% + (-5.13%) = 4.40%), làm cho việc phân tích dữ liệu cổ phiếu, crypto, và xây dựng mô hình AI trở nên đơn giản hơn rất nhiều.

Bài này giải thích:
1. Log tự nhiên (ln) là gì
2. Log-return là gì
3. So sánh simple return vs log-return
4. Tính chất cộng dồn
5. Ví dụ cụ thể VietcomBank
6. Ứng dụng trong quỹ, AI, risk management

---

## Log tự nhiên (ln) là gì?


![Minh họa nội dung log tu nhien log return trong dau tu — nguồn Pexels](/images/posts/log-tu-nhien-log-return-trong-dau-tu-inline.webp)

*Nguồn: Pexels / Yan Krukau*


**Log tự nhiên (natural logarithm)** ký hiệu **ln** là **hàm ngược của e**:

```
Nếu e^x = y  ⟹  ln(y) = x
```

**Ví dụ:**
- e^1 = 2.71828... ⟹ ln(2.71828) = 1
- e^0 = 1 ⟹ ln(1) = 0
- e^(0.5) ≈ 1.6487 ⟹ ln(1.6487) = 0.5

**Tính chất quan trọng:**
```
ln(a × b) = ln(a) + ln(b)
ln(a / b) = ln(a) - ln(b)
```

Nhìn có vẻ "chuyên môn", nhưng tính chất này là **chìa khóa để log-return cộng dồn**. Ta sẽ thấy ngay.

---

## Log-return là gì?

Thay vì tính lợi suất theo cách thông thường:
```
Simple return = (Pt - Pt-1) / Pt-1
```

Giới tài chính dùng:
```
Log-return = ln(Pt / Pt-1)
```

**Ký hiệu:**
- Pt = giá tại thời điểm t
- Pt-1 = giá tại thời điểm t-1
- ln = logarit tự nhiên

---

## So sánh: Simple Return vs Log-Return

### Ví dụ: Giá tăng 10% rồi giảm 5%

**Ngày 1:** Giá 100,000 → 110,000 VND (+10%)  
**Ngày 2:** Giá 110,000 → 104,500 VND (-5%)

### Cách 1: Simple Return (phương pháp thông thường)

```
R1 = (110,000 - 100,000) / 100,000 = 10%
R2 = (104,500 - 110,000) / 110,000 = -4.91%

Tổng lợi suất = (104,500 - 100,000) / 100,000 = 4.5%

Nhưng: 10% + (-4.91%) = 5.09% ≠ 4.5% ✗
```

**Vấn đề:** Không thể cộng đơn giản! Lũy suất lên nhau theo kiểu nhân, không phải cộng.

### Cách 2: Log-Return (phương pháp tài chính)

```
R1 = ln(110,000 / 100,000) = ln(1.10) ≈ 0.0953 (= 9.53%)
R2 = ln(104,500 / 110,000) = ln(0.9545) ≈ -0.0513 (= -5.13%)

Tổng = 0.0953 + (-0.0513) = 0.0440 (= 4.40%)

Kiểm tra: ln(104,500 / 100,000) = ln(1.045) = 0.0440 ✓
```

**Ưu điểm:** Cộng dồn hoàn hảo! 9.53% + (-5.13%) = 4.40% chính xác.

### Bảng so sánh

| **Giai đoạn** | **Giá** | **Simple Return** | **Log-Return** |
|---|---|---|---|
| 0 | 100,000 | — | — |
| 1 | 110,000 | 10.00% | 9.53% |
| 2 | 104,500 | -4.91% | -5.13% |
| **Tổng** | — | 4.50% (từ công thức) | **4.40%** ✅ |
| **Tổng (cộng)** | — | 5.09% ≠ 4.50% ❌ | **4.40%** ✅ |

---

## Tính chất cộng dồn hoàn hảo

Đây là sức mạnh thực sự của log-return.

**Với N giai đoạn:**
```
Rtotal = ln(Pt / Pt-1) + ln(Pt-1 / Pt-2) + ... + ln(P1 / P0)
       = ln( (Pt / Pt-1) × (Pt-1 / Pt-2) × ... × (P1 / P0) )  [sử dụng ln(a×b) = ln(a) + ln(b)]
       = ln(Pt / P0)
```

**Diễn giải:** Tổng log-return từ ngày 0 đến ngày t chính bằng ln(giá cuối / giá đầu).

**Ví dụ 3: Giá 100 → 150 → 100**

```
Simple return: +50% rồi -33.33% = +16.67% (cộng) nhưng lợi suất thực = 0% ✗
Log-return: ln(1.50) + ln(2/3) = 0.4055 + (-0.4055) = 0 ✓
```

**Tính đối xứng:** +50% rồi -33.33% = net 0%. Log-return nhận diện ngay; simple return thì không.

---

## Ứng dụng trong đầu tư thực tế

### 1. Quỹ đầu tư

Quỹ tính volatility (biến động) của cổ phiếu bằng **độ lệch chuẩn của log-return hàng ngày**:

```
σ (volatility) = stdev(R1, R2, R3, ..., Rn)
```

Nếu dùng simple return, tính toán sẽ phức tạp hơn vì không thể cộng đơn giản.

### 2. Machine Learning / AI Tài chính

AI dùng log-return để:
- **Forecast giá** (time-series prediction)
- **Phát hiện pattern** (pattern recognition)
- **Tối ưu danh mục** (portfolio optimization)

Lý do: Log-return **gần với phân phối chuẩn** (normal distribution), nên các mô hình thống kê hoạt động tốt hơn.

### 3. Quản trị rủi ro

VaR (Value at Risk) tính toán dựa trên **log-return history**:

```
Xác suất mất 5% trong ngày = P(R < -0.0513)
```

Cộng dồn hoàn hảo giúp quản lý rủi ro cho danh mục nhiều ngày/tháng.

### 4. Định lượng (Quant)

Quant analyst dùng log-return để:
- Tính **correlation** giữa các cổ phiếu
- Xây dựng **factor model**
- Phát triển **trading strategy**

---

## Vì sao log-return tốt hơn?

### ✅ Tính chất cộng dồn

Rtotal = R1 + R2 + ... + Rn (chính xác, không cần nhân)

### ✅ Đối xứng

+50% rồi -33% = neutral log-return (0%)  
Simple return nhận diện sai.

### ✅ Phân phối chuẩn

Log-return theo phân phối chuẩn gần hơn simple return, nên phù hợp thống kê.

### ✅ Time-series analysis

ARIMA, GARCH, các mô hình chuỗi thời gian khác **yêu cầu log-return**.

### ✅ Continuity

Công thức A = Pe^(rt) từ Bài 1 kết nối với log-return:
```
Nếu A = Pe^(rt)  ⟹  ln(A/P) = rt  ⟹  ln(A/P) / t = r
```

---

## Checklist người mới

✅ **ln là hàm ngược của e:** e^x = y ⟹ ln(y) = x  
✅ **Log-return = ln(Pt/Pt-1)**  
✅ **Tính chất cộng dồn:** R1 + R2 + ... = ln(Pt/P0)  
✅ **Simple return ≠ log-return** (chênh lệch nhỏ với return nhỏ, lớn với return lớn)  
✅ **Ứng dụng:** quỹ, AI, risk, quant  
✅ **Tại sao:** cộng dồn, đối xứng, phân phối chuẩn  

---

## Kết luận: Cầu nối đến Bài 3 & beyond

**Log-return là ngôn ngữ thôi thúc của tài chính chuyên nghiệp.**

- **Bài 1** dạy bạn lãi kép liên tục (A = Pe^(rt))
- **Bài 2** dạy bạn log-return (R = ln(Pt/Pt-1))
- **Bài 3 trở đi:** Quỹ dùng log-return để tối ưu danh mục, quỹ dùng nó để quản lý rủi ro, Black-Scholes dùng nó để định giá quyền chọn

Tiếp theo: **"Quỹ đầu tư dùng toán học như thế nào?"** — nơi log-return meets portfolio theory, efficient frontier, và Sharpe ratio.
