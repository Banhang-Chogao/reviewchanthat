#!/usr/bin/env bash
# Read-only release gates that can safely run in parallel after dependencies load.
set -euo pipefail

log_dir=$(mktemp -d)
declare -a names=(frontmatter dates summaries heroes inline)
declare -a pids=()

run_check() {
  local name=$1
  shift
  "$@" >"$log_dir/$name.log" 2>&1 &
  pids+=("$!")
}

run_check frontmatter python3 scripts/rule.py
run_check dates python3 scripts/qa_dates.py
run_check summaries python3 scripts/normalize_ai_summaries.py --check
run_check heroes python3 scripts/qa_hero_images.py
run_check inline python3 scripts/qa_inline_images.py

status=0
for index in "${!names[@]}"; do
  name=${names[$index]}
  if ! wait "${pids[$index]}"; then
    status=1
  fi
  echo "--- ${name} ---"
  sed -n '1,240p' "$log_dir/$name.log"
done

rm -rf "$log_dir"
exit "$status"
