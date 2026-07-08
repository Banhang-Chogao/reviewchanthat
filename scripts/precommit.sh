#!/usr/bin/env bash
set -euo pipefail

python3 scripts/compliance.py --strict --no-public
python3 scripts/qa_blog.py
hugo --minify