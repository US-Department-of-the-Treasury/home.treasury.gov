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
- Rate limiting with random jitter
- Resume support (saves state to continue interrupted crawls)
- CDN block detection (Akamai, CloudFront)
- Browser-like headers to avoid blocks

**Usage:**
```bash
python crawler.py <url> [options]

Options:
  --output, -o         Output directory (default: ./crawl_output)
  --rate-limit, -r     Requests per second (default: 2)
  --max-depth, -d      Maximum crawl depth (default: 10)
  --no-verify-ssl      Disable SSL verification
  --no-assets          Skip downloading assets
  --start-urls         Additional URLs to start from
  --focus, -f          Focus on specific path prefix (e.g., /news/press-releases)
  --use-sitemap-from   Use sitemap from alternate URL to discover URLs
```

**Output Structure:**
```
crawl_output/
├── crawl_state.json    # Crawl state (for resume)
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
  --rate-limit, -r      Requests per second (default: 2)
  --no-verify-ssl       Disable SSL verification
  --no-assets           Skip downloading assets
  --text-threshold      Text similarity threshold (default: 0.9)
  --visual-threshold    Visual difference threshold (default: 0.01)
  --viewports           Viewport sizes: desktop tablet mobile
  --workers, -w         Number of parallel workers (default: 8)
  --focus, -f           Focus on specific path prefix (e.g., /news/press-releases)
  --use-target-sitemap  Use target's sitemap for source URL discovery
  --skip-crawl          Skip crawling (use existing data)
  --skip-text           Skip text comparison
  --skip-visual         Skip visual comparison
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

### 3. Crawl with Alternate Sitemap

When source site blocks sitemap access:

```bash
# Use localhost sitemap to discover URLs, fetch from live site
python crawler.py https://home.treasury.gov \
    --use-sitemap-from http://localhost:1313 \
    --focus /news/press-releases \
    --rate-limit 1 \
    --output ./crawl_source
```

### 4. Visual Comparison Only

```bash
python visual_comparator.py \
    https://home.treasury.gov \
    http://localhost:1313 \
    --urls-file critical_pages.txt \
    --viewports desktop mobile \
    --output ./visual_report
```

### 5. Check Crawl State

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

### 6. Reset and Start Fresh

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
# 1. Use very low rate limit
python crawler.py https://example.com --rate-limit 0.5

# 2. Use target's sitemap for URL discovery
python mirror.py https://example.com \
    --target-url http://localhost:1313 \
    --use-target-sitemap

# 3. Whitelist your IP in Akamai console (if you have access)
```

The crawler uses browser-like headers and random delays to minimize blocks.

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
