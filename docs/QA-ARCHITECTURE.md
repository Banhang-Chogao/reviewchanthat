# QA & Compliance Architecture

## Overview

This document describes the multi-tier QA system that allows new feature deployments without being blocked by existing content debt.

## Core Principle

**Strict on Changed, Lenient on Unchanged**

- **Changed files**: Full compliance enforcement (new regressions prevented)
- **Unchanged files**: Baseline debt accepted (old issues not blocking)

## Components

### 1. QA Scope Detection (`scripts/qa_scope.py`)

Detects which posts changed between base and head branches.

```bash
# Auto-detect GitHub PR context
python scripts/qa_scope.py --github-pr --out reports/qa-scope.json

# Custom branch comparison
python scripts/qa_scope.py --base origin/main --head HEAD --out reports/qa-scope.json
```

**Output**: `reports/qa-scope.json`
```json
{
  "changed_files": ["content/posts/new-post.md"],
  "changed_posts": ["new-post"],
  "unchanged_posts": ["old-post", "another-old"],
  "scope_mode": "changed-only",
  "total_posts": 42,
  "message": "Check 1 changed posts + 42 total"
}
```

### 2. Compliance Checker (`scripts/compliance.py`)

Scans posts for rule violations.

```bash
# Check all posts (default)
python scripts/compliance.py --strict

# Check only changed posts (PR mode)
python scripts/compliance.py --strict --changed-files-only --qa-scope reports/qa-scope.json

# Fix issues and apply safe corrections
python scripts/compliance.py --fix
```

**Mode Filtering**:
- If `--changed-files-only` is set and `only_posts` is populated, only those posts are scanned
- `discover_posts()` filters the post list based on `only_posts` set

### 3. Baseline Debt Registry (`data/qa-baseline-debt.json`)

Documents known issues in old content that don't block new deploys.

```json
{
  "known_issues": {
    "VERIFIED_WITHOUT_CREATOR": {
      "affected_posts": ["bangkok-3-ngay-3-dem-mua-mua", ...],
      "status": "acceptable",
      "auto_fix": false
    },
    "MISSING_IMAGE_METADATA": {
      "affected_posts": ["new-iphone-post", ...],
      "status": "in-progress",
      "auto_fix": true
    }
  },
  "rules": {
    "VERIFIED_WITHOUT_CREATOR": {
      "new_rule": "OK if source+license verified (creator not available from API)"
    }
  }
}
```

### 4. Debt Fix Workflow (`.github/workflows/qa-debt-fix.yml`)

Scheduled automation to resolve baseline debt.

```yaml
on:
  schedule:
    - cron: "0 9 * * 1"  # Every Monday 9 AM UTC
  workflow_dispatch:
    inputs:
      limit: "5"  # Max issues to fix
```

**Features**:
- Auto-detects auto-fixable issues from baseline debt
- Creates fix PR with compliance corrections
- Gradual debt reduction without blocking feature work

## Workflow Integration

### PR Check Workflow

```yaml
- name: Detect changed files for QA scope
  run: python scripts/qa_scope.py --github-pr --out reports/qa-scope.json

- name: Content compliance (changed files only)
  run: python scripts/compliance.py --strict --no-public \
    --changed-files-only --qa-scope reports/qa-scope.json \
    --report-json data/compliance-report.json
```

**Result**: PR only checks changed posts, no blocking on old content

### Debt Fix Workflow

Runs weekly to create PR for auto-fixable issues.

**Result**: Gradual debt reduction with separate PRs

## Compliance Rules

### VERIFIED_WITHOUT_CREATOR (Softened)

**Old Rule**: ERROR if `image_attribution_verified=true` but `image_creator` empty

**New Rule**: OK if `image_source` + `image_license` verified (creator may not be available from API)

**Applies to**:
- Thai travel guides (12 posts) - API cannot resolve creators
- Recently added posts (5 posts) - scheduled for image sourcing

## Usage Examples

### As a Developer

```bash
# Check your changes before push
python scripts/qa_scope.py --base origin/main --head HEAD
python scripts/compliance.py --strict --changed-files-only

# Fix auto-fixable issues
python scripts/compliance.py --fix

# Full scan (with warnings downgraded)
python scripts/compliance.py
```

### As a QA Engineer

```bash
# Monitor new content
python scripts/qa_scope.py --github-pr
python scripts/compliance.py --strict --changed-files-only \
  --qa-scope reports/qa-scope.json

# Check baseline debt status
cat data/qa-baseline-debt.json

# Create debt-fix PR manually
python scripts/compliance.py --fix
# Then commit and push as PR
```

### As DevOps/Release Manager

```bash
# Deploy with QA gate (automatic in workflow)
# .github/workflows/pr-check.yml integrates QA automatically

# Monitor debt reduction
# qa-debt-fix.yml runs weekly and creates PRs

# Disable changed-files-only mode for full audit
python scripts/compliance.py --strict --report-json audit.json
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Only check changed files in PR | Prevent new regressions while allowing old debt |
| Separate debt-fix workflow | Debt reduction doesn't interfere with feature work |
| Creator field optional if source verified | APIs often can't resolve creator, so verify alternative |
| Baseline debt as JSON registry | Clear audit trail, easy to update as debt resolves |
| Auto-fixable subset in debt | Some issues can be fixed programmatically |

## Monitoring & Metrics

Track in `data/qa-baseline-debt.json`:
- `total_debt_items`: Count of known issues
- `blocking_issues`: Issues that would fail strict mode
- `non_blocking_issues`: Accepted debt
- `auto_fixable`: Issues scheduled for resolution

## Future Improvements

1. Dashboard to visualize debt over time
2. Per-post debt tracking (which post has which issues)
3. Auto-assign debt-fix PRs to content team
4. Gradual strictness increase (ratchet enforcement)
5. Machine learning to predict debt categories
