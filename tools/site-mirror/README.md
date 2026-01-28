# Site Mirror - Website Mirroring and Comparison Tools

A first-principles approach to capturing and verifying website migrations. This toolset crawls websites, downloads all content, and performs both text-based and visual comparisons to ensure completeness.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      SITE MIRROR                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐         ┌─────────────┐                    │
│  │   SOURCE    │         │   TARGET    │                    │
│  │    SITE     │         │    SITE     │                    │
│  └──────┬──────┘         └──────┬──────┘                    │
│         │                       │                            │
│         ▼                       ▼                            │
│  ┌─────────────────────────────────────────┐                │
│  │            PHASE 1: CRAWL               │                │
│  │  • Sitemap.xml parsing                  │                │
│  │  • Recursive link discovery             │                │
│  │  • Asset downloading (PDF, images)      │                │
│  │  • Resume support                       │                │
│  │  • CDN block detection                  │                │
│  └─────────────────────────────────────────┘                │
│         │                       │                            │
│         ▼                       ▼                            │
│  ┌─────────────────────────────────────────┐                │
│  │         PHASE 2: TEXT COMPARISON        │                │
│  │  • Content extraction (strips nav/footer)│               │
│  │  • Path normalization (trailing slashes) │               │
│  │  • Similarity scoring                   │                │
│  │  • Diff generation                      │                │
│  └─────────────────────────────────────────┘                │
│         │                       │                            │
│         ▼                       ▼                            │
│  ┌─────────────────────────────────────────┐                │
│  │        PHASE 3: VISUAL COMPARISON       │                │
│  │  • Playwright screenshots               │                │
│  │  • Pixel-level diff                     │                │
│  │  • Multiple viewports                   │                │
│  │  • Dynamic content handling             │                │
│  └─────────────────────────────────────────┘                │
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────┐                │
│  │           CONSOLIDATED REPORT           │                │
│  │  • HTML report with visual diffs        │                │
│  │  • JSON data for CI/CD integration      │                │
│  │  • Pass/Warning/Fail status             │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Create virtual environment
cd tools/site-mirror
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Quick Start

### Full Mirror Workflow

Compare a live site against your local Hugo server:

```bash
# Start Hugo server in another terminal
hugo server

# Run comparison (use --use-target-sitemap if source blocks sitemap)
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --use-target-sitemap \
    --rate-limit 1 \
    --depth 1 \
    --output ./report
```

### Individual Tools

Each tool can be used independently:

```bash
# 1. Crawl a site
python crawler.py https://home.treasury.gov \
    --output ./crawl_source \
    --rate-limit 1 \
    --max-depth 5

# 2. Compare text content
python text_comparator.py ./crawl_source ./crawl_target \
    --output ./text_report \
    --threshold 0.9 \
    --focus /news/press-releases

# 3. Compare visual appearance
python visual_comparator.py https://home.treasury.gov https://staging.treasury.gov \
    --urls-file urls.txt \
    --output ./visual_report \
    --viewport desktop
```

---

## Tools Reference

### `crawler.py` - Site Crawler

Downloads all pages and assets from a website.

