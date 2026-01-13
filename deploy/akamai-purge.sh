#!/bin/bash
#
# Purge Akamai cache after deployment
# Requires: Akamai CLI with purge module installed
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

echo "🔄 Purging Akamai cache for $HOSTNAME"
echo "   Network: $AKAMAI_NETWORK"

# Check if Akamai CLI is available
if ! command -v akamai &> /dev/null; then
  echo "❌ Akamai CLI not found"
  echo "   Install from: https://developer.akamai.com/cli"
  exit 1
fi

# Full site purge
akamai purge invalidate \
  --hostname "$HOSTNAME" \
  --network "$AKAMAI_NETWORK"

echo "✅ Cache purge initiated"
echo "   Note: Purge may take a few minutes to propagate globally"
