#!/usr/bin/env python3
"""
Press Release Audit - Compare local press releases to live Treasury.gov

Uses 50 parallel Playwright browsers to audit all press releases.

Usage:
    python scripts/audit_press_releases.py
    python scripts/audit_press_releases.py --limit 1000  # Test with subset
    python scripts/audit_press_releases.py --workers 50  # Adjust parallelism
"""

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from playwright.async_api import async_playwright, Browser
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

# Default workers
DEFAULT_WORKERS = 50


@dataclass
class AuditResult:
    """Result of auditing a single press release."""
    file_path: str
    url_path: str
    status: str  # 'ok', 'title_mismatch', 'content_mismatch', 'date_mismatch', 'not_found', 'error'
    local_title: str = ""
    live_title: str = ""
    local_date: str = ""
    live_date: str = ""
    similarity_score: float = 1.0
    is_hallucination: bool = False
    error_message: str = ""


def extract_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and body from markdown."""
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
    """Get URL path from frontmatter or file path."""
    if "url" in frontmatter:
        return frontmatter["url"]
    
    # Derive from file path
    rel_path = file_path.relative_to(CONTENT_DIR)
    url_path = "/" + str(rel_path).replace(".md", "")
    return url_path


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.strip().lower()
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts."""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_text(text1)[:3000]
    norm2 = normalize_text(text2)[:3000]
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Remove common suffixes
    title = re.sub(r"\s*\|\s*U\.?S\.?\s*Department of the Treasury.*$", "", title, flags=re.I)
    title = re.sub(r"\s*-\s*U\.?S\.?\s*Department of the Treasury.*$", "", title, flags=re.I)
    return title.strip()


def discover_press_releases(content_dir: Path, limit: Optional[int] = None) -> List[Path]:
    """Discover all press release files."""
    pr_dir = content_dir / "news" / "press-releases"
    files = []
    
    for md_file in pr_dir.rglob("*.md"):
        if md_file.name != "_index.md":
            files.append(md_file)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    if limit:
        files = files[:limit]
    
    return files


async def audit_press_release(
    browser: Browser,
    file_path: Path,
    semaphore: asyncio.Semaphore,
) -> AuditResult:
    """Audit a single press release."""
    async with semaphore:
        result = AuditResult(
            file_path=str(file_path.relative_to(BASE_DIR)),
            url_path="",
            status="ok",
        )
        
        try:
            # Read local file
            content = file_path.read_text(encoding="utf-8")
            frontmatter, body = extract_frontmatter(content)
            
            url_path = get_url_path(frontmatter, file_path)
            result.url_path = url_path
            result.local_title = frontmatter.get("title", "")
            result.local_date = frontmatter.get("date", "")[:10]  # Just date part
            
            # Create browser context
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            
            try:
                page = await context.new_page()
                live_url = f"{LIVE_SITE}{url_path}"
                
                try:
                    response = await page.goto(live_url, wait_until="domcontentloaded", timeout=30000)
                    
                    if response and response.status == 404:
                        result.status = "not_found"
                        result.error_message = "HTTP 404"
                        return result
                    
                    # Wait for content
                    await asyncio.sleep(0.5)
                    
                    # Extract title
                    page_title = await page.title()
                    result.live_title = normalize_title(page_title)
                    
                    # Try to get the article title from h1
                    try:
                        h1 = await page.query_selector("article h1, .press-release-title, main h1")
                        if h1:
                            result.live_title = await h1.inner_text()
                    except:
                        pass
                    
                    # Check for soft 404
                    body_text = await page.inner_text("body")
                    if "page not found" in body_text.lower()[:500]:
                        result.status = "not_found"
                        result.error_message = "Soft 404"
                        return result
                    
                    # Extract date from page
                    try:
                        date_elem = await page.query_selector(".press-release-date, .date, time, .field--name-created")
                        if date_elem:
                            date_text = await date_elem.inner_text()
                            result.live_date = date_text.strip()[:10]
                    except:
                        pass
                    
                    # Get main content from region-content (the actual press release)
                    live_content = ""
                    try:
                        content_elem = await page.query_selector(".region-content")
                        if content_elem:
                            text = await content_elem.inner_text()
                            # Skip header navigation and clean content
                            lines = text.split('\n')
                            content_lines = []
                            found_date = False
                            for line in lines:
                                stripped = line.strip()
                                if not stripped:
                                    continue
                                # Skip navigation items
                                if stripped.upper() in ['PRESS RELEASES', 'NEWS', 'HOME']:
                                    continue
                                # Start capturing after we see a date-like line
                                if not found_date and any(month in stripped for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                                    found_date = True
                                    continue
                                if found_date:
                                    content_lines.append(stripped)
                            live_content = ' '.join(content_lines)
                    except:
                        pass
                    
                    # Compare titles
                    title_sim = calculate_similarity(result.local_title, result.live_title)
                    if title_sim < 0.8:
                        result.status = "title_mismatch"
                    
                    # Compare content
                    if live_content and body:
                        result.similarity_score = calculate_similarity(body, live_content)
                        if result.similarity_score < 0.3:
                            result.status = "content_mismatch"
                            result.is_hallucination = True
                        elif result.similarity_score < 0.6:
                            result.status = "content_mismatch"
                    
                except Exception as e:
                    result.status = "error"
                    result.error_message = str(e)[:100]
                    
            finally:
                await context.close()
                
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)[:100]
        
        return result


