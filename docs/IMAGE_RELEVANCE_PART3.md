# Part 3: Image Relevance Auditing & Compliance Gate

Verify generated images are relevant and compliant before publishing.

## Overview

Quality control pipeline:

```
Generated Image (from Part 2)
    ↓
Image Audit (check validity, compliance, relevance)
    ↓
Compliance Gate (ALLOW | BLOCK | REVIEW)
    ↓
Publishing Decision
```

## New Scripts

### 1. audit_generated_images.py
Comprehensive image audit system.

**Checks:**
- ✅ File exists and is valid
- ✅ No forbidden items detected
- ✅ Compliance score (0-1) based on analysis flags
- ✅ Relevance score (0-1) based on topic/keywords
- ✅ Compliance issues catalog

**Usage:**
```bash
# Single post
python3 scripts/audit_generated_images.py --post content/posts/post.md

# Batch audit all
python3 scripts/audit_generated_images.py --batch \
  --json reports/image-audit.json \
  --md reports/image-audit.md
```

**Output:**
```json
{
  "slug": "busan-thang-10-nen-di-dau",
  "title": "Busan tháng 10...",
  "exists": true,
  "is_valid": true,
  "file_size": 152000,
  "dimensions": [1200, 630],
  "compliance_score": 0.85,
  "relevance_score": 0.75,
  "compliance_issues": [],
  "passes_audit": true
}
```

### 2. image_compliance_gate.py
Hard gate that blocks/allows publishing.

**Rules:**
1. Image MUST exist
2. Image MUST be valid (not corrupted)
3. Compliance ≥ 70%
4. Relevance ≥ 60%
5. No critical issues (fake, trademark, forbidden)

**Decision Types:**
- `ALLOW` — Publish, image passes all checks
- `BLOCK` — Stop, critical failure (missing, corrupted, forbidden items)
- `REVIEW` — Manual review needed (low compliance/relevance)

**Usage:**
```bash
# Gate single post
python3 scripts/image_compliance_gate.py --post content/posts/post.md

# Output: ALLOW | BLOCK | REVIEW + reason

# Batch gate all posts
python3 scripts/image_compliance_gate.py --batch \
  --report reports/gate-decisions.json

# Strict mode: BLOCK instead of REVIEW on low scores
python3 scripts/image_compliance_gate.py --batch --fail-on-missing
```

## Audit Scores

### Compliance Score (0-1)

Penalties:
- Forbidden keyword in filename: -0.15
- Forbidden items in analysis: -0.10
- Mentions people: -0.05
- Mentions trademarks: -0.05

**Examples:**
- No issues → 1.00 ✅
- Forbidden keyword → 0.85
- Trademark mention → 0.95
- People + trademark → 0.90

### Relevance Score (0-1)

Heuristics:
- File size > 100KB: +0.30
- File size > 50KB: +0.20
- File size < 5KB: -0.20 (placeholder)
- Topic detected: +0.20
- Keywords found: +0.10
- Tone detected: +0.10

**Examples:**
- Substantial image + all metadata: 0.80-1.00
- Minimal content: 0.30-0.50
- Placeholder: 0.20-0.40

## Integration Points

### With Part 1 (Analysis)
Uses:
- `has_forbidden_items` flag
- `forbidden_items_found` list
- `mentions_people`, `mentions_trademarks`
- `topic`, `tone`, `keywords`

### With Part 2 (Generation)
Audits:
- Generated images (file path)
- Prompt used
- Backend used
- Generation metadata

## Workflow

### Manual
```bash
# 1. Analyze post
python3 scripts/analyze_post_for_image.py --post content/posts/post.md

# 2. Generate image
python3 scripts/generate_hero_image.py --post content/posts/post.md

# 3. Audit image
python3 scripts/audit_generated_images.py --post content/posts/post.md

# 4. Gate decision
python3 scripts/image_compliance_gate.py --post content/posts/post.md
# Output: ALLOW / BLOCK / REVIEW
```

### Automated (CI/CD)
```yaml
# .github/workflows/image-gate.yml
- name: Analyze posts
  run: python3 scripts/batch_analyze_posts_for_image.py

- name: Generate images
  run: python3 scripts/batch_generate_images.py --backend dalle3

- name: Audit images
  run: python3 scripts/audit_generated_images.py --batch

- name: Gate check
  run: python3 scripts/image_compliance_gate.py --batch --fail-on-missing
```

## Thresholds

| Metric | Threshold | Reason |
|--------|-----------|--------|
| Compliance Score | ≥ 70% | Must be substantially compliant |
| Relevance Score | ≥ 60% | Can accept some uncertainty |
| File Size (Relevant) | > 50KB | Indicates real content, not placeholder |
| File Size (Placeholder) | < 5KB | Fallback warning |

## Compliance Issues

### Critical (Block)
- "fake": Deceptive content
- "trademark": Brand misuse
- "forbidden": Policy violation
- Missing/corrupted image

### Warning (Review)
- Low compliance/relevance score
- Large file size variance
- Unusual metadata

## Example Report

```markdown
# Image Audit Report

**Total images:** 150
**Passed:** 142 (95%)
**Failed:** 8 (5%)

## ✅ Passed Images
- `busan-thang-10-nen-di-dau` (compliance: 85%, relevance: 75%)
- `bangkok-3-ngay-3-dem` (compliance: 90%, relevance: 70%)

## ❌ Failed Images
- `app-store-gatekeeper` (compliance: 45%, relevance: 55%)
  - Post mentions trademarks - verify image doesn't misuse brands
  - Compliance score too low
```

## Next Steps: Part 4

### Automatic Remediation
- Re-generate if fails
- Try different backend
- Fallback strategies

### Human-in-the-Loop
- Queue for manual review
- Suggest image adjustments
- Collect feedback

### Integration
- Block merge if gate fails
- Publish comment on PR
- Prevent workflow progression

## Files

- `scripts/audit_generated_images.py` — Image audit (400 lines)
- `scripts/image_compliance_gate.py` — Compliance gate (300 lines)
- `docs/IMAGE_RELEVANCE_PART3.md` — This file

Depends on:
- Part 1: Content analysis
- Part 2: Image generation
