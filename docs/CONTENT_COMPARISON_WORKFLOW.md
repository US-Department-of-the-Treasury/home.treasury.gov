# Content Comparison & Fix Workflow

How we identify and fix content gaps between the Hugo rebuild and the live Treasury site.

## Quick Start (User Workflow)

1. **Receive the comparison JSON** — you get a `text_comparison-N.json` file from the crawl/diff pipeline
2. **Open Claude Code** in the `home.treasury.gov` repo
3. **Give Claude the JSON path** — e.g. "I have a list of issues at `~/Downloads/text_comparison-3.json`"
4. **Claude analyzes the report** — identifies empty pages, content diffs, and missing pages
5. **Tell Claude to fix a batch** — e.g. "fix the first 20 empty content pages"
6. **Claude runs `fix_empty_content.py`** — fetches content from the live site (HTML or JSON API), updates Hugo markdown files with correct dates and body content
7. **Review and PR** — Claude creates a branch, commits the fixes, and opens a PR for review
8. **Repeat** with `--offset` for the next batch until all issues are resolved

The script pulls content from `home.treasury.gov` using either:
- **HTML scraping** — fetches the page and extracts body from Drupal field classes
- **JSON API** (`/jsonapi/node/news`, etc.) — structured data when available

## Overview

We receive a JSON comparison report that diffs the text content of pages on the live site (`home.treasury.gov`) against their Hugo equivalents. Pages fall into one of these statuses:

| Status | Meaning |
|--------|---------|
| `identical` | Content matches exactly |
| `similar` | Minor differences (formatting, whitespace) |
| `different` | Content differs — may be empty, partial, or wrong |
| `missing_in_target` | Page exists on live site but not in Hugo |
| `missing_in_source` | Page exists in Hugo but not on live site |

## The Comparison JSON

File: typically named `text_comparison-N.json` (received from the crawl/diff pipeline).

### Structure

```json
{
  "source_dir": "report/crawl_source",
  "target_dir": "report/crawl_target",
  "timestamp": "2026-01-22T15:45:58.192775",
  "total_urls": 36943,
  "identical": 7748,
  "similar": 7108,
  "different": 3207,
  "missing_in_target": 17899,
  "missing_in_source": 981,
  "comparisons": [...]
}
```

### Comparison Entry

Each entry in `comparisons` has:

```json
{
  "url": "/news/press-releases/sm549",
  "source_path": "...",
  "target_path": "...",
  "similarity": 0.0,
  "source_word_count": 478,
  "target_word_count": 0,
  "missing_in_target": [],
  "added_in_target": [],
  "status": "different",
  "diff_snippet": "Length mismatch: source=3150, target=0"
}
```

Key fields:
- `url` — the page path on home.treasury.gov
- `source_word_count` — word count on live site
- `target_word_count` — word count in Hugo build
- `similarity` — 0.0 to 1.0 (0 = completely different, 1 = identical)
- `status` — one of: `identical`, `similar`, `different`, `missing_target`, `missing_source`

## Analyzing the Report

Use Python to inspect the report:

```bash
python3 -c "
import json
with open('path/to/text_comparison-3.json') as f:
    data = json.load(f)

print(f'Total: {data[\"total_urls\"]}')
print(f'Identical: {data[\"identical\"]}')
print(f'Similar: {data[\"similar\"]}')
print(f'Different: {data[\"different\"]}')
print(f'Missing in target: {data[\"missing_in_target\"]}')
print(f'Missing in source: {data[\"missing_in_source\"]}')

# Find empty-content pages (have Hugo file but no body)
empty = [c for c in data['comparisons']
         if c['status'] == 'different' and c['target_word_count'] == 0]
print(f'Empty-content pages: {len(empty)}')
"
```

## Fixing Empty-Content Pages

These are pages where the Hugo file exists (with front matter) but has no body content.

### Script: `scripts/fix_empty_content.py`

Fetches actual content from the live Treasury site and updates Hugo markdown files.

### How It Works

1. Reads the comparison JSON and filters to `status=different` + `target_word_count=0`
2. For each page, finds the corresponding Hugo markdown file
3. Fetches the live page HTML from `home.treasury.gov`
4. Extracts:
   - **Date** from the `og:updated_time` meta tag
   - **Body** from `field--name-field-page-body` or `field--name-field-news-body` HTML classes
