+++
noindex = true
title = "GitHub Actions Delays Starting Runs on July 9, 2026: What Happened, Why Pages Builds Failed, and How to Protect CI/CD"
date = "2026-07-09T20:21:28+07:00"
date_display = "09-07-2026 20:21:28 GMT +7"
commit = "e1b87c29"
slug = "github-actions-run-start-delays-july-9-2026-ci-cd-protection"
categories = ["cong-nghe"]
tags = ["GitHub Actions", "GitHub Pages", "CI/CD", "DevOps", "GitHub Status", "incident response"]
author = "Minh Hoàng"
image = "images/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection.webp"
thumbnail = "images/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection.webp"
image_alt = "Ảnh minh họa GitHub Actions Delays Starting Runs on July 9, 2026: What Happened, Why Pages Builds Failed, and How to Protect CI/CD — nguồn Pexels"
image_status = "verified"
image_provider = "pexels"
image_source = "Pexels"
image_source_url = "https://www.pexels.com/photo/person-in-blue-leggings-8692281/"
image_license = "Pexels License"
image_license_url = "https://www.pexels.com/license/"
image_commercial_use = true
image_owner = "external"
image_creator = "Yaroslav Shuraev"
image_creator_url = "https://www.pexels.com/@yaroslav-shuraev"
image_creator_id = ""
image_attribution_verified = true
image_attribution_source = "pexels_api"
draft = false
seo_title = "GitHub Actions Delays Starting Runs on July 9, 2026: What"
description = "On July 9, 2026, GitHub reported an incident titled \"Delays starting Actions runs\". The practical symptom was simple: workflows that should have started on"

[[external_links]]
url = "https://www.githubstatus.com/incidents/cstx3v63mklm"

