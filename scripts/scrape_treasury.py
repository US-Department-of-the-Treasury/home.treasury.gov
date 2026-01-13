#!/usr/bin/env python3
"""
Treasury.gov Content Scraper

Extracts content from home.treasury.gov for Hugo migration.
Pulls pages, assets, and converts HTML to Markdown.

Usage:
    python scripts/scrape_treasury.py --discover    # Find all URLs from sitemap/crawl
    python scripts/scrape_treasury.py --scrape      # Scrape discovered URLs
    python scripts/scrape_treasury.py --all         # Do both
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiohttp
import aiofiles
import html2text
import requests
import yaml
from bs4 import BeautifulSoup
from slugify import slugify
from tqdm import tqdm

# Configuration
BASE_URL = "https://home.treasury.gov"
OUTPUT_DIR = Path(__file__).parent.parent / "content"
ASSETS_DIR = Path(__file__).parent.parent / "static"
DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = Path(__file__).parent.parent / ".cache"

# Sitemap locations to try
SITEMAP_URLS = [
    f"{BASE_URL}/sitemap.xml",
    f"{BASE_URL}/sitemap_index.xml",
    f"{BASE_URL}/sitemap",
]

# Content type mapping based on URL patterns
CONTENT_TYPE_PATTERNS = [
    (r"^/news/press-releases/", "press-releases"),
    (r"^/news/press-center/", "press-center"),
    (r"^/news/featured-stories/", "featured-stories"),
    (r"^/news/", "news"),
    (r"^/policy-issues/", "policy-issues"),
    (r"^/about/", "about"),
    (r"^/services/", "services"),
    (r"^/resource-center/", "resource-center"),
    (r"^/system/files/", None),  # Skip file downloads in content
]


class TreasuryScraper:
    def __init__(self):
        self.discovered_urls = set()
        self.scraped_urls = set()
        self.failed_urls = set()
        self.assets = set()
        
        # HTML to Markdown converter
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.body_width = 0  # Don't wrap lines
        self.h2t.protect_links = True
        
        # Ensure directories exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def discover_from_sitemap(self):
        """Try to fetch and parse sitemap(s)."""
        print("🔍 Attempting to discover URLs from sitemap...")
        
        for sitemap_url in SITEMAP_URLS:
            try:
                response = requests.get(sitemap_url, timeout=30)
                if response.status_code == 200:
                    print(f"  ✓ Found sitemap at {sitemap_url}")
                    self._parse_sitemap(response.text, sitemap_url)
            except Exception as e:
                print(f"  ✗ Failed to fetch {sitemap_url}: {e}")
        
        print(f"  → Discovered {len(self.discovered_urls)} URLs from sitemaps")

    def _parse_sitemap(self, content, url):
        """Parse sitemap XML content."""
        soup = BeautifulSoup(content, "lxml-xml")
        
        # Check if it's a sitemap index
        sitemap_tags = soup.find_all("sitemap")
        if sitemap_tags:
            print(f"  → Found sitemap index with {len(sitemap_tags)} sitemaps")
            for sitemap in sitemap_tags:
                loc = sitemap.find("loc")
                if loc:
                    try:
                        resp = requests.get(loc.text.strip(), timeout=30)
                        if resp.status_code == 200:
                            self._parse_sitemap(resp.text, loc.text.strip())
                    except Exception as e:
                        print(f"    ✗ Failed to fetch {loc.text}: {e}")
        
        # Parse URL entries
        url_tags = soup.find_all("url")
        for url_tag in url_tags:
            loc = url_tag.find("loc")
            if loc:
                self.discovered_urls.add(loc.text.strip())

    def discover_from_crawl(self, max_pages=500):
        """Crawl the site to discover URLs."""
        print(f"🕷️ Crawling site to discover URLs (max {max_pages} pages)...")
        
        to_visit = {BASE_URL, f"{BASE_URL}/"}
        visited = set()
        
        with tqdm(total=max_pages, desc="Crawling") as pbar:
            while to_visit and len(visited) < max_pages:
                url = to_visit.pop()
                if url in visited:
                    continue
                
                try:
                    response = requests.get(url, timeout=30)
                    visited.add(url)
                    pbar.update(1)
                    
                    if response.status_code == 200:
                        self.discovered_urls.add(url)
                        soup = BeautifulSoup(response.text, "lxml")
                        
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            full_url = urljoin(url, href)
                            
                            # Only follow internal links
                            if full_url.startswith(BASE_URL):
                                # Skip files, anchors, query strings
                                parsed = urlparse(full_url)
                                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                                
                                if clean_url not in visited:
                                    to_visit.add(clean_url)
                                    
                except Exception as e:
                    pass  # Silently skip failed URLs during discovery
        
        print(f"  → Discovered {len(self.discovered_urls)} URLs from crawling")

    def save_discovered_urls(self):
        """Save discovered URLs to a JSON file."""
        cache_file = CACHE_DIR / "discovered_urls.json"
        data = {
            "discovered_at": datetime.now().isoformat(),
            "count": len(self.discovered_urls),
            "urls": sorted(list(self.discovered_urls))
        }
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved {len(self.discovered_urls)} URLs to {cache_file}")

    def load_discovered_urls(self):
        """Load previously discovered URLs."""
        cache_file = CACHE_DIR / "discovered_urls.json"
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                self.discovered_urls = set(data["urls"])
                print(f"📂 Loaded {len(self.discovered_urls)} URLs from cache")
                return True
        return False

    def classify_url(self, url):
        """Determine content type and output path for a URL."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        
        if not path:
            return "home", "_index.md"
        
        # Check against patterns
        for pattern, content_type in CONTENT_TYPE_PATTERNS:
            if re.match(pattern, path):
                if content_type is None:
                    return None, None  # Skip this URL
                break
        else:
            content_type = "pages"
        
        # Generate output path
        path_parts = [p for p in path.split("/") if p]
        
        if len(path_parts) == 0:
            return "home", "_index.md"
        
        # Section index pages
        if len(path_parts) == 1:
            return path_parts[0], "_index.md"
        
        # Regular pages
        filename = f"{path_parts[-1]}.md"
        section = "/".join(path_parts[:-1])
        
        return section, filename

    def extract_metadata(self, soup, url):
        """Extract front matter metadata from page."""
        metadata = {
            "url": urlparse(url).path,
            "draft": False,
        }
        
        # Title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.text.strip()
            # Remove site name suffix
            title = re.sub(r"\s*\|\s*U\.?S\.?\s*Department of the Treasury.*$", "", title)
            metadata["title"] = title
        
        # Meta description
        desc_tag = soup.find("meta", {"name": "description"})
        if desc_tag and desc_tag.get("content"):
            metadata["description"] = desc_tag["content"]
        
        # Date - look for various date indicators
        date_patterns = [
            (soup.find("meta", {"property": "article:published_time"}), "content"),
            (soup.find("time", {"datetime": True}), "datetime"),
            (soup.find(class_=re.compile(r"date|published|posted")), "text"),
        ]
        for tag, attr in date_patterns:
            if tag:
                date_str = tag.get(attr) if attr != "text" else tag.text
                if date_str:
                    try:
                        # Try to parse the date
                        parsed_date = self._parse_date(date_str.strip())
                        if parsed_date:
                            metadata["date"] = parsed_date
                            break
                    except:
                        pass
        
        # Categories/Tags
        for meta_tag in soup.find_all("meta", {"property": "article:tag"}):
            if "tags" not in metadata:
                metadata["tags"] = []
            metadata["tags"].append(meta_tag.get("content"))
        
        # Open Graph image
        og_image = soup.find("meta", {"property": "og:image"})
        if og_image and og_image.get("content"):
            metadata["image"] = og_image["content"]
        
        return metadata

    def _parse_date(self, date_str):
        """Try to parse a date string in various formats."""
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:len(date_str)], fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def extract_content(self, soup):
        """Extract main content from page."""
        # Try to find main content area
        content_selectors = [
            ("main", {}),
            ("article", {}),
            ("div", {"class": re.compile(r"content|main|body", re.I)}),
            ("div", {"id": re.compile(r"content|main|body", re.I)}),
            ("div", {"role": "main"}),
        ]
        
        content = None
        for tag, attrs in content_selectors:
            content = soup.find(tag, attrs)
            if content:
                break
        
        if not content:
            content = soup.find("body")
        
        if not content:
            return ""
        
        # Remove unwanted elements
        for unwanted in content.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            unwanted.decompose()
        
        # Remove navigation and menu elements
        for unwanted in content.find_all(class_=re.compile(r"nav|menu|sidebar|breadcrumb|skip", re.I)):
            unwanted.decompose()
        
        # Convert to Markdown
        html_content = str(content)
        markdown = self.h2t.handle(html_content)
        
        # Clean up markdown
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)  # Multiple newlines
        markdown = markdown.strip()
        
        return markdown

    def collect_assets(self, soup, url):
        """Find and record assets (images, PDFs, etc.) to download."""
        base = urlparse(url)
        
        # Images
        for img in soup.find_all("img", src=True):
            src = img["src"]
            full_url = urljoin(url, src)
            if full_url.startswith(BASE_URL):
                self.assets.add(full_url)
        
        # PDFs and documents
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]):
                full_url = urljoin(url, href)
                if full_url.startswith(BASE_URL):
                    self.assets.add(full_url)

    def scrape_page(self, url):
        """Scrape a single page and convert to Hugo content."""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                self.failed_urls.add(url)
                return False
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Classify the URL
            section, filename = self.classify_url(url)
            if section is None:
                return True  # Skip but don't mark as failed
            
            # Extract metadata and content
            metadata = self.extract_metadata(soup, url)
            content = self.extract_content(soup)
            
            # Collect assets
            self.collect_assets(soup, url)
            
            # Write content file
            output_path = OUTPUT_DIR / section / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            front_matter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(front_matter)
                f.write("---\n\n")
                f.write(content)
            
            self.scraped_urls.add(url)
            return True
            
        except Exception as e:
            self.failed_urls.add(url)
            return False

    async def download_asset(self, session, url, semaphore):
        """Download a single asset."""
        async with semaphore:
            try:
                parsed = urlparse(url)
                local_path = ASSETS_DIR / parsed.path.lstrip("/")
                
                # Skip if already exists
                if local_path.exists():
                    return True
                
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(local_path, "wb") as f:
                            await f.write(content)
                        return True
            except Exception as e:
                pass
            return False

    async def download_assets(self, max_concurrent=10):
        """Download all collected assets."""
        if not self.assets:
            print("📦 No assets to download")
            return
        
        print(f"📦 Downloading {len(self.assets)} assets...")
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_asset(session, url, semaphore) for url in self.assets]
            results = []
            for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Assets"):
                result = await coro
                results.append(result)
        
        success = sum(results)
        print(f"  → Downloaded {success}/{len(self.assets)} assets")

    def scrape_all(self):
        """Scrape all discovered URLs."""
        print(f"📄 Scraping {len(self.discovered_urls)} pages...")
        
        for url in tqdm(sorted(self.discovered_urls), desc="Scraping"):
            self.scrape_page(url)
        
        print(f"  → Scraped {len(self.scraped_urls)} pages successfully")
        print(f"  → Failed: {len(self.failed_urls)} pages")
        
        # Save failed URLs for review
        if self.failed_urls:
            failed_file = CACHE_DIR / "failed_urls.json"
            with open(failed_file, "w") as f:
                json.dump(sorted(list(self.failed_urls)), f, indent=2)
            print(f"  → Saved failed URLs to {failed_file}")

    def generate_report(self):
        """Generate a migration report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "discovered_urls": len(self.discovered_urls),
            "scraped_urls": len(self.scraped_urls),
            "failed_urls": len(self.failed_urls),
            "assets_found": len(self.assets),
            "content_sections": {},
        }
        
        # Count content by section
        for path in OUTPUT_DIR.rglob("*.md"):
            section = path.parent.relative_to(OUTPUT_DIR).as_posix()
            if section not in report["content_sections"]:
                report["content_sections"][section] = 0
            report["content_sections"][section] += 1
        
        report_file = DATA_DIR / "migration_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Migration Report:")
        print(f"   Discovered: {report['discovered_urls']} URLs")
        print(f"   Scraped: {report['scraped_urls']} pages")
        print(f"   Failed: {report['failed_urls']} pages")
        print(f"   Assets: {report['assets_found']} files")
        print(f"   Report saved to {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Scrape home.treasury.gov for Hugo migration")
    parser.add_argument("--discover", action="store_true", help="Discover URLs from sitemap and crawling")
    parser.add_argument("--scrape", action="store_true", help="Scrape discovered URLs")
    parser.add_argument("--assets", action="store_true", help="Download assets")
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--max-crawl", type=int, default=500, help="Max pages to crawl (default: 500)")
    
    args = parser.parse_args()
    
    if not any([args.discover, args.scrape, args.assets, args.all]):
        parser.print_help()
        sys.exit(1)
    
    scraper = TreasuryScraper()
    
    if args.discover or args.all:
        scraper.discover_from_sitemap()
        scraper.discover_from_crawl(max_pages=args.max_crawl)
        scraper.save_discovered_urls()
    
    if args.scrape or args.all:
        if not scraper.discovered_urls:
            if not scraper.load_discovered_urls():
                print("❌ No URLs discovered. Run with --discover first.")
                sys.exit(1)
        scraper.scrape_all()
        scraper.generate_report()
    
    if args.assets or args.all:
        if scraper.assets:
            asyncio.run(scraper.download_assets())
        else:
            print("📦 No assets collected. Run --scrape first to collect asset URLs.")


if __name__ == "__main__":
    main()
