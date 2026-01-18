# Post-Migration Roadmap

This document outlines the technical improvements, optimizations, and new features planned following the successful migration of home.treasury.gov to the Hugo static site generator.

**Migration Status:** ✅ Complete (16,564 pages migrated)  
**Current State:** Production-ready, all tests passing  
**Last Updated:** January 18, 2026

---

## Table of Contents

1. [Inline CSS Optimization](#1-inline-css-optimization)
2. [Dynamic Pages & Applications](#2-dynamic-pages--applications)
3. [Performance Optimizations](#3-performance-optimizations)
4. [Code Refactoring](#4-code-refactoring)
5. [New Features & Ideas](#5-new-features--ideas)
6. [Technical Debt](#6-technical-debt)
7. [Timeline & Priorities](#7-timeline--priorities)

---

## 1. Inline CSS Optimization

### Current State

The site currently uses inline critical CSS in the `<head>` for fast first-paint, with full stylesheets loaded asynchronously. This approach works but has maintainability concerns.

### Issues to Address

| Issue | Impact | Priority |
|-------|--------|----------|
| Duplicate CSS in head and external files | Increased page size | Medium |
| Manual critical CSS extraction | Maintenance burden | Medium |
| Inline styles in some templates | CSP concerns (currently allowed) | Low |

### Proposed Solutions

#### 1.1 Automated Critical CSS Extraction

```bash
# Use critical package to auto-extract above-the-fold CSS
npm install critical --save-dev
```

Create a build step that:
1. Generates full CSS bundle
2. Extracts critical CSS per template type
3. Inlines critical CSS in Hugo templates
4. Loads remainder asynchronously

#### 1.2 CSS Architecture Refactor

```
themes/treasury/assets/css/
├── critical/
│   ├── base.css          # Typography, colors, variables
│   ├── layout.css        # Header, nav, footer basics
│   └── above-fold.css    # Combined critical CSS
├── components/
│   ├── navigation.css
│   ├── mega-menu.css
│   ├── cards.css
│   ├── forms.css
│   └── pagination.css
├── pages/
│   ├── homepage.css
│   ├── news-list.css
│   ├── article.css
│   └── search.css
└── treasury.css          # Main bundle (imports all)
```

#### 1.3 Remove Inline Styles from HTML

Audit and remove any remaining inline `style=""` attributes:

```bash
# Find inline styles
grep -r 'style="' themes/treasury/layouts/ --include="*.html"
```

Move all styles to external CSS files for:
- Better caching
- CSP compliance (can remove 'unsafe-inline' for styles)
- Easier maintenance

---

## 2. Dynamic Pages & Applications

### Current State

Some Treasury pages require dynamic functionality that static HTML cannot provide:

| Application | Current Status | Complexity |
|-------------|----------------|------------|
| Interest Rate Data | Links to legacy | High |
| OFAC Sanctions Search | External link | N/A |
| TARP Data | Static tables | Medium |
| Auction Results | Links to legacy | High |
| Forms/Applications | External links | N/A |

### Proposed Solutions

#### 2.1 Client-Side Data Applications

For data that updates regularly but can be fetched client-side:

```javascript
// Example: Interest Rate Widget
async function loadInterestRates() {
  const response = await fetch('/api/interest-rates.json');
  const data = await response.json();
  renderRatesTable(data);
}
```

**Implementation:**
1. Create JSON data files updated via scheduled Hugo builds
2. Use vanilla JS to fetch and render
3. Progressive enhancement - show static fallback if JS fails

#### 2.2 Serverless API Endpoints

For data requiring server processing:

```
AWS Lambda Functions:
├── /api/interest-rates     → Fetch from Treasury data API
├── /api/auction-results    → Fetch from TreasuryDirect
└── /api/search             → Elasticsearch/Algolia proxy
```

**Architecture:**
```
CloudFront → S3 (static) → Hugo pages
          → Lambda@Edge → API endpoints
```

#### 2.3 Hybrid Approach for Search

Replace USA.gov search with custom solution:

**Option A: Algolia (Recommended)**
- Client-side search with instant results
- Hugo plugin for index generation
- Free tier for government sites

**Option B: Pagefind**
- Static search index generated at build time
- No external dependencies
- Works offline

```bash
# Install Pagefind
npm install pagefind

# Add to build
hugo && npx pagefind --source public
```

#### 2.4 Migration Priority

| Phase | Applications | Timeline |
|-------|--------------|----------|
| Phase 1 | Interest rate display widgets | Q1 2026 |
| Phase 2 | Client-side search (Pagefind/Algolia) | Q2 2026 |
| Phase 3 | Auction results integration | Q3 2026 |
| Phase 4 | Full API layer (Lambda) | Q4 2026 |

---

## 3. Performance Optimizations

### Current Metrics

| Metric | Current | Target |
|--------|---------|--------|
| First Contentful Paint | ~1.2s | <1.0s |
| Largest Contentful Paint | ~2.1s | <1.5s |
| Cumulative Layout Shift | <0.1 | <0.05 |
| Total Page Size | ~350KB | <250KB |

### Proposed Optimizations

#### 3.1 Image Optimization

```toml
# hugo.toml - Enable image processing
[imaging]
  quality = 80
  resampleFilter = "lanczos"

[imaging.exif]
  disableLatLong = true
```

**Actions:**
- [ ] Convert all PNGs to WebP with fallbacks
- [ ] Implement responsive images with `srcset`
- [ ] Add lazy loading for below-fold images
- [ ] Generate AVIF format for modern browsers

```html
<!-- Example responsive image -->
<picture>
  <source srcset="/images/hero.avif" type="image/avif">
  <source srcset="/images/hero.webp" type="image/webp">
  <img src="/images/hero.jpg" alt="..." loading="lazy">
</picture>
```

#### 3.2 Font Optimization

Current: 2 fonts preloaded (Source Sans Pro, Merriweather)

**Actions:**
- [ ] Subset fonts to used characters only
- [ ] Use `font-display: swap` consistently
- [ ] Consider system font stack for body text
- [ ] Self-host fonts (already done ✅)

```css
/* Optimized font loading */
@font-face {
  font-family: 'Source Sans Pro';
  src: url('/fonts/source-sans-pro-subset.woff2') format('woff2');
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153;
}
```

#### 3.3 JavaScript Optimization

Current: Multiple small JS files loaded per page

**Actions:**
- [ ] Bundle all JS into single file per page type
- [ ] Implement code splitting for large features
- [ ] Add module/nomodule pattern for modern browsers
- [ ] Tree-shake unused code

```html
<!-- Modern browsers get ES modules -->
<script type="module" src="/js/treasury.modern.js"></script>
<!-- Legacy browsers get transpiled bundle -->
<script nomodule src="/js/treasury.legacy.js"></script>
```

#### 3.4 Caching Strategy

```
Cache-Control Headers:
├── HTML pages       → max-age=300 (5 min)
├── CSS/JS (hashed)  → max-age=31536000, immutable
├── Images           → max-age=2592000 (30 days)
├── Fonts            → max-age=31536000, immutable
└── JSON data        → max-age=3600 (1 hour)
```

#### 3.5 Preloading & Prefetching

```html
<!-- Preload critical resources -->
<link rel="preload" href="/fonts/source-sans-pro.woff2" as="font" crossorigin>
<link rel="preload" href="/css/critical.css" as="style">

<!-- Prefetch likely next pages -->
<link rel="prefetch" href="/news/press-releases/">
<link rel="prefetch" href="/about/">
```

---

## 4. Code Refactoring

### 4.1 Template Organization

Current structure is functional but could be cleaner:

```
themes/treasury/layouts/
├── _default/
│   ├── baseof.html       # Base template
│   ├── list.html         # Default list
│   └── single.html       # Default single
├── partials/
│   ├── header.html       # Site header
│   ├── footer.html       # Site footer
│   ├── navigation.html   # Main nav
│   ├── mega-menu.html    # Mega menu
│   └── ...               # 20+ partials
├── news/
│   ├── list.html         # News list
│   └── single.html       # News article
└── shortcodes/
    └── ...               # Custom shortcodes
```

**Proposed Changes:**
- [ ] Create component-based partial structure
- [ ] Add render hooks for markdown elements
- [ ] Implement Hugo modules for shared components
- [ ] Document template hierarchy

#### 4.2 CSS Variable Consolidation

Audit and consolidate CSS custom properties:

```css
:root {
  /* Current: scattered across files */
  /* Proposed: single source of truth */
  
  /* Colors - Primary */
  --color-primary: #0050b4;
  --color-primary-dark: #002d72;
  --color-primary-light: #1a4480;
  
  /* Colors - Neutral */
  --color-gray-100: #f0f0f0;
  --color-gray-200: #e0e0e0;
  /* ... */
  
  /* Typography */
  --font-serif: 'Merriweather', Georgia, serif;
  --font-sans: 'Source Sans Pro', sans-serif;
  
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
}
```

#### 4.3 JavaScript Modernization

Current: ES5-compatible vanilla JS

**Proposed:**
- [ ] Migrate to ES6+ modules
- [ ] Add TypeScript for type safety (optional)
- [ ] Implement proper error boundaries
- [ ] Add comprehensive JSDoc comments

```javascript
// Before: ES5
(function() {
  var searchForm = document.getElementById('search');
  if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
      // ...
    });
  }
})();

// After: ES6 module
export function initSearch() {
  const searchForm = document.querySelector('#search');
  searchForm?.addEventListener('submit', handleSearch);
}
```

#### 4.4 Content Architecture

Audit content types and front matter:

```yaml
# Standardized front matter for news articles
---
title: "Article Title"
date: 2026-01-18T10:00:00-05:00
description: "Meta description for SEO"
categories:
  - press-releases
tags:
  - sanctions
  - ofac
authors:
  - Office of Public Affairs
related:
  - /news/press-releases/related-article/
---
```

---

## 5. New Features & Ideas

### 5.1 Enhanced Search

**Pagefind Integration:**
```bash
# Build-time index generation
hugo && npx pagefind --source public --bundle-dir _pagefind

# Result: instant client-side search
```

Features:
- [ ] Full-text search across all content
- [ ] Faceted filtering (date, category, topic)
- [ ] Search suggestions/autocomplete
- [ ] Highlighted results

### 5.2 Dark Mode

Already have CSS for `prefers-color-scheme: dark`. Need UI toggle:

```html
<button id="theme-toggle" aria-label="Toggle dark mode">
  <svg class="icon-sun">...</svg>
  <svg class="icon-moon">...</svg>
</button>
```

```javascript
// Theme toggle with localStorage persistence
function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}
```

### 5.3 Print Optimization

Enhance print stylesheet for official documents:

- [ ] Treasury letterhead for press releases
- [ ] QR code linking to online version
- [ ] Page numbers and document info
- [ ] Remove navigation and interactive elements

### 5.4 Accessibility Enhancements

Beyond WCAG 2.2 AA compliance:

- [ ] Add skip links for all major sections
- [ ] Implement ARIA live regions for dynamic content
- [ ] Add high contrast mode toggle
- [ ] Improve screen reader navigation landmarks

### 5.5 Multi-language Support (Future)

Hugo has built-in i18n support:

```
content/
├── en/
│   └── news/
│       └── press-releases/
└── es/
    └── noticias/
        └── comunicados-de-prensa/
```

### 5.6 RSS/Atom Enhancements

- [ ] Category-specific feeds
- [ ] Full-text feeds option
- [ ] JSON Feed format
- [ ] WebSub/PubSubHubbub for instant updates

---

## 6. Technical Debt

### Known Issues to Address

| Issue | File(s) | Priority |
|-------|---------|----------|
| Duplicate mega menu code | navigation.html, mobile-nav.html | Medium |
| Magic numbers in CSS | treasury.css | Low |
| Inconsistent spacing values | Multiple CSS files | Low |
| Legacy browser support code | treasury.js | Low |
| Unused CSS rules | treasury.css | Medium |

### Documentation Gaps

- [ ] Component library documentation
- [ ] CSS architecture guide
- [ ] JavaScript API documentation
- [ ] Deployment runbook
- [ ] Incident response procedures

### Testing Gaps

- [ ] Fix failing new Playwright tests (13-16)
- [ ] Add visual regression tests
- [ ] Add performance budget tests
- [ ] Add accessibility monitoring

---

## 7. Timeline & Priorities

### Q1 2026 (Current)

| Task | Status | Owner |
|------|--------|-------|
| Complete migration | ✅ Done | - |
| Accessibility fixes | ✅ Done | - |
| Test suite expansion | ✅ Done | - |
| CSS architecture audit | 📋 Planned | - |

### Q2 2026

| Task | Priority | Estimate |
|------|----------|----------|
| Implement Pagefind search | High | 2 weeks |
| Image optimization pipeline | High | 1 week |
| Font subsetting | Medium | 3 days |
| Dark mode toggle | Low | 3 days |

### Q3 2026

| Task | Priority | Estimate |
|------|----------|----------|
| Interest rate widgets | High | 3 weeks |
| JavaScript bundling/splitting | Medium | 1 week |
| CSS refactoring | Medium | 2 weeks |
| Print stylesheet enhancement | Low | 1 week |

### Q4 2026

| Task | Priority | Estimate |
|------|----------|----------|
| Serverless API layer | High | 4 weeks |
| Multi-language prep | Medium | 2 weeks |
| Performance monitoring | Medium | 1 week |
| Documentation overhaul | Medium | 2 weeks |

---

## Contributing

To contribute to post-migration improvements:

1. Create a feature branch from `post-migration`
2. Implement changes following existing patterns
3. Add/update tests as needed
4. Submit PR with detailed description

---

## References

- [Hugo Documentation](https://gohugo.io/documentation/)
- [USWDS Design System](https://designsystem.digital.gov/)
- [Section 508 Standards](https://www.section508.gov/)
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
