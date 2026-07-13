+++
noindex = true
title = "GitHub Actions and Pages Have Recovered: What to Check After the July 9, 2026 CI/CD Incident"
date = "2026-07-09T22:35:00+07:00"
date_display = "09-07-2026 22:35:00 GMT +7"
commit = "8660546e"
slug = "github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident"
categories = ["cong-nghe"]
tags = ["GitHub Actions", "GitHub Pages", "CI/CD", "DevOps", "GitHub Status", "incident recovery"]
author = "Minh Hoàng"
image = "images/posts/github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident.webp"
thumbnail = "images/posts/github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident.webp"
image_alt = "Ảnh minh họa GitHub Actions and Pages Have Recovered: What to Check After the July 9, 2026 CI/CD Incident — nguồn Pixabay"
image_status = "verified"
image_provider = "pixabay"
image_source = "Pixabay"
image_source_url = "https://pixabay.com/photos/valentines-day-background-paper-1100254/"
image_license = "Pixabay Content License"
image_license_url = ""
image_commercial_use = true
image_owner = "external"
image_creator = "DariuszSankowski"
image_creator_url = "https://pixabay.com/photos/valentines-day-background-paper-1100254/"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pixabay_api"
draft = false
related_posts = ["github-actions-run-start-delays-july-9-2026-ci-cd-protection"]
seo_title = "GitHub Actions and Pages Have Recovered: What to Check After"
description = "GitHub marked the Actions and Pages incident as resolved at 13:52 UTC on July 9, 2026. All systems now show green on the GitHub Status page. But a recovered"

