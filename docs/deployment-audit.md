# Deployment speed audit

Date: 2026-07-18 (Asia/Ho_Chi_Minh)

## Target graph

```text
PR:       checkout (shallow) → cached minimal Python → changed-content/workflow QA
main:     checkout (shallow) → cached Hugo/Python → parallel critical QA
          → one Hugo build → post-build QA → Pages artifact → Pages deploy
          → live homepage/SHA/404 smoke check
nightly:  SEO/content direction/images/links/analytics/ML/doctor maintenance
```

The production job owns the only Hugo build used for the release. The deploy job
consumes that artifact and never checks out source or rebuilds it. No R2 or local
Hugo build is used.

## Workflow and job classification

| Workflow / job | Previous role | Decision | Reason / estimated time saved | Risk and rollback |
|---|---|---|---|---|
| `deploy.yml` / `build` | Installed full Python stack, processed every image, ran content direction, optimizer, ML, reports, Hugo, then post-build QA | KEEP / MERGE | Canonical release path; removed full image processing and noncritical reports; parallelized independent source/public gates. Estimated 3–12 min per deploy, plus API/rate-limit variance. | Missing tracked image or QA defect can block release; restore prior build steps from git if required. |
| `deploy.yml` / `deploy` | Pages deployment after build | KEEP | Required Pages upload/deploy; now cancelable per ref and followed by live smoke. | Pages failure remains visible; rerun workflow or revert the pipeline commit. |
| `pr-check.yml` / `build-check` | Full Hugo build, full date/sitemap/link scans, image API autofix, duplicate Hugo install/version | MERGE / KEEP | Fast changed-content/workflow QA only; production build is reserved for `main`. Minimal `requirements-ci.txt` avoids installing ML/analytics/image stack. Estimated 1–5 min per PR. | PRs no longer prove a full render; `main` build and smoke remain the release gate. Restore a PR build temporarily if a template regression needs diagnosis. |
| `auto-merge.yml` / `evaluate` | Label/rebase/enable auto-merge | KEEP | Policy automation, not a release build; checkout/action tags pinned. | Disable auto-merge or remove the label if it misclassifies a PR. |
| `autobot-*.yml` jobs | Nightly content/SEO/link/image maintenance with direct commits | MOVE / KEEP | Already schedule/manual-only; excluded generated reports stay out of release triggers. Keep their automation isolated from production. | Bot changes still pass the canonical `main` pipeline; disable the individual schedule if noisy. |
| `content-direction.yml` / `content-direction` | Scheduled report, QA, Hugo render, report commit | MOVE / KEEP | Noncritical content-direction work stays daily/manual and is not part of production build. | Manual dispatch remains available; revert that workflow independently. |
| `content-direction-optimizer.yml` / `optimize` | Nightly all-safe metadata/link/freshness/gap mutations and QA | MOVE / KEEP | Heavy content work is outside release path and remains manually/scheduled. | Revert its bot PR/commit; production content QA remains active. |
| `ga4-footer.yml` / `fetch` | Six-hour analytics fetch, generated-data commit, explicit deploy trigger | MOVE / KEEP | Analytics is scheduled/manual, never a PR/release prerequisite; latest run cancels older runs. Its explicit deploy trigger remains because the footer data is site-visible. | Disable schedule or revert generated data; Pages deploy remains independent of analytics QA. |
| `ml-retrain.yml` / `auto-train` | Retrained on schedule and every matching `main` push, then committed model/data | MOVE / KEEP | Removed the `push` trigger to prevent every content/model update from starting another release; schedule/manual remains. | Manual retrain is available; revert only the trigger change if push-driven retraining is required. |
| `deployment-doctor.yml` / `doctor` | Manual report collection, diagnosis, autofix, dashboard commit | MOVE / KEEP | Manual maintenance and diagnosis, not release blocking; shallow checkout is sufficient. | Dispatch manually; revert the workflow if dashboard export needs the old history. |
| `autofix-on-deploy-fail.yml` / `autofix` | Automatic post-failure full-tree mutation and deploy retry | DISABLE AUTO / KEEP MANUAL | Prevents bot commits, full-tree fixes, and recursive deploy retries from racing the canonical pipeline. Manual input requires affected post paths and applies only scoped fixes. | Dispatch with explicit scope; revert this workflow if automatic recovery is proven safe. |
| `pr-autofix.yml` / `autofix` | Manual normalization autofix with full requirements install | KEEP / OPTIMIZE | Still manual, but uses cached minimal CI requirements. | Run manually or revert dependency change. |
| `post-merge-autofix.yml` / `delegate-to-doctor` | Manual wrapper that only dispatched Deployment Doctor | REMOVE | Duplicated the doctor dispatch with no additional behavior. Estimated 10–30 sec and one confusing workflow entry per use. | Restore the deleted file if a separate compatibility trigger is required. |
| `qa-debt-fix.yml` / `fix-debt` | Manual debt reader whose `changed` output was hardcoded false | REMOVE | Dead/no-op workflow; did not reach its PR steps. | Restore from git if its implementation is completed later. |

## Production step classification

| Step | Decision | Reason |
|---|---|---|
| Shallow checkout | KEEP | Source is sufficient; no history-dependent release step remains. |
| Python/Hugo setup and caches | KEEP / MERGE | One Python setup, minimal lock file, explicit cache keys; one Hugo version and Hugo build cache. |
| Frontmatter, dates, summary, hero, inline QA | KEEP | Essential TOML, real-date, image existence, and render-hook guards; read-only and parallel. |
| Full `process_images.py` | REMOVE FROM RELEASE | WebP assets are tracked; downloading/converting every post on every deploy is slow and can hit provider limits. Image selection remains author/maintenance workflow responsibility and hero QA blocks missing assets. |
| Content direction / optimizer / ML risk / report generation | MOVE | Diagnostic and editorial maintenance, not release correctness. |
| Single Hugo build | KEEP | The only build that feeds the Pages artifact. |
| Generated posts sitemap, internal links, sitemap, index/404 checks | KEEP | Essential public-output validation, parallel after the build. |
| Pages upload/deploy | KEEP | Required production delivery. |
| Live smoke | KEEP | Confirms the homepage, deployed commit metadata, and 404 behavior after Pages deployment. |

## Timing and rollback

The timed wrapper records UTC start/end and seconds in the Actions log and job
summary for dependency install, source QA, metadata, version generation, Hugo,
sitemap generation, public QA, and live smoke. The baseline estimates above are
replaced with measured values after the first green PR and production run.

Rollback is one revert of the audit PR. That restores the previous workflow files;
content and tracked image assets are not changed by this audit. If only the new
release path is problematic, dispatch the manual scoped autofix for a confirmed
post path, then rerun `Deploy to GitHub Pages` after review.
