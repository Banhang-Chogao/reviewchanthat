#!/usr/bin/env bash
# Run one CI command and emit a durable timing record to the Actions log/summary.
set -euo pipefail

label=${1:?timed.sh requires a label}
shift
start_epoch=$(date +%s)
start_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "::group::${label} (started ${start_iso})"
status=0
if "$@"; then
  status=0
else
  status=$?
fi
end_epoch=$(date +%s)
end_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
duration=$((end_epoch - start_epoch))
echo "${label}: ${duration}s (${start_iso} → ${end_iso})"
echo "::endgroup::"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf '| %s | %ss | %s → %s |\n' "$label" "$duration" "$start_iso" "$end_iso" >> "$GITHUB_STEP_SUMMARY"
fi

exit "$status"
