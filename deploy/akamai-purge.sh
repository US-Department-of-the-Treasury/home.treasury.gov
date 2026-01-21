#!/bin/bash
#
# Purge Akamai cache after deployment
# Requires: Akamai CLI with purge module installed
#
# Usage:
#   ./deploy/akamai-purge.sh                        # Purge entire site
#   ./deploy/akamai-purge.sh /news/press-releases/  # Purge specific path
#   ./deploy/akamai-purge.sh --assets               # Purge CSS/JS/images
#   ./deploy/akamai-purge.sh --news                 # Purge all news content
#   ./deploy/akamai-purge.sh --staging              # Purge staging network
#
# Setup:
#   1. Install Akamai CLI: https://developer.akamai.com/cli
#   2. Install purge module: akamai install purge
#   3. Configure credentials: akamai config
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration from config.env if it exists
if [[ -f "$SCRIPT_DIR/config.env" ]]; then
  source "$SCRIPT_DIR/config.env"
fi

# Configuration - set in deploy/config.env (copy from config.env.example)
AKAMAI_NETWORK="${AKAMAI_NETWORK:-production}"
HOSTNAME="${AKAMAI_HOSTNAME:-home.treasury.gov}"
PURGE_TYPE="all"
CUSTOM_PATHS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --staging)
      AKAMAI_NETWORK="staging"
      shift
      ;;
    --assets)
      PURGE_TYPE="assets"
      shift
      ;;
    --news)
      PURGE_TYPE="news"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options] [paths...]"
      echo ""
      echo "Options:"
      echo "  --staging    Purge staging network instead of production"
      echo "  --assets     Purge CSS, JS, images, and fonts"
      echo "  --news       Purge all news content"
      echo "  [paths...]   Specific paths to purge (e.g., /news/press-releases/)"
      echo ""
      echo "Examples:"
      echo "  $0                              # Full site purge"
      echo "  $0 /about/                      # Purge about section"
      echo "  $0 --assets                     # Purge static assets"
      echo "  $0 --news --staging             # Purge news on staging"
      exit 0
      ;;
    /*)
      CUSTOM_PATHS+=("$1")
      PURGE_TYPE="custom"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run $0 --help for usage"
      exit 1
      ;;
  esac
done

echo "🔄 Akamai Cache Purge"
echo "   Hostname: $HOSTNAME"
echo "   Network:  $AKAMAI_NETWORK"
echo ""

# Check if Akamai CLI is available
if ! command -v akamai &> /dev/null; then
  echo "❌ Akamai CLI not found"
  echo "   Install from: https://developer.akamai.com/cli"
  exit 1
fi

# Check if purge module is installed
if ! akamai purge --version &> /dev/null; then
  echo "❌ Akamai purge module not installed"
  echo "   Run: akamai install purge"
  exit 1
fi

# Build URL list based on purge type
URLS=()

case "$PURGE_TYPE" in
  all)
    echo "   Type: Full site purge"
    # Purge by hostname (all URLs)
    akamai purge invalidate \
      --hostname "$HOSTNAME" \
      --network "$AKAMAI_NETWORK"
    echo ""
    echo "✅ Full site purge initiated"
    echo "   Note: Purge may take 5-10 minutes to propagate globally"
    exit 0
    ;;
  assets)
    echo "   Type: Static assets"
    URLS=(
      "https://${HOSTNAME}/css/*"
      "https://${HOSTNAME}/js/*"
      "https://${HOSTNAME}/images/*"
      "https://${HOSTNAME}/fonts/*"
    )
    ;;
  news)
    echo "   Type: News content"
    URLS=(
      "https://${HOSTNAME}/news/*"
      "https://${HOSTNAME}/news/press-releases/*"
      "https://${HOSTNAME}/news/statements-remarks/*"
      "https://${HOSTNAME}/news/testimonies/*"
      "https://${HOSTNAME}/news/readouts/*"
      "https://${HOSTNAME}/news/featured-stories/*"
    )
    ;;
  custom)
    echo "   Type: Custom paths"
    for path in "${CUSTOM_PATHS[@]}"; do
      URLS+=("https://${HOSTNAME}${path}")
    done
    ;;
esac

# Display URLs to purge
echo ""
echo "   URLs to purge:"
for url in "${URLS[@]}"; do
  echo "     - $url"
done
echo ""

# Execute purge
echo "   Executing purge..."
akamai purge invalidate \
  --urls "${URLS[@]}" \
  --network "$AKAMAI_NETWORK"

echo ""
echo "✅ Cache purge initiated for ${#URLS[@]} URL pattern(s)"
echo "   Note: Purge may take 5-10 minutes to propagate globally"
