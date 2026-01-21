#!/bin/bash
#
# Akamai Migration Validation Script
# Validates Hugo site is correctly served through Akamai
#
# Usage:
#   ./deploy/validate-akamai.sh                    # Validate production
#   ./deploy/validate-akamai.sh staging            # Validate staging network
#   ./deploy/validate-akamai.sh --quick            # Quick smoke test only
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DOMAIN="home.treasury.gov"
STAGING_SUFFIX=".edgesuite-staging.net"

# Parse arguments
MODE="full"
NETWORK="production"

while [[ $# -gt 0 ]]; do
  case "$1" in
    staging)
      NETWORK="staging"
      shift
      ;;
    --quick)
      MODE="quick"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [staging] [--quick]"
      echo ""
      echo "Options:"
      echo "  staging    Test against Akamai staging network"
      echo "  --quick    Run quick smoke test only"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set target URL based on network
if [[ "$NETWORK" == "staging" ]]; then
  TARGET_HOST="${DOMAIN}${STAGING_SUFFIX}"
  CURL_OPTS="-H \"Host: ${DOMAIN}\""
else
  TARGET_HOST="${DOMAIN}"
  CURL_OPTS=""
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

log() { echo -e "[$(date '+%H:%M:%S')] $1"; }
pass() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; ((ERRORS++)); }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; ((WARNINGS++)); }

echo ""
echo "============================================"
echo " Akamai Migration Validation"
echo " Target: $TARGET_HOST"
echo " Network: $NETWORK"
echo " Mode: $MODE"
echo "============================================"
echo ""

# Helper function for curl with proper host header
do_curl() {
  local url="$1"
  local opts="${2:-}"
  if [[ "$NETWORK" == "staging" ]]; then
    curl -sI -H "Host: ${DOMAIN}" $opts "https://${TARGET_HOST}${url}"
  else
    curl -sI $opts "https://${TARGET_HOST}${url}"
  fi
}

do_curl_body() {
  local url="$1"
  if [[ "$NETWORK" == "staging" ]]; then
    curl -s -H "Host: ${DOMAIN}" "https://${TARGET_HOST}${url}"
  else
    curl -s "https://${TARGET_HOST}${url}"
  fi
}

# =============================================================================
# 1. DNS & Connectivity
# =============================================================================
log "1. DNS & Connectivity"

# DNS resolution
IP=$(dig +short $DOMAIN | head -1)
if [[ -n "$IP" ]]; then
  pass "DNS resolves: $DOMAIN → $IP"
else
  fail "DNS resolution failed for $DOMAIN"
fi

# Basic connectivity
STATUS=$(do_curl "/" | head -1 | awk '{print $2}')
if [[ "$STATUS" == "200" ]]; then
  pass "Homepage returns 200 OK"
else
  fail "Homepage returns $STATUS (expected 200)"
fi

# =============================================================================
# 2. Edge Network Verification
# =============================================================================
log "2. Edge Network Verification"

HEADERS=$(do_curl "/")

# Check for Akamai headers
if echo "$HEADERS" | grep -qiE "(X-Akamai|Akamai|edgekey)"; then
  pass "Akamai edge headers detected"
else
  warn "No Akamai headers detected (may be expected in some configs)"
fi

# Check X-Cache header
XCACHE=$(echo "$HEADERS" | grep -i "^X-Cache:" | head -1)
if [[ -n "$XCACHE" ]]; then
  pass "X-Cache: $XCACHE"
else
  warn "No X-Cache header found"
fi

# =============================================================================
# 3. Security Headers
# =============================================================================
log "3. Security Headers"

check_header() {
  local name="$1"
  local expected="$2"
  local value=$(echo "$HEADERS" | grep -i "^$name:" | head -1 | cut -d: -f2- | xargs)
  
  if [[ -z "$value" ]]; then
    fail "$name header missing"
  elif [[ -n "$expected" ]] && ! echo "$value" | grep -qi "$expected"; then
    warn "$name present but may not match expected value"
    echo "      Found: $value"
  else
    pass "$name: $value"
  fi
}

check_header "Strict-Transport-Security" "max-age"
check_header "X-Frame-Options" "DENY"
check_header "X-Content-Type-Options" "nosniff"
check_header "Content-Security-Policy" "default-src"

# =============================================================================
# 4. Critical Pages
# =============================================================================
log "4. Critical Pages"

CRITICAL_PAGES=(
  "/"
  "/news/press-releases/"
  "/about/"
  "/policy-issues/"
  "/services/"
)

for page in "${CRITICAL_PAGES[@]}"; do
  STATUS=$(do_curl "$page" | head -1 | awk '{print $2}')
  if [[ "$STATUS" == "200" ]]; then
    pass "$page → 200 OK"
  else
    fail "$page → $STATUS"
  fi
done

# Quick mode stops here
if [[ "$MODE" == "quick" ]]; then
  echo ""
  log "Quick validation complete."
  if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✅ All quick checks passed${NC}"
    exit 0
  else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    exit 1
  fi
fi

# =============================================================================
# 5. News Articles (Sample)
# =============================================================================
log "5. News Articles (Sample)"

# Get a sample article from the list page
SAMPLE_ARTICLES=$(do_curl_body "/news/press-releases/" | \
  grep -oP 'href="/news/press-releases/[^"]+/' | \
  head -5 | sed 's/href="//' | sed 's/"$//')

if [[ -z "$SAMPLE_ARTICLES" ]]; then
  warn "Could not extract sample articles from list page"
else
  for article in $SAMPLE_ARTICLES; do
    STATUS=$(do_curl "$article" | head -1 | awk '{print $2}')
    if [[ "$STATUS" == "200" ]]; then
      pass "$article → 200 OK"
    else
      fail "$article → $STATUS"
    fi
  done