[ai_summary]
enabled = true
collapsed = false
disclaimer = "This article is based on GitHub's public status updates. Operational details may change if GitHub publishes follow-up information."
items = ["GitHub reported degraded availability for Actions on July 9, 2026, with hosted-runner jobs delayed or failing to start.", "GitHub Pages builds were also affected during part of the incident, while existing Pages sites remained accessible according to GitHub's update.", "A queued workflow is not automatically a broken commit; if the job never reached checkout, your code has not been tested yet.", "Teams can reduce impact with concurrency controls, limited retries, platform-incident detection, non-essential workflow pauses, and post-deploy live verification."]
image_attribution_checked_at = "2026-07-12T08:48:50+07:00"
image_query = "github actions delays starting runs"
+++
On July 9, 2026, GitHub reported an incident titled ["Delays starting Actions runs"](https://www.githubstatus.com/incidents/cstx3v63mklm). The practical symptom was simple: workflows that should have started on GitHub-hosted runners stayed in a queued or pending state, sometimes long enough for retries to be exhausted. During part of the same incident, GitHub Pages builds were also affected.

This was not a full GitHub outage. Git operations, repositories, and existing GitHub Pages sites could still be reachable while new Actions jobs waited for runner capacity. That distinction matters. A stuck deploy during this incident did not automatically mean a bad commit, a broken Hugo build, or a Pages configuration mistake.

For teams watching a deploy screen, the key diagnostic question was: did the job ever start executing steps? If the workflow was still waiting for a hosted runner, the repository code had not reached checkout, dependency install, build, tests, or deploy. The failure mode was upstream platform availability, not application logic.

## What happened on July 9, 2026

GitHub's public status timeline began with an investigation into degraded Actions performance at 04:34 UTC. A later update said a portion of GitHub-hosted runner jobs were delayed by more than five minutes, with some runs failing after extended delays. As the incident developed, GitHub reported a higher share of affected Actions runs and noted that some customers were hitting hosted compute concurrency limits because delayed jobs occupied capacity.

The incident expanded beyond Actions alone. At 12:36 UTC, GitHub reported degraded performance for Pages. At 12:46 UTC, GitHub reported degraded availability for Actions. A later recovery update said Actions and Pages were recovering, but recovery does not mean every queued workflow instantly disappears. Backlog still has to drain, and jobs already created during the incident may remain queued until a runner becomes available or a newer workflow cancels them through concurrency settings.

For a static site on GitHub Pages, the visible behavior can look confusing:

| Signal | What it usually means during this incident |
| --- | --- |
| Workflow is queued | GitHub has accepted the run, but a runner has not started the job. |
| Job says it is waiting for a hosted runner | The build has not reached checkout or any repository code yet. |
| Older runs are cancelled | Concurrency settings or repeated manual dispatches may be replacing prior runs. |
| Pages site still loads | Existing deployed files remain accessible even if new builds are delayed. |
| Pages build fails to start | The problem can be platform-side, not a content or configuration bug. |

## Why GitHub Pages builds failed or stalled

GitHub Pages deployments commonly rely on GitHub Actions. A typical static-site workflow checks out the repository, installs Hugo or another site generator, builds the `public` directory, uploads the Pages artifact, and then deploys it. Every one of those steps depends on the job being assigned to a runner first.

When hosted-runner start delays happen, the workflow can be created but not actually run. That creates a sharp boundary:

- Before runner assignment, no checkout has happened.
- Before checkout, no dependency install has happened.
- Before build, Hugo, tests, and content scripts have not evaluated the commit.
- Before artifact upload, Pages has nothing new to publish.

That is why Pages builds can appear to fail while the website itself remains accessible. The live site is the previous successful deployment. The new deployment is delayed because the build pipeline has not completed.

Repeatedly clicking "Run workflow" can make the situation worse. If a workflow uses a concurrency group, new dispatches may cancel older runs or stack additional queued work behind the same hosted-runner shortage. During an Actions incident, one clean deploy attempt is often better than a burst of manual retries.

## How to tell platform delay from a code bug

The fastest way to avoid false debugging is to inspect the job boundary.

If the run shows messages like "Waiting for a runner to pick up this job" or "Job is waiting for a hosted runner to come online," the job has not reached your code. Do not start rewriting build scripts, changing package versions, or reverting content until a runner has actually executed the failing step.

Once the runner starts, the diagnosis changes. A failure in `actions/checkout`, dependency installation, Hugo build, tests, image processing, or Pages artifact upload is now inside the workflow execution path. At that point, logs matter. Before that point, status pages and queue behavior matter more than repository changes.

A practical incident checklist looks like this:

1. Check GitHub Status for Actions and Pages.
2. Open the latest workflow run and inspect the job state, not only the workflow summary.
3. Confirm whether any step has started.
4. Avoid repeated manual dispatches while hosted runners are degraded.
5. Keep one latest deploy attempt active unless it is clearly stale after recovery.
6. Verify the live URL after deployment, not just the green check mark.

## Why concurrency controls matter

Concurrency controls are useful when deploys are frequent. They prevent multiple deploy jobs from racing to publish different versions of the site. But during a platform incident, concurrency can also make the run list look chaotic because newer runs may cancel older runs before they ever execute.

For GitHub Pages deploy workflows, a conservative pattern is:

```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

That setting avoids cancelling a deployment that has already started. Some teams prefer `cancel-in-progress: true` for preview builds or non-production checks, but production deploys usually benefit from a calmer queue. The right answer depends on whether freshness or completion is more important for the workflow.

For content sites, completion usually matters more. A delayed article publish is annoying; a chain of cancelled deploy attempts is harder to reason about and can hide the first real build error that appears after runners recover.

## How teams can protect CI/CD pipelines

The July 9 incident is a reminder that CI/CD resilience is not only about your code. It also depends on the behavior of the platform that schedules, runs, and deploys that code.

Good protection starts with operational clarity:

- Separate platform state from repository state in your incident notes.
- Treat queued jobs as untested code, not failed code.
- Keep deploy workflows idempotent so a retry can publish the same commit safely.
- Make build logs easy to scan by keeping custom scripts explicit and noisy only when needed.
- Use concurrency groups intentionally for production deploys.
- Pause non-essential workflows when hosted-runner capacity is degraded.
- Keep a recent successful deployment available so Pages can continue serving the site while new builds wait.

For teams with static sites, post-deploy verification is especially important. A successful workflow only proves that the deploy process completed. It does not prove that the expected URL is live, crawlable, linked in the sitemap, and free of accidental `noindex` metadata. After an incident, verify the production URL directly.

## What to do if your deploy is stuck

If your GitHub Pages deploy is stuck during an Actions incident, do not start with code changes. Start with state:

1. Read the latest GitHub Status update for Actions and Pages.
2. Confirm whether the job has started on a runner.
3. If no step has started, wait for runner capacity to recover.
4. If multiple manual deploys exist, stop dispatching new ones.
5. After recovery, keep the newest relevant run and cancel only clearly obsolete runs.
6. When the build finally starts, review logs normally.
7. After deployment, open the live URL and the sitemap URL.

That approach prevents two common mistakes: blaming a good commit for a platform queue, and creating enough duplicate deploy attempts that the run history becomes harder to understand.

## Bottom line

The GitHub Actions and GitHub Pages incident on July 9, 2026 was primarily a hosted-runner start and Pages build availability problem, not evidence that every queued repository had broken code. If a workflow never reached checkout, your commit had not been tested yet.

For CI/CD protection, the lesson is straightforward: monitor platform status, use deploy concurrency carefully, avoid retry storms, keep workflows idempotent, and verify the live site after the queue clears. Those habits will not prevent a hosted-runner incident, but they will keep your team from turning a platform delay into an avoidable deployment mess.
