#!/usr/bin/env python3
"""
Visual Comparator - Compares visual appearance of pages using screenshots.

Features:
- Takes screenshots of source and target pages using Playwright
- Pixel-level comparison with configurable threshold
- Generates visual diff images
- Handles dynamic content (hides dates, timestamps)
- Multiple viewport sizes for responsive testing
- Parallel screenshot capture for performance
"""

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageChops, ImageDraw
from playwright.async_api import async_playwright, Page


@dataclass
class VisualComparison:
    """Result of visual comparison between two pages."""
    url: str
    source_screenshot: Optional[str] = None
    target_screenshot: Optional[str] = None
    diff_image: Optional[str] = None
    diff_percentage: float = 0.0
    status: str = "unknown"  # identical, similar, different, error
    viewport: str = "desktop"
    error: Optional[str] = None


@dataclass
class VisualReport:
    """Overall visual comparison report."""
    source_base_url: str
    target_base_url: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_pages: int = 0
    identical: int = 0
    similar: int = 0
    different: int = 0
    errors: int = 0
    comparisons: list[VisualComparison] = field(default_factory=list)

    def save(self, path: Path):
        """Save report to JSON."""
        data = asdict(self)
        path.write_text(json.dumps(data, indent=2))


class ScreenshotCapture:
    """Captures screenshots using Playwright."""

    VIEWPORTS = {
        "desktop": {"width": 1920, "height": 1080},
        "tablet": {"width": 768, "height": 1024},
        "mobile": {"width": 375, "height": 812},
    }

    # CSS to hide dynamic content
    HIDE_DYNAMIC_CSS = """
        /* Hide dynamic timestamps and dates */
        time, .date, .timestamp, [datetime] {
            visibility: hidden !important;
        }
        /* Hide ads and tracking */
        .ad, .advertisement, [class*="tracking"] {
            display: none !important;
        }
        /* Disable animations */
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }
    """

    def __init__(
        self,
        output_dir: Path,
        viewport: str = "desktop",
        full_page: bool = True,
        wait_for_network: bool = True
    ):
        self.output_dir = output_dir
        self.viewport = viewport
        self.full_page = full_page
        self.wait_for_network = wait_for_network

        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def capture(self, url: str, page: Page) -> Optional[Path]:
        """Capture screenshot of a URL."""
        try:
            # Set viewport
            viewport_size = self.VIEWPORTS.get(self.viewport, self.VIEWPORTS["desktop"])
            await page.set_viewport_size(viewport_size)

            # Navigate to page
            await page.goto(url, wait_until="networkidle" if self.wait_for_network else "load")

            # Inject CSS to hide dynamic content
            await page.add_style_tag(content=self.HIDE_DYNAMIC_CSS)

            # Wait for any lazy-loaded content
            await asyncio.sleep(1)

            # Generate filename from URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"{url_hash}_{self.viewport}.png"
            screenshot_path = self.output_dir / filename

            # Take screenshot
            await page.screenshot(
                path=str(screenshot_path),
                full_page=self.full_page
            )

            return screenshot_path

        except Exception as e:
            print(f"Error capturing {url}: {e}")
            return None


