#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Normalize image attribution (manifest/cache/posts) ==="
python3 scripts/fix_attribution.py

echo "=== Process images (sync frontmatter from manifest) ==="
python3 scripts/process_images.py

echo "=== Normalize AI summaries (check) ==="
python3 scripts/normalize_ai_summaries.py --check

echo "=== Content compliance (strict) ==="
python3 scripts/compliance.py --strict --no-public --report-json data/compliance-report.json

echo "=== QA blog ==="
python3 scripts/qa_blog.py

echo "=== Hugo build ==="
hugo --minify

echo ""
echo "PASSED: precommit checks complete."