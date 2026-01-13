#!/usr/bin/env python3
"""
Treasury.gov JSON API Scraper

Pulls structured data from the Drupal JSON API at home.treasury.gov/jsonapi.
Some endpoints require admin authentication - these are marked and will be
enabled once credentials are available.

Usage:
    python scripts/scrape_jsonapi.py [--admin-token TOKEN]
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path

BASE_URL = "https://home.treasury.gov/jsonapi"
DATA_DIR = Path(__file__).parent.parent / "data" / "api"
TIMEOUT = 30

# Taxonomy endpoints (mostly public)
TAXONOMY_ENDPOINTS = [
    "taxonomy_term/news_category",
    "taxonomy_term/content_offices",
    "taxonomy_term/tags",
    "taxonomy_term/ofac_tags",
    "taxonomy_term/ofac_faqs",
    "taxonomy_term/cfius_faq",
    "taxonomy_term/states",
    "taxonomy_term/recent_actions",
    "taxonomy_term/media_type",
    "taxonomy_term/faq_topics",
    "taxonomy_term/agenda_owner",
    "taxonomy_term/data_collection",
]

# Content endpoints (require admin for most)
CONTENT_ENDPOINTS = [
    "node/news",
    "node/page",
    "node/custom_page",
    "node/landing_page",
    "node/faq",
    "node/faqs",
    "node/data_set",
    "node/ofac_recent_action",
    "node/schedule_public",
    "node/schedule_travel",
    "node/slideshow",
    "node/slideshow_slide",
]

# Block content endpoints
BLOCK_ENDPOINTS = [
    "block_content/basic",
    "block_content/hero",
    "block_content/media_slideshow",
    "block_content/mega_menu",
    "block_content/text",
    "block_content/tile",
]

# Media endpoints (require admin)
MEDIA_ENDPOINTS = [
    "media/image",
    "media/document",
    "media/video",
    "media/audio_file",
]

# Data feed entities (Treasury rates, etc.)
DATA_FEED_ENDPOINTS = [
    "dfu_entity/daily_treasury_bill_rates",
    "dfu_entity/daily_treasury_long_term_rate",
    "dfu_entity/daily_treasury_real_long_term",
    "dfu_entity/daily_treasury_real_yield_curve",
    "dfu_entity/daily_treasury_yield_curve",
]


def fetch_endpoint(endpoint: str, token: str = None, page_limit: int = 50) -> dict:
    """Fetch data from a JSON API endpoint."""
    url = f"{BASE_URL}/{endpoint}"
    params = {"page[limit]": page_limit}
    headers = {"Accept": "application/vnd.api+json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  Error fetching {endpoint}: {e}")
        return None


def fetch_all_pages(endpoint: str, token: str = None, max_pages: int = 100) -> list:
    """Fetch all pages of data from a paginated endpoint."""
    all_data = []
    url = f"{BASE_URL}/{endpoint}"
    params = {"page[limit]": 50}
    headers = {"Accept": "application/vnd.api+json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    page = 0
    while url and page < max_pages:
        try:
            response = requests.get(url, params=params if page == 0 else None, 
                                   headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("data", [])
            all_data.extend(items)
            
            # Check for next page
            links = data.get("links", {})
            url = links.get("next", {}).get("href") if isinstance(links.get("next"), dict) else links.get("next")
            page += 1
            
            if items:
                print(f"  📄 Page {page}: {len(items)} items")
            
            time.sleep(0.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Error on page {page}: {e}")
            break
    
    return all_data


def save_data(endpoint: str, data, simplified: bool = True):
    """Save data to JSON file."""
    # Create filename from endpoint
    filename = endpoint.replace("/", "_") + ".json"
    filepath = DATA_DIR / filename
    
    # Optionally simplify taxonomy data
    if simplified and isinstance(data, list):
        simplified_data = []
        for item in data:
            attrs = item.get("attributes", {})
            simplified_item = {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": attrs.get("name") or attrs.get("title"),
                "description": attrs.get("description"),
                "weight": attrs.get("weight"),
                "status": attrs.get("status"),
                "changed": attrs.get("changed"),
                "path": attrs.get("path", {}).get("alias"),
            }
            # Add any extra fields that might be useful
            for key in ["drupal_internal__tid", "drupal_internal__nid", "langcode"]:
                if key in attrs:
                    simplified_item[key.replace("drupal_internal__", "")] = attrs[key]
            simplified_data.append(simplified_item)
        data = simplified_data
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"  💾 Saved to {filepath}")


def scrape_taxonomies(token: str = None):
    """Scrape all taxonomy endpoints."""
    print("\n📚 SCRAPING TAXONOMIES")
    print("=" * 50)
    
    for endpoint in TAXONOMY_ENDPOINTS:
        print(f"\n🔍 {endpoint}")
        data = fetch_all_pages(endpoint, token)
        
        if data:
            save_data(endpoint, data)
            print(f"  ✅ {len(data)} terms found")
        else:
            print(f"  ❌ No data (may require authentication)")


def scrape_content(token: str = None):
    """Scrape content node endpoints (requires admin for most)."""
    print("\n📰 SCRAPING CONTENT")
    print("=" * 50)
    
    for endpoint in CONTENT_ENDPOINTS:
        print(f"\n🔍 {endpoint}")
        data = fetch_all_pages(endpoint, token, max_pages=10)  # Limit pages for content
        
        if data:
            save_data(endpoint, data, simplified=False)
            print(f"  ✅ {len(data)} items found")
        else:
            print(f"  🔒 Requires authentication")


def scrape_blocks(token: str = None):
    """Scrape block content endpoints."""
    print("\n🧱 SCRAPING BLOCKS")
    print("=" * 50)
    
    for endpoint in BLOCK_ENDPOINTS:
        print(f"\n🔍 {endpoint}")
        data = fetch_all_pages(endpoint, token)
        
        if data:
            save_data(endpoint, data, simplified=False)
            print(f"  ✅ {len(data)} blocks found")
        else:
            print(f"  🔒 Requires authentication")


def scrape_media(token: str = None):
    """Scrape media endpoints (requires admin)."""
    print("\n🖼️  SCRAPING MEDIA")
    print("=" * 50)
    
    for endpoint in MEDIA_ENDPOINTS:
        print(f"\n🔍 {endpoint}")
        data = fetch_all_pages(endpoint, token, max_pages=5)
        
        if data:
            save_data(endpoint, data, simplified=False)
            print(f"  ✅ {len(data)} media items found")
        else:
            print(f"  🔒 Requires authentication")


def scrape_data_feeds(token: str = None):
    """Scrape Treasury data feed entities."""
    print("\n📊 SCRAPING DATA FEEDS")
    print("=" * 50)
    
    for endpoint in DATA_FEED_ENDPOINTS:
        print(f"\n🔍 {endpoint}")
        data = fetch_all_pages(endpoint, token, max_pages=5)
        
        if data:
            save_data(endpoint, data, simplified=False)
            print(f"  ✅ {len(data)} data entries found")
        else:
            print(f"  🔒 Requires authentication")


def get_api_index():
    """Fetch and save the full API index."""
    print("\n📋 FETCHING API INDEX")
    print("=" * 50)
    
    try:
        response = requests.get(BASE_URL, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Extract all available endpoints
        links = data.get("links", {})
        endpoints = {k: v.get("href") if isinstance(v, dict) else v 
                    for k, v in links.items() if k != "self"}
        
        with open(DATA_DIR / "api_index.json", "w") as f:
            json.dump(endpoints, f, indent=2)
        
        print(f"  ✅ {len(endpoints)} endpoints indexed")
        return endpoints
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {e}")
        return {}


def generate_hugo_data():
    """Convert scraped API data to Hugo data files."""
    print("\n🔄 GENERATING HUGO DATA FILES")
    print("=" * 50)
    
    hugo_data_dir = Path(__file__).parent.parent / "data"
    
    # News categories -> Hugo data
    news_cat_file = DATA_DIR / "taxonomy_term_news_category.json"
    if news_cat_file.exists():
        with open(news_cat_file) as f:
            categories = json.load(f)
        
        hugo_categories = [{"name": c["name"], "weight": c.get("weight", 0)} 
                          for c in categories if c.get("name")]
        
        with open(hugo_data_dir / "news_categories.json", "w") as f:
            json.dump(hugo_categories, f, indent=2)
        print("  ✅ Created data/news_categories.json")
    
    # States -> Hugo data
    states_file = DATA_DIR / "taxonomy_term_states.json"
    if states_file.exists():
        with open(states_file) as f:
            states = json.load(f)
        
        hugo_states = [{"name": s["name"], "id": s.get("tid")} 
                      for s in states if s.get("name")]
        
        with open(hugo_data_dir / "states.json", "w") as f:
            json.dump(hugo_states, f, indent=2)
        print("  ✅ Created data/states.json")
    
    # OFAC tags -> Hugo data  
    ofac_file = DATA_DIR / "taxonomy_term_ofac_tags.json"
    if ofac_file.exists():
        with open(ofac_file) as f:
            ofac_tags = json.load(f)
        
        hugo_ofac = [{"name": t["name"]} for t in ofac_tags if t.get("name")]
        
        with open(hugo_data_dir / "ofac_tags.json", "w") as f:
            json.dump(hugo_ofac, f, indent=2)
        print("  ✅ Created data/ofac_tags.json")


def main():
    parser = argparse.ArgumentParser(description="Scrape Treasury.gov JSON API")
    parser.add_argument("--admin-token", help="Admin OAuth token for authenticated endpoints")
    parser.add_argument("--taxonomies-only", action="store_true", help="Only scrape taxonomies")
    parser.add_argument("--all", action="store_true", help="Attempt all endpoints (needs auth for most)")
    args = parser.parse_args()
    
    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🏛️  Treasury.gov JSON API Scraper")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Output: {DATA_DIR}")
    
    if args.admin_token:
        print("🔑 Using admin authentication")
    else:
        print("🔓 Public access only (some endpoints will be restricted)")
    
    # Get API index first
    get_api_index()
    
    # Always scrape taxonomies (mostly public)
    scrape_taxonomies(args.admin_token)
    
    if args.all or args.admin_token:
        scrape_content(args.admin_token)
        scrape_blocks(args.admin_token)
        scrape_media(args.admin_token)
        scrape_data_feeds(args.admin_token)
    
    # Generate Hugo data files
    generate_hugo_data()
    
    print("\n" + "=" * 50)
    print("✅ SCRAPING COMPLETE")
    print(f"📁 Data saved to: {DATA_DIR}")
    
    if not args.admin_token:
        print("\n💡 TIP: Run with --admin-token TOKEN to access restricted endpoints")
        print("   Get a token from the Drupal admin: /admin/config/services/consumer")


if __name__ == "__main__":
    main()
