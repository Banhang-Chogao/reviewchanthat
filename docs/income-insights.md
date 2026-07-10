# Income Insights — Private Financial Tracker

Mini-app quản lý thu nhập, nợ và dòng tiền cá nhân, chạy hoàn toàn trên client.

## Kiến trúc

```
content/doi-song/income-insights/_index.md  ← noindex, layout override
layouts/doi-song/income-insights.html        ← access gate + table + charts
assets/css/income-insights.css               ← BEM CSS, existing design tokens
static/js/income-insights.js                 ← main app logic
static/js/income-insights-engine.js           ← local rule engine (AI Insights)
static/data/income-insights-schema.json       ← JSON schema
scripts/qa_income_insights.py                ← QA script
private-data/income-insights.local.json       ← untracked sample
```

## Tính năng

- Bảng giao dịch Excel-like (13 cột A-M)
- F (Sub Total) = B (Income) + D (Debt), read-only
- J (Date) = DATE(L, M, K), read-only
- CRUD: thêm, nhân bản, xoá dòng
- Sắp xếp, lọc theo tháng/năm, tìm kiếm
- Định dạng VND
- Validate ngày
- Tổng Income, Debt, Net, Debt/Income ratio (KPI cards)
- 8 biểu đồ Chart.js (defer-load, không CLS)
- AI Insights local (rule engine, không gửi dữ liệu ra ngoài)
- Autosave (3s debounce + visibility change)
- Undo (20 levels)
- Export/Import encrypted JSON (AES-GCM + PBKDF2)
- Export CSV (UTF-8 BOM)
- Dữ liệu mẫu (test only)

## Bảo mật

- Access gate SHA-256 hash (không plaintext 9898 trong source)
- Session unlock (sessionStorage)
- Rate limit + cooldown sau 5 lần sai
- Dữ liệu mã hóa AES-GCM, key PBKDF2 từ access code
- Lưu IndexedDB, không commit public repo
- Không GA4 event chứa dữ liệu tài chính
- Noindex, nofollow, không sitemap/RSS/search

## Remote Sync

Chưa cấu hình. V1 dùng encrypted local storage + encrypted export/import.

## QA

```bash
python scripts/qa_income_insights.py
hugo --minify
```

Hard checks:

```bash
grep -R "9898" public static layouts assets data || true
grep -R "private_key\|github_token\|ghp_" public static layouts assets data || true
grep -R "income-insights" public/sitemap.xml public/index.xml public/search* || true
grep -R "private-data" public || true
git check-ignore private-data/income-insights.local.json
```
