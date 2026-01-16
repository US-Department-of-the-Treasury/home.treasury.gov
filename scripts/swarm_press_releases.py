#!/usr/bin/env python3
"""
Swarm scraper for Treasury press releases.
Fetches all 13,284 press releases using parallel API calls.

Usage:
    python scripts/swarm_press_releases.py
    python scripts/swarm_press_releases.py --workers 20
    python scripts/swarm_press_releases.py --dry-run
"""

import argparse
import html
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://home.treasury.gov/jsonapi/node/news"
PRESS_RELEASES_UUID = "cf77c794-0050-49b5-88cd-4b9382644cdf"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news" / "press-releases"
PAGE_SIZE = 50
TOTAL_ITEMS = 13284
TOTAL_PAGES = (TOTAL_ITEMS + PAGE_SIZE - 1) // PAGE_SIZE  # 266 pages
TIMEOUT = 30

HEADERS = {
    "Accept": "application/vnd.api+json",
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}

# Thread-safe counters
stats_lock = Lock()
stats = {
    "fetched": 0,
    "saved": 0,
    "skipped": 0,
    "errors": 0,
}


def html_to_markdown(html_content: str) -> str:
    """Convert HTML to clean Markdown."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Heading hierarchy (H1 in content → H2, etc.)
    heading_map = {"h1": 2, "h2": 2, "h3": 3, "h4": 3, "h5": 3, "h6": 3}
    for tag_name, level in heading_map.items():
        for h in soup.find_all(tag_name):
            text = h.get_text(strip=True)
            if text:
                h.replace_with(f"\n\n{'#' * level} {text}\n\n")
    
    # Bold/Strong
    for tag in soup.find_all(["strong", "b"]):
        tag.replace_with(f"**{tag.get_text()}**")
    
    # Italic/Em
    for tag in soup.find_all(["em", "i"]):
        tag.replace_with(f"*{tag.get_text()}*")
    
    # Links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            if href.startswith("/"):
                href = f"https://home.treasury.gov{href}"
            a.replace_with(f"[{text}]({href})")
        elif text:
            a.replace_with(text)
    
    # Lists
    for ul in soup.find_all("ul"):
        items = [f"- {li.get_text(strip=True)}" for li in ul.find_all("li", recursive=False)]
        ul.replace_with("\n" + "\n".join(items) + "\n")
    
    for ol in soup.find_all("ol"):
        items = [f"{i}. {li.get_text(strip=True)}" for i, li in enumerate(ol.find_all("li", recursive=False), 1)]
        ol.replace_with("\n" + "\n".join(items) + "\n")
    
    # Paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n\n{text}\n\n")
    
    # Line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    text = soup.get_text()
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n +", "\n", text)
    
    return text.strip()


def extract_release_number(path_alias: str) -> str:
    """Extract release number from path like /news/press-releases/sb0357."""
    if not path_alias:
        return ""
    match = re.search(r"/(sb|jl|sm)(\d+)$", path_alias, re.IGNORECASE)
    if match:
        return f"{match.group(1).upper()}{match.group(2)}"
    return ""


def create_slug(path_alias: str) -> str:
    """Create filename slug from path alias."""
    if not path_alias:
        return "untitled"
    slug = path_alias.rstrip("/").split("/")[-1].lower()
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug or "untitled"


def fetch_page(page_num: int, session: requests.Session) -> list:
    """Fetch a single page of press releases."""
    offset = page_num * PAGE_SIZE
    url = (
        f"{BASE_URL}?filter[field_news_news_category.id]={PRESS_RELEASES_UUID}"
        f"&sort=-field_news_publication_date"
        f"&page[limit]={PAGE_SIZE}&page[offset]={offset}"
    )
    
    try:
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        items = data.get("data", [])
        
        with stats_lock:
            stats["fetched"] += len(items)
        
        return items
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        print(f"  ⚠️ Page {page_num} error: {e}", flush=True)
        return []


def save_item(item: dict, existing_slugs: set) -> bool:
    """Save a single item to markdown. Returns True if saved."""
    attrs = item.get("attributes", {})
    
    title = attrs.get("title", "Untitled")
    
    # Publication date
    pub_date = attrs.get("field_news_publication_date", "")
    date_str = pub_date[:10] if pub_date else datetime.now().strftime("%Y-%m-%d")
    
    # Body content
    body_field = attrs.get("field_news_body", {})
    body_html = body_field.get("value", "") if isinstance(body_field, dict) else str(body_field or "")
    body_md = html_to_markdown(body_html)
    
    # Path and slug
    path = attrs.get("path", {})
    alias = path.get("alias", "") if isinstance(path, dict) else ""
    release_number = extract_release_number(alias)
    slug = create_slug(alias)
    
    # Skip if already exists
    if slug in existing_slugs:
        with stats_lock:
            stats["skipped"] += 1
        return False
    
    # Build filename and path
    filename = f"{date_str}-{slug}.md"
    filepath = CONTENT_DIR / filename
    
    if filepath.exists():
        with stats_lock:
            stats["skipped"] += 1
        return False
    
    # Build front matter
    fm_lines = ["---"]
    
    # Escape title properly
    if "\n" in title or '"' in title or ":" in title:
        escaped = title.replace("'", "''")
        fm_lines.append(f"title: '{escaped}'")
    else:
        fm_lines.append(f"title: {title}")
    
    fm_lines.append(f"date: {date_str}")
    fm_lines.append("draft: false")
    
    if release_number:
        fm_lines.append(f"press_release_number: {release_number}")
    if alias:
        fm_lines.append(f"url: {alias}")
    
    fm_lines.append("---")
    fm_lines.append("")
    
    content = "\n".join(fm_lines) + body_md + "\n"
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        with stats_lock:
            stats["saved"] += 1
        
        # Add to existing set
        existing_slugs.add(slug)
        return True
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        return False


def get_existing_slugs() -> set:
    """Get set of existing URL slugs to avoid duplicates."""
    slugs = set()
    
    if not CONTENT_DIR.exists():
        return slugs
    
    for md_file in CONTENT_DIR.glob("*.md"):
        if md_file.name == "_index.md":
            continue
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read(1500)
            
            url_match = re.search(r"^url:\s*(.+)$", content, re.MULTILINE)
            if url_match:
                url = url_match.group(1).strip().strip("'\"")
                slug = url.rstrip("/").split("/")[-1].lower()
                slugs.add(slug)
        except Exception:
            continue
    
    return slugs


def main():
    parser = argparse.ArgumentParser(description="Swarm scraper for Treasury press releases")
    parser.add_argument("--workers", type=int, default=15, help="Number of parallel workers (default: 15)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't save")
    parser.add_argument("--start-page", type=int, default=0, help="Starting page number")
    parser.add_argument("--end-page", type=int, default=TOTAL_PAGES, help="Ending page number")
    args = parser.parse_args()
    
    print("=" * 60, flush=True)
    print("🐝 SWARM SCRAPER - Treasury Press Releases", flush=True)
    print("=" * 60, flush=True)
    print(f"📊 Target: ~{TOTAL_ITEMS} items across {TOTAL_PAGES} pages", flush=True)
    print(f"⚡ Workers: {args.workers}", flush=True)
    print(f"📁 Output: {CONTENT_DIR}", flush=True)
    if args.dry_run:
        print("🔍 DRY RUN - no files will be saved", flush=True)
    print(flush=True)
    
    # Ensure output directory exists
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get existing slugs for deduplication
    print("📋 Scanning existing content...", flush=True)
    existing_slugs = get_existing_slugs()
    print(f"   Found {len(existing_slugs)} existing articles", flush=True)
    print(flush=True)
    
    # Create session for connection pooling
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=args.workers,
        pool_maxsize=args.workers * 2,
        max_retries=3,
    )
    session.mount("https://", adapter)
    
    start_time = time.time()
    all_items = []
    
    # Phase 1: Fetch all pages in parallel
    print(f"🚀 Phase 1: Fetching pages {args.start_page}-{args.end_page}...", flush=True)
    
    pages_to_fetch = list(range(args.start_page, args.end_page))
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_page, page, session): page for page in pages_to_fetch}
        
        completed = 0
        for future in as_completed(futures):
            items = future.result()
            all_items.extend(items)
            completed += 1
            
            if completed % 20 == 0 or completed == len(pages_to_fetch):
                elapsed = time.time() - start_time
                rate = stats["fetched"] / elapsed if elapsed > 0 else 0
                print(f"   📥 {completed}/{len(pages_to_fetch)} pages | {stats['fetched']} items | {rate:.0f}/sec", flush=True)
    
    fetch_time = time.time() - start_time
    print(f"\n✅ Fetched {len(all_items)} items in {fetch_time:.1f}s", flush=True)
    print(flush=True)
    
    if args.dry_run:
        print("🔍 DRY RUN complete - no files saved", flush=True)
        return
    
    # Phase 2: Save all items
    print("💾 Phase 2: Saving articles...", flush=True)
    save_start = time.time()
    
    for i, item in enumerate(all_items):
        save_item(item, existing_slugs)
        
        if (i + 1) % 500 == 0:
            print(f"   💾 {i + 1}/{len(all_items)} processed | {stats['saved']} saved | {stats['skipped']} skipped", flush=True)
    
    save_time = time.time() - save_start
    total_time = time.time() - start_time
    
    print(flush=True)
    print("=" * 60, flush=True)
    print("✅ COMPLETE", flush=True)
    print("=" * 60, flush=True)
    print(f"📥 Fetched:  {stats['fetched']} items", flush=True)
    print(f"💾 Saved:    {stats['saved']} new articles", flush=True)
    print(f"⏭️  Skipped:  {stats['skipped']} duplicates", flush=True)
    print(f"⚠️  Errors:   {stats['errors']}", flush=True)
    print(f"⏱️  Time:     {total_time:.1f}s (fetch: {fetch_time:.1f}s, save: {save_time:.1f}s)", flush=True)
    print(f"📁 Output:   {CONTENT_DIR}", flush=True)


if __name__ == "__main__":
    main()
