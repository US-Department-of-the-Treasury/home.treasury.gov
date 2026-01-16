#!/usr/bin/env python3
"""
Treasury Webcast Archive Scraper

Scrapes webcast listings from Treasury.gov archive pages (2016-2024)
and generates Hugo markdown files.

Usage:
    python scripts/scrape_webcasts.py           # Scrape all years
    python scripts/scrape_webcasts.py --year 2024  # Scrape single year
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://home.treasury.gov/news/webcasts"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "news" / "webcasts"
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}


def scrape_year(year: int) -> list:
    """Scrape webcasts for a specific year."""
    url = f"{BASE_URL}/{year}"
    print(f"📥 Fetching {url}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract webcasts from USWDS card layout
    webcasts = []
    seen_urls = set()
    
    # Find all usa-card containers
    cards = soup.find_all('li', class_=re.compile('usa-card'))
    
    for card in cards:
        # Get link from card header
        link = card.find('a', href=re.compile(r'vbrick'))
        if not link:
            continue
        
        url = link.get('href', '')
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        title = link.get_text(strip=True)
        if not title or len(title) < 3:
            continue
        
        # Get date from card body
        body = card.find(class_='usa-card__body')
        date_text = ""
        time_text = ""
        
        if body:
            body_text = body.get_text(strip=True)
            # Match "Month DD, YYYY HH:MMAM/PM" or without comma
            date_match = re.search(
                r'([A-Z][a-z]+ \d{1,2},? \d{4})\s*(\d{1,2}:\d{2}\s*[AP]M)?',
                body_text
            )
            if date_match:
                date_text = date_match.group(1)
                time_text = date_match.group(2) or ""
        
        webcasts.append({
            'title': title,
            'url': url,
            'date': date_text.strip(),
            'time': time_text.strip(),
        })
    
    # Fallback: if no cards found, try direct link extraction
    if not webcasts:
        for link in soup.find_all('a', href=re.compile(r'vbrick')):
            url = link.get('href', '')
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            webcasts.append({
                'title': title,
                'url': url,
                'date': '',
                'time': '',
            })
    
    print(f"   ✅ Found {len(webcasts)} webcasts")
    return webcasts


def generate_markdown(year: int, webcasts: list) -> str:
    """Generate Hugo markdown content for a year's webcasts."""
    
    # Sort by date (most recent first)
    def parse_date(w):
        try:
            # Handle "Month DD, YYYY" or "Month DD YYYY"
            date_str = w.get('date', '').replace(',', '')
            return datetime.strptime(date_str, '%B %d %Y')
        except:
            return datetime.min
    
    sorted_webcasts = sorted(webcasts, key=parse_date, reverse=True)
    
    lines = [
        "---",
        f'title: "{year} Webcasts"',
        f"date: {year}-01-01",
        "draft: false",
        f"url: /news/webcasts/{year}",
        "---",
        "",
        f"## {year} Webcasts",
        "",
        "| Event | Date |",
        "|-------|------|",
    ]
    
    for w in sorted_webcasts:
        title = w['title']
        url = w['url']
        date = w['date']
        time = w['time']
        
        date_display = date
        if time:
            date_display = f"{date} {time}"
        
        # Escape pipes in title
        title = title.replace('|', '\\|')
        
        lines.append(f"| [{title}]({url}) | {date_display} |")
    
    lines.extend([
        "",
        "*All times Eastern.*",
        "",
        "---",
        "",
        "[← Back to Webcasts](/news/webcasts/)",
    ])
    
    return "\n".join(lines)


def save_year(year: int, content: str):
    """Save markdown file for a year."""
    filepath = CONTENT_DIR / f"{year}.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding='utf-8')
    print(f"   💾 Saved {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Treasury webcast archives")
    parser.add_argument(
        "--year",
        type=int,
        help="Scrape specific year only (default: all 2016-2024)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without saving",
    )
    
    args = parser.parse_args()
    
    print("🎬 Treasury Webcast Scraper")
    print()
    
    if args.year:
        years = [args.year]
    else:
        years = list(range(2016, 2025))  # 2016-2024
    
    total_webcasts = 0
    
    for year in years:
        webcasts = scrape_year(year)
        
        if webcasts:
            total_webcasts += len(webcasts)
            content = generate_markdown(year, webcasts)
            
            if args.dry_run:
                print(f"\n--- {year}.md preview ---")
                print(content[:500])
                print("...")
            else:
                save_year(year, content)
        
        print()
    
    print("=" * 40)
    print(f"✅ Total: {total_webcasts} webcasts across {len(years)} years")
    
    if not args.dry_run:
        print(f"\nFiles saved to: {CONTENT_DIR}")


if __name__ == "__main__":
    main()
