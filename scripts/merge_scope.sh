#!/usr/bin/env bash
# merge_scope.sh — SCOPE-ONLY pre-merge / pre-push gate
#
# Chỉ chạy script Python trên post trong scope thay đổi.
# Không quét toàn bộ content/posts/ (~400 bài).
#
# Usage:
#   bash scripts/merge_scope.sh              # check only vs origin/main
#   bash scripts/merge_scope.sh --fix        # check + safe autofix scope
#   bash scripts/merge_scope.sh --merge      # check then merge branch → main
#   bash scripts/merge_scope.sh --base origin/main --head HEAD
#   SCOPE_POSTS="content/posts/a.md ..." bash scripts/merge_scope.sh
#   :merge-scope   (zsh alias)
#
# Exit: 0 = pass, non-zero = fail

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASE="${MERGE_SCOPE_BASE:-origin/main}"
HEAD="${MERGE_SCOPE_HEAD:-HEAD}"
DO_FIX=0
DO_MERGE=0
EXTRA_POSTS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --fix) DO_FIX=1; shift ;;
    --merge) DO_MERGE=1; shift ;;
    --base) BASE="$2"; shift 2 ;;
    --head) HEAD="$2"; shift 2 ;;
    --post) EXTRA_POSTS="$EXTRA_POSTS $2"; shift 2 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

echo "╔═══════════════════════════════════════════╗"
echo "║  merge-scope — SCOPE-ONLY py checks       ║"
echo "╚═══════════════════════════════════════════╝"
echo "  base=$BASE  head=$HEAD  fix=$DO_FIX  merge=$DO_MERGE"
echo ""

if ! git rev-parse --verify "$BASE" >/dev/null 2>&1; then
  echo ">>> Fetching origin..."
  git fetch origin main 2>/dev/null || true
fi

# Collect unique content/posts/*.md paths into POSTS_FILE
POSTS_FILE="$(mktemp)"
{
  if git rev-parse --verify "$BASE" >/dev/null 2>&1; then
    git diff --name-only "${BASE}...${HEAD}" -- content/posts/ 2>/dev/null || true
  fi
  git diff --name-only -- content/posts/ 2>/dev/null || true
  git diff --name-only --cached -- content/posts/ 2>/dev/null || true
  git ls-files --others --exclude-standard -- content/posts/ 2>/dev/null || true
  if [ -n "${SCOPE_POSTS:-}" ]; then
    # shellcheck disable=SC2086
    for p in $SCOPE_POSTS; do echo "$p"; done
  fi
  if [ -n "$EXTRA_POSTS" ]; then
    for p in $EXTRA_POSTS; do echo "$p"; done
  fi
} | grep -E '^content/posts/[^/]+\.md$' | sort -u | while read -r p; do
  [ -f "$p" ] && echo "$p"
done > "$POSTS_FILE"

POST_COUNT=$(wc -l < "$POSTS_FILE" | tr -d ' ')

if [ "$POST_COUNT" -eq 0 ]; then
  rm -f "$POSTS_FILE"
  echo ">>> No content/posts/*.md in scope."
  echo "    (Non-post changes only — skip post py scripts.)"
  if [ "$DO_MERGE" -eq 1 ]; then
    branch="$(git rev-parse --abbrev-ref HEAD)"
    if [ "$branch" = "main" ]; then
      echo ">>> On main — nothing to merge."
      exit 0
    fi
    echo ">>> Merging $branch → main (no post scope)..."
    git fetch origin main
    git checkout main
    git pull --ff-only origin main
    git merge --no-ff "$branch" -m "merge: $branch (scope: no posts)"
    echo ">>> OK. Review then: git push origin main"
  fi
  exit 0
fi

echo ">>> Scope posts ($POST_COUNT):"
sed 's/^/    - /' "$POSTS_FILE"
echo ""

# Build args arrays as newline-safe via temp files
POST_ARGS_FILE="$(mktemp)"
SLUG_ARGS_FILE="$(mktemp)"
while read -r p; do
  printf -- '--post\n%s\n' "$p" >> "$POST_ARGS_FILE"
  slug="$(basename "$p" .md)"
  printf -- '--slug\n%s\n' "$slug" >> "$SLUG_ARGS_FILE"
done < "$POSTS_FILE"

export SCOPE_POSTS
SCOPE_POSTS="$(tr '\n' ' ' < "$POSTS_FILE")"

run_step() {
  title="$1"
  shift
  echo ">>> $title"
  echo "    $*"
  if "$@"; then
    echo "    ✅ OK"
    echo ""
    return 0
  else
    echo "    ❌ FAIL: $title" >&2
    echo ""
    return 1
  fi
}

# Read args into "$@" via xargs-safe: use bash arrays if bash 4+, else eval carefully
# Portable: build command line with while read
run_with_post_args() {
  title="$1"
  shift
  # remaining: command prefix; post args from file
  cmd_prefix="$*"
  echo ">>> $title"
  # shellcheck disable=SC2046
  set -- $cmd_prefix
  while read -r a; do
    set -- "$@" "$a"
  done < "$POST_ARGS_FILE"
  echo "    $*"
  if "$@"; then
    echo "    ✅ OK"
    echo ""
    return 0
  fi
  echo "    ❌ FAIL: $title" >&2
  echo ""
  return 1
}