fi

# =============================================================================
# 6. Static Assets
# =============================================================================
log "6. Static Assets"

# CSS
CSS_HEADERS=$(do_curl "/css/treasury.css")
CSS_STATUS=$(echo "$CSS_HEADERS" | head -1 | awk '{print $2}')
if [[ "$CSS_STATUS" == "200" ]]; then
  pass "/css/treasury.css → 200 OK"
  
  # Check cache headers
  CACHE_CONTROL=$(echo "$CSS_HEADERS" | grep -i "^cache-control:" | head -1)
  if echo "$CACHE_CONTROL" | grep -qi "max-age"; then
    pass "Cache-Control present: $CACHE_CONTROL"
  else
    warn "CSS missing Cache-Control header"
  fi
else
  fail "/css/treasury.css → $CSS_STATUS"
fi

# JavaScript
JS_STATUS=$(do_curl "/js/treasury.js" | head -1 | awk '{print $2}')
if [[ "$JS_STATUS" == "200" ]]; then
  pass "/js/treasury.js → 200 OK"
else
  fail "/js/treasury.js → $JS_STATUS"
fi

# Images
IMG_STATUS=$(do_curl "/images/treasury-seal.svg" | head -1 | awk '{print $2}')
if [[ "$IMG_STATUS" == "200" ]]; then
  pass "/images/treasury-seal.svg → 200 OK"
else
  fail "/images/treasury-seal.svg → $IMG_STATUS"
fi

# Fonts
FONT_STATUS=$(do_curl "/fonts/source-sans-pro-400.woff2" | head -1 | awk '{print $2}')
if [[ "$FONT_STATUS" == "200" ]]; then
  pass "/fonts/source-sans-pro-400.woff2 → 200 OK"
else
  fail "/fonts/source-sans-pro-400.woff2 → $FONT_STATUS"
fi

# =============================================================================
# 7. Compression
# =============================================================================
log "7. Compression"

ENCODING=$(do_curl "/" "-H 'Accept-Encoding: gzip, br'" | grep -i "^content-encoding:" | head -1)
if echo "$ENCODING" | grep -qiE "(gzip|br)"; then
  pass "Compression enabled: $ENCODING"
else
  warn "Compression may not be enabled (or already uncompressed)"
fi

# =============================================================================
# 8. 404 Handling
# =============================================================================
log "8. 404 Handling"

NOT_FOUND_STATUS=$(do_curl "/this-page-does-not-exist-xyz123/" | head -1 | awk '{print $2}')
if [[ "$NOT_FOUND_STATUS" == "404" ]]; then
  pass "Non-existent page returns 404"
  
  # Check if custom 404 page is served
  NOT_FOUND_BODY=$(do_curl_body "/this-page-does-not-exist-xyz123/" | head -50)
  if echo "$NOT_FOUND_BODY" | grep -qi "treasury"; then
    pass "Custom 404 page contains Treasury branding"
  else
    warn "404 page may not be the custom Hugo 404"
  fi
else
  warn "Non-existent page returns $NOT_FOUND_STATUS (expected 404)"
fi

# =============================================================================
# 9. Response Times
# =============================================================================
log "9. Response Times"

measure_time() {
  local url="$1"
  if [[ "$NETWORK" == "staging" ]]; then
    curl -so /dev/null -w "%{time_total}" -H "Host: ${DOMAIN}" "https://${TARGET_HOST}${url}"
  else
    curl -so /dev/null -w "%{time_total}" "https://${TARGET_HOST}${url}"
  fi
}

TIMES=()
for i in 1 2 3; do
  TIME=$(measure_time "/news/press-releases/")
  TIMES+=("$TIME")
done

# Calculate average (simple bash math)
TOTAL=0
for t in "${TIMES[@]}"; do
  TOTAL=$(echo "$TOTAL + $t" | bc)
done
AVG=$(echo "scale=3; $TOTAL / 3" | bc)

if (( $(echo "$AVG < 1.0" | bc -l) )); then
  pass "Average response time: ${AVG}s"
elif (( $(echo "$AVG < 2.0" | bc -l) )); then
  warn "Average response time: ${AVG}s (acceptable but could be better)"
else
  fail "Average response time: ${AVG}s (too slow)"
fi

# =============================================================================
# 10. Sitemap & RSS
# =============================================================================
log "10. Sitemap & RSS"

SITEMAP_STATUS=$(do_curl "/sitemap.xml" | head -1 | awk '{print $2}')
if [[ "$SITEMAP_STATUS" == "200" ]]; then
  pass "/sitemap.xml → 200 OK"
else
  warn "/sitemap.xml → $SITEMAP_STATUS"
fi

RSS_STATUS=$(do_curl "/news/press-releases/index.xml" | head -1 | awk '{print $2}')
if [[ "$RSS_STATUS" == "200" ]]; then
  pass "/news/press-releases/index.xml → 200 OK"
else
  warn "/news/press-releases/index.xml → $RSS_STATUS"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================"
echo " Validation Summary"
echo "============================================"
echo ""

if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
  echo -e "${GREEN}✅ All validations passed!${NC}"
  echo ""
  echo "The Hugo site is correctly configured and accessible via Akamai."
  exit 0
elif [[ $ERRORS -eq 0 ]]; then
  echo -e "${YELLOW}⚠️  Passed with $WARNINGS warning(s)${NC}"
  echo ""
  echo "Review warnings above. Site is functional but may need attention."
  exit 0
else
  echo -e "${RED}❌ $ERRORS error(s) and $WARNINGS warning(s)${NC}"
  echo ""
  echo "Critical issues found. Review errors above before proceeding."
  exit 1
fi
