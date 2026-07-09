# Image Context Analysis System

Content understanding layer for smarter, context-aware image generation.

## Overview

Before generating hero images for blog posts, the system analyzes the content to understand:
- **Primary topic** (autumn travel, tech products, regulatory compliance, etc.)
- **Entities** (locations, products, brands mentioned)
- **Keywords** extracted via TF-IDF
- **Tone** (travel, casual, formal, technical, emotional)
- **Audience** (travelers, developers, finance users, etc.)
- **Visual metaphors** and thematic concepts
- **Positive keywords** to include in images
- **Forbidden keywords** to avoid (compliance check)
- **Key facts** from the post
- **Palette suggestions** based on topic
- **Composition hints** for image generation

This enables:
1. **Relevance:** Images match article context, not off-topic stock photos
2. **Compliance:** Flags forbidden items (fake people, fake UI, trademarks, etc.)
3. **Quality:** Structured data guides AI image generation with context
4. **Auditability:** JSON + Markdown reports for review

## Usage

### Single Post Analysis

Analyze one post and output JSON + Markdown report:

```bash
python3 scripts/analyze_post_for_image.py \
  --post content/posts/example.md \
  --out reports/image-context/example.json \
  --md reports/image-context/example.md
```

Output:
- `reports/image-context/example.json` — Structured analysis data
- `reports/image-context/example.md` — Human-readable report

### Batch Analysis

Analyze all posts or first N posts:

```bash
python3 scripts/batch_analyze_posts_for_image.py

# Limit to first 10 posts
python3 scripts/batch_analyze_posts_for_image.py --limit 10
```

Outputs:
- `reports/image-context/` — JSON analysis for each post
- `reports/image-context-summary.json` — Aggregated statistics
- `reports/image-context-summary.md` — Summary report by topic

## JSON Output Schema

```json
{
  "slug": "post-slug",
  "title": "Post title",
  "description": "Meta description",
  "primary_topic": "autumn_leaves",
  "topic_confidence": 0.8,
  "entities": {
    "locations": ["Busan", "Seoul"],
    "products": [],
    "brands": []
  },
  "keywords": ["biển", "busan", "mùa"],
  "tone": ["travel"],
  "audience": "travelers, nature enthusiasts",
  "search_intent": "User wants to understand: autumn_leaves",
  "visual_metaphors": [],
  "positive_keywords": ["lá rụng", "mùa thu", "autumn leaves"],
  "forbidden_keywords": ["flower", "rose", "bloom"],
  "key_facts": ["Busan tháng 10 mát...", "Lá đỏ ở Busan..."],
  "mentions_people": false,
  "mentions_products": false,
  "mentions_trademarks": false,
  "image_hint": "Topic: autumn_leaves | Tone: travel | Include: lá rụng...",
  "palette_suggestion": ["burnt-orange", "deep-brown", "amber"],
  "composition_hint": "landscape with landmark/scene, human-scale perspective",
  "has_forbidden_items": false,
  "forbidden_items_found": []
}
```

## Topic Profiles

The system recognizes these topic categories (ordered by specificity):

### 1. **apple_dma** — Apple Regulatory / DMA
- **Keywords:** DMA, Digital Markets Act, gatekeeper, notarization, sideload, anti-steering
- **Audience:** Tech policy enthusiasts, developers
- **Tone:** Technical, regulatory, analytical
- **Forbidden:** Conspiracy, fake law, misleading regulation

### 2. **thailand_travel** — Thailand Travel
- **Keywords:** Bangkok, Phuket, Chiang Mai, temple, beach, tropical
- **Audience:** Travelers, beach enthusiasts
- **Tone:** Travel, relaxed
- **Forbidden:** Japan, Korea, Europe, cold

### 3. **korea_travel** — Korea Travel
- **Keywords:** Seoul, Busan, Jeju, hanbok, temple, palace
- **Audience:** Travelers, Korea enthusiasts
- **Tone:** Travel, cultural
- **Forbidden:** Japan, China, Vietnam

