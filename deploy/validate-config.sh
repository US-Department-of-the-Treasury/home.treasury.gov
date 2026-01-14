#!/bin/bash
set -euo pipefail

# Validate SSM configuration before deployment
# This ensures infrastructure was provisioned via Terraform before deploying content
#
# Usage: ./deploy/validate-config.sh [environment]
#
# The SSM parameters are created by Terraform and represent the deployed infrastructure.
# This script fails fast if infrastructure hasn't been provisioned, preventing
# deployments to non-existent resources.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="treasury-home"
ENVIRONMENT="${1:-staging}"
SSM_PREFIX="/${PROJECT_NAME}/${ENVIRONMENT}"

# Required SSM parameters (created by Terraform)
REQUIRED_PARAMS=(
  "S3_BUCKET_NAME"
  "CLOUDFRONT_DISTRIBUTION_ID"
  "CLOUDFRONT_DOMAIN"
  "SITE_URL"
)

echo "Validating SSM configuration for ${PROJECT_NAME}/${ENVIRONMENT}..."
echo ""

MISSING_PARAMS=()
FOUND_PARAMS=()

for param in "${REQUIRED_PARAMS[@]}"; do
  FULL_PATH="${SSM_PREFIX}/${param}"
  if VALUE=$(aws ssm get-parameter --name "$FULL_PATH" --query 'Parameter.Value' --output text 2>/dev/null); then
    FOUND_PARAMS+=("$param=$VALUE")
    echo "  [OK] ${param}"
  else
    MISSING_PARAMS+=("$param")
    echo "  [MISSING] ${param}"
  fi
done

echo ""

if [ ${#MISSING_PARAMS[@]} -gt 0 ]; then
  echo "ERROR: Missing required SSM parameters"
  echo ""
  echo "The following parameters were not found:"
  for param in "${MISSING_PARAMS[@]}"; do
    echo "  - ${SSM_PREFIX}/${param}"
  done
  echo ""
  echo "These parameters are created by Terraform. To fix:"
  echo ""
  echo "  1. Ensure Terraform has been applied:"
  echo "     cd terraform && terraform apply"
  echo ""
  echo "  2. Or manually create the parameters (not recommended):"
  for param in "${MISSING_PARAMS[@]}"; do
    echo "     aws ssm put-parameter --name '${SSM_PREFIX}/${param}' --value '<value>' --type String"
  done
  echo ""
  exit 1
fi

echo "All required SSM parameters found!"
echo ""
echo "Configuration:"
for param in "${FOUND_PARAMS[@]}"; do
  echo "  ${param}"
done
echo ""
echo "Ready for deployment."