run_with_slug_args() {
  title="$1"
  shift
  cmd_prefix="$*"
  echo ">>> $title"
  set -- $cmd_prefix
  while read -r a; do
    set -- "$@" "$a"
  done < "$SLUG_ARGS_FILE"
  echo "    $*"
  if "$@"; then
    echo "    ✅ OK"
    echo ""
    return 0
  fi
  echo "    ❌ FAIL: $title" >&2
  echo ""
  return 1
}

FAIL=0

# 1. Healer
while read -r p; do
  if [ "$DO_FIX" -eq 1 ]; then
    run_step "deploy-failure-healer --fix-all --post $p" \
      python3 scripts/deploy-failure-healer.py --fix-all --post "$p" || FAIL=1
  else
    # scan may print issues without failing hard
    run_step "deploy-failure-healer --scan --post $p" \
      python3 scripts/deploy-failure-healer.py --scan --post "$p" || true
  fi
done < "$POSTS_FILE"

# 2. Dates
if [ "$DO_FIX" -eq 1 ]; then
  run_with_post_args "qa_dates --fix-obvious (scope)" \
    python3 scripts/qa_dates.py --fix-obvious || FAIL=1
fi
run_with_post_args "qa_dates (scope)" \
  python3 scripts/qa_dates.py || FAIL=1

# 3. rule.py
if [ "$DO_FIX" -eq 1 ]; then
  run_with_post_args "rule.py --fix (scope)" \
    python3 scripts/rule.py --fix || FAIL=1
else
  run_with_post_args "rule.py (scope)" \
    python3 scripts/rule.py || FAIL=1
fi

# 4. commit ids
run_with_post_args "add_commit_id (scope)" \
  python3 scripts/add_commit_id.py || true

# 5. internal links
if [ "$DO_FIX" -eq 1 ]; then
  run_with_post_args "strip_unused_internal_links --write (scope)" \
    python3 scripts/strip_unused_internal_links.py --write || true
else
  run_with_post_args "strip_unused_internal_links --dry-run (scope)" \
    python3 scripts/strip_unused_internal_links.py --dry-run || true
fi

# 6. hardcoded footer
while read -r p; do
  if [ "$DO_FIX" -eq 1 ]; then
    run_step "move_hardcoded_footer --fix --post $p" \
      python3 scripts/move_hardcoded_footer_sections.py --fix --post "$p" || true
  else
    python3 scripts/move_hardcoded_footer_sections.py --post "$p" || true
  fi
done < "$POSTS_FILE"

# 7. process images
if [ "$DO_FIX" -eq 1 ]; then
  run_with_slug_args "process_images (scope slugs)" \
    python3 scripts/process_images.py || true
fi

# 8. inline hook
run_step "qa_inline_images" python3 scripts/qa_inline_images.py || true

# 9. markers / commit field on scope only
echo ">>> Grep markers (scope only)"
fail_markers=0
while read -r p; do
  if grep -n 'IMAGE_API_QUERY\|/posts/placeholder-' "$p" >/dev/null 2>&1; then
    echo "    ⚠ $p has IMAGE_API_QUERY or placeholder links"
    grep -n 'IMAGE_API_QUERY\|/posts/placeholder-' "$p" || true
    fail_markers=1
  fi
  if grep -E '^(commit|date|image):' "$p" >/dev/null 2>&1; then
    echo "    ⚠ $p has YAML-style keys in front matter"
    grep -nE '^(commit|date|image):' "$p" || true
    fail_markers=1
  fi
  if grep -q '^commit = ""' "$p" 2>/dev/null || ! grep -q '^commit = "' "$p" 2>/dev/null; then
    echo "    ⚠ $p missing/empty commit id"
    fail_markers=1
  fi
done < "$POSTS_FILE"

if [ "$fail_markers" -eq 1 ]; then
  echo "    ❌ marker/commit check failed" >&2
  FAIL=1
else
  echo "    ✅ OK"
fi
echo ""

rm -f "$POSTS_FILE" "$POST_ARGS_FILE" "$SLUG_ARGS_FILE"

if [ "$FAIL" -ne 0 ]; then
  echo "=== SCOPE CHECK FAILED ===" >&2
  exit 1
fi

echo "=== SCOPE CHECK PASS ($POST_COUNT post(s)) ==="

if [ "$DO_MERGE" -eq 1 ]; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$branch" = "main" ]; then
    echo ">>> On main — scope OK. Push: git push origin main"
    exit 0
  fi
  echo ">>> Merging $branch → main..."
  git fetch origin main
  git checkout main
  git pull --ff-only origin main
  git merge --no-ff "$branch" -m "merge: $branch (scope-only pre-check passed)"
  echo ">>> Merged. Next: git push origin main  (FIFO ≥30s if another deploy just ran)"
fi

exit 0
