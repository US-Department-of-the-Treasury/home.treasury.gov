#!/bin/bash
# Run batch audits in parallel using xargs

cd /Users/CorcosS/code/home.treasury.gov

# Get missing batch numbers (those without results or with empty results)
missing_batches() {
    for i in $(seq -w 1 165); do
        result_file="audit/news/results/batch-$i.json"
        if [ ! -f "$result_file" ] || [ $(jq 'length' "$result_file" 2>/dev/null || echo 0) -eq 0 ]; then
            echo "$i"
        fi
    done
}

# Run audit for a single batch
audit_one() {
    batch="$1"
    echo "Starting batch-$batch..."
    ./audit/audit-batch.sh "audit/news/batches/batch-${batch}.json" "audit/news/results/batch-${batch}.json" 2>/dev/null
    echo "Completed batch-$batch"
}

export -f audit_one

# Run in parallel (20 at a time)
echo "=== Starting parallel audit ==="
echo "Missing batches: $(missing_batches | wc -l | tr -d ' ')"
missing_batches | xargs -P 20 -I {} bash -c 'audit_one {}'
echo "=== All batches complete ==="
