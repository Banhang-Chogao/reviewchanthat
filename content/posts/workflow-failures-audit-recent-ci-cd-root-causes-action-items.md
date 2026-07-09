+++
title = "Workflow Failures Audit: How We Identified Recent CI/CD Failures, Root Causes, and Action Items"
date = 2026-07-09T23:00:00+07:00
description = "A practical audit of recent CI/CD workflow failures: how to list failed runs, identify root causes, separate QA debt from deploy issues, and turn incidents into action items."
slug = "workflow-failures-audit-recent-ci-cd-root-causes-action-items"
categories = ["cong-nghe"]
tags = ["GitHub Actions", "CI/CD", "DevOps", "workflow failures", "deployment", "incident response"]
author = "Minh Hoàng"
image = "images/posts/workflow-failures-audit-recent-ci-cd-root-causes-action-items.webp"
thumbnail = "images/posts/workflow-failures-audit-recent-ci-cd-root-causes-action-items.webp"
image_alt = "Editorial illustration showing workflow failures audit with identified root causes and action items for CI/CD incident response."
image_status = "verified"
image_provider = "self-generated"
image_source = "self-owned"
image_source_url = "https://banhang-chogao.github.io/reviewchanthat/images/posts/workflow-failures-audit-recent-ci-cd-root-causes-action-items.webp"
image_license = "Original self-hosted editorial illustration by Review Chân Thật"
image_license_url = "https://banhang-chogao.github.io/reviewchanthat/branding-ci/"
image_commercial_use = true
image_owner = "self"
image_creator = "Review Chân Thật"
image_creator_url = "https://banhang-chogao.github.io/reviewchanthat/"
image_creator_id = "review-chan-that-generated"
image_attribution_verified = true
image_attribution_source = "self_generated"
image_generation_method = "programmatic_or_ai_assisted_editorial_illustration"
draft = false
related_posts = [
  "github-actions-run-start-delays-july-9-2026-ci-cd-protection",
  "github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident"
]

[ai_summary]
enabled = true
title = "Quick summary"
collapsed = false
disclaimer = "This article is based on recent public GitHub Actions run metadata from this repository. Root-cause labels should be verified against workflow logs before operational decisions."
items = [
  "Recent workflow failures should be audited as a system, not treated as isolated random errors.",
  "A failed deploy, a failed QA debt fix, and a self-owned image metadata bug can require different responses.",
  "The best response is to list failed runs, classify root causes, define action items, and prevent unrelated debt from blocking feature deploys.",
  "A good CI/CD pipeline should distinguish platform delay, deploy mismatch, QA debt, and changed-file compliance failures before running autofix."
]
+++

When your CI/CD pipeline starts failing, the worst approach is to treat each failure as independent. A cluster of failures—three QA debt runs failing, two deploys failing, each at different commits—is not random noise. It is a signal that **the system** has accumulated debt, misalignment, or a platform issue.

This article walks through how we audited five recent failed GitHub Actions runs, identified three distinct root causes, and turned them into actionable fixes. The goal is not to hide failures. The goal is to make them explainable.

## The failed runs we reviewed

Over a six-hour period on July 9, 2026, we saw multiple workflow failures:

| Run | Commit | Workflow | What failed | Initial signal |
|-----|--------|----------|-------------|----------------|
| qa-debt-fix #9 | 4ae8ea3 | `.github/workflows/qa-debt-fix.yml` | QA check halted | Image metadata missing |
| Deploy #201 | bd05d05 | Deploy to GitHub Pages | Build failed early | Self-owned image no direct_url |
| qa-debt-fix #8 | bd05d05 | `.github/workflows/qa-debt-fix.yml` | QA check halted | Same image issue |
| Deploy #200 | 878650a | Deploy to GitHub Pages | Build failed early | Self-owned image no direct_url |
| qa-debt-fix #7 | 878650a | `.github/workflows/qa-debt-fix.yml` | QA check halted | Same image issue |

At first glance: five failures, three commits, two workflows. On closer inspection: **one root cause** (self-owned image handling), one **secondary pattern** (QA debt), and one **policy misalignment** (footer link removal).

## Pattern 1: A self-owned image is not the same as a provider image

The first signal was clear in the logs:

```
FAIL: No direct_url in manifest for github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident
```

This came from our `process_images.py` script, which downloads images from external providers during the build. The script was checking every image for a `direct_url` field, and treating the absence of that field as a fatal error.

