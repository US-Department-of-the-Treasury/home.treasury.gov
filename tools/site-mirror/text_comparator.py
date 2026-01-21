#!/usr/bin/env python3
"""
Text Comparator - Compares text content between source and migrated sites.

Features:
- Extracts main content from HTML (strips boilerplate)
- Normalizes whitespace and formatting
- Generates diff reports with similarity scores
- Identifies missing, added, and changed content
- Outputs detailed comparison report

Performance optimizations:
- Parallel processing with ThreadPoolExecutor
- Hash-first comparison (skip diff if identical)
- Fast lxml parser
- Resume support
"""

import argparse
import difflib
import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

from bs4 import BeautifulSoup


@dataclass
class TextComparison:
    """Result of comparing text content between two pages."""
    url: str
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    similarity: float = 0.0
    source_word_count: int = 0
    target_word_count: int = 0
    missing_in_target: list[str] = field(default_factory=list)
    added_in_target: list[str] = field(default_factory=list)
    status: str = "unknown"  # identical, similar, different, missing_source, missing_target
    diff_snippet: str = ""


@dataclass
class ComparisonReport:
    """Overall comparison report."""
    source_dir: str
    target_dir: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_urls: int = 0
    identical: int = 0
    similar: int = 0  # >90% similarity
    different: int = 0  # <90% similarity
    missing_in_target: int = 0
    missing_in_source: int = 0
    comparisons: list[TextComparison] = field(default_factory=list)

    def save(self, path: Path):
        """Save report to JSON."""
        data = asdict(self)
        path.write_text(json.dumps(data, indent=2))