class ImageComparator:
    """Compares images pixel by pixel."""

    def __init__(self, threshold: float = 0.01):
        """
        Args:
            threshold: Maximum difference percentage to consider images similar (0.01 = 1%)
        """
        self.threshold = threshold

    def compare(
        self,
        image1_path: Path,
        image2_path: Path,
        diff_output: Optional[Path] = None
    ) -> tuple[float, Optional[Path]]:
        """
        Compare two images and return difference percentage.

        Returns:
            Tuple of (diff_percentage, diff_image_path)
        """
        try:
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')

            # Resize to same dimensions if needed
            if img1.size != img2.size:
                # Use the larger dimensions
                max_width = max(img1.width, img2.width)
                max_height = max(img1.height, img2.height)

                img1 = self._resize_canvas(img1, max_width, max_height)
                img2 = self._resize_canvas(img2, max_width, max_height)

            # Calculate difference
            diff = ImageChops.difference(img1, img2)

            # Count different pixels
            diff_data = list(diff.getdata())
            total_pixels = len(diff_data)
            different_pixels = sum(1 for pixel in diff_data if sum(pixel) > 30)  # threshold for "different"

            diff_percentage = different_pixels / total_pixels

            # Generate diff image if requested
            diff_path = None
            if diff_output:
                diff_img = self._create_diff_image(img1, img2, diff)
                diff_img.save(diff_output)
                diff_path = diff_output

            return diff_percentage, diff_path

        except Exception as e:
            print(f"Error comparing images: {e}")
            return 1.0, None

    def _resize_canvas(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Resize image canvas (not scale) to target dimensions."""
        new_img = Image.new('RGB', (width, height), (255, 255, 255))
        new_img.paste(img, (0, 0))
        return new_img

    def _create_diff_image(
        self,
        img1: Image.Image,
        img2: Image.Image,
        diff: Image.Image
    ) -> Image.Image:
        """Create a visual diff image showing differences in red."""
        # Create output image
        width = img1.width * 3
        height = img1.height
        output = Image.new('RGB', (width, height))

        # Paste source, target, and diff side by side
        output.paste(img1, (0, 0))
        output.paste(img2, (img1.width, 0))

        # Create highlighted diff
        highlighted = img2.copy()
        diff_data = list(diff.getdata())

        pixels = list(highlighted.getdata())
        new_pixels = []

        for i, (orig, diff_pixel) in enumerate(zip(pixels, diff_data)):
            if sum(diff_pixel) > 30:
                # Highlight differences in red
                new_pixels.append((255, 0, 0))
            else:
                new_pixels.append(orig)

        highlighted.putdata(new_pixels)
        output.paste(highlighted, (img1.width * 2, 0))

        # Add labels
        draw = ImageDraw.Draw(output)
        draw.text((10, 10), "Source", fill=(0, 0, 0))
        draw.text((img1.width + 10, 10), "Target", fill=(0, 0, 0))
        draw.text((img1.width * 2 + 10, 10), "Diff", fill=(255, 0, 0))

        return output


class VisualComparator:
    """Main visual comparison orchestrator."""

    def __init__(
        self,
        source_base_url: str,
        target_base_url: str,
        output_dir: Path,
        viewport: str = "desktop",
        threshold: float = 0.01,
        concurrency: int = 4
    ):
        self.source_base_url = source_base_url.rstrip('/')
        self.target_base_url = target_base_url.rstrip('/')
        self.output_dir = output_dir
        self.viewport = viewport
        self.threshold = threshold
        self.concurrency = concurrency

        self.screenshots_dir = output_dir / "screenshots"
        self.diffs_dir = output_dir / "diffs"

        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)

        self.image_comparator = ImageComparator(threshold=threshold)

        # Resume support - track completed URLs
        self.state_file = output_dir / "visual_state.json"
        self.completed_urls: set[str] = set()
        self._load_state()

    def _load_state(self):
        """Load previous state for resume support."""
        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                self.completed_urls = set(state.get("completed_urls", []))
                print(f"Resuming: {len(self.completed_urls)} URLs already compared")
            except Exception:
                pass

    def _save_state(self):
        """Save state for resume support."""
        state = {"completed_urls": list(self.completed_urls)}
        self.state_file.write_text(json.dumps(state))

    async def compare_urls(self, urls: list[str]) -> VisualReport:
        """Compare a list of URLs between source and target."""
        report = VisualReport(
            source_base_url=self.source_base_url,
            target_base_url=self.target_base_url,
            total_pages=len(urls)
        )

        # Filter out already completed URLs (resume support)
        pending_urls = [u for u in urls if u not in self.completed_urls]
        print(f"URLs to compare: {len(pending_urls)} (skipping {len(urls) - len(pending_urls)} already done)")

        if not pending_urls:
            print("All URLs already compared!")
            return report

        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # Create pages for parallel capture
            semaphore = asyncio.Semaphore(self.concurrency)
            completed_count = 0

            async def compare_url(url: str) -> VisualComparison:
                nonlocal completed_count
                async with semaphore:
                    result = await self._compare_single_url(browser, url)
                    # Mark as completed and save state periodically
                    self.completed_urls.add(url)
                    completed_count += 1
                    if completed_count % 10 == 0:
                        self._save_state()
                        print(f"  Progress: {completed_count}/{len(pending_urls)}")
                    return result

            tasks = [compare_url(url) for url in pending_urls]
            comparisons = await asyncio.gather(*tasks, return_exceptions=True)

            await browser.close()

        # Save final state
        self._save_state()

        # Process results
        for i, comp in enumerate(comparisons):
            if isinstance(comp, Exception):
                # Handle exceptions from gather
                comp = VisualComparison(
                    url=pending_urls[i],
                    viewport=self.viewport,
                    status="error",
                    error=str(comp)
                )

            report.comparisons.append(comp)

            if comp.status == "identical":
                report.identical += 1
            elif comp.status == "similar":
                report.similar += 1
            elif comp.status == "different":
                report.different += 1
            else:
                report.errors += 1

        return report

    async def _compare_single_url(self, browser, url_path: str) -> VisualComparison:
        """Compare a single URL between source and target."""
        comparison = VisualComparison(url=url_path, viewport=self.viewport)

        # Construct full URLs
        source_url = f"{self.source_base_url}{url_path}"
        target_url = f"{self.target_base_url}{url_path}"

        source_context = None
        target_context = None

        try:
            # Create browser contexts for isolation
            source_context = await browser.new_context()
            target_context = await browser.new_context()

            source_page = await source_context.new_page()
            target_page = await target_context.new_page()

            # Create screenshot capture
            capture = ScreenshotCapture(
                output_dir=self.screenshots_dir,
                viewport=self.viewport
            )

            # Capture screenshots - handle failures individually
            source_screenshot = None
            target_screenshot = None

            try:
                source_screenshot = await capture.capture(source_url, source_page)
            except Exception as e:
                comparison.error = f"Source failed: {e}"

            try:
                target_screenshot = await capture.capture(target_url, target_page)
            except Exception as e:
                if comparison.error:
                    comparison.error += f"; Target failed: {e}"
                else:
                    comparison.error = f"Target failed: {e}"

            if not source_screenshot:
                comparison.status = "error"
                if not comparison.error:
                    comparison.error = "Failed to capture source screenshot"
                return comparison

            if not target_screenshot:
                comparison.status = "missing_target"
                if not comparison.error:
                    comparison.error = "Target page not found or failed to load"
                return comparison

            comparison.source_screenshot = str(source_screenshot)
            comparison.target_screenshot = str(target_screenshot)

            # Compare screenshots
            url_hash = hashlib.md5(url_path.encode()).hexdigest()[:12]
            diff_path = self.diffs_dir / f"{url_hash}_{self.viewport}_diff.png"

            diff_percentage, diff_image = self.image_comparator.compare(
                source_screenshot,
                target_screenshot,
                diff_path
            )

            comparison.diff_percentage = diff_percentage
            comparison.diff_image = str(diff_image) if diff_image else None

            # Determine status
            if diff_percentage < 0.001:
                comparison.status = "identical"
            elif diff_percentage < self.threshold:
                comparison.status = "similar"
            else:
                comparison.status = "different"

        except Exception as e:
            comparison.status = "error"
            comparison.error = str(e)

        finally:
            # Always close contexts
            if source_context:
                try:
                    await source_context.close()
                except Exception:
                    pass
            if target_context:
                try:
                    await target_context.close()
                except Exception:
                    pass

        return comparison


def generate_html_report(report: VisualReport, output_path: Path):
    """Generate HTML visual comparison report."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Visual Comparison Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .stat {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .identical {{ color: #28a745; }}
        .similar {{ color: #ffc107; }}
        .different {{ color: #dc3545; }}
        .comparison-card {{ border: 1px solid #ddd; margin: 20px 0; border-radius: 8px; overflow: hidden; }}
        .comparison-header {{ background: #f5f5f5; padding: 15px; border-bottom: 1px solid #ddd; }}
        .comparison-header.identical {{ border-left: 4px solid #28a745; }}
        .comparison-header.similar {{ border-left: 4px solid #ffc107; }}
        .comparison-header.different {{ border-left: 4px solid #dc3545; }}
        .comparison-body {{ padding: 15px; }}
        .screenshot-container {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .screenshot {{ max-width: 100%; border: 1px solid #ddd; }}
        .diff-image {{ max-width: 100%; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        .badge-identical {{ background: #28a745; color: white; }}
        .badge-similar {{ background: #ffc107; color: black; }}
        .badge-different {{ background: #dc3545; color: white; }}
    </style>
</head>
<body>
    <h1>Visual Comparison Report</h1>
    <p>Generated: {report.timestamp}</p>
    <p>Source: {report.source_base_url}</p>
    <p>Target: {report.target_base_url}</p>

    <div class="summary">
        <div class="stat">
            <div class="stat-value">{report.total_pages}</div>
            <div class="stat-label">Total Pages</div>
        </div>
        <div class="stat">
            <div class="stat-value identical">{report.identical}</div>
            <div class="stat-label">Identical</div>
        </div>
        <div class="stat">
            <div class="stat-value similar">{report.similar}</div>
            <div class="stat-label">Similar</div>
        </div>
        <div class="stat">
            <div class="stat-value different">{report.different}</div>
            <div class="stat-label">Different</div>
        </div>
    </div>

    <h2>Comparisons with Differences</h2>
"""

    # Sort by diff percentage descending
    different_comparisons = [c for c in report.comparisons if c.status in ("different", "similar")]
    different_comparisons.sort(key=lambda x: x.diff_percentage, reverse=True)

    for comp in different_comparisons[:50]:  # Limit to 50
        badge_class = f"badge-{comp.status}"
        html += f"""
    <div class="comparison-card">
        <div class="comparison-header {comp.status}">
            <strong>{comp.url}</strong>
            <span class="badge {badge_class}">{comp.status} ({comp.diff_percentage:.2%})</span>
        </div>
        <div class="comparison-body">
"""
        if comp.diff_image:
            html += f'<img class="diff-image" src="{comp.diff_image}" alt="Visual diff">'

        html += """
        </div>
    </div>
"""

    html += """
</body>
</html>
"""

    output_path.write_text(html)


async def main():
    parser = argparse.ArgumentParser(
        description="Visual comparison between source and target sites"
    )
    parser.add_argument(
        "source_url",
        help="Source site base URL"
    )
    parser.add_argument(
        "target_url",
        help="Target site base URL"
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        help="File containing URL paths to compare (one per line)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("./visual_report"),
        help="Output directory"
    )
    parser.add_argument(
        "--viewport", "-v",
        choices=["desktop", "tablet", "mobile"],
        default="desktop",
        help="Viewport size (default: desktop)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.01,
        help="Difference threshold (default: 0.01 = 1%%)"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=4,
        help="Number of parallel comparisons (default: 4)"
    )

    args = parser.parse_args()

    # Load URLs to compare
    if args.urls_file and args.urls_file.exists():
        urls = [line.strip() for line in args.urls_file.read_text().splitlines() if line.strip()]
    else:
        # Default to homepage
        urls = ["/"]

    args.output.mkdir(parents=True, exist_ok=True)

    comparator = VisualComparator(
        source_base_url=args.source_url,
        target_base_url=args.target_url,
        output_dir=args.output,
        viewport=args.viewport,
        threshold=args.threshold,
        concurrency=args.concurrency
    )

    print(f"Comparing {len(urls)} URLs")
    print(f"Source: {args.source_url}")
    print(f"Target: {args.target_url}")
    print(f"Viewport: {args.viewport}")
    print("=" * 50)

    report = await comparator.compare_urls(urls)

    # Save reports
    report.save(args.output / "visual_report.json")
    generate_html_report(report, args.output / "visual_report.html")

    # Print summary
    print("\n" + "=" * 50)
    print("VISUAL COMPARISON SUMMARY")
    print("=" * 50)
    print(f"Total pages:  {report.total_pages}")
    print(f"Identical:    {report.identical}")
    print(f"Similar:      {report.similar}")
    print(f"Different:    {report.different}")
    print(f"Errors:       {report.errors}")
    print(f"\nReports saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
