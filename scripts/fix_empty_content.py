#!/usr/bin/env python3
"""
Fix Empty Content Pages

Reads the text_comparison JSON report, identifies pages with empty content
in the Hugo build, fetches the actual content from the live Treasury site,
and updates the Hugo markdown files with correct dates and body content.

Usage:
    # Fix first 20 empty-content pages (dry run)
    python scripts/fix_empty_content.py --limit 20 --dry-run

    # Fix first 20 for real
    python scripts/fix_empty_content.py --limit 20

    # Fix all empty-content pages
    python scripts/fix_empty_content.py

    # Use a specific comparison file
    python scripts/fix_empty_content.py --input /path/to/text_comparison.json --limit 50
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Configuration
SITE_URL = "https://home.treasury.gov"
CONTENT_DIR = Path(__file__).parent.parent / "content"
DEFAULT_INPUT = Path(__file__).parent.parent / "text_comparison-2.json"
TIMEOUT = 30
REQUEST_DELAY = 0.5  # Seconds between requests to avoid rate limiting

HEADERS = {
    "User-Agent": "Treasury Hugo Migration Bot/1.0",
    "Accept": "text/html,application/xhtml+xml",
}

# URL path -> Hugo content folder mapping
FOLDER_MAP = {
    "/news/press-releases/": "news/press-releases",
    "/news/media-advisories/": "news/media-advisories",
    "/news/weekly-public-schedule/": "news/weekly-public-schedule",
    "/news/weekly-schedule-updates/": "news/weekly-schedule-updates",
    "/news/featured-stories/": "news/featured-stories",
    "/news/statements-remarks/": "news/statements-remarks",
    "/news/readouts/": "news/readouts",
    "/news/testimonies/": "news/testimonies",
    "/news/recent-highlights/": "news/recent-highlights",
    "/about/history/": "about/history",
    "/about/offices/": "about/offices",
    "/about/careers-at-treasury/": "about/careers-at-treasury",
    "/about/general-information/": "about/general-information",
    "/policy-issues/": "policy-issues",
    "/data/": "data",
}


def url_to_folder(url_path: str) -> str:
    """Map a URL path to the correct Hugo content folder."""
    for prefix, folder in FOLDER_MAP.items():
        if url_path.startswith(prefix):
            return folder
    # Fallback: use the URL structure directly
    parts = url_path.strip("/").split("/")
    if len(parts) >= 2:
        return "/".join(parts[:-1])
    return "misc"


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Process headings - maintain proper hierarchy (H2+ for content)
    heading_map = {
        "h1": 2,
        "h2": 2,
        "h3": 3,
        "h4": 4,
        "h5": 5,
        "h6": 6,
    }

    for tag_name, target_level in heading_map.items():
        for h in soup.find_all(tag_name):
            text = h.get_text(strip=True)
            if text:
                h.replace_with(f"\n\n{'#' * target_level} {text}\n\n")

    # Tables - convert to markdown tables
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            table.replace_with("")
            continue

        md_rows = []
        for i, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [c.get_text(strip=True).replace("|", "\\|") for c in cells]
            md_rows.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                md_rows.append("| " + " | ".join(["---"] * len(cell_texts)) + " |")

        table.replace_with("\n\n" + "\n".join(md_rows) + "\n\n")

    # Bold/Strong
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text()
        if text.strip():
            tag.replace_with(f"**{text}**")

    # Italic/Em
    for tag in soup.find_all(["em", "i"]):
        text = tag.get_text()
        if text.strip():
            tag.replace_with(f"*{text}*")

    # Links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            if href.startswith("/"):
                href = f"{SITE_URL}{href}"
            a.replace_with(f"[{text}]({href})")
        elif text:
            a.replace_with(text)

    # Unordered lists
    for ul in soup.find_all("ul"):
        items = []
        for li in ul.find_all("li", recursive=False):
            li_text = li.get_text(strip=True)
            if li_text:
                items.append(f"- {li_text}")
        ul.replace_with("\n" + "\n".join(items) + "\n")

    # Ordered lists
    for ol in soup.find_all("ol"):
        items = []
        for idx, li in enumerate(ol.find_all("li", recursive=False), 1):
            li_text = li.get_text(strip=True)
            if li_text:
                items.append(f"{idx}. {li_text}")
        ol.replace_with("\n" + "\n".join(items) + "\n")

    # Paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n\n{text}\n\n")

    # Line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # Get text and clean up
    text = soup.get_text()
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n +", "\n", text)

    return text.strip()


def fetch_page_content(url_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch a page from home.treasury.gov and extract date and body content.

    Returns:
        Tuple of (date_str, body_html, error_message)
        date_str: YYYY-MM-DD format
        body_html: Raw HTML of the body field
        error_message: None on success, error description on failure
    """
    full_url = f"{SITE_URL}{url_path}"

    try:
        resp = requests.get(full_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, None, f"HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract date from og:updated_time meta tag
        date_str = None
        meta_date = soup.find("meta", property="og:updated_time")
        if meta_date:
            raw_date = meta_date.get("content", "")
            if raw_date:
                # Handle both YYYY-MM-DD and full ISO formats
                date_str = raw_date[:10]

        # Extract body content - try multiple field names
        body_html = None
        body_field = None

        # Priority order of body field selectors
        selectors = [
            re.compile(r"field--name-field-page-body"),
            re.compile(r"field--name-field-news-body"),
            re.compile(r"field--name-field-schedule-body"),
            re.compile(r"field--name-field-schedule-public-body"),
        ]

        for selector in selectors:
            body_field = soup.find(class_=selector)
            if body_field:
                break

        if body_field:
            # Get the inner HTML (not the wrapper div)
            body_html = body_field.decode_contents()
        else:
            # Last resort: look for the main content area
            # Skip if we can't find a specific body field
            return date_str, None, "No body field found in HTML"

        return date_str, body_html, None

    except requests.exceptions.Timeout:
        return None, None, "Request timed out"
    except requests.exceptions.RequestException as e:
        return None, None, f"Request error: {e}"
    except Exception as e:
        return None, None, f"Parse error: {e}"


def find_hugo_file(url_path: str) -> Optional[Path]:
    """Find the Hugo markdown file for a given URL path."""
    slug = url_path.rstrip("/").split("/")[-1]

    # Search content directory for files with matching URL in front matter
    for md_file in CONTENT_DIR.rglob("*.md"):
        if md_file.name == "_index.md":
            continue
        if slug in md_file.name:
            # Quick check front matter for URL match
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    head = f.read(1000)
                if f"url: {url_path}" in head or f"url: '{url_path}'" in head:
                    return md_file
            except Exception:
                continue

    # Broader search if slug-based didn't work
    for md_file in CONTENT_DIR.rglob("*.md"):
        if md_file.name == "_index.md":
            continue
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                head = f.read(1000)
            if f"url: {url_path}" in head or f"url: '{url_path}'" in head:
                return md_file
        except Exception:
            continue

    return None


def parse_front_matter(content: str) -> Tuple[dict, str]:
    """Parse YAML front matter and body from a markdown file.

    Returns:
        Tuple of (front_matter_dict, body_content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    fm_text = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    # Simple YAML parsing (handles our front matter format)
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            fm[key] = value

    return fm, body


def build_front_matter(fm: dict) -> str:
    """Build YAML front matter string from dict."""
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, str):
            # Quote values with YAML-special characters
            needs_quoting = (
                "\n" in value or '"' in value or ":" in value or
                "'" in value or "*" in value or "#" in value or
                value.startswith(("[", "{", ">", "|", "!"))
            )
            if needs_quoting:
                escaped = value.replace("'", "''")
                lines.append(f"{key}: '{escaped}'")
            else:
                lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def fix_page(url_path: str, dry_run: bool = False) -> Tuple[bool, str]:
    """Fix a single page by fetching content and updating the Hugo file.

    Returns:
        Tuple of (success, message)
    """
    # Find existing Hugo file
    hugo_file = find_hugo_file(url_path)
    if not hugo_file:
        return False, "Hugo file not found"

    # Read current content
    with open(hugo_file, "r", encoding="utf-8") as f:
        current_content = f.read()

    fm, existing_body = parse_front_matter(current_content)

    # Fetch live page content
    date_str, body_html, error = fetch_page_content(url_path)
    if error and not body_html:
        return False, f"Fetch failed: {error}"

    # Convert body to markdown
    body_md = html_to_markdown(body_html) if body_html else ""
    if not body_md:
        return False, "Empty body after conversion"

    # Update front matter
    if date_str:
        fm["date"] = date_str

    # Ensure URL is set
    fm["url"] = url_path

    # Determine correct folder
    correct_folder = url_to_folder(url_path)
    correct_dir = CONTENT_DIR / correct_folder
    slug = url_path.rstrip("/").split("/")[-1]
    date_prefix = date_str if date_str else fm.get("date", "2020-01-01")
    new_filename = f"{date_prefix}-{slug}.md"
    new_path = correct_dir / new_filename

    # Build new file content
    new_content = build_front_matter(fm) + "\n\n" + body_md + "\n"

    if dry_run:
        moved = ""
        if new_path != hugo_file:
            moved = f" (MOVE: {hugo_file.relative_to(CONTENT_DIR)} -> {new_path.relative_to(CONTENT_DIR)})"
        return True, f"Would update: date={date_str}, body={len(body_md)} chars{moved}"

    # Write updated file
    correct_dir.mkdir(parents=True, exist_ok=True)

    # If file needs to move to a different location
    if new_path != hugo_file:
        # Write to new location
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        # Remove old file
        hugo_file.unlink()
        return True, f"Fixed and moved: {hugo_file.name} -> {new_path.relative_to(CONTENT_DIR)}"
    else:
        with open(hugo_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, f"Fixed in place: {hugo_file.name}"


def load_empty_content_urls(input_file: Path, limit: int = 0, offset: int = 0) -> list:
    """Load URLs of pages with empty content from comparison JSON.

    Args:
        input_file: Path to the text_comparison JSON file
        limit: Max number of URLs to return (0 = all)
        offset: Number of entries to skip from the start

    Returns:
        List of URL path strings
    """
    with open(input_file, "r") as f:
        data = json.load(f)

    # Filter to entries with status=different and target_word_count=0
    empty_entries = [
        c for c in data["comparisons"]
        if c["status"] == "different" and c["target_word_count"] == 0
    ]

    # Apply offset
    if offset > 0:
        empty_entries = empty_entries[offset:]

    # Apply limit
    if limit > 0:
        empty_entries = empty_entries[:limit]

    return [e["url"] for e in empty_entries]


def main():
    parser = argparse.ArgumentParser(
        description="Fix empty-content pages by fetching from live Treasury site",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run on first 20 pages
  python scripts/fix_empty_content.py --limit 20 --dry-run

  # Fix first 20 pages
  python scripts/fix_empty_content.py --limit 20

  # Fix pages 21-40
  python scripts/fix_empty_content.py --limit 20 --offset 20

  # Fix all empty-content pages
  python scripts/fix_empty_content.py

  # Use specific input file
  python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json --limit 50
        """,
    )
    parser.add_argument(
        "--input",
        type=str,
        help=f"Path to text_comparison JSON file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max pages to process (0 = all)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip this many entries from the start",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY,
        help=f"Delay between requests in seconds (default: {REQUEST_DELAY})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    input_file = Path(args.input) if args.input else DEFAULT_INPUT
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    print("Treasury Empty Content Fixer")
    print(f"  Input: {input_file}")
    print(f"  Content dir: {CONTENT_DIR}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if args.limit:
        print(f"  Limit: {args.limit}")
    if args.offset:
        print(f"  Offset: {args.offset}")
    print(f"  Delay: {args.delay}s between requests")
    print()

    # Load URLs to fix
    urls = load_empty_content_urls(input_file, limit=args.limit, offset=args.offset)
    print(f"Found {len(urls)} pages to process")
    print()

    # Process each URL
    success_count = 0
    fail_count = 0
    results = []

    for i, url_path in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url_path}", end=" ... ", flush=True)

        success, message = fix_page(url_path, dry_run=args.dry_run)

        if success:
            success_count += 1
            print(f"OK - {message}")
        else:
            fail_count += 1
            print(f"FAIL - {message}")

        results.append({
            "url": url_path,
            "success": success,
            "message": message,
        })

        # Rate limiting (skip on dry run if no actual fetch)
        if not args.dry_run and i < len(urls):
            time.sleep(args.delay)

    # Summary
    print()
    print("=" * 60)
    print(f"RESULTS: {success_count} fixed, {fail_count} failed, {len(urls)} total")
    if args.dry_run:
        print("(DRY RUN - no changes made)")
    print()

    # Show failures
    failures = [r for r in results if not r["success"]]
    if failures:
        print("Failed pages:")
        for r in failures:
            print(f"  {r['url']}: {r['message']}")

    # Write results log
    log_file = Path(__file__).parent.parent / "fix_empty_content_log.json"
    with open(log_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": args.dry_run,
            "total": len(urls),
            "success": success_count,
            "failed": fail_count,
            "results": results,
        }, f, indent=2)
    print(f"Log written to: {log_file}")


if __name__ == "__main__":
    main()