class TextExtractor:
    """Extracts main content text from HTML."""

    # Elements that typically contain main content
    CONTENT_SELECTORS = [
        "main",
        "article",
        "[role='main']",
        ".main-content",
        ".content",
        "#content",
        ".post-content",
        ".entry-content",
    ]

    # Elements to remove (navigation, footer, etc.)
    REMOVE_SELECTORS = [
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        ".navigation",
        ".menu",
        ".breadcrumb",
        ".footer",
        ".header",
        "script",
        "style",
        "noscript",
        "[role='navigation']",
        "[role='banner']",
        "[role='contentinfo']",
    ]

    def extract(self, html: str) -> str:
        """Extract main text content from HTML."""
        # Detect XML vs HTML and use appropriate parser
        content_start = html.strip()[:100].lower()
        if content_start.startswith('<?xml') or '<rss' in content_start or '<urlset' in content_start:
            # XML content (sitemap, RSS, etc.) - return empty, not comparable as text
            return ""

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for selector in self.REMOVE_SELECTORS:
            for elem in soup.select(selector):
                elem.decompose()

        # Try to find main content container
        content = None
        for selector in self.CONTENT_SELECTORS:
            content = soup.select_one(selector)
            if content:
                break

        # Fall back to body if no content container found
        if not content:
            content = soup.body or soup

        # Extract text
        text = content.get_text(separator="\n", strip=True)

        # Normalize
        text = self._normalize_text(text)

        return text

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove extra newlines
        text = re.sub(r'\n\s*\n', '\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        # Normalize unicode
        text = text.encode('ascii', 'ignore').decode('ascii')

        return text

    def extract_structured(self, html: str) -> dict:
        """Extract structured content (headings, paragraphs, lists)."""
        # Detect XML vs HTML
        content_start = html.strip()[:100].lower()
        if content_start.startswith('<?xml') or '<rss' in content_start or '<urlset' in content_start:
            return {"title": "", "headings": [], "paragraphs": [], "lists": [], "links": [], "meta": {}}

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for selector in self.REMOVE_SELECTORS:
            for elem in soup.select(selector):
                elem.decompose()

        content = None
        for selector in self.CONTENT_SELECTORS:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.body or soup

        structured = {
            "title": "",
            "headings": [],
            "paragraphs": [],
            "lists": [],
            "links": [],
            "meta": {}
        }

        # Extract title
        title = soup.find("title")
        if title:
            structured["title"] = title.get_text(strip=True)

        # Extract meta
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content_val = meta.get("content")
            if name and content_val:
                structured["meta"][name] = content_val

        # Extract headings
        for level in range(1, 7):
            for heading in content.find_all(f"h{level}"):
                structured["headings"].append({
                    "level": level,
                    "text": heading.get_text(strip=True)
                })

        # Extract paragraphs
        for p in content.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                structured["paragraphs"].append(text)

        # Extract lists
        for ul in content.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            if items:
                structured["lists"].append(items)

        # Extract links
        for a in content.find_all("a", href=True):
            structured["links"].append({
                "text": a.get_text(strip=True),
                "href": a["href"]
            })

        return structured


class TextComparator:
    """Compares text content between two site crawls."""

    def __init__(
        self,
        source_dir: Path,
        target_dir: Path,
        similarity_threshold: float = 0.9,
        num_workers: int = None,
        focus_path: Optional[str] = None
    ):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.similarity_threshold = similarity_threshold
        self.num_workers = num_workers or min(8, multiprocessing.cpu_count())
        self.extractor = TextExtractor()
        self.focus_path = focus_path.rstrip('/') if focus_path else None

        # Cache for extracted text (avoids re-parsing)
        self._text_cache: dict[str, str] = {}
        self._hash_cache: dict[str, str] = {}

    def _matches_focus(self, url: str) -> bool:
        """Check if URL matches the focus path prefix."""
        if not self.focus_path:
            return True
        parsed = urlparse(url)
        path = parsed.path
        return path.startswith(self.focus_path) or path.startswith(self.focus_path + '/')

    def compare_all(self) -> ComparisonReport:
        """Compare all pages between source and target using parallel processing."""
        report = ComparisonReport(
            source_dir=str(self.source_dir),
            target_dir=str(self.target_dir)
        )

        # Load crawl states to get URL mappings
        source_state = self._load_crawl_state(self.source_dir)
        target_state = self._load_crawl_state(self.target_dir)

        if not source_state or not target_state:
            print("Error: Could not load crawl states")
            return report

        source_urls = set(source_state.get("crawled_urls", []))
        target_urls = set(target_state.get("crawled_urls", []))

        # Filter by focus path if set
        if self.focus_path:
            source_urls = {u for u in source_urls if self._matches_focus(u)}
            target_urls = {u for u in target_urls if self._matches_focus(u)}
            print(f"Focus path: {self.focus_path}/* - filtered to {len(source_urls)} source, {len(target_urls)} target URLs")

        # Convert URLs to paths for comparison (ignore domain differences)
        # Normalize paths by stripping trailing slashes for consistent matching
        def normalize_path(url: str) -> str:
            path = urlparse(url).path.rstrip('/')
            return path if path else '/'

        source_paths = {normalize_path(u): u for u in source_urls}
        target_paths = {normalize_path(u): u for u in target_urls}

        all_paths = set(source_paths.keys()) | set(target_paths.keys())
        report.total_urls = len(all_paths)

        print(f"Comparing {len(all_paths)} URL paths with {self.num_workers} workers...")
        print(f"  Source: {len(source_paths)} paths, Target: {len(target_paths)} paths")

        # Parallel comparison
        completed = 0
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_path = {
                executor.submit(self._compare_path, path, source_paths, target_paths): path
                for path in all_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    comparison = future.result()
                except Exception as e:
                    comparison = TextComparison(url=path, status="error")
                    comparison.diff_snippet = str(e)

                report.comparisons.append(comparison)
                completed += 1

                # Update counts
                if comparison.status == "identical":
                    report.identical += 1
                elif comparison.status == "similar":
                    report.similar += 1
                elif comparison.status == "different":
                    report.different += 1
                elif comparison.status == "missing_target":
                    report.missing_in_target += 1
                elif comparison.status == "missing_source":
                    report.missing_in_source += 1

                if completed % 500 == 0:
                    print(f"Progress: {completed}/{len(all_paths)} ({report.identical} identical, {report.different} different)")

        return report

    def _compare_path(
        self,
        path: str,
        source_paths: dict[str, str],
        target_paths: dict[str, str]
    ) -> TextComparison:
        """Compare a single URL path between source and target."""
        comparison = TextComparison(url=path)

        in_source = path in source_paths
        in_target = path in target_paths

        if not in_source:
            comparison.status = "missing_source"
            return comparison

        if not in_target:
            comparison.status = "missing_target"
            return comparison

        # Get full URLs for file path resolution
        source_url = source_paths[path]
        target_url = target_paths[path]

        # Load and compare content
        source_path = self._url_to_path(source_url, self.source_dir)
        target_path = self._url_to_path(target_url, self.target_dir)

        comparison.source_path = str(source_path) if source_path.exists() else None
        comparison.target_path = str(target_path) if target_path.exists() else None

        if not source_path.exists():
            comparison.status = "missing_source"
            return comparison

        if not target_path.exists():
            comparison.status = "missing_target"
            return comparison

        # OPTIMIZATION 1: Hash-first comparison (fast path for identical files)
        try:
            source_bytes = source_path.read_bytes()
            target_bytes = target_path.read_bytes()

            source_hash = hashlib.md5(source_bytes).hexdigest()
            target_hash = hashlib.md5(target_bytes).hexdigest()

            # If raw files are identical, skip text extraction entirely
            if source_hash == target_hash:
                comparison.status = "identical"
                comparison.similarity = 1.0
                # Estimate word count from file size
                comparison.source_word_count = len(source_bytes) // 6
                comparison.target_word_count = len(target_bytes) // 6
                return comparison

            source_html = source_bytes.decode('utf-8', errors='ignore')
            target_html = target_bytes.decode('utf-8', errors='ignore')

        except Exception as e:
            comparison.status = "error"
            comparison.diff_snippet = str(e)
            return comparison

        # Extract text content
        source_text = self.extractor.extract(source_html)
        target_text = self.extractor.extract(target_html)

        # OPTIMIZATION 2: Hash extracted text (catch normalized identical)
        source_text_hash = hashlib.md5(source_text.encode()).hexdigest()
        target_text_hash = hashlib.md5(target_text.encode()).hexdigest()

        comparison.source_word_count = len(source_text.split())
        comparison.target_word_count = len(target_text.split())

        if source_text_hash == target_text_hash:
            comparison.status = "identical"
            comparison.similarity = 1.0
            return comparison

        # OPTIMIZATION 3: Quick length check before expensive similarity
        len_ratio = min(len(source_text), len(target_text)) / max(len(source_text), len(target_text)) if max(len(source_text), len(target_text)) > 0 else 1.0

        if len_ratio < 0.5:
            # Very different lengths - definitely different, skip expensive similarity
            comparison.status = "different"
            comparison.similarity = len_ratio * 0.5  # Rough estimate
            comparison.diff_snippet = f"Length mismatch: source={len(source_text)}, target={len(target_text)}"
            return comparison

        # Calculate full similarity (expensive)
        comparison.similarity = self._calculate_similarity(source_text, target_text)

        # Determine status
        if comparison.similarity >= 0.99:
            comparison.status = "identical"
        elif comparison.similarity >= self.similarity_threshold:
            comparison.status = "similar"
        else:
            comparison.status = "different"

        # Generate diff for different content (only if needed)
        if comparison.status == "different":
            comparison.diff_snippet = self._generate_diff(source_text, target_text)
            comparison.missing_in_target = self._find_missing_sentences(source_text, target_text)
            comparison.added_in_target = self._find_missing_sentences(target_text, source_text)

        return comparison

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _generate_diff(self, source: str, target: str, context: int = 3) -> str:
        """Generate unified diff between source and target."""
        source_lines = source.split('\n')
        target_lines = target.split('\n')

        diff = difflib.unified_diff(
            source_lines,
            target_lines,
            fromfile='source',
            tofile='target',
            lineterm='',
            n=context
        )

        # Return first 50 lines of diff
        diff_lines = list(diff)[:50]
        return '\n'.join(diff_lines)

    def _find_missing_sentences(self, source: str, target: str) -> list[str]:
        """Find sentences in source that are missing from target."""
        # Simple sentence splitting
        source_sentences = set(re.split(r'[.!?]+', source))
        target_sentences = set(re.split(r'[.!?]+', target))

        # Clean up sentences
        source_sentences = {s.strip() for s in source_sentences if len(s.strip()) > 20}
        target_sentences = {s.strip() for s in target_sentences if len(s.strip()) > 20}

        missing = source_sentences - target_sentences

        # Return top 10 missing sentences
        return list(missing)[:10]

    def _load_crawl_state(self, crawl_dir: Path) -> Optional[dict]:
        """Load crawl state from directory."""
        state_file = crawl_dir / "crawl_state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return None

    def _url_to_path(self, url: str, base_dir: Path) -> Path:
        """Convert URL to local file path."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            path = "index"

        if parsed.query:
            query_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
            path = f"{path}_{query_hash}"

        if not Path(path).suffix:
            path = f"{path}.html"

        return base_dir / "pages" / path


def generate_html_report(report: ComparisonReport, output_path: Path):
    """Generate HTML report from comparison results."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Text Comparison Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .stat {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #666; }}
        .identical {{ color: #28a745; }}
        .similar {{ color: #ffc107; }}
        .different {{ color: #dc3545; }}
        .missing {{ color: #6c757d; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .diff {{ background: #f8f8f8; padding: 10px; font-family: monospace; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }}
        .progress {{ background: #e9ecef; border-radius: 4px; overflow: hidden; }}
        .progress-bar {{ height: 8px; }}
    </style>
</head>
<body>
    <h1>Text Comparison Report</h1>
    <p>Generated: {report.timestamp}</p>

    <div class="summary">
        <div class="stat">
            <div class="stat-value">{report.total_urls}</div>
            <div class="stat-label">Total URLs</div>
        </div>
        <div class="stat">
            <div class="stat-value identical">{report.identical}</div>
            <div class="stat-label">Identical</div>
        </div>
        <div class="stat">
            <div class="stat-value similar">{report.similar}</div>
            <div class="stat-label">Similar (&gt;90%)</div>
        </div>
        <div class="stat">
            <div class="stat-value different">{report.different}</div>
            <div class="stat-label">Different</div>
        </div>
        <div class="stat">
            <div class="stat-value missing">{report.missing_in_target}</div>
            <div class="stat-label">Missing in Target</div>
        </div>
        <div class="stat">
            <div class="stat-value missing">{report.missing_in_source}</div>
            <div class="stat-label">Missing in Source</div>
        </div>
    </div>

    <h2>Pages with Differences</h2>
    <table>
        <tr>
            <th>URL</th>
            <th>Similarity</th>
            <th>Status</th>
            <th>Source Words</th>
            <th>Target Words</th>
        </tr>
"""

    # Add rows for pages with differences (sorted by similarity)
    different_pages = [c for c in report.comparisons if c.status in ("different", "missing_target")]
    different_pages.sort(key=lambda x: x.similarity)

    for comp in different_pages[:100]:  # Limit to 100
        status_class = comp.status.replace("_", "-")
        html += f"""
        <tr>
            <td><a href="{comp.url}">{comp.url[:80]}...</a></td>
            <td>{comp.similarity:.1%}</td>
            <td class="{status_class}">{comp.status}</td>
            <td>{comp.source_word_count}</td>
            <td>{comp.target_word_count}</td>
        </tr>
"""

    html += """
    </table>
</body>
</html>
"""

    output_path.write_text(html)


def main():
    parser = argparse.ArgumentParser(
        description="Compare text content between two site crawls"
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Source crawl directory"
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Target crawl directory"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("./comparison_report"),
        help="Output directory for reports"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.9,
        help="Similarity threshold (default: 0.9)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count, max 8)"
    )
    parser.add_argument(
        "--focus", "-f",
        help="Focus on specific path prefix (e.g., /news/press-releases)"
    )

    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    comparator = TextComparator(
        source_dir=args.source,
        target_dir=args.target,
        similarity_threshold=args.threshold,
        num_workers=args.workers,
        focus_path=args.focus
    )

    print(f"Comparing {args.source} vs {args.target}")
    if args.focus:
        print(f"Focus path: {args.focus}/*")
    print("=" * 50)

    report = comparator.compare_all()

    # Save reports
    report.save(args.output / "comparison_report.json")
    generate_html_report(report, args.output / "comparison_report.html")

    # Print summary
    print("\n" + "=" * 50)
    print("COMPARISON SUMMARY")
    print("=" * 50)
    print(f"Total URLs:        {report.total_urls}")
    print(f"Identical:         {report.identical} ({report.identical/report.total_urls:.1%})")
    print(f"Similar (>90%):    {report.similar} ({report.similar/report.total_urls:.1%})")
    print(f"Different:         {report.different} ({report.different/report.total_urls:.1%})")
    print(f"Missing in target: {report.missing_in_target}")
    print(f"Missing in source: {report.missing_in_source}")
    print(f"\nReports saved to: {args.output}")


if __name__ == "__main__":
    main()