### 4. **autumn_leaves** — Seasonal Travel / Autumn
- **Keywords:** Lá rụng, mùa thu, fall foliage, dry leaves, brown, orange
- **Audience:** Travelers, nature enthusiasts
- **Tone:** Travel, contemplative
- **Forbidden:** Flower, rose, bloom, tropical, spring
- **Palette:** burnt-orange, deep-brown, amber, warm-gold

### 5. **apple_product** — Apple Tech Products
- **Keywords:** iPhone, iOS, camera, design, feature, battery
- **Audience:** Tech enthusiasts, Apple users
- **Tone:** Tech, analytical
- **Forbidden:** Android, Samsung, Google, knockoff

### 6. **finance_banking** — Finance & Banking
- **Keywords:** Banking, payment, credit card, ATM, transfer, fintech
- **Audience:** Finance users, tech enthusiasts
- **Tone:** Technical, informative
- **Forbidden:** Nature, flower, casual

## Compliance Checks

The system flags content with:
- `mentions_people` — If post mentions creating people/celebrities
- `mentions_products` — If post features real products
- `mentions_trademarks` — If post mentions brands
- `has_forbidden_items` — If post contains regulatory red flags

### Forbidden Item Categories

1. **autumn_leaves**: Flowers, blooms (use tree leaves, not flowers)
2. **people_avoidance**: Celebrity, person, portrait (avoid fake people)
3. **trademark**: Logo, official branding (avoid trademark misuse)
4. **fake_ui**: Fake screenshot, mock UI (avoid deceptive interfaces)

## Integration with Image Generation

The analysis output guides image generation systems:

1. **`image_hint`** — Semantic prompt for image models
2. **`palette_suggestion`** — Recommended color palette
3. **`composition_hint`** — Visual layout guidance
4. **`positive_keywords`** — Terms to emphasize
5. **`forbidden_keywords`** — Terms to avoid
6. **`has_forbidden_items`** — Block image if compliance fails

Example AI image prompt construction:
```
Topic: {primary_topic}
Tone: {tone}
Include: {positive_keywords}
Avoid: {forbidden_keywords}
Palette: {palette_suggestion}
Composition: {composition_hint}
```

## Improvement Opportunities

1. **Add NER (Named Entity Recognition)** — Better entity extraction (using spaCy or transformers)
2. **Semantic Search Intent** — Use embeddings to detect search intent
3. **Visual Mood Classification** — Map tone to visual styles
4. **Multi-language Support** — Better Vietnamese NLP
5. **Domain-Specific Training** — Fine-tune models on Review Chân Thật corpus
6. **Forbidden Item Auditing** — Verify images don't violate compliance flags

## Files

- **scripts/analyze_post_for_image.py** — Single-post analyzer
- **scripts/batch_analyze_posts_for_image.py** — Batch analyzer for all posts
- **reports/image-context/** — Generated JSON analysis files
- **reports/image-context-summary.md** — Aggregated topic report
- **docs/IMAGE_CONTEXT_ANALYSIS.md** — This file

## Hard Rules (From Owner)

1. ✅ Extract topic, entities, tone, audience BEFORE drawing
2. ✅ Flag forbidden items (flowers for autumn, fake people, trademarks)
3. ✅ Don't fake creator attribution
4. ✅ Don't use logo/trademark without permission
5. ✅ Don't create fake screenshots/UI
6. ✅ Don't use off-topic images
7. ✅ Don't publish if hero image doesn't pass compliance
8. ✅ Don't call secrets from frontend
9. ✅ Don't hardcode URLs (missing `/reviewchanthat/`)

## Next Steps

1. ✅ **Phase 1:** Content understanding layer (you are here)
2. **Phase 2:** Self-hosted image generation system (Gradio/DALL-E local)
3. **Phase 3:** Integrate analysis → image generation pipeline
4. **Phase 4:** Image relevance auditing + compliance gate
5. **Phase 5:** Multi-language support (Vietnamese + English)
