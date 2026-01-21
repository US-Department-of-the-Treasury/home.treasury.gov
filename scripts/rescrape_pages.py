#!/usr/bin/env python3
"""
Re-scrape pages from live Treasury.gov to replace hallucinated content.

Uses Playwright to extract actual content from live pages and update local markdown files.

Usage:
    python scripts/rescrape_pages.py
    python scripts/rescrape_pages.py --dry-run  # Preview without saving
"""

import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Page

# Configuration
BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content"
STAGING_DIR = BASE_DIR / "staging"
LIVE_SITE = "https://home.treasury.gov"

# Load hallucination report
HALLUCINATION_REPORT = STAGING_DIR / "hallucination_audit.json"


def load_hallucinated_files() -> List[Dict]:
    """Load list of hallucinated files from audit report."""
    if not HALLUCINATION_REPORT.exists():
        print(f"Error: {HALLUCINATION_REPORT} not found")
        print("Run the audit first: python scripts/audit_hallucinations_playwright.py")
        return []
    
    with open(HALLUCINATION_REPORT) as f:
        data = json.load(f)
    
    # Get both hallucinations and content mismatches
    files = data.get("hallucinations", []) + data.get("content_mismatches", [])
    return files


async def extract_page_content(page: Page, url: str) -> Dict:
    """Extract title and content from a live Treasury page."""
    result = {
        "title": "",
        "content": "",
        "success": False,
        "error": None,
    }
    
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        
        if response and response.status == 404:
            result["error"] = "HTTP 404"
            return result
        
        # Wait for content to load
        await asyncio.sleep(1)
        
        # Extract title from page title (cleaner than h1 which is site name)
        page_title = await page.title()
        if " | " in page_title:
            result["title"] = page_title.split(" | ")[0].strip()
        elif " - U.S. Department of the Treasury" in page_title:
            result["title"] = page_title.replace(" - U.S. Department of the Treasury", "").strip()
        else:
            result["title"] = page_title.strip()
        
        # Extract main content from region-content
        content_elem = await page.query_selector(".region-content")
        if not content_elem:
            content_elem = await page.query_selector("main")
        
        if content_elem:
            # Get the HTML to preserve structure
            html = await content_elem.inner_html()
            text = await content_elem.inner_text()
            
            # Convert to markdown-friendly format
            content = convert_html_to_markdown(html, text)
            result["content"] = content
            result["success"] = True
        else:
            result["error"] = "No content element found"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def convert_html_to_markdown(html: str, text: str) -> str:
    """Convert HTML content to markdown format."""
    # Simple conversion - clean up the text
    lines = text.split('\n')
    cleaned = []
    
    skip_patterns = [
        'skip to main content',
        'an official website of the united states',
        "here's how you know",
        'continuing resolution',
        'president donald j. trump has signed',
    ]
    
    nav_items = {'HOME', 'ABOUT', 'ABOUT TREASURY', 'POLICY ISSUES', 'DATA', 
                 'SERVICES', 'NEWS', 'SEARCH', 'BREADCRUMB', 'YEAR IN REVIEW'}
    
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        
        # Skip empty lines at start
        if not stripped and not cleaned:
            continue
        
        # Skip navigation and header items
        if stripped.upper() in nav_items:
            continue
        
        # Skip boilerplate
        skip = False
        for pattern in skip_patterns:
            if pattern in lower:
                skip = True
                break
        if skip:
            continue
        
        # Skip single uppercase words (likely nav)
        if stripped.isupper() and len(stripped) < 40 and ' ' not in stripped:
            continue
        
        cleaned.append(stripped)
    
    # Join and clean up
    content = '\n\n'.join(cleaned)
    
    # Remove excessive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


def update_markdown_file(file_path: Path, new_title: str, new_content: str, dry_run: bool = False) -> bool:
    """Update a markdown file with new content while preserving frontmatter structure."""
    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False
    
    # Read existing file
    existing = file_path.read_text(encoding="utf-8")
    
    # Parse frontmatter
    if existing.startswith("---"):
        parts = existing.split("---", 2)
        if len(parts) >= 3:
            frontmatter_lines = parts[1].strip().split('\n')
            
            # Update title in frontmatter if different
            new_fm_lines = []
            for line in frontmatter_lines:
                if line.startswith("title:"):
                    # Keep the new title from live site
                    new_fm_lines.append(f'title: "{new_title}"')
                else:
                    new_fm_lines.append(line)
            
            # Reconstruct file
            new_frontmatter = '\n'.join(new_fm_lines)
            new_file = f"---\n{new_frontmatter}\n---\n\n{new_content}\n"
            
            if dry_run:
                print(f"  Would update: {file_path}")
                print(f"    New title: {new_title}")
                print(f"    Content length: {len(new_content)} chars")
                return True
            
            file_path.write_text(new_file, encoding="utf-8")
            return True
    
    return False


async def rescrape_pages(files: List[Dict], dry_run: bool = False, max_concurrent: int = 5):
    """Re-scrape all hallucinated pages from live site."""
    print(f"\n{'='*60}")
    print("Re-scraping Pages from Live Treasury.gov")
    print(f"{'='*60}")
    print(f"Files to process: {len(files)}")
    print(f"Dry run: {dry_run}")
    print()
    
    if not files:
        print("No files to process")
        return
    
    success_count = 0
    error_count = 0
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        async def process_file(file_info: Dict) -> Tuple[str, bool, str]:
            async with semaphore:
                file_path = BASE_DIR / file_info["file"]
                url_path = file_info["url"]
                live_url = f"{LIVE_SITE}{url_path}"
                
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                
                try:
                    page = await context.new_page()
                    result = await extract_page_content(page, live_url)
                    
                    if result["success"] and result["content"]:
                        updated = update_markdown_file(
                            file_path, 
                            result["title"], 
                            result["content"],
                            dry_run
                        )
                        if updated:
                            return (file_info["file"], True, "")
                        else:
                            return (file_info["file"], False, "Failed to update file")
                    else:
                        return (file_info["file"], False, result.get("error", "No content"))
                
                finally:
                    await context.close()
        
        # Process all files
        tasks = [process_file(f) for f in files]
        
        completed = 0
        for coro in asyncio.as_completed(tasks):
            file_path, success, error = await coro
            completed += 1
            
            if success:
                success_count += 1
                print(f"  ✓ [{completed}/{len(files)}] {file_path}")
            else:
                error_count += 1
                print(f"  ✗ [{completed}/{len(files)}] {file_path} - {error}")
        
        await browser.close()
    
    print(f"\n{'='*60}")
    print("Re-scrape Complete")
    print(f"{'='*60}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    
    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")


def main():
    parser = argparse.ArgumentParser(
        description="Re-scrape hallucinated pages from live Treasury.gov"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="Number of concurrent browser tabs (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Load hallucinated files
    files = load_hallucinated_files()
    
    if not files:
        return
    
    print(f"Found {len(files)} files to re-scrape")
    
    # Run re-scrape
    asyncio.run(rescrape_pages(files, args.dry_run, args.concurrent))


if __name__ == "__main__":
    main()