But here's the catch: **self-generated images do not have a direct_url**. They are stored locally under `static/images/posts/`. They do not need to be downloaded. The script should skip the direct_url requirement entirely for self-owned content.

### What the correct behavior should be

For **provider/external images**:
- Require `direct_url` or `source_url` pointing to the original image
- Download the image during build
- Convert to WebP, add watermark, verify attribution
- Fail if the URL is broken or attribution is missing

For **self-owned images**:
- Do not require `direct_url`
- Check that the local file exists under `static/images/posts/`
- Verify metadata clearly marks it as `image_owner = "self"` and `image_provider = "self-generated"`
- Update frontmatter with local path and site URL
- Pass through without failure, even if the image is not ready yet

### The fix

We updated the image processing logic to:

```python
is_self_owned = source in SELF_SOURCE_PLATFORMS or is_self_owned_entry(entry)

if is_self_owned:
    # Self-owned images skip direct_url requirement
    if os.path.exists(dest_path):
        # Image ready; process it
        ...
    else:
        # Image not ready yet; skip but don't fail
        print(f"Self-owned image not ready: {dest_path}")
        continue

if not direct_url:
    # Only external images need direct_url
    print(f"FAIL: No direct_url in manifest for {slug}")
    failed += 1
```

**Action item**: Update image processing scripts to handle self-owned images without requiring `direct_url`.

## Pattern 2: QA debt should not block unrelated feature deploys

We saw six failed runs from `.github/workflows/qa-debt-fix.yml` in the same period. Each failure corresponded to a feature deploy or fix (footer link removal, date formatting, process images fix).

The pattern is clear: a **strict QA check** is running on every commit to main, and if **any old post** fails the check (missing creator attribution, fallback image, legacy metadata), the **entire deploy** is blocked.

This is the "baseline debt blocking new work" anti-pattern.

### What's wrong with this approach

- An unrelated new feature (footer link removal) fails because an old travel post uses a placeholder image
- A critical bug fix (date formatting) is held up by a stale image link in a different post
- The developer sees "build failed" and has no clear way to separate real issues from historical debt
- Each commit to main re-runs the full-site check, amplifying the noise

### What the correct behavior should be

For **new or changed posts**:
- Strict compliance gate: require creator, real image, proper metadata
- Fail if the check fails; do not deploy the broken post
- The developer can fix it in the same PR or revert

For **unchanged old posts**:
- Add to a baseline of known issues
- Do not re-check them on every deploy unless explicitly fixing them
- Schedule batch updates to clean up old debt on a separate branch

For **the main deploy pipeline**:
- Run quick structural checks (YAML parsing, template syntax)
- Run compliance only on changed files
- Keep old debt in a monitored baseline, not a blocking gate

### The fix

We need to:

1. **Scope QA to changed files only**
   - Use `git diff main...HEAD` to identify changed posts
   - Run strict checks only on those posts
   - Skip old posts unless they are the target of a specific fix

2. **Keep a baseline of known issues**
   - Document which old posts fail which checks
   - Store the baseline in version control
   - Skip those checks for baseline posts in the deploy pipeline
   - Schedule a separate "QA debt cleanup" PR to fix them batch by batch

3. **Separate autofix from gate**
   - The deploy gate should fail loudly if something is truly broken
   - Post-deploy autofix (metadata updates, frontmatter normalization) can run separately

**Action items**:
- Create a `--scope-changed-only` flag for QA scripts
- Maintain a compliance baseline for old posts
- Schedule weekly QA debt cleanup PRs

## Pattern 3: Deploy failure is not always live-site downtime

Two Deploy to GitHub Pages runs failed for commit `ab2808b` (the GitHub Actions incident post). These were both failures, but:
- The first failure was a **build failure** (image processing halted)
- The second failure was a **workflow_dispatch manual re-run** attempting recovery

The recovery runs succeeded (newer deploys to the same commit with better luck or manual fixes).

### What's important to distinguish

- **Build failed**: Hugo build error, artifact not created
- **Deploy failed**: Artifact created but Pages publish failed or rejected
- **Live site stale**: Deploy succeeded but older commit is still live
- **Live site down**: Pages serving 500 or empty

When a deploy fails, **verify the live URL and commit SHA before assuming the site is broken**.

### The fix

Each deploy should:

1. Publish build-info.json to the artifact with the commit SHA, build timestamp, and deploy result
2. On deploy failure, compare the live site's build-info SHA to the queued SHA
3. If live site is newer, the old deploy is superseded; do not retry it
4. If live site is older, re-run the latest commit only; cancel all other queued runs
5. Add a post-deploy check that fetches the live site and verifies the expected commit is live

