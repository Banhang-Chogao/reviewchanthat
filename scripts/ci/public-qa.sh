#!/usr/bin/env bash
# Post-build checks. They consume the one public/ tree produced by Hugo.
set -euo pipefail

test -s public/index.html
test -s public/404.html

log_dir=$(mktemp -d)
declare -a names=(internal-links sitemap)
declare -a pids=()

python3 scripts/qa_internal_links.py --public-dir public >"$log_dir/internal-links.log" 2>&1 &
pids+=("$!")
python3 scripts/qa_sitemap.py >"$log_dir/sitemap.log" 2>&1 &
pids+=("$!")

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