[ai_summary]
enabled = true
collapsed = false
disclaimer = "This article is based on GitHub's public status information and should be verified against GitHub Status before operational decisions."
items = ["GitHub Status shows systems operational again after the July 9, 2026 Actions and Pages incident, but teams should still verify their own pipeline state.", "A recovered platform does not automatically mean every queued, cancelled, or failed workflow has been redeployed successfully.", "Static-site owners should verify the live URL, the latest deployed commit, Pages build history, and any failed Actions runs before declaring the incident over for their own site.", "The best response after recovery is to rerun only the latest necessary deploy, cancel superseded jobs, and keep non-essential automation paused until the pipeline is stable."]
image_attribution_checked_at = "2026-07-12T08:49:03+07:00"
image_query = "github actions pages have recovered"
+++
GitHub marked the Actions and Pages incident as **resolved** at 13:52 UTC on July 9, 2026. All systems now show green on the [GitHub Status page](https://www.githubstatus.com/). But a recovered status dashboard does not automatically mean your workflows, build artifacts, and live site are healthy.

Here is the post-recovery checklist every developer and static-site owner should run through.

## 1. Check your Actions workflow run history

Navigate to the **Actions** tab of each repository that was active during the incident window (04:34 UTC to 13:52 UTC). Look for:

- **Queued runs that never started** — GitHub Status reported approximately 30% of hosted-runner jobs experienced start delays exceeding 5 minutes, and a smaller percentage exhausted retries and failed. Any workflow triggered during this window may still be queued, stuck, or silently cancelled.
- **Failed runs from exhausted retries** — some workflow runs could not start runners even after several retry attempts. If your notification settings missed the failure alert, the run may be sitting in a failed state.
- **Concurrency-limit throttling** — the incident caused some customers to exceed their hosted compute concurrency limit because long-queued jobs held runner slots open. Even after recovery, your concurrency limit may still be saturated.

**Action item:** open the Actions tab, sort by triggered date, and re-run any workflow that failed between 04:34 UTC and 13:52 UTC. Cancel any jobs that are still queued from before the resolution time and trigger a fresh run instead.

## 2. Verify your GitHub Pages deployment

GitHub Pages builds failed during a roughly 20-minute window within the incident (around 12:36 UTC to 12:54 UTC). Pages content itself remained accessible — served content was not affected — but *new* deployments did not build during that window.

**Action:** check your Pages deployment log under the repository Settings > Pages. Confirm the latest successful deployment timestamp and the deployed commit SHA. If your last deploy was during the incident window, trigger a manual redeploy from the Pages settings or push a new commit to force a fresh build.

Then visit your live site and verify that the most recent changes are actually rendered. A "resolved" status on the dashboard does not redeploy your site automatically.

## 3. Confirm GitHub Status 90-day uptime data

As of recovery, the 90-day uptime figures reported by [GitHub Status](https://www.githubstatus.com/) are:

- **Actions:** 99.8%
- **Pages:** 99.96%
- **API Requests:** 99.94%
- **Pull Requests:** 99.71%
- **Codespaces:** 99.84%
- **Copilot:** 99.89%

These numbers will shift over time. The next incident or maintenance window will adjust them. Bookmark the status page and check the actual values before any executive report.

## 4. Review notification and alert gaps

The incident escalated over approximately nine hours. The timeline was:

- 04:34 UTC — GitHub began investigating
- 04:51 UTC — confirmed ~5% of runs had start delays exceeding 5 minutes
- 10:15 UTC — impact grew to ~30% of runs
- 12:36 UTC — Pages builds also affected
- 12:54 UTC — first recovery signal for both Actions and Pages
- 13:52 UTC — incident marked resolved

**Action:** review your monitoring and alerting pipeline. If your team relies solely on GitHub Status webhooks or third-party uptime monitors, consider adding workflow-level health checks that test actual run completion, not just API availability.

## 5. Static-site checklist for Pages owners

If this blog (or any GitHub Pages site you maintain) was publishing content during the incident:

| Check | What to verify |
|---|---|
| Live URL | Open your domain in an incognito window. Does it load? |
| Latest deploy | Settings > Pages > latest deployment must be post-13:52 UTC |
| Deployed commit | Confirm the commit SHA matches your latest merge |
| Build history | Pages > Build history — any build failures at 12:36 UTC? |
| Assets | Verify CSS, JS, and image assets load on the live site |
| RSS/Atom feed | If applicable, check the feed reflects all recent posts |
| Custom domain | If you use a custom domain, verify TLS certificate and DNS are functional |

## 6. Copilot Cloud Agent and Code Review

GitHub confirmed that Copilot Cloud Agent and Copilot Code Review failed for approximately 30 minutes during the incident. If you use these features:

- Check your PR review history for any reviews that were not posted
- Verify that any automated Copilot-driven actions (PR creation, code suggestion comments) were not silently dropped during the affected window

## 7. Rerun strategy: do not blindly rerun everything

A common mistake after a CI/CD platform incident is to rerun every workflow that was ever triggered during the outage. This creates a stampede of redundant jobs that overwhelms the recovering infrastructure.

**Best practice:**
- Cancel all queued jobs that are now superseded by later pushes.
- Rerun only the latest deploy or test workflow for each branch.
- If you have a monorepo with matrix builds, stagger the reruns rather than launching them simultaneously.
- Keep non-essential scheduled workflows paused for one full cycle after recovery to let the platform stabilise.

## 8. What comes next

GitHub has stated that a detailed root cause analysis (RCA) will be shared as soon as it is available. The incident affected Actions, Pages builds, Copilot Cloud Agent, and Copilot Code Review. The underlying cause was related to infrastructure capacity for hosted runner job scheduling — not a code regression or a security breach.

When the RCA is published, it will be worth reading to understand whether your team needs to adjust run-timeouts, concurrency limits, or failover strategies.

## External sources

- [GitHub Status — Delays starting Actions runs](https://www.githubstatus.com/incidents/cstx3v63mklm)
- [GitHub Status homepage — live system status](https://www.githubstatus.com/)
- [First incident report: GitHub Actions Delays Starting Runs on July 9, 2026](/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection/)
