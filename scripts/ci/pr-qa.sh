#!/usr/bin/env bash
# Fast PR gate: validate only changed posts and workflow/config syntax.
set -euo pipefail

python3 scripts/qa_scope.py --base HEAD^ --head HEAD --out reports/qa-scope.json

python3 - <<'PY'
import glob
import yaml

for path in sorted(glob.glob('.github/workflows/*.yml')):
    with open(path, encoding='utf-8') as handle:
        yaml.safe_load(handle)
    print(f"workflow syntax OK: {path}")
PY

posts=()
while IFS= read -r post; do
  posts+=("$post")
done < <(python3 - <<'PY'
import json

with open('reports/qa-scope.json', encoding='utf-8') as handle:
    for slug in json.load(handle).get('changed_posts', []):
        print(f'content/posts/{slug}.md')
PY
)

if ((${#posts[@]} == 0)); then
  echo 'No changed posts: post-specific QA skipped.'
  exit 0
fi

post_args=()
for post in "${posts[@]}"; do
  post_args+=(--post "$post")
done

python3 scripts/rule.py "${post_args[@]}"
python3 scripts/qa_dates.py "${post_args[@]}"
python3 scripts/qa_blog.py --scope-report reports/qa-scope.json
python3 scripts/normalize_ai_summaries.py --check
python3 scripts/qa_inline_images.py
