#!/usr/bin/env python3
"""
Site Mirror - Main orchestrator for site mirroring and comparison.

This script orchestrates the complete workflow:
1. Crawl source site
2. Crawl target site (or use existing Hugo build)
3. Run text comparison
4. Run visual comparison
5. Generate consolidated report
"""

import argparse
import asyncio
import json
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from urllib.parse import urlparse
import httpx

# Import our modules
from crawler import Crawler, CrawlState, SitemapParser, DEFAULT_HEADERS
from text_comparator import TextComparator, ComparisonReport, generate_html_report as generate_text_html
from visual_comparator import VisualComparator, VisualReport, generate_html_report as generate_visual_html


@dataclass
class MirrorConfig:
    """Configuration for the mirror operation."""
    source_url: str
    target_url: Optional[str] = None
    target_dir: Optional[Path] = None  # For local Hugo build
    output_dir: Path = Path("./mirror_output")
    crawl_depth: int = 10
    rate_limit: float = 5.0
    max_concurrent: int = 10
    verify_ssl: bool = True
    include_assets: bool = True
    text_threshold: float = 0.9
    visual_threshold: float = 0.01
    viewports: list[str] = field(default_factory=lambda: ["desktop"])
    num_workers: int = 8
    skip_crawl: bool = False
    skip_source_crawl: bool = False
    skip_target_crawl: bool = False
    skip_text: bool = False
    skip_visual: bool = False
    pages_only: bool = False  # Compare webpages only (from sitemaps, excludes assets)
    focus_path: Optional[str] = None  # Focus on specific path prefix
    use_target_sitemap: bool = False  # Use target's sitemap for source URL discovery


@dataclass
class MirrorReport:
    """Consolidated mirror report."""
    config: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    crawl_summary: dict = field(default_factory=dict)
    text_summary: dict = field(default_factory=dict)
    visual_summary: dict = field(default_factory=dict)
    overall_status: str = "unknown"  # pass, warning, fail


