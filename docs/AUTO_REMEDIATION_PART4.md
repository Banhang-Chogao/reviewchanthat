# Part 4: Automatic Remediation & Human-in-Loop Review

Auto-fix failed images and queue critical issues for human review.

## Overview

When image fails compliance gate:

```
Failed Image (compliance or relevance too low)
    ↓
Auto-remediate (try different backend/parameters)
    ↓
SUCCESS: Image passes new audit
    ├─ BLOCK: Critical issues → queue review
    ├─ REVIEW: Low scores → human review
    └─ ALLOW: Passes → publish
```

## New Scripts

### auto_remediate_images.py

**Remediation strategy:**
1. Try different backend (dalle3 → placeholder)
2. Try different size (1200x630 → 1024x1024)
3. Create better placeholder with topic colors
4. Queue for manual review if all fail

**Usage:**
```bash
# Single post
python3 scripts/auto_remediate_images.py --post content/posts/post.md

# Batch with dry-run
python3 scripts/auto_remediate_images.py --batch --dry-run

# Actual remediation + report
python3 scripts/auto_remediate_images.py --batch --report reports/remediation.json
```

**Results:**
```json
{
  "slug": "post-slug",
  "original_reason": "Compliance score too low",
  "attempt": 2,
  "backend": "dalle3",
  "result": "SUCCESS|FAILED|MANUAL_REVIEW"
}
```

## Workflow

### For Failed Image:

```bash
# 1. Image fails gate
python3 scripts/image_compliance_gate.py --post content/posts/post.md
# Output: BLOCK "Compliance 45% < 70%"

# 2. Auto-remediate
python3 scripts/auto_remediate_images.py --post content/posts/post.md
# Output: ✅ Remediation successful!
#   Attempt 1: dalle3, size 1200x630
#   Audit: compliance 82%, relevance 75%

# 3. Verify passes
python3 scripts/image_compliance_gate.py --post content/posts/post.md
# Output: ALLOW "Compliance 82%, Relevance 75%"
```

### Batch Workflow:

```bash
# Audit all
python3 scripts/audit_generated_images.py --batch \
  --json reports/audit.json --md reports/audit.md

# Analyze failures
grep '"passes_audit": false' reports/audit.json | wc -l  # 12 failures

# Remediate
python3 scripts/auto_remediate_images.py --batch \
  --report reports/remediation.json

# Check results
cat reports/remediation.json | grep '"result"'
# "successful": 8
# "manual_review": 4
```

## Decision Queue

Images that fail auto-remediation go to review queue:

```json
{
  "timestamp": "2026-07-09T...",
  "queue_items": [
    {
      "slug": "post-slug-1",
      "issue": "Compliance 40% (forbidden items detected)",
      "suggested_action": "Review content + regenerate with stricter filters",
      "reviewer": null,
      "status": "pending"
    },
    {
      "slug": "post-slug-2",
      "issue": "Relevance 50% (mismatched image for topic)",
      "suggested_action": "Manually select better image or regenerate",
      "reviewer": null,
      "status": "pending"
    }
  ]
}
```

## Integration with CI/CD

```yaml
# .github/workflows/image-pipeline.yml
name: Image Generation Pipeline

on: [pull_request, workflow_dispatch]

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Part 1: Analyze
      - name: Analyze posts
        run: python3 scripts/batch_analyze_posts_for_image.py

      # Part 2: Generate
      - name: Generate images
        run: python3 scripts/batch_generate_images.py --backend dalle3
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # Part 3: Audit
      - name: Audit images
        run: python3 scripts/audit_generated_images.py --batch

      # Part 4: Remediate
      - name: Auto-remediate failures
        run: python3 scripts/auto_remediate_images.py --batch

      # Part 3: Gate
      - name: Compliance gate
        run: python3 scripts/image_compliance_gate.py --batch
        continue-on-error: true  # Allow review queue

      # Commit results
      - name: Commit images
        run: |
          git add static/images/posts/
          git commit -m "chore: regenerated hero images"
          git push

      # Create review queue
      - name: Create PR comment
        if: failure()
        run: |
          echo "🖼️  Image generation complete"
          echo "See reports/ for audit and remediation details"
```

## Thresholds

| Scenario | Action |
|----------|--------|
| Compliance ≥ 70%, Relevance ≥ 60% | ALLOW → Publish |
| Compliance 50-69% | REVIEW → Manual |
| Compliance < 50% | BLOCK → Don't publish |
| Relevance < 50% | BLOCK → Don't publish |

## Files

- `scripts/auto_remediate_images.py` — Automatic fixing (250 lines)
- `docs/AUTO_REMEDIATION_PART4.md` — This file

Depends on:
- Part 1: Content analysis
- Part 2: Image generation
- Part 3: Image audit & gate
