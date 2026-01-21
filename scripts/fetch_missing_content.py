#!/usr/bin/env python3
"""
Fetch Missing Content from Treasury JSON API

Reads text_comparison.json to find pages with missing content,
then prepares bulk API requests and fetches the original content.

Usage:
    python3 scripts/fetch_missing_content.py
    python3 scripts/fetch_missing_content.py --output-file staging/missing_content.json
    python3 scripts/fetch_missing_content.py --prepare-bulk-urls
    python3 scripts/fetch_missing_content.py --fetch

Output Files:
    staging/missing_content.json     - Full analysis with missing text snippets
    staging/bulk_fetch_urls.txt      - URLs ready for bulk API fetching
    staging/missing_items_flat.json  - Flat array of all missing items
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import time


def log(msg: str = "", end: str = "\n"):
    """Print with immediate flush for real-time output."""
    print(msg, end=end, flush=True)

# Configuration
BASE_URL = "https://home.treasury.gov"
JSONAPI_BASE = f"{BASE_URL}/jsonapi/node/news"
TIMEOUT = 30
MAX_WORKERS = 1  # Sequential to avoid rate limiting
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds (increased for 503 errors)

HEADERS = {
    "Accept": "application/vnd.api+json",
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
}

HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def extract_slug_from_url(url: str) -> str:
    """Extract the slug (e.g., 'po3637') from a URL path."""
    return url.rstrip("/").split("/")[-1]


def fetch_html_page(path: str, verbose: bool = False) -> Optional[str]:
    """Fetch the HTML content directly from a page URL.
    
    This is a fallback when the JSON API is unavailable (503 errors).
    """
    page_url = f"{BASE_URL}{path}"
    
    if verbose:
        log(f"      >>> Fetching HTML: {page_url}")
    
    for attempt in range(MAX_RETRIES):
        try:
            if verbose:
                log(f"      ... attempt {attempt + 1}/{MAX_RETRIES}", end="")
            
            response = requests.get(page_url, headers=HTML_HEADERS, timeout=TIMEOUT)
            
            if verbose:
                log(f" -> HTTP {response.status_code}")
            
            if response.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_DELAY * (attempt + 1)
                if verbose:
                    log(f"      !!! Server error {response.status_code}, waiting {delay}s...")
                time.sleep(delay)
                continue
            
            response.raise_for_status()
            
            if verbose:
                log(f"      <<< Got {len(response.text)} characters of HTML")
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            if verbose:
                log(f" -> ERROR")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                if verbose:
                    log(f"      !!! {e}")
                    log(f"      ... waiting {delay}s...")
                time.sleep(delay)
            else:
                if verbose:
                    log(f"      !!! FAILED after {MAX_RETRIES} attempts: {e}")
                return None
    
    return None


def extract_content_from_html(html: str) -> dict:
    """Extract title and body content from Treasury press release HTML page."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Find main content area first
        main = soup.find(id="main-content")
        
        # Extract title from the title field
        title = ""
        if main:
            title_field = main.select_one(".field--name-title")
            if title_field:
                title = title_field.get_text(strip=True)
        
        # Fallback title selectors
        if not title:
            for selector in ["h1.page-title", "span.field--name-title", "#main-content h1"]:
                tag = soup.select_one(selector)
                if tag:
                    title = tag.get_text(strip=True)
                    break
        
        # Extract the news body content
        body_html = ""
        body_text = ""
        
        if main:
            # Primary: the news body field (most specific for press releases)
            body_field = main.select_one(".field--name-field-news-body")
            if body_field:
                body_html = str(body_field)
                body_text = body_field.get_text(strip=True)
        
        # Fallback selectors if primary didn't work
        if not body_html or len(body_html) < 100:
            fallback_selectors = [
                "#main-content .field--name-body",
                "#main-content .node__content",
                "#main-content .clearfix.text-formatted",
            ]
            for selector in fallback_selectors:
                content = soup.select_one(selector)
                if content:
                    body_html = str(content)
                    body_text = content.get_text(strip=True)
                    break
        
        # Last resort: entire main content
        if not body_html and main:
            body_html = str(main)
            body_text = main.get_text(strip=True)
        
        return {
            "title": title,
            "body_html": body_html,
            "body_text": body_text,
            "body_length": len(body_html),
            "text_length": len(body_text),
        }
        
    except Exception as e:
        return {
            "title": "",
            "body_html": "",
            "body_text": "",
            "body_length": 0,
            "text_length": 0,
            "error": str(e),
        }


