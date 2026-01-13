# U.S. Department of the Treasury - Hugo Site

Static site build of [home.treasury.gov](https://home.treasury.gov) using [Hugo](https://gohugo.io/).

## Prerequisites

- [Hugo Extended](https://gohugo.io/installation/) v0.120.0 or later
- [Python 3.10+](https://www.python.org/) (for content scraping)
- [AWS CLI](https://aws.amazon.com/cli/) (for deployment)
- [Akamai CLI](https://developer.akamai.com/cli) (for cache purging)

## Quick Start

```bash
# Install Python dependencies for scraper
pip install -r requirements.txt

# Run Hugo development server
hugo server -D

# Build for production
hugo --minify
```

## Project Structure

```
.
├── archetypes/          # Content templates
├── content/             # Markdown content (scraped + authored)
├── data/                # Data files (JSON/YAML)
├── deploy/              # Deployment scripts
├── layouts/             # Custom layouts (overrides theme)
├── scripts/             # Utility scripts
│   └── scrape_treasury.py
├── static/              # Static assets (images, CSS, JS)
├── themes/
│   └── treasury/        # USWDS-based theme
├── hugo.toml            # Hugo configuration
└── requirements.txt     # Python dependencies
```

## Content Migration

### Scraping from Live Site

The scraper pulls content directly from home.treasury.gov:

```bash
# Discover all URLs (sitemap + crawling)
python scripts/scrape_treasury.py --discover

# Scrape discovered pages to Markdown
python scripts/scrape_treasury.py --scrape

# Download images and documents
python scripts/scrape_treasury.py --assets

# Run full pipeline
python scripts/scrape_treasury.py --all
```

Scraped content is saved to `content/` with YAML front matter.

### Manual Content

Create new content using archetypes:

```bash
# New page
hugo new about/new-page.md

# New press release
hugo new news/press-releases/2026-01-13-title.md
```

## Development

```bash
# Start dev server with drafts
hugo server -D

# Start with live reload and verbose output
hugo server -D --navigateToChanged --verbose
```

## Deployment

### AWS S3 + Akamai

1. Configure AWS credentials
2. Update bucket names in `deploy/s3-sync.sh`
3. Deploy:

```bash
# Deploy to staging
./deploy/s3-sync.sh staging

# Deploy to production
./deploy/s3-sync.sh prod

# Purge Akamai cache
./deploy/akamai-purge.sh
```

### S3 Bucket Configuration

The S3 bucket should be configured for static website hosting:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

Enable static website hosting with:
- Index document: `index.html`
- Error document: `404.html`

## Theme

The `treasury` theme is built on the [U.S. Web Design System (USWDS)](https://designsystem.digital.gov/) v3.x.

### USWDS Assets

Download USWDS assets and place in `themes/treasury/static/`:

```bash
# From npm
npm install @uswds/uswds
cp -r node_modules/@uswds/uswds/dist/css/uswds.min.css themes/treasury/static/css/
cp -r node_modules/@uswds/uswds/dist/js/uswds.min.js themes/treasury/static/js/
cp -r node_modules/@uswds/uswds/dist/img/* themes/treasury/static/images/
```

## Configuration

See `hugo.toml` for site configuration options:

- `baseURL`: Production URL
- `params.description`: Site description
- `menus`: Navigation structure
- `taxonomies`: Content categorization

## License

Public Domain - See [LICENSE](LICENSE)
