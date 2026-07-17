#!/usr/bin/env bash
# ============================================================
# nn — AUTONOMOUS: fetch source → rewrite → images → commit → push
#
# Usage (anywhere inside repo):
#   :nn <url> [slug]
#
# Ví dụ:
#   :nn https://example.com/bai-goc
#   :nn https://example.com/bai-goc slug-moi
#
# File này tracked trong repo — source từ .zshrc:
#   source "$(git rev-parse --show-toplevel)/scripts/nn.sh"
# ============================================================

nn() {
  local wd="${1:-$PWD}"
  cd "$wd" 2>/dev/null || { echo "Invalid dir: $wd"; return 1; }
  local repo
  repo=$(git rev-parse --show-toplevel 2>/dev/null)
  [ -z "$repo" ] && { echo "Not a git repo"; return 1; }
  cd "$repo" || { echo "Cannot cd to repo root"; return 1; }

  local source="$2" slug="$3"
  local source_path=".nn_source"
  local content=""

  # === 1. FETCH SOURCE ==========================================
  if echo "$source" | grep -qE '^https?://'; then
    echo ">>> Fetching $source ..."
    content=$(curl -sL "$source" 2>/dev/null || wget -qO- "$source" 2>/dev/null)
    [ -z "$content" ] && { echo "FAILED: fetch URL"; return 1; }
    echo "$source" > "$source_path"
    echo "---CONTENT---" >> "$source_path"
    echo "$content" >> "$source_path"
    echo ">>> Saved source ($(wc -c < "$source_path") bytes)"
  elif [ -n "$source" ]; then
    echo ">>> Using text source"
    echo "text" > "$source_path"
    echo "$source" >> "$source_path"
  else
    echo "Usage: :nn <url> [slug]"
    return 1
  fi

  # === 2. PICK CATEGORY (ít bài nhất) ===========================
  local cats=("review" "du-lich" "doi-song" "tai-chinh" "cong-nghe")
  local counts=()
  for c in "${cats[@]}"; do
    counts+=($(grep -c "categories.*=.*\[\"$c\"\]" content/posts/*.md 2>/dev/null))
  done
  local min_idx=0 min_val=${counts[0]}
  for i in {1..4}; do
    [ "${counts[$i]}" -lt "$min_val" ] 2>/dev/null && min_val=${counts[$i]} && min_idx=$i
  done
  local cat=${cats[$min_idx]}

  # === 3. GENERATE SLUG ==========================================
  [ -z "$slug" ] && slug="nn-$(date +%s)"
  local path="content/posts/$slug.md"
  [ -f "$path" ] && { echo "File exists: $path"; return 1; }

  # === 4. CREATE SKELETON =======================================
  {
    echo "+++"
    echo "title = \"(will be rewritten by opencode)\""
    echo "seo_title = \"(will be rewritten by opencode)\""
    echo "commit = \"\""
    echo "date = \"$(date -u +"%Y-%m-%dT%H:%M:%S+07:00")\""
    echo "slug = \"$slug\""
    echo "draft = false"
    echo "categories = [\"$cat\"]"
    echo "tags = []"
    echo "description = \"(will be rewritten by opencode)\""
    echo "author = \"Reviewchanthat\""
    echo "date_display = \"$(date -u +"%d-%m-%Y %H:%M:%S GMT +7")\""
    echo "image = \"\""
    echo "thumbnail = \"\""
    echo "+++"
  } > "$path"

  echo ""
  echo "╔═══════════════════════════════════════════╗"
  echo "║  :nn — AUTO PIPELINE                      ║"
  echo "╚═══════════════════════════════════════════╝"
  echo "  Source : $source"
  echo "  File   : $path"
  echo "  Cat    : $cat (ít bài nhất)"
  echo "  Ref    : $source_path"
  echo ""
}
alias ':nn'='nn'
