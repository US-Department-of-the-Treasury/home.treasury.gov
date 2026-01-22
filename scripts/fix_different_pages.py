#!/usr/bin/env python3
"""
Fix Different Pages

Fetches fresh content from the live Treasury site for pages that have
content differences and updates the Hugo markdown files.

Usage:
    python3 scripts/fix_different_pages.py --dry-run
    python3 scripts/fix_different_pages.py --limit 50
    python3 scripts/fix_different_pages.py --min-similarity 0.0 --max-similarity 0.5
    python3 scripts/fix_different_pages.py
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
from bs4 import BeautifulSoup, NavigableString, Tag


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
            response = requests.get(page_url, headers=HTML_HEADERS, timeout=TIMEOUT)
            
            if response.status_code == 404:
                return None
            
            if response.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_DELAY * (attempt + 1)
                log(f" {response.status_code}, retrying...")
                time.sleep(delay)
                continue
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                time.sleep(delay)
            else:
                return None
    
    return None


def element_to_markdown(element) -> str:
    """Recursively convert an HTML element to Markdown, preserving inline formatting."""
    if isinstance(element, NavigableString):
        text = str(element)
        text = re.sub(r'\s+', ' ', text)
        return text
    
    if not isinstance(element, Tag):
        return ""
    
    tag_name = element.name.lower() if element.name else ""
    
    if tag_name in ["script", "style", "head", "meta", "link"]:
        return ""
    
    children_text = ""
    for child in element.children:
        children_text += element_to_markdown(child)
    
    if tag_name in ["strong", "b"]:
        inner = children_text.strip()
        if inner:
            return f"**{inner}**"
        return ""
    
    if tag_name in ["em", "i"]:
        inner = children_text.strip()
        if inner and "Archived Content" not in inner:
            return f"*{inner}*"
        return ""
    
    if tag_name == "a":
        href = element.get("href", "")
        inner = children_text.strip()
        if href and inner:
            if href.startswith("/"):
                href = f"https://home.treasury.gov{href}"
            return f"[{inner}]({href})"
        return inner
    
    if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(tag_name[1])
        target_level = max(2, level)
        inner = children_text.strip()
        if inner:
            return f"\n\n{'#' * target_level} {inner}\n\n"
        return ""
    
    if tag_name == "p":
        inner = children_text.strip()
        if inner:
            return f"\n\n{inner}\n\n"
        return ""
    
    if tag_name == "br":
        return " "
    
    if tag_name == "li":
        return children_text.strip()
    
    if tag_name == "ul":
        items = []
        for li in element.find_all("li", recursive=False):
            li_text = element_to_markdown(li).strip()
            if li_text:
                items.append(f"- {li_text}")
        if items:
            return "\n\n" + "\n".join(items) + "\n\n"
        return ""
    
    if tag_name == "ol":
        items = []
        start = 1
        try:
            start_attr = element.get("start", 1)
            if start_attr:
                start = int(start_attr)
        except:
            start = 1
        for idx, li in enumerate(element.find_all("li", recursive=False), start):
            li_text = element_to_markdown(li).strip()
            if li_text:
                items.append(f"{idx}. {li_text}")
        if items:
            return "\n\n" + "\n".join(items) + "\n\n"
        return ""
    
    if tag_name == "table":
        return f"\n\n{str(element)}\n\n"
    
    if tag_name == "img":
        src = element.get("src", "")
        alt = element.get("alt", "")
        if src and "spacer" not in src.lower():
            if src.startswith("/"):
                src = f"https://home.treasury.gov{src}"
            return f"\n\n![{alt}]({src})\n\n"
        return ""
    
    if tag_name == "blockquote":
        inner = children_text.strip()
        if inner:
            lines = inner.split("\n")
            quoted = "\n".join(f"> {line}" for line in lines if line.strip())
            return f"\n\n{quoted}\n\n"
        return ""
    
    if tag_name == "div":
        classes = element.get("class", [])
        if "field--name-field-news-body" in classes:
            return children_text
        return children_text
    
    return children_text


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    for tag in soup.find_all(["script", "style", "head", "meta", "link", "nav", "header", "footer"]):
        tag.decompose()
    
    for em in soup.find_all(["em", "i"]):
        if em.get_text(strip=True) == "(Archived Content)":
            parent = em.parent
            em.decompose()
            if parent and parent.name == "p" and not parent.get_text(strip=True):
                parent.decompose()
    
    markdown = element_to_markdown(soup)
    markdown = html.unescape(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r" +", " ", markdown)
    markdown = re.sub(r"\n +", "\n", markdown)
    markdown = re.sub(r" +\n", "\n", markdown)
    markdown = re.sub(r"^\s+", "", markdown)
    markdown = re.sub(r"\s+$", "", markdown)
    
    return markdown.strip()


def extract_press_release_data(html_content: str, url_path: str) -> dict:
    """Extract press release metadata and content from HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    main = soup.find(id="main-content")
    
    # Extract title
    title = ""
    if main:
        title_field = main.select_one(".field--name-title")
        if title_field:
            title = title_field.get_text(strip=True)
    
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    
    # Extract publication date
    pub_date = None
    if main:
        date_field = main.select_one(".field--name-field-news-publication-date time")
        if date_field and date_field.get("datetime"):
            pub_date = date_field.get("datetime")[:10]
    
    # Extract body content
    body_html = ""
    if main:
        body_field = main.select_one(".field--name-field-news-body")
        if body_field:
            body_html = str(body_field)
    
    # Convert to markdown
    body_md = html_to_markdown(body_html)
    
    return {
        "title": title,
        "date": pub_date,
        "body_html": body_html,
        "body_md": body_md,
    }


