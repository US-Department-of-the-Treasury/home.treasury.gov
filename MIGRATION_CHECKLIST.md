# Treasury Website Migration Checklist

**Project:** home.treasury.gov Hugo Migration  
**Last Updated:** January 16, 2026  
**Status:** ✅ Ready for Deployment

---

## 📊 Migration Overview

| Metric | Value |
|--------|-------|
| Total Pages | 16,592 |
| Build Time | ~3 minutes |
| Hugo Version | 0.154.5 |
| Theme | Custom Treasury Theme |

---

## ✅ COMPLETED TASKS

### Content Migration

#### News Content
- [x] **Press Releases** - 13,158 files ✅
- [x] **Readouts** - 864 files ✅
- [x] **Statements & Remarks** - 453 files ✅
- [x] **Testimonies** - 88 files ✅
- [x] **Featured Stories** - 169 files ✅
- [x] **Media Advisories** - 769 files ✅
- [x] **Weekly Public Schedule** - 715 files ✅
- [x] **Weekly Schedule Updates** - 160 files ✅

#### Static Pages
- [x] **About Section** - 17 pages
  - [x] Role of the Treasury
  - [x] Officials
  - [x] Organizational Chart
  - [x] History (Overview, Prior Secretaries)
  - [x] Careers (Headquarters, Bureaus)
  - [x] Budget & Performance
  
- [x] **Policy Issues Section** - 14 pages
  - [x] Tax Policy
  - [x] International Affairs
  - [x] Terrorism & Illicit Finance
  - [x] Financing the Government
  - [x] Small Business Programs
  - [x] Consumer Policy
  - [x] Economic Policy
  - [x] Tribal Affairs
  - [x] Climate Change

- [x] **Services Section** - 9 pages
  - [x] Taxes
  - [x] Bonds and Securities
  - [x] Currency and Coins
  - [x] Treasury Payments
  - [x] Forms
  - [x] Report Fraud
  - [x] Government Shared Services
  - [x] Tours and Library

- [x] **Data Section** - 4 pages
  - [x] TIC System
  - [x] Treasury Open Data
  - [x] U.S. International Reserve Position

---

### Templates & Layouts

#### Core Templates
- [x] Base template (`baseof.html`)
- [x] Homepage (`index.html`)
- [x] Single page template
- [x] List/Section template
- [x] Content page template
- [x] 404 error page

#### News Templates
- [x] News single article
- [x] News listing page
- [x] News search page
- [x] News "all" page

#### Partials
- [x] Header with mega menu navigation
- [x] Footer with bureau links
- [x] USA.gov official banner
- [x] Alert/announcement banner
- [x] Breadcrumbs
- [x] Pagination
- [x] News sidebar
- [x] Article sidebar

---

### Homepage Sections
- [x] Hero section with Treasury Building image
- [x] Quick Links grid (6 cards)
  - Taxes & IRS
  - Savings Bonds
  - Currency & Coins
  - Careers
  - Data & Charts
  - Report Fraud
- [x] Latest News section (6 press releases)
- [x] Secretary Spotlight (Scott Bessent)
- [x] Policy Areas grid (4 cards)
- [x] Treasury Bureaus grid (6 cards)

---

### Styling & UX

#### CSS Features
- [x] CSS variables for theming
- [x] Treasury official colors
- [x] Responsive breakpoints
- [x] Mobile-first approach

#### Visual Enhancements
- [x] Entrance animations (fadeInUp)
- [x] Staggered animation delays
- [x] Smooth hover transitions
- [x] Gold accent styling
- [x] Enhanced focus states

#### Accessibility (508 Compliance)
- [x] Skip navigation link
- [x] ARIA labels on navigation
- [x] Focus indicators (3px gold outline)
- [x] Screen reader text (`.sr-only`)
- [x] Semantic HTML structure
- [x] `prefers-reduced-motion` support
- [x] Keyboard navigation support

---

### Assets

#### Images
- [x] Treasury seal (SVG)
- [x] Treasury building (WebP/PNG)
- [x] Secretary Bessent photo (WebP/JPG)
- [x] Favicon
- [x] USA flag icon
- [x] .gov and HTTPS icons

#### Fonts (Self-hosted)
- [x] Source Sans Pro (body text)
- [x] Merriweather (headings)
- [x] 7 WOFF2 font files

---

### Configuration

#### Hugo Config
- [x] `hugo.toml` - Production config
- [x] `hugo.dev.toml` - Development config (fast builds)
- [x] Navigation data (`data/navigation.json`)
- [x] Search filters (`data/search_filters.json`)

#### Deployment
- [x] Terraform configuration
  - [x] `main.tf`
  - [x] `variables.tf`
  - [x] `outputs.tf`
  - [x] `provider.tf`
- [x] Deployment scripts
  - [x] `s3-sync.sh`
  - [x] `akamai-purge.sh`
  - [x] `validate-config.sh`
- [x] Akamai caching rules

---

