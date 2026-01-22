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

# Import our modules
from crawler import Crawler, CrawlState
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
    skip_text: bool = False
    skip_visual: bool = False
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

        # Phase 1: Crawl
        if not self.config.skip_crawl:
            print("\n" + "=" * 60)
            print("PHASE 1: CRAWLING")
            print("=" * 60)

            source_state = await self._crawl_source()
            report.crawl_summary["source"] = {
                "urls_discovered": len(source_state.discovered_urls),
                "urls_crawled": len(source_state.crawled_urls),
                "urls_failed": len(source_state.failed_urls)
            }

            if self.config.target_url:
                target_state = await self._crawl_target()
                report.crawl_summary["target"] = {
                    "urls_discovered": len(target_state.discovered_urls),
                    "urls_crawled": len(target_state.crawled_urls),
                    "urls_failed": len(target_state.failed_urls)
                }

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
        skip_text=args.skip_text,
        skip_visual=args.skip_visual,
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
