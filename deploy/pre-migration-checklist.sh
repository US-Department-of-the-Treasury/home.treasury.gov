#!/bin/bash
#
# Pre-Migration Checklist for Akamai Cutover
# Run this script before initiating the migration
#
# Usage: ./deploy/pre-migration-checklist.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

log() { echo -e "\n${BLUE}▶ $1${NC}"; }
pass() { echo -e "  ${GREEN}✅ $1${NC}"; ((CHECKS_PASSED++)); }
fail() { echo -e "  ${RED}❌ $1${NC}"; ((CHECKS_FAILED++)); }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; ((CHECKS_WARNED++)); }
info() { echo -e "  ${BLUE}ℹ️  $1${NC}"; }

echo ""
echo "========================================================"
echo "  Treasury Hugo → Akamai Pre-Migration Checklist"
echo "========================================================"
echo "  Date: $(date)"
echo "========================================================"

# =============================================================================
# 1. Local Environment Checks
# =============================================================================
log "1. Local Environment"

# Hugo installed
if command -v hugo &> /dev/null; then
  HUGO_VERSION=$(hugo version | head -1)
  pass "Hugo installed: $HUGO_VERSION"
else
  fail "Hugo is not installed"
fi

# AWS CLI
if command -v aws &> /dev/null; then
  AWS_VERSION=$(aws --version 2>&1 | head -1)
  pass "AWS CLI installed: $AWS_VERSION"
else
  fail "AWS CLI is not installed"
fi

# Akamai CLI
if command -v akamai &> /dev/null; then
  AKAMAI_VERSION=$(akamai --version 2>&1 | head -1)
  pass "Akamai CLI installed: $AKAMAI_VERSION"
else
  fail "Akamai CLI is not installed"
  info "Install from: https://developer.akamai.com/cli"
fi

# jq for JSON parsing
if command -v jq &> /dev/null; then
  pass "jq installed"
else
  warn "jq not installed (optional but helpful)"
fi

# bc for calculations
if command -v bc &> /dev/null; then
  pass "bc installed"
else
  warn "bc not installed (needed for some validation scripts)"
fi

# =============================================================================
# 2. AWS Access
# =============================================================================
log "2. AWS Access"

# AWS credentials valid
if aws sts get-caller-identity &> /dev/null; then
  AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
  pass "AWS credentials valid (Account: $AWS_ACCOUNT)"
else
  fail "AWS credentials not valid or expired"
fi