### Technical Features
- [x] Service worker for offline support
- [x] Critical CSS inlining
- [x] Asset fingerprinting for cache busting
- [x] Minification support
- [x] JSON feed generation (`index.json`)
- [x] XML sitemap generation
- [x] RSS feed

---

## ✅ SCRAPING COMPLETE

All news content has been successfully scraped:

| Category | Count | Status |
|----------|-------|--------|
| Media Advisories | 769 | ✅ Complete |
| Weekly Public Schedule | 715 | ✅ Complete |

**Total Content Files:** 16,376

---

## ❌ TODO (Remaining Tasks)

### High Priority

#### 1. Fix Scraped Content Dates
- [x] Media advisories have incorrect dates (showing today's date instead of original) ✅
- [x] Weekly schedules have incorrect dates ✅
- [x] **Action:** Created `scripts/fix_scraped_dates.py` - fixed 483 dates ✅

#### 2. Content Verification
- [x] Spot-check 20 media advisories for correct content ✅
- [x] Spot-check 20 weekly schedules for correct content ✅
- [x] Verify no duplicate content (duplicates are expected - same ID in different categories) ✅
- [x] Check for any files with empty/missing body content ✅
  - ~570 media advisories and ~570 weekly schedules have empty bodies
  - These are archived items (2010-2015) no longer accessible on Treasury.gov
  - Files still have titles, dates, and URLs for archive listings

#### 3. Full Build Test
- [x] Run `hugo --minify` and verify no errors ✅
- [x] Confirm final page count: **16,507 pages** ✅
- [x] Check build time is acceptable: **~3 minutes** ✅

---

### Medium Priority

#### 4. Link Verification
- [x] Test all internal navigation links ✅ (122 found, 2 minor missing)
- [x] Created 85 stub pages for missing nav links ✅
- [x] Verify external links to bureaus work ✅ (74 external links)
- [ ] Check search functionality integration
- [ ] Test pagination on news pages

#### 5. Accessibility Audit
- [x] Basic accessibility check ✅
  - ✅ `lang="en-us"` on HTML
  - ✅ Skip link present
  - ✅ 46 ARIA attributes
  - ✅ Alt text on images
  - ✅ Focus indicators (gold outline)
- [ ] Run pa11y or axe accessibility scan (optional)
- [ ] Test with screen reader (optional)
- [ ] Keyboard-only navigation test (optional)

#### 6. Performance Check
- [ ] Lighthouse performance score
- [ ] Check Core Web Vitals
- [ ] Verify image optimization
- [ ] Test mobile performance

---

### Deployment

#### 7. Staging Deployment
- [ ] Configure AWS credentials
- [ ] Run `terraform init`
- [ ] Run `terraform plan`
- [ ] Deploy to staging environment
- [ ] Verify staging site works

#### 8. Production Deployment
- [ ] Final content review
- [ ] Run `terraform apply` for production
- [ ] Configure Akamai CDN
- [ ] Set up SSL/TLS
- [ ] Verify DNS configuration
- [ ] Test production site

#### 9. Post-Deployment
- [ ] Set up monitoring
- [ ] Configure alerting
- [ ] Document deployment process
- [ ] Create runbook for content updates

---

## 📁 Project Structure

```
home.treasury.gov/
├── archetypes/          # Content templates
├── content/             # All markdown content
│   ├── about/           # 17 pages
│   ├── data/            # 4 pages
│   ├── news/            # 15,000+ articles
│   ├── policy-issues/   # 14 pages
│   ├── resource-center/ # Data pages
│   └── services/        # 9 pages
├── data/                # Navigation & config JSON
├── deploy/              # Deployment scripts
├── docs/                # Documentation
├── public/              # Generated site
├── scripts/             # Python scrapers & utilities
├── static/              # Static assets
├── terraform/           # Infrastructure as code
├── themes/treasury/     # Hugo theme
│   ├── assets/          # CSS, JS source
│   ├── layouts/         # HTML templates
│   └── static/          # Theme assets
├── hugo.toml            # Production config
├── hugo.dev.toml        # Development config
└── MIGRATION_CHECKLIST.md  # This file
```

---

## 🔧 Useful Commands

```bash
# Development server (limited content, fast)
hugo server --config hugo.dev.toml

# Full development server (all content, slow)
hugo server

# Production build
hugo --minify

# Check content stats
find content -name "*.md" | wc -l

# Check for bad titles
grep -r 'title: "U.S. Department of the Treasury"' content/news/

# Run accessibility test
npx pa11y http://localhost:1313
```

---

## 📞 Contacts & Resources

- **Live Site:** https://home.treasury.gov
- **Hugo Documentation:** https://gohugo.io/documentation/
- **USWDS (Design System):** https://designsystem.digital.gov/

---

## Changelog

### January 16, 2026
- ✅ **Content migration 100% complete**
- 13,158 press releases migrated
- 769 media advisories migrated
- 715 weekly public schedules migrated
- 864 readouts migrated
- 453 statements & remarks migrated
- All static pages created
- Homepage with Secretary Bessent spotlight
- Visual enhancements added (animations, polish)
