# VC Writer Publish Worker

Minimal Cloudflare Worker backend for the Veritable Content writer at `/admin/writer/`.

## Endpoints

- `POST /api/cms/publish`
  - Accepts `multipart/form-data`.
  - Field `payload` is JSON with metadata, full generated Markdown, image metadata, and file field names.
  - Optional `categoriesCatalog` in payload syncs `data/categories.json` before the article commit.
  - Image files are included as separate form fields referenced by `images[].fileField`.
  - Commits uploaded source images, `.meta.json` files, and `content/posts/<slug>.md` through the GitHub Contents API.
- `GET /api/cms/categories`
  - Returns the current `data/categories.json` catalog from GitHub.
- `PUT /api/cms/categories`
  - Accepts JSON `{ "message": "...", "catalog": { "items": [...], "aliases": {...} } }`.
  - Validates and commits `data/categories.json`.
- `GET /api/cms/deploy-status?run_id=<id>`
  - Optional status helper for known GitHub Actions run IDs.

## Required Secrets

Set these with `wrangler secret put`:

```bash
wrangler secret put GITHUB_TOKEN
wrangler secret put CMS_ADMIN_SECRET
```

Do not put either value in `wrangler.jsonc`, localStorage, or committed files.

## Required Vars

Configured in `wrangler.jsonc`:

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_BRANCH`
- `GITHUB_DEPLOY_WORKFLOW`
- `CMS_ALLOWED_ORIGIN`
- `CMS_CONTENT_DIR`
- `CMS_IMAGE_SOURCE_DIR`
- `CMS_PUBLIC_SITE_BASE`
- `CMS_MAX_IMAGE_BYTES`

Optional:

- `CMS_COMMITTER_NAME`
- `CMS_COMMITTER_EMAIL`
- `CMS_FORCE_WORKFLOW_DISPATCH=true`

## GitHub Token Permissions

Use a fine-grained token or GitHub App token with:

- Repository contents: read/write
- Actions workflows: read/write, only if manual workflow dispatch is required

This repository deploy workflow already runs on `push` to `main` and supports `workflow_dispatch`. The Worker detects the push trigger and returns `deploy.status = "auto_on_push"` unless `CMS_FORCE_WORKFLOW_DISPATCH=true`.

## Publish Flow

1. Validate admin bearer token.
2. Validate metadata, generated Markdown, slug, date, image metadata, and blocked strings.
3. Upload source images to `static/images/posts-src/`.
4. Upload source image metadata to `static/images/posts-src/<file>.meta.json`.
5. Commit Markdown to `content/posts/<slug>.md`.
6. Return commit SHA, article path, predicted URL, uploaded image paths, and deploy status.

The image pipeline processes source images during GitHub Actions deploy and writes watermarked WebP files to `static/images/posts/`.

## Local Development

```bash
cd workers/cms-publish
wrangler dev
```

Then set the API endpoint in the admin writer UI to the local Worker URL and use the `CMS_ADMIN_SECRET` value as the admin token.
