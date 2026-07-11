+++
title = "Monte Carlo trong tài chính: Mô phỏng 10 triệu kịch bản"
description = "Monte Carlo simulation là gì? Học Brownian motion, random sampling, pricing exotic options, VaR calculation, portfolio simulation, và variance reduction techniques."
date = "2026-07-10T12:15:00+07:00"
commit = "9008aff"
lastmod = "2026-07-10T12:15:00+07:00"
seo_title = "Monte Carlo: simulation, Brownian motion, exotic options, VaR"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["Monte Carlo", "simulation", "Brownian motion", "random sampling", "exotic options", "VaR calculation"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 13
image = "images/posts/monte-carlo-trong-tai-chinh-la-gi.webp"
date_display = "10-07-2026 12:15:00 GMT +7"
lastmod_display = "10-07-2026 12:15:00 GMT +7"
thumbnail = "images/posts/monte-carlo-trong-tai-chinh-la-gi.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/blue-dice-in-close-up-photography-6990178/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "DS stories"
image_creator_url = "https://www.pexels.com/@ds-stories"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = ""
image_attribution_checked_at = "2026-07-11T17:30:39+07:00"
draft = false

[ai_summary]
items = ["Monte Carlo: Mô phỏng N×10^6 kịch bản random để ước lượng option price, VaR, portfolio value", "Brownian Motion: dS = μS dt + σS dW (random walk log-price)", "Giả định: S tuân theo log-normal distribution, dW là Wiener process", "Discretization: Δt nhỏ (1 ngày, 1 giờ) để discretize SDE", "Pricing: E[Option Payoff] = (1/N) × Σ Payoff_i × e^(-rT)", "VaR: Sort 10M outcomes, lấy 1% worst case", "Variance Reduction: Antithetic sampling, control variates để giảm N needed"]
draft = false
+++

**Monte Carlo** — phương pháp mô phỏng dựa trên **random sampling**.

Ứng dụng:
1. **định giá exotic options** (American, barrier, lookback)
2. **Tính VaR, rủi ro danh mục**
3. **Quản trị rủi ro**: Mô phỏng portfolio values

---

## Brownian Motion & Ito's Lemma


![Minh họa nội dung monte carlo trong tai chinh la gi — nguồn Pexels](/images/posts/monte-carlo-trong-tai-chinh-la-gi-inline.webp)

*Nguồn: Pexels / AlphaTradeZone*


### Mô hình giá tài sản

```
dS = μS dt + σS dW
```

**Ký hiệu:**
- dS = thay đổi giá
- μ = drift (kỳ vọng tăng trưởng)
- σ = volatility
- dW = Brownian increment (random)
- dt = time increment nhỏ

### Giải pháp (Geometric Brownian Motion)

```
S_T = S_0 × exp( (μ - σ²/2)T + σ√T × Z )
```

**Ký hiệu:**
- Z ~ N(0,1) (chuẩn Gaussian)
- exp = e (từ Bài 1!)

---

## Thuật toán Monte Carlo

### Bước 1: Sinh Random Paths

Với 10,000 mô phỏng, mỗi mô phỏng:

```
S_1 = S_0 × exp( (μ - σ²/2)Δt + σ√Δt × Z_1 )
S_2 = S_1 × exp( (μ - σ²/2)Δt + σ√Δt × Z_2 )
...
S_T = S_{T-1} × exp( (μ - σ²/2)Δt + σ√Δt × Z_T )
```

**Kết quả:** 10,000 possible prices S_T tại expiry.

### Bước 2: Tính Payoff

Với mỗi S_T:

```
Payoff = max(S_T - K, 0)  [for call option]
```

### Bước 3: Discount & Average

```
Option Price = e^(-rT) × Average(Payoff)
              = e^(-rT) × (1/N) × Σ Payoff_i
```

### Ví dụ: Exotic Asian Option

Call option có strike = average price trong năm (chứ không spot price).

**Black-Scholes không giải được** → dùng Monte Carlo.

```
Path 1: S_0 = 100, S_3m = 105, S_6m = 102, S_9m = 110, S_12m = 108
  Average = 105
  Payoff = max(105 - 100, 0) = 5

Path 2: S_0 = 100, S_3m = 98, S_6m = 100, S_9m = 97, S_12m = 95
  Average = 98
  Payoff = 0

...

Option Price = e^(-0.05×1) × Average(5, 0, ...) ≈ 2.5
```

---

## VaR with Monte Carlo

### Bước

1. Sinh 10 triệu paths cho portfolio
2. Tính portfolio value S_T cho mỗi path
3. Sort từ xấu đến tốt
4. VaR_99% = value ở 1% worst case (path 100,000)

### Ví dụ

10 triệu paths:
- Path 1 (xấu nhất): Portfolio = -5 tỷ VND
- Path 2: -4.8 tỷ VND
- ...
- Path 100,000: -3.5 tỷ VND ← VaR_99%

---

## Variance Reduction

10 triệu paths **rất chậm**. Kỹ thuật giảm variance:

### Antithetic Sampling

Sinh Z ~ N(0,1), rồi dùng cả (Z, -Z):

```
Path_1 uses Z
Path_2 uses -Z (antithetic)
Average Price = (Price_1 + Price_2) / 2
```

**Ưu điểm:** Giảm variance 50%, chỉ cần 5 triệu paths.

### Control Variates

Dùng Black-Scholes (known) làm benchmark:

```
Exotic Price ≈ Black-Scholes(Vanilla) + E[Exotic - Vanilla]
```

Phần cuối tính qua Monte Carlo (ít variance).

---

## Convergence & Accuracy

Lỗi giảm tỷ lệ với 1/√N:

```
Lỗi ≈ σ_payoff / √N

N = 1,000: Lỗi ~ ±3%
N = 100,000: Lỗi ~ ±0.3%
N = 10,000,000: Lỗi ~ ±0.03%
```

---

## Ứng dụng thực tế

1. **Investment Banks:** định giá Bermudan swaptions, barrier options
2. **Insurance:** Mô phỏng claims, rủi ro dài hạn
3. **Pension Funds:** ALM (asset-liability management)
4. **Risk Management:** Scenario analysis

---

## Checklist Monte Carlo

✅ Brownian Motion: dS = μS dt + σS dW  
✅ Giải: S_T = S_0 × exp((μ - σ²/2)T + σ√T Z)  
✅ Algo: Sinh paths → Payoff → Discount → Average  
✅ VaR: Sort outcomes, lấy 1% worst  
✅ Variance Reduction: Antithetic, Control Variates  
✅ Convergence: Error ~ 1/√N  

---

## Tiếp theo: AI trong tài chính

Bài 14: AI trong tài chính
