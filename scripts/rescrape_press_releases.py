#!/usr/bin/env python3
"""
Re-scrape hallucinated press releases from live Treasury.gov

Usage:
    python scripts/rescrape_press_releases.py
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent.parent
STAGING_DIR = BASE_DIR / "staging"
LIVE_SITE = "https://home.treasury.gov"


def load_hallucinated_files():
    """Load list of hallucinated press releases from audit report."""
    report_path = STAGING_DIR / "press_release_audit.json"
    if not report_path.exists():
        print(f"Error: {report_path} not found")
        return []
    
    with open(report_path) as f:
        data = json.load(f)
    
    return data.get("hallucinations", [])


async def scrape_press_release(browser, url_path):
    """Scrape a single press release from the live site."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    
    result = {
        "title": "",
        "date": "",
        "content": "",
        "success": False,
    }
    
    try:
        page = await context.new_page()
        url = f"{LIVE_SITE}{url_path}"
        
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        
        if response and response.status == 404:
            result["error"] = "HTTP 404"
            return result
        
        await asyncio.sleep(1)
        
        # Extract title from page title
        page_title = await page.title()
        result["title"] = re.sub(r"\s*\|.*$", "", page_title).strip()
        
        # Get region-content for the full press release
        region = await page.query_selector(".region-content")
        if region:
            text = await region.inner_text()
            lines = text.split('\n')
            
            content_lines = []
            found_date = False
            date_line = ""
            skip_next_title = False
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                
                # Skip navigation items
                if stripped.upper() in ['PRESS RELEASES', 'NEWS', 'HOME']:
                    continue
                
                # Skip archived content notice
                if '(Archived Content)' in stripped:
                    continue
                
                # Look for date line
                if not found_date:
                    for month in ['January', 'February', 'March', 'April', 'May', 'June', 
                                  'July', 'August', 'September', 'October', 'November', 'December']:
                        if month in stripped and len(stripped) < 50:
                            found_date = True
                            date_line = stripped
                            skip_next_title = True
                            break
                    if found_date:
                        continue
                
                # Skip the title line (usually first after date)
                if skip_next_title:
                    skip_next_title = False
                    # Skip if it looks like a repeat of the title
                    if stripped == result["title"] or len(stripped) > 100:
                        continue
                
                if found_date:
                    content_lines.append(stripped)
            
            result["date"] = date_line
            
            # If no date found, try to get all content after title
            if not found_date and len(lines) > 5:
                # Skip first few lines (nav, title) and take the rest
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.upper() in ['PRESS RELEASES', 'NEWS', 'HOME']:
                        continue
                    if '(Archived Content)' in stripped:
                        continue
                    if stripped == result["title"]:
                        continue
                    if stripped:
                        content_lines.append(stripped)
            
            result["content"] = '\n\n'.join(content_lines)
            if result["content"]:
                result["success"] = True
    
    except Exception as e:
        result["error"] = str(e)
    
    finally:
        await context.close()
    
    return result


def update_markdown_file(file_path, new_title, new_date, new_content):
    """Update a markdown file with new content."""
    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False
    
    existing = file_path.read_text(encoding="utf-8")
    
    if not existing.startswith("---"):
        print(f"  No frontmatter: {file_path}")
        return False
    
    parts = existing.split("---", 2)
    if len(parts) < 3:
        return False
    
    frontmatter_lines = parts[1].strip().split('\n')
    
    # Update title in frontmatter
    new_fm_lines = []
    for line in frontmatter_lines:
        if line.startswith("title:"):
            # Escape quotes in title
            safe_title = new_title.replace('"', '\\"')
            new_fm_lines.append(f'title: "{safe_title}"')
        else:
            new_fm_lines.append(line)
    
    new_frontmatter = '\n'.join(new_fm_lines)
    new_file = f"---\n{new_frontmatter}\n---\n\n{new_content}\n"
    
    file_path.write_text(new_file, encoding="utf-8")
    return True


async def rescrape_hallucinations(files, max_concurrent=10):
    """Re-scrape all hallucinated press releases."""
    print(f"\n{'='*60}")
    print("Re-scraping Hallucinated Press Releases")
    print(f"{'='*60}")
    print(f"Files to process: {len(files)}")
    print()
    
    semaphore = asyncio.Semaphore(max_concurrent)
    success_count = 0
    error_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        async def process_file(file_info):
            nonlocal success_count, error_count
            
            async with semaphore:
                file_path = BASE_DIR / file_info["file"]
                url_path = file_info["url"]
                
                result = await scrape_press_release(browser, url_path)
                
                if result["success"] and result["content"]:
                    updated = update_markdown_file(
                        file_path,
                        result["title"],
                        result["date"],
                        result["content"]
                    )
                    if updated:
                        success_count += 1
                        print(f"  ✓ {file_info['file']}")
                        return True
                
                error_count += 1
                print(f"  ✗ {file_info['file']} - {result.get('error', 'No content')}")
                return False
        
        tasks = [process_file(f) for f in files]
        await asyncio.gather(*tasks)
        
        await browser.close()
    
    print(f"\n{'='*60}")
    print("Re-scrape Complete")
    print(f"{'='*60}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")


def main():
    files = load_hallucinated_files()
    
    if not files:
        print("No hallucinated files to process")
        return
    
    print(f"Found {len(files)} hallucinated press releases")
    
    asyncio.run(rescrape_hallucinations(files))


if __name__ == "__main__":
    main()
