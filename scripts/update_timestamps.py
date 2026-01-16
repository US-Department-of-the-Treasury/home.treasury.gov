#!/usr/bin/env python3
"""
Treasury Timestamp Updater

Fetches full timestamps from Treasury JSON API and merges them into existing content files.
Only updates the date field - doesn't re-download content.

Usage:
    python scripts/update_timestamps.py --limit 1000
    python scripts/update_timestamps.py --since 2020-01-01 --limit 5000
    python scripts/update_timestamps.py --dry-run --limit 100
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
BASE_URL = "https://home.treasury.gov/jsonapi/node/news"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
STAGING_FILE = Path(__file__).parent.parent / "staging" / "timestamps.json"
TIMEOUT = 30

HEADERS = {
    "Accept": "application/vnd.api+json",
    "User-Agent": "Treasury Timestamp Updater/1.0",
}


def fetch_all_timestamps(limit: int = 1000, since_date: str = None) -> dict:
    """Fetch timestamps for all news items from the API.
    
    Returns:
        Dict mapping URL slug -> {title, timestamp, url}
    """
    timestamps = {}
    
    # Build base URL with sorting
    url = f"{BASE_URL}?sort=-field_news_publication_date"
    
    # Only fetch the fields we need
    url += "&fields[node--news]=title,field_news_publication_date,path"
    
    # Add date filter if specified
    if since_date:
        url += f"&filter[field_news_publication_date][condition][path]=field_news_publication_date"
        url += f"&filter[field_news_publication_date][condition][operator]=%3E%3D"
        url += f"&filter[field_news_publication_date][condition][value]={since_date}"
    
    # Pagination
    page_size = 50
    url += f"&page%5Blimit%5D={page_size}"
    
    print(f"📡 Fetching timestamps from Treasury JSON API...")
    if since_date:
        print(f"   Since: {since_date}")
    print(f"   Limit: {limit}")
    
    page = 0
    fetched = 0
    
    while fetched < limit:
        page += 1
        print(f"   Page {page}...", end=" ", flush=True)
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            page_items = data.get("data", [])
            if not page_items:
                print("(empty)")
                break
            
            for item in page_items:
                attrs = item.get("attributes", {})
                
                title = attrs.get("title", "")
                pub_date = attrs.get("field_news_publication_date", "")
                
                # Get URL path
                path = attrs.get("path", {})
                alias = path.get("alias", "") if isinstance(path, dict) else ""
                
                if alias and pub_date:
                    # Extract slug from path
                    slug = alias.rstrip("/").split("/")[-1].lower()
                    
                    timestamps[slug] = {
                        "title": title,
                        "timestamp": pub_date,
                        "url": alias,
                    }
                    fetched += 1
                    
                    if fetched >= limit:
                        break
            
            print(f"{len(page_items)} items (total: {fetched})")
            
            if fetched >= limit:
                break
            
            # Check for next page
            links = data.get("links", {})
            next_link = links.get("next")
            if next_link:
                url = next_link.get("href") if isinstance(next_link, dict) else next_link
            else:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"\n   ⚠️ Error: {e}")
            break
    
    return timestamps


def save_staging(timestamps: dict):
    """Save timestamps to staging file."""
    STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(STAGING_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(timestamps)} timestamps to {STAGING_FILE}")


def load_staging() -> dict:
    """Load timestamps from staging file."""
    if not STAGING_FILE.exists():
        return {}
    
    with open(STAGING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_timestamps(dry_run: bool = False) -> tuple:
    """Merge staged timestamps into content files.
    
    Returns:
        Tuple of (updated_count, skipped_count, not_found_count)
    """
    timestamps = load_staging()
    if not timestamps:
        print("❌ No staged timestamps found. Run with --fetch first.")
        return 0, 0, 0
    
    print(f"\n🔄 Merging {len(timestamps)} timestamps into content files...")
    
    updated = 0
    skipped = 0
    not_found = 0
    
    # Build index of all content files by URL slug
    content_files = {}
    for category_dir in CONTENT_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for md_file in category_dir.glob("*.md"):
            if md_file.name == "_index.md":
                continue
            
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract URL from frontmatter
                url_match = re.search(r"^url:\s*(.+)$", content, re.MULTILINE)
                if url_match:
                    url = url_match.group(1).strip().strip("'\"")
                    slug = url.rstrip("/").split("/")[-1].lower()
                    content_files[slug] = {
                        "path": md_file,
                        "content": content,
                    }
            except Exception:
                continue
    
    print(f"   Found {len(content_files)} content files")
    
    # Match and update
    for slug, ts_data in timestamps.items():
        if slug not in content_files:
            not_found += 1
            continue
        
        file_info = content_files[slug]
        content = file_info["content"]
        filepath = file_info["path"]
        
        # Parse existing date
        date_match = re.search(r"^date:\s*(.+)$", content, re.MULTILINE)
        if not date_match:
            skipped += 1
            continue
        
        old_date = date_match.group(1).strip().strip("'\"")
        new_timestamp = ts_data["timestamp"]
        
        # Skip if already has full timestamp
        if "T" in old_date:
            skipped += 1
            continue
        
        # Update the date line
        new_content = re.sub(
            r"^date:\s*.+$",
            f"date: {new_timestamp}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        
        if new_content == content:
            skipped += 1
            continue
        
        if dry_run:
            print(f"   [DRY RUN] {filepath.name}: {old_date} → {new_timestamp}")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
        
        updated += 1
    
    return updated, skipped, not_found


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and merge timestamps from Treasury API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch timestamps from API and save to staging",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge staged timestamps into content files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum items to fetch (default: 1000)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Only fetch items since this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    
    args = parser.parse_args()
    
    # Default to fetch + merge if neither specified
    if not args.fetch and not args.merge:
        args.fetch = True
        args.merge = True
    
    print("🏛️  Treasury Timestamp Updater")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.fetch:
        timestamps = fetch_all_timestamps(limit=args.limit, since_date=args.since)
        save_staging(timestamps)
        
        # Show sample
        print("\n📋 Sample timestamps:")
        for i, (slug, data) in enumerate(list(timestamps.items())[:5]):
            ts = data["timestamp"]
            title = data["title"][:50]
            print(f"   {slug}: {ts} - {title}...")
    
    if args.merge:
        updated, skipped, not_found = merge_timestamps(dry_run=args.dry_run)
        
        print(f"\n{'=' * 50}")
        if args.dry_run:
            print(f"🔍 DRY RUN - No files modified")
        print(f"✅ Updated: {updated}")
        print(f"⏭️  Skipped (already has time or unchanged): {skipped}")
        print(f"❓ Not found in content: {not_found}")


if __name__ == "__main__":
    main()
