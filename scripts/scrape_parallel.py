#!/usr/bin/env python3
"""
Treasury.gov Parallel Press Releases Scraper

Parallelized version using 5 concurrent workers for faster scraping.
Scrapes press releases from home.treasury.gov and saves them as Hugo markdown files.

Usage:
    python scripts/scrape_parallel.py [--workers 5] [--pages 10] [--category all]
"""

import os
import re
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue

BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
TIMEOUT = 30

# News categories and their URL paths
NEWS_CATEGORIES = {
    "press-releases": "/news/press-releases",
    "featured-stories": "/news/featured-stories",
    "statements-remarks": "/news/statements-remarks",
    "readouts": "/news/readouts",
    "testimonies": "/news/testimonies",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Treasury Migration Bot",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Thread-safe counter
print_lock = Lock()
stats = {"saved": 0, "errors": 0}
stats_lock = Lock()


def safe_print(*args, **kwargs):
    """Thread-safe print with flush."""
    with print_lock:
        print(*args, **kwargs, flush=True)


def get_soup(url: str) -> BeautifulSoup:
    """Fetch URL and return BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def extract_article_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract article links from a listing page."""
    links = []
    
    skip_patterns = [
        "/news/press-releases$",
        "/news/featured-stories$",
        "/news/statements-remarks$",
        "/news/readouts$",
        "/news/testimonies$",
        "/news/webcasts$",
        "/news/press-contacts$",
        "/press-contacts$",
    ]
    
    selectors = [
        ".view-content .views-row a",
        ".news-item a",
        ".view-news a",
        "article a",
        ".field-content a",
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for el in elements:
            href = el.get("href")
            if href and "/news/" in href:
                full_url = urljoin(base_url, href)
                is_nav = any(re.search(pattern, full_url) for pattern in skip_patterns)
                if is_nav:
                    continue
                if full_url not in links:
                    links.append(full_url)
    
    return links


def get_next_page_url(soup: BeautifulSoup, base_url: str) -> str:
    """Get the next page URL from pagination."""
    next_link = soup.select_one(".pager__item--next a, .pager-next a, a[rel='next']")
    if next_link:
        href = next_link.get("href")
        if href:
            return urljoin(base_url, href)
    return None


def extract_article_data(soup: BeautifulSoup, url: str) -> dict:
    """Extract article data from a single article page."""
    data = {
        "url": url,
        "title": "",
        "date": "",
        "category": "",
        "release_number": "",
        "content": "",
        "summary": "",
    }
    
    # Extract title from <title> tag
    title_el = soup.select_one("title")
    if title_el:
        full_title = title_el.get_text(strip=True)
        if " | " in full_title:
            data["title"] = full_title.split(" | ")[0].strip()
        else:
            data["title"] = full_title
    
    if not data["title"] or data["title"] == "U.S. Department of the Treasury":
        h1_el = soup.select_one("h1.page-title, h1.title, article h1")
        if h1_el:
            h1_text = h1_el.get_text(strip=True)
            if h1_text != "U.S. Department of the Treasury":
                data["title"] = h1_text
    
    # Extract date
    date_selectors = [
        ".date-display-single",
        ".field--name-field-date",
        ".news-date",
        "time[datetime]",
        ".field--name-created",
    ]
    
    for selector in date_selectors:
        date_el = soup.select_one(selector)
        if date_el:
            dt = date_el.get("datetime")
            if dt:
                data["date"] = dt[:10]
                break
            date_text = date_el.get_text(strip=True)
            if date_text:
                for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"]:
                    try:
                        parsed = datetime.strptime(date_text, fmt)
                        data["date"] = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            if data["date"]:
                break
    
    if not data["date"]:
        meta_date = soup.select_one('meta[property="article:published_time"]')
        if meta_date:
            data["date"] = meta_date.get("content", "")[:10]
    
    # Extract release number
    release_el = soup.select_one(".field--name-field-release-number, .release-number")
    if release_el:
        data["release_number"] = release_el.get_text(strip=True)
    
    # Extract category from URL
    for cat_slug, cat_path in NEWS_CATEGORIES.items():
        if cat_path in url:
            data["category"] = cat_slug
            break
    
    # Extract main content
    content_selectors = [
        ".field--name-body",
        ".node__content .field--type-text-long",
        "article .content",
        ".news-content",
        ".main-content .content",
    ]
    
    for selector in content_selectors:
        content_el = soup.select_one(selector)
        if content_el:
            for unwanted in content_el.select("script, style, .field-label"):
                unwanted.decompose()
            data["content"] = str(content_el)
            first_p = content_el.select_one("p")
            if first_p:
                data["summary"] = first_p.get_text(strip=True)[:300]
            break
    
    return data


def html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown."""
    soup = BeautifulSoup(html, "lxml")
    
    for i in range(1, 7):
        for h in soup.find_all(f"h{i}"):
            h.replace_with(f"\n{'#' * i} {h.get_text(strip=True)}\n")
    
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n{text}\n")
    
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            a.replace_with(f"[{text}]({href})")
    
    for ul in soup.find_all("ul"):
        items = []
        for li in ul.find_all("li"):
            items.append(f"- {li.get_text(strip=True)}")
        ul.replace_with("\n" + "\n".join(items) + "\n")
    
    for ol in soup.find_all("ol"):
        items = []
        for i, li in enumerate(ol.find_all("li"), 1):
            items.append(f"{i}. {li.get_text(strip=True)}")
        ol.replace_with("\n" + "\n".join(items) + "\n")
    
    for strong in soup.find_all(["strong", "b"]):
        strong.replace_with(f"**{strong.get_text(strip=True)}**")
    
    for em in soup.find_all(["em", "i"]):
        em.replace_with(f"*{em.get_text(strip=True)}*")
    
    text = soup.get_text()
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def create_slug(title: str, date: str) -> str:
    """Create a URL-safe slug from title and date."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')[:80]
    
    if date:
        return f"{date}-{slug}"
    return slug


def save_article(data: dict, category: str):
    """Save article as Hugo markdown file."""
    if not data["title"]:
        return None
    
    cat_dir = CONTENT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    slug = create_slug(data["title"], data["date"])
    filename = f"{slug}.md"
    filepath = cat_dir / filename
    
    md_content = html_to_markdown(data["content"]) if data["content"] else ""
    
    front_matter = {
        "title": data["title"],
        "date": data["date"] or datetime.now().strftime("%Y-%m-%d"),
        "draft": False,
        "category": data.get("category", category),
    }
    
    if data.get("release_number"):
        front_matter["release_number"] = data["release_number"]
    
    if data.get("summary"):
        front_matter["description"] = data["summary"][:160]
    
    fm_lines = ["---"]
    for key, value in front_matter.items():
        if isinstance(value, str):
            value = value.replace('"', '\\"')
            fm_lines.append(f'{key}: "{value}"')
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm_lines.append("")
    
    full_content = "\n".join(fm_lines) + md_content
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    return filepath


def scrape_single_article(args):
    """Scrape a single article - designed for parallel execution."""
    url, category = args
    try:
        soup = get_soup(url)
        data = extract_article_data(soup, url)
        filepath = save_article(data, category)
        
        if filepath:
            with stats_lock:
                stats["saved"] += 1
            return ("success", url, filepath)
        return ("empty", url, None)
        
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        return ("error", url, str(e))


def collect_all_links(category: str, max_pages: int) -> list:
    """Collect all article links from a category using direct page URLs."""
    if category not in NEWS_CATEGORIES:
        return []
    
    base_path = NEWS_CATEGORIES[category]
    base_url = f"{BASE_URL}{base_path}"
    
    all_links = []
    empty_page_count = 0
    
    for page_num in range(max_pages):
        # Treasury uses ?page=0, ?page=1, etc.
        if page_num == 0:
            url = base_url
        else:
            url = f"{base_url}?page={page_num}"
        
        if page_num % 10 == 0:
            safe_print(f"   📄 Collecting page {page_num + 1}...")
        
        try:
            soup = get_soup(url)
            links = extract_article_links(soup, BASE_URL)
            
            if not links:
                empty_page_count += 1
                if empty_page_count >= 3:
                    safe_print(f"   📄 No more articles after page {page_num + 1}")
                    break
            else:
                empty_page_count = 0
                all_links.extend(links)
            
            time.sleep(0.3)  # Small delay for pagination
            
        except requests.exceptions.HTTPError as e:
            if "404" in str(e):
                safe_print(f"   📄 Reached end at page {page_num + 1}")
                break
            safe_print(f"   ⚠️ Error on page {page_num + 1}: {e}")
            break
        except Exception as e:
            safe_print(f"   ⚠️ Error on page {page_num + 1}: {e}")
            continue
    
    # Remove duplicates
    seen = set()
    unique_links = []
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links


def scrape_category_parallel(category: str, max_pages: int, num_workers: int):
    """Scrape a category using parallel workers."""
    safe_print(f"\n{'='*60}")
    safe_print(f"📂 Category: {category.upper()}")
    safe_print(f"   URL: {BASE_URL}{NEWS_CATEGORIES[category]}")
    
    # First collect all links (fast, sequential)
    links = collect_all_links(category, max_pages)
    safe_print(f"   🔗 Found {len(links)} unique articles")
    
    if not links:
        return 0
    
    # Create category directory and index
    cat_dir = CONTENT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    title = category.replace("-", " ").title()
    index_content = f"""---
title: "{title}"
date: {datetime.now().strftime("%Y-%m-%d")}
draft: false
type: "news"
---
"""
    with open(cat_dir / "_index.md", "w") as f:
        f.write(index_content)
    
    # Parallel scraping with progress
    safe_print(f"   🚀 Scraping with {num_workers} parallel workers...")
    
    start_time = time.time()
    saved_count = 0
    error_count = 0
    
    # Prepare work items
    work_items = [(url, category) for url in links]
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(scrape_single_article, item): item for item in work_items}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            status, url, result = future.result()
            
            if status == "success":
                saved_count += 1
            elif status == "error":
                error_count += 1
            
            # Progress update every 10 articles
            if completed % 10 == 0 or completed == len(links):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                safe_print(f"   ⏳ Progress: {completed}/{len(links)} ({rate:.1f} articles/sec)")
    
    elapsed = time.time() - start_time
    safe_print(f"   ✅ Saved {saved_count} articles in {elapsed:.1f}s")
    if error_count:
        safe_print(f"   ⚠️ {error_count} errors")
    
    return saved_count


def main():
    parser = argparse.ArgumentParser(description="Parallel Treasury.gov scraper")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--pages", type=int, default=10, help="Max pages to scrape per category")
    parser.add_argument("--category", default="all", help="Category to scrape (or 'all')")
    args = parser.parse_args()
    
    safe_print("🏛️  Treasury.gov PARALLEL Press Releases Scraper")
    safe_print(f"👷 Workers: {args.workers}")
    safe_print(f"📄 Max pages per category: {args.pages}")
    safe_print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"📁 Output: {CONTENT_DIR}")
    
    # Create main news index
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONTENT_DIR / "_index.md", "w") as f:
        f.write('---\ntitle: "News"\ndate: 2024-01-01\n---\n')
    
    # Determine categories
    if args.category == "all":
        categories = list(NEWS_CATEGORIES.keys())
    else:
        categories = [args.category]
    
    total_start = time.time()
    total_saved = 0
    
    for category in categories:
        saved = scrape_category_parallel(category, args.pages, args.workers)
        total_saved += saved
    
    total_elapsed = time.time() - total_start
    
    safe_print("\n" + "=" * 60)
    safe_print(f"🎉 COMPLETE!")
    safe_print(f"   📊 Total articles saved: {total_saved}")
    safe_print(f"   ⏱️  Total time: {total_elapsed:.1f}s")
    safe_print(f"   📁 Content saved to: {CONTENT_DIR}")


if __name__ == "__main__":
    main()