# S3 bucket access
S3_BUCKET=$(aws ssm get-parameter --name "/treasury-home/prod/S3_BUCKET_NAME" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
if [[ -n "$S3_BUCKET" ]]; then
  pass "S3 bucket configured: $S3_BUCKET"
  
  # Can list bucket
  if aws s3 ls "s3://$S3_BUCKET/" --max-items 1 &> /dev/null; then
    pass "S3 bucket accessible"
  else
    fail "Cannot access S3 bucket"
  fi
else
  fail "S3 bucket name not found in SSM"
fi

# CloudFront distribution
CF_DIST=$(aws ssm get-parameter --name "/treasury-home/prod/CLOUDFRONT_DISTRIBUTION_ID" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
if [[ -n "$CF_DIST" ]]; then
  pass "CloudFront distribution: $CF_DIST"
else
  warn "CloudFront distribution ID not in SSM (may be expected if already migrated)"
fi

# =============================================================================
# 3. Akamai Access
# =============================================================================
log "3. Akamai Access"

# Check Akamai auth
if akamai auth 2>&1 | grep -q "authorized"; then
  pass "Akamai CLI authenticated"
else
  warn "Akamai CLI may not be authenticated"
  info "Run: akamai auth"
fi

# Check purge module
if akamai purge --version &> /dev/null; then
  pass "Akamai purge module installed"
else
  fail "Akamai purge module not installed"
  info "Run: akamai install purge"
fi

# =============================================================================
# 4. Hugo Site Build
# =============================================================================
log "4. Hugo Site Build"

cd "$PROJECT_ROOT"

# Can build site
if hugo --minify --gc &> /dev/null; then
  pass "Hugo build successful"
  
  # Count pages
  HTML_COUNT=$(find public -name "*.html" 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$HTML_COUNT" -gt 16000 ]]; then
    pass "Generated $HTML_COUNT HTML pages"
  else
    warn "Only $HTML_COUNT pages generated (expected 16,000+)"
  fi
else
  fail "Hugo build failed"
fi

# Check for critical files
CRITICAL_FILES=(
  "public/index.html"
  "public/news/press-releases/index.html"
  "public/about/index.html"
  "public/404.html"
  "public/sitemap.xml"
)

for file in "${CRITICAL_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    pass "$file exists"
  else
    fail "$file missing"
  fi
done

# =============================================================================
# 5. Current Site Status
# =============================================================================
log "5. Current Production Site"

DOMAIN="home.treasury.gov"

# DNS check
DNS_RESULT=$(dig +short $DOMAIN | head -1)
if [[ -n "$DNS_RESULT" ]]; then
  pass "DNS resolves: $DOMAIN → $DNS_RESULT"
else
  fail "DNS resolution failed"
fi

# Site responding
HTTP_STATUS=$(curl -sI "https://$DOMAIN/" | head -1 | awk '{print $2}')
if [[ "$HTTP_STATUS" == "200" ]]; then
  pass "Production site responding: 200 OK"
else
  fail "Production site returned: $HTTP_STATUS"
fi

# Check current CDN (CloudFront vs Akamai)
VIA_HEADER=$(curl -sI "https://$DOMAIN/" | grep -i "^Via:" | head -1)
if echo "$VIA_HEADER" | grep -qi "cloudfront"; then
  info "Currently served by CloudFront: $VIA_HEADER"
elif echo "$VIA_HEADER" | grep -qi "akamai"; then
  info "Already served by Akamai: $VIA_HEADER"
else
  info "Via header: $VIA_HEADER"
fi

# =============================================================================
# 6. Content Sync Status
# =============================================================================
log "6. Content Sync Status"

# Check git status
cd "$PROJECT_ROOT"
if [[ -z "$(git status --porcelain)" ]]; then
  pass "Git working directory clean"
else
  warn "Uncommitted changes in working directory"
  info "Run: git status"
fi

# Check branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" == "staging" ]] || [[ "$BRANCH" == "master" ]]; then
  pass "On branch: $BRANCH"
else
  warn "On branch: $BRANCH (expected staging or master)"
fi

# Check remote sync
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse origin/$BRANCH 2>/dev/null || echo "unknown")
if [[ "$LOCAL_SHA" == "$REMOTE_SHA" ]]; then
  pass "Local and remote in sync"
else
  warn "Local commits not pushed to origin/$BRANCH"
fi

# =============================================================================
# 7. Configuration Files
# =============================================================================
log "7. Configuration Files"

# deploy/config.env
if [[ -f "$SCRIPT_DIR/config.env" ]]; then
  pass "deploy/config.env exists"
  
  # Check required vars
  source "$SCRIPT_DIR/config.env"
  if [[ -n "${AKAMAI_HOSTNAME:-}" ]]; then
    pass "AKAMAI_HOSTNAME configured: $AKAMAI_HOSTNAME"
  else
    warn "AKAMAI_HOSTNAME not set in config.env"
  fi
else
  warn "deploy/config.env not found"
  info "Copy from config.env.example and configure"
fi

# Akamai caching rules
if [[ -f "$SCRIPT_DIR/akamai-caching-rules.json" ]]; then
  pass "akamai-caching-rules.json exists"
  
  # Validate JSON
  if jq empty "$SCRIPT_DIR/akamai-caching-rules.json" 2>/dev/null; then
    pass "akamai-caching-rules.json is valid JSON"
  else
    fail "akamai-caching-rules.json is invalid JSON"
  fi
else
  warn "akamai-caching-rules.json not found"
fi

# =============================================================================
# 8. Security Configuration
# =============================================================================
log "8. Security Configuration"

# Check CSP in terraform
if grep -q "Content-Security-Policy" "$PROJECT_ROOT/terraform/main.tf" 2>/dev/null; then
  pass "CSP defined in Terraform"
else
  warn "CSP not found in Terraform config"
fi

# Check for inline scripts (CSP violations)
INLINE_SCRIPTS=$(grep -r "<script>" "$PROJECT_ROOT/themes/" --include="*.html" 2>/dev/null | grep -v "src=" | grep -v "{{" | wc -l | tr -d ' ')
if [[ "$INLINE_SCRIPTS" -eq 0 ]]; then
  pass "No inline scripts found (CSP compliant)"
else
  fail "$INLINE_SCRIPTS inline script(s) found (CSP violation)"
fi

# Check for inline event handlers
INLINE_HANDLERS=$(grep -rE "on(click|load|submit|change|error)=" "$PROJECT_ROOT/themes/" --include="*.html" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$INLINE_HANDLERS" -eq 0 ]]; then
  pass "No inline event handlers found (CSP compliant)"
else
  fail "$INLINE_HANDLERS inline event handler(s) found (CSP violation)"
fi

# =============================================================================
# 9. DNS TTL Check
# =============================================================================
log "9. DNS TTL Check"

DNS_TTL=$(dig +nocmd +noall +answer $DOMAIN | awk '{print $2}' | head -1)
if [[ -n "$DNS_TTL" ]]; then
  if [[ "$DNS_TTL" -le 300 ]]; then
    pass "DNS TTL is low enough for quick cutover: ${DNS_TTL}s"
  else
    warn "DNS TTL is high: ${DNS_TTL}s (recommended: ≤300s before cutover)"
    info "Lower TTL 48 hours before migration"
  fi
else
  warn "Could not determine DNS TTL"
fi

# =============================================================================
# 10. Documentation
# =============================================================================
log "10. Documentation"

DOCS=(
  "docs/AKAMAI_MIGRATION_PLAYBOOK.md"
  "docs/AKAMAI_INTEGRATION.md"
  "docs/TESTING_INSTRUCTIONS.md"
)

for doc in "${DOCS[@]}"; do
  if [[ -f "$PROJECT_ROOT/$doc" ]]; then
    pass "$doc exists"
  else
    warn "$doc not found"
  fi
done

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "========================================================"
echo "  Pre-Migration Checklist Summary"
echo "========================================================"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $CHECKS_PASSED"
echo -e "  ${RED}Failed:${NC}  $CHECKS_FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $CHECKS_WARNED"
echo ""

if [[ $CHECKS_FAILED -eq 0 ]]; then
  echo -e "${GREEN}✅ Ready for migration!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Review any warnings above"
  echo "  2. Coordinate with CDN team on Akamai property configuration"
  echo "  3. Schedule migration window"
  echo "  4. Run: ./deploy/validate-akamai.sh staging"
  exit 0
else
  echo -e "${RED}❌ Not ready for migration${NC}"
  echo ""
  echo "Please fix the $CHECKS_FAILED failed check(s) before proceeding."
  exit 1
fi
