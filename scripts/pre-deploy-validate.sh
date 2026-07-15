#!/bin/bash
################################################################################
# PRE-DEPLOY VALIDATION GATEWAY
# ==============================
# The ultimate blocker to prevent ALL deployment failures.
# Run this BEFORE `git push origin main`
#
# Usage: bash scripts/pre-deploy-validate.sh [--fix]
################################################################################

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED=0
PASSED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PRE-DEPLOY VALIDATION GATEWAY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

# =============================================================================
# CHECK 1: Git Status
# =============================================================================
echo -e "${BLUE}[1/13] Git Status Check${NC}"
if git diff-index --quiet HEAD --; then
    pass "Working directory is clean"
else
    warn "Uncommitted changes exist - please commit before pushing"
fi

# =============================================================================
# CHECK 2: Branch is main
# =============================================================================
echo -e "\n${BLUE}[2/13] Branch Check${NC}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "main" ]; then
    pass "On main branch"
else
    fail "Not on main branch (current: $CURRENT_BRANCH) - checkout main first"
fi

# =============================================================================
# CHECK 3: Deploy Failure Scanner
# =============================================================================
echo -e "\n${BLUE}[3/13] Deploy Failure Scanner${NC}"
if python3 scripts/deploy-failure-healer.py --scan 2>/dev/null | grep -q "No deployment issues"; then
    pass "No deployment issues detected"
else
    if [ "$1" == "--fix" ]; then
        info "Auto-fixing deployment issues..."
        python3 scripts/deploy-failure-healer.py --fix-all
        pass "Deployment issues auto-fixed"
    else
        fail "Deployment issues found - run with --fix to auto-heal"
    fi
fi

