#!/usr/bin/env bash
# Full Section 508 / WCAG automated scan for ALL pages in sitemap.xml.
#
# Usage:
#   ./scripts/test_508_all_pages.sh
#   ./scripts/test_508_all_pages.sh --base-url http://localhost:1313 --concurrency 6
#   ./scripts/test_508_all_pages.sh --max-urls 200   # quick smoke test
#
# Notes:
# - Uses `npx` with a temporary npm cache (no global installs).
# - Scanning all sitemap URLs is long-running.

set -euo pipefail

BASE_URL="http://localhost:1313"
CONCURRENCY="6"
MAX_URLS=""

usage() {
  cat <<'EOF'
Usage: ./scripts/test_508_all_pages.sh [options]

Options:
  --base-url URL        Base URL to test (default: http://localhost:1313)
  --concurrency N       pa11y-ci concurrency (default: 6)
  --max-urls N          Limit number of URLs scanned (default: no limit)
  -h, --help            Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="${2:-}"; shift 2 ;;
    --concurrency) CONCURRENCY="${2:-}"; shift 2 ;;
    --max-urls) MAX_URLS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required." >&2
  exit 2
fi

SITEMAP_URL="${BASE_URL%/}/sitemap.xml"
echo "Fetching sitemap: ${SITEMAP_URL}"

URLS="$(curl -fsSL "$SITEMAP_URL" \
  | tr '\n' ' ' \
  | sed -E 's#</loc>#</loc>\n#g' \
  | sed -nE 's#.*<loc>([^<]+)</loc>.*#\1#p' \
  | grep -E "^${BASE_URL%/}/" \
  | sort -u)"

if [[ -z "$URLS" ]]; then
  echo "ERROR: No URLs found in sitemap. Is Hugo running at ${BASE_URL}?" >&2
  exit 1
fi

COUNT_TOTAL="$(printf "%s\n" "$URLS" | wc -l | tr -d ' ')"
echo "Found ${COUNT_TOTAL} URLs in sitemap."

if [[ -n "$MAX_URLS" ]]; then
  echo "Limiting to first ${MAX_URLS} URLs (smoke test)."
  # Avoid SIGPIPE under pipefail when head closes early.
  set +o pipefail
  URLS="$(printf "%s\n" "$URLS" | head -n "$MAX_URLS" || true)"
  set -o pipefail
fi

TMPDIR="$(mktemp -d /tmp/pa11y-all-pages.XXXXXX)"
CONFIG_FILE="${TMPDIR}/.pa11yci.all-pages.json"

NPM_CACHE_DIR="$(mktemp -d /tmp/pa11y-npm-cache.XXXXXX)"
trap 'rm -rf "$TMPDIR" "$NPM_CACHE_DIR"' EXIT

printf "%s\n" "$URLS" | python3 -c '
import json
import sys

config_file = sys.argv[1]
concurrency = int(sys.argv[2])
urls = [line.strip() for line in sys.stdin if line.strip()]

config = {
  "defaults": {
    "standard": "WCAG2AA",
    "timeout": 30000,
    "wait": 1000,
    "ignore": [
      "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail"
    ],
    "chromeLaunchConfig": {
      "args": ["--no-sandbox"]
    }
  },
  "concurrency": concurrency,
  "urls": urls
}

with open(config_file, "w", encoding="utf-8") as f:
  json.dump(config, f, indent=2)
  f.write("\n")
' "$CONFIG_FILE" "$CONCURRENCY"

echo "Running pa11y-ci with config: ${CONFIG_FILE}"
npm_config_cache="$NPM_CACHE_DIR" npx -y pa11y-ci --config "$CONFIG_FILE"
