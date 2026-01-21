#!/usr/bin/env python3
"""Debug script to understand Treasury live site content extraction."""

import asyncio
import sys

from playwright.async_api import async_playwright


async def debug_page(url: str):
    """Debug a single page to understand content extraction."""
    print(f"\n{'='*60}")
    print(f"Debugging: {url}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        page = await context.new_page()
        
        try:
            print("Loading page...")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"HTTP Status: {response.status}")
            
            print("Waiting for network idle...")
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            print("Extra wait for JS rendering...")
            await asyncio.sleep(2)
            
            # Get page title
            title = await page.title()
            print(f"\nPage Title: {title}")
            
            # Try to find h1
            h1_selectors = [
                "h1",
                ".page-title",
                "[role='main'] h1",
                "main h1",
            ]
            
            print("\nH1 Elements Found:")
            for selector in h1_selectors:
                elements = await page.query_selector_all(selector)
                for elem in elements:
                    text = await elem.inner_text()
                    print(f"  {selector}: '{text[:100]}...' " if len(text) > 100 else f"  {selector}: '{text}'")
            
            # Check main content area
            print("\nMain Content Areas:")
            content_selectors = [
                ".field--name-body",
                ".node__content",
                "[role='main'] .content",
                ".layout-content",
                "main",
            ]
            
            for selector in content_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    preview = text[:500].replace('\n', ' ')
                    print(f"  {selector}: {len(text)} chars")
                    print(f"    Content: '{preview}...'")
            
            # Check if this looks like a search/404 page
            body_text = await page.inner_text("body")
            print(f"\nFull body length: {len(body_text)} chars")
            
            if "enter search term" in body_text.lower()[:500]:
                print("WARNING: Looks like a search/404 page!")
            else:
                print("Page appears to have real content")
            
            # Take screenshot for verification
            screenshot_path = "/Users/ludwitt/home.treasury.gov/staging/debug_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"\nScreenshot saved to: {screenshot_path}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://home.treasury.gov/about/general-information/role-of-the-treasury"
    
    asyncio.run(debug_page(url))
