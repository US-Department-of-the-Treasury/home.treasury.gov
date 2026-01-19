#!/bin/bash
#
# Deploy Hugo site to AWS S3
# Usage: ./deploy/s3-sync.sh [environment]
#
# Environments:
#   staging  - Deploy to staging bucket
#   prod     - Deploy to production bucket (requires confirmation)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/public"

# Load configuration from config.env if it exists
if [[ -f "$SCRIPT_DIR/config.env" ]]; then
  source "$SCRIPT_DIR/config.env"
fi

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
SSM_PREFIX="${SSM_PREFIX:-/treasury-home}"

# Parse arguments
ENVIRONMENT="${1:-staging}"

# Fetch configuration from SSM (primary) or fall back to config.env
fetch_ssm_param() {
  local param_name="$1"
  local default_value="$2"
  local value
  value=$(aws ssm get-parameter --name "${SSM_PREFIX}/${ENVIRONMENT}/${param_name}" --query 'Parameter.Value' --output text 2>/dev/null || true)
  if [[ -n "$value" && "$value" != "None" ]]; then
    echo "$value"
  else
    echo "$default_value"
  fi
}

case "$ENVIRONMENT" in
  staging|prod|production)
    # Normalize production
    [[ "$ENVIRONMENT" == "production" ]] && ENVIRONMENT="prod"

    # Fetch bucket name from SSM
    S3_BUCKET=$(fetch_ssm_param "S3_BUCKET_NAME" "")

    if [[ -z "$S3_BUCKET" ]]; then
      echo "❌ Could not find S3 bucket name in SSM: ${SSM_PREFIX}/${ENVIRONMENT}/S3_BUCKET_NAME"
      exit 1
    fi

    if [[ "$ENVIRONMENT" == "prod" ]]; then
      echo "⚠️  You are about to deploy to PRODUCTION ($S3_BUCKET)"
      read -p "Are you sure? (yes/no): " CONFIRM
      if [[ "$CONFIRM" != "yes" ]]; then
        echo "Deployment cancelled."
        exit 0
      fi
    else
      echo "🚀 Deploying to STAGING ($S3_BUCKET)"
    fi
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT"
    echo "Usage: $0 [staging|prod]"
    exit 1
    ;;
esac

# Fetch site URL for Hugo baseURL
SITE_URL=$(fetch_ssm_param "SITE_URL" "")
if [[ -z "$SITE_URL" ]]; then
  echo "⚠️  No SITE_URL found in SSM, using default from hugo.toml"
  echo "   Set SSM parameter: ${SSM_PREFIX}/${ENVIRONMENT}/SITE_URL"
fi

# Build the site
echo "📦 Building Hugo site..."
cd "$PROJECT_ROOT"

if [[ -n "$SITE_URL" ]]; then
  echo "   Using baseURL: $SITE_URL"
  hugo --minify --gc --baseURL "$SITE_URL"
else
  hugo --minify --gc
fi

if [[ ! -d "$BUILD_DIR" ]]; then
  echo "❌ Build failed - no public directory found"
  exit 1
fi

# Count files
FILE_COUNT=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
echo "   Found $FILE_COUNT files to deploy"

# Sync to S3
echo "☁️  Syncing to S3..."

# HTML files - no cache (for immediate updates)
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET" \
  --region "$AWS_REGION" \
  --exclude "*" \
  --include "*.html" \
  --cache-control "max-age=0, no-cache, no-store, must-revalidate" \
  --content-type "text/html; charset=utf-8" \
  --delete

# CSS/JS - long cache with versioning (Hugo fingerprints these)
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET" \
  --region "$AWS_REGION" \
  --exclude "*" \
  --include "*.css" \
  --include "*.js" \
  --cache-control "max-age=31536000, immutable"

# Images - long cache
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET" \
  --region "$AWS_REGION" \
  --exclude "*" \
  --include "*.jpg" \
  --include "*.jpeg" \
  --include "*.png" \
  --include "*.gif" \
  --include "*.svg" \
  --include "*.webp" \
  --include "*.ico" \
  --cache-control "max-age=2592000"

# Documents - medium cache
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET" \
  --region "$AWS_REGION" \
  --exclude "*" \
  --include "*.pdf" \
  --include "*.doc" \
  --include "*.docx" \
  --include "*.xls" \
  --include "*.xlsx" \
  --cache-control "max-age=86400"

# Everything else
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET" \
  --region "$AWS_REGION" \
  --cache-control "max-age=3600" \
  --delete

# Invalidate CloudFront cache (required for every deploy)
# Fetch distribution ID from SSM if not set
if [[ -z "$CLOUDFRONT_DISTRIBUTION_ID" ]]; then
  SSM_PATH="/treasury-home/${ENVIRONMENT}/CLOUDFRONT_DISTRIBUTION_ID"
  CLOUDFRONT_DISTRIBUTION_ID=$(aws ssm get-parameter --name "$SSM_PATH" --query 'Parameter.Value' --output text 2>/dev/null || true)
fi

if [[ -n "$CLOUDFRONT_DISTRIBUTION_ID" ]]; then
  echo "🔄 Invalidating CloudFront cache (distribution: $CLOUDFRONT_DISTRIBUTION_ID)..."
  aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" \
    --output text
  echo "   Invalidation created - cache will clear within 1-2 minutes"
else
  echo "⚠️  No CloudFront distribution ID found - skipping cache invalidation"
  echo "   Set CLOUDFRONT_DISTRIBUTION_ID in config.env or SSM parameter: /treasury-home/${ENVIRONMENT}/CLOUDFRONT_DISTRIBUTION_ID"
fi

echo "✅ Deployment complete!"
echo "   Bucket:  s3://$S3_BUCKET"
echo "   Files:   $FILE_COUNT"
if [[ -n "$SITE_URL" ]]; then
  echo "   Site:    $SITE_URL"
fi