class SiteMirror:
    """Main orchestrator for site mirroring and comparison."""

    def __init__(self, config: MirrorConfig):
        self.config = config
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        self.source_crawl_dir = self.output_dir / "crawl_source"
        self.target_crawl_dir = self.output_dir / "crawl_target"
        self.text_report_dir = self.output_dir / "text_comparison"
        self.visual_report_dir = self.output_dir / "visual_comparison"

    async def run(self) -> MirrorReport:
        """Execute the complete mirror workflow."""
        report = MirrorReport(config=asdict(self.config))

        print("=" * 60)
        print("SITE MIRROR - COMPLETE WORKFLOW")
        print("=" * 60)
        print(f"Source: {self.config.source_url}")
        if self.config.target_url:
            print(f"Target: {self.config.target_url}")
        elif self.config.target_dir:
            print(f"Target: {self.config.target_dir} (local)")
        if self.config.focus_path:
            print(f"Focus: {self.config.focus_path}/*")
        if self.config.use_target_sitemap:
            print(f"URL Discovery: Using target's sitemap (source sitemap blocked)")
        print(f"Output: {self.config.output_dir}")
        print()

        # Quick URL-only comparison mode
        if self.config.pages_only:
            await self._run_pages_only_comparison()
            return report

        # Phase 1: Crawl
        if not self.config.skip_crawl:
            print("\n" + "=" * 60)
            print("PHASE 1: CRAWLING")
            print("=" * 60)

            # Crawl source (unless skipped)
            if not self.config.skip_source_crawl:
                source_state = await self._crawl_source()
                report.crawl_summary["source"] = {
                    "urls_discovered": len(source_state.discovered_urls),
                    "urls_crawled": len(source_state.crawled_urls),
                    "urls_failed": len(source_state.failed_urls)
                }
            else:
                print("Skipping source crawl (--skip-source-crawl)")

            # Crawl target (unless skipped)
            if self.config.target_url and not self.config.skip_target_crawl:
                target_state = await self._crawl_target()
                report.crawl_summary["target"] = {
                    "urls_discovered": len(target_state.discovered_urls),
                    "urls_crawled": len(target_state.crawled_urls),
                    "urls_failed": len(target_state.failed_urls)
                }
            elif self.config.skip_target_crawl:
                print("Skipping target crawl (--skip-target-crawl)")

        # Phase 2: Text Comparison
        if not self.config.skip_text:
            print("\n" + "=" * 60)
            print("PHASE 2: TEXT COMPARISON")
            print("=" * 60)

            text_report = self._run_text_comparison()
            report.text_summary = {
                "total_urls": text_report.total_urls,
                "identical": text_report.identical,
                "similar": text_report.similar,
                "different": text_report.different,
                "missing_in_target": text_report.missing_in_target,
                "missing_in_source": text_report.missing_in_source
            }

        # Phase 3: Visual Comparison
        if not self.config.skip_visual:
            print("\n" + "=" * 60)
            print("PHASE 3: VISUAL COMPARISON")
            print("=" * 60)

            # Get sample URLs for visual comparison
            sample_urls = self._get_sample_urls()

            for viewport in self.config.viewports:
                visual_report = await self._run_visual_comparison(sample_urls, viewport)
                report.visual_summary[viewport] = {
                    "total_pages": visual_report.total_pages,
                    "identical": visual_report.identical,
                    "similar": visual_report.similar,
                    "different": visual_report.different,
                    "errors": visual_report.errors
                }

        # Calculate overall status
        report.overall_status = self._calculate_overall_status(report)

        # Save consolidated report
        self._save_report(report)

        return report

    async def _crawl_source(self) -> CrawlState:
        """Crawl the source site."""
        print(f"\nCrawling source: {self.config.source_url}")

        crawler = Crawler(
            base_url=self.config.source_url,
            output_dir=self.source_crawl_dir,
            rate_limit=self.config.rate_limit,
            max_depth=self.config.crawl_depth,
            max_concurrent=self.config.max_concurrent,
            verify_ssl=self.config.verify_ssl,
            include_assets=self.config.include_assets,
            focus_path=self.config.focus_path
        )

        # Use target's sitemap to discover URLs if source sitemap is blocked
        use_sitemap_from = self.config.target_url if self.config.use_target_sitemap else None
        return await crawler.crawl(use_sitemap_from=use_sitemap_from)

    async def _crawl_target(self) -> CrawlState:
        """Crawl the target site."""
        print(f"\nCrawling target: {self.config.target_url}")

        crawler = Crawler(
            base_url=self.config.target_url,
            output_dir=self.target_crawl_dir,
            rate_limit=self.config.rate_limit,
            max_depth=self.config.crawl_depth,
            max_concurrent=self.config.max_concurrent,
            verify_ssl=self.config.verify_ssl,
            include_assets=self.config.include_assets,
            focus_path=self.config.focus_path
        )

        return await crawler.crawl()

    async def _run_pages_only_comparison(self) -> dict:
        """
        Quick webpage URL comparison - uses local crawl data or sitemaps.
        Filters out asset URLs (PDFs, images, etc.).
        Optionally compares text content if --skip-text is not set.
        """
        print("\n" + "=" * 60)
        print("PAGES-ONLY COMPARISON (--pages-only)")
        print("=" * 60)
        print("Comparing webpage URLs only (excluding PDFs, images, etc.)")

        # Check for local crawl state files first
        source_state_file = self.source_crawl_dir / "crawl_state.json"
        target_state_file = self.target_crawl_dir / "crawl_state.json"

        source_paths = set()
        target_paths = set()

        if source_state_file.exists() and target_state_file.exists():
            # Use local crawl state
            print("\nUsing local crawl data...")

            source_state = json.loads(source_state_file.read_text())
            source_urls = set(source_state.get("crawled_urls", []))
            source_paths = self._urls_to_paths(source_urls, self.config.source_url)
            print(f"  Source: {len(source_urls)} crawled URLs, {len(source_paths)} webpages")

            target_state = json.loads(target_state_file.read_text())
            target_urls = set(target_state.get("crawled_urls", []))
            target_paths = self._urls_to_paths(target_urls, self.config.target_url)
            print(f"  Target: {len(target_urls)} crawled URLs, {len(target_paths)} webpages")

        else:
            # Fetch from sitemaps
            print("\nNo local crawl data found, fetching sitemaps...")

            async with httpx.AsyncClient(
                timeout=60,
                verify=self.config.verify_ssl,
                headers=DEFAULT_HEADERS,
                follow_redirects=True
            ) as client:
                sitemap_parser = SitemapParser(client)

                # Get target URLs first (target is usually localhost, faster)
                print(f"\nFetching target sitemap: {self.config.target_url}/sitemap.xml", flush=True)
                target_urls = await sitemap_parser.parse(f"{self.config.target_url}/sitemap.xml")
                target_paths = self._urls_to_paths(target_urls, self.config.target_url)
                print(f"  Found {len(target_urls)} total URLs, {len(target_paths)} webpages")

                # Get source URLs (use target sitemap if --use-target-sitemap)
                if self.config.use_target_sitemap:
                    print(f"\nUsing target sitemap for source URL discovery (--use-target-sitemap)")
                    source_paths = target_paths.copy()
                    source_urls = target_urls
                    print(f"  Using {len(source_paths)} URLs from target sitemap")
                else:
                    print(f"\nFetching source sitemap: {self.config.source_url}/sitemap.xml", flush=True)
                    source_urls = await sitemap_parser.parse(f"{self.config.source_url}/sitemap.xml")
                    source_paths = self._urls_to_paths(source_urls, self.config.source_url)
                    print(f"  Found {len(source_urls)} total URLs, {len(source_paths)} webpages")

        # Apply focus path filter if set
        if self.config.focus_path:
            focus = self.config.focus_path.rstrip('/')
            source_paths = {p for p in source_paths if p.startswith(focus) or p.startswith(focus + '/')}
            target_paths = {p for p in target_paths if p.startswith(focus) or p.startswith(focus + '/')}
            print(f"\nFiltered to focus path '{focus}':")
            print(f"  Source: {len(source_paths)} URLs")
            print(f"  Target: {len(target_paths)} URLs")

        # Compare sets
        missing_in_target = source_paths - target_paths
        missing_in_source = target_paths - source_paths
        common = source_paths & target_paths

        result = {
            "source_url": self.config.source_url,
            "target_url": self.config.target_url,
            "focus_path": self.config.focus_path,
            "source_total": len(source_paths),
            "target_total": len(target_paths),
            "common": len(common),
            "missing_in_target": sorted(missing_in_target),
            "missing_in_source": sorted(missing_in_source),
            "text_comparison": None,
        }

        # Print URL summary
        print("\n" + "=" * 60)
        print("URL COMPARISON RESULTS")
        print("=" * 60)
        print(f"Source URLs:        {len(source_paths)}")
        print(f"Target URLs:        {len(target_paths)}")
        print(f"Common:             {len(common)}")
        print(f"Missing in target:  {len(missing_in_target)}")
        print(f"Missing in source:  {len(missing_in_source)}")

        # Text comparison for common URLs (unless --skip-text)
        if not self.config.skip_text and common:
            print("\n" + "=" * 60)
            print("TEXT COMPARISON (common pages)")
            print("=" * 60)

            # Check if local crawl data exists
            source_pages_dir = self.source_crawl_dir / "pages"
            target_pages_dir = self.target_crawl_dir / "pages"

            if source_pages_dir.exists() and target_pages_dir.exists():
                print("Using local crawl data...")
                text_results = self._compare_text_for_paths_local(sorted(common))
            else:
                print("Fetching pages live...")
                text_results = await self._compare_text_for_urls(sorted(common))

            result["text_comparison"] = text_results

            # Save text comparison to text_comparison/ directory (same as normal workflow)
            self.text_report_dir.mkdir(parents=True, exist_ok=True)
            text_report_path = self.text_report_dir / "text_comparison.json"
            text_report_path.write_text(json.dumps(text_results, indent=2))
            print(f"Text comparison JSON: {text_report_path}")

            # Generate text comparison HTML report
            text_html = self._generate_text_comparison_html(text_results, sorted(common))
            text_html_path = self.text_report_dir / "text_comparison.html"
            text_html_path.write_text(text_html)
            print(f"Text comparison HTML: {text_html_path}")

        # Save URL comparison results
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        report_path = self.output_dir / "url_comparison.json"
        report_path.write_text(json.dumps(result, indent=2))
        print(f"\nURL comparison JSON: {report_path}")

        # Save missing in target list
        if missing_in_target:
            missing_target_path = self.output_dir / "missing_in_target.txt"
            missing_target_path.write_text("\n".join(sorted(missing_in_target)))
            print(f"Missing in target: {missing_target_path}")

        # Save missing in source list
        if missing_in_source:
            missing_source_path = self.output_dir / "missing_in_source.txt"
            missing_source_path.write_text("\n".join(sorted(missing_in_source)))
            print(f"Missing in source: {missing_source_path}")

        # Generate URL comparison HTML report
        html = self._generate_pages_only_html_report(result)
        html_path = self.output_dir / "url_comparison.html"
        html_path.write_text(html)
        print(f"HTML report: {html_path}")

        return result

    def _compare_text_for_paths_local(self, paths: list[str]) -> dict:
        """
        Compare text content from locally crawled files.
        Uses parallel workers via ThreadPoolExecutor.
        """
        from difflib import SequenceMatcher
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {
            "total": len(paths),
            "identical": 0,
            "similar": 0,
            "different": 0,
            "errors": 0,
            "details": [],
        }

        def compare_single(path: str) -> dict | None:
            """Compare a single path from local files."""
            # Convert URL path to local file path
            # /news/press-releases/jy123 -> pages/news/press-releases/jy123.html or pages/news/press-releases/jy123/index.html
            clean_path = path.strip('/')

            # Try different file patterns
            possible_source_paths = [
                self.source_crawl_dir / "pages" / f"{clean_path}.html",
                self.source_crawl_dir / "pages" / clean_path / "index.html",
                self.source_crawl_dir / "pages" / f"{clean_path}/index.html",
            ]
            possible_target_paths = [
                self.target_crawl_dir / "pages" / f"{clean_path}.html",
                self.target_crawl_dir / "pages" / clean_path / "index.html",
                self.target_crawl_dir / "pages" / f"{clean_path}/index.html",
            ]

            source_file = None
            target_file = None

            for p in possible_source_paths:
                if p.exists():
                    source_file = p
                    break

            for p in possible_target_paths:
                if p.exists():
                    target_file = p
                    break

            if not source_file or not target_file:
                return {"path": path, "error": "file_not_found"}

            try:
                source_html = source_file.read_text(errors='ignore')
                target_html = target_file.read_text(errors='ignore')

                source_text = self._extract_text(source_html)
                target_text = self._extract_text(target_html)

                similarity = SequenceMatcher(None, source_text, target_text).ratio()

                if similarity >= 0.99:
                    status = "identical"
                elif similarity >= self.config.text_threshold:
                    status = "similar"
                else:
                    status = "different"

                return {
                    "path": path,
                    "similarity": round(similarity, 4),
                    "status": status,
                }

            except Exception as e:
                return {"path": path, "error": str(e)}

        # Run comparisons in parallel using ThreadPoolExecutor
        print(f"  Comparing {len(paths)} pages with {self.config.num_workers} workers (local files)...")

        completed = 0
        with ThreadPoolExecutor(max_workers=self.config.num_workers) as executor:
            futures = {executor.submit(compare_single, path): path for path in paths}

            for future in as_completed(futures):
                r = future.result()
                completed += 1

                if completed % 50 == 0 or completed == len(paths):
                    print(f"  Progress: {completed}/{len(paths)} pages compared", flush=True)

                if r is None:
                    continue
                if "error" in r:
                    results["errors"] += 1
                else:
                    results["details"].append(r)
                    if r["status"] == "identical":
                        results["identical"] += 1
                    elif r["status"] == "similar":
                        results["similar"] += 1
                    else:
                        results["different"] += 1

        # Print summary
        print(f"\nText comparison complete:")
        print(f"  Identical: {results['identical']}")
        print(f"  Similar:   {results['similar']}")
        print(f"  Different: {results['different']}")
        print(f"  Errors:    {results['errors']}")

        return results

    async def _compare_text_for_urls(self, paths: list[str]) -> dict:
        """
        Fetch and compare text content for a list of URL paths (live fetch).
        Uses parallel workers with rate limiting.
        Returns comparison statistics and details.
        """
        from difflib import SequenceMatcher
        from crawler import AsyncRateLimiter

        results = {
            "total": len(paths),
            "identical": 0,
            "similar": 0,
            "different": 0,
            "errors": 0,
            "details": [],
        }

        # Use rate limiter for controlled parallelism
        rate_limiter = AsyncRateLimiter(
            rate_limit=self.config.rate_limit,
            max_concurrent=self.config.num_workers
        )

        # Progress tracking
        completed = [0]
        lock = asyncio.Lock()

        async def compare_single(path: str, client: httpx.AsyncClient) -> dict | None:
            """Compare a single URL pair."""
            source_url = f"{self.config.source_url.rstrip('/')}{path}"
            target_url = f"{self.config.target_url.rstrip('/')}{path}"

            await rate_limiter.acquire()
            try:
                # Fetch both pages in parallel
                source_resp, target_resp = await asyncio.gather(
                    client.get(source_url),
                    client.get(target_url),
                    return_exceptions=True
                )

                if isinstance(source_resp, Exception) or isinstance(target_resp, Exception):
                    return {"path": path, "error": "fetch_failed"}

                if source_resp.status_code != 200 or target_resp.status_code != 200:
                    return {"path": path, "error": f"status_{source_resp.status_code}_{target_resp.status_code}"}

                # Extract text content
                source_text = self._extract_text(source_resp.text)
                target_text = self._extract_text(target_resp.text)

                # Calculate similarity
                similarity = SequenceMatcher(None, source_text, target_text).ratio()

                # Categorize
                if similarity >= 0.99:
                    status = "identical"
                elif similarity >= self.config.text_threshold:
                    status = "similar"
                else:
                    status = "different"

                return {
                    "path": path,
                    "similarity": round(similarity, 4),
                    "status": status,
                }

            except Exception as e:
                return {"path": path, "error": str(e)}
            finally:
                rate_limiter.release()
                # Update progress
                async with lock:
                    completed[0] += 1
                    if completed[0] % 10 == 0 or completed[0] == len(paths):
                        print(f"  Progress: {completed[0]}/{len(paths)} pages compared", flush=True)

        # Run comparisons in parallel
        async with httpx.AsyncClient(
            timeout=30,
            verify=self.config.verify_ssl,
            headers=DEFAULT_HEADERS,
            follow_redirects=True
        ) as client:
            print(f"  Comparing {len(paths)} pages with {self.config.num_workers} workers (live fetch)...")
            tasks = [compare_single(path, client) for path in paths]
            comparison_results = await asyncio.gather(*tasks)

        # Aggregate results
        for r in comparison_results:
            if r is None:
                continue
            if "error" in r:
                results["errors"] += 1
            else:
                results["details"].append(r)
                if r["status"] == "identical":
                    results["identical"] += 1
                elif r["status"] == "similar":
                    results["similar"] += 1
                else:
                    results["different"] += 1

        # Print summary
        print(f"\nText comparison complete:")
        print(f"  Identical: {results['identical']}")
        print(f"  Similar:   {results['similar']}")
        print(f"  Different: {results['different']}")
        print(f"  Errors:    {results['errors']}")

        return results

    def _extract_text(self, html: str) -> str:
        """Extract main text content from HTML, stripping nav/footer/scripts."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Remove non-content elements
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        # Try to find main content
        main = soup.find('main') or soup.find('article') or soup.find(id='content') or soup.find(class_='content')
        if main:
            text = main.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _generate_text_comparison_html(self, text_results: dict, paths: list[str]) -> str:
        """Generate HTML report for text comparison (compatible with normal workflow)."""
        total = text_results.get('total', 0)
        identical = text_results.get('identical', 0)
        similar = text_results.get('similar', 0)
        different = text_results.get('different', 0)
        errors = text_results.get('errors', 0)

        # Determine status
        if total > 0:
            identical_pct = identical / total
            if identical_pct >= 0.9:
                status = "PASS"
                status_color = "#28a745"
            elif identical_pct >= 0.7:
                status = "WARNING"
                status_color = "#ffc107"
            else:
                status = "FAIL"
                status_color = "#dc3545"
        else:
            status = "NO DATA"
            status_color = "#6c757d"

        # Build details table
        details = text_results.get('details', [])
        rows_html = ""
        for d in sorted(details, key=lambda x: x.get('similarity', 0)):
            sim = d.get('similarity', 0)
            path = d.get('path', '')
            st = d.get('status', 'unknown')
            color = "#28a745" if st == "identical" else "#ffc107" if st == "similar" else "#dc3545"
            rows_html += f'<tr><td><code>{path}</code></td><td style="color: {color};">{sim:.1%}</td><td>{st.upper()}</td></tr>\n'

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Text Comparison Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 40px; max-width: 1400px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .status {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 8px;
            color: white;
            font-size: 1.5em;
            font-weight: bold;
            background: {status_color};
        }}
        .section {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .section h2 {{ margin-top: 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }}
        .stat {{ background: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #e9ecef; }}
        code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
        .table-container {{ max-height: 600px; overflow-y: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Text Comparison Report</h1>
        <div class="status">{status}</div>
        <p>Generated: {datetime.now().isoformat()}</p>
        <p>Source: {self.config.source_url} | Target: {self.config.target_url}</p>
    </div>

    <div class="section">
        <h2>Summary</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Compared</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #28a745;">{identical}</div>
                <div class="stat-label">Identical (≥99%)</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #ffc107;">{similar}</div>
                <div class="stat-label">Similar (≥{self.config.text_threshold:.0%})</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #dc3545;">{different}</div>
                <div class="stat-label">Different</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #6c757d;">{errors}</div>
                <div class="stat-label">Errors</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>All Comparisons ({len(details)} pages)</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr><th>Path</th><th>Similarity</th><th>Status</th></tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

    def _urls_to_paths(self, urls: set[str], base_url: str) -> set[str]:
        """Convert full URLs to paths, filtering to webpages only (no assets)."""
        # Asset extensions to exclude
        asset_extensions = {
            # Documents
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.rtf',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp', '.tiff',
            # Media
            '.mp3', '.mp4', '.wav', '.avi', '.mov', '.wmv', '.flv', '.webm',
            # Data/config
            '.json', '.xml', '.csv', '.txt', '.yaml', '.yml',
            # Code/web assets
            '.js', '.css', '.woff', '.woff2', '.ttf', '.eot', '.map',
            # Archives
            '.zip', '.tar', '.gz', '.rar', '.7z',
        }

        paths = set()
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/') or '/'

            # Check if path has an asset extension
            path_lower = path.lower()
            is_asset = any(path_lower.endswith(ext) for ext in asset_extensions)

            # Include if it's a webpage (no extension, .html, .htm, or directory)
            if not is_asset:
                paths.add(path)

        return paths

    def _generate_pages_only_html_report(self, result: dict) -> str:
        """Generate HTML report for pages-only comparison."""
        missing_target_count = len(result['missing_in_target'])
        missing_source_count = len(result['missing_in_source'])

        status = "PASS"
        status_color = "#28a745"
        if missing_target_count > 0:
            pct_missing = missing_target_count / max(result['source_total'], 1)
            if pct_missing > 0.1:
                status = "FAIL"
                status_color = "#dc3545"
            else:
                status = "WARNING"
                status_color = "#ffc107"

        missing_target_html = "\n".join(f"<li><code>{p}</code></li>" for p in result['missing_in_target'][:100])
        if missing_target_count > 100:
            missing_target_html += f"<li>... and {missing_target_count - 100} more</li>"

        missing_source_html = "\n".join(f"<li><code>{p}</code></li>" for p in result['missing_in_source'][:100])
        if missing_source_count > 100:
            missing_source_html += f"<li>... and {missing_source_count - 100} more</li>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>URL Comparison Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 40px; max-width: 1200px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .status {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 8px;
            color: white;
            font-size: 1.5em;
            font-weight: bold;
            background: {status_color};
        }}
        .section {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .section h2 {{ margin-top: 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }}
        .stat {{ background: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        ul {{ max-height: 400px; overflow-y: auto; }}
        code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>URL Comparison Report</h1>
        <div class="status">{status}</div>
        <p>Generated: {datetime.now().isoformat()}</p>
    </div>

    <div class="section">
        <h2>Configuration</h2>
        <p><strong>Source:</strong> {result['source_url']}</p>
        <p><strong>Target:</strong> {result['target_url']}</p>
        {f"<p><strong>Focus:</strong> {result['focus_path']}</p>" if result['focus_path'] else ""}
    </div>

    <div class="section">
        <h2>Summary</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{result['source_total']}</div>
                <div class="stat-label">Source URLs</div>
            </div>
            <div class="stat">
                <div class="stat-value">{result['target_total']}</div>
                <div class="stat-label">Target URLs</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #28a745;">{result['common']}</div>
                <div class="stat-label">Common</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #dc3545;">{missing_target_count}</div>
                <div class="stat-label">Missing in Target</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #6c757d;">{missing_source_count}</div>
                <div class="stat-label">Missing in Source</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Missing in Target ({missing_target_count})</h2>
        <p>These URLs exist in source but not in target:</p>
        <ul>{missing_target_html if missing_target_html else "<li>None</li>"}</ul>
    </div>

    <div class="section">
        <h2>Missing in Source ({missing_source_count})</h2>
        <p>These URLs exist in target but not in source (new pages):</p>
        <ul>{missing_source_html if missing_source_html else "<li>None</li>"}</ul>
    </div>
{self._generate_text_comparison_section(result.get('text_comparison'))}
</body>
</html>"""

    def _generate_text_comparison_section(self, text_comparison: dict | None) -> str:
        """Generate HTML section for text comparison results."""
        if not text_comparison:
            return ""

        # Build details table for non-identical pages
        different_pages = [d for d in text_comparison.get('details', []) if d['status'] != 'identical']
        details_html = ""
        if different_pages:
            rows = "\n".join(
                f'<tr><td><code>{d["path"]}</code></td><td>{d["similarity"]:.1%}</td><td>{d["status"].upper()}</td></tr>'
                for d in sorted(different_pages, key=lambda x: x['similarity'])[:50]
            )
            details_html = f"""
    <h3>Pages with Differences</h3>
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="background: #e9ecef;"><th style="padding: 8px; text-align: left;">Path</th><th style="padding: 8px;">Similarity</th><th style="padding: 8px;">Status</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    {f'<p><em>Showing first 50 of {len(different_pages)} pages with differences</em></p>' if len(different_pages) > 50 else ''}
"""

        return f"""
    <div class="section">
        <h2>Text Comparison</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{text_comparison.get('total', 0)}</div>
                <div class="stat-label">Total Compared</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #28a745;">{text_comparison.get('identical', 0)}</div>
                <div class="stat-label">Identical</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #ffc107;">{text_comparison.get('similar', 0)}</div>
                <div class="stat-label">Similar</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #dc3545;">{text_comparison.get('different', 0)}</div>
                <div class="stat-label">Different</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #6c757d;">{text_comparison.get('errors', 0)}</div>
                <div class="stat-label">Errors</div>
            </div>
        </div>
        {details_html}
    </div>
"""

    def _run_text_comparison(self) -> ComparisonReport:
        """Run text content comparison."""
        self.text_report_dir.mkdir(parents=True, exist_ok=True)

        comparator = TextComparator(
            source_dir=self.source_crawl_dir,
            target_dir=self.target_crawl_dir,
            similarity_threshold=self.config.text_threshold,
            num_workers=self.config.num_workers,
            focus_path=self.config.focus_path
        )

        report = comparator.compare_all()

        # Save reports
        report.save(self.text_report_dir / "text_comparison.json")
        generate_text_html(report, self.text_report_dir / "text_comparison.html")

        return report

    async def _run_visual_comparison(self, urls: list[str], viewport: str) -> VisualReport:
        """Run visual comparison for a viewport."""
        viewport_dir = self.visual_report_dir / viewport
        viewport_dir.mkdir(parents=True, exist_ok=True)

        comparator = VisualComparator(
            source_base_url=self.config.source_url,
            target_base_url=self.config.target_url or f"file://{self.config.target_dir}",
            output_dir=viewport_dir,
            viewport=viewport,
            threshold=self.config.visual_threshold
        )

        report = await comparator.compare_urls(urls)

        # Save reports
        report.save(viewport_dir / "visual_comparison.json")
        generate_visual_html(report, viewport_dir / "visual_comparison.html")

        return report

    def _get_sample_urls(self, max_urls: int = 100) -> list[str]:
        """Get sample URLs for visual comparison."""
        state_file = self.source_crawl_dir / "crawl_state.json"

        if not state_file.exists():
            if self.config.focus_path:
                return [self.config.focus_path]
            return ["/"]

        state = json.loads(state_file.read_text())
        urls = list(state.get("crawled_urls", []))

        # Filter to HTML pages only
        html_urls = [u for u in urls if not any(u.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.css', '.js'])]

        # Extract paths
        from urllib.parse import urlparse
        paths = list(set(urlparse(u).path for u in html_urls))

        # Filter by focus path if set
        if self.config.focus_path:
            focus = self.config.focus_path.rstrip('/')
            paths = [p for p in paths if p.startswith(focus) or p.startswith(focus + '/')]

        # Sample URLs
        if len(paths) > max_urls:
            import random
            paths = random.sample(paths, max_urls)

        return paths

    def _calculate_overall_status(self, report: MirrorReport) -> str:
        """Calculate overall status based on comparisons."""
        # Check text comparison
        text = report.text_summary
        if text:
            total = text.get("total_urls", 0)
            if total > 0:
                identical_pct = text.get("identical", 0) / total
                missing_pct = text.get("missing_in_target", 0) / total

                if missing_pct > 0.1:  # >10% missing
                    return "fail"
                if identical_pct < 0.8:  # <80% identical
                    return "warning"

        # Check visual comparison
        for viewport, visual in report.visual_summary.items():
            total = visual.get("total_pages", 0)
            if total > 0:
                different_pct = visual.get("different", 0) / total
                if different_pct > 0.2:  # >20% different
                    return "warning"

        return "pass"

    def _save_report(self, report: MirrorReport):
        """Save consolidated report."""
        # JSON report
        report_path = self.output_dir / "mirror_report.json"
        report_path.write_text(json.dumps(asdict(report), indent=2))

        # HTML report
        html = self._generate_html_report(report)
        (self.output_dir / "mirror_report.html").write_text(html)

        print(f"\nReports saved to: {self.output_dir}")

    def _generate_html_report(self, report: MirrorReport) -> str:
        """Generate consolidated HTML report."""
        status_color = {
            "pass": "#28a745",
            "warning": "#ffc107",
            "fail": "#dc3545",
            "unknown": "#6c757d"
        }

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Site Mirror Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 40px; max-width: 1200px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .status {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 8px;
            color: white;
            font-size: 1.5em;
            font-weight: bold;
            background: {status_color.get(report.overall_status, '#6c757d')};
        }}
        .section {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .section h2 {{ margin-top: 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .stat {{ background: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .links {{ margin-top: 30px; }}
        .links a {{ display: inline-block; margin: 5px 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .links a:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Site Mirror Report</h1>
        <div class="status">{report.overall_status.upper()}</div>
        <p>Generated: {report.timestamp}</p>
    </div>

    <div class="section">
        <h2>Configuration</h2>
        <p><strong>Source:</strong> {self.config.source_url}</p>
        <p><strong>Target:</strong> {self.config.target_url or self.config.target_dir}</p>
    </div>
"""

        # Crawl summary
        if report.crawl_summary:
            html += """
    <div class="section">
        <h2>Crawl Summary</h2>
        <div class="grid">
"""
            for site, stats in report.crawl_summary.items():
                html += f"""
            <div class="stat">
                <div class="stat-value">{stats.get('urls_crawled', 0)}</div>
                <div class="stat-label">{site.title()} URLs Crawled</div>
            </div>
"""
            html += """
        </div>
    </div>
"""

        # Text comparison summary
        if report.text_summary:
            text = report.text_summary
            html += f"""
    <div class="section">
        <h2>Text Comparison</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{text.get('total_urls', 0)}</div>
                <div class="stat-label">Total URLs</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #28a745;">{text.get('identical', 0)}</div>
                <div class="stat-label">Identical</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #ffc107;">{text.get('similar', 0)}</div>
                <div class="stat-label">Similar</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #dc3545;">{text.get('different', 0)}</div>
                <div class="stat-label">Different</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #6c757d;">{text.get('missing_in_target', 0)}</div>
                <div class="stat-label">Missing in Target</div>
            </div>
        </div>
    </div>
"""

        # Visual comparison summary
        if report.visual_summary:
            html += """
    <div class="section">
        <h2>Visual Comparison</h2>
"""
            for viewport, visual in report.visual_summary.items():
                html += f"""
        <h3>{viewport.title()}</h3>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{visual.get('total_pages', 0)}</div>
                <div class="stat-label">Pages Compared</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #28a745;">{visual.get('identical', 0)}</div>
                <div class="stat-label">Identical</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: #dc3545;">{visual.get('different', 0)}</div>
                <div class="stat-label">Different</div>
            </div>
        </div>
"""
            html += """
    </div>
"""

        # Links to detailed reports
        html += """
    <div class="links">
        <h2>Detailed Reports</h2>
        <a href="text_comparison/text_comparison.html">Text Comparison Report</a>
        <a href="visual_comparison/desktop/visual_comparison.html">Visual Comparison Report</a>
    </div>

</body>
</html>
"""
        return html


async def main():
    parser = argparse.ArgumentParser(
        description="Mirror and compare websites"
    )
    parser.add_argument(
        "source_url",
        help="Source site URL to mirror"
    )
    parser.add_argument(
        "--target-url",
        help="Target site URL to compare against"
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        help="Local directory (Hugo build) to compare against"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("./mirror_output"),
        help="Output directory"
    )
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=10,
        help="Maximum crawl depth"
    )
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=5.0,
        help="Max requests per second, aggregate across all workers (default: 5)"
    )
    parser.add_argument(
        "--max-concurrent", "-c",
        type=int,
        default=10,
        help="Max concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL verification"
    )
    parser.add_argument(
        "--no-assets",
        action="store_true",
        help="Skip downloading assets"
    )
    parser.add_argument(
        "--text-threshold",
        type=float,
        default=0.9,
        help="Text similarity threshold (default: 0.9)"
    )
    parser.add_argument(
        "--visual-threshold",
        type=float,
        default=0.01,
        help="Visual difference threshold (default: 0.01)"
    )
    parser.add_argument(
        "--viewports",
        nargs="+",
        default=["desktop"],
        choices=["desktop", "tablet", "mobile"],
        help="Viewports for visual comparison"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=8,
        help="Number of parallel workers for comparison (default: 8)"
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip crawling (use existing crawl data)"
    )
    parser.add_argument(
        "--skip-source-crawl",
        action="store_true",
        help="Skip crawling source (only crawl target)"
    )
    parser.add_argument(
        "--skip-target-crawl",
        action="store_true",
        help="Skip crawling target (only crawl source)"
    )
    parser.add_argument(
        "--skip-text",
        action="store_true",
        help="Skip text comparison"
    )
    parser.add_argument(
        "--skip-visual",
        action="store_true",
        help="Skip visual comparison"
    )
    parser.add_argument(
        "--pages-only",
        action="store_true",
        help="Fast comparison using local crawl data if available (URL + text, excludes assets)"
    )
    parser.add_argument(
        "--focus", "-f",
        help="Focus on specific path prefix (e.g., /news/press-releases)"
    )
    parser.add_argument(
        "--use-target-sitemap",
        action="store_true",
        help="Use target's sitemap to discover URLs for source crawl (useful when source blocks sitemap)"
    )

    args = parser.parse_args()

    if not args.target_url and not args.target_dir:
        parser.error("Either --target-url or --target-dir must be specified")

    config = MirrorConfig(
        source_url=args.source_url,
        target_url=args.target_url,
        target_dir=args.target_dir,
        output_dir=args.output,
        crawl_depth=args.depth,
        rate_limit=args.rate_limit,
        max_concurrent=args.max_concurrent,
        verify_ssl=not args.no_verify_ssl,
        include_assets=not args.no_assets,
        text_threshold=args.text_threshold,
        visual_threshold=args.visual_threshold,
        viewports=args.viewports,
        num_workers=args.workers,
        skip_crawl=args.skip_crawl,
        skip_source_crawl=args.skip_source_crawl,
        skip_target_crawl=args.skip_target_crawl,
        skip_text=args.skip_text,
        skip_visual=args.skip_visual,
        pages_only=args.pages_only,
        focus_path=args.focus,
        use_target_sitemap=args.use_target_sitemap
    )

    mirror = SiteMirror(config)
    report = await mirror.run()

    # Print final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Overall Status: {report.overall_status.upper()}")
    print(f"Report: {config.output_dir / 'mirror_report.html'}")


if __name__ == "__main__":
    asyncio.run(main())
