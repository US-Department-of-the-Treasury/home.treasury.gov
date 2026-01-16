#!/usr/bin/env python3
"""
Scrape Missing News Content

Identifies and scrapes news content that exists on Treasury.gov but 
is missing from the Hugo content directory.

Usage:
    python scripts/scrape_missing_news.py --category press-releases --limit 500
    python scripts/scrape_missing_news.py --category media-advisories --limit 1000
    python scripts/scrape_missing_news.py --all --limit 2000
"""

import argparse
import html
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
URLS_FILE = Path(__file__).parent.parent / "docs" / "all_tres_urls.md"
TIMEOUT = 30

# Category path mappings
CATEGORY_PATHS = {
    "press-releases": "/news/press-releases/",
    "media-advisories": "/news/media-advisories/",
    "weekly-public-schedule": "/news/weekly-public-schedule/",
    "weekly-schedule-updates": "/news/weekly-schedule-updates/",
    "featured-stories": "/news/featured-stories/",
    "readouts": "/news/readouts/",
    "statements-remarks": "/news/statements-remarks/",
    "testimonies": "/news/testimonies/",
}

HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
    "Accept": "text/html,application/xhtml+xml",
}


def get_existing_slugs(category: str) -> Set[str]:
    """Get set of existing content slugs for a category."""
    slugs = set()
    
    category_dir = CONTENT_DIR / category
    if not category_dir.exists():
        return slugs
    
    for md_file in category_dir.glob("*.md"):
        if md_file.name == "_index.md":
            continue
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read(2000)
            
            # Extract URL from frontmatter
            url_match = re.search(r"^url:\s*(.+)$", content, re.MULTILINE)
            if url_match:
                url = url_match.group(1).strip().strip("'\"")
                slug = url.rstrip("/").split("/")[-1].lower()
                slugs.add(slug)
            else:
                # Use filename as fallback
                slug = md_file.stem.split("-", 3)[-1] if "-" in md_file.stem else md_file.stem
                slugs.add(slug.lower())
                
        except Exception:
            continue
    
    return slugs


def get_drupal_urls(category: str) -> Set[str]:
    """Get set of URLs from the all_tres_urls.md file for a category."""
    urls = set()
    path_prefix = CATEGORY_PATHS.get(category, f"/news/{category}/")
    
    if not URLS_FILE.exists():
        print(f"   ⚠️ URLs file not found: {URLS_FILE}")
        return urls
    
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if f"home.treasury.gov{path_prefix}" in line and "?" not in line:
                # Extract slug from URL
                match = re.search(rf"{re.escape(path_prefix)}([^/\s\"']+)", line)
                if match:
                    slug = match.group(1).lower()
                    urls.add(slug)
    
    return urls


def html_to_markdown(html_content: str) -> str:
    """Convert HTML to clean Markdown."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove scripts, styles, nav, footer
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    
    # Process headings
    heading_map = {"h1": 2, "h2": 2, "h3": 3, "h4": 3, "h5": 3, "h6": 3}
    for tag_name, target_level in heading_map.items():
        for h in soup.find_all(tag_name):
            text = h.get_text(strip=True)
            if text:
                h.replace_with(f"\n\n{'#' * target_level} {text}\n\n")
    
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
                href = f"{BASE_URL}{href}"
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
    
    return text.strip()


def scrape_page(url: str) -> Optional[dict]:
    """Scrape a single page and extract content."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract title
    title_elem = soup.find("h1") or soup.find("title")
    title = title_elem.get_text(strip=True) if title_elem else "Untitled"
    title = re.sub(r"\s*\|\s*U\.S\. Department of the Treasury$", "", title)
    
    # Extract date
    date_str = None
    
    # Try meta tag
    date_meta = soup.find("meta", {"property": "article:published_time"})
    if date_meta:
        date_str = date_meta.get("content", "")[:10]
    
    # Try date element
    if not date_str:
        date_elem = soup.find(class_=re.compile(r"date|time|published", re.I))
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            # Parse various date formats
            for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(date_text, fmt)
                    date_str = parsed.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
    
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Extract main content
    content_area = (
        soup.find("article") or 
        soup.find(class_=re.compile(r"content|body|article", re.I)) or
        soup.find("main")
    )
    
    if content_area:
        # Remove sidebars, navigation
        for elem in content_area.find_all(class_=re.compile(r"sidebar|nav|menu|footer|header", re.I)):
            elem.decompose()
        content_html = str(content_area)
    else:
        content_html = ""
    
    content_md = html_to_markdown(content_html)
    
    # Extract press release number from URL or content
    release_number = ""
    match = re.search(r"/(sb|jl|sm|tg)(\d+)$", url, re.IGNORECASE)
    if match:
        release_number = f"{match.group(1).upper()}{match.group(2)}"
    
    return {
        "title": title,
        "date": date_str,
        "content": content_md,
        "release_number": release_number,
        "url": url.replace(BASE_URL, ""),
    }