def find_markdown_file(slug: str, content_dir: Path) -> Optional[Path]:
    """Find the markdown file for a given slug."""
    matches = list(content_dir.glob(f"*{slug}.md"))
    if matches:
        return matches[0]
    
    # Try case-insensitive
    for f in content_dir.iterdir():
        if f.suffix == ".md" and slug.lower() in f.stem.lower():
            return f
    
    return None


def extract_frontmatter(content: str) -> tuple:
    """Extract frontmatter and body from markdown file."""
    if not content.startswith("---"):
        return "", content
    
    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = "---" + parts[1] + "---"
        body = parts[2].strip()
        return frontmatter, body
    
    return "", content


def main():
    parser = argparse.ArgumentParser(
        description="Fix pages with content differences",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="staging/pages_to_fix.json",
        help="Path to pages_to_fix.json",
    )
    parser.add_argument(
        "--content-dir",
        type=str,
        default="content/news/press-releases",
        help="Content directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of pages to process",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="Minimum similarity to process (0.0-1.0)",
    )
    parser.add_argument(
        "--max-similarity",
        type=float,
        default=1.0,
        help="Maximum similarity to process (0.0-1.0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds",
    )
    
    args = parser.parse_args()
    
    workspace = Path(__file__).parent.parent
    input_path = workspace / args.input_file
    content_dir = workspace / args.content_dir
    
    log("=" * 70)
    log("FIX DIFFERENT PAGES")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    log()
    
    # Load pages to fix
    log(f"[1/3] LOADING PAGES TO FIX")
    log(f"      Input: {input_path}")
    
    if not input_path.exists():
        log(f"      ERROR: File not found!")
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    pages = data.get("pages", [])
    
    # Filter by similarity range
    pages = [p for p in pages 
             if args.min_similarity <= p.get("similarity", 0) <= args.max_similarity]
    
    log(f"      Total in file: {data.get('total', 0)}")
    log(f"      After filtering ({args.min_similarity:.0%}-{args.max_similarity:.0%}): {len(pages)}")
    
    if args.limit:
        pages = pages[:args.limit]
        log(f"      Limited to: {len(pages)}")
    
    log()
    
    # Process each page
    log(f"[2/3] FETCHING AND UPDATING PAGES")
    log("-" * 70)
    
    updated = 0
    skipped = 0
    errors = 0
    not_found = 0
    
    for i, page in enumerate(pages, 1):
        url = page.get("url", "")
        similarity = page.get("similarity", 0)
        slug = url.rstrip("/").split("/")[-1]
        
        log()
        log(f"  [{i}/{len(pages)}] {url} ({similarity:.1%} similar)")
        
        # Find existing markdown file
        md_file = find_markdown_file(slug, content_dir)
        
        if not md_file:
            log(f"      SKIP: No markdown file found for {slug}")
            not_found += 1
            continue
        
        log(f"      File: {md_file.name}")
        
        if args.dry_run:
            log(f"      DRY RUN: Would fetch and update")
            updated += 1
            continue
        
        # Fetch fresh content
        log(f"      Fetching...", end="")
        html_content = fetch_page(url)
        
        if not html_content:
            log(f" FAILED")
            errors += 1
            continue
        
        log(f" OK")
        
        # Extract data
        page_data = extract_press_release_data(html_content, url)
        
        if not page_data["body_md"]:
            log(f"      SKIP: No body content extracted")
            skipped += 1
            continue
        
        log(f"      Title: {page_data['title'][:50]}..." if page_data['title'] else "      Title: (none)")
        log(f"      Body: {len(page_data['body_md'])} chars")
        
        # Read existing file
        existing_content = md_file.read_text(encoding="utf-8")
        frontmatter, old_body = extract_frontmatter(existing_content)
        
        # Create updated content
        new_content = f"{frontmatter}\n\n{page_data['body_md']}\n"
        
        # Write updated file
        md_file.write_text(new_content, encoding="utf-8")
        log(f"      UPDATED: {md_file.name}")
        updated += 1
        
        # Delay between requests
        if i < len(pages) and args.delay > 0:
            time.sleep(args.delay)
    
    log()
    log("-" * 70)
    
    # Summary
    log(f"[3/3] SUMMARY")
    log("=" * 70)
    log(f"  Total processed: {len(pages)}")
    log(f"  Updated: {updated}")
    log(f"  Skipped: {skipped}")
    log(f"  Not found: {not_found}")
    log(f"  Errors: {errors}")
    
    if args.dry_run:
        log()
        log("  NOTE: This was a DRY RUN. No files were changed.")
    
    log()


if __name__ == "__main__":
    main()
