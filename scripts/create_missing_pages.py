#!/usr/bin/env python3
"""
Create Missing Press Release Pages

Fetches pages that exist on the live Treasury site but are missing from
the Hugo build, and creates the corresponding markdown files.

Usage:
    python3 scripts/create_missing_pages.py --dry-run
    python3 scripts/create_missing_pages.py --limit 10
    python3 scripts/create_missing_pages.py
"""

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


def log(msg: str = "", end: str = "\n"):
    """Print with immediate flush for real-time output."""
    print(msg, end=end, flush=True)


# Configuration
BASE_URL = "https://home.treasury.gov"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 3

HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def fetch_page(url_path: str) -> Optional[str]:
    """Fetch HTML content from a page URL."""
    page_url = f"{BASE_URL}{url_path}"
    
    for attempt in range(MAX_RETRIES):
        try:
            log(f"      Fetching: {page_url[:70]}...", end="")
            response = requests.get(page_url, headers=HTML_HEADERS, timeout=TIMEOUT)
            log(f" {response.status_code}")
            
            if response.status_code == 404:
                log(f"      Page not found (404)")
                return None
            
            if response.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_DELAY * (attempt + 1)
                log(f"      Server error, retrying in {delay}s...")
                time.sleep(delay)
                continue
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                log(f" ERROR")
                log(f"      {e}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                log(f" FAILED")
                return None
    
    return None


def extract_press_release_data(html_content: str, url_path: str) -> dict:
    """Extract press release metadata and content from HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find main content area
    main = soup.find(id="main-content")
    
    # Extract title
    title = ""
    if main:
        title_field = main.select_one(".field--name-title")
        if title_field:
            title = title_field.get_text(strip=True)
    
    if not title:
        # Fallback
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    
    # Extract publication date
    pub_date = None
    if main:
        date_field = main.select_one(".field--name-field-news-publication-date time")
        if date_field and date_field.get("datetime"):
            pub_date = date_field.get("datetime")[:10]  # YYYY-MM-DD
    
    # Try to extract date from body content
    if not pub_date and main:
        body = main.select_one(".field--name-field-news-body")
        if body:
            text = body.get_text()
            # Look for patterns like "January 23, 2008" or "2008-01-23"
            date_patterns = [
                r"(\w+ \d{1,2}, \d{4})",  # January 23, 2008
                r"(\d{4}-\d{2}-\d{2})",   # 2008-01-23
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text[:500])
                if match:
                    try:
                        from dateutil import parser as date_parser
                        parsed = date_parser.parse(match.group(1))
                        pub_date = parsed.strftime("%Y-%m-%d")
                        break
                    except:
                        pass
    
    # Extract slug from URL
    slug = url_path.rstrip("/").split("/")[-1]
    
    # Try to infer date from slug patterns like jy2419, hp768, etc.
    if not pub_date:
        # Default to a placeholder date - we'll need to fix these manually
        pub_date = "2020-01-01"
    
    # Extract body content
    body_html = ""
    if main:
        body_field = main.select_one(".field--name-field-news-body")
        if body_field:
            body_html = str(body_field)
    
    # Convert body to clean text (simple conversion)
    body_text = ""
    if body_html:
        body_soup = BeautifulSoup(body_html, "html.parser")
        
        # Remove archived content notice
        for em in body_soup.find_all("em"):
            if "Archived Content" in em.get_text():
                em.decompose()
        
        body_text = body_soup.get_text(separator="\n", strip=True)
        body_text = re.sub(r"\n{3,}", "\n\n", body_text)
    
    # Determine press release number from slug
    press_release_number = ""
    slug_upper = slug.upper()
    for prefix in ["JY", "HP", "SM", "JS", "SB", "LS", "TG", "PO"]:
        if slug_upper.startswith(prefix):
            press_release_number = slug_upper
            break
    
    return {
        "title": title,
        "date": pub_date,
        "url": url_path,
        "slug": slug,
        "press_release_number": press_release_number,
        "body_html": body_html,
        "body_text": body_text,
    }


def create_markdown_content(data: dict) -> str:
    """Create Hugo markdown file content."""
    # Build frontmatter
    title = data["title"].replace('"', '\\"')
    
    lines = [
        "---",
        f'title: "{title}"',
        f'date: {data["date"]}',
        "draft: false",
        f'url: {data["url"]}',
    ]
    
    if data["press_release_number"]:
        lines.append(f'press_release_number: {data["press_release_number"]}')
    
    lines.append("---")
    lines.append("")
    
    # Add body content
    if data["body_text"]:
        lines.append(data["body_text"])
    
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Create missing press release pages from live Treasury site",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="text_comparison.json",
        help="Path to text_comparison.json",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="content/news/press-releases",
        help="Output directory for markdown files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of pages to process",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    workspace = Path(__file__).parent.parent
    input_path = workspace / args.input_file
    output_dir = workspace / args.output_dir
    
    log("=" * 70)
    log("CREATE MISSING PRESS RELEASE PAGES")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    log()
    
    # Load comparison data
    log(f"[1/3] LOADING COMPARISON DATA")
    log(f"      Input: {input_path}")
    
    if not input_path.exists():
        log(f"      ERROR: File not found!")
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter to missing_target pages
    comparisons = data.get("comparisons", [])
    missing = [item for item in comparisons if item.get("status") == "missing_target"]
    
    log(f"      Total comparisons: {len(comparisons)}")
    log(f"      Missing from Hugo: {len(missing)}")
    
    if args.limit:
        missing = missing[:args.limit]
        log(f"      Limited to: {len(missing)}")
    
    log()
    
    # Process each missing page
    log(f"[2/3] FETCHING AND CREATING PAGES")
    log("-" * 70)
    
    created = 0
    skipped = 0
    errors = 0
    
    for i, item in enumerate(missing, 1):
        url = item.get("url", "")
        slug = url.rstrip("/").split("/")[-1]
        
        log()
        log(f"  [{i}/{len(missing)}] {url}")
        
        # Check if file already exists
        existing = list(output_dir.glob(f"*{slug}.md"))
        if existing:
            log(f"      SKIPPED: File already exists: {existing[0].name}")
            skipped += 1
            continue
        
        if args.dry_run:
            log(f"      DRY RUN: Would fetch and create file")
            created += 1
            continue
        
        # Fetch the page
        html_content = fetch_page(url)
        
        if not html_content:
            log(f"      ERROR: Could not fetch page")
            errors += 1
            continue
        
        # Extract data
        page_data = extract_press_release_data(html_content, url)
        
        if not page_data["title"]:
            log(f"      ERROR: Could not extract title")
            errors += 1
            continue
        
        log(f"      Title: {page_data['title'][:60]}...")
        log(f"      Date: {page_data['date']}")
        log(f"      Body: {len(page_data['body_text'])} chars")
        
        # Create markdown content
        markdown = create_markdown_content(page_data)
        
        # Determine filename
        filename = f"{page_data['date']}-{slug}.md"
        filepath = output_dir / filename
        
        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        log(f"      CREATED: {filename}")
        created += 1
        
        # Delay between requests
        if i < len(missing) and args.delay > 0:
            time.sleep(args.delay)
    
    log()
    log("-" * 70)
    
    # Summary
    log(f"[3/3] SUMMARY")
    log("=" * 70)
    log(f"  Total processed: {len(missing)}")
    log(f"  Created: {created}")
    log(f"  Skipped (already exist): {skipped}")
    log(f"  Errors: {errors}")
    
    if args.dry_run:
        log()
        log("  NOTE: This was a DRY RUN. No files were created.")
        log("  Run without --dry-run to create files.")
    
    log()


if __name__ == "__main__":
    main()
