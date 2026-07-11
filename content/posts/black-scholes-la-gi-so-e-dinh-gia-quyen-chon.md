+++
draft = false
title = "Black-Scholes là gì? Công thức định giá quyền chọn sử dụng số e"
description = "Black-Scholes là công thức định giá option nổi tiếng. Học C = S×Φ(d1) - K×e^(-rT)×Φ(d2), Greeks, implied volatility, và ứng dụng thực tế."
date = "2026-07-10T13:16:14+07:00"
commit = "f8496fd"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "Black-Scholes: định giá option, call price, implied volatility"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["Black-Scholes", "option pricing", "call option", "put option", "implied volatility", "Greeks", "derivative"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 11
image = "images/posts/black-scholes-la-gi-so-e-dinh-gia-quyen-chon.webp"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"
thumbnail = "images/posts/black-scholes-la-gi-so-e-dinh-gia-quyen-chon.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/multiple-graphs-on-a-laptop-screen-6770610/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Alesia  Kozik"
image_creator_url = "https://www.pexels.com/@alesiakozik"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T14:44:35+07:00"

[ai_summary]
items = ["Black-Scholes: Công thức định giá call option được phát hiện năm 1973", "C = S×Φ(d1) - K×e^(-rT)×Φ(d2) — thứ nhất thấy e^(-rT) từ Bài 1!", "d1, d2 = công thức logarit + phân phối chuẩn để tính Φ (cumulative normal CDF)", "Giả định: σ hằng số, không có dividend, European option (chỉ thực hiện khi expiry)", "Implied Volatility: Đảo ngược công thức để tìm σ từ giá market", "Put-Call Parity: C - P = S - K×e^(-rT) (mối quan hệ call/put)", "Thực tế: Volatility Smile, American options, dividend adjustment cần mô hình phức tạp hơn"]
+++

**Black-Scholes** — công thức định giá **quyền chọn (option)** nổi tiếng nhất.

Được **Robert Merton, Myron Scholes** phát hiện năm 1973 (Nobel Prize 1997).

Công thức này là **cái cơ" của derivatives pricing**.

---

## Black-Scholes Formula


![Minh họa nội dung black scholes la gi so e dinh gia quyen chon — nguồn Pexels](/images/posts/black-scholes-la-gi-so-e-dinh-gia-quyen-chon-inline.webp)

*Nguồn: Pexels / AlphaTradeZone*


### Call Option Price

```
C = S × Φ(d1) - K × e^(-rT) × Φ(d2)
```

**Ký hiệu:**
- S = giá cổ phiếu hiện tại
- K = strike price (giá thực hiện)
- r = lãi suất phi rủi ro
- T = thời gian đến expiry (năm)
- σ = volatility (độ biến động hàng năm)
- Φ = cumulative normal distribution function (CDF)
- e^(-rT) = discount factor (từ Bài 1!)

### Công thức d1, d2

```
d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
d2 = d1 - σ√T
```

**Diễn giải:**
- ln(S/K) = log-return từ now đến strike (Bài 2!)
- (r + σ²/2)T = drift + volatility adjustment
- σ√T = volatility scaling (time)

### Ví dụ: Call Option VietcomBank

Giả định:
- S = 150,000 VND
- K = 150,000 VND (at-the-money)
- T = 1 năm
- r = 5%
- σ = 20%

```
d1 = [ln(1) + (0.05 + 0.04/2)×1] / (0.2×1) = 0.35
d2 = 0.35 - 0.2 = 0.15

Φ(d1) ≈ 0.637
Φ(d2) ≈ 0.560

C = 150,000 × 0.637 - 150,000 × e^(-0.05) × 0.560
  = 95,550 - 150,000 × 0.9512 × 0.560
  = 95,550 - 80,082
  ≈ 15,468 VND
```

**Call option price ≈ 15,468 VND**

---

## Put Option (European)

Put-Call Parity:
```
C - P = S - K × e^(-rT)
```

**Diễn giải:** Nếu biết call price, tính put = Call - (S - K×e^(-rT))

### Ví dụ

Từ ví dụ trên:
```
P = C - S + K×e^(-rT)
  = 15,468 - 150,000 + 150,000×0.9512
  = 15,468 - 150,000 + 142,680
  ≈ 8,148 VND
```

**Put option price ≈ 8,148 VND**

---

## Implied Volatility

Thực tế, option được giao dịch ở **market price**, chứ không theo Black-Scholes.

Giới phân tích **đảo ngược** công thức:

```
Given: Market Call Price = 16,000 VND
Find: σ sao cho C(σ) = 16,000
```

**Công thức bậc 2 không giải được, dùng numerical methods (Newton-Raphson).**

**Kết quả:** σ ≈ 21.5%

→ **Implied Vol = 21.5%** (cao hơn dự báo 20%)

**Diễn giải:** Market kỳ vọng biến động cao hơn norm → call option đắt.

---

## Giả định Black-Scholes

1. **σ hằng số:** Thực tế σ thay đổi (volatility smile)
2. **European option:** Chỉ thực hiện khi expiry (American option phức tạp hơn)
3. **Không dividend:** Cổ phiếu trả cổ tức → cần điều chỉnh
4. **Lãi suất hằng số:** Thực tế lãi suất thay đổi
5. **Lognormal distribution:** Log-return phân phối chuẩn

**Mở rộng:** Volatility smile, stochastic vol models, American option (binomial tree), dividend adjustment.

---

## Ứng dụng

1. **Hedging:** công ty bảo vệ rủi ro bằng options
2. **Speculation:** Trader kiếm lợi từ chênh lệch price vs Black-Scholes
3. **Employee Stock Options:** công ty tính giá trị compensation cho nhân viên

---

## Checklist Black-Scholes

✅ C = S×Φ(d1) - K×e^(-rT)×Φ(d2)  
✅ d1 = [ln(S/K) + (r+σ²/2)T] / (σ√T)  
✅ d2 = d1 - σ√T  
✅ Put-Call Parity: C - P = S - K×e^(-rT)  
✅ Implied Vol: Đảo ngược công thức tìm σ  
✅ Giả định: σ hằng, European, lognormal  

---

## Tiếp theo: Risk Management

Bài 12: Risk Management trong tài chính
