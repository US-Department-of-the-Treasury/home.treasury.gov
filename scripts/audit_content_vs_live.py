#!/usr/bin/env python3
"""
Treasury Content Audit Script

Compares local markdown content files against the live Treasury.gov site
to detect discrepancies, hallucinations, or incorrect content.

Usage:
    python scripts/audit_content_vs_live.py --workers 50 --deep-sample 500
    python scripts/audit_content_vs_live.py --workers 50 --quick-only
    python scripts/audit_content_vs_live.py --workers 50 --content-type news

Features:
    - 50 parallel workers using asyncio
    - JSON API for news content (fast, accurate)
    - HTML scraping for non-news content
    - Quick title/date check on all files
    - Deep text comparison on random sample
    - JSON and Markdown report output
"""

import argparse
import asyncio
import html
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urljoin

import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

# Configuration
BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content"
OUTPUT_DIR = BASE_DIR / "staging"
LIVE_SITE = "https://home.treasury.gov"
JSON_API_BASE = f"{LIVE_SITE}/jsonapi/node/news"

# Rate limiting
REQUEST_DELAY = 0.1  # 100ms between requests per worker
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # Initial retry delay in seconds

# Headers
HEADERS = {
    "User-Agent": "Treasury Hugo Audit Bot/1.0 (Content Verification)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}

JSON_HEADERS = {
    "User-Agent": "Treasury Hugo Audit Bot/1.0 (Content Verification)",
    "Accept": "application/vnd.api+json",
}


@dataclass
class AuditResult:
    """Result of auditing a single content file."""
    file_path: str
    url_path: str
    content_type: str  # 'news' or 'page'
    status: str  # 'ok', 'title_mismatch', 'date_mismatch', 'content_mismatch', 'not_found', 'error'
    local_title: str = ""
    live_title: str = ""
    local_date: str = ""
    live_date: str = ""
    similarity_score: float = 1.0
    deep_checked: bool = False
    error_message: str = ""
    diff_sample: str = ""


@dataclass
class AuditSummary:
    """Summary of the entire audit."""
    timestamp: str
    total_files: int = 0
    quick_checked: int = 0
    deep_checked: int = 0
    ok_count: int = 0
    title_mismatch_count: int = 0
    date_mismatch_count: int = 0
    content_mismatch_count: int = 0
    not_found_count: int = 0
    error_count: int = 0
    potential_hallucinations: int = 0
    results: List[AuditResult] = field(default_factory=list)


def extract_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and body from markdown content."""
    frontmatter = {}
    body = content
    
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            
            # Parse simple YAML
            for line in fm_text.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    frontmatter[key] = value
    
    return frontmatter, body


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace and formatting."""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove markdown formatting
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # Italic
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # Headers
    
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
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def html_to_text(html_content: str) -> str:
    """Convert HTML to plain text for comparison."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style elements
    for element in soup(["script", "style", "nav", "header", "footer"]):
        element.decompose()
    
    return soup.get_text(separator=" ", strip=True)


def classify_content(file_path: Path) -> str:
    """Classify content as 'news' or 'page' based on path."""
    rel_path = str(file_path.relative_to(CONTENT_DIR))
    
    news_sections = [
        "news/press-releases",
        "news/featured-stories",
        "news/statements-remarks",
        "news/readouts",
        "news/testimonies",
        "news/webcasts",
        "news/media-advisories",
        "news/weekly-public-schedule",
        "news/weekly-schedule-updates",
        "news/recent-highlights",
    ]
    
    for section in news_sections:
        if rel_path.startswith(section):
            return "news"
    
    return "page"


def get_url_path(frontmatter: Dict, file_path: Path) -> str:
    """Get the URL path for a content file."""
    # Check for explicit URL in frontmatter
    if "url" in frontmatter:
        return frontmatter["url"]
    
    # Generate from file path
    rel_path = file_path.relative_to(CONTENT_DIR)
    url_path = "/" + str(rel_path).replace(".md", "").replace("_index", "")
    
    # Clean up double slashes
    url_path = re.sub(r"/{2,}", "/", url_path)
    
    return url_path


async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict,
    semaphore: asyncio.Semaphore,
    is_json: bool = False,
) -> Tuple[Optional[str], int]:
    """Fetch URL with retry logic and rate limiting."""
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                await asyncio.sleep(REQUEST_DELAY)
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    status = response.status
                    
                    if status == 200:
                        if is_json:
                            data = await response.json()
                            return json.dumps(data), status
                        else:
                            return await response.text(), status
                    
                    if status in (429, 503):
                        # Rate limited or service unavailable - retry with backoff
                        delay = RETRY_DELAY * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    
                    if status == 404:
                        return None, status
                    
                    # Other errors
                    return None, status
                    
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None, 0
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None, -1
        
        return None, 0


# Global cache for API data - populated once at start
API_CACHE: Dict[str, Dict] = {}  # url_path -> item data
API_CACHE_BY_SLUG: Dict[str, Dict] = {}  # slug -> item data


async def prefetch_api_data(session: aiohttp.ClientSession, limit: int = 20000) -> int:
    """Prefetch all news items from API into cache for fast lookup."""
    global API_CACHE, API_CACHE_BY_SLUG
    
    print("Prefetching news data from API (this may take a few minutes)...")
    
    url = f"{JSON_API_BASE}?sort=-field_news_publication_date&page%5Blimit%5D=50"
    total_fetched = 0
    page = 0
    
    while total_fetched < limit:
        page += 1
        try:
            async with session.get(url, headers=JSON_HEADERS, timeout=60) as response:
                if response.status != 200:
                    print(f"   API returned {response.status}, stopping prefetch")
                    break
                
                data = await response.json()
                items = data.get("data", [])
                
                if not items:
                    break
                
                for item in items:
                    attrs = item.get("attributes", {})
                    path = attrs.get("path", {})
                    alias = path.get("alias", "") if isinstance(path, dict) else ""
                    
                    if alias:
                        API_CACHE[alias] = item
                        slug = alias.rstrip("/").split("/")[-1].lower()
                        API_CACHE_BY_SLUG[slug] = item
                
                total_fetched += len(items)
                
                if page % 10 == 0:
                    print(f"   Fetched {total_fetched} items...")
                
                # Get next page
                links = data.get("links", {})
                next_link = links.get("next")
                if next_link:
                    url = next_link.get("href") if isinstance(next_link, dict) else next_link
                else:
                    break
                    
        except Exception as e:
            print(f"   Error fetching API page {page}: {e}")
            break
    
    print(f"   Cached {len(API_CACHE)} news items from API")
    return len(API_CACHE)


async def audit_news_item(
    session: aiohttp.ClientSession,
    file_path: Path,
    frontmatter: Dict,
    body: str,
    url_path: str,
    semaphore: asyncio.Semaphore,
    do_deep_check: bool,
) -> AuditResult:
    """Audit a news content item using cached API data."""
    result = AuditResult(
        file_path=str(file_path.relative_to(BASE_DIR)),
        url_path=url_path,
        content_type="news",
        status="ok",
        local_title=frontmatter.get("title", ""),
        local_date=frontmatter.get("date", "")[:10] if frontmatter.get("date") else "",
        deep_checked=do_deep_check,
    )
    
    # Look up in cache first (no network request needed)
    item = API_CACHE.get(url_path)
    
    if not item:
        # Try by slug
        slug = url_path.rstrip("/").split("/")[-1].lower()
        item = API_CACHE_BY_SLUG.get(slug)
    
    if not item:
        # Cache miss - this item may be new or have a different path
        # Mark as not_found in cache (we already fetched all available items)
        result.status = "not_found"
        result.error_message = "Not in API cache (may be new content)"
        return result
    
    try:
        attrs = item.get("attributes", {})
        
        # Extract live title
        result.live_title = attrs.get("title", "")
        
        # Extract live date
        pub_date = attrs.get("field_news_publication_date", "")
        result.live_date = pub_date[:10] if pub_date else ""
        
        # Check title match
        if normalize_text(result.local_title) != normalize_text(result.live_title):
            result.status = "title_mismatch"
        
        # Check date match
        if result.local_date and result.live_date:
            if result.local_date != result.live_date:
                if result.status == "ok":
                    result.status = "date_mismatch"
        
        # Deep content check
        if do_deep_check:
            body_field = attrs.get("field_news_body", {})
            live_html = ""
            if isinstance(body_field, dict):
                live_html = body_field.get("value", "")
            elif body_field:
                live_html = str(body_field)
            
            live_text = html_to_text(live_html)
            result.similarity_score = calculate_similarity(body, live_text)
            
            if result.similarity_score < 0.7:
                result.status = "content_mismatch"
                # Create diff sample
                local_preview = normalize_text(body)[:200]
                live_preview = normalize_text(live_text)[:200]
                result.diff_sample = f"Local: {local_preview}...\nLive: {live_preview}..."
        
    except Exception as e:
        result.status = "error"
        result.error_message = str(e)
    
    return result


async def audit_page_item(
    session: aiohttp.ClientSession,
    file_path: Path,
    frontmatter: Dict,
    body: str,
    url_path: str,
    semaphore: asyncio.Semaphore,
    do_deep_check: bool,
) -> AuditResult:
    """Audit a non-news page using HTML scraping."""
    result = AuditResult(
        file_path=str(file_path.relative_to(BASE_DIR)),
        url_path=url_path,
        content_type="page",
        status="ok",
        local_title=frontmatter.get("title", ""),
        local_date=frontmatter.get("date", "")[:10] if frontmatter.get("date") else "",
        deep_checked=do_deep_check,
    )
    
    # Fetch the live page
    page_url = f"{LIVE_SITE}{url_path}"
    content, status = await fetch_with_retry(session, page_url, HEADERS, semaphore)
    
    if status == 404 or not content:
        result.status = "not_found"
        result.error_message = f"HTTP {status}" if status else "Connection error"
        return result
    
    try:
        soup = BeautifulSoup(content, "html.parser")
        
        # Extract title - prefer h1 in main content, then page title
        # Treasury site structure: look for h1 in main content area
        main_content = soup.find("main") or soup.find("article") or soup.find(".content") or soup
        title_elem = main_content.find("h1")
        
        if title_elem:
            result.live_title = title_elem.get_text(strip=True)
        else:
            # Fall back to <title> tag
            title_elem = soup.find("title")
            if title_elem:
                result.live_title = title_elem.get_text(strip=True)
                # Clean up title if it includes site name
                if " | " in result.live_title:
                    result.live_title = result.live_title.split(" | ")[0].strip()
                # Treasury site uses " - " separator too
                if " - U.S. Department of the Treasury" in result.live_title:
                    result.live_title = result.live_title.replace(" - U.S. Department of the Treasury", "").strip()
                # If still generic, mark as not found
                if result.live_title == "U.S. Department of the Treasury":
                    result.live_title = ""
        
        # Detect soft 404 - page returns 200 but shows homepage/search interface
        # Treasury site shows "Enter search term" when a page isn't found
        page_text = soup.get_text()
        if "Enter search term" in page_text[:500] or "advanced search" in page_text[:500].lower():
            # This is likely a soft 404 - the page shows the search/homepage instead
            if not result.live_title:
                result.status = "not_found"
                result.error_message = "Soft 404 - page shows homepage/search instead of content"
                return result
        
        # Check title match
        if result.local_title and result.live_title:
            title_sim = calculate_similarity(result.local_title, result.live_title)
            if title_sim < 0.8:
                result.status = "title_mismatch"
        elif not result.live_title:
            # No title found on live site
            result.status = "not_found"
            result.error_message = "No title found on live page"
            return result
        
        # Deep content check
        if do_deep_check:
            # Extract main content
            main_content = soup.find("main") or soup.find("article") or soup.find(".content")
            if main_content:
                live_text = main_content.get_text(separator=" ", strip=True)
            else:
                live_text = soup.get_text(separator=" ", strip=True)
            
            result.similarity_score = calculate_similarity(body, live_text)
            
            if result.similarity_score < 0.7:
                result.status = "content_mismatch"
                local_preview = normalize_text(body)[:200]
                live_preview = normalize_text(live_text)[:200]
                result.diff_sample = f"Local: {local_preview}...\nLive: {live_preview}..."
        
    except Exception as e:
        result.status = "error"
        result.error_message = str(e)
    
    return result


async def audit_file(
    session: aiohttp.ClientSession,
    file_path: Path,
    semaphore: asyncio.Semaphore,
    do_deep_check: bool,
) -> AuditResult:
    """Audit a single content file."""
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
    except Exception as e:
        return AuditResult(
            file_path=str(file_path.relative_to(BASE_DIR)),
            url_path="",
            content_type="unknown",
            status="error",
            error_message=f"Failed to read file: {e}",
        )
    
    frontmatter, body = extract_frontmatter(content)
    
    # Skip drafts
    if frontmatter.get("draft", "").lower() == "true":
        return AuditResult(
            file_path=str(file_path.relative_to(BASE_DIR)),
            url_path="",
            content_type="unknown",
            status="ok",
            error_message="Skipped draft",
        )
    
    url_path = get_url_path(frontmatter, file_path)
    content_type = classify_content(file_path)
    
    if content_type == "news":
        return await audit_news_item(
            session, file_path, frontmatter, body, url_path, semaphore, do_deep_check
        )
    else:
        return await audit_page_item(
            session, file_path, frontmatter, body, url_path, semaphore, do_deep_check
        )


def discover_content_files(content_dir: Path, content_type: Optional[str] = None) -> List[Path]:
    """Discover all content markdown files."""
    files = []
    
    for md_file in content_dir.rglob("*.md"):
        # Skip index files for listing pages
        if md_file.name == "_index.md":
            continue
        
        # Filter by content type if specified
        if content_type:
            file_type = classify_content(md_file)
            if content_type == "news" and file_type != "news":
                continue
            if content_type == "pages" and file_type != "page":
                continue
        
        files.append(md_file)
    
    return files


async def run_audit(
    workers: int = 50,
    deep_sample: int = 500,
    quick_only: bool = False,
    content_type: Optional[str] = None,
    api_limit: int = 5000,
) -> AuditSummary:
    """Run the full content audit."""
    print(f"\n{'='*60}")
    print("Treasury Content Audit")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Workers: {workers}")
    print(f"Deep sample size: {deep_sample if not quick_only else 0}")
    print(f"Content filter: {content_type or 'all'}")
    print()
    
    # Discover files
    print("Discovering content files...")
    files = discover_content_files(CONTENT_DIR, content_type)
    print(f"Found {len(files)} content files")
    
    # Select deep check sample
    deep_check_files: Set[Path] = set()
    if not quick_only and deep_sample > 0:
        sample_size = min(deep_sample, len(files))
        deep_check_files = set(random.sample(files, sample_size))
        print(f"Selected {len(deep_check_files)} files for deep content check")
    
    # Create summary
    summary = AuditSummary(
        timestamp=datetime.now().isoformat(),
        total_files=len(files),
    )
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(workers)
    
    # Create HTTP session
    connector = aiohttp.TCPConnector(limit=workers, limit_per_host=workers)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Prefetch news data from API for fast lookup (limited to most recent items)
        news_count = sum(1 for f in files if classify_content(f) == "news")
        if news_count > 0:
            await prefetch_api_data(session, limit=api_limit)
        
        # Create tasks
        tasks = []
        for file_path in files:
            do_deep = file_path in deep_check_files
            task = audit_file(session, file_path, semaphore, do_deep)
            tasks.append(task)
        
        # Run with progress bar
        print(f"\nAuditing {len(files)} files with {workers} workers...")
        results = []
        
        for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Auditing"):
            result = await coro
            results.append(result)
            
            # Update summary counts
            summary.quick_checked += 1
            if result.deep_checked:
                summary.deep_checked += 1
            
            if result.status == "ok":
                summary.ok_count += 1
            elif result.status == "title_mismatch":
                summary.title_mismatch_count += 1
            elif result.status == "date_mismatch":
                summary.date_mismatch_count += 1
            elif result.status == "content_mismatch":
                summary.content_mismatch_count += 1
                if result.similarity_score < 0.5:
                    summary.potential_hallucinations += 1
            elif result.status == "not_found":
                summary.not_found_count += 1
            elif result.status == "error":
                summary.error_count += 1
    
    summary.results = results
    return summary


def generate_json_report(summary: AuditSummary, output_path: Path):
    """Generate JSON report."""
    # Organize results by category
    report = {
        "timestamp": summary.timestamp,
        "summary": {
            "total_files": summary.total_files,
            "quick_checked": summary.quick_checked,
            "deep_checked": summary.deep_checked,
            "ok_count": summary.ok_count,
            "title_mismatch_count": summary.title_mismatch_count,
            "date_mismatch_count": summary.date_mismatch_count,
            "content_mismatch_count": summary.content_mismatch_count,
            "not_found_count": summary.not_found_count,
            "error_count": summary.error_count,
            "potential_hallucinations": summary.potential_hallucinations,
        },
        "discrepancies": {
            "title_mismatch": [],
            "date_mismatch": [],
            "content_mismatch": [],
            "not_found": [],
            "potential_hallucinations": [],
            "errors": [],
        },
    }
    
    for result in summary.results:
        result_dict = {
            "file": result.file_path,
            "url": result.url_path,
            "type": result.content_type,
            "local_title": result.local_title,
            "live_title": result.live_title,
            "local_date": result.local_date,
            "live_date": result.live_date,
            "similarity": result.similarity_score,
            "error": result.error_message,
        }
        
        if result.status == "title_mismatch":
            report["discrepancies"]["title_mismatch"].append(result_dict)
        elif result.status == "date_mismatch":
            report["discrepancies"]["date_mismatch"].append(result_dict)
        elif result.status == "content_mismatch":
            report["discrepancies"]["content_mismatch"].append(result_dict)
            if result.similarity_score < 0.5:
                report["discrepancies"]["potential_hallucinations"].append(result_dict)
        elif result.status == "not_found":
            report["discrepancies"]["not_found"].append(result_dict)
        elif result.status == "error":
            report["discrepancies"]["errors"].append(result_dict)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"JSON report saved to: {output_path}")


def generate_markdown_report(summary: AuditSummary, output_path: Path):
    """Generate Markdown report."""
    lines = [
        "# Treasury Content Audit Report",
        "",
        f"**Generated:** {summary.timestamp}",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total Files | {summary.total_files:,} |",
        f"| Quick Checked | {summary.quick_checked:,} |",
        f"| Deep Checked | {summary.deep_checked:,} |",
        f"| OK | {summary.ok_count:,} |",
        f"| Title Mismatch | {summary.title_mismatch_count:,} |",
        f"| Date Mismatch | {summary.date_mismatch_count:,} |",
        f"| Content Mismatch | {summary.content_mismatch_count:,} |",
        f"| Not Found on Live | {summary.not_found_count:,} |",
        f"| Errors | {summary.error_count:,} |",
        f"| **Potential Hallucinations** | **{summary.potential_hallucinations}** |",
        "",
    ]
    
    # Calculate pass rate
    if summary.quick_checked > 0:
        pass_rate = (summary.ok_count / summary.quick_checked) * 100
        lines.append(f"**Pass Rate:** {pass_rate:.1f}%")
        lines.append("")
    
    # Potential Hallucinations (most critical)
    hallucinations = [r for r in summary.results if r.status == "content_mismatch" and r.similarity_score < 0.5]
    if hallucinations:
        lines.append("## Potential Hallucinations (Critical)")
        lines.append("")
        lines.append("These files have content that differs significantly from the live site (<50% similarity):")
        lines.append("")
        for result in hallucinations[:20]:  # Limit to top 20
            lines.append(f"### `{result.file_path}`")
            lines.append("")
            lines.append(f"- **URL:** {result.url_path}")
            lines.append(f"- **Similarity:** {result.similarity_score:.1%}")
            lines.append(f"- **Local Title:** {result.local_title}")
            lines.append(f"- **Live Title:** {result.live_title}")
            if result.diff_sample:
                lines.append("")
                lines.append("**Content Sample:**")
                lines.append("```")
                lines.append(result.diff_sample)
                lines.append("```")
            lines.append("")
        
        if len(hallucinations) > 20:
            lines.append(f"*...and {len(hallucinations) - 20} more. See JSON report for full list.*")
            lines.append("")
    
    # Title Mismatches
    title_mismatches = [r for r in summary.results if r.status == "title_mismatch"]
    if title_mismatches:
        lines.append("## Title Mismatches")
        lines.append("")
        lines.append("| File | Local Title | Live Title |")
        lines.append("|------|-------------|------------|")
        for result in title_mismatches[:50]:
            local = result.local_title[:40] + "..." if len(result.local_title) > 40 else result.local_title
            live = result.live_title[:40] + "..." if len(result.live_title) > 40 else result.live_title
            lines.append(f"| `{result.file_path}` | {local} | {live} |")
        
        if len(title_mismatches) > 50:
            lines.append("")
            lines.append(f"*...and {len(title_mismatches) - 50} more. See JSON report for full list.*")
        lines.append("")
    
    # Date Mismatches
    date_mismatches = [r for r in summary.results if r.status == "date_mismatch"]
    if date_mismatches:
        lines.append("## Date Mismatches")
        lines.append("")
        lines.append("| File | Local Date | Live Date |")
        lines.append("|------|------------|-----------|")
        for result in date_mismatches[:50]:
            lines.append(f"| `{result.file_path}` | {result.local_date} | {result.live_date} |")
        
        if len(date_mismatches) > 50:
            lines.append("")
            lines.append(f"*...and {len(date_mismatches) - 50} more. See JSON report for full list.*")
        lines.append("")
    
    # Not Found
    not_found = [r for r in summary.results if r.status == "not_found"]
    if not_found:
        lines.append("## Not Found on Live Site")
        lines.append("")
        lines.append("These local files have no corresponding page on the live site:")
        lines.append("")
        for result in not_found[:30]:
            lines.append(f"- `{result.file_path}` ({result.url_path})")
        
        if len(not_found) > 30:
            lines.append("")
            lines.append(f"*...and {len(not_found) - 30} more. See JSON report for full list.*")
        lines.append("")
    
    # Content Mismatches (non-hallucination)
    content_mismatches = [r for r in summary.results if r.status == "content_mismatch" and r.similarity_score >= 0.5]
    if content_mismatches:
        lines.append("## Content Mismatches (Moderate)")
        lines.append("")
        lines.append("These files have some content differences (50-70% similarity):")
        lines.append("")
        lines.append("| File | Similarity | Notes |")
        lines.append("|------|------------|-------|")
        for result in content_mismatches[:30]:
            lines.append(f"| `{result.file_path}` | {result.similarity_score:.1%} | {result.error_message or '-'} |")
        
        if len(content_mismatches) > 30:
            lines.append("")
            lines.append(f"*...and {len(content_mismatches) - 30} more. See JSON report for full list.*")
        lines.append("")
    
    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
        "1. **Potential Hallucinations**: Review all items marked as potential hallucinations immediately. These may contain AI-generated or incorrect content.",
        "",
        "2. **Title Mismatches**: Verify if title changes are intentional updates or sync issues.",
        "",
        "3. **Not Found**: These may be new content not yet on the live site, or pages that have been removed/moved.",
        "",
        "4. **Date Mismatches**: Check if date format or timezone handling differs between systems.",
        "",
    ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Markdown report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Audit local content against live Treasury.gov",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full audit with 50 workers and 500 deep checks
    python scripts/audit_content_vs_live.py --workers 50 --deep-sample 500

    # Quick check only (title/date, no content comparison)
    python scripts/audit_content_vs_live.py --workers 50 --quick-only

    # Audit only news content
    python scripts/audit_content_vs_live.py --workers 50 --content-type news
        """,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=50,
        help="Number of parallel workers (default: 50)",
    )
    parser.add_argument(
        "--deep-sample",
        type=int,
        default=500,
        help="Number of files for deep content comparison (default: 500)",
    )
    parser.add_argument(
        "--quick-only",
        action="store_true",
        help="Only do quick title/date checks, no content comparison",
    )
    parser.add_argument(
        "--content-type",
        choices=["news", "pages", "all"],
        default="all",
        help="Filter by content type (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Output directory for reports (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--api-limit",
        type=int,
        default=5000,
        help="Max items to prefetch from API (default: 5000, covers ~1 year of content)",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    content_type = None if args.content_type == "all" else args.content_type
    
    # Run audit
    start_time = time.time()
    summary = asyncio.run(
        run_audit(
            workers=args.workers,
            deep_sample=args.deep_sample,
            quick_only=args.quick_only,
            content_type=content_type,
            api_limit=args.api_limit,
        )
    )
    elapsed = time.time() - start_time
    
    # Generate reports
    print(f"\n{'='*60}")
    print("Generating Reports")
    print(f"{'='*60}")
    
    json_path = output_dir / "audit_results.json"
    md_path = output_dir / "audit_report.md"
    
    generate_json_report(summary, json_path)
    generate_markdown_report(summary, md_path)
    
    # Print summary
    print(f"\n{'='*60}")
    print("Audit Complete")
    print(f"{'='*60}")
    print(f"Duration: {elapsed:.1f} seconds")
    print(f"Files checked: {summary.quick_checked:,}")
    print(f"Deep checks: {summary.deep_checked:,}")
    print()
    print("Results:")
    print(f"  OK: {summary.ok_count:,}")
    print(f"  Title mismatches: {summary.title_mismatch_count:,}")
    print(f"  Date mismatches: {summary.date_mismatch_count:,}")
    print(f"  Content mismatches: {summary.content_mismatch_count:,}")
    print(f"  Not found on live: {summary.not_found_count:,}")
    print(f"  Errors: {summary.error_count:,}")
    print(f"  POTENTIAL HALLUCINATIONS: {summary.potential_hallucinations}")
    print()
    print(f"Reports saved to:")
    print(f"  {json_path}")
    print(f"  {md_path}")
    
    # Exit with error if hallucinations found
    if summary.potential_hallucinations > 0:
        print(f"\n!! WARNING: {summary.potential_hallucinations} potential hallucinations detected!")
        sys.exit(1)


if __name__ == "__main__":
    main()