**Action item**: Add build-info publication and live-site verification to the deploy workflow.

## Pattern 4: Removing a visible link should update QA expectations

When the commit `bd05d05` removed the deployment-snapshot link from the footer, both the deploy and the QA check failed. Why? Because the QA script still expected that link to exist.

This is a **policy mismatch**: the product decision removed the link, but the QA automation was not updated.

### What went wrong

- Product/content decision: "deployment-snapshot is noindex; remove from footer"
- Deploy action: footer.html updated, link removed
- QA action: Still checking for the link; fails because it's gone
- Result: Deploy blocked by stale QA

### The fix

When removing a user-facing link or feature:

1. **Update QA rules first** (in the same PR or a preceding commit)
2. **Update the template** (footer, layout, etc.)
3. **Verify the change** (live QA check passes)
4. **Deploy** the updated rules and templates together

If QA is strict about a link, and you remove the link, update QA in the same commit. Do not let the old rule block the new behavior.

**Action item**: Align footer/link QA checks with the product decision on deployment-snapshot visibility.

## Action items we should perform

Here's the priority list for fixing these issues:

| Priority | Action item | Owner | Expected result |
|----------|-------------|-------|-----------------|
| P0 | Fix process_images.py to skip direct_url check for self-owned images | Engineering | qa-debt-fix and Deploy runs pass for images without direct_url |
| P0 | Add changed-files compliance scope to QA pipeline | Engineering | QA debt stops blocking unrelated feature deploys |
| P1 | Maintain baseline of known QA debt | QA/Engineering | Old posts don't fail new deploys |
| P1 | Add live deploy verification using build-info | Engineering | Failed deploys distinguished from stale sites |
| P1 | Cancel superseded deploy runs on newer commits | Engineering | Workflow queue stays clean |
| P2 | Align footer/deployment-snapshot QA with product rules | Content/QA | No false failures when links are intentionally removed |
| P2 | Schedule batch QA debt cleanup PRs | Engineering | Gradual improvement of old post metadata |
| P3 | Make post-merge autofix root-cause aware | Engineering | Autofixes applied only when safe |

## What we should NOT automate blindly

As you implement fixes, keep these traps in mind:

- **Do not run full-site image replacement** when one deploy fails. Check what changed first.
- **Do not create hotfix PRs** when the root cause is runner capacity delay. The platform will recover; your hotfix may be unnecessary.
- **Do not mark self-generated images** as external provider images. They have different requirements.
- **Do not fake image creators** or use placeholder names to pass compliance. If attribution is missing, that's a real issue.
- **Do not bypass compliance for new/changed posts**. The gate is there to prevent future debt.
- **Do not keep retrying old commits** after a newer deploy exists. Cancel and redeploy the latest instead.

## The incident-response checklist

When workflow failures cluster, follow this checklist:

1. **List recent failed runs** using `gh run list --status failure --branch main`
2. **Inspect whether each run reached checkout/build** or failed at environment setup
3. **Identify workflow name, commit SHA, and affected files** for each failure
4. **Classify root cause** using patterns you've seen before
5. **Decide whether it is safe to autofix** (or if a manual review is needed first)
6. **Write action items** for each root cause
7. **Verify the live URL** and commit SHA to distinguish build failure from deploy failure from stale deployment
8. **Publish a short lesson learned** if the incident teaches something reusable

## Final thoughts

The goal of this incident response is not to hide failures or pretend they did not happen. The goal is to make failures explainable and actionable.

A good CI/CD pipeline is one where:
- Failures are rare because the system is well-maintained
- When they do occur, they are easy to diagnose
- Root causes are classified and tracked
- Action items emerge naturally from the diagnosis
- Automation prevents new failures, not replaces the fix

The best blog post after an incident is not a rant about "the platform was broken" or "everything failed." The best post is a useful runbook: here is what we saw, here is what caused it, here is how we fixed it, and here is how we prevent it next time.

We hope this breakdown helps you audit your own workflow failures—and more importantly, turn clusters of failures into clusters of fixes.

---

**Related articles:**
- [GitHub Actions run-start delays (July 9, 2026 incident)](/reviewchanthat/posts/github-actions-run-start-delays-july-9-2026-ci-cd-protection/)
- [GitHub Actions and Pages have recovered (what to check)](/reviewchanthat/posts/github-actions-pages-recovered-july-9-2026-what-to-check-after-ci-cd-incident/)
