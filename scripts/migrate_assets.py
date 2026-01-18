#!/usr/bin/env python3
"""
Treasury Static Asset Migration Script

Downloads static assets (PDFs, images, spreadsheets) from Treasury.gov
and prepares them for S3 upload.

Usage:
    python scripts/migrate_assets.py --inventory    # Just list assets
    python scripts/migrate_assets.py --download     # Download assets
    python scripts/migrate_assets.py --upload       # Upload to S3
"""

import argparse
import hashlib
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

# Configuration
BASE_URL = "https://home.treasury.gov"
URLS_FILE = Path(__file__).parent.parent / "docs" / "all_tres_urls.md"
ASSETS_DIR = Path(__file__).parent.parent / "static" / "system" / "files"
TIMEOUT = 60
MAX_WORKERS = 5

HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}

# File extensions to download
ASSET_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx",
    ".ppt", ".pptx", ".zip", ".jpg", ".jpeg", ".png",
    ".gif", ".svg", ".xml", ".txt", ".htm", ".html",
}


def get_asset_urls() -> list:
    """Extract asset URLs from the URL list."""
    assets = []
    
    if not URLS_FILE.exists():
        print(f"Error: URLs file not found: {URLS_FILE}")
        return assets
    
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "home.treasury.gov/system/files/" in line:
                # Extract the URL
                match = re.search(r'https://home\.treasury\.gov/system/files/[^\s"\'<>]+', line)
                if match:
                    url = match.group(0)
                    # Check extension
                    parsed = urlparse(url)
                    path = unquote(parsed.path)
                    ext = Path(path).suffix.lower()
                    if ext in ASSET_EXTENSIONS or not ext:
                        assets.append(url)
    
    return list(set(assets))  # Deduplicate


def inventory_assets():
    """Generate inventory of assets to migrate."""
    urls = get_asset_urls()
    
    print(f"📊 Asset Inventory")
    print(f"   Total assets: {len(urls)}")
    print()
    
    # Count by extension
    by_ext = {}
    by_subdir = {}
    
    for url in urls:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = Path(path).suffix.lower() or "(none)"
        by_ext[ext] = by_ext.get(ext, 0) + 1
        
        # Get subdirectory (e.g., /system/files/131/)
        parts = path.split("/")
        if len(parts) > 4:
            subdir = parts[4]
            by_subdir[subdir] = by_subdir.get(subdir, 0) + 1
    
    print("   By extension:")
    for ext, count in sorted(by_ext.items(), key=lambda x: -x[1])[:15]:
        print(f"      {ext}: {count}")
    
    print()
    print("   By subdirectory:")
    for subdir, count in sorted(by_subdir.items(), key=lambda x: -x[1])[:15]:
        print(f"      {subdir}/: {count}")
    
    # Write inventory file
    inventory_file = Path(__file__).parent.parent / "docs" / "asset_inventory.txt"
    with open(inventory_file, "w") as f:
        for url in sorted(urls):
            f.write(url + "\n")
    
    print()
    print(f"   Inventory written to: {inventory_file}")
    
    return urls


def download_asset(url: str, force: bool = False) -> tuple:
    """Download a single asset.
    
    Returns:
        Tuple of (url, success, message)
    """
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        # Create local path: static/system/files/...
        local_path = ASSETS_DIR / path.replace("/system/files/", "")
        
        if local_path.exists() and not force:
            return (url, True, "exists")
        
        # Create directory
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        response.raise_for_status()
        
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return (url, True, "downloaded")
        
    except Exception as e:
        return (url, False, str(e))


def download_assets(urls: list, max_workers: int = MAX_WORKERS, force: bool = False):
    """Download assets in parallel."""
    print(f"📥 Downloading {len(urls)} assets...")
    print(f"   Workers: {max_workers}")
    print(f"   Output: {ASSETS_DIR}")
    print()
    
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    existed = 0
    errors = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_asset, url, force): url for url in urls}
        
        for i, future in enumerate(as_completed(futures), 1):
            url, success, message = future.result()
            filename = url.split("/")[-1][:40]
            
            if success:
                if message == "exists":
                    existed += 1
                    status = "⏭️"
                else:
                    downloaded += 1
                    status = "✅"
            else:
                errors += 1
                status = "❌"
            
            # Progress
            if i % 50 == 0 or i == len(urls):
                print(f"   Progress: {i}/{len(urls)} ({downloaded} new, {existed} existing, {errors} errors)")
    
    print()
    print(f"   ✅ Downloaded: {downloaded}")
    print(f"   ⏭️ Already existed: {existed}")
    print(f"   ❌ Errors: {errors}")


def generate_s3_sync_command():
    """Generate AWS CLI command for S3 sync."""
    print("📤 S3 Upload Command")
    print()
    print("   Run the following to sync assets to S3:")
    print()
    print(f'   aws s3 sync {ASSETS_DIR} s3://YOUR-BUCKET/system/files/ \\')
    print('       --acl public-read \\')
    print('       --cache-control "public, max-age=31536000" \\')
    print('       --exclude "*.DS_Store"')
    print()
    print("   Or use the deploy script:")
    print("   ./deploy/s3-sync.sh prod --include-assets")


def main():
    parser = argparse.ArgumentParser(description="Treasury asset migration")
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Generate asset inventory",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download assets to local directory",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Show S3 upload command",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of assets to download (0 = all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Number of parallel download workers (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download of existing files",
    )
    
    args = parser.parse_args()
    
    if not any([args.inventory, args.download, args.upload]):
        parser.print_help()
        sys.exit(1)
    
    print("🏛️  Treasury Asset Migration")
    print()
    
    if args.inventory:
        inventory_assets()
    
    if args.download:
        urls = get_asset_urls()
        if args.limit > 0:
            urls = urls[:args.limit]
        download_assets(urls, max_workers=args.workers, force=args.force)
    
    if args.upload:
        generate_s3_sync_command()


if __name__ == "__main__":
    main()
