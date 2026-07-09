# Part 2: Self-Hosted Image Generation System

Convert content analysis into beautiful, context-aware hero images.

## Overview

Uses the **Part 1 content analysis** to generate semantic prompts, then calls image generation backends to create self-hosted images matching the post's context and tone.

### Pipeline

```
Post Markdown
    ↓
Part 1: Content Analysis (analyze_post_for_image.py)
    ↓
Analysis JSON (topic, tone, keywords, metadata)
    ↓
Part 2: Prompt Builder (image_prompt_builder.py)
    ↓
Semantic Image Prompt (natural language guidance)
    ↓
Image Generation Backend (DALL-E 3, Stable Diffusion, placeholder)
    ↓
Hero Image (PNG/WebP)
```

## New Scripts

### 1. **image_prompt_builder.py** (290 lines)
Builds natural language image prompts from analysis.

**Features:**
- Topic-specific templates (6 profiles)
- Tone and style synthesis
- Visual metaphor mapping
- Composition guidance
- Negative prompts (compliance)

**Usage:**
```bash
# Demo
python3 scripts/image_prompt_builder.py

# From analysis file
python3 scripts/image_prompt_builder.py reports/image-context/post.json
```

**Output:**
```
Subject: Busan tháng 10 (autumn leaves)
Style: nature photography, autumn aesthetic
Lighting: warm golden hour sunlight, soft shadows
Mood: nostalgic, peaceful, contemplative, travel
Composition: landscape with landmark/scene
Include: lá rụng, mùa thu, fall foliage, warm, brown
Negative: flower, rose, bloom, text, watermark
```

### 2. **generate_hero_image.py** (200 lines)
Generate and save hero images.

**Backends:**
- `dalle3` — DALL-E 3 via OpenAI API (paid, high quality)
- `placeholder` — Gradient + text (free, instant, for testing)
- (Future: stable-diffusion via Replicate)

**Usage:**
```bash
# Single post analysis → image
python3 scripts/generate_hero_image.py \
  --analysis reports/image-context/post.json \
  --backend dalle3 \
  --size 1200x630

# Post markdown → analysis → image
python3 scripts/generate_hero_image.py \
  --post content/posts/post.md \
  --backend placeholder
```

### 3. **batch_generate_images.py** (80 lines)
Generate images for all analyzed posts.

**Usage:**
```bash
# Placeholder for all posts
python3 scripts/batch_generate_images.py --backend placeholder

# DALL-E 3 for first 10 posts
python3 scripts/batch_generate_images.py --backend dalle3 --limit 10
```

## Prompt Generation Logic

### Topic Templates

Each topic has predefined:
- **Style:** Visual aesthetic (e.g., "nature photography, autumn aesthetic")
- **Lighting:** Illumination hints (e.g., "warm golden hour sunlight")
- **Mood:** Emotional tone (e.g., "nostalgic, peaceful, contemplative")
- **Details:** Key visual elements

### Examples

#### Autumn Travel (autumn_leaves)
```
Style: nature photography, autumn aesthetic
Lighting: warm golden hour sunlight, soft shadows
Mood: nostalgic, peaceful, contemplative
Keywords: lá rụng, mùa thu, fall foliage, brown, orange, warm
Negative: flower, rose, bloom, tropical, spring
```

#### Korea Travel (korea_travel)
```
Style: travel photography, cultural documentary
Lighting: natural daylight, vibrant colors
Mood: inviting, cultural, adventurous
Keywords: korea, seoul, temple, palace, street, market
Negative: japan, china, vietnam, thailand
```

#### Tech Products (apple_product)
```
Style: product photography, tech minimalism
Lighting: professional studio lighting, clean
Mood: premium, innovative, precise
Keywords: iphone, ios, camera, design, feature, battery
Negative: android, samsung, google, knockoff
```

## Compliance Integration

The system enforces compliance from Part 1 analysis:

### Forbidden Items Check
Before generating, checks if analysis flagged:
- ✅ Forbidden keywords (e.g., flowers for autumn)
- ✅ Mentions people (avoid fake people/celebrities)
- ✅ Mentions trademarks (avoid logo misuse)
- ✅ Fake UI patterns (avoid deceptive screens)

### Negative Prompts
Automatically includes to prevent:
- "text, watermark, blurry, low quality, compressed"
- Forbidden keywords from analysis
- Trademark/logo terms
- Fake UI elements

## Backend Configuration

### DALL-E 3 (OpenAI API)

**Setup:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Cost:** ~$0.04-0.10 per image (1024x1024)

**Quality:** Excellent, very controllable

**Parameters:**
- `quality`: `draft` | `standard` (default) | `hd`
- `style`: `vivid` | `natural` (default)

### Stable Diffusion (Future)

Planned via Replicate or local inference

**Setup:**
```bash
export REPLICATE_API_TOKEN="r8_..."
```

**Cost:** Free tier available, then ~$0.01-0.05 per image

### Placeholder (Fallback)

**Cost:** Free

**Quality:** Low (gradient + text), for testing only

**Used when:**
- External APIs unavailable
- Development/testing
- Fallback if API fails

## Example Workflow

```bash
# Step 1: Analyze a post (Part 1)
python3 scripts/analyze_post_for_image.py \
  --post content/posts/busan-thang-10-nen-di-dau.md \
  --out reports/image-context/busan.json

# Step 2: Build image prompt (Part 2)
python3 scripts/image_prompt_builder.py reports/image-context/busan.json

# Step 3: Generate hero image (Part 2)
python3 scripts/generate_hero_image.py \
  --analysis reports/image-context/busan.json \
  --backend placeholder

# Result: static/images/posts/busan-thang-10-nen-di-dau.webp
```

## Integration with Blog

### Manual Flow

1. Author writes post
2. CI runs Part 1: `batch_analyze_posts_for_image.py`
3. Author runs Part 2: `batch_generate_images.py`
4. Review images, commit to static/images/posts/
5. Hugo builds, deploys

### Automated Flow (Future)

- GitHub Actions runs both parts
- Generates images, commits them
- Or uploads to CDN
- Posts publish with hero images included

## Testing

Generate placeholder images for first 5 posts:

```bash
python3 scripts/batch_generate_images.py --backend placeholder --limit 5
```

Check outputs:
```bash
ls static/images/posts/*.webp | head -5
```

## Known Limitations

1. **Placeholder backend:** Low quality (gradient only)
2. **DALL-E 3:** Needs API key, costs ~$0.05 per image
3. **Stable Diffusion:** Not yet integrated (Part 2 future)
4. **Aspect ratio:** Currently 1200x630 or custom, may crop

## Next Steps

### Phase 3: Image Relevance Auditing
- Verify generated images match post context
- Automated relevance scoring
- Human-in-the-loop review gate

### Phase 4: Compliance Gate
- Block publish if forbidden items detected
- Content moderation checks
- Brand/trademark validation

### Phase 5: Multi-language Support
- Vietnamese-specific visual metaphors
- Locale-aware tone detection
- Regional image generation options

## Files

- **scripts/image_prompt_builder.py** — Prompt generation
- **scripts/generate_hero_image.py** — Single image generation
- **scripts/batch_generate_images.py** — Batch processing
- **docs/IMAGE_GENERATION_PART2.md** — This file

## Integration with Part 1

Depends on:
- `analyze_post_for_image.py` — Content analysis
- `reports/image-context/*.json` — Analysis output

Uses:
- Topic profiles (matching)
- Keywords (positive/forbidden)
- Tone indicators
- Visual metaphors
- Compliance flags
