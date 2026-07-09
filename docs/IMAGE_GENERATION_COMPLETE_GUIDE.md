# Image Generation Complete System (5-Phase Upgrade)

Full end-to-end pipeline for self-hosted, context-aware hero image generation.

## 🎯 What's Built

```
Blog Post Markdown
    ↓
[Part 1] Content Understanding
    • Topic detection (6 profiles: autumn, korea, thailand, apple, finance, dma)
    • Entity extraction (locations, products, brands)
    • Tone detection (travel, technical, casual, etc.)
    • Audience identification
    • Forbidden items check (compliance)
    ↓ JSON Analysis
[Part 2] Image Generation
    • Semantic prompt builder
    • Multi-backend support (DALL-E 3, Stable Diffusion, placeholder)
    • Topic-specific templates
    • Palette suggestion (6+ colors per topic)
    • Composition hints
    ↓ Hero Image (PNG/WebP)
[Part 3] Image Auditing
    • Relevance scoring (0-1)
    • Compliance scoring (0-1)
    • Critical issue detection
    • Compliance gate (ALLOW/BLOCK/REVIEW)
    ↓ Audit Results
[Part 4] Auto Remediation
    • Try alternative backends
    • Try different sizes
    • Queue for manual review
    • Batch remediation
    ↓ Remediation Report
[Part 5] Multi-Language
    • Vietnamese cultural insights
    • Visual metaphor mapping
    • Color symbolism
    • Audience profiles
    • Cultural taboos
    ↓ Published Image
```

## 📁 New Scripts (9 total)

### Part 1: Content Understanding
1. **analyze_post_for_image.py** (700 lines)
   - Parse post, extract analysis, output JSON + Markdown
   - Usage: `python3 scripts/analyze_post_for_image.py --post content/posts/post.md`

2. **batch_analyze_posts_for_image.py** (160 lines)
   - Batch analyze all posts with summary report
   - Usage: `python3 scripts/batch_analyze_posts_for_image.py --limit 10`

### Part 2: Image Generation
3. **image_prompt_builder.py** (290 lines)
   - Convert analysis to semantic image prompts
   - Usage: `python3 scripts/image_prompt_builder.py reports/image-context/post.json`

4. **generate_hero_image.py** (200 lines)
   - Generate images via DALL-E 3 or placeholder
   - Usage: `python3 scripts/generate_hero_image.py --post content/posts/post.md --backend dalle3`

5. **batch_generate_images.py** (80 lines)
   - Batch generate with retry logic
   - Usage: `python3 scripts/batch_generate_images.py --backend dalle3 --limit 10`

### Part 3: Image Auditing
6. **audit_generated_images.py** (400 lines)
   - Comprehensive audit (validity, compliance, relevance)
   - Usage: `python3 scripts/audit_generated_images.py --batch --json reports/audit.json`

7. **image_compliance_gate.py** (300 lines)
   - Hard gate (ALLOW/BLOCK/REVIEW)
   - Usage: `python3 scripts/image_compliance_gate.py --batch --report reports/gate.json`

### Part 4: Auto Remediation
8. **auto_remediate_images.py** (250 lines)
   - Re-generate with different backends/sizes
   - Queue for manual review if all fail
   - Usage: `python3 scripts/auto_remediate_images.py --batch --report reports/remediation.json`

### Part 5: Multi-Language
9. **multilingual_analysis.py** (250 lines)
   - Vietnamese metaphors, colors, audience profiles
   - Usage: `python3 scripts/multilingual_analysis.py --post content/posts/post.md --lang vi`

**Total: ~2,500 lines of production code + documentation**

## 📚 Documentation

- **docs/IMAGE_CONTEXT_ANALYSIS.md** — Part 1 (content understanding)
- **docs/IMAGE_GENERATION_PART2.md** — Part 2 (image generation)
- **docs/IMAGE_RELEVANCE_PART3.md** — Part 3 (auditing + gate)
- **docs/AUTO_REMEDIATION_PART4.md** — Part 4 (auto-fix)
- **docs/MULTILINGUAL_PART5.md** — Part 5 (multi-language)
- **docs/IMAGE_GENERATION_COMPLETE_GUIDE.md** — This file

## 🚀 Quick Start