def fetch_by_path_alias(path_alias: str, verbose: bool = False) -> Optional[dict]:
    """Fetch a news item by its path alias from the JSON API with retry logic."""
    filter_param = f"filter[path.alias]={path_alias}"
    api_url = f"{JSONAPI_BASE}?{filter_param}"
    
    if verbose:
        log(f"      >>> Requesting: {api_url[:80]}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            if verbose:
                log(f"      ... attempt {attempt + 1}/{MAX_RETRIES}", end="")
            
            response = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
            
            if verbose:
                log(f" -> HTTP {response.status_code}")
            
            # Handle rate limiting / server errors with retry
            if response.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_DELAY * (attempt + 1)  # Exponential backoff
                if verbose:
                    log(f"      !!! Server error {response.status_code}, waiting {delay}s before retry...")
                time.sleep(delay)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get("data", [])
            if items:
                if verbose:
                    log(f"      <<< Found {len(items)} item(s)")
                return items[0]
            
            if verbose:
                log(f"      <<< No items found in API response")
            return None
            
        except requests.exceptions.RequestException as e:
            if verbose:
                log(f" -> ERROR")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                if verbose:
                    log(f"      !!! {e}")
                    log(f"      ... waiting {delay}s before retry...")
                time.sleep(delay)
            else:
                if verbose:
                    log(f"      !!! FAILED after {MAX_RETRIES} attempts: {e}")
                return None
    
    return None


def load_comparison_data(filepath: Path) -> dict:
    """Load and parse the text_comparison.json file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_missing_content(comparisons: list) -> dict:
    """Analyze all comparisons and extract detailed missing content info.
    
    Returns a structured analysis with:
    - urls_with_missing: list of URLs that have missing content
    - all_missing_items: flat list of all missing text snippets with their URLs
    - by_url: dict mapping URL -> missing items
    - stats: summary statistics
    """
    urls_with_missing = []
    all_missing_items = []
    by_url = {}
    
    for item in comparisons:
        missing_texts = item.get("missing_in_target", [])
        if not missing_texts:
            continue
        
        url = item.get("url", "")
        similarity = item.get("similarity", 0)
        source_words = item.get("source_word_count", 0)
        target_words = item.get("target_word_count", 0)
        
        urls_with_missing.append({
            "url": url,
            "slug": extract_slug_from_url(url),
            "missing_count": len(missing_texts),
            "similarity": similarity,
            "source_word_count": source_words,
            "target_word_count": target_words,
            "word_diff": source_words - target_words,
        })
        
        by_url[url] = {
            "missing_texts": missing_texts,
            "similarity": similarity,
            "diff_snippet": item.get("diff_snippet", ""),
        }
        
        # Create flat list of all missing items
        for i, text in enumerate(missing_texts):
            all_missing_items.append({
                "url": url,
                "slug": extract_slug_from_url(url),
                "index": i,
                "text": text,
                "text_length": len(text),
                "text_preview": text[:150] + "..." if len(text) > 150 else text,
            })
    
    return {
        "urls_with_missing": urls_with_missing,
        "all_missing_items": all_missing_items,
        "by_url": by_url,
        "stats": {
            "total_urls_with_missing": len(urls_with_missing),
            "total_missing_snippets": len(all_missing_items),
            "avg_missing_per_url": len(all_missing_items) / len(urls_with_missing) if urls_with_missing else 0,
        }
    }


def generate_bulk_api_urls(urls: list) -> list:
    """Generate JSON API URLs for bulk fetching.
    
    Returns list of API URLs that can be used to fetch content.
    """
    api_urls = []
    for item in urls:
        url = item["url"] if isinstance(item, dict) else item
        api_url = f"{JSONAPI_BASE}?filter[path.alias]={url}"
        api_urls.append({
            "page_url": url,
            "api_url": api_url,
            "full_page_url": f"{BASE_URL}{url}",
        })
    return api_urls


def fetch_single_url(url_info: dict, verbose: bool = False) -> dict:
    """Fetch a single URL from the API. Used for parallel fetching."""
    url = url_info["url"]
    result = {
        "url": url,
        "slug": url_info.get("slug", extract_slug_from_url(url)),
        "api_found": False,
    }
    
    # Small delay to avoid rate limiting
    time.sleep(0.5)
    
    api_item = fetch_by_path_alias(url, verbose=verbose)
    
    if api_item:
        attrs = api_item.get("attributes", {})
        body_field = attrs.get("field_news_body", {})
        
        if isinstance(body_field, dict):
            body_html = body_field.get("value", "")
        else:
            body_html = str(body_field) if body_field else ""
        
        result.update({
            "api_found": True,
            "title": attrs.get("title", ""),
            "publication_date": attrs.get("field_news_publication_date", ""),
            "body_html": body_html,
            "body_length": len(body_html),
            "drupal_id": api_item.get("id", ""),
        })
    else:
        result["error"] = "Not found in JSON API"
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Fetch missing content from Treasury JSON API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze and show all missing content (verbose)
  python3 scripts/fetch_missing_content.py

  # Generate bulk API URLs for external fetching
  python3 scripts/fetch_missing_content.py --prepare-bulk-urls

  # Fetch content from API and save
  python3 scripts/fetch_missing_content.py --fetch

  # Show detailed info for each missing item
  python3 scripts/fetch_missing_content.py --show-all-missing
        """,
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="text_comparison.json",
        help="Path to text_comparison.json (default: text_comparison.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="staging",
        help="Output directory (default: staging)",
    )
    parser.add_argument(
        "--prepare-bulk-urls",
        action="store_true",
        help="Generate bulk API URLs file for external fetching",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Actually fetch content from the API",
    )
    parser.add_argument(
        "--show-all-missing",
        action="store_true",
        help="Print every missing text snippet",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of URLs to process",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=MAX_WORKERS,
        help=f"Number of parallel API requests (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "--use-html",
        action="store_true",
        help="Fetch from HTML pages instead of JSON API (fallback for 503 errors)",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    workspace = Path(__file__).parent.parent
    input_path = workspace / args.input_file
    output_dir = workspace / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log("=" * 70)
    log("FETCH MISSING CONTENT FROM TREASURY JSON API")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    log()
    
    # Load comparison data
    log(f"[1/5] LOADING INPUT FILE")
    log(f"      Path: {input_path}")
    
    if not input_path.exists():
        log(f"      ERROR: File not found!")
        sys.exit(1)
    
    data = load_comparison_data(input_path)
    comparisons = data.get("comparisons", [])
    
    log(f"      Total comparisons loaded: {len(comparisons)}")
    log(f"      Source: {data.get('source_dir', 'unknown')}")
    log(f"      Target: {data.get('target_dir', 'unknown')}")
    log()
    
    # Analyze missing content
    log(f"[2/5] ANALYZING MISSING CONTENT")
    analysis = analyze_missing_content(comparisons)
    stats = analysis["stats"]
    
    log(f"      URLs with missing content: {stats['total_urls_with_missing']}")
    log(f"      Total missing text snippets: {stats['total_missing_snippets']}")
    log(f"      Avg missing per URL: {stats['avg_missing_per_url']:.1f}")
    log()
    
    # Apply limit if specified
    urls_to_process = analysis["urls_with_missing"]
    if args.limit:
        urls_to_process = urls_to_process[:args.limit]
        log(f"      Limited to: {len(urls_to_process)} URLs")
        log()
    
    # Show detailed missing content
    log(f"[3/5] MISSING CONTENT DETAILS")
    log("-" * 70)
    
    for i, url_info in enumerate(urls_to_process, 1):
        url = url_info["url"]
        by_url_data = analysis["by_url"].get(url, {})
        missing_texts = by_url_data.get("missing_texts", [])
        
        log()
        log(f"  [{i}/{len(urls_to_process)}] {url}")
        log(f"      Slug: {url_info['slug']}")
        log(f"      Similarity: {url_info['similarity']:.1%}")
        log(f"      Word count: source={url_info['source_word_count']}, target={url_info['target_word_count']}, diff={url_info['word_diff']}")
        log(f"      Missing snippets: {len(missing_texts)}")
        log()
        
        if args.show_all_missing:
            for j, text in enumerate(missing_texts, 1):
                log(f"      MISSING #{j}:")
                # Show full text, wrapped
                lines = text.split('\n')
                for line in lines:
                    # Wrap long lines
                    while len(line) > 100:
                        log(f"        {line[:100]}")
                        line = line[100:]
                    log(f"        {line}")
                log()
        else:
            # Show preview of first 3
            for j, text in enumerate(missing_texts[:3], 1):
                preview = text[:120].replace('\n', ' ')
                if len(text) > 120:
                    preview += "..."
                log(f"      [{j}] {preview}")
            
            if len(missing_texts) > 3:
                log(f"      ... and {len(missing_texts) - 3} more (use --show-all-missing)")
    
    log()
    log("-" * 70)
    
    # Generate bulk API URLs
    log(f"[4/5] GENERATING BULK API URLs")
    
    bulk_urls = generate_bulk_api_urls(urls_to_process)
    
    # Save bulk URLs to file
    bulk_urls_file = output_dir / "bulk_fetch_urls.txt"
    with open(bulk_urls_file, "w") as f:
        f.write(f"# Bulk API URLs for fetching missing content\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Total URLs: {len(bulk_urls)}\n")
        f.write(f"#\n")
        f.write(f"# Format: PAGE_URL | API_URL\n")
        f.write(f"#\n\n")
        
        for item in bulk_urls:
            f.write(f"{item['page_url']}\n")
            f.write(f"  API: {item['api_url']}\n")
            f.write(f"\n")
    
    log(f"      Saved {len(bulk_urls)} URLs to: {bulk_urls_file}")
    
    # Save flat missing items array
    flat_items_file = output_dir / "missing_items_flat.json"
    flat_output = {
        "timestamp": datetime.now().isoformat(),
        "source_file": str(input_path),
        "total_items": len(analysis["all_missing_items"]),
        "items": analysis["all_missing_items"],
    }
    
    with open(flat_items_file, "w", encoding="utf-8") as f:
        json.dump(flat_output, f, indent=2, ensure_ascii=False)
    
    log(f"      Saved {len(analysis['all_missing_items'])} flat items to: {flat_items_file}")
    
    # If --prepare-bulk-urls, also save a simple URL list
    if args.prepare_bulk_urls:
        simple_urls_file = output_dir / "urls_to_fetch.json"
        simple_output = {
            "timestamp": datetime.now().isoformat(),
            "base_api_url": JSONAPI_BASE,
            "total_urls": len(urls_to_process),
            "urls": [
                {
                    "path": item["url"],
                    "slug": item["slug"],
                    "api_filter": f"filter[path.alias]={item['url']}",
                    "full_api_url": f"{JSONAPI_BASE}?filter[path.alias]={item['url']}",
                    "missing_count": item["missing_count"],
                }
                for item in urls_to_process
            ],
        }
        
        with open(simple_urls_file, "w", encoding="utf-8") as f:
            json.dump(simple_output, f, indent=2, ensure_ascii=False)
        
        log(f"      Saved URL list to: {simple_urls_file}")
        
        # Also print curl commands
        log()
        log("      CURL COMMANDS FOR BULK FETCHING:")
        log("      " + "-" * 50)
        for item in bulk_urls[:5]:
            log(f"      curl -H 'Accept: application/vnd.api+json' \\")
            log(f"           '{item['api_url']}'")
            log()
        if len(bulk_urls) > 5:
            log(f"      ... and {len(bulk_urls) - 5} more URLs")
    
    log()
    
    # Fetch from API if requested
    if args.fetch:
        fetch_mode = "HTML pages" if args.use_html else "JSON API"
        log(f"[5/5] FETCHING FROM {fetch_mode.upper()}")
        log(f"      Mode: Sequential (for reliable output)")
        log(f"      URLs to fetch: {len(urls_to_process)}")
        if args.use_html:
            log(f"      Note: Using HTML fallback (bypasses JSON API 503 errors)")
        log("-" * 70)
        log()
        
        results = []
        success_count = 0
        fail_count = 0
        
        for i, url_info in enumerate(urls_to_process, 1):
            url = url_info["url"]
            slug = url_info.get("slug", extract_slug_from_url(url))
            
            log(f"  [{i}/{len(urls_to_process)}] Fetching: {url}")
            log(f"      Slug: {slug}")
            
            if args.use_html:
                # Fetch HTML directly from page
                html = fetch_html_page(url, verbose=True)
                
                if html:
                    success_count += 1
                    content = extract_content_from_html(html)
                    
                    log(f"      *** SUCCESS ***")
                    log(f"      Title: {content.get('title', 'N/A')[:70]}")
                    log(f"      Body HTML: {content.get('body_length', 0)} chars")
                    log(f"      Body Text: {content.get('text_length', 0)} chars")
                    
                    results.append({
                        "url": url,
                        "slug": slug,
                        "source": "html",
                        "api_found": True,
                        "title": content.get("title", ""),
                        "body_html": content.get("body_html", ""),
                        "body_text": content.get("body_text", ""),
                        "body_length": content.get("body_length", 0),
                        "text_length": content.get("text_length", 0),
                    })
                else:
                    fail_count += 1
                    log(f"      *** FAILED - Could not fetch HTML ***")
                    results.append({
                        "url": url,
                        "slug": slug,
                        "source": "html",
                        "api_found": False,
                        "error": "Could not fetch HTML page",
                    })
            else:
                # Fetch from JSON API
                api_item = fetch_by_path_alias(url, verbose=True)
                
                if api_item:
                    success_count += 1
                    attrs = api_item.get("attributes", {})
                    body_field = attrs.get("field_news_body", {})
                    
                    if isinstance(body_field, dict):
                        body_html = body_field.get("value", "")
                    else:
                        body_html = str(body_field) if body_field else ""
                    
                    title = attrs.get("title", "")
                    pub_date = attrs.get("field_news_publication_date", "")
                    
                    log(f"      *** SUCCESS ***")
                    log(f"      Title: {title[:70]}")
                    log(f"      Date: {pub_date}")
                    log(f"      Body: {len(body_html)} characters")
                    
                    results.append({
                        "url": url,
                        "slug": slug,
                        "source": "jsonapi",
                        "api_found": True,
                        "title": title,
                        "publication_date": pub_date,
                        "body_html": body_html,
                        "body_length": len(body_html),
                        "drupal_id": api_item.get("id", ""),
                    })
                else:
                    fail_count += 1
                    log(f"      *** FAILED - Not found in API ***")
                    log(f"      TIP: Try --use-html to fetch from HTML pages instead")
                    results.append({
                        "url": url,
                        "slug": slug,
                        "source": "jsonapi",
                        "api_found": False,
                        "error": "Not found in JSON API",
                    })
            
            log()
            
            # Small delay between requests
            if i < len(urls_to_process):
                log(f"      ... waiting 2s before next request ...")
                time.sleep(2)
                log()
        
        log("-" * 70)
        log(f"      COMPLETE!")
        log(f"      Fetched successfully: {success_count}")
        log(f"      Failed: {fail_count}")
        
        # Save fetched results
        fetched_file = output_dir / "fetched_content.json"
        fetched_output = {
            "timestamp": datetime.now().isoformat(),
            "source_file": str(input_path),
            "total_processed": len(results),
            "success_count": success_count,
            "fail_count": fail_count,
            "items": results,
        }
        
        with open(fetched_file, "w", encoding="utf-8") as f:
            json.dump(fetched_output, f, indent=2, ensure_ascii=False)
        
        log(f"      Saved results to: {fetched_file}")
    else:
        log(f"[5/5] SKIPPING API FETCH (use --fetch to enable)")
    
    log()
    log("=" * 70)
    log("SUMMARY")
    log("=" * 70)
    log(f"  URLs with missing content: {stats['total_urls_with_missing']}")
    log(f"  Total missing snippets: {stats['total_missing_snippets']}")
    log()
    log("Output files:")
    log(f"  - {output_dir / 'bulk_fetch_urls.txt'}")
    log(f"  - {output_dir / 'missing_items_flat.json'}")
    if args.prepare_bulk_urls:
        log(f"  - {output_dir / 'urls_to_fetch.json'}")
    if args.fetch:
        log(f"  - {output_dir / 'fetched_content.json'}")
    log()


if __name__ == "__main__":
    main()
