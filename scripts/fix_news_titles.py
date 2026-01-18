#!/usr/bin/env python3
"""
Fix news article titles that were scraped incorrectly.

Identifies articles with generic titles like "U.S. Department of the Treasury"
and re-fetches the correct titles from the live site.

Usage:
    python scripts/fix_news_titles.py --check    # Show files with bad titles
    python scripts/fix_news_titles.py --fix      # Fix the titles
"""

import argparse
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
BAD_TITLES = [
    "U.S. Department of the Treasury",
    "Untitled",
    "U.S. Department Of The Treasury",
]
HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}


def find_bad_titles() -> list:
    """Find all markdown files with bad titles."""
    bad_files = []
    
    for category_dir in CONTENT_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for md_file in category_dir.glob("*.md"):
            if md_file.name == "_index.md":
                continue
            
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract title from frontmatter
                title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip().strip('"\'')
                    if title in BAD_TITLES:
                        # Extract URL
                        url_match = re.search(r'^url:\s*(.+)$', content, re.MULTILINE)
                        url = url_match.group(1).strip() if url_match else ""
                        bad_files.append({
                            "file": md_file,
                            "title": title,
                            "url": url,
                        })
            except Exception as e:
                print(f"Error reading {md_file}: {e}")
    
    return bad_files


def fetch_correct_title(url_path: str) -> str:
    """Fetch the correct title from the live site."""
    url = f"{BASE_URL}{url_path}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Try multiple selectors for the title
    # 1. Look for the main article title (common on Treasury pages)
    title_elem = soup.find("h1", class_=re.compile(r"title|heading", re.I))
    
    # 2. Try any h1 that's not just the site name
    if not title_elem:
        for h1 in soup.find_all("h1"):
            text = h1.get_text(strip=True)
            if text and text not in BAD_TITLES and len(text) > 10:
                title_elem = h1
                break
    
    # 3. Try the page title from <title> tag, but extract just the article part
    if not title_elem:
        title_tag = soup.find("title")
        if title_tag:
            full_title = title_tag.get_text(strip=True)
            # Remove site name suffix
            parts = full_title.split("|")
            if len(parts) > 1:
                return parts[0].strip()
            return full_title
    
    if title_elem:
        title = title_elem.get_text(strip=True)
        # Clean up
        title = re.sub(r"\s*\|\s*U\.S\. Department of the Treasury$", "", title)
        return title
    
    return None


def fix_title_in_file(file_path: Path, new_title: str) -> bool:
    """Update the title in a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Escape quotes in title
        escaped_title = new_title.replace('"', '\\"')
        
        # Replace the title line
        new_content = re.sub(
            r'^title:\s*["\']?.+?["\']?\s*$',
            f'title: "{escaped_title}"',
            content,
            count=1,
            flags=re.MULTILINE
        )
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fix bad news titles")
    parser.add_argument("--check", action="store_true", help="Show files with bad titles")
    parser.add_argument("--fix", action="store_true", help="Fix the titles")
    parser.add_argument("--limit", type=int, default=0, help="Limit files to fix")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests")
    
    args = parser.parse_args()
    
    if not args.check and not args.fix:
        parser.print_help()
        sys.exit(1)
    
    print("🔍 Finding files with bad titles...")
    bad_files = find_bad_titles()
    print(f"   Found {len(bad_files)} files with generic titles")
    
    if args.check:
        print("\nFiles with bad titles:")
        for item in bad_files[:50]:
            print(f"   {item['file'].name}: {item['url']}")
        if len(bad_files) > 50:
            print(f"   ... and {len(bad_files) - 50} more")
        return
    
    if args.fix:
        to_fix = bad_files[:args.limit] if args.limit > 0 else bad_files
        print(f"\n🔧 Fixing {len(to_fix)} files...")
        
        fixed = 0
        failed = 0
        
        for i, item in enumerate(to_fix, 1):
            url_path = item["url"]
            if not url_path:
                print(f"   [{i}/{len(to_fix)}] {item['file'].name}: No URL, skipping")
                failed += 1
                continue
            
            print(f"   [{i}/{len(to_fix)}] {item['file'].name}...", end=" ", flush=True)
            
            new_title = fetch_correct_title(url_path)
            if new_title and new_title not in BAD_TITLES:
                if fix_title_in_file(item["file"], new_title):
                    print(f"✅ \"{new_title[:50]}...\"" if len(new_title) > 50 else f"✅ \"{new_title}\"")
                    fixed += 1
                else:
                    print("❌ Write failed")
                    failed += 1
            else:
                print("⚠️ Could not fetch title")
                failed += 1
            
            time.sleep(args.delay)
        
        print(f"\n✅ Fixed: {fixed}")
        print(f"❌ Failed: {failed}")


if __name__ == "__main__":
    main()