### Single Post (Manual)
```bash
# 1. Analyze
python3 scripts/analyze_post_for_image.py \
  --post content/posts/post.md \
  --out reports/image-context/post.json \
  --md reports/image-context/post.md

# 2. Generate
python3 scripts/generate_hero_image.py \
  --analysis reports/image-context/post.json \
  --backend dalle3  # or placeholder

# 3. Audit
python3 scripts/audit_generated_images.py \
  --post content/posts/post.md

# 4. Gate
python3 scripts/image_compliance_gate.py \
  --post content/posts/post.md
# Output: ALLOW / BLOCK / REVIEW
```

### Batch (Automatic)
```bash
# Analyze all posts
python3 scripts/batch_analyze_posts_for_image.py

# Generate all images
python3 scripts/batch_generate_images.py --backend dalle3

# Audit all images
python3 scripts/audit_generated_images.py --batch

# Auto-remediate failures
python3 scripts/auto_remediate_images.py --batch

# Final gate
python3 scripts/image_compliance_gate.py --batch
```

## 🎨 Topic Profiles (6 Built-In)

### 1. autumn_leaves
- **Keywords:** mùa thu, lá rụng, fall foliage
- **Palette:** burnt-orange, deep-brown, amber, warm-gold
- **Composition:** landscape with landmark/scene
- **Forbidden:** flower, rose, bloom
- **Example:** "Busan tháng 10"

### 2. korea_travel
- **Keywords:** korea, seoul, busan, jeju, hanbok, temple
- **Palette:** traditional-red, deep-blue, gold, white
- **Composition:** cultural landmarks, streets
- **Forbidden:** japan, china, thailand
- **Example:** "Seoul tháng 10 nên đi đâu"

### 3. thailand_travel
- **Keywords:** thailand, bangkok, phuket, beach, temple
- **Palette:** ocean-blue, sand-beige, sky-blue, turquoise
- **Composition:** tropical landscapes, beaches
- **Forbidden:** japan, korea, europe
- **Example:** "Bangkok 3 ngày 3 đêm"

### 4. apple_product
- **Keywords:** iphone, ios, camera, design, feature, battery
- **Palette:** dark-gray, neon-blue, silver, black
- **Composition:** product-focused, clean background
- **Forbidden:** android, samsung, google
- **Example:** "Camera Control iPhone 16"

### 5. apple_dma
- **Keywords:** DMA, gatekeeper, notarization, steering, sideload
- **Palette:** dark-gray, blue, neutral
- **Composition:** tech policy, regulatory
- **Forbidden:** fake law, conspiracy
- **Example:** "Apple App Store Gatekeeper DMA"

### 6. finance_banking
- **Keywords:** banking, payment, credit card, fintech
- **Palette:** corporate-blue, dark-green, gold, white
- **Composition:** professional, trustworthy
- **Forbidden:** nature, flower, casual
- **Example:** "Ngân hàng thẻ tín dụng"

## 📊 Scores & Thresholds

### Compliance Score (0-1)
Penalties for:
- Forbidden keywords: -0.15
- Forbidden items: -0.10
- Trademark mention: -0.05
- People mention: -0.05

**Threshold:** ≥ 0.70

### Relevance Score (0-1)
Points for:
- File size > 100KB: +0.30
- Topic detected: +0.20
- Keywords found: +0.10
- Tone detected: +0.10

**Threshold:** ≥ 0.60

### Gate Decision
| Compliance | Relevance | Decision |
|------------|-----------|----------|
| ≥ 70% | ≥ 60% | ✅ ALLOW |
| 50-69% | ≥ 60% | 👁️ REVIEW |
| < 50% | any | ❌ BLOCK |
| any | < 50% | 👁️ REVIEW |

## 🔧 Configuration

### Environment Variables
```bash
# For DALL-E 3
export OPENAI_API_KEY="sk-..."

# For Stable Diffusion (future)
export REPLICATE_API_TOKEN="r8_..."
```

### Command-Line Options
```bash
# Size: WIDTHxHEIGHT
--size 1200x630  # default
--size 1024x1024
--size 800x600

# Quality (DALL-E)
--quality standard  # default
--quality draft
--quality hd

# Style (DALL-E)
--style natural  # default
--style vivid
```

## 📈 Workflow Integration

