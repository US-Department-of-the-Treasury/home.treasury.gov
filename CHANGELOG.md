# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Akamai integration documentation (`docs/AKAMAI_INTEGRATION.md`)
- Scripts README with usage documentation (`scripts/README.md`)
- CONTRIBUTING.md for contributor guidelines
- LICENSE file (Public Domain / CC0)
- CHANGELOG.md for version tracking

### Changed
- Footer redesigned with dark navy theme matching Treasury.gov
- Navigation links updated with 53+ URL corrections
- Pagination now uses `?page=X` format to match Drupal
- All "Home" links now point to live Treasury site
- Social media links updated (Twitter → X)

### Fixed
- 64 broken navigation URLs corrected
- 7 footer URLs updated to current destinations
- External links no longer open in new tabs
- 404 pages now redirect to live Treasury site

### Removed
- 94 incomplete press releases (scraped with missing content)
- 11 incomplete featured stories
- Unused partials (`pagination.html`, `latest-news.html`)
- Redundant scraping scripts (moved to `deprecated/`)
- Duplicate `static/favicon.ico`
- Root `content/_index.md` (handled by template)

## [0.1.0] - 2026-01-13

### Added
- Initial Hugo site structure
- Treasury theme based on USWDS
- Press releases section with 20 complete articles
- Navigation mega menu with search
- Footer with bureau links and social icons
- Breadcrumb navigation
- Alert banner component
- Python scraping scripts for content migration
- Deployment scripts for S3 and Akamai

---

## Version Format

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
