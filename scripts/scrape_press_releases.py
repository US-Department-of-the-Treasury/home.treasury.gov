#!/usr/bin/env python3
"""
Treasury.gov Press Releases Scraper

Scrapes press releases from home.treasury.gov and saves them as Hugo markdown files.
Focuses on the news section with proper categorization.

Usage:
    python scripts/scrape_press_releases.py [--pages 5] [--category press-releases]
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
from tqdm import tqdm

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


def get_soup(url: str) -> BeautifulSoup:
    """Fetch URL and return BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def extract_article_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract article links from a listing page."""
    links = []
    
    # Navigation/sidebar URLs to skip
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
    
    # Try different selectors for article links
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
                
                # Skip navigation links
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
    
    # Extract title from <title> tag (most reliable for Treasury site)
    title_el = soup.select_one("title")
    if title_el:
        full_title = title_el.get_text(strip=True)
        # Remove site name suffix " | U.S. Department of the Treasury"
        if " | " in full_title:
            data["title"] = full_title.split(" | ")[0].strip()
        else:
            data["title"] = full_title
    
    # Fallback to h1 if title tag doesn't have article title
    if not data["title"] or data["title"] == "U.S. Department of the Treasury":
        h1_el = soup.select_one("h1.page-title, h1.title, article h1")
        if h1_el:
            h1_text = h1_el.get_text(strip=True)
            if h1_text != "U.S. Department of the Treasury":
                data["title"] = h1_text
    
    # Extract date - try multiple sources
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
            # Try datetime attribute first
            dt = date_el.get("datetime")
            if dt:
                data["date"] = dt[:10]  # YYYY-MM-DD
                break
            # Try text content
            date_text = date_el.get_text(strip=True)
            if date_text:
                # Try to parse various date formats
                for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"]:
                    try:
                        parsed = datetime.strptime(date_text, fmt)
                        data["date"] = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            if data["date"]:
                break
    
    # If no date found, try meta tags
    if not data["date"]:
        meta_date = soup.select_one('meta[property="article:published_time"]')
        if meta_date:
            data["date"] = meta_date.get("content", "")[:10]
    
    # Extract release number
    release_el = soup.select_one(".field--name-field-release-number, .release-number")
    if release_el:
        data["release_number"] = release_el.get_text(strip=True)
    
    # Extract category from breadcrumb or URL
    breadcrumb = soup.select(".breadcrumb a, .breadcrumb-item a")
    for bc in breadcrumb:
        text = bc.get_text(strip=True).lower()
        if text in ["press releases", "statements & remarks", "readouts", "testimonies", "featured stories"]:
            data["category"] = text.replace(" & ", "-").replace(" ", "-")
            break
    
    # Fallback: extract category from URL
    if not data["category"]:
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
            # Remove unwanted elements
            for unwanted in content_el.select("script, style, .field-label"):
                unwanted.decompose()
            
            # Get HTML content
            data["content"] = str(content_el)
            
            # Create summary from first paragraph
            first_p = content_el.select_one("p")
            if first_p:
                data["summary"] = first_p.get_text(strip=True)[:300]
            break
    
    return data


def html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown."""
    soup = BeautifulSoup(html, "lxml")
    
    # Simple conversion rules
    # Convert headers
    for i in range(1, 7):
        for h in soup.find_all(f"h{i}"):
            h.replace_with(f"\n{'#' * i} {h.get_text(strip=True)}\n")
    
    # Convert paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n{text}\n")
    
    # Convert links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            a.replace_with(f"[{text}]({href})")
    
    # Convert lists
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
    
    # Convert bold/italic
    for strong in soup.find_all(["strong", "b"]):
        strong.replace_with(f"**{strong.get_text(strip=True)}**")
    
    for em in soup.find_all(["em", "i"]):
        em.replace_with(f"*{em.get_text(strip=True)}*")
    
    # Get text and clean up
    text = soup.get_text()
    
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def create_slug(title: str, date: str) -> str:
    """Create a URL-safe slug from title and date."""
    # Clean title
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')[:80]
    
    # Add date prefix for uniqueness
    if date:
        return f"{date}-{slug}"
    return slug


