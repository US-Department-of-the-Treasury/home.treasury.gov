#!/bin/bash
#
# Deploy Hugo site to AWS S3
# Usage: ./deploy/s3-sync.sh [environment] [options]
#
# Environments:
#   staging  - Deploy to staging bucket
#   prod     - Deploy to production bucket (requires confirmation)
#
# Options:
#   --include-assets  - Also sync static assets from static/system/files/
#   --assets-only     - Only sync static assets, skip Hugo build
#   --dry-run         - Show what would be deployed without actually deploying
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/public"
ASSETS_DIR="$PROJECT_ROOT/static/system/files"

# Load configuration from config.env if it exists
if [[ -f "$SCRIPT_DIR/config.env" ]]; then
  source "$SCRIPT_DIR/config.env"
fi

# Configuration - set in deploy/config.env (copy from config.env.example)
S3_BUCKET_STAGING="${S3_BUCKET_STAGING:-treasury-hugo-staging}"
S3_BUCKET_PROD="${S3_BUCKET_PROD:-treasury-hugo-prod}"
AWS_REGION="${AWS_REGION:-us-east-1}"
CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-}"

# Parse arguments
ENVIRONMENT="${1:-staging}"
INCLUDE_ASSETS=false
ASSETS_ONLY=false
DRY_RUN=""

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-assets)
      INCLUDE_ASSETS=true
      shift
      ;;
    --assets-only)
      ASSETS_ONLY=true
      shift
      ;;
    --dry-run)
      DRY_RUN="--dryrun"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

case "$ENVIRONMENT" in
  staging)
    S3_BUCKET="$S3_BUCKET_STAGING"
    echo "🚀 Deploying to STAGING ($S3_BUCKET)"
    ;;
  prod|production)
    S3_BUCKET="$S3_BUCKET_PROD"
    echo "⚠️  You are about to deploy to PRODUCTION ($S3_BUCKET)"
    read -p "Are you sure? (yes/no): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
      echo "Deployment cancelled."
      exit 0
    fi
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT"
    echo "Usage: $0 [staging|prod]"
    exit 1
    ;;
esac

# Build the site (unless assets-only)
if [[ "$ASSETS_ONLY" != "true" ]]; then
  echo "📦 Building Hugo site..."
  cd "$PROJECT_ROOT"
  hugo --minify --gc

  if [[ ! -d "$BUILD_DIR" ]]; then
    echo "❌ Build failed - no public directory found"
    exit 1
  fi

  # Count files
  FILE_COUNT=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
  echo "   Found $FILE_COUNT files to deploy"

  # Sync to S3
  echo "☁️  Syncing to S3..."
else
  echo "📄 Assets-only mode - skipping Hugo build"
  FILE_COUNT=0
fi

if [[ "$ASSETS_ONLY" != "true" ]]; then

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
  $DRY_RUN \
  --delete
fi

# Sync static assets if requested
if [[ "$INCLUDE_ASSETS" == "true" || "$ASSETS_ONLY" == "true" ]]; then
  if [[ -d "$ASSETS_DIR" ]]; then
    ASSET_COUNT=$(find "$ASSETS_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "📄 Syncing $ASSET_COUNT static assets..."
    
    aws s3 sync "$ASSETS_DIR" "s3://$S3_BUCKET/system/files" \
      --region "$AWS_REGION" \
      --cache-control "max-age=2592000" \
      $DRY_RUN
    
    echo "   ✅ Assets synced to s3://$S3_BUCKET/system/files/"
  else
    echo "⚠️  No assets directory found at $ASSETS_DIR"
    echo "   Run: python scripts/migrate_assets.py --download"
  fi
fi

# Invalidate CloudFront if configured
if [[ -n "$CLOUDFRONT_DISTRIBUTION_ID" && "$ENVIRONMENT" == "prod" ]]; then
  echo "🔄 Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*"
fi

echo ""
echo "✅ Deployment complete!"
echo "   Bucket: s3://$S3_BUCKET"
if [[ "$ASSETS_ONLY" != "true" ]]; then
  echo "   Hugo files: $FILE_COUNT"
fi
if [[ "$INCLUDE_ASSETS" == "true" || "$ASSETS_ONLY" == "true" ]]; then
  echo "   Assets: $ASSET_COUNT"
fi
