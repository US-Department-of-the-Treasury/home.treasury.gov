#!/usr/bin/env python3
"""
Parallel Batch Scraper for Treasury News Content

Runs multiple scraper workers in parallel to speed up content migration.
Each worker handles a subset of the remaining URLs.

Usage:
    python scripts/scrape_parallel_batch.py --workers 10
"""

import argparse
import concurrent.futures
import html
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
URLS_FILE = Path(__file__).parent.parent / "docs" / "all_tres_urls.md"
TIMEOUT = 30

CATEGORY_PATHS = {
    "media-advisories": "/news/media-advisories/",
    "weekly-public-schedule": "/news/weekly-public-schedule/",
}

HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
    "Accept": "text/html,application/xhtml+xml",
}


def get_existing_ids(category: str) -> Set[str]:
    """Get set of existing content IDs for a category."""
    category_dir = CONTENT_DIR / category
    existing = set()
    
    if not category_dir.exists():
        return existing
    
    for f in category_dir.glob("*.md"):
        if f.name == "_index.md":
            continue
        # Extract ID from filename like 2025-12-23-js1234.md
        parts = f.stem.split("-")
        if len(parts) >= 4:
            existing.add(parts[-1].lower())
    
    return existing


def get_urls_for_category(category: str) -> List[str]:
    """Get all URLs for a category from the URLs file."""
    urls = []
    path_pattern = CATEGORY_PATHS.get(category, "")
    
    if not path_pattern or not URLS_FILE.exists():
        return urls
    
    with open(URLS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if path_pattern in line and line.startswith("http"):
                urls.append(line)
    
    return urls


def get_missing_urls(category: str) -> List[str]:
    """Get URLs that haven't been scraped yet."""
    existing_ids = get_existing_ids(category)
    all_urls = get_urls_for_category(category)
    
    missing = []
    for url in all_urls:
        # Extract ID from URL
        url_id = url.rstrip("/").split("/")[-1].lower()
        if url_id not in existing_ids:
            missing.append(url)
    
    return missing


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Process headers
    for tag_name, level in [("h1", 2), ("h2", 2), ("h3", 3), ("h4", 3)]:
        for h in soup.find_all(tag_name):
            text = h.get_text(strip=True)
            if text:
                h.replace_with(f"\n\n{'#' * level} {text}\n\n")
    
    # Bold/Strong
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text()
        tag.replace_with(f"**{text}**")
    
    # Italic/Em
    for tag in soup.find_all(["em", "i"]):
        text = tag.get_text()
        tag.replace_with(f"*{text}*")
    
    # Links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            if href.startswith("/"):
                href = urljoin(BASE_URL, href)
            a.replace_with(f"[{text}]({href})")
    
    # Lists
    for ul in soup.find_all("ul"):
        items = []
        for li in ul.find_all("li", recursive=False):
            items.append(f"- {li.get_text(strip=True)}")
        ul.replace_with("\n" + "\n".join(items) + "\n")
    
    for ol in soup.find_all("ol"):
        items = []
        for i, li in enumerate(ol.find_all("li", recursive=False), 1):
            items.append(f"{i}. {li.get_text(strip=True)}")
        ol.replace_with("\n" + "\n".join(items) + "\n")
    
    # Paragraphs
    for p in soup.find_all("p"):
        text = p.get_text()
        p.replace_with(f"\n{text}\n")
    
    # Get text and clean up
    text = soup.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    
    return text.strip()


def scrape_page(url: str) -> Optional[Tuple[str, str, str, str]]:
    """Scrape a single page and return (id, title, date, content)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract ID from URL
        page_id = url.rstrip("/").split("/")[-1]
        
        # Get title
        title = "Untitled"
        title_el = soup.find("h1") or soup.find("title")
        if title_el:
            title = title_el.get_text(strip=True)
            # Clean up generic titles
            if "U.S. Department of the Treasury" in title:
                # Try to get a better title from og:title
                og_title = soup.find("meta", {"property": "og:title"})
                if og_title and og_title.get("content"):
                    title = og_title["content"]
        
        # Get date
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_el = soup.find("time") or soup.find(class_="field--name-field-date-time-public")
        if date_el:
            date_text = date_el.get("datetime") or date_el.get_text(strip=True)
            # Try to parse date
            for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    parsed = datetime.strptime(date_text[:10], "%Y-%m-%d")
                    date_str = parsed.strftime("%Y-%m-%d")
                    break
                except:
                    pass
        
        # Get content
        content = ""
        body_el = soup.find(class_="field--name-field-news-body") or soup.find(class_="field--name-body")
        if body_el:
            content = html_to_markdown(str(body_el))
        
        return (page_id, title, date_str, content)
    
    except Exception as e:
        return None


def save_content(category: str, page_id: str, title: str, date_str: str, content: str) -> bool:
    """Save scraped content to a markdown file."""
    category_dir = CONTENT_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean title for YAML
    clean_title = title.replace('"', '\\"').replace("\n", " ")
    if len(clean_title) > 200:
        clean_title = clean_title[:197] + "..."
    
    # Build frontmatter
    frontmatter = f'''---
title: "{clean_title}"
date: {date_str}
draft: false
url: /news/{category}/{page_id}
---
'''
    
    # Write file
    filename = f"{date_str}-{page_id}.md"
    filepath = category_dir / filename
    
    with open(filepath, "w") as f:
        f.write(frontmatter)
        f.write(content)
    
    return True


def scrape_worker(args: Tuple[str, str, int]) -> Tuple[str, bool]:
    """Worker function for parallel scraping."""
    url, category, worker_id = args
    
    result = scrape_page(url)
    if result:
        page_id, title, date_str, content = result
        save_content(category, page_id, title, date_str, content)
        return (url, True)
    
    return (url, False)


def main():
    parser = argparse.ArgumentParser(description="Parallel batch scraper")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests per worker")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 PARALLEL BATCH SCRAPER")
    print(f"   Workers: {args.workers}")
    print("=" * 60)
    print()
    
    # Get missing URLs for each category
    all_work = []
    
    for category in ["media-advisories", "weekly-public-schedule"]:
        missing = get_missing_urls(category)
        print(f"📂 {category}: {len(missing)} URLs to scrape")
        for url in missing:
            all_work.append((url, category, 0))
    
    if not all_work:
        print("\n✅ All content already scraped!")
        return
    
    print(f"\n📊 Total URLs to scrape: {len(all_work)}")
    print(f"⏱️  Starting {args.workers} parallel workers...\n")
    
    # Track progress
    completed = 0
    failed = 0
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel scraping
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scrape_worker, work): work for work in all_work}
        
        for future in concurrent.futures.as_completed(futures):
            url, success = future.result()
            completed += 1
            
            if success:
                page_id = url.rstrip("/").split("/")[-1]
                print(f"   [{completed}/{len(all_work)}] {page_id}... ✅")
            else:
                failed += 1
                print(f"   [{completed}/{len(all_work)}] FAILED: {url}")
            
            # Small delay to be respectful
            time.sleep(args.delay)
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("✅ SCRAPING COMPLETE")
    print(f"   Completed: {completed - failed}")
    print(f"   Failed: {failed}")
    print(f"   Time: {elapsed:.1f}s ({completed/elapsed:.1f} pages/sec)")
    print("=" * 60)


if __name__ == "__main__":
    main()
