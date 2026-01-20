#!/usr/bin/env python3
"""
Playwright-based Content Audit for Hallucination Detection

Uses headless browser to compare local Hugo site content against live Treasury.gov
to detect AI-generated or incorrect content.

Usage:
    # Audit all non-news pages against live site
    python scripts/audit_hallucinations_playwright.py

    # Audit specific files
    python scripts/audit_hallucinations_playwright.py --files content/policy-issues/tax-policy/tax-expenditures.md

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Check for playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    print("Error: playwright not installed. Run:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

# Configuration
BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content"
OUTPUT_DIR = BASE_DIR / "staging"
LIVE_SITE = "https://home.treasury.gov"
LOCAL_SITE = "http://localhost:1313"

# Parallel workers
MAX_CONCURRENT = 10


@dataclass
class PageAuditResult:
    """Result of auditing a single page."""
    file_path: str
    url_path: str
    status: str  # 'ok', 'content_mismatch', 'not_found_live', 'not_found_local', 'error'
    local_title: str = ""
    live_title: str = ""
    local_content_length: int = 0
    live_content_length: int = 0
    similarity_score: float = 1.0
    is_hallucination: bool = False
    local_excerpt: str = ""
    live_excerpt: str = ""
    diff_sample: str = ""
    error_message: str = ""
    live_is_soft_404: bool = False


def extract_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and body from markdown content."""
    frontmatter = {}
    body = content
    
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            
            for line in fm_text.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    frontmatter[key] = value
    
    return frontmatter, body