5. Converts body HTML to markdown
6. Updates the Hugo file with correct date and body content
7. Moves file to correct folder/filename if needed (fixes wrong dates in filenames)

### Usage

```bash
# Dry run — see what would change without writing anything
python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json --limit 20 --dry-run

# Fix first 20 pages
python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json --limit 20

# Fix next batch (pages 21-50)
python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json --offset 20 --limit 30

# Fix all empty-content pages
python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json

# Slower request rate (if getting rate-limited)
python scripts/fix_empty_content.py --input ~/Downloads/text_comparison-3.json --limit 50 --delay 1.0
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | `text_comparison-2.json` | Path to the comparison JSON file |
| `--limit` | 0 (all) | Maximum pages to process |
| `--offset` | 0 | Skip this many entries from the start |
| `--dry-run` | false | Show what would change without writing |
| `--delay` | 0.5 | Seconds between requests (rate limiting) |
| `--verbose` | false | Show detailed output |

### Output

- Updated markdown files in `content/`
- Log file: `fix_empty_content_log.json` with per-page results

## Alternative: JSON API

The live site exposes a Drupal JSON API at `https://home.treasury.gov/jsonapi`. This is faster for structured content but has limitations:

- **Works well:** Unfiltered queries, title-based filters, category filters
- **Slow/times out:** Path alias filters (`filter[path.alias]=...`)

### Content types available via JSON API

| Content Type | API Endpoint | Used For |
|---|---|---|
| `node--news` | `/jsonapi/node/news` | Press releases, media advisories, featured stories |
| `node--schedule_public` | `/jsonapi/node/schedule_public` | Weekly public schedules |
| `node--page` | `/jsonapi/node/page` | General pages |
| `node--custom_page` | `/jsonapi/node/custom_page` | Custom layout pages |

### Example: Fetch news by category

```bash
curl -s -H "Accept: application/vnd.api+json" \
  "https://home.treasury.gov/jsonapi/node/news?filter[field_news_news_category.id]=cf77c794-0050-49b5-88cd-4b9382644cdf&page[limit]=5&sort=-field_news_publication_date"
```

See `scripts/scrape_jsonapi_news.py` for the full JSON API scraper.

## Workflow: Processing a New Comparison Report

1. **Receive** a new `text_comparison-N.json` file

2. **Analyze** the report to understand scope:
   ```bash
   python3 -c "import json; d=json.load(open('file.json')); print(d['different'], 'different pages')"
   ```

3. **Dry-run** on a small batch to verify the fix script works:
   ```bash
   python scripts/fix_empty_content.py --input file.json --limit 20 --dry-run
   ```

4. **Run** on the batch:
   ```bash
   python scripts/fix_empty_content.py --input file.json --limit 20
   ```

5. **Build locally** to verify pages render:
   ```bash
   hugo --config hugo.toml
   # Check: public/news/press-releases/sm549/index.html
   ```
   Note: `hugo.dev.toml` ignores pre-2025 content — use `hugo.toml` for full builds.

6. **Create branch and PR**:
   ```bash
   git checkout -b feature/fix-empty-content-batch-N staging
   git add content/ scripts/
   git commit -m "fix: populate N empty-content pages with live Treasury content"
   git push -u origin feature/fix-empty-content-batch-N
   gh pr create --base staging
   ```

7. **Continue** with next batch using `--offset`:
   ```bash
   python scripts/fix_empty_content.py --input file.json --offset 20 --limit 50
   ```

## Known Issues

- **YAML quoting:** Titles with `*`, `#`, `:`, or other YAML-special characters must be quoted. The script handles this automatically.
- **Date accuracy:** The `og:updated_time` meta tag sometimes reflects the last edit date rather than original publication date. For news items, the JSON API's `field_news_publication_date` is more accurate when available.
- **Rate limiting:** The live site may slow responses if requests are too frequent. Use `--delay 1.0` or higher if you see timeouts.
- **Missing body fields:** Some page types use different field names. If the script reports "No body field found", the page may need a new selector added to `fetch_page_content()`.
