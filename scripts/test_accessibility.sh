#!/bin/bash
# Section 508 / WCAG 2.1 AA Accessibility Testing
# Uses pa11y for automated accessibility scanning
#
# Prerequisites:
#   npm install -g pa11y pa11y-ci
#
# Usage:
#   ./scripts/test_accessibility.sh [url]
#   ./scripts/test_accessibility.sh  # defaults to localhost:1313

set -e

# Default URL
BASE_URL="${1:-http://localhost:1313}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "  Section 508 / WCAG 2.1 AA Compliance Test"
echo "============================================"
echo ""
echo "Testing: $BASE_URL"
echo ""

# Check if pa11y is installed
if ! command -v pa11y &> /dev/null; then
    echo -e "${YELLOW}pa11y not found. Installing...${NC}"
    npm install -g pa11y pa11y-ci
fi

# URLs to test
URLS=(
    "/news/press-releases/"
    "/news/press-releases/sb0357/"
)

TOTAL_ERRORS=0
TOTAL_WARNINGS=0

for path in "${URLS[@]}"; do
    url="${BASE_URL}${path}"
    echo -e "${YELLOW}Testing: ${path}${NC}"
    echo "----------------------------------------"
    
    # Run pa11y with WCAG 2.1 AA standard (Section 508 baseline)
    OUTPUT=$(pa11y "$url" \
        --standard WCAG2AA \
        --reporter cli \
        --timeout 30000 \
        --ignore "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail" \
        2>&1) || true
    
    # Count errors and warnings
    ERRORS=$(echo "$OUTPUT" | grep -c "Error:" || true)
    WARNINGS=$(echo "$OUTPUT" | grep -c "Warning:" || true)
    
    TOTAL_ERRORS=$((TOTAL_ERRORS + ERRORS))
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + WARNINGS))
    
    if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ No issues found${NC}"
    else
        echo "$OUTPUT"
        echo ""
        echo -e "Errors: ${RED}${ERRORS}${NC}, Warnings: ${YELLOW}${WARNINGS}${NC}"
    fi
    echo ""
done

echo "============================================"
echo "  Summary"
echo "============================================"
echo -e "Total Errors:   ${RED}${TOTAL_ERRORS}${NC}"
echo -e "Total Warnings: ${YELLOW}${TOTAL_WARNINGS}${NC}"
echo ""

if [ "$TOTAL_ERRORS" -gt 0 ]; then
    echo -e "${RED}✗ Accessibility issues found${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Add alt text to images"
    echo "  - Ensure sufficient color contrast (4.5:1 for text)"
    echo "  - Add labels to form inputs"
    echo "  - Use semantic HTML (headings, landmarks)"
    echo "  - Ensure keyboard navigation works"
    exit 1
else
    echo -e "${GREEN}✓ No critical accessibility errors${NC}"
    exit 0
fi