async def run_audit(
    files: List[Path],
    max_workers: int = 50,
) -> List[AuditResult]:
    """Run audit on all files with parallel workers."""
    print(f"\n{'='*70}")
    print("Press Release Content Audit")
    print(f"{'='*70}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Files to audit: {len(files)}")
    print(f"Parallel workers: {max_workers}")
    print()
    
    results = []
    semaphore = asyncio.Semaphore(max_workers)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            tasks = [audit_press_release(browser, f, semaphore) for f in files]
            
            # Process with progress
            completed = 0
            issues_found = 0
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                completed += 1
                
                # Track issues
                if result.status not in ["ok", "not_found"]:
                    issues_found += 1
                
                # Progress every 100 or on issues
                if completed % 100 == 0 or completed == len(files):
                    pct = completed * 100 // len(files)
                    print(f"  Progress: {completed:,}/{len(files):,} ({pct}%) - Issues: {issues_found}")
                
                # Report hallucinations immediately
                if result.is_hallucination:
                    print(f"  ⚠️  HALLUCINATION: {result.file_path} ({result.similarity_score:.1%})")
                elif result.status == "title_mismatch":
                    pass  # Don't spam with title mismatches
                elif result.status == "content_mismatch":
                    print(f"  ⚡ Content mismatch: {result.file_path} ({result.similarity_score:.1%})")
        
        finally:
            await browser.close()
    
    return results


def generate_report(results: List[AuditResult], output_dir: Path):
    """Generate JSON and Markdown reports."""
    # Counts
    ok_count = sum(1 for r in results if r.status == "ok")
    title_mismatch = sum(1 for r in results if r.status == "title_mismatch")
    content_mismatch = sum(1 for r in results if r.status == "content_mismatch")
    not_found = sum(1 for r in results if r.status == "not_found")
    errors = sum(1 for r in results if r.status == "error")
    hallucinations = sum(1 for r in results if r.is_hallucination)
    
    # JSON report
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "ok": ok_count,
            "title_mismatch": title_mismatch,
            "content_mismatch": content_mismatch,
            "not_found": not_found,
            "errors": errors,
            "hallucinations": hallucinations,
        },
        "hallucinations": [
            {
                "file": r.file_path,
                "url": r.url_path,
                "similarity": r.similarity_score,
                "local_title": r.local_title,
                "live_title": r.live_title,
            }
            for r in results if r.is_hallucination
        ],
        "content_mismatches": [
            {
                "file": r.file_path,
                "url": r.url_path,
                "similarity": r.similarity_score,
            }
            for r in results if r.status == "content_mismatch" and not r.is_hallucination
        ],
        "title_mismatches": [
            {
                "file": r.file_path,
                "local_title": r.local_title,
                "live_title": r.live_title,
            }
            for r in results if r.status == "title_mismatch"
        ][:50],  # Limit to 50
    }
    
    json_path = output_dir / "press_release_audit.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    
    # Markdown report
    md_lines = [
        "# Press Release Audit Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total Audited | {len(results):,} |",
        f"| OK | {ok_count:,} |",
        f"| Title Mismatch | {title_mismatch:,} |",
        f"| Content Mismatch | {content_mismatch:,} |",
        f"| Not Found on Live | {not_found:,} |",
        f"| Errors | {errors:,} |",
        f"| **HALLUCINATIONS** | **{hallucinations}** |",
        "",
    ]
    
    # Hallucinations
    if hallucinations > 0:
        md_lines.extend([
            "## Detected Hallucinations",
            "",
            "These files have content that significantly differs from live site:",
            "",
        ])
        
        for r in results:
            if r.is_hallucination:
                md_lines.extend([
                    f"### `{r.file_path}`",
                    f"- URL: {r.url_path}",
                    f"- Similarity: {r.similarity_score:.1%}",
                    f"- Local title: {r.local_title}",
                    f"- Live title: {r.live_title}",
                    "",
                ])
    
    # Content mismatches
    mismatches = [r for r in results if r.status == "content_mismatch" and not r.is_hallucination]
    if mismatches:
        md_lines.extend([
            "## Content Mismatches",
            "",
            "| File | Similarity |",
            "|------|------------|",
        ])
        for r in mismatches[:30]:
            md_lines.append(f"| `{r.file_path}` | {r.similarity_score:.1%} |")
        if len(mismatches) > 30:
            md_lines.append(f"\n*...and {len(mismatches) - 30} more*")
        md_lines.append("")
    
    md_path = output_dir / "press_release_audit.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    
    print(f"\nReports saved to:")
    print(f"  {json_path}")
    print(f"  {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Audit press releases against live site")
    parser.add_argument("--limit", type=int, help="Limit number of files to audit")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Parallel workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Discover files
    print("Discovering press releases...")
    files = discover_press_releases(CONTENT_DIR, args.limit)
    print(f"Found {len(files):,} press releases")
    
    if not files:
        print("No files to audit")
        return
    
    # Run audit
    results = asyncio.run(run_audit(files, args.workers))
    
    # Generate reports
    generate_report(results, output_dir)
    
    # Summary
    hallucinations = [r for r in results if r.is_hallucination]
    mismatches = [r for r in results if r.status == "content_mismatch"]
    
    print(f"\n{'='*70}")
    print("Audit Complete")
    print(f"{'='*70}")
    print(f"Total: {len(results):,}")
    print(f"Hallucinations: {len(hallucinations)}")
    print(f"Content mismatches: {len(mismatches)}")
    
    if hallucinations:
        print(f"\n⚠️  {len(hallucinations)} HALLUCINATIONS DETECTED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