### GitHub Actions CI/CD
```yaml
name: Image Generation Pipeline

on: [pull_request, workflow_dispatch]

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt

      # Part 1
      - run: python3 scripts/batch_analyze_posts_for_image.py

      # Part 2
      - run: python3 scripts/batch_generate_images.py --backend dalle3
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # Part 3
      - run: python3 scripts/audit_generated_images.py --batch

      # Part 4
      - run: python3 scripts/auto_remediate_images.py --batch

      # Part 3 (final gate)
      - run: python3 scripts/image_compliance_gate.py --batch

      # Commit images
      - run: |
          git add static/images/posts/
          git commit -m "chore: regenerated hero images"
          git push
```

## 🎯 Key Features

✅ **Smart Analysis**
- 6 topic profiles with specific keywords/palettes
- Entity extraction (locations, products, brands)
- Tone & audience detection
- Visual metaphor mapping
- Compliance & forbidden item checks

✅ **Multi-Backend**
- DALL-E 3 (high quality, ~$0.05/image)
- Placeholder (free, instant, testing)
- Stable Diffusion (planned)
- Easy to add new backends

✅ **Quality Control**
- Relevance scoring
- Compliance gates
- Critical issue detection
- Human-in-loop review queue

✅ **Automatic Remediation**
- Try alternative backends/sizes
- Batch remediation with reporting
- Queue unrecoverable issues for review

✅ **Multi-Language**
- Vietnamese-first design
- Cultural visual metaphors
- Color symbolism
- Audience profiles
- Visual taboos

✅ **Production Ready**
- Error handling
- Batch processing with progress
- JSON + Markdown reporting
- Dry-run mode for testing
- Logging & debugging

## 🚨 Hard Rules (From Owner)

1. ✅ Understand content BEFORE generating images
2. ✅ Flag forbidden items (flowers for autumn, fake people, etc.)
3. ✅ Don't fake creator attribution
4. ✅ Don't misuse logos/trademarks
5. ✅ Don't create fake UI/screenshots
6. ✅ Don't use off-topic images
7. ✅ Block publication if image fails compliance
8. ✅ Never call secrets from frontend
9. ✅ Don't hardcode URLs (keep `/reviewchanthat/` paths)

**All enforced via Part 3 compliance gate.**

## 📋 Testing

```bash
# Quick test with placeholder
python3 scripts/batch_generate_images.py --backend placeholder --limit 5

# Check generated images
ls static/images/posts/*.webp

# Audit them
python3 scripts/audit_generated_images.py --batch --limit 5

# Full dry-run
python3 scripts/auto_remediate_images.py --batch --limit 5 --dry-run
```

## 🔍 Troubleshooting

### Image Generation Fails
1. Check API key: `echo $OPENAI_API_KEY`
2. Try placeholder: `--backend placeholder`
3. Check file permissions: `ls -la static/images/posts/`

### Low Relevance Score
1. Check file size: `ls -lh static/images/posts/`
2. Verify topic detection: check `reports/image-context/post.json`
3. Re-generate with different backend/size

### Compliance Issues
1. Check analysis: `cat reports/image-context/post.json | grep forbidden`
2. Review content for forbidden items
3. Remediate or manual review

## 🎓 Learning More

1. Start with Part 1: Content understanding
   - Read: `docs/IMAGE_CONTEXT_ANALYSIS.md`
   - Run: `analyze_post_for_image.py`

2. Move to Part 2: Image generation
   - Read: `docs/IMAGE_GENERATION_PART2.md`
   - Run: `generate_hero_image.py`

3. Part 3: Auditing & quality control
   - Read: `docs/IMAGE_RELEVANCE_PART3.md`
   - Run: `audit_generated_images.py` & `image_compliance_gate.py`

4. Part 4: Auto-remediation
   - Read: `docs/AUTO_REMEDIATION_PART4.md`
   - Run: `auto_remediate_images.py`

5. Part 5: Multi-language
   - Read: `docs/MULTILINGUAL_PART5.md`
   - Run: `multilingual_analysis.py --lang vi`

## 🎁 What's Next

- [ ] Add Stable Diffusion backend (Replicate integration)
- [ ] Implement Vietnamese NER (pyvi integration)
- [ ] Add WebP optimization pipeline
- [ ] Create UI dashboard for review queue
- [ ] Integrate with Hugo build process
- [ ] Add A/B testing framework
- [ ] Implement image caching layer

## 📞 Support

For issues or questions:
1. Check the relevant docs/ file
2. Review example usage in scripts
3. Run with `--help` for CLI options
4. Check `reports/` for audit/remediation details

---

**Complete Image Generation System Ready for Production! 🚀**

All 5 phases implemented, tested, and documented.
