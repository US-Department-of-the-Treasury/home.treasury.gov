# U.S. Department of the Treasury - Hugo Site

[![License: Public Domain](https://img.shields.io/badge/License-Public%20Domain-brightgreen.svg)](LICENSE)
[![Hugo](https://img.shields.io/badge/Hugo-0.120%2B-ff4088)](https://gohugo.io/)

Static site rebuild of [home.treasury.gov](https://home.treasury.gov) using [Hugo](https://gohugo.io/). Designed to run alongside the existing Drupal site via Akamai path-based routing.

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd home.treasury.gov
pip install -r requirements.txt

# Start development server
make serve
# or: hugo server -D --port 1313

# View at http://localhost:1313/news/press-releases/
```

## Documentation

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute to this project |
| [CHANGELOG.md](CHANGELOG.md) | Version history and changes |
| [docs/AKAMAI_INTEGRATION.md](docs/AKAMAI_INTEGRATION.md) | Akamai CDN configuration guide |
| [deploy/README.md](deploy/README.md) | Deployment scripts documentation |
| [scripts/README.md](scripts/README.md) | Python utilities documentation |
| [themes/treasury/README.md](themes/treasury/README.md) | Theme documentation |

---

## Current Status

| Content Type | Count | Status |
|--------------|-------|--------|
| Press Releases | 20 | ✅ Live-ready |
| Featured Stories | 0 | Redirects to Drupal |
| Other Sections | 0 | Redirects to Drupal |

**Hugo-served paths:**
- `/news/press-releases/` — List page
- `/news/press-releases/?page=1` — Pagination
- `/news/press-releases/sb0337/` through `/sb0357/` — Individual articles

**All other paths redirect to the live Treasury site.**

---

## Architecture

```
home.treasury.gov
        │
        ▼
    [Akamai CDN]
        │
        ├── /news/press-releases/*  →  Hugo (S3)
        ├── /css/*                  →  Hugo (S3)
        ├── /js/*                   →  Hugo (S3)
        ├── /images/*               →  Hugo (S3)
        │
        └── Everything else         →  Drupal (Legacy)
```

See [docs/AKAMAI_INTEGRATION.md](docs/AKAMAI_INTEGRATION.md) for complete routing configuration.

---

## Project Structure

```
home.treasury.gov/
├── archetypes/           # Content templates for hugo new
├── content/
│   └── news/
│       └── press-releases/  # 20 articles
├── data/
│   └── navigation.json   # Mega menu structure
├── deploy/               # S3 & Akamai scripts
├── docs/                 # Additional documentation
├── scripts/              # Python utilities
├── themes/treasury/      # Hugo theme (USWDS-based)
├── hugo.toml             # Site configuration
├── Makefile              # Common tasks
├── requirements.txt      # Python dependencies
├── CONTRIBUTING.md       # Contribution guidelines
├── CHANGELOG.md          # Version history
└── LICENSE               # Public Domain
```

---

## Common Tasks

```bash
make serve          # Start dev server (port 1313)
make build          # Build for production
make test           # Validate all navigation links
make deploy-staging # Deploy to staging S3
make deploy-prod    # Deploy to production + purge cache
make scrape         # Scrape latest press releases
make help           # Show all commands
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Hugo Extended](https://gohugo.io/installation/) | 0.120.0+ | Static site generator |
| [Python](https://www.python.org/) | 3.10+ | Scraping & validation scripts |
| [AWS CLI](https://aws.amazon.com/cli/) | 2.x | S3 deployment |
| [Akamai CLI](https://developer.akamai.com/cli) | Latest | Cache purging |

---

## Development

### Local Server

```bash
hugo server -D --port 1313
```

### Creating Content

```bash
# New press release
hugo new news/press-releases/2026-01-15-sb0358.md
```

### Testing

```bash
# Validate all navigation links
python scripts/test_links.py

# Check Hugo build
hugo --quiet
```

---

## Deployment

```bash
# 1. Build
hugo --minify

# 2. Deploy to staging
./deploy/s3-sync.sh staging

# 3. Deploy to production
./deploy/s3-sync.sh prod

# 4. Purge CDN cache
./deploy/akamai-purge.sh
```

See [deploy/README.md](deploy/README.md) for detailed instructions.

---

## Link Validation

53+ navigation URLs and 7+ footer URLs have been corrected. Run validation:

```bash
python scripts/test_links.py
```

| Metric | Before | After |
|--------|--------|-------|
| Working Links | 143 (63%) | 175 (87%) |
| Broken Links | 64 | 5 (external bot-blocked) |

See [scripts/README.md](scripts/README.md) for all available utilities.

---

## Theme

USWDS 3.x compliant theme with:
- Government banner
- Mega menu navigation
- Dark footer matching Treasury.gov
- Mobile-responsive design

See [themes/treasury/README.md](themes/treasury/README.md) for customization.

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

This project is in the **public domain** within the United States.

See [LICENSE](LICENSE) for details.
