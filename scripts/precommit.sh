#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Normalize AI summaries (check) ==="
python3 scripts/normalize_ai_summaries.py --check

echo "=== Hugo build ==="
hugo --minify

echo ""
echo "PASSED: precommit checks complete."