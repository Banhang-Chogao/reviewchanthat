# Organic Search Autobot — Phase Plan

> Generated: 10-07-2026 00:51:00
> Source: Phase 0 Audit — Review Chân Thật Hugo blog

## Current State

| Metric | Value |
|---|---|
| Posts | 157 |
| Total words | 190,334 |
| Categories | 5 |
| Authors | 1 |
| Score | 90.6 / 100 |
| Action items remaining | 7 |
| Workflows | 17 |
| Scripts | 70 |

## Score Breakdown

| Component | Score | Target | Gap | Risk |
|---|---|---|---|---|
| seo_titles | 4.0 / 15 | 15 | -11 | **HIGH** — title > 60 chars |
| meta_descriptions | 12.5 / 15 | 15 | -2.5 | MEDIUM — desc too long |
| internal_links | 24.4 / 25 | 25 | -0.6 | LOW |
| orphan_posts | 19.5 / 20 | 20 | -0.5 | LOW |
| freshness | 9.9 / 10 | 10 | -0.1 | LOW |
| content_gaps | 6 / 10 | 10 | -4 | **MEDIUM** |
| data_integrity | 5 / 5 | 5 | 0 | NONE |

## Phase Plan

### Phase 1 — Restore Content Direction Core

- **Goal**: Content Direction là source of truth, không rỗng, không image section
- **Files**: scripts/content_direction.py, scripts/qa_content_direction.py, data/content-direction.json, reports/content-direction-report.md
- **Risk**: LOW — đã có file, chỉ refine
- **Auto-merge**: ✅
- **Rollback**: git revert

### Phase 2 — Score System + Dashboard

- **Goal**: Score system hiển thị trên dashboard (đã có sẵn score JSON + list.html)
- **Files**: data/content-direction-score.json (đã có), layouts/content-direction/list.html (đã có section optimizer)
- **Risk**: LOW — đã deploy
- **Auto-merge**: ✅
- **Status**: ✅ DONE

### Phase 3 — Safe Metadata Optimizer

- **Goal**: Tự fix seo_title + description an toàn
- **Files**: scripts/content_direction_optimizer.py (đã có), scripts/qa_autobot_fixer_I.py (đã có)
- **Risk**: LOW — chỉ metadata, không body
- **Auto-merge**: ✅
- **Status**: ✅ DONE (autobot-seo-title, autobot-desc workflows đã tạo)

### Phase 4 — Data-driven Internal Link Optimizer

- **Goal**: Giảm orphan, tăng crawl flow
- **Files**: scripts/build_internal_link_graph.py (đã có), scripts/autobot_internal_link_inserter.py (đã có), data/internal-links.json (đã có)
- **Risk**: MEDIUM — chèn link vào body cần QA kỹ
- **Auto-merge**: ✅ (đã có auto-resolve conflict)
- **Status**: ✅ DONE (autobot-internal-links, autobot-orphan workflows đã tạo)

### Phase 5 — Freshness + Content Gap Queue

- **Goal**: Queue refresh + brief, không rewrite
- **Files**: scripts/autobot_content_updater.py (đã có), scripts/autobot_content_gap_filler.py (đã có)
- **Risk**: LOW — chỉ queue/brief, không sửa body
- **Auto-merge**: ✅
- **Status**: ✅ DONE (autobot-content-updater, autobot-content-gap workflows đã tạo)

### Phase 6 — Hugo SEO Tech Guards

- **Goal**: Date format, canonical, sitemap, JSON-LD, broken link guards
- **Files**: scripts/qa_dates.py, scripts/qa_sitemap.py, scripts/qa_blog.py, scripts/gen_posts_sitemap.py
- **Risk**: LOW — read-only checks, không sửa content
- **Auto-merge**: ✅ (nếu pass)
- **Recommended**: SAFE — implement next

### Phase 7 — Nightly GitHub Actions Bot

- **Goal**: Workflow chạy 00:00 GMT+7, apply safe optimizations, tạo PR
- **Files**: .github/workflows/autobot-fixer-I.yml (đã có), 6 autobot workflows mới (đã có)
- **Risk**: LOW — loop guard, auto-resolve conflict
- **Auto-merge**: ✅
- **Status**: ✅ DONE (7 workflows đang chạy nightly)

### Phase 8 — Deployment Doctor Integration

- **Goal**: Auto-diagnose failure, safe autofix, retry cap 2
- **Files**: scripts/deployment_doctor_*.py (đã có), .github/workflows/deployment-doctor.yml (đã có)
- **Risk**: LOW — report only + known safe fix
- **Auto-merge**: ✅
- **Recommended**: SAFE — implement next

### Phase 9 — Full Auto PR + Auto-merge Culture

- **Goal**: All-safe nightly, score tăng dần về 100
- **Risk**: MEDIUM — cần Phase 6+8 stable trước
- **Auto-merge**: ✅
- **Status**: ⏳ WAIT (sau Phase 6)

## Implementation Order (Recommended)

```
Phase 0 → Phase 6 → Phase 8 → verify → Phase 9
```

All other phases (1-5, 7) are **DONE**.

## What's Already Done

| Phase | Status |
|---|---|
| 1 — Content Direction Core | ✅ DONE (report 157 posts) |
| 2 — Score System | ✅ DONE (90.6/100, dashboard hiển thị) |
| 3 — Metadata Optimizer | ✅ DONE (autobot-seo-title, autobot-desc) |
| 4 — Internal Link Optimizer | ✅ DONE (autobot-internal-links, autobot-orphan) |
| 5 — Freshness + Content Gap | ✅ DONE (autobot-content-updater, autobot-content-gap) |
| 7 — Nightly Bot | ✅ DONE (7 workflows, 00:00-04:00 GMT+7) |

## What's Left

| Phase | Effort | Priority | Decision |
|---|---|---|---|
| 6 — SEO Tech Guards | ~2 hrs | **HIGH** | **recommended_now** |
| 8 — Deployment Doctor Integration | ~1 hr | MEDIUM | **safe_later** |
| 9 — Full Auto PR + Auto-merge | ~1 hr | LOW | **needs_owner_approval** |

## Phase 6 — Detailed Scope

### Files to create/modify

| File | Action | Purpose |
|---|---|---|
| `scripts/qa_dates.py` | Audit | Kiểm tra date format |
| `scripts/qa_sitemap.py` | Audit | Sitemap load + exclude noindex |
| `scripts/qa_blog.py` | New | Blog-wide checks |
| `scripts/gen_posts_sitemap.py` | Audit | Posts-only sitemap |
| `layouts/partials/head/seo.html` | Tạo | JSON-LD Article schema |
| `layouts/partials/head/canonical.html` | Tạo | Canonical guard |
| `content/robots.txt` | Tạo | Robots allow all |
| `.github/workflows/pr-check.yml` | Audit | Add SEO guards |

### Checks Phase 6 sẽ implement

1. **Dates**: all posts must have datetime offset +07:00
2. **Sitemap**: không include noindex/deleted/draft
3. **Canonical**: mọi post page có rel=canonical đúng baseURL
4. **JSON-LD**: Article schema với headline, description, author, date
5. **Broken links**: scan internal links, report relative URL problems

## Decision

Vậy là tất cả Phase 1-5 và 7 đã hoàn tất. Chỉ còn 3 phase còn lại:

| Phase | Nên làm? | Thời gian |
|---|---|---|
| 6 — SEO Tech Guards (date/canonical/sitemap/schema/link checks) | **recommended_now** | ~2 tiếng |
| 8 — Deployment Doctor Integration | safe_later | ~1 tiếng |
| 9 — All-safe Auto-merge | needs_owner_approval | ~1 tiếng |