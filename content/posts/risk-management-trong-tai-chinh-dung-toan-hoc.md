+++
title = "Risk Management trong tài chính: Từ VaR đến stress testing"
description = "Risk management dùng toán học gì? Học VaR, Expected Shortfall, correlation breakdown, tail risk, stress scenarios, historical vs parametric VaR, và backtesting."
date = "2026-07-10T12:00:00+07:00"
lastmod = "2026-07-10T12:00:00+07:00"
seo_title = "Risk management: VaR, CVaR, stress test, correlation breakdown"
authors = ["Minh Hoàng"]
categories = ["tai-chinh"]
tags = ["risk management", "VaR", "CVaR", "correlation", "stress test", "tail risk", "backtesting"]
series = ["ham-so-mu-e-va-toan-hoc-tai-chinh"]
series_order = 12
image = "images/posts/risk-management-trong-tai-chinh-dung-toan-hoc.webp"
image_alt = "Ảnh minh họa Risk Management trong tài chính: Từ VaR đến stress testing — nguồn Pexels"
date_display = "10-07-2026 12:00:00 GMT +7"
lastmod_display = "10-07-2026 12:00:00 GMT +7"

[ai_summary]
items = ["Risk Management = Định lượng, monitor, minimize rủi ro tài chính", "VaR_α = Tổn thất tối đa ở mức tin cậy α% (đã học ở Bài 6)", "Historical VaR: Từ 250 ngày lịch sử, lấy 1% tồi nhất", "Parametric VaR: VaR = Portfolio × Z × σ (giả định phân phối chuẩn)", "Expected Shortfall: Mất lỗ trung bình vượt quá VaR", "Correlation Breakdown: Khi thị trường crash, correlation → 1 (diversification fail!)", "Stress Testing: Kịch bản cực đoan (2008 crisis, COVID, war, etc)"]
thumbnail = "images/posts/risk-management-trong-tai-chinh-dung-toan-hoc.webp"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/woman-with-gloves-inserting-a-card-into-an-automated-machine-5699338/"
image_provider = "pexels"
image_license = "Pexels License"
image_license_url = ""
image_commercial_use = true
image_owner = "external"
image_creator = "RDNE Stock project"
image_creator_url = "https://www.pexels.com/@rdne"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pexels_api"
image_status = "verified"
image_attribution_checked_at = "2026-07-10T14:01:45+07:00"
image_query = "atm banking transaction"
+++

**Risk Management** — quản lý rủi ro trong tài chính.

Tại sao quan trọng? Năm 2008, Lehman Brothers, Bear Stearns **collapse**. Lý do: **không quản lý rủi ro tốt**.

Bài này giải thích risk management frameworks & toán học.

---

## Risk Hierarchy

### Tier 1: Market Risk

```
Loss = Δ Position × Δ Market Price
```

VaR, Greeks, Duration (bond interest rate risk).

### Tier 2: Credit Risk

```
Loss = Exposure × Probability of Default × Loss Given Default
```

Rating agencies (Moody's, S&P) dùng models.

### Tier 3: Operational Risk

```
Loss = Frequency × Severity (Thảm họa, hack, sai lệm)
```

Basel III: ngân hàng phải giữ **capital reserve** 10% assets.

### Tier 4: Liquidity Risk

```
Liquidity Loss = Normal Spread + Extra Spread (khi rush to exit)
```

---

## Historical VaR

### Bước

1. Thu thập log-return 250 ngày
2. Sắp xếp từ xấu đến tốt
3. VaR_99% = return ở vị trí 2-3 xấu nhất (1% × 250 = 2.5 ≈ 2-3)

### Ví dụ: Cổ phiếu VietcomBank

250 ngày return từ xấu:
- Ngày -1: -3.5%
- Ngày -2: -3.2%
- Ngày -3: -2.9%

VaR_99% = -3.2%

Nếu danh mục = 100 tỷ VND:
```
VaR_99% Loss = 100 tỷ × 3.2% = 3.2 tỷ VND
```

---

## Parametric VaR

Giả định phân phối chuẩn:

```
VaR = Portfolio Value × Z_α × σ
```

**Ưu điểm:** Nhanh, không cần lịch sử dài  
**Nhược điểm:** Giả định chuẩn fail khi tail risk cao

---

## Expected Shortfall (CVaR)

```
ES_α = E[Loss | Loss > VaR_α]
```

**Ví dụ:**
- VaR_99% = 3.2%
- ES_99% = 4% (trung bình khi vượt 3.2%)

---

## Correlation Breakdown

**Normal time:** Correlation(Stock_A, Bond) ≈ -0.3 (diversification!)

**Crisis time (2008, COVID):** Correlation → +0.9 (mọi thứ rơi cùng lúc!)

```
Diversified Portfolio Không guarantee trong crisis
```

---

## Stress Testing

Kịch bản cực đoan:

### Ví dụ 1: Interest Rate +2%

```
Bond Price = PV = Σ Coupon × e^(-r×t)

Nếu r tăng 2% → Bond value giảm (inversely proportional)
Loss ≈ -2% × Duration
```

### Ví dụ 2: Market Crash 30%

```
Loss = -30% × Portfolio Value
```

### Ví dụ 3: Correlation → 1

```
Loss = Worst Scenario Asset × All Allocations
```

---

## Backtesting VaR

**Kiểm tra:** VaR model có chính xác không?

1. Tính VaR hàng ngày (250 ngày)
2. So sánh với thực tế return
3. Đếm "exceptions" (khi real loss > VaR)

**Kỳ vọng:** 2-3 exceptions/năm (1% × 250)  
**Nếu > 5:** Mô hình sai → cần điều chỉnh σ

---

## Risk Limits

Ngân hàng đặt limits:

```
Daily VaR Limit = $X million
Notional Limit = $Y million (tổng exposure)
Greeks Limit: Delta ≤ $Z, Gamma ≤ ...
```

Nếu vượt → trader phải giảm position.

---

## Capital Adequacy (Basel III)

Ngân hàng phải giữ **capital reserve**:

```
Capital Ratio = Capital / Risk-Weighted Assets ≥ 10.5%
```

**Diễn giải:** Nếu assets = 1000 tỷ, phải giữ capital ≥ 105 tỷ để absorb losses.

---

## Checklist Risk Management

✅ Market Risk: VaR, Greeks, Duration  
✅ Credit Risk: PD, LGD, EAD  
✅ Operational Risk: Frequency × Severity  
✅ Liquidity Risk: Bid-Ask Spread + Liquidity Crisis  
✅ Stress Testing: Kịch bản cực đoan  
✅ Backtesting: Kiểm tra VaR accuracy  

---

## Tiếp theo: Monte Carlo

Bài 13: Monte Carlo trong tài chính