def save_content(data: dict, category: str) -> Optional[Path]:
    """Save scraped content as Hugo markdown."""
    slug = data["url"].rstrip("/").split("/")[-1]
    filename = f"{data['date']}-{slug}.md"
    
    output_dir = CONTENT_DIR / category
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    
    if filepath.exists():
        return None
    
    # Build front matter
    fm_lines = ["---"]
    
    # Escape title properly
    title = data["title"].replace('"', '\\"')
    fm_lines.append(f'title: "{title}"')
    fm_lines.append(f"date: {data['date']}")
    fm_lines.append("draft: false")
    
    if data["release_number"]:
        fm_lines.append(f"press_release_number: {data['release_number']}")
    
    fm_lines.append(f"url: {data['url']}")
    fm_lines.append("---")
    fm_lines.append("")
    
    full_content = "\n".join(fm_lines) + data["content"] + "\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    return filepath


def ensure_section_index(category: str):
    """Create section _index.md if it doesn't exist."""
    section_dir = CONTENT_DIR / category
    section_dir.mkdir(parents=True, exist_ok=True)
    
    index_file = section_dir / "_index.md"
    if not index_file.exists():
        title = category.replace("-", " ").title()
        with open(index_file, "w") as f:
            f.write(f'''---
title: "{title}"
date: {datetime.now().strftime("%Y-%m-%d")}
draft: false
type: "news"
---
''')


def main():
    parser = argparse.ArgumentParser(description="Scrape missing news content")
    parser.add_argument(
        "--category",
        choices=list(CATEGORY_PATHS.keys()),
        help="Category to scrape",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scrape all categories",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum items to scrape per category (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without saving",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    
    args = parser.parse_args()
    
    if not args.category and not args.all:
        print("Error: Must specify --category or --all")
        sys.exit(1)
    
    categories = list(CATEGORY_PATHS.keys()) if args.all else [args.category]
    
    print("🏛️  Treasury.gov Missing Content Scraper")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    total_scraped = 0
    
    for category in categories:
        print(f"\n{'=' * 60}")
        print(f"📂 Category: {category}")
        print("=" * 60)
        
        # Ensure section exists
        ensure_section_index(category)
        
        # Get existing and Drupal slugs
        existing = get_existing_slugs(category)
        drupal = get_drupal_urls(category)
        
        print(f"   Existing in Hugo: {len(existing)}")
        print(f"   Found in Drupal:  {len(drupal)}")
        
        # Find missing
        missing = drupal - existing
        print(f"   Missing:          {len(missing)}")
        
        if not missing:
            print("   ✅ All content already migrated!")
            continue
        
        # Limit to requested amount
        to_scrape = list(missing)[:args.limit]
        print(f"   Will scrape:      {len(to_scrape)}")
        
        if args.dry_run:
            print("\n   [DRY RUN] Would scrape:")
            for slug in to_scrape[:20]:
                print(f"      - {slug}")
            if len(to_scrape) > 20:
                print(f"      ... and {len(to_scrape) - 20} more")
            continue
        
        # Scrape missing content
        print(f"\n   Scraping {len(to_scrape)} items...")
        
        scraped = 0
        errors = 0
        path_prefix = CATEGORY_PATHS[category]
        
        for i, slug in enumerate(to_scrape, 1):
            url = f"{BASE_URL}{path_prefix}{slug}"
            
            print(f"   [{i}/{len(to_scrape)}] {slug}...", end=" ", flush=True)
            
            data = scrape_page(url)
            if data:
                filepath = save_content(data, category)
                if filepath:
                    print("✅")
                    scraped += 1
                else:
                    print("⏭️ (exists)")
            else:
                print("❌")
                errors += 1
            
            if args.delay > 0:
                time.sleep(args.delay)
        
        print(f"\n   ✅ Scraped {scraped} items")
        if errors:
            print(f"   ⚠️ {errors} errors")
        
        total_scraped += scraped
    
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE: {total_scraped} total items scraped")
    print(f"📁 Content saved to: {CONTENT_DIR}")


if __name__ == "__main__":
    main()