**Features:**
- Sitemap.xml parsing for URL discovery
- Alternate sitemap support (use target's sitemap for source crawl)
- Recursive link following
- Binary asset downloading (PDF, images, etc.)
- **Strict rate limiting** - enforces aggregate limit across all concurrent requests
- Resume support (saves state to continue interrupted crawls)
- CDN block detection (Akamai, CloudFront)
- Browser-like headers to avoid blocks

**Usage:**
```bash
python crawler.py <url> [options]

Options:
  --output, -o         Output directory (default: ./crawl_output)
  --rate-limit, -r     Max requests per second, aggregate (default: 2)
  --max-concurrent, -c Max concurrent HTTP connections (default: 10)
  --max-depth, -d      Maximum crawl depth (default: 10)
  --no-verify-ssl      Disable SSL verification
  --no-assets          Skip downloading assets
  --start-urls         Additional URLs to start from
  --focus, -f          Focus on specific path prefix (e.g., /news/press-releases)
  --use-sitemap-from   Use sitemap from alternate URL to discover URLs
```

**Rate Limiting:**

The `--rate-limit` flag enforces a **global aggregate limit** across all concurrent requests:

```bash
--rate-limit 5           # Max 5 requests/second total (not per connection)
--max-concurrent 10      # Up to 10 HTTP connections at once
```

This is enforced strictly - if you set `--rate-limit 2`, the crawler will never exceed 2 requests per second regardless of concurrency.

**Output Structure:**
```
crawl_output/
├── crawl_state.json    # Crawl state (for resume)
├── crawl_errors.json   # Detailed error log (for IT troubleshooting)
├── pages/              # HTML pages
│   ├── index.html
│   ├── about/
│   │   └── index.html
│   └── news/
│       └── press-releases/
│           └── article-slug.html
└── assets/             # Binary assets
    ├── document.pdf
    └── image.png
```

**Error Log (`crawl_errors.json`):**

Contains detailed error information for IT troubleshooting:
```json
{
  "total_errors": 5,
  "generated_at": "2024-01-21T10:30:00",
  "base_url": "https://home.treasury.gov",
  "errors": [
    {
      "url": "https://home.treasury.gov/news/...",
      "status_code": 403,
      "error_type": "cdn_block",
      "error_message": "Blocked by CDN (Access Denied)",
      "response_headers": { "server": "AkamaiGHost", ... },
      "response_body_preview": "<html>Access Denied...",
      "timestamp": "2024-01-21T10:30:00"
    }
  ]
}
```

Error types: `cdn_block`, `http_error`, `timeout`, `connection_error`, `unknown`

---

### `text_comparator.py` - Text Content Comparison

Compares extracted text content between two crawled sites.

**Features:**
- Main content extraction (strips navigation, footer, etc.)
- Text normalization (whitespace, encoding)
- Path normalization (handles trailing slash differences)
- Similarity scoring using SequenceMatcher
- Parallel processing for speed
- Diff generation for changed content
- Missing content detection

**Usage:**
```bash
python text_comparator.py <source_dir> <target_dir> [options]

Options:
  --output, -o      Output directory (default: ./comparison_report)
  --threshold, -t   Similarity threshold (default: 0.9 = 90%)
  --workers, -w     Number of parallel workers (default: 8)
  --focus, -f       Focus on specific path prefix
```

**Output:**
- `comparison_report.json` - Detailed comparison data
- `comparison_report.html` - Visual HTML report

**Comparison Statuses:**
| Status | Description |
|--------|-------------|
| `identical` | 99%+ similarity |
| `similar` | Above threshold (default 90%) |
| `different` | Below threshold |
| `missing_target` | URL exists in source but not target |
| `missing_source` | URL exists in target but not source |

---

### `visual_comparator.py` - Visual Screenshot Comparison

Compares visual appearance using Playwright screenshots.

**Features:**
- Headless browser screenshots
- Pixel-level comparison
- Multiple viewport sizes (desktop, tablet, mobile)
- Dynamic content hiding (dates, timestamps)
- Parallel screenshot capture
- Visual diff image generation

**Usage:**
```bash
python visual_comparator.py <source_url> <target_url> [options]

Options:
  --urls-file       File with URL paths to compare (one per line)
  --output, -o      Output directory (default: ./visual_report)
  --viewport, -v    Viewport size: desktop, tablet, mobile
  --threshold, -t   Difference threshold (default: 0.01 = 1%)
  --concurrency, -c Number of parallel comparisons (default: 4)
```

**Output:**
- `visual_report.json` - Comparison data
- `visual_report.html` - Report with embedded diff images
- `screenshots/` - Individual screenshots
- `diffs/` - Side-by-side diff images

**Diff Image Format:**
```
┌────────────┬────────────┬────────────┐
│   SOURCE   │   TARGET   │    DIFF    │
│            │            │ (red = Δ)  │
└────────────┴────────────┴────────────┘
```

---

### `mirror.py` - Main Orchestrator

Runs the complete workflow: crawl → text compare → visual compare → report.

**Usage:**
```bash
python mirror.py <source_url> [options]

Required (one of):
  --target-url      Target site URL to compare
  --target-dir      Local directory (Hugo build) to compare

Options:
  --output, -o          Output directory (default: ./mirror_output)
  --depth, -d           Maximum crawl depth (default: 10)
  --rate-limit, -r      Max requests per second, aggregate (default: 5)
  --max-concurrent, -c  Max concurrent HTTP connections (default: 10)
  --no-verify-ssl       Disable SSL verification
  --no-assets           Skip downloading assets
  --text-threshold      Text similarity threshold (default: 0.9)
  --visual-threshold    Visual difference threshold (default: 0.01)
  --viewports           Viewport sizes: desktop tablet mobile
  --workers, -w         Parallel workers for text comparison (default: 8)
  --focus, -f           Focus on specific path prefix (e.g., /news/press-releases)
  --use-target-sitemap  Use target's sitemap for source URL discovery
  --skip-crawl          Skip crawling (use existing data)
  --skip-source-crawl   Skip crawling source (only crawl target)
  --skip-target-crawl   Skip crawling target (only crawl source)
  --skip-text           Skip text comparison
  --skip-visual         Skip visual comparison
  --pages-only           Fast comparison using local crawl data (URL + text comparison, excludes assets)
```

**Concurrency Options Explained:**

| Flag | Controls | Used By |
|------|----------|---------|
| `--rate-limit` | Max HTTP requests/second (aggregate) | Crawler |
| `--max-concurrent` | Max simultaneous HTTP connections | Crawler |
| `--workers` | CPU threads for text diffing | Text Comparator |

```bash
# Example: gentle crawl, fast comparison
python mirror.py https://example.com \
    --target-url http://localhost:1313 \
    --rate-limit 2 \        # 2 req/s to avoid CDN blocks
    --max-concurrent 5 \    # 5 connections max
    --workers 16            # 16 threads for text comparison (CPU-bound)
```

**Example - Compare Against Local Hugo Server:**
```bash
# Terminal 1: Start Hugo server
hugo server

# Terminal 2: Run comparison
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --use-target-sitemap \
    --rate-limit 1 \
    --depth 1 \
    --workers 16 \
    --output ./report
```

**Example - Skip Crawl (Use Existing Data):**
```bash
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --skip-crawl \
    --workers 16 \
    --output ./report
```

**Example - Pages-Only Comparison (URL + Text):**

The `--pages-only` flag provides a lightweight comparison mode that:
- Compares webpage URLs only (excludes PDFs, images, JS, CSS, etc.)
- Uses local crawl data if available (very fast), otherwise fetches from sitemaps
- Generates both URL comparison and text comparison reports
- Uses `--workers` for parallel text comparison

```bash
# Compare pages using existing crawl data
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --pages-only \
    --workers 16 \
    --output ./report
```

If no local crawl data exists, it fetches sitemaps. Use `--use-target-sitemap` to avoid CDN blocks:

```bash
# Fetch from sitemaps (use target sitemap to avoid source CDN block)
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --pages-only \
    --use-target-sitemap \
    --focus /news/press-releases \
    --output ./report
```

**Output structure:**
```
report/
├── url_comparison.json          # URL set comparison data
├── url_comparison.html          # URL comparison report
├── missing_in_target.txt        # URLs to migrate
├── missing_in_source.txt        # New URLs only on target
└── text_comparison/
    ├── text_comparison.json     # Text similarity data
    └── text_comparison.html     # Text comparison report
```

**URL-only mode (skip text comparison):**
```bash
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --pages-only \
    --skip-text \
    --output ./report
```

---

### `check_missing.py` - Extract Missing URLs

Extracts missing URLs from comparison reports for further analysis or IT troubleshooting.

**Usage:**
```bash
python check_missing.py <report_path> [options]

Options:
  --missing-type    Type of missing URLs: target or source (default: target)
  --focus, -f       Filter to specific path prefix
  --output, -o      Output file (default: missing_urls.txt)
```

**Examples:**
```bash
# Extract URLs missing in target (pages that need to be migrated)
python check_missing.py report/text_comparison/text_comparison.json

# Extract URLs missing in source (new pages only on target)
python check_missing.py report/text_comparison/text_comparison.json --missing-type source

# Filter to specific section
python check_missing.py report/text_comparison/text_comparison.json --focus /news/press-releases

# Custom output file
python check_missing.py report/text_comparison/text_comparison.json -o pages_to_migrate.txt
```

**Output:**
- `missing_urls.txt` - One URL path per line, sorted alphabetically

---

## Output Reports

### Consolidated Report (`mirror_report.html`)

The main report includes:
- **Overall Status**: PASS / WARNING / FAIL
- **Crawl Summary**: URLs discovered and crawled
- **Text Comparison**: Identical, similar, different, missing counts
- **Visual Comparison**: Per-viewport comparison results
- **Links**: To detailed sub-reports

### Status Criteria

| Status | Condition |
|--------|-----------|
| **PASS** | >80% identical text, <20% visual differences |
| **WARNING** | <80% identical OR >20% visual differences |
| **FAIL** | >10% missing pages in target |

---

## Common Use Cases

### 1. Compare Press Releases Section

```bash
# Use target sitemap since source CDN may block
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --use-target-sitemap \
    --rate-limit 1 \
    --output ./press_releases_report
```

### 2. Quick Re-comparison (Skip Crawl)

```bash
# After initial crawl, re-run just the comparison
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --skip-crawl \
    --output ./report
```

### 3. Pages-Only Comparison (Fast)

Use `--pages-only` after crawling to quickly re-compare using local data:

```bash
# Uses local crawl data - very fast, parallel processing
python mirror.py https://home.treasury.gov \
    --target-url http://localhost:1313 \
    --focus /news/press-releases \
    --pages-only \
    --workers 16 \
    --output ./report
```

This generates both `url_comparison.*` and `text_comparison/` reports. Uses local crawl files if available, otherwise fetches from sitemaps.

Add `--skip-text` to skip text comparison and only compare URL sets.

### 4. Crawl with Alternate Sitemap

When source site blocks sitemap access:

```bash
# Use localhost sitemap to discover URLs, fetch from live site
python crawler.py https://home.treasury.gov \
    --use-sitemap-from http://localhost:1313 \
    --focus /news/press-releases \
    --rate-limit 1 \
    --output ./crawl_source
```

### 5. Visual Comparison Only

```bash
python visual_comparator.py \
    https://home.treasury.gov \
    http://localhost:1313 \
    --urls-file critical_pages.txt \
    --viewports desktop mobile \
    --output ./visual_report
```

### 6. Check Crawl State

```bash
# View crawl progress
cat report/crawl_source/crawl_state.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'Discovered: {len(d[\"discovered_urls\"])}')
print(f'Crawled: {len(d[\"crawled_urls\"])}')
print(f'Failed: {len(d[\"failed_urls\"])}')
"
```

### 7. Reset and Start Fresh

```bash
# Delete crawl state to start over
rm -rf report/crawl_source
rm -rf report/crawl_target
```

---

## Troubleshooting

### CDN Blocking (Akamai/CloudFront)

If crawling gets blocked with "Access Denied":

```bash
# 1. Use very low rate limit and concurrency
python crawler.py https://example.com --rate-limit 0.5 --max-concurrent 2

# 2. Use target's sitemap for URL discovery
python mirror.py https://example.com \
    --target-url http://localhost:1313 \
    --use-target-sitemap

# 3. Whitelist your IP in Akamai console (if you have access)
```

The crawler uses browser-like headers to minimize blocks. Rate limiting is strictly enforced - `--rate-limit 2` guarantees no more than 2 requests/second regardless of concurrency.

### SSL Certificate Errors

```bash
# Disable SSL verification (for self-signed certs)
python crawler.py https://example.com --no-verify-ssl
```

### Path Mismatch (Trailing Slashes)

The text comparator normalizes paths automatically:
- `/news/press-releases/jy123` and `/news/press-releases/jy123/` are treated as the same

### Memory Issues (Large Sites)

```bash
# Limit crawl depth and skip assets
python crawler.py https://example.com --max-depth 3 --no-assets
```

### Resume Interrupted Crawl

The crawler automatically saves state. Simply re-run the same command:

```bash
# Will resume from where it left off
python crawler.py https://example.com --output ./crawl_output
```

---

## Architecture

```
tools/site-mirror/
├── mirror.py              # Main orchestrator
├── crawler.py             # Sitemap + recursive crawler
├── text_comparator.py     # Text content comparison
├── visual_comparator.py   # Screenshot comparison
├── check_missing.py       # Extract missing URLs from reports
├── requirements.txt       # Python dependencies
├── .gitignore             # Ignore output files
└── README.md              # This file
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `httpx` | Async HTTP client |
| `beautifulsoup4` | HTML parsing |
| `playwright` | Headless browser |
| `Pillow` | Image processing |
| `lxml` | XML/HTML parsing |

---

## How It Works

### URL Discovery
1. Parse sitemap.xml (or use alternate sitemap via `--use-sitemap-from`)
2. Follow links recursively up to `--depth`
3. Filter by `--focus` path prefix if specified

### Text Comparison
1. Extract main content from HTML (strips nav, footer, scripts)
2. Normalize paths (remove trailing slashes, ignore domain)
3. Compare using SequenceMatcher similarity ratio
4. Generate diffs for changed content

### Visual Comparison
1. Capture screenshots with Playwright
2. Compare pixel-by-pixel
3. Generate diff images highlighting changes

---

## Comparison with Existing Methodology

| Aspect | Existing (JSON API) | Site Mirror (Crawler) |
|--------|--------------------|-----------------------|
| **Discovery** | Manual category endpoints | Sitemap + recursive |
| **Scope** | News content only | Entire site |
| **Assets** | Not migrated | Downloaded + verified |
| **Verification** | None | Text + Visual diff |
| **Completeness** | Manual tracking | Automated detection |
| **Output** | Markdown files | Crawl archive + reports |

The two approaches are complementary:
- **JSON API scraper**: Best for structured content (news articles)
- **Site Mirror**: Best for completeness verification and gap detection
