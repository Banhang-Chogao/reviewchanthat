#!/bin/bash
# Auto-update version.toml with latest git commit
# Run before Hugo build

COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
COMMIT_FULL=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION_DATE=$(date -u +'%d-%m-%Y')

cat > data/version.toml << EOF
# Auto-generated at build time - do not edit manually
# Updated by CI/CD pipeline with latest commit hash
commit_short = "$COMMIT_SHORT"
commit_full = "$COMMIT_FULL"
build_date = "$BUILD_DATE"
version_date = "$VERSION_DATE"
EOF

echo "✅ Updated data/version.toml: $COMMIT_SHORT"
