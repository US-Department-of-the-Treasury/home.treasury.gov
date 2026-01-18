#!/usr/bin/env python3
"""
Fill Empty Content

Fetches content for files that only have frontmatter but no body.
"""

import re
import sys
import time
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
HEADERS = {"User-Agent": "Treasury Hugo Migration Bot/1.0"}
TIMEOUT = 30


def fetch_content(url_path: str) -> Optional[str]:
    """Fetch article content from Treasury.gov"""
    try:
        resp = requests.get(BASE_URL + url_path, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find the main content
        article = (
            soup.find("article") or 
            soup.find(class_="node-content") or 
            soup.find(class_="field--name-body") or
            soup.find("main")
        )
        
        if not article:
            return None
        
        # Remove unwanted elements
        for tag in article.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        
        # Get text content
        text = article.get_text(separator="\n\n", strip=True)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text if len(text) > 50 else None
        
    except Exception as e:
        return None


def process_file(file_path: Path) -> bool:
    """Process a single file - return True if fixed"""
    content = file_path.read_text()
    
    # Parse frontmatter
    match = re.match(r'^---\n(.*?)\n---\n?(.*)', content, re.DOTALL)
    if not match:
        return False
    
    frontmatter = match.group(1)
    body = match.group(2).strip()
    
    # Skip if already has content
    if len(body) > 50:
        return False
    
    # Extract URL from frontmatter
    url_match = re.search(r'url:\s*(/news/[^\s\n]+)', frontmatter)
    if not url_match:
        return False
    
    url_path = url_match.group(1)
    
    # Fetch content
    new_body = fetch_content(url_path)
    if not new_body:
        return False
    
    # Update file
    new_content = f"---\n{frontmatter}\n---\n\n{new_body}\n"
    file_path.write_text(new_content)
    
    return True


def main():
    categories = ["media-advisories", "weekly-public-schedule"]
    
    print("🔧 Filling Empty Content (100 parallel workers)", flush=True)
    print("=" * 50, flush=True)
    
    for category in categories:
        cat_dir = CONTENT_DIR / category
        if not cat_dir.exists():
            continue
        
        # Find empty files
        empty_files = []
        for f in cat_dir.glob("*.md"):
            if f.name == "_index.md":
                continue
            
            content = f.read_text()
            match = re.match(r'^---\n.*?\n---\n?(.*)', content, re.DOTALL)
            if match:
                body = match.group(1).strip()
                if len(body) < 50:
                    empty_files.append(f)
        
        print(f"\n📂 {category}: {len(empty_files)} empty files", flush=True)
        
        if not empty_files:
            continue
        
        fixed = 0
        failed = 0
        
        # Process with thread pool - 100 parallel workers
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(process_file, f): f for f in empty_files}
            
            for i, future in enumerate(as_completed(futures)):
                if future.result():
                    fixed += 1
                else:
                    failed += 1
                
                if (i + 1) % 25 == 0:
                    print(f"   Progress: {i+1}/{len(empty_files)} (fixed: {fixed})", flush=True)
        
        print(f"   ✅ Fixed: {fixed}")
        print(f"   ❌ Failed: {failed}")
    
    print(f"\n{'=' * 50}")
    print("✅ Done!")


if __name__ == "__main__":
    main()
