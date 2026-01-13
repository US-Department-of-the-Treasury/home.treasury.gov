#!/usr/bin/env python3
"""
Treasury.gov Ultra-Fast Parallel Scraper

Parallelizes BOTH page collection AND article scraping for maximum speed.
Designed to scrape 1500+ pages of press releases efficiently.

Usage:
    python scripts/scrape_all.py --workers 10 --max-pages 2000
"""

import os
import re
import sys
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Treasury Migration Bot",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print_lock = Lock()
stats = {"pages_collected": 0, "articles_saved": 0, "errors": 0}
stats_lock = Lock()


def log(msg):
    with print_lock:
        print(msg, flush=True)


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def collect_page_links(page_num: int, category_path: str) -> list:
    """Collect article links from a single listing page."""
    if page_num == 0:
        url = f"{BASE_URL}{category_path}"
    else:
        url = f"{BASE_URL}{category_path}?page={page_num}"
    
    try:
        soup = get_soup(url)
        links = []
        
        # Skip patterns for navigation links
        skip_patterns = [
            r"/news/press-releases$",
            r"/news/featured-stories$", 
            r"/news/statements-remarks$",
            r"/news/readouts$",
            r"/news/testimonies$",
            r"/news/webcasts$",
            r"/press-contacts$",
        ]
        
        # Find all article links
        for a in soup.select(".view-content a, .field-content a, article a"):
            href = a.get("href", "")
            if "/news/" in href and not any(re.search(p, href) for p in skip_patterns):
                full_url = urljoin(BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
        
        with stats_lock:
            stats["pages_collected"] += 1
        
        return links
        
    except Exception as e:
        return []


def extract_article(url: str) -> dict:
    """Extract article data from a single article page."""
    soup = get_soup(url)
    data = {"url": url, "title": "", "date": "", "content": "", "summary": ""}
    
    # Title from <title> tag
    title_el = soup.select_one("title")
    if title_el:
        full_title = title_el.get_text(strip=True)
        if " | " in full_title:
            data["title"] = full_title.split(" | ")[0].strip()
        else:
            data["title"] = full_title
    
    # Date
    for selector in [".date-display-single", ".field--name-field-date", "time[datetime]"]:
        date_el = soup.select_one(selector)
        if date_el:
            dt = date_el.get("datetime")
            if dt:
                data["date"] = dt[:10]
                break
            date_text = date_el.get_text(strip=True)
            for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    data["date"] = datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
                    break
                except:
                    pass
            if data["date"]:
                break
    
    # Content
    content_el = soup.select_one(".field--name-body, article .content")
    if content_el:
        for unwanted in content_el.select("script, style"):
            unwanted.decompose()
        data["content"] = content_el.get_text(separator="\n", strip=True)
        first_p = content_el.select_one("p")
        if first_p:
            data["summary"] = first_p.get_text(strip=True)[:200]
    
    return data


def save_article(data: dict, category: str) -> Path:
    """Save article as Hugo markdown file."""
    if not data["title"]:
        return None
    
    cat_dir = CONTENT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    # Create slug
    slug = data["title"].lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)[:80].strip('-')
    
    if data["date"]:
        filename = f"{data['date']}-{slug}.md"
    else:
        filename = f"{slug}.md"
    
    filepath = cat_dir / filename
    
    # Front matter
    fm = [
        "---",
        f'title: "{data["title"].replace(chr(34), chr(39))}"',
        f'date: "{data["date"] or datetime.now().strftime("%Y-%m-%d")}"',
        f'draft: false',
        f'category: "{category}"',
    ]
    if data["summary"]:
        fm.append(f'description: "{data["summary"][:160].replace(chr(34), chr(39))}"')
    fm.append("---")
    fm.append("")
    
    content = "\n".join(fm) + data["content"]
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath


def scrape_article(args):
    """Scrape and save a single article."""
    url, category = args
    try:
        data = extract_article(url)
        filepath = save_article(data, category)
        if filepath:
            with stats_lock:
                stats["articles_saved"] += 1
            return ("ok", url)
        return ("empty", url)
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        return ("error", url, str(e))


def main():
    parser = argparse.ArgumentParser(description="Ultra-fast Treasury scraper")
    parser.add_argument("--workers", type=int, default=10, help="Parallel workers")
    parser.add_argument("--max-pages", type=int, default=2000, help="Max pages to check")
    parser.add_argument("--category", default="press-releases", help="Category to scrape")
    args = parser.parse_args()
    
    category_paths = {
        "press-releases": "/news/press-releases",
        "featured-stories": "/news/featured-stories",
    }
    
    if args.category not in category_paths:
        log(f"Unknown category: {args.category}")
        return
    
    cat_path = category_paths[args.category]
    
    log(f"🏛️  Treasury.gov ULTRA-FAST Scraper")
    log(f"👷 Workers: {args.workers}")
    log(f"📂 Category: {args.category}")
    log(f"📄 Max pages: {args.max_pages}")
    log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")
    
    # Create output directory
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    (CONTENT_DIR / args.category).mkdir(exist_ok=True)
    
    # PHASE 1: Parallel page link collection
    log("=" * 60)
    log("PHASE 1: Collecting article links from all pages...")
    start_time = time.time()
    
    all_links = set()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(collect_page_links, page, cat_path): page 
            for page in range(args.max_pages)
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            links = future.result()
            all_links.update(links)
            
            if completed % 100 == 0:
                log(f"   📄 Collected {completed}/{args.max_pages} pages, {len(all_links)} unique articles found...")
    
    collect_time = time.time() - start_time
    log(f"   ✅ Found {len(all_links)} unique articles in {collect_time:.1f}s")
    log("")
    
    if not all_links:
        log("No articles found!")
        return
    
    # PHASE 2: Parallel article scraping
    log("=" * 60)
    log("PHASE 2: Scraping all articles...")
    start_time = time.time()
    
    work_items = [(url, args.category) for url in all_links]
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scrape_article, item): item for item in work_items}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            
            if completed % 100 == 0 or completed == len(all_links):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                log(f"   ⏳ {completed}/{len(all_links)} articles ({rate:.1f}/sec) - {stats['articles_saved']} saved")
    
    scrape_time = time.time() - start_time
    
    log("")
    log("=" * 60)
    log(f"🎉 COMPLETE!")
    log(f"   📊 Pages collected: {stats['pages_collected']}")
    log(f"   📊 Articles saved: {stats['articles_saved']}")
    log(f"   ⚠️  Errors: {stats['errors']}")
    log(f"   ⏱️  Collection time: {collect_time:.1f}s")
    log(f"   ⏱️  Scraping time: {scrape_time:.1f}s")
    log(f"   📁 Saved to: {CONTENT_DIR / args.category}")


if __name__ == "__main__":
    main()
