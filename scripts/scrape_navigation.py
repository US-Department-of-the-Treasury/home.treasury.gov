#!/usr/bin/env python3
"""
Scrape navigation menu structure from Treasury.gov
Extracts the mega menu links and saves them as JSON for Hugo.
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from collections import OrderedDict

BASE_URL = "https://home.treasury.gov"
OUTPUT_DIR = Path(__file__).parent.parent / "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Treasury Migration Bot",
}


def scrape_navigation():
    """Scrape the main navigation menu from Treasury.gov"""
    print("🔍 Fetching Treasury.gov homepage...")
    response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "lxml")
    
    navigation = OrderedDict()
    
    # Find main nav items
    nav_items = soup.select("nav.usa-nav .usa-nav__primary-item, .main-nav .nav-item, #block-mainnavigation li")
    
    print(f"   Found {len(nav_items)} top-level nav items")
    
    for item in nav_items:
        # Get the top-level link
        top_link = item.select_one("> a, > button")
        if not top_link:
            continue
            
        title = top_link.get_text(strip=True)
        href = top_link.get("href", "")
        
        if not title or title in ["Search", ""]:
            continue
        
        print(f"   📁 {title}")
        
        # Look for submenu items
        submenu = item.select(".usa-nav__submenu a, .dropdown-menu a, .submenu a")
        
        children = []
        for sub in submenu:
            sub_title = sub.get_text(strip=True)
            sub_href = sub.get("href", "")
            
            if sub_title and sub_href:
                # Make absolute URL
                if sub_href.startswith("/"):
                    sub_href = f"{BASE_URL}{sub_href}"
                
                children.append({
                    "title": sub_title,
                    "url": sub_href
                })
                print(f"      - {sub_title}")
        
        # Make absolute URL for top-level
        if href.startswith("/"):
            href = f"{BASE_URL}{href}"
        
        navigation[title] = {
            "title": title,
            "url": href,
            "children": children
        }
    
    return navigation


def scrape_all_internal_links():
    """Scrape all internal links from the homepage for reference."""
    print("\n🔍 Collecting all internal links...")
    response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(response.text, "lxml")
    
    links = {}
    
    for a in soup.select("a[href^='/']"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        
        if href and text and href not in links:
            # Skip anchors and query strings for cleaner data
            if "#" in href:
                href = href.split("#")[0]
            if "?" in href:
                href = href.split("?")[0]
            
            if href and href != "/":
                links[href] = text
    
    # Sort by path
    sorted_links = OrderedDict(sorted(links.items()))
    return sorted_links


def save_navigation(nav_data, all_links):
    """Save navigation data as JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save structured navigation
    nav_file = OUTPUT_DIR / "navigation.json"
    with open(nav_file, "w", encoding="utf-8") as f:
        json.dump(nav_data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved navigation structure to {nav_file}")
    
    # Save all links for reference
    links_file = OUTPUT_DIR / "all_links.json"
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(all_links, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved all internal links to {links_file}")


def main():
    print("🏛️  Treasury.gov Navigation Scraper")
    print("=" * 50)
    
    # Scrape navigation
    navigation = scrape_navigation()
    
    # Scrape all internal links
    all_links = scrape_all_internal_links()
    
    print(f"\n📊 Summary:")
    print(f"   - {len(navigation)} top-level menu items")
    print(f"   - {sum(len(v['children']) for v in navigation.values())} submenu items")
    print(f"   - {len(all_links)} unique internal links")
    
    # Save data
    save_navigation(navigation, all_links)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
