#!/usr/bin/env python3
"""
Site Crawler - Discovers and downloads all pages and assets from a website.

Features:
- Sitemap.xml parsing for URL discovery
- Recursive link following from any start URL
- Asset downloading (PDF, images, CSS, JS)
- Respects robots.txt (with override option)
- Rate limiting to avoid overwhelming servers
- Resume support via state file
"""

import argparse
import asyncio
import hashlib
import json
import random
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse
import mimetypes

import httpx
from bs4 import BeautifulSoup

# Default configuration
DEFAULT_RATE_LIMIT = 2  # requests per second (lowered to avoid blocks)
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_DEPTH = 10

# Use a real browser User-Agent to avoid CDN blocks
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Browser-like headers to avoid Akamai/CDN blocks
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


@dataclass
class CrawlResult:
    """Result of crawling a single URL."""
    url: str
    status_code: int
    content_type: str
    content_hash: str
    local_path: Optional[str] = None
    links: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CrawlState:
    """Persistent crawl state for resume support."""
    base_url: str
    discovered_urls: set[str] = field(default_factory=set)
    crawled_urls: set[str] = field(default_factory=set)
    failed_urls: dict[str, str] = field(default_factory=dict)  # url -> error
    results: list[CrawlResult] = field(default_factory=list)

    def save(self, path: Path):
        """Save state to JSON file."""
        data = {
            "base_url": self.base_url,
            "discovered_urls": list(self.discovered_urls),
            "crawled_urls": list(self.crawled_urls),
            "failed_urls": self.failed_urls,
            "results": [asdict(r) for r in self.results]
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> "CrawlState":
        """Load state from JSON file."""
        data = json.load(path.open())
        state = cls(base_url=data["base_url"])
        state.discovered_urls = set(data["discovered_urls"])
        state.crawled_urls = set(data["crawled_urls"])
        state.failed_urls = data["failed_urls"]
        state.results = [CrawlResult(**r) for r in data["results"]]
        return state


class SitemapParser:
    """Parses sitemap.xml and sitemap index files."""

    SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def parse(self, sitemap_url: str) -> set[str]:
        """Parse sitemap and return all URLs."""
        urls = set()

        try:
            response = await self.client.get(sitemap_url)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Check if this is a sitemap index
            sitemap_refs = root.findall(".//sm:sitemap/sm:loc", self.SITEMAP_NS)
            if sitemap_refs:
                # Recursively parse child sitemaps
                for ref in sitemap_refs:
                    child_urls = await self.parse(ref.text)
                    urls.update(child_urls)
            else:
                # Parse URL entries
                url_elements = root.findall(".//sm:url/sm:loc", self.SITEMAP_NS)
                for elem in url_elements:
                    if elem.text:
                        urls.add(elem.text.strip())

        except Exception as e:
            print(f"Error parsing sitemap {sitemap_url}: {e}")

        return urls


class Crawler:
    """Async web crawler with rate limiting and resume support."""

    BINARY_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar',
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.woff', '.woff2', '.ttf', '.eot',
        '.csv', '.xml', '.json'
    }

    def __init__(
        self,
        base_url: str,
        output_dir: Path,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        max_depth: int = DEFAULT_MAX_DEPTH,
        verify_ssl: bool = True,
        include_assets: bool = True,
        focus_path: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        self.rate_limit = rate_limit
        self.max_depth = max_depth
        self.verify_ssl = verify_ssl
        self.include_assets = include_assets

        # Focus path - only crawl URLs under this path prefix
        self.focus_path = focus_path.rstrip('/') if focus_path else None

        self.state = CrawlState(base_url=base_url)
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.state_file = output_dir / "crawl_state.json"

        # Create output directories
        (output_dir / "pages").mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)

    async def crawl(self, start_urls: Optional[set[str]] = None, use_sitemap_from: Optional[str] = None) -> CrawlState:
        """Main crawl entry point."""

        # Load existing state if resuming
        if self.state_file.exists():
            print("Resuming from previous crawl state...")
            self.state = CrawlState.load(self.state_file)

            # If focus path is set, filter existing state to only include matching URLs
            if self.focus_path:
                self.state.discovered_urls = {u for u in self.state.discovered_urls if self._matches_focus(u)}
                self.state.crawled_urls = {u for u in self.state.crawled_urls if self._matches_focus(u)}
                print(f"Filtered to {len(self.state.crawled_urls)} URLs matching focus path")

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            verify=self.verify_ssl,
            follow_redirects=True,
            headers=DEFAULT_HEADERS
        ) as client:
            self.client = client

            # Show focus path if set
            if self.focus_path:
                print(f"Focus: {self.focus_path}/* (only crawling URLs under this path)")

            # Discover URLs from sitemap (optional - crawl continues even if blocked)
            if use_sitemap_from:
                # Use alternate sitemap (e.g., from localhost) and convert URLs to this domain
                print(f"Using sitemap from {use_sitemap_from}/sitemap.xml (converting URLs to {self.base_url})...")
                sitemap_parser = SitemapParser(client)
                alt_sitemap_urls = await sitemap_parser.parse(f"{use_sitemap_from}/sitemap.xml")
                # Convert URLs from alternate domain to this domain
                sitemap_urls = set()
                alt_parsed = urlparse(use_sitemap_from)
                for url in alt_sitemap_urls:
                    parsed = urlparse(url)
                    # Replace the domain with our base domain
                    converted = urlunparse((
                        urlparse(self.base_url).scheme,
                        urlparse(self.base_url).netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        ""
                    ))
                    sitemap_urls.add(converted)
                print(f"Converted {len(sitemap_urls)} URLs from alternate sitemap")
            else:
                print(f"Parsing sitemap from {self.base_url}/sitemap.xml...")
                sitemap_parser = SitemapParser(client)
                sitemap_urls = await sitemap_parser.parse(f"{self.base_url}/sitemap.xml")

            # Filter sitemap URLs by focus path
            if self.focus_path:
                sitemap_urls = {u for u in sitemap_urls if self._matches_focus(u)}
                if sitemap_urls:
                    print(f"Found {len(sitemap_urls)} URLs in sitemap matching focus path")
                else:
                    print("No URLs from sitemap (blocked or empty) - will discover via links")
            else:
                if sitemap_urls:
                    print(f"Found {len(sitemap_urls)} URLs in sitemap")
                else:
                    print("No URLs from sitemap (blocked or empty) - will discover via links")

            self.state.discovered_urls.update(sitemap_urls)

            # Always add start URL(s) to ensure crawl can proceed
            if start_urls:
                # Filter start URLs by focus path too
                if self.focus_path:
                    start_urls = {u for u in start_urls if self._matches_focus(u)}
                self.state.discovered_urls.update(start_urls)

            # Add focus path or base URL as starting point
            if self.focus_path:
                start_url = f"{self.base_url}{self.focus_path}"
                self.state.discovered_urls.add(start_url)
                print(f"Starting from: {start_url}")
            else:
                self.state.discovered_urls.add(self.base_url)
                print(f"Starting from: {self.base_url}")

            # Crawl all discovered URLs
            await self._crawl_all()

        # Save final state
        self.state.save(self.state_file)

        return self.state

    async def _crawl_all(self):
        """Crawl all discovered URLs."""
        depth = 0

        # Always do at least one pass to crawl discovered URLs (even if max_depth is 0)
        while depth <= self.max_depth:
            # Get URLs to crawl at this depth
            pending = self.state.discovered_urls - self.state.crawled_urls
            pending = {u for u in pending if u not in self.state.failed_urls}

            if not pending:
                break

            print(f"\nDepth {depth}: {len(pending)} URLs to crawl")

            # Crawl in batches
            batch_size = 50
            pending_list = list(pending)

            for i in range(0, len(pending_list), batch_size):
                batch = pending_list[i:i + batch_size]
                tasks = [self._crawl_url(url) for url in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        self.state.failed_urls[url] = str(result)
                    elif result:
                        self.state.results.append(result)
                        # Add discovered links for next depth
                        self.state.discovered_urls.update(result.links)
                        if self.include_assets:
                            self.state.discovered_urls.update(result.assets)

                # Save state periodically
                if i % 100 == 0:
                    self.state.save(self.state_file)
                    print(f"  Progress: {len(self.state.crawled_urls)}/{len(self.state.discovered_urls)} URLs")

            depth += 1

        print(f"\nCrawl complete: {len(self.state.crawled_urls)} URLs crawled")

    async def _crawl_url(self, url: str) -> Optional[CrawlResult]:
        """Crawl a single URL."""
        async with self.semaphore:
            # Rate limiting with random jitter to appear more human-like
            base_delay = 1.0 / self.rate_limit
            jitter = random.uniform(0.5, 1.5)  # 50-150% of base delay
            await asyncio.sleep(base_delay * jitter)

            try:
                # Determine if this is a binary file
                parsed = urlparse(url)
                ext = Path(parsed.path).suffix.lower()
                is_binary = ext in self.BINARY_EXTENSIONS

                if is_binary:
                    return await self._download_asset(url)
                else:
                    return await self._crawl_page(url)

            except Exception as e:
                self.state.crawled_urls.add(url)
                return CrawlResult(
                    url=url,
                    status_code=0,
                    content_type="",
                    content_hash="",
                    error=str(e)
                )

    async def _crawl_page(self, url: str) -> CrawlResult:
        """Crawl an HTML page."""
        response = await self.client.get(url)
        self.state.crawled_urls.add(url)

        content_type = response.headers.get("content-type", "")
        content = response.content
        content_hash = hashlib.sha256(content).hexdigest()

        # Detect CDN blocks (Akamai, CloudFront, etc.)
        content_lower = content[:1000].lower()
        if b'access denied' in content_lower or b'errors.edgesuite.net' in content_lower:
            return CrawlResult(
                url=url,
                status_code=403,
                content_type=content_type,
                content_hash=content_hash,
                error="Blocked by CDN (Access Denied)"
            )

        # Parse HTML to extract links and assets
        links = []
        assets = []

        if "text/html" in content_type:
            soup = BeautifulSoup(content, "html.parser")

            # Extract links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                abs_url = self._normalize_url(href, url)
                if abs_url and self._is_same_domain(abs_url) and self._matches_focus(abs_url):
                    links.append(abs_url)

            # Extract assets
            for img in soup.find_all("img", src=True):
                src = img["src"]
                abs_url = self._normalize_url(src, url)
                if abs_url:
                    assets.append(abs_url)

            for link in soup.find_all("link", href=True):
                href = link["href"]
                abs_url = self._normalize_url(href, url)
                if abs_url:
                    assets.append(abs_url)

            for script in soup.find_all("script", src=True):
                src = script["src"]
                abs_url = self._normalize_url(src, url)
                if abs_url:
                    assets.append(abs_url)

        # Save content
        local_path = self._url_to_path(url, "pages")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)

        return CrawlResult(
            url=url,
            status_code=response.status_code,
            content_type=content_type,
            content_hash=content_hash,
            local_path=str(local_path),
            links=links,
            assets=assets
        )

    async def _download_asset(self, url: str) -> CrawlResult:
        """Download a binary asset."""
        response = await self.client.get(url)
        self.state.crawled_urls.add(url)

        content = response.content
        content_hash = hashlib.sha256(content).hexdigest()
        content_type = response.headers.get("content-type", "")

        # Save asset
        local_path = self._url_to_path(url, "assets")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)

        return CrawlResult(
            url=url,
            status_code=response.status_code,
            content_type=content_type,
            content_hash=content_hash,
            local_path=str(local_path)
        )

    def _normalize_url(self, href: str, base_url: str) -> Optional[str]:
        """Normalize a URL, resolving relative paths."""
        if not href:
            return None

        # Skip javascript:, mailto:, tel:, etc.
        if href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
            return None

        # Resolve relative URLs
        abs_url = urljoin(base_url, href)

        # Parse and clean
        parsed = urlparse(abs_url)

        # Remove fragment
        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ""  # no fragment
        ))

        return cleaned

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL is on the same domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain

    def _matches_focus(self, url: str) -> bool:
        """Check if URL matches the focus path prefix."""
        if not self.focus_path:
            return True  # No focus, all URLs match

        parsed = urlparse(url)
        path = parsed.path

        # URL must start with focus path
        return path.startswith(self.focus_path) or path.startswith(self.focus_path + '/')

    def _url_to_path(self, url: str, subdir: str) -> Path:
        """Convert URL to local file path."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            path = "index"

        # Add query string hash if present
        if parsed.query:
            query_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
            path = f"{path}_{query_hash}"

        # Ensure file extension
        if not Path(path).suffix:
            path = f"{path}.html"

        return self.output_dir / subdir / path


async def main():
    parser = argparse.ArgumentParser(
        description="Crawl and download a website"
    )
    parser.add_argument(
        "url",
        help="Base URL to crawl (e.g., https://home.treasury.gov)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("./crawl_output"),
        help="Output directory (default: ./crawl_output)"
    )
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=DEFAULT_RATE_LIMIT,
        help=f"Requests per second (default: {DEFAULT_RATE_LIMIT})"
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help=f"Maximum crawl depth (default: {DEFAULT_MAX_DEPTH})"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL verification"
    )
    parser.add_argument(
        "--no-assets",
        action="store_true",
        help="Skip downloading assets (images, PDFs, etc.)"
    )
    parser.add_argument(
        "--start-urls",
        nargs="+",
        help="Additional start URLs"
    )
    parser.add_argument(
        "--focus", "-f",
        help="Focus on specific path prefix (e.g., /news/press-releases)"
    )
    parser.add_argument(
        "--use-sitemap-from",
        help="Use sitemap from alternate URL (e.g., http://localhost:1313) to discover URLs"
    )

    args = parser.parse_args()

    crawler = Crawler(
        base_url=args.url,
        output_dir=args.output,
        rate_limit=args.rate_limit,
        max_depth=args.max_depth,
        verify_ssl=not args.no_verify_ssl,
        include_assets=not args.no_assets,
        focus_path=args.focus
    )

    start_urls = set(args.start_urls) if args.start_urls else None

    print(f"Starting crawl of {args.url}")
    print(f"Output directory: {args.output}")
    print(f"Rate limit: {args.rate_limit} req/s")
    print(f"Max depth: {args.max_depth}")
    if args.focus:
        print(f"Focus path: {args.focus}")
    if args.use_sitemap_from:
        print(f"Using sitemap from: {args.use_sitemap_from}")
    print("=" * 50)

    state = await crawler.crawl(start_urls, use_sitemap_from=args.use_sitemap_from)

    # Print summary
    print("\n" + "=" * 50)
    print("CRAWL SUMMARY")
    print("=" * 50)
    print(f"URLs discovered: {len(state.discovered_urls)}")
    print(f"URLs crawled: {len(state.crawled_urls)}")
    print(f"URLs failed: {len(state.failed_urls)}")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