def save_article(data: dict, category: str):
    """Save article as Hugo markdown file."""
    if not data["title"]:
        return None
    
    # Create category directory
    cat_dir = CONTENT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    # Create slug and filename
    slug = create_slug(data["title"], data["date"])
    filename = f"{slug}.md"
    filepath = cat_dir / filename
    
    # Convert content to markdown
    md_content = html_to_markdown(data["content"]) if data["content"] else ""
    
    # Build front matter
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
    
    # Format front matter as YAML
    fm_lines = ["---"]
    for key, value in front_matter.items():
        if isinstance(value, str):
            # Escape quotes in strings
            value = value.replace('"', '\\"')
            fm_lines.append(f'{key}: "{value}"')
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm_lines.append("")
    
    # Combine front matter and content
    full_content = "\n".join(fm_lines) + md_content
    
    # Write file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    return filepath


def scrape_category(category: str, max_pages: int = 5, delay: float = 1.0):
    """Scrape all articles from a news category."""
    if category not in NEWS_CATEGORIES:
        print(f"❌ Unknown category: {category}")
        return []
    
    base_path = NEWS_CATEGORIES[category]
    url = f"{BASE_URL}{base_path}"
    
    print(f"\n📂 Scraping: {category}")
    print(f"   URL: {url}")
    
    all_links = []
    page = 1
    
    # Collect all article links
    while url and page <= max_pages:
        print(f"   Page {page}...")
        try:
            soup = get_soup(url)
            links = extract_article_links(soup, BASE_URL)
            
            if not links:
                print(f"   No more articles found")
                break
            
            all_links.extend(links)
            url = get_next_page_url(soup, BASE_URL)
            page += 1
            time.sleep(delay)
            
        except Exception as e:
            print(f"   ⚠️ Error on page {page}: {e}")
            break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    print(f"   Found {len(unique_links)} unique articles")
    
    # Scrape each article
    saved = []
    for link in tqdm(unique_links, desc=f"   Scraping {category}"):
        try:
            soup = get_soup(link)
            data = extract_article_data(soup, link)
            
            filepath = save_article(data, category)
            if filepath:
                saved.append(filepath)
            
            time.sleep(delay)
            
        except Exception as e:
            print(f"\n   ⚠️ Error scraping {link}: {e}")
    
    return saved


def create_section_index(category: str, title: str):
    """Create the _index.md file for a news category."""
    cat_dir = CONTENT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    index_content = f"""---
title: "{title}"
date: {datetime.now().strftime("%Y-%m-%d")}
draft: false
type: "news"
---
"""
    
    with open(cat_dir / "_index.md", "w") as f:
        f.write(index_content)


def main():
    parser = argparse.ArgumentParser(description="Scrape Treasury.gov press releases")
    parser.add_argument("--pages", type=int, default=5, help="Max pages to scrape per category")
    parser.add_argument("--category", default="all", help="Category to scrape (or 'all')")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests")
    args = parser.parse_args()
    
    print("🏛️  Treasury.gov Press Releases Scraper")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Output: {CONTENT_DIR}")
    
    # Create main news index
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONTENT_DIR / "_index.md", "w") as f:
        f.write('---\ntitle: "News"\ndate: 2024-01-01\n---\n')
    
    # Determine which categories to scrape
    if args.category == "all":
        categories = list(NEWS_CATEGORIES.keys())
    else:
        categories = [args.category]
    
    total_saved = 0
    
    for category in categories:
        # Create section index
        title = category.replace("-", " ").title()
        create_section_index(category, title)
        
        # Scrape category
        saved = scrape_category(category, max_pages=args.pages, delay=args.delay)
        total_saved += len(saved)
        print(f"   ✅ Saved {len(saved)} articles to content/news/{category}/")
    
    print("\n" + "=" * 50)
    print(f"✅ COMPLETE: {total_saved} total articles saved")
    print(f"📁 Content saved to: {CONTENT_DIR}")


if __name__ == "__main__":
    main()
