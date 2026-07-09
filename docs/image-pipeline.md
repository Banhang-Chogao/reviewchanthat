# Image Pipeline: API-First with Self-Generated Fallback

## Policy

Review Chân Thật prioritizes high-quality stock images from trusted providers over self-generated editorial illustrations.

**Priority:**
1. **API Images** (Pexels → Pixabay → Unsplash → Freepik)
   - Typically higher quality and more natural
   - Sourced from photographer/creator verified by platform
   - Clear licensing and commercial use rights
2. **Self-Generated Fallback** (only if API fails)
   - Used when no API images meet criteria
   - Local editorial illustrations
   - Owned and attributed to Review Chân Thật

**When API selection fails:**
- No available API key for any provider
- API quota/rate-limit reached
- No suitable candidate in responses
- Provider connection error

## Attribution Rules

### API Images
**Required fields:**
- `image` — processed WebP path (no leading slash)
- `thumbnail` — same as image
- `image_provider` — "pexels" | "pixabay" | "unsplash" | "freepik"
- `image_source` — "Pexels" | "Pixabay" | "Unsplash" | "Freepik"
- `image_source_url` — original provider page/asset URL
- `image_license` — provider license name
- `image_license_url` — official provider license page
- `image_commercial_use` — must be `true`
- `image_owner` — "external"
- `image_creator` — photographer/artist name (from provider) OR empty string
- `image_creator_url` — creator profile URL (if available) OR empty string
- `image_creator_id` — provider-specific creator ID (optional)
- `image_attribution_verified` — `true` if creator name from provider, `false` if creator empty
- `image_attribution_source` — "pexels_api" | "pixabay_api" | "unsplash_api" | "freepik_api" | "not_found"
- `image_status` — "verified"

**Creator rules:**
- **If provider returns creator name:** set `image_creator`, mark `image_attribution_verified = true`
- **If provider has no creator:** set `image_creator = ""` (empty), `image_attribution_verified = false`
- **Never fake or guess creator names**

### Self-Generated Images
**Required fields:**
- `image` — processed WebP path
- `image_provider` — "self-generated"
- `image_source` — "Review Chân Thật"
- `image_source_url` — site URL
- `image_license` — "Original self-hosted editorial illustration by Review Chân Thật"
- `image_license_url` — branding/CI page
- `image_commercial_use` — `true`
- `image_owner` — "self"
- `image_creator` — "Review Chân Thật"
- `image_creator_url` — site URL
- `image_creator_id` — "review-chan-that-generated"
- `image_attribution_verified` — `true`
- `image_attribution_source` — "self_generated"
- `image_status` — "verified"

## Image Selection Process

### 1. Collect candidates from API providers
```
python3 scripts/select_images.py --post content/posts/example.md --fix
```

Queries are built from:
- Post title
- Category/tags
- First headings
- Custom topic profiles (Korea, Apple, Finance, Autumn leaves, etc.)

### 2. Lightweight matching (no heavy compliance scoring)

For each candidate, check:
- ✓ Has required fields (source_url, direct_url, license, commercial_use)
- ✓ Image size/aspect ratio suitable for hero (landscape, min 1200x630)
- ✓ No obvious topic mismatches (avoid blocked keywords)
- ✓ No obvious watermarks/logos/text overlays

**Do NOT:**
- Score based on semantic relevance using CLIP
- Score based on color palette matching
- Block deployment because of "low relevance score"
- Apply complex content compliance gates

### 3. Fallback to self-generated if needed
- Check if self-generated image exists in `assets/generated-images/<slug>.{png,jpg,webp}`
- If found, use it with self-generated metadata
- If not found, mark post as `needs_image`

### 4. Download, process, and publish
```
python3 scripts/process_images.py
```

- Download image from provider direct_url
- Crop/resize to 800x450 (16:9)
- Add watermark attribution
- Save as WebP to `static/images/posts/<slug>.webp`
- Update post frontmatter with image metadata

## Usage

### Select images for all posts with missing/bad images
```bash
python3 scripts/select_images.py --all --fix --api-first --only-missing-or-bad
```

