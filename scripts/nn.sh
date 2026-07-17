#!/usr/bin/env bash
# ============================================================
# nn — News-to-New: lấy source từ URL/văn bản → viết lại bài
#         blog theo rule hệ thống (AGENTS.md), né vi phạm bản
#         quyền, tạo nết riêng cho bài mới.
#
# Usage (anywhere inside repo):
#   :nn <url|text> [slug] [title] [desc]
#
# Ví dụ:
#   :nn https://example.com/bai-goc slug-moi "Tựa đề" "Mô tả SEO"
#
# File này là SOURCE OF TRUTH — được source từ .zshrc qua:
#   source "$(git rev-parse --show-toplevel)/scripts/nn.sh"
# ============================================================


nn() {
  local wd="${1:-$PWD}"
  cd "$wd" 2>/dev/null || { echo "Invalid dir: $wd"; return 1; }
  if [ ! -f scripts/select_images.py ]; then
    # Try to find repo root
    local repo
    repo=$(git rev-parse --show-toplevel 2>/dev/null)
    [ -z "$repo" ] && { echo "Not a reviewchanthat repo"; return 1; }
    cd "$repo" || { echo "Cannot cd to repo root"; return 1; }
    [ ! -f scripts/select_images.py ] && { echo "Not reviewchanthat root"; return 1; }
  fi

  echo "╔═══════════════════════════════════════════╗"
  echo "║  :nn — Viết lại bài từ nguồn gốc         ║"
  echo "╚═══════════════════════════════════════════╝"
  echo ""

  local source="$2" slug="$3" title="$4" desc="$5"
  local is_url=0
  local source_path=".nn_source"

  # --- LẤY NGUỒN -------------------------------------------------
  if echo "$source" | grep -qE '^https?://'; then
    is_url=1
    echo ">>> Fetching source from URL: $source"
    local content
    content=$(curl -sL "$source" 2>/dev/null || wget -qO- "$source" 2>/dev/null)
    if [ -z "$content" ]; then
      echo "FAILED: Could not fetch URL."
      cd - >/dev/null; return 1
    fi
    echo "$source" > "$source_path"
    echo "---SOURCE CONTENT BELOW---" >> "$source_path"
    echo "$content" >> "$source_path"
    echo ">>> Saved source ($(wc -c < "$source_path") bytes)"
  elif [ -n "$source" ]; then
    echo ">>> Using provided text as source"
    echo "text" > "$source_path"
    echo "$source" >> "$source_path"
  else
    echo -n "Source URL: "
    read source
    if echo "$source" | grep -qE '^https?://'; then
      is_url=1
      local content
      content=$(curl -sL "$source" 2>/dev/null || wget -qO- "$source" 2>/dev/null)
      if [ -z "$content" ]; then
        echo "FAILED: Could not fetch URL."
        cd - >/dev/null; return 1
      fi
      echo "$source" > "$source_path"
      echo "---SOURCE CONTENT BELOW---" >> "$source_path"
      echo "$content" >> "$source_path"
    else
      echo "$source" > "$source_path"
    fi
    echo ">>> Saved source to $source_path"
  fi

  # --- CHỌN CATEGORY ÍT BÀI NHẤT ----------------------------------
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
  echo "  Category: $cat ($min_val bài hiện có)"

  # --- SLUG / TITLE / DESC ----------------------------------------
  local epoch=$EPOCHSECONDS
  if [ -z "$slug" ]; then
    if [ -t 0 ]; then
      echo -n "Slug (vd: bai-viet-moi): "
      read slug
    fi
    [ -z "$slug" ] && slug="bai-viet-$(strftime '%Y%m%d-%H%M%S' $epoch)"
  fi

  local path="content/posts/$slug.md"
  [ -f "$path" ] && { echo "File exists: $path"; cd - >/dev/null; return 1; }

  if [ -z "$title" ]; then
    if [ -t 0 ]; then
      echo -n "Title: "
      read title
    fi
    [ -z "$title" ] && title="Bài viết $(strftime '%d/%m/%Y' $epoch)"
  fi
  if [ -z "$desc" ]; then
    if [ -t 0 ]; then
      echo -n "Meta description (50-160 chars, SEO): "
      read desc
    fi
  fi
  [ -z "$desc" ] && desc="Bài viết tổng hợp và phân tích chi tiết — thông tin hữu ích, trải nghiệm thực tế, cập nhật $(strftime '%Y' $epoch)."

  local now=$(strftime "%Y-%m-%dT%H:%M:%S+07:00" $epoch)
  local now_display=$(strftime "%d-%m-%Y %H:%M:%S GMT +7" $epoch)

  # --- TẠO FILE BLOG ----------------------------------------------
  {
    echo "+++"
    echo "title = \"$title\""
    echo "seo_title = \"$title\""
    echo "commit = \"\""
    echo "date = \"$now\""
    echo "slug = \"$slug\""
    echo "draft = true"
    echo "categories = [\"$cat\"]"
    echo "tags = []"
    echo "description = \"$desc\""
    echo "author = \"Reviewchanthat\""
    echo "date_display = \"$now_display\""
    echo "image = \"\""
    echo "thumbnail = \"\""
    echo "+++"
    echo ""

    # Source reference comment — strictly for rewrite
    if [ $is_url -eq 1 ]; then
      echo "<!-- NN source URL: $source -->"
    fi
    echo "<!-- Source file: $source_path (delete after done) -->"
    echo ""
    echo "Viết ≥2000 từ, human-first, rewrite từ nguồn tham khảo. Không sao chép nguyên câu."
    echo "Viết lại với văn phong Review Chân Thật: chân thật, có trải nghiệm, có chiều sâu, không mùi AI."
    echo "Dùng nguồn để lấy ý + structure, diễn đạt lại hoàn toàn bằng lời văn riêng."
  } > "$path"

  echo ""
  echo "  ✅ File created: $path"
  echo "  📄 Source saved: $source_path"
  echo ""
  echo "  → Mở editor và rewrite (≥2000 từ)"
  echo "  → Sau khi viết xong chạy:"
  echo "    source .env && python3 scripts/select_images.py --post $path --fix"
  echo "    python3 scripts/add_commit_id.py --post $path"
  echo "    rm -f $source_path"
  echo ""

  local ans="n"
  if [ -t 0 ]; then
    echo -n "Mở editor ngay? (y/N): "
    read ans
  fi
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    ${EDITOR:-vim} "$path"
    echo ""
    echo "  Đã viết xong! Chạy pipeline..."
    cd "$wd"
    source .env 2>/dev/null
    python3 scripts/select_images.py --post "$path" --fix 2>&1 | tail -5
    python3 scripts/add_commit_id.py --post "$path" 2>&1 | tail -2
    rm -f "$source_path"
    echo "  → ':audit' rồi ':commit' để deploy"
  fi

  cd - >/dev/null 2>&1 || true
}

alias ':nn'='nn'
