#!/bin/bash
# Audit a batch of URLs - compare Hugo titles vs Drupal titles

BATCH_FILE="$1"
OUTPUT_FILE="$2"

if [ -z "$BATCH_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <batch-file.json> <output-file.json>"
    exit 1
fi

# Extract titles from Hugo HTML
get_hugo_title() {
    local url="$1"
    # Handle both /path/ and /path URLs
    local hugo_file="public${url}/index.html"
    if [[ "$url" == */ ]]; then
        hugo_file="public${url}index.html"
    fi
    if [ -f "$hugo_file" ]; then
        sed -n 's/.*<title>\([^<]*\)<\/title>.*/\1/p' "$hugo_file" 2>/dev/null | head -1
    else
        echo "FILE_NOT_FOUND"
    fi
}

# Fetch Drupal page title
get_drupal_title() {
    local url="$1"
    local drupal_url="https://home.treasury.gov${url}"
    local html=$(curl -sL --max-time 10 "$drupal_url" 2>/dev/null)
    if [ -n "$html" ]; then
        echo "$html" | sed -n 's/.*<title>\([^<]*\)<\/title>.*/\1/p' | head -1
    else
        echo "FETCH_FAILED"
    fi
}

# Start JSON array
echo "[" > "$OUTPUT_FILE"

# Read URLs from batch file
urls=$(jq -r '.[].url' "$BATCH_FILE")
total=$(echo "$urls" | wc -l | tr -d ' ')
count=0
first=true

while IFS= read -r url; do
    count=$((count + 1))

    # Get titles
    hugo_title=$(get_hugo_title "$url")
    drupal_title=$(get_drupal_title "$url")

    # Compare (normalize whitespace)
    hugo_norm=$(echo "$hugo_title" | tr -s ' ' | sed 's/^ //;s/ $//')
    drupal_norm=$(echo "$drupal_title" | tr -s ' ' | sed 's/^ //;s/ $//')

    if [ "$hugo_norm" = "$drupal_norm" ]; then
        match="true"
    else
        match="false"
    fi

    # Escape JSON strings
    hugo_escaped=$(echo "$hugo_title" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
    drupal_escaped=$(echo "$drupal_title" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')

    # Append to JSON (with comma handling)
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi

    printf '  {"url": "%s", "hugo_title": "%s", "drupal_title": "%s", "title_match": %s}' \
        "$url" "$hugo_escaped" "$drupal_escaped" "$match" >> "$OUTPUT_FILE"

    echo "[$count/$total] $url - match: $match" >&2

done <<< "$urls"

# Close JSON array
echo "" >> "$OUTPUT_FILE"
echo "]" >> "$OUTPUT_FILE"

echo "Results written to $OUTPUT_FILE" >&2
