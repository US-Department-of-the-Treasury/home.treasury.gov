#!/usr/bin/env python3
"""
Treasury.gov JSON API News Scraper

Fast scraper using the Drupal JSON API to fetch news content.
Significantly faster than HTML scraping (~50 items/second vs ~6 items/minute).

Usage:
    python scripts/scrape_jsonapi_news.py --category press-releases --limit 100
    python scripts/scrape_jsonapi_news.py --category all --limit 500
    python scripts/scrape_jsonapi_news.py --category press-releases --since 2026-01-01

Categories:
    press-releases, featured-stories, statements-remarks, readouts, testimonies
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://home.treasury.gov/jsonapi/node/news"
DEFAULT_CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"
CONTENT_DIR = DEFAULT_CONTENT_DIR  # Can be overridden by --output-dir
TIMEOUT = 30

# News category mapping (name -> UUID from taxonomy_term/news_category)
# To refresh these UUIDs: curl -s "https://home.treasury.gov/jsonapi/taxonomy_term/news_category"
NEWS_CATEGORIES = {
    "press-releases": "cf77c794-0050-49b5-88cd-4b9382644cdf",
    "featured-stories": "429abc81-2e6f-4b53-bce2-c00a50647848",
    "statements-remarks": "f00aa509-9bd9-4709-a492-2b91c494c08d",
    "readouts": "f80b30aa-2c3b-449e-bdd0-beb4b9140da6",
    "testimonies": "03e1010e-a191-4299-abf0-a58781d1eb33",
}

# Reverse mapping for lookups
CATEGORY_UUID_TO_SLUG = {v: k for k, v in NEWS_CATEGORIES.items()}

HEADERS = {
    "Accept": "application/vnd.api+json",
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown with 508-compliant heading hierarchy.
    
    Ensures headings start at H2 (since H1 is reserved for page title) and
    maintains proper sequential hierarchy (H2 → H3 → H4, no skips).
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Process headers - shift all up to ensure proper hierarchy
    # Content headings should be H2+ (H1 is page title in Hugo template)
    # H1 in content → H2, H2 → H2, H3 → H3, H4 → H3, etc.
    heading_map = {
        "h1": 2,  # H1 in content becomes H2
        "h2": 2,  # H2 stays H2
        "h3": 3,  # H3 stays H3
        "h4": 3,  # H4 becomes H3 (avoid deep nesting)
        "h5": 3,  # H5 becomes H3
        "h6": 3,  # H6 becomes H3
    }
    
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
            # Make relative URLs absolute
            if href.startswith("/"):
                href = f"https://home.treasury.gov{href}"
            a.replace_with(f"[{text}]({href})")
        elif text:
            a.replace_with(text)
    
    # Unordered lists
    for ul in soup.find_all("ul"):
        items = []
        for li in ul.find_all("li", recursive=False):
            li_text = li.get_text(strip=True)
            items.append(f"- {li_text}")
        ul.replace_with("\n" + "\n".join(items) + "\n")
    
    # Ordered lists
    for ol in soup.find_all("ol"):
        items = []
        for idx, li in enumerate(ol.find_all("li", recursive=False), 1):
            li_text = li.get_text(strip=True)
            items.append(f"{idx}. {li_text}")
        ol.replace_with("\n" + "\n".join(items) + "\n")
    
    # Paragraphs - add spacing
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n\n{text}\n\n")
    
    # Line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    # Get text and clean up
    text = soup.get_text()
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Multiple newlines -> double
    text = re.sub(r" +", " ", text)  # Multiple spaces -> single
    text = re.sub(r"\n +", "\n", text)  # Leading spaces on lines
    
    # Fix spacing around bold/italic (add space after ** or * if followed by letter)
    text = re.sub(r"\*\*([^*]+)\*\*([a-zA-Z])", r"**\1** \2", text)
    text = re.sub(r"\*([^*]+)\*([a-zA-Z])", r"*\1* \2", text)
    
    return text.strip()


def extract_release_number(path_alias: str) -> str:
    """Extract release number from path alias like /news/press-releases/sb0357."""
    if not path_alias:
        return ""
    
    match = re.search(r"/(sb|jl|sm)(\d+)$", path_alias, re.IGNORECASE)
    if match:
        prefix = match.group(1).upper()
        number = match.group(2)
        return f"{prefix}{number}"
    return ""


def create_slug(path_alias: str) -> str:
    """Create filename slug from path alias."""
    if not path_alias:
        return "untitled"
    
    # Extract the last part of the path
    slug = path_alias.rstrip("/").split("/")[-1]
    
    # Clean up
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    
    return slug or "untitled"


def find_existing_content(content_dir: Path) -> dict:
    """Build index of existing content for duplicate detection.
    
    Returns:
        Dictionary with multiple indexes:
        - 'urls': set of URL slugs
        - 'release_numbers': set of press release numbers
        - 'files': dict of filepath -> (date, slug)
    """
    index = {
        "urls": set(),
        "release_numbers": set(),
        "files": {},
    }
    
    for category_dir in content_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        for md_file in category_dir.glob("*.md"):
            if md_file.name == "_index.md":
                continue
            
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read(2000)  # Only read front matter
                
                # Extract URL
                url_match = re.search(r"^url:\s*(.+)$", content, re.MULTILINE)
                if url_match:
                    url = url_match.group(1).strip().strip("'\"")
                    slug = url.rstrip("/").split("/")[-1].lower()
                    index["urls"].add(slug)
                
                # Extract press release number
                pr_match = re.search(r"^press_release_number:\s*(.+)$", content, re.MULTILINE)
                if pr_match:
                    pr_num = pr_match.group(1).strip().upper()
                    index["release_numbers"].add(pr_num)
                
                # Track file
                index["files"][str(md_file)] = md_file.stem
                
            except Exception:
                continue
    
    return index


def is_duplicate(item: dict, existing_index: dict) -> Tuple[bool, str]:
    """Check if an item is a duplicate of existing content.
    
    Returns:
        Tuple of (is_duplicate, reason)
    """
    attrs = item.get("attributes", {})
    
    # Check URL slug
    path = attrs.get("path", {})
    alias = path.get("alias", "") if isinstance(path, dict) else ""
    if alias:
        slug = alias.rstrip("/").split("/")[-1].lower()
        if slug in existing_index["urls"]:
            return True, f"URL slug '{slug}' already exists"
    
    # Check press release number
    release_num = extract_release_number(alias)
    if release_num and release_num.upper() in existing_index["release_numbers"]:
        return True, f"Press release {release_num} already exists"
    
    return False, ""


def fetch_news_items(
    category: str = None,
    limit: int = 100,
    since_date: str = None,
    path_filter: str = None,
) -> list:
    """Fetch news items from the JSON API.
    
    Args:
        category: Filter by Drupal category (may not match URL path)
        limit: Maximum items to fetch
        since_date: Only fetch items since this date (YYYY-MM-DD)
        path_filter: Filter by URL path prefix (e.g., '/news/press-releases/')
    """
    items = []
    
    # Build base URL with sorting
    url = f"{BASE_URL}?sort=-field_news_publication_date"
    
    # Add category filter if specified (and not using path filter)
    if category and category in NEWS_CATEGORIES and not path_filter:
        category_uuid = NEWS_CATEGORIES[category]
        url += f"&filter[field_news_news_category.id]={category_uuid}"
    
    # Add date filter if specified
    if since_date:
        url += f"&filter[field_news_publication_date][condition][path]=field_news_publication_date"
        url += f"&filter[field_news_publication_date][condition][operator]=%3E%3D"
        url += f"&filter[field_news_publication_date][condition][value]={since_date}"
    
    # Note: path filtering is done client-side after fetch
    # The API doesn't reliably support path.alias filtering
    
    # Pagination
    page_size = min(50, limit)
    url += f"&page%5Blimit%5D={page_size}"
    
    print(f"📡 Fetching news from JSON API...")
    if category and not path_filter:
        print(f"   Category: {category}")
    if path_filter:
        print(f"   Path filter: {path_filter}")
    if since_date:
        print(f"   Since: {since_date}")
    print(f"   Limit: {limit}")
    
    page = 0
    while len(items) < limit:
        page += 1
        print(f"   Page {page}...", end=" ", flush=True)
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            page_items = data.get("data", [])
            if not page_items:
                print("(empty)")
                break
            
            # Filter by path if specified (client-side filtering)
            if path_filter:
                filtered = []
                for item in page_items:
                    attrs = item.get("attributes", {})
                    path = attrs.get("path", {})
                    alias = path.get("alias", "") if isinstance(path, dict) else ""
                    if path_filter in alias:
                        filtered.append(item)
                page_items = filtered
            
            items.extend(page_items)
            print(f"{len(page_items)} items (total: {len(items)})")
            
            # Check for next page
            links = data.get("links", {})
            next_link = links.get("next")
            if next_link:
                url = next_link.get("href") if isinstance(next_link, dict) else next_link
            else:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"\n   ⚠️ Error: {e}")
            break
    
    # Trim to limit
    return items[:limit]


def determine_category(item: dict, use_title_analysis: bool = True) -> str:
    """Determine the category slug from the item's relationships and content.
    
    Priority order:
    1. Drupal taxonomy category (most reliable)
    2. Title keyword analysis (catches miscategorized content)
    3. URL path analysis (fallback)
    
    Args:
        item: The JSON API item
        use_title_analysis: If True, also analyze title for category hints
    """
    attrs = item.get("attributes", {})
    title = attrs.get("title", "").lower()
    
    # Method 1: Check Drupal taxonomy category (highest priority)
    rels = item.get("relationships", {})
    cat_rel = rels.get("field_news_news_category", {})
    cat_data = cat_rel.get("data", {})
    
    drupal_category = None
    if cat_data:
        cat_uuid = cat_data.get("id", "")
        drupal_category = CATEGORY_UUID_TO_SLUG.get(cat_uuid)
    
    # Method 2: Title keyword analysis (catches miscategorized content)
    title_category = None
    if use_title_analysis:
        if title.startswith("readout"):
            title_category = "readouts"
        elif (title.startswith("statement by") or 
              title.startswith("joint statement") or
              title.startswith("remarks by")):
            title_category = "statements-remarks"
        elif title.startswith("testimony") or "testifies" in title:
            title_category = "testimonies"
    
    # Method 3: URL path analysis (fallback)
    path = attrs.get("path", {})
    alias = path.get("alias", "") if isinstance(path, dict) else ""
    
    path_category = None
    if "/featured-stories/" in alias:
        path_category = "featured-stories"
    elif "/readouts/" in alias:
        path_category = "readouts"
    elif "/statements-remarks/" in alias:
        path_category = "statements-remarks"
    elif "/testimonies/" in alias:
        path_category = "testimonies"
    elif "/press-releases/" in alias:
        path_category = "press-releases"
    
    # Priority: title_category > drupal_category > path_category
    # Title analysis catches items that Drupal miscategorized
    if title_category:
        return title_category
    if drupal_category:
        return drupal_category
    if path_category:
        return path_category
    
    return "press-releases"  # Default fallback


def save_item(
    item: dict,
    category_override: str = None,
    skip_existing: bool = True,
    existing_index: dict = None,
    respect_drupal_url: bool = True,
) -> Optional[Path]:
    """Save a news item as a Hugo markdown file with 508-compliant formatting.

    Args:
        item: The JSON API item data
        category_override: Force output to specific category folder
        skip_existing: If True, don't overwrite existing files
        existing_index: Pre-built index for fast duplicate detection
        respect_drupal_url: If True, keep original Drupal URL; if False, use Hugo category
        
    Returns:
        Path to saved file, or None if skipped
    """
    attrs = item.get("attributes", {})
    
    # Extract fields
    title = attrs.get("title", "Untitled")
    
    # Get publication date
    pub_date = attrs.get("field_news_publication_date", "")
    if pub_date:
        # Parse ISO date and extract YYYY-MM-DD
        date_str = pub_date[:10]
    else:
        # Fallback to created date
        created = attrs.get("created", "")
        date_str = created[:10] if created else datetime.now().strftime("%Y-%m-%d")
    
    # Get body content
    body_field = attrs.get("field_news_body", {})
    if isinstance(body_field, dict):
        body_html = body_field.get("value", "")
    else:
        body_html = str(body_field) if body_field else ""
    
    # Convert to markdown
    body_md = html_to_markdown(body_html)
    
    # Get path alias for URL and release number
    path = attrs.get("path", {})
    alias = path.get("alias", "") if isinstance(path, dict) else ""
    
    release_number = extract_release_number(alias)
    slug = create_slug(alias)
    
    # Determine category - use smart detection if no override
    category = category_override or determine_category(item, use_title_analysis=True)
    
    # Check for duplicates using index if provided
    if existing_index:
        is_dup, reason = is_duplicate(item, existing_index)
        if is_dup:
            return None  # Skip duplicates silently
    
    # Create filename: YYYY-MM-DD-slug.md
    filename = f"{date_str}-{slug}.md"
    
    # Create output directory
    output_dir = CONTENT_DIR / category
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    
    # Build front matter
    front_matter = {
        "title": title,
        "date": date_str,
        "draft": False,
    }
    
    if release_number:
        front_matter["press_release_number"] = release_number
    
    if alias:
        front_matter["url"] = alias
    
    # Format front matter as YAML
    fm_lines = ["---"]
    for key, value in front_matter.items():
        if isinstance(value, bool):
            fm_lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, str):
            # Escape quotes and handle multiline
            if "\n" in value or '"' in value or ":" in value:
                escaped = value.replace("'", "''")
                fm_lines.append(f"{key}: '{escaped}'")
            else:
                fm_lines.append(f"{key}: {value}")
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm_lines.append("")
    
    # Combine front matter and content
    full_content = "\n".join(fm_lines) + body_md + "\n"
    
    if skip_existing and filepath.exists():
        return None

    # Write file (overwrite allowed if skip_existing=False)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Treasury.gov news via JSON API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape latest 100 press releases (by Drupal category)
  python scripts/scrape_jsonapi_news.py --category press-releases --limit 100

  # Scrape ALL items under /news/press-releases/ URL (any category)
  python scripts/scrape_jsonapi_news.py --path-filter /news/press-releases/ --limit 100

  # Scrape all news since January 2026
  python scripts/scrape_jsonapi_news.py --category all --since 2026-01-01

  # Scrape featured stories
  python scripts/scrape_jsonapi_news.py --category featured-stories --limit 50

Categories:
  press-releases, featured-stories, statements-remarks, readouts, testimonies, all
        """,
    )
    parser.add_argument(
        "--category",
        default=None,
        choices=list(NEWS_CATEGORIES.keys()) + ["all"],
        help="Filter by Drupal category (default: none)",
    )
    parser.add_argument(
        "--path-filter",
        type=str,
        help="Filter by URL path prefix (e.g., /news/press-releases/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of items to fetch (default: 100)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Only fetch items since this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-category",
        type=str,
        help="Override output category folder (default: auto-detect from path)",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Overwrite existing files if present (default: false)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without saving",
    )
    parser.add_argument(
        "--no-recategorize",
        action="store_true",
        help="Don't recategorize based on title analysis (use Drupal category as-is)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including recategorization decisions",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for content (default: content/news/)",
    )
    
    args = parser.parse_args()
    
    # Override output directory if specified
    global CONTENT_DIR
    if args.output_dir:
        CONTENT_DIR = Path(args.output_dir)
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Validate arguments
    if not args.category and not args.path_filter:
        print("Error: Must specify either --category or --path-filter")
        sys.exit(1)
    
    print("🏛️  Treasury.gov JSON API News Scraper")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Output: {CONTENT_DIR}")
    print()
    
    # Build index of existing content for duplicate detection
    print("📊 Building content index for duplicate detection...")
    existing_index = find_existing_content(CONTENT_DIR)
    print(f"   Found {len(existing_index['urls'])} existing URLs")
    print(f"   Found {len(existing_index['release_numbers'])} existing press release numbers")
    print()
    
    total_saved = 0
    total_duplicates = 0
    
    # Path filter mode: fetch all matching items regardless of category
    if args.path_filter:
        print(f"\n{'=' * 50}")
        print(f"📂 Path filter: {args.path_filter}")
        print("=" * 50)
        
        # Determine output category from path or override
        if args.output_category:
            output_category = args.output_category
        elif "/press-releases/" in args.path_filter:
            output_category = "press-releases"
        elif "/featured-stories/" in args.path_filter:
            output_category = "featured-stories"
        elif "/readouts/" in args.path_filter:
            output_category = "readouts"
        elif "/testimonies/" in args.path_filter:
            output_category = "testimonies"
        else:
            output_category = "press-releases"  # Default
        
        # Create section index if needed
        section_dir = CONTENT_DIR / output_category
        section_dir.mkdir(parents=True, exist_ok=True)
        index_file = section_dir / "_index.md"
        if not index_file.exists():
            title = output_category.replace("-", " ").title()
            with open(index_file, "w") as f:
                f.write(f'---\ntitle: "{title}"\ndate: {datetime.now().strftime("%Y-%m-%d")}\ndraft: false\ntype: "news"\n---\n')
        
        # Fetch items by path
        items = fetch_news_items(
            limit=args.limit,
            since_date=args.since,
            path_filter=args.path_filter,
        )
        
        if items:
            print(f"\n💾 Saving {len(items)} items...")
            
            if args.dry_run:
                for item in items[:10]:
                    attrs = item.get("attributes", {})
                    title = attrs.get("title", "")[:60]
                    date = attrs.get("field_news_publication_date", "")[:10]
                    print(f"   [DRY RUN] [{date}] {title}")
                if len(items) > 10:
                    print(f"   ... and {len(items) - 10} more")
            else:
                saved = 0
                skipped = 0
                recategorized = 0
                for item in items:
                    try:
                        # Determine actual category (may differ from output_category)
                        actual_category = determine_category(item, use_title_analysis=True)
                        if actual_category != output_category:
                            recategorized += 1
                        
                        filepath = save_item(
                            item,
                            category_override=actual_category,  # Use detected category
                            skip_existing=not args.overwrite_existing,
                            existing_index=existing_index,
                        )
                        if filepath is None:
                            skipped += 1
                        else:
                            saved += 1
                            # Update index with new item
                            attrs = item.get("attributes", {})
                            path = attrs.get("path", {})
                            alias = path.get("alias", "") if isinstance(path, dict) else ""
                            if alias:
                                slug = alias.rstrip("/").split("/")[-1].lower()
                                existing_index["urls"].add(slug)
                            release_num = extract_release_number(alias)
                            if release_num:
                                existing_index["release_numbers"].add(release_num.upper())
                    except Exception as e:
                        attrs = item.get("attributes", {})
                        title = attrs.get("title", "unknown")[:40]
                        print(f"   ⚠️ Error saving '{title}': {e}")
                
                print(f"   ✅ Saved {saved} new items")
                if recategorized:
                    print(f"   🔄 Recategorized {recategorized} items based on title analysis")
                if skipped:
                    print(f"   ⏭️ Skipped {skipped} existing/duplicate items")
                total_saved += saved
        else:
            print(f"   No items found matching {args.path_filter}")
    
    # Category mode: fetch by Drupal category
    elif args.category:
        if args.category == "all":
            categories = list(NEWS_CATEGORIES.keys())
        else:
            categories = [args.category]
        
        for category in categories:
            print(f"\n{'=' * 50}")
            print(f"📂 Category: {category}")
            print("=" * 50)
            
            # Create section index if needed
            section_dir = CONTENT_DIR / category
            section_dir.mkdir(parents=True, exist_ok=True)
            index_file = section_dir / "_index.md"
            if not index_file.exists():
                title = category.replace("-", " ").title()
                with open(index_file, "w") as f:
                    f.write(f'---\ntitle: "{title}"\ndate: {datetime.now().strftime("%Y-%m-%d")}\ndraft: false\ntype: "news"\n---\n')
            
            # Fetch items
            items = fetch_news_items(
                category=category,
                limit=args.limit,
                since_date=args.since,
            )
            
            if not items:
                print(f"   No items found for {category}")
                continue
            
            print(f"\n💾 Saving {len(items)} items...")
            
            if args.dry_run:
                for item in items[:10]:
                    attrs = item.get("attributes", {})
                    title = attrs.get("title", "")[:60]
                    date = attrs.get("field_news_publication_date", "")[:10]
                    print(f"   [DRY RUN] [{date}] {title}")
                if len(items) > 10:
                    print(f"   ... and {len(items) - 10} more")
                continue
            
            saved = 0
            skipped = 0
            recategorized = 0
            for item in items:
                try:
                    # Determine actual category based on content analysis
                    actual_category = determine_category(item, use_title_analysis=True)
                    if actual_category != category:
                        recategorized += 1
                    
                    filepath = save_item(
                        item,
                        category_override=actual_category,  # Use detected category
                        skip_existing=not args.overwrite_existing,
                        existing_index=existing_index,
                    )
                    if filepath is None:
                        skipped += 1
                    else:
                        saved += 1
                        # Update index with new item
                        attrs = item.get("attributes", {})
                        path = attrs.get("path", {})
                        alias = path.get("alias", "") if isinstance(path, dict) else ""
                        if alias:
                            slug = alias.rstrip("/").split("/")[-1].lower()
                            existing_index["urls"].add(slug)
                        release_num = extract_release_number(alias)
                        if release_num:
                            existing_index["release_numbers"].add(release_num.upper())
                except Exception as e:
                    attrs = item.get("attributes", {})
                    title = attrs.get("title", "unknown")[:40]
                    print(f"   ⚠️ Error saving '{title}': {e}")
            
            print(f"   ✅ Saved {saved} new items")
            if recategorized:
                print(f"   🔄 Recategorized {recategorized} items based on title analysis")
            if skipped:
                print(f"   ⏭️ Skipped {skipped} existing/duplicate items")
            total_saved += saved
    
    print("\n" + "=" * 50)
    print(f"✅ COMPLETE: {total_saved} total items saved")
    print(f"📁 Content saved to: {CONTENT_DIR}")


if __name__ == "__main__":
    main()
