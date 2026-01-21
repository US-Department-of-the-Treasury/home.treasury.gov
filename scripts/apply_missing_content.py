#!/usr/bin/env python3
"""
Apply Missing Content to Hugo Markdown Files

Reads the fetched content from staging/fetched_content.json and updates
the corresponding Hugo markdown files in content/news/press-releases/.

Usage:
    python3 scripts/apply_missing_content.py
    python3 scripts/apply_missing_content.py --dry-run
    python3 scripts/apply_missing_content.py --limit 2
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


def log(msg: str = "", end: str = "\n"):
    """Print with immediate flush for real-time output."""
    print(msg, end=end, flush=True)


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown.
    
    Handles Treasury press release formatting including tables,
    lists, links, and styled text.
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove the wrapper div if present
    wrapper = soup.find("div", class_="field--name-field-news-body")
    if wrapper:
        soup = wrapper
    
    # Process headers
    for tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(tag_name[1])
        # Content headings should be H2+ (H1 is page title)
        target_level = max(2, level)
        for h in soup.find_all(tag_name):
            text = h.get_text(strip=True)
            if text:
                h.replace_with(f"\n\n{'#' * target_level} {text}\n\n")
    
    # Bold/Strong
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text()
        if text.strip():
            tag.replace_with(f"**{text}**")
    
    # Italic/Em (but not archived content notice)
    for tag in soup.find_all(["em", "i"]):
        text = tag.get_text()
        if text.strip() and "Archived Content" not in text:
            tag.replace_with(f"*{text}*")
        elif "Archived Content" in text:
            tag.replace_with("")  # Remove archived notice, Hugo adds it
    
    # Links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            # Make relative URLs absolute if needed
            if href.startswith("/"):
                href = f"https://home.treasury.gov{href}"
            a.replace_with(f"[{text}]({href})")
        elif text:
            a.replace_with(text)
    
    # Handle tables - convert to markdown tables or preserve as HTML
    for table in soup.find_all("table"):
        # For complex tables, keep as raw HTML
        # Just clean up the table a bit
        table_html = str(table)
        # Add newlines around table
        table.replace_with(f"\n\n{table_html}\n\n")
    
    # Unordered lists
    for ul in list(soup.find_all("ul")):
        if ul is None:
            continue
        items = []
        for li in ul.find_all("li", recursive=False):
            li_text = li.get_text(strip=True)
            if li_text:
                items.append(f"- {li_text}")
        if items:
            ul.replace_with("\n" + "\n".join(items) + "\n")
        else:
            try:
                ul.decompose()
            except:
                pass
    
    # Ordered lists
    for ol in list(soup.find_all("ol")):
        if ol is None:
            continue
        items = []
        start = 1
        try:
            start_attr = ol.get("start", 1)
            if start_attr:
                start = int(start_attr)
        except:
            start = 1
        for idx, li in enumerate(ol.find_all("li", recursive=False), start):
            li_text = li.get_text(strip=True)
            if li_text:
                items.append(f"{idx}. {li_text}")
        if items:
            ol.replace_with("\n" + "\n".join(items) + "\n")
        else:
            try:
                ol.decompose()
            except:
                pass
    
    # Paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(f"\n\n{text}\n\n")
        else:
            p.decompose()
    
    # Line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    # Images - convert to markdown
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src and "spacer" not in src:
            if src.startswith("/"):
                src = f"https://home.treasury.gov{src}"
            img.replace_with(f"\n\n![{alt}]({src})\n\n")
        else:
            img.decompose()
    
    # Remove empty tags
    for tag in soup.find_all(["dir", "span", "td", "tr", "tbody", "center"]):
        text = tag.get_text(strip=True)
        if text:
            tag.replace_with(f" {text} ")
        else:
            tag.decompose()
    
    # Get text and clean up
    text = soup.get_text()
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Multiple newlines -> double
    text = re.sub(r" +", " ", text)  # Multiple spaces -> single
    text = re.sub(r"\n +", "\n", text)  # Leading spaces on lines
    text = re.sub(r" +\n", "\n", text)  # Trailing spaces on lines
    
    return text.strip()


def find_markdown_file(slug: str, content_dir: Path) -> Path:
    """Find the markdown file for a given slug."""
    # Look for files matching *slug.md pattern
    for md_file in content_dir.glob(f"*{slug}.md"):
        return md_file
    return None


def extract_frontmatter(content: str) -> tuple:
    """Extract frontmatter and body from markdown file.
    
    Returns (frontmatter_str, body_str) tuple.
    """
    if not content.startswith("---"):
        return "", content
    
    # Find the closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return "", content
    
    frontmatter = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()
    
    return frontmatter, body


def create_updated_content(frontmatter: str, new_body: str) -> str:
    """Create the updated markdown content with frontmatter and new body."""
    return f"---\n{frontmatter}\n---\n\n{new_body}\n"


def main():
    parser = argparse.ArgumentParser(
        description="Apply fetched content to Hugo markdown files",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="staging/fetched_content.json",
        help="Path to fetched_content.json",
    )
    parser.add_argument(
        "--content-dir",
        type=str,
        default="content/news/press-releases",
        help="Path to Hugo content directory",
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
        help="Limit number of files to process",
    )
    parser.add_argument(
        "--use-html",
        action="store_true",
        help="Keep HTML content instead of converting to markdown",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    workspace = Path(__file__).parent.parent
    input_path = workspace / args.input_file
    content_dir = workspace / args.content_dir
    
    log("=" * 70)
    log("APPLY MISSING CONTENT TO HUGO MARKDOWN FILES")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    log()
    
    # Load fetched content
    log(f"[1/3] LOADING FETCHED CONTENT")
    log(f"      Input: {input_path}")
    
    if not input_path.exists():
        log(f"      ERROR: File not found!")
        log(f"      Run: python3 scripts/fetch_missing_content.py --fetch --use-html")
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    items = data.get("items", [])
    log(f"      Loaded {len(items)} items")
    
    # Filter to only successful fetches
    items = [item for item in items if item.get("api_found")]
    log(f"      Successfully fetched: {len(items)}")
    
    if args.limit:
        items = items[:args.limit]
        log(f"      Limited to: {len(items)}")
    
    log()
    
    # Process each item
    log(f"[2/3] UPDATING MARKDOWN FILES")
    log("-" * 70)
    
    updated = 0
    skipped = 0
    errors = 0
    
    for i, item in enumerate(items, 1):
        url = item.get("url", "")
        slug = item.get("slug", "")
        title = item.get("title", "")
        body_html = item.get("body_html", "")
        
        log()
        log(f"  [{i}/{len(items)}] {url}")
        log(f"      Slug: {slug}")
        log(f"      Title: {title[:60]}...")
        
        # Find the markdown file
        md_file = find_markdown_file(slug, content_dir)
        
        if not md_file:
            log(f"      ERROR: Markdown file not found for slug '{slug}'")
            errors += 1
            continue
        
        log(f"      File: {md_file.name}")
        
        # Read current content
        with open(md_file, "r", encoding="utf-8") as f:
            current_content = f.read()
        
        frontmatter, current_body = extract_frontmatter(current_content)
        
        log(f"      Current body: {len(current_body)} chars")
        
        # Convert HTML to markdown (or keep as HTML)
        if args.use_html:
            new_body = body_html
        else:
            new_body = html_to_markdown(body_html)
        
        log(f"      New body: {len(new_body)} chars")
        
        # Check if content actually changed
        if new_body.strip() == current_body.strip():
            log(f"      SKIPPED: Content unchanged")
            skipped += 1
            continue
        
        if args.dry_run:
            log(f"      DRY RUN: Would update file")
            log(f"      --- Current (first 200 chars) ---")
            log(f"      {current_body[:200]}...")
            log(f"      --- New (first 200 chars) ---")
            log(f"      {new_body[:200]}...")
            updated += 1
        else:
            # Create updated content
            updated_content = create_updated_content(frontmatter, new_body)
            
            # Write the file
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
            
            log(f"      UPDATED: {md_file}")
            updated += 1
    
    log()
    log("-" * 70)
    
    # Summary
    log(f"[3/3] SUMMARY")
    log("=" * 70)
    log(f"  Total processed: {len(items)}")
    log(f"  Updated: {updated}")
    log(f"  Skipped (unchanged): {skipped}")
    log(f"  Errors: {errors}")
    
    if args.dry_run:
        log()
        log("  NOTE: This was a DRY RUN. No files were modified.")
        log("  Run without --dry-run to apply changes.")
    
    log()


if __name__ == "__main__":
    main()