def get_url_path(frontmatter: Dict, file_path: Path) -> str:
    """Get the URL path for a content file."""
    if "url" in frontmatter:
        return frontmatter["url"]
    
    rel_path = file_path.relative_to(CONTENT_DIR)
    url_path = "/" + str(rel_path).replace(".md", "").replace("_index", "")
    url_path = re.sub(r"/{2,}", "/", url_path)
    
    return url_path


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    
    # Remove common boilerplate
    text = re.sub(r"Skip to main content", "", text, flags=re.IGNORECASE)
    text = re.sub(r"An official website of the United States government", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Here's how you know", "", text, flags=re.IGNORECASE)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip().lower()
    
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    # Use shorter sequences for comparison to handle varying content lengths
    if len(norm1) > 5000:
        norm1 = norm1[:5000]
    if len(norm2) > 5000:
        norm2 = norm2[:5000]
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def is_soft_404(page_text: str, title: str) -> bool:
    """Detect if page content indicates a soft 404 (page not found but returns 200)."""
    # Check if title is just the site name (no page-specific title)
    if title and title.strip() in ["U.S. Department of the Treasury", "Treasury", ""]:
        return True
    
    # Check for explicit not found messages in main content (not header)
    # Look for these phrases after the first 500 chars (skip header)
    lower_text = page_text.lower()
    main_content = lower_text[500:3000] if len(lower_text) > 500 else lower_text
    
    explicit_404_phrases = [
        "page not found",
        "the page you requested could not be found",
        "we couldn't find that page",
        "this page doesn't exist",
        "has been moved or deleted",
        "no longer available",
        "404 error",
    ]
    
    for phrase in explicit_404_phrases:
        if phrase in main_content:
            return True
    
    # Check if the page has very little content (just navigation)
    # Real pages should have substantial content
    if len(page_text) < 500:
        return True
    
    return False


def discover_non_news_files(content_dir: Path) -> List[Path]:
    """Discover all non-news content files (pages that may have hallucinations)."""
    files = []
    
    # Focus on sections that might have generated content
    focus_sections = [
        "about",
        "policy-issues", 
        "services",
        "data",
        "footer",
        "utility",
        "resource-center",
    ]
    
    for section in focus_sections:
        section_path = content_dir / section
        if section_path.exists():
            for md_file in section_path.rglob("*.md"):
                if md_file.name != "_index.md":
                    files.append(md_file)
    
    return files


async def extract_page_content(page: Page, wait_for_js: bool = True) -> Tuple[str, str]:
    """Extract title and main content from a rendered page."""
    # Wait for JavaScript to render content
    if wait_for_js:
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass
        
        # Wait for common content indicators to appear
        try:
            await page.wait_for_selector("h1, .page-title, [role='main'] h1", timeout=5000)
        except:
            pass
        
        # Extra wait for dynamic content
        await asyncio.sleep(1)
    
    # Extract title - try multiple approaches
    title = ""
    try:
        # Treasury site specific selectors
        title_selectors = [
            ".page-title",
            ".content h1",
            "[role='main'] h1", 
            "main h1:first-of-type",
            "article h1",
            "h1.title",
            "h1",
        ]
        
        for selector in title_selectors:
            h1 = await page.query_selector(selector)
            if h1:
                text = await h1.inner_text()
                text = text.strip()
                # Skip if it's just the site name
                if text and text.upper() not in ["U.S. DEPARTMENT OF THE TREASURY", "TREASURY"]:
                    title = text
                    break
        
        # Fallback to page title
        if not title:
            title = await page.title()
            # Clean site name from title
            if " | " in title:
                title = title.split(" | ")[0]
            if " - U.S. Department of the Treasury" in title:
                title = title.replace(" - U.S. Department of the Treasury", "")
            if title.upper() == "U.S. DEPARTMENT OF THE TREASURY":
                title = ""
    except:
        pass
    
    # Extract main content - try Treasury-specific selectors
    content = ""
    try:
        # Best selector for Treasury site - the region-content area
        content_selectors = [
            ".region-content",  # Primary content region
            ".node__content",   # Drupal node content
            ".layout-content",  # Layout content area
            "main article",
            "main",
        ]
        
        for selector in content_selectors:
            elem = await page.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                # Check if this is substantial content (not just nav/header)
                if len(text) > 300:
                    content = text
                    break
        
        # If we still have no content, fall back to body
        if not content:
            content = await page.inner_text("body")
        
        # Clean up the content - remove navigation elements
        lines = content.split('\n')
        cleaned_lines = []
        
        # Track when we've passed the page title
        found_title = False
        in_footer = False
        
        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Skip common navigation/header patterns
            if line_stripped in ['HOME', 'ABOUT', 'ABOUT TREASURY', 'POLICY ISSUES', 'DATA', 
                                 'SERVICES', 'NEWS', 'SEARCH', 'YEAR IN REVIEW', 
                                 'WORKING FAMILIES TAX CUTS', 'BREADCRUMB']:
                continue
            
            # Skip the government banner
            if 'continuing resolution' in line_lower:
                continue
            if 'an official website of the united states' in line_lower:
                continue
            if "here's how you know" in line_lower:
                continue
            
            # Skip footer
            if 'privacy policy' in line_lower and len(line_stripped) < 50:
                in_footer = True
            if in_footer:
                continue
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Skip lines that are just uppercase nav items
            if line_stripped.isupper() and len(line_stripped) < 30:
                continue
            
            cleaned_lines.append(line_stripped)
        
        content = ' '.join(cleaned_lines)
        
    except Exception as e:
        content = ""
    
    return title.strip(), content.strip()


async def audit_page(
    browser: Browser,
    file_path: Path,
    semaphore: asyncio.Semaphore,
    check_local: bool = False,
) -> PageAuditResult:
    """Audit a single page by comparing local markdown to live site."""
    async with semaphore:
        result = PageAuditResult(
            file_path=str(file_path.relative_to(BASE_DIR)),
            url_path="",
            status="ok",
        )
        
        try:
            # Read local markdown file
            content = file_path.read_text(encoding="utf-8")
            frontmatter, body = extract_frontmatter(content)
            
            # Skip drafts
            if frontmatter.get("draft", "").lower() == "true":
                result.status = "ok"
                result.error_message = "Skipped draft"
                return result
            
            url_path = get_url_path(frontmatter, file_path)
            result.url_path = url_path
            result.local_title = frontmatter.get("title", "")
            result.local_content_length = len(body)
            result.local_excerpt = normalize_text(body)[:300]
            
            # Create browser context
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            
            try:
                page = await context.new_page()
                
                # Visit live site
                live_url = f"{LIVE_SITE}{url_path}"
                try:
                    response = await page.goto(live_url, wait_until="domcontentloaded", timeout=30000)
                    
                    if response and response.status == 404:
                        result.status = "not_found_live"
                        result.error_message = "HTTP 404 on live site"
                        return result
                    
                    live_title, live_content = await extract_page_content(page)
                    result.live_title = live_title
                    result.live_content_length = len(live_content)
                    result.live_excerpt = normalize_text(live_content)[:300]
                    
                    # Check for soft 404
                    if is_soft_404(live_content, live_title):
                        result.live_is_soft_404 = True
                        result.status = "not_found_live"
                        result.error_message = "Soft 404 - page shows search/error content"
                        return result
                    
                except Exception as e:
                    result.status = "error"
                    result.error_message = f"Failed to load live page: {e}"
                    return result
                
                # Compare content
                # Use local markdown body vs live rendered content
                result.similarity_score = calculate_similarity(body, live_content)
                
                # Determine if this is a hallucination
                if result.similarity_score < 0.3:
                    result.status = "content_mismatch"
                    result.is_hallucination = True
                    
                    # Create diff sample
                    local_lines = normalize_text(body)[:500].split()[:50]
                    live_lines = normalize_text(live_content)[:500].split()[:50]
                    
                    result.diff_sample = f"LOCAL: {' '.join(local_lines[:20])}...\n\nLIVE: {' '.join(live_lines[:20])}..."
                
                elif result.similarity_score < 0.7:
                    result.status = "content_mismatch"
                    result.diff_sample = f"Similarity: {result.similarity_score:.1%}"
                
                # Check title match
                if result.local_title and result.live_title:
                    title_sim = calculate_similarity(result.local_title, result.live_title)
                    if title_sim < 0.7 and result.status == "ok":
                        result.status = "title_mismatch"
                
            finally:
                await context.close()
                
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
        
        return result


async def run_audit(
    files: List[Path],
    max_concurrent: int = 10,
) -> List[PageAuditResult]:
    """Run the audit on all files using Playwright."""
    print(f"\n{'='*60}")
    print("Playwright Content Audit")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Files to audit: {len(files)}")
    print(f"Concurrent browsers: {max_concurrent}")
    print()
    
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            # Process files
            tasks = []
            for file_path in files:
                task = audit_page(browser, file_path, semaphore)
                tasks.append(task)
            
            # Run with progress reporting
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                completed += 1
                
                # Progress indicator
                if completed % 10 == 0 or completed == len(files):
                    print(f"  Progress: {completed}/{len(files)} ({completed*100//len(files)}%)")
                
                # Report issues immediately
                if result.is_hallucination:
                    print(f"  ⚠️  HALLUCINATION: {result.file_path}")
                elif result.status == "content_mismatch":
                    print(f"  ⚡ Content mismatch: {result.file_path} ({result.similarity_score:.1%})")
                elif result.status == "not_found_live":
                    pass  # Don't spam with not-found messages
        
        finally:
            await browser.close()
    
    return results


def generate_report(results: List[PageAuditResult], output_dir: Path):
    """Generate JSON and Markdown reports."""
    # Count results
    ok_count = sum(1 for r in results if r.status == "ok")
    mismatch_count = sum(1 for r in results if r.status == "content_mismatch")
    not_found_count = sum(1 for r in results if r.status == "not_found_live")
    error_count = sum(1 for r in results if r.status == "error")
    hallucination_count = sum(1 for r in results if r.is_hallucination)
    
    # JSON report
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "ok": ok_count,
            "content_mismatch": mismatch_count,
            "not_found_live": not_found_count,
            "errors": error_count,
            "hallucinations": hallucination_count,
        },
        "hallucinations": [
            {
                "file": r.file_path,
                "url": r.url_path,
                "similarity": r.similarity_score,
                "local_title": r.local_title,
                "live_title": r.live_title,
                "local_excerpt": r.local_excerpt[:200],
                "live_excerpt": r.live_excerpt[:200],
            }
            for r in results if r.is_hallucination
        ],
        "content_mismatches": [
            {
                "file": r.file_path,
                "url": r.url_path,
                "similarity": r.similarity_score,
                "local_title": r.local_title,
                "live_title": r.live_title,
            }
            for r in results if r.status == "content_mismatch" and not r.is_hallucination
        ],
        "not_found_on_live": [
            {
                "file": r.file_path,
                "url": r.url_path,
                "is_soft_404": r.live_is_soft_404,
                "local_title": r.local_title,
            }
            for r in results if r.status == "not_found_live"
        ],
    }
    
    json_path = output_dir / "hallucination_audit.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    
    # Markdown report
    md_lines = [
        "# Hallucination Audit Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total Files Audited | {len(results)} |",
        f"| OK (content matches) | {ok_count} |",
        f"| Content Mismatch | {mismatch_count} |",
        f"| Not Found on Live Site | {not_found_count} |",
        f"| Errors | {error_count} |",
        f"| **HALLUCINATIONS** | **{hallucination_count}** |",
        "",
    ]
    
    # Hallucinations section
    hallucinations = [r for r in results if r.is_hallucination]
    if hallucinations:
        md_lines.extend([
            "## Detected Hallucinations",
            "",
            "These files contain content that does NOT exist on the live Treasury.gov site:",
            "",
        ])
        
        for r in hallucinations:
            md_lines.extend([
                f"### `{r.file_path}`",
                "",
                f"- **URL:** {r.url_path}",
                f"- **Similarity to Live:** {r.similarity_score:.1%}",
                f"- **Local Title:** {r.local_title}",
                f"- **Live Title:** {r.live_title or '(none)'}",
                "",
                "**Local Content Preview:**",
                "```",
                r.local_excerpt[:300] + "...",
                "```",
                "",
                "**Live Content Preview:**",
                "```",
                r.live_excerpt[:300] + "..." if r.live_excerpt else "(empty or search page)",
                "```",
                "",
                "---",
                "",
            ])
    
    # Content mismatches
    mismatches = [r for r in results if r.status == "content_mismatch" and not r.is_hallucination]
    if mismatches:
        md_lines.extend([
            "## Content Mismatches (Non-Hallucination)",
            "",
            "These files have some content differences but may not be hallucinations:",
            "",
            "| File | Similarity | Local Title | Live Title |",
            "|------|------------|-------------|------------|",
        ])
        
        for r in mismatches[:20]:
            local_t = r.local_title[:30] + "..." if len(r.local_title) > 30 else r.local_title
            live_t = r.live_title[:30] + "..." if len(r.live_title) > 30 else r.live_title
            md_lines.append(f"| `{r.file_path}` | {r.similarity_score:.1%} | {local_t} | {live_t} |")
        
        if len(mismatches) > 20:
            md_lines.append(f"\n*...and {len(mismatches) - 20} more*")
        md_lines.append("")
    
    # Not found
    not_found = [r for r in results if r.status == "not_found_live"]
    if not_found:
        md_lines.extend([
            "## Pages Not Found on Live Site",
            "",
            "These local files have no corresponding page on the live site (may be new or generated content):",
            "",
        ])
        
        for r in not_found[:30]:
            soft_404 = " (soft 404)" if r.live_is_soft_404 else ""
            md_lines.append(f"- `{r.file_path}` → {r.url_path}{soft_404}")
        
        if len(not_found) > 30:
            md_lines.append(f"\n*...and {len(not_found) - 30} more*")
        md_lines.append("")
    
    # Recommendations
    md_lines.extend([
        "## Recommendations",
        "",
        "1. **Hallucinations**: Delete or replace these files - they contain AI-generated content not from the live site.",
        "",
        "2. **Not Found**: Review whether these are:",
        "   - New content to be published",
        "   - Placeholder/template content that should be removed",
        "   - Pages that were removed from the live site",
        "",
        "3. **Content Mismatches**: Review for accuracy - may be intentional updates or need re-scraping.",
        "",
    ])
    
    md_path = output_dir / "hallucination_audit.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    
    print(f"\nReports saved to:")
    print(f"  {json_path}")
    print(f"  {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Audit content for hallucinations using Playwright",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="Specific files to audit (default: all non-news pages)",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Number of concurrent browser tabs (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Output directory for reports (default: {OUTPUT_DIR})",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Discover files to audit
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        print("Discovering non-news content files...")
        files = discover_non_news_files(CONTENT_DIR)
        print(f"Found {len(files)} files to audit")
    
    if not files:
        print("No files to audit")
        return
    
    # Run audit
    results = asyncio.run(run_audit(files, args.concurrent))
    
    # Generate reports
    generate_report(results, output_dir)
    
    # Summary
    hallucinations = [r for r in results if r.is_hallucination]
    not_found = [r for r in results if r.status == "not_found_live"]
    
    print(f"\n{'='*60}")
    print("Audit Complete")
    print(f"{'='*60}")
    print(f"Total files audited: {len(results)}")
    print(f"HALLUCINATIONS DETECTED: {len(hallucinations)}")
    print(f"Pages not found on live: {len(not_found)}")
    
    if hallucinations:
        print(f"\n!! {len(hallucinations)} HALLUCINATIONS DETECTED !!")
        for r in hallucinations:
            print(f"   - {r.file_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
