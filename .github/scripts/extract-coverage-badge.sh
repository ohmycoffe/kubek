#!/usr/bin/env bash
set -euo pipefail

coverage_file="${1:-coverage.json}"

if [[ ! -f "$coverage_file" ]]; then
  echo "Coverage file not found: $coverage_file" >&2
  exit 1
fi

percent="$(jq -r '(.totals.percent_covered + 0.5 | floor)' "$coverage_file")"

if (( percent >= 90 )); then
  color="brightgreen"
elif (( percent >= 80 )); then
  color="green"
elif (( percent >= 70 )); then
  color="yellow"
else
  color="red"
fi

echo "percent=$percent"
echo "color=$color"
