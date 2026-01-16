#!/usr/bin/env python3
"""
Parallel API counter - counts items in Drupal JSON API using concurrent requests.
Outputs progress in real-time.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import time

BASE = "https://home.treasury.gov/jsonapi/node/news"
HEADERS = {"Accept": "application/vnd.api+json"}

CATS = [
    ("press-releases", "cf77c794-0050-49b5-88cd-4b9382644cdf"),
    ("featured-stories", "429abc81-2e6f-4b53-bce2-c00a50647848"), 
    ("statements-remarks", "f00aa509-9bd9-4709-a492-2b91c494c08d"),
    ("readouts", "f80b30aa-2c3b-449e-bdd0-beb4b9140da6"),
    ("testimonies", "03e1010e-a191-4299-abf0-a58781d1eb33"),
]

def count_category(name, uuid):
    """Count all items in a category."""
    count = 0
    offset = 0
    
    while offset < 10000:  # Safety limit
        url = f"{BASE}?filter[field_news_news_category.id]={uuid}&page[limit]=50&page[offset]={offset}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            data = r.json()
            items = len(data.get("data", []))
            count += items
            
            # Print progress
            print(f"  {name}: {count} (page {offset//50 + 1})", flush=True)
            
            if items < 50:
                break
            offset += 50
            
        except Exception as e:
            print(f"  {name}: ERROR at offset {offset} - {e}", flush=True)
            break
    
    return name, count

def main():
    print("=" * 50, flush=True)
    print("PARALLEL API COUNTER - Fetching all categories", flush=True)
    print("=" * 50, flush=True)
    print(flush=True)
    
    start = time.time()
    results = {}
    
    # Run all categories in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(count_category, name, uuid): name for name, uuid in CATS}
        
        for future in as_completed(futures):
            name, count = future.result()
            results[name] = count
            print(f"  ✅ {name} COMPLETE: {count}", flush=True)
    
    elapsed = time.time() - start
    
    print(flush=True)
    print("=" * 50, flush=True)
    print("RESULTS", flush=True)
    print("=" * 50, flush=True)
    
    total = 0
    for name, uuid in CATS:
        count = results.get(name, 0)
        total += count
        print(f"  {name}: {count}", flush=True)
    
    print(f"\n  TOTAL: {total}", flush=True)
    print(f"  Time: {elapsed:.1f}s", flush=True)

if __name__ == "__main__":
    main()
