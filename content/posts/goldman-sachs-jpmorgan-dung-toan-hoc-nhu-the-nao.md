+++
draft = false
title = "Goldman Sachs & JPMorgan dùng toán học như thế nào? High-frequency trading & derivatives"
description = "Goldman Sachs, JPMorgan dùng toán học gì? Học algorithmic trading, derivatives pricing, volatility smile, Greeks (delta, gamma, vega), stochastic models, machine learning."
date = "2026-07-10T13:16:14+07:00"
commit = "f8496fd"
lastmod = "2026-07-10T14:10:36+07:00"
seo_title = "Goldman Sachs, JPMorgan: derivatives pricing, Greeks, HFT"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["Goldman Sachs", "JPMorgan", "derivatives", "Greeks", "high-frequency trading", "volatility smile"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 7
image = "images/posts/goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao.webp"
date_display = "10-07-2026 13:16:14 GMT +7"
lastmod_display = "10-07-2026 14:10:36 GMT +7"
thumbnail = "images/posts/goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/iconic-wall-street-skyline-in-new-york-city-33471680/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Colwyn Davis"
image_creator_url = "https://www.pexels.com/@colwyn-davis-1763356180"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T16:20:40+07:00"

[ai_summary]
items = ["Goldman Sachs, JPMorgan: 2 ngân hàng đầu tư lớn nhất thế giới", "Derivatives pricing: Black-Scholes, local volatility, stochastic volatility", "Greeks: Delta (độ nhạy giá), Gamma (độ cong), Vega (độ nhạy volatility)", "Volatility Smile: σ thay đổi theo strike price (không hằng số)", "Algorithmic Trading: Machines tự động mua/bán hàng triệu giao dịch/ngày", "Market Microstructure: Spread, latency, order flow prediction", "Machine Learning: Neural networks dự báo giá, market impact models"]
+++

Goldman Sachs & JPMorgan là 2 ngân hàng đầu tư lớn nhất. Họ dùng **toán học cực kỳ phức tạp** cho:

1. **định giá derivatives** (options, swaps, exotics)
2. **Giao dịch cao tần** (high-frequency trading)
3. **Quản lý rủi ro** (VaR, Greeks, hedging)

Bài này giải thích **mathematics of investment banks**.

---

## Derivatives Pricing


![Minh họa nội dung goldman sachs jpmorgan dung toan hoc nhu the nao — nguồn Pexels](/images/posts/goldman-sachs-jpmorgan-dung-toan-hoc-nhu-the-nao-inline.webp)

*Nguồn: Pexels / Egor Komarov*


### Black-Scholes (cơ bản)

```
C = S×Φ(d1) - K×e^(-rT)×Φ(d2)
```

Đây chúng ta thấy **e^(-rT)** từ Bài 1!

Nhưng Black-Scholes giả định volatility **hằng số**, điều này **không đúng** trong thực tế.

### Volatility Smile

Thực tế, σ thay đổi theo strike price:

```
σ(K) = σ₀ + a×(K - F) + b×(K - F)²
```

**Diễn giải:** Phương trình bậc 2 để fit volatility curve.

---

## Greeks

Investment banks phải hedging continuous. Họ dùng **Greeks** để đo rủi ro:

### Delta (Δ)

```
Δ = ∂C / ∂S
```

**Diễn giải:** Nếu giá tăng $1, call option tăng $Δ.

**Hedging:** Nếu Δ = 0.6, bán 0.6 cổ phiếu để hedge 1 call option.

### Gamma (Γ)

```
Γ = ∂Δ / ∂S
```

**Diễn giải:** Tốc độ thay đổi của Delta. Gamma cao = rủi ro cao.

### Vega (ν)

```
ν = ∂C / ∂σ
```

**Diễn giải:** Nếu volatility tăng 1%, call option tăng $ ν.

---

## Stochastic Volatility Models

Thay vì σ hằng số, các banks dùng:

```
dS = μS dt + σ(t) S dW₁
dσ = κ(θ - σ) dt + ξ σ dW₂
```

**Ký hiệu:**
- S = giá cổ phiếu
- σ(t) = volatility (thay đổi theo thời gian)
- dW = Brownian motion (ngẫu nhiên)

**Ưu điểm:** Bắt được volatility smile, clustering volatility.

---

## Algorithmic Trading

Goldman Sachs, JPMorgan chạy **computers tự động giao dịch**:

### Execution Algorithm

```
Objective: Mua 1 triệu cổ phiếu mà tối thiểu tổn thất (market impact)

Constraint: Giá tối đa, time limit, liquidity

Solver: Optimal Execution (dynamic programming, control theory)
```

**Kết quả:** Mua dần dần (nhỏ giọt) để tránh làm tăng giá.

### Market Making

```
Bid-Ask Spread = Spread₀ + λ × Volume + μ × Inventory
```

**Diễn giải:** Nếu bạn giữ nhiều cổ phiếu (inventory cao), bạn cắt spread (muốn bán).

---

## Order Flow & Prediction

```
Expected Price = f(Recent Orders, Volatility, Spread)
```

Machines dùng **neural networks** để dự báo micro-price movement (millisecond).

---

## Checklist Investment Banks

✅ Black-Scholes: C = S×Φ(d1) - K×e^(-rT)×Φ(d2)  
✅ Volatility Smile: σ(K) không hằng số  
✅ Greeks: Δ, Γ, ν để hedging  
✅ Stochastic Volatility: dσ = κ(θ - σ) dt + ...  
✅ Algorithmic Trading: optimal execution  
✅ Machine Learning: micro-price prediction  

---

## Tiếp theo: BlackRock

Bài 8: BlackRock dùng toán học & dữ liệu như thế nào