### Force self-generated fallback only (for testing)
```bash
python3 scripts/select_images.py --post content/posts/example.md --fix --force-generated
```

### Full pipeline (recommended)
```bash
python3 scripts/refresh_all_images.py
```

Steps:
1. Audit posts
2. Select images (API → fallback)
3. Process images (download/crop/watermark)
4. Mark self-owned as verified
5. Resolve missing creator attribution from cache
6. Check attribution compliance
7. Report

## Deployment Gates

**Fail deployment only for:**
- New/changed post missing image completely
- Missing thumbnail
- Missing source URL or provider
- Missing license/commercial_use
- Fake/blocked creator detected
- Local image file missing or broken
- External hotlink instead of local processed path

**Do NOT fail for:**
- Low relevance score
- Missing creator (allowed if provider didn't supply)
- Color palette mismatch
- Content context score

**Old image debt baseline:**
- Existing posts with legacy images do not block unrelated PRs
- Use `--only-missing-or-bad` to skip already-complete images
- Image refresh is not required for non-image changes

## Provider API Configuration

Set in `.env` file (not tracked in Git):
```
PEXELS_API_KEY=your_key
PIXABAY_API_KEY=your_key
UNSPLASH_ACCESS_KEY=your_key
FREEPIK_API_KEY=your_key
```

If not set, provider is skipped gracefully.

## Cache and Artifacts

- `data/images.json` — manifest of selected images (source → destination mappings)
- `data/image-provider-cache.json` — cached creator metadata from providers
- `data/image-selection-report.json` — selection summary per post
- `reports/image-selection-report.md` — human-readable selection summary
- `static/images/posts-src/<slug>.jpg` — downloaded source image
- `static/images/posts/<slug>.webp` — processed hero image (with watermark)

## Hard Checks (CI/CD)

Run after image pipeline to ensure no regressions:
```bash
# No broken images
grep -R "fallback.webp" content public static data || true

# No fake creators
grep -R "Park Bogum\|Pexels Creator\|Unsplash Photographer\|Unknown" content data public || true

# No secrets leaked
grep -R "PEXELS_API_KEY\|PIXABAY_API_KEY\|BEGIN PRIVATE KEY" data reports public || true

# No relative image paths
grep -R 'src="/images/' public || true

# No merge conflicts
grep -R "<<<<<<<\|=======\|>>>>>>>" content data || true
```

## Architecture

```
input: content/posts/*.md
  ↓
[select_images.py]
  ├─ Try API: Pexels → Pixabay → Unsplash → Freepik
  ├─ Lightweight matching (no CLIP/color scoring)
  ├─ Fallback to self-generated if available
  └─ Output: data/images.json manifest
  ↓
[process_images.py]
  ├─ Download from direct_url
  ├─ Crop to 800x450 (16:9)
  ├─ Add watermark
  ├─ Save static/images/posts/<slug>.webp
  └─ Update post frontmatter
  ↓
[image_author_resolver.py]
  ├─ Fill missing creator from cache
  └─ Don't fake names
  ↓
[check_image_attribution.py]
  └─ Verify required fields present
  ↓
output: content/posts/*.md with image metadata
output: static/images/posts/*.webp
```

## Troubleshooting

**No API images selected:**
- Check `.env` has at least one API key configured
- Check queries are reasonable (avoid overly generic terms)
- Try `--dry-run` to see provider responses
- Check `data/image-selection-report.json` for details

**Self-generated fallback not found:**
- Post marked as `image_status: needs_image`
- Run `python3 scripts/generate_hero_image.py --post content/posts/example.md` to generate
- Or use API-only mode and skip self-generated posts

**Watermark text wrong:**
- Check `image_creator` in post frontmatter
- Creator must be from provider API (not fake/blocked)
- Use `image_author_resolver.py` to fill from cache

**Image still broken in build:**
- Check path doesn't have leading `/`
- Check WebP file exists in `static/images/posts/`
- Run `python3 scripts/qa_generated_images.py` for QA
