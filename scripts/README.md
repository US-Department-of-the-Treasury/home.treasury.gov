# Scripts

Python utilities for content scraping, link validation, and URL management.

## Prerequisites

```bash
pip install -r ../requirements.txt
```

---

## Link Validation Tools

These scripts help validate and fix URLs in the navigation and footer.

### `test_links.py`

Tests all URLs from `navigation.json` and footer/header templates to ensure they point to live pages.

```bash
python scripts/test_links.py
```

**Output:**
- Reports working links (200), redirects (3xx), and broken links (4xx/5xx)
- Shows context for each URL (which menu item, column, etc.)
- Generates summary statistics

**Use when:** After modifying `data/navigation.json` or updating footer links.

---

### `fetch_live_links.py`

Scrapes the live Treasury site to find correct URLs for broken links.

```bash
python scripts/fetch_live_links.py
```

**What it does:**
1. Takes a list of known broken URLs
2. Searches the live site for similar/related pages
3. Suggests corrected URLs based on what actually exists

**Use when:** You have broken links and need to find where they moved.

---

### `scrape_live_nav.py`

Scrapes the actual mega-menu navigation from the live Treasury site.

```bash
python scripts/scrape_live_nav.py
```

**What it does:**
1. Fetches the homepage and extracts all navigation links
2. Organizes links by section
3. Outputs a mapping of link text → URL

**Use when:** You need to rebuild or verify `navigation.json` against the live site.

---

### `apply_corrections.py`

Bulk applies URL corrections to `navigation.json` and footer templates.

```bash
python scripts/apply_corrections.py
```

**What it does:**
1. Contains a `CORRECTIONS` dictionary mapping old URLs → new URLs
2. Updates `data/navigation.json` with corrected paths
3. Updates `themes/treasury/layouts/partials/footer.html`

**Use when:** You've identified broken URLs and want to fix them in bulk.

**To add new corrections:** Edit the `CORRECTIONS` dict at the top of the file:
```python
CORRECTIONS = {
    "/old/broken/path": "/new/working/path",
    "/another/old": "https://external-site.gov/",
}
```

---

## Content Scrapers

These scripts pull content from the live Treasury site for the Hugo migration.

### `scrape_jsonapi_news.py` ⭐ RECOMMENDED

**Fast JSON API scraper** - fetches news content directly from the Drupal JSON API.
Much faster than HTML scraping (~50 items/second vs ~6 items/minute).

```bash
# Scrape all items under /news/press-releases/ URL (recommended)
python scripts/scrape_jsonapi_news.py --path-filter /news/press-releases/ --limit 100

# Scrape by Drupal category (may miss items with different categorization)
python scripts/scrape_jsonapi_news.py --category press-releases --limit 100

# Scrape items since a specific date
python scripts/scrape_jsonapi_news.py --path-filter /news/press-releases/ --since 2026-01-01

# Dry run - see what would be scraped
python scripts/scrape_jsonapi_news.py --path-filter /news/press-releases/ --limit 50 --dry-run
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--path-filter` | none | Filter by URL path (e.g., `/news/press-releases/`) |
| `--category` | none | Filter by Drupal category |
| `--limit` | 100 | Maximum items to fetch |
| `--since` | none | Only fetch items since date (YYYY-MM-DD) |
| `--output-category` | auto | Override output folder |
| `--dry-run` | false | Show items without saving |

**Categories:** `press-releases`, `featured-stories`, `statements-remarks`, `readouts`, `testimonies`, `all`

**Output:** Markdown files in `content/news/<category>/`

---

### `scrape_press_releases.py`

HTML scraper for press releases with progress tracking. Slower but works as fallback.

```bash
# Scrape 20 pages of press releases
python scripts/scrape_press_releases.py --pages 20

# Scrape featured stories instead
python scripts/scrape_press_releases.py --pages 10 --category featured-stories
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--pages` | 10 | Number of listing pages to scrape |
| `--category` | press-releases | Category: `press-releases` or `featured-stories` |

**Output:** Markdown files in `content/news/<category>/`

---

### `scrape_parallel.py`

Fast parallel scraper using multiple workers.

```bash
# Scrape with 5 parallel workers
python scripts/scrape_parallel.py --workers 5 --pages 100

# Scrape all categories
python scripts/scrape_parallel.py --workers 10 --pages 50 --category all
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--workers` | 5 | Number of parallel workers |
| `--pages` | 10 | Max pages per category |
| `--category` | all | Category or `all` for everything |

**Use when:** You need to scrape large amounts of content quickly.

---

### `scrape_treasury.py`

Full-featured async scraper with URL discovery.

```bash
# Discover all URLs from sitemap
python scripts/scrape_treasury.py --discover

# Scrape discovered URLs
python scripts/scrape_treasury.py --scrape

# Do both
python scripts/scrape_treasury.py --all
```

**Features:**
- Sitemap parsing for URL discovery
- Async HTTP requests for speed
- HTML to Markdown conversion
- Asset downloading (images, PDFs)
- Content type detection based on URL patterns

**Output:**
- Content: `content/` directory
- Assets: `static/` directory
- Cache: `.cache/` directory

---

## Typical Workflows

### Validate all navigation links

```bash
python scripts/test_links.py
```

### Fix broken URLs

1. Run link test to identify broken URLs:
   ```bash
   python scripts/test_links.py > broken_links.txt
   ```

2. Find correct URLs on live site:
   ```bash
   python scripts/fetch_live_links.py
   ```

3. Add corrections to `apply_corrections.py`

4. Apply fixes:
   ```bash
   python scripts/apply_corrections.py
   ```

5. Re-test:
   ```bash
   python scripts/test_links.py
   ```

### Scrape new press releases

```bash
# Scrape latest 5 pages (50 articles)
python scripts/scrape_press_releases.py --pages 5
```

### Full content refresh

```bash
# Parallel scrape all categories
python scripts/scrape_parallel.py --workers 10 --pages 200 --category all
```

---

## Output Locations

| Script | Output |
|--------|--------|
| `scrape_*.py` | `content/news/` |
| `scrape_treasury.py` | `content/`, `static/`, `.cache/` |
| `apply_corrections.py` | Modifies `data/navigation.json`, `themes/treasury/layouts/partials/footer.html` |

---

## Notes

- All scrapers respect rate limiting with built-in delays
- User-Agent headers mimic a browser to avoid blocking
- Some external government sites block automated testing but work in browsers
- Scraped content may need manual cleanup for formatting issues