# =============================================================================
# CHECK 4: TOML Syntax Validation
# =============================================================================
echo -e "\n${BLUE}[4/13] TOML Syntax Check${NC}"
YAML_SYNTAX_COUNT=$(grep -r "commit:\|date:\|image:\|title:\|draft:" content/posts/*.md 2>/dev/null | wc -l)
if [ "$YAML_SYNTAX_COUNT" -eq 0 ]; then
    pass "No YAML syntax in TOML frontmatter"
else
    fail "Found $YAML_SYNTAX_COUNT YAML syntax errors - use = not :"
    grep -n "commit:\|date:\|image:" content/posts/*.md | head -3
fi

# =============================================================================
# CHECK 5: Commit Hash Coverage
# =============================================================================
echo -e "\n${BLUE}[5/13] Commit Hash Coverage${NC}"
TOTAL_POSTS=$(ls content/posts/*.md | wc -l)
POSTS_WITH_HASH=$(grep -l "^commit = " content/posts/*.md 2>/dev/null | wc -l)
if [ "$POSTS_WITH_HASH" -eq "$TOTAL_POSTS" ]; then
    pass "All $TOTAL_POSTS posts have commit hashes"
else
    warn "Only $POSTS_WITH_HASH/$TOTAL_POSTS posts have commit hashes"
    if [ "$1" == "--fix" ]; then
        # Prefer SCOPE_POSTS="content/posts/a.md content/posts/b.md" when set (fast).
        # Full-tree only as last resort (slow on ~400 posts).
        if [ -n "${SCOPE_POSTS:-}" ]; then
            info "Running add_commit_id.py (SCOPE_POSTS)..."
            post_args=()
            for p in $SCOPE_POSTS; do post_args+=(--post "$p"); done
            python3 scripts/add_commit_id.py "${post_args[@]}"
        else
            warn "SCOPE_POSTS unset → add_commit_id.py --all (slow). Export SCOPE_POSTS for scope-only."
            info "Running add_commit_id.py --all..."
            python3 scripts/add_commit_id.py --all
        fi
        pass "Commit hashes added"
    fi
fi

# =============================================================================
# CHECK 6: Date Format & Timezone
# =============================================================================
echo -e "\n${BLUE}[6/13] Date Format & Timezone Check${NC}"
if python3 scripts/qa_dates.py 2>/dev/null | grep -q "PASS"; then
    pass "All dates are valid ISO 8601 +07:00"
else
    fail "Date validation failed (incl. future dates)"
    if [ "$1" == "--fix" ]; then
        info "Auto-fixing date issues..."
        python3 scripts/qa_dates.py --fix-obvious
        # Re-verify — never claim fixed without confirming the gate now passes
        if python3 scripts/qa_dates.py 2>/dev/null | grep -q "PASS"; then
            pass "Date issues fixed"
        else
            fail "Date issues remain after auto-fix — fix manually before deploy"
            python3 scripts/qa_dates.py 2>&1 | grep -i "future\|FAIL" | head -5
        fi
    fi
fi

# =============================================================================
# CHECK 7: TOML Frontmatter Validation
# =============================================================================
echo -e "\n${BLUE}[7/13] TOML Frontmatter & Rule Check${NC}"
if python3 scripts/rule.py --fix 2>/dev/null | grep -q "PASS"; then
    pass "TOML frontmatter is valid"
else
    fail "TOML validation failed"
fi

# =============================================================================
# CHECK 8: Image Coverage
# =============================================================================
echo -e "\n${BLUE}[8/13] Hero Image Coverage${NC}"
POSTS_WITHOUT_IMAGE=$(grep -L "image = " content/posts/*.md 2>/dev/null | wc -l)
if [ "$POSTS_WITHOUT_IMAGE" -eq 0 ]; then
    pass "All posts have hero images"
else
    fail "$POSTS_WITHOUT_IMAGE posts are missing hero images"
fi

# =============================================================================
# CHECK 9: WebP Image Tracking
# =============================================================================
echo -e "\n${BLUE}[9/13] WebP Image Tracking${NC}"
WEBP_FILES=$(find static/images/posts/ -name "*.webp" 2>/dev/null | wc -l)
TRACKED_WEBP=$(git ls-files static/images/posts/*.webp 2>/dev/null | wc -l)
if [ "$WEBP_FILES" -eq "$TRACKED_WEBP" ]; then
    pass "All $WEBP_FILES WebP images are tracked"
else
    warn "$WEBP_FILES WebP files exist but only $TRACKED_WEBP are tracked"
    if [ "$1" == "--fix" ]; then
        info "Force-adding untracked WebP files..."
        git add -f static/images/posts/*.webp
        pass "WebP images force-added"
    fi
fi

# =============================================================================
# CHECK 10: Fake Links Detection
# =============================================================================
echo -e "\n${BLUE}[10/13] Fake Internal Links Check${NC}"
FAKE_LINKS=$(grep -r "/posts/placeholder-" content/posts/ 2>/dev/null | wc -l)
if [ "$FAKE_LINKS" -eq 0 ]; then
    pass "No fake placeholder links found"
else
    fail "Found $FAKE_LINKS fake internal links"
fi

# =============================================================================
# CHECK 11: IMAGE_API_QUERY Markers
# =============================================================================
echo -e "\n${BLUE}[11/13] Dead Marker Detection${NC}"
IMAGE_MARKERS=$(grep -r "!\[\[IMAGE_API_QUERY:" content/posts/ 2>/dev/null | wc -l)
if [ "$IMAGE_MARKERS" -eq 0 ]; then
    pass "No dead IMAGE_API_QUERY markers"
else
    fail "Found $IMAGE_MARKERS IMAGE_API_QUERY markers - must be removed"
fi

# =============================================================================
# CHECK 12: Content Depth
# =============================================================================
echo -e "\n${BLUE}[12/13] Content Depth Check${NC}"
LOW_CONTENT=$(find content/posts -name "*.md" -exec sh -c 'wc=$(($(tail -n +29 "$1" 2>/dev/null | wc -w))); if [ "$wc" -lt 3000 ]; then echo "$1"; fi' _ {} \; 2>/dev/null | wc -l)
if [ "$LOW_CONTENT" -eq 0 ]; then
    pass "All posts meet 3000+ word requirement"
else
    warn "$LOW_CONTENT posts have less than 3000 words"
fi

# =============================================================================
# CHECK 13: Conflict Status
# =============================================================================
echo -e "\n${BLUE}[13/13] Merge Conflict Check${NC}"
CONFLICTS=$(git diff --name-only --diff-filter=U 2>/dev/null | wc -l)
if [ "$CONFLICTS" -eq 0 ]; then
    pass "No merge conflicts"
else
    fail "Found $CONFLICTS file(s) with merge conflicts"
    if [ "$1" == "--fix" ]; then
        info "Running conflict resolver..."
        python3 scripts/conflict-resolver.py --auto-resolve
        pass "Conflicts auto-resolved"
    fi
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  VALIDATION SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

TOTAL=$((PASSED + FAILED + WARNINGS))
PASS_RATE=$((PASSED * 100 / TOTAL))

echo -e "  ${GREEN}Passed:${NC}  $PASSED/$TOTAL"
echo -e "  ${RED}Failed:${NC}  $FAILED/$TOTAL"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS/$TOTAL"
echo -e "  ${BLUE}Pass Rate:${NC} $PASS_RATE%"

echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ALL CHECKS PASSED - SAFE TO DEPLOY!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Next step: ${BLUE}git push origin main${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ DEPLOYMENT BLOCKED - FIX ISSUES BEFORE PUSH${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Run with ${BLUE}--fix${NC} flag to auto-heal issues:"
    echo -e "  bash scripts/pre-deploy-validate.sh ${BLUE}--fix${NC}"
    exit 1
fi
