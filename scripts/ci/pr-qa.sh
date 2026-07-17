#!/usr/bin/env bash
# Fast PR gate: validate only changed posts and workflow/config syntax.
set -euo pipefail

python scripts/qa_scope.py --base HEAD^ --head HEAD --out reports/qa-scope.json

python - <<'PY'
import glob
import yaml

for path in sorted(glob.glob('.github/workflows/*.yml')):
    with open(path, encoding='utf-8') as handle:
        yaml.safe_load(handle)
    print(f"workflow syntax OK: {path}")
PY

mapfile -t posts < <(python - <<'PY'
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

python scripts/rule.py "${post_args[@]}"
python scripts/qa_dates.py "${post_args[@]}"
python scripts/qa_blog.py --scope-report reports/qa-scope.json
python scripts/normalize_ai_summaries.py --check
python scripts/qa_inline_images.py
