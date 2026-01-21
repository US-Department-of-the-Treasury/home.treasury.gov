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


def element_to_markdown(element) -> str:
    """Recursively convert an HTML element to Markdown, preserving inline formatting."""
    from bs4 import NavigableString, Tag
    
    if isinstance(element, NavigableString):
        text = str(element)
        # Normalize whitespace but preserve single spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    if not isinstance(element, Tag):
        return ""
    
    tag_name = element.name.lower() if element.name else ""
    
    # Skip certain elements entirely
    if tag_name in ["script", "style", "head", "meta", "link"]:
        return ""
    
    # Recursively process children first
    children_text = ""
    for child in element.children:
        children_text += element_to_markdown(child)
    
    # Handle specific tags
    if tag_name in ["strong", "b"]:
        inner = children_text.strip()
        if inner:
            return f"**{inner}**"
        return ""
    
    if tag_name in ["em", "i"]:
        inner = children_text.strip()
        # Skip "Archived Content" notices
        if inner and "Archived Content" not in inner:
            return f"*{inner}*"
        return ""
    
    if tag_name == "a":
        href = element.get("href", "")
        inner = children_text.strip()
        if href and inner:
            # Make relative URLs absolute
            if href.startswith("/"):
                href = f"https://home.treasury.gov{href}"
            return f"[{inner}]({href})"
        return inner
    
    if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(tag_name[1])
        # Content headings should be H2+ (H1 is page title)
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
        return " "  # Convert <br> to space within paragraphs
    
    if tag_name == "li":
        inner = children_text.strip()
        return inner
    
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
        # Keep tables as HTML for now (they're complex)
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
            # Prefix each line with >
            lines = inner.split("\n")
            quoted = "\n".join(f"> {line}" for line in lines if line.strip())
            return f"\n\n{quoted}\n\n"
        return ""
    
    if tag_name == "div":
        # Check for specific wrapper divs
        classes = element.get("class", [])
        if "field--name-field-news-body" in classes:
            return children_text
        # Otherwise just return children
        return children_text
    
    # Default: just return children's text
    return children_text


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown.
    
    Handles Treasury press release formatting including tables,
    lists, links, and styled text.
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "head", "meta", "link", "nav", "header", "footer"]):
        tag.decompose()
    
    # Remove "(Archived Content)" notices - Hugo adds these
    for em in soup.find_all(["em", "i"]):
        if em.get_text(strip=True) == "(Archived Content)":
            # Also remove parent <p> if it only contains this
            parent = em.parent
            em.decompose()
            if parent and parent.name == "p" and not parent.get_text(strip=True):
                parent.decompose()
    
    # Convert to markdown using recursive function
    markdown = element_to_markdown(soup)
    
    # Decode HTML entities
    markdown = html.unescape(markdown)
    
    # Clean up whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)  # Multiple newlines -> double
    markdown = re.sub(r" +", " ", markdown)  # Multiple spaces -> single
    markdown = re.sub(r"\n +", "\n", markdown)  # Leading spaces on lines
    markdown = re.sub(r" +\n", "\n", markdown)  # Trailing spaces on lines
    markdown = re.sub(r"^\s+", "", markdown)  # Leading whitespace
    markdown = re.sub(r"\s+$", "", markdown)  # Trailing whitespace
    
    return markdown.strip()


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
