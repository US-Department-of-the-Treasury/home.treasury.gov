# Playwright Test Suite Documentation

Comprehensive end-to-end testing for the Treasury Hugo site using Playwright.

## Quick Start

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Run all tests
npm test

# Run tests against local Hugo server
npm run test:local

# Run tests against staging
npm run test:staging

# Run specific test file
npx playwright test tests/1-visual-layout.spec.ts

# Run tests in headed mode (see browser)
npx playwright test --headed

# Run tests with UI mode (interactive)
npx playwright test --ui
```

## Test Suite Index

| File | Category | Tests | Description |
|------|----------|-------|-------------|
| [1-visual-layout.spec.ts](#1-visual-layout) | Visual | 20 | Responsive design, broken images, JS errors |
| [2-navigation.spec.ts](#2-navigation) | Navigation | 13 | Skip links, menus, breadcrumbs |
| [3-keyboard-accessibility.spec.ts](#3-keyboard-accessibility) | Accessibility | 12 | Focus indicators, tab order, keyboard traps |
| [4-news-search.spec.ts](#4-news-search) | Functionality | 17 | Search, filters, pagination |
| [5-news-list.spec.ts](#5-news-list) | Functionality | 11 | News list pages, inline filters |
| [6-csp-compliance.spec.ts](#6-csp-compliance) | Security | 13 | CSP violations, inline scripts |
| [7-accessibility-axe.spec.ts](#7-accessibility-axe) | Accessibility | 14 | axe-core WCAG 2.2 AA scans |
| [8-performance.spec.ts](#8-performance) | Performance | 11 | Load times, CLS, caching |
| [9-link-validation.spec.ts](#9-link-validation) | Links | 24 | Mega menus, broken links, redirects |
| [10-section-layout.spec.ts](#10-section-layout) | Layout | 18 | Section pages, sidebars, breadcrumbs |
| [11-article-page.spec.ts](#11-article-page) | Content | 18 | Article pages, metadata sidebar |
| [12-rss-sitemap.spec.ts](#12-rss-sitemap) | SEO | 15 | RSS feeds, sitemap validation |
| [13-user-preferences.spec.ts](#13-user-preferences) | Accessibility | 16 | Dark mode, reduced motion, zoom |
| [14-form-validation.spec.ts](#14-form-validation) | Functionality | 18 | Form inputs, validation, errors |
| [15-meta-seo.spec.ts](#15-meta-seo) | SEO | 20 | Meta tags, OG tags, headings |
| [16-service-worker.spec.ts](#16-service-worker) | PWA | 16 | Service worker, caching, offline |

**Total: 16 test files, 250+ tests**

---

## Test Categories

### 1-visual-layout

**Purpose:** Verify visual layout and responsive design across devices.

**Tests:**
- Homepage loads without JavaScript errors
- No broken images on key pages
- Responsive at desktop (1200px), tablet (768px), mobile (375px)
- Footer displays correctly
- Main content area exists
- No horizontal scroll at mobile widths

**Run:** `npx playwright test tests/1-visual-layout.spec.ts`

---

### 2-navigation

**Purpose:** Test navigation functionality and accessibility.

**Tests:**
- Skip link is first focusable element
- Skip link navigates to main content
- Main navigation visible on desktop
- Navigation links are clickable
- Dropdown menus open on interaction
- Hamburger menu works on mobile
- Mobile menu opens and closes
- Internal links navigate correctly
- External links have `rel="noopener"`
- Breadcrumbs display correctly
- Header logo links to homepage
- Footer links are functional

**Run:** `npx playwright test tests/2-navigation.spec.ts`

---

### 3-keyboard-accessibility

**Purpose:** Ensure full keyboard accessibility compliance.

**Tests:**
- All focusable elements have visible focus indicators
- Focused links have visible outline
- Tab order is logical
- No keyboard traps exist
- Modal dialogs can be closed with Escape
- Buttons activatable with Enter and Space
- Links activatable with Enter
- Form fields are navigable with Tab
- Form labels are associated with inputs
- axe-core keyboard accessibility checks pass

**Run:** `npx playwright test tests/3-keyboard-accessibility.spec.ts`

---

### 4-news-search

**Purpose:** Test advanced search functionality.

**Tests:**
- Search form is present and visible
- Keyword search input exists
- Date filter controls exist
- Keyword search returns results
- Empty search shows message or all results
- Date preset filters work (Today, This Week, This Month)
- Document type dropdown works
- Office dropdown works
- Results count is displayed
- Results have accessible announcements (aria-live)
- Pagination controls exist and work
- Load More button works
- Reset button clears filters

**Run:** `npx playwright test tests/4-news-search.spec.ts`

---

### 5-news-list

**Purpose:** Test news list pages and inline filters.

**Tests:**
- Page displays list of press releases
- Each news item has date and title
- Inline date filters work (Today, This Week, This Month, This Year)
- Date range inputs exist
- Date range filter applies correctly
- Keyword search filters results
- Pagination is displayed
- Page number links work
- Jump to page form works
- All News page displays items from all categories

**Run:** `npx playwright test tests/5-news-list.spec.ts`

---

### 6-csp-compliance

**Purpose:** Verify Content Security Policy compliance.

**Tests:**
- No CSP violations on homepage, press releases, search, all news, 404
- No inline `onclick` handlers
- No inline event handlers on search page
- No inline script tags without `src`
- All scripts are from same origin
- All stylesheets are from same origin
- Form submit works without inline handler
- Buttons work without inline handlers
- JavaScript executes without CSP blocking

**Run:** `npx playwright test tests/6-csp-compliance.spec.ts`

---

### 7-accessibility-axe

**Purpose:** Run axe-core accessibility scans for WCAG 2.2 AA.

**Tests:**
- Homepage has no accessibility violations
- Proper heading hierarchy
- Images have alt text
- Press releases page passes axe scan
- List items use proper semantic markup
- Advanced search page passes axe scan
- Form controls have accessible labels
- Buttons have accessible names
- All News page passes axe scan
- 404 page passes axe scan
- Homepage meets color contrast requirements
- Page has proper landmark regions
- Links have discernible text
- No duplicate link text with different destinations

**Run:** `npx playwright test tests/7-accessibility-axe.spec.ts`

---

### 8-performance

**Purpose:** Test page load performance and stability.

**Tests:**
- Homepage loads within 3 seconds
- Press releases page loads within 3 seconds
- Search page loads within 3 seconds
- Homepage has no significant layout shift
- News list has stable layout during pagination
- Images have `loading` attribute for lazy loading
- Images have width and height to prevent layout shift
- Critical CSS is loaded
- JavaScript files load successfully
- Fonts load successfully
- Static assets have cache headers

**Run:** `npx playwright test tests/8-performance.spec.ts`

---

### 9-link-validation

**Purpose:** Validate all navigation links work correctly.

**Tests:**
- All About Treasury mega menu links are valid
- All Policy Issues mega menu links are valid
- All Data mega menu links are valid
- All Services mega menu links are valid
- All News mega menu links are valid
- All homepage internal links are valid
- Footer links are valid
- No unintentional redirects to old treasury.gov
- Critical navigation links return 200
- Comprehensive crawl of all links from navigation.json

**Run:** `npx playwright test tests/9-link-validation.spec.ts`

---

### 10-section-layout

**Purpose:** Test section and content page layouts.

**Tests:**
- Section pages have correct layout structure
- Content pages have correct layout structure
- About Treasury sidebar shows child sections
- Subsection has back link to parent
- Content page sidebar shows sibling pages
- Active page is highlighted in sidebar
- Breadcrumbs show correct hierarchy
- Section page shows content cards for child pages
- Content cards are links to child pages
- Layout is responsive at mobile and tablet widths
- Sidebar has proper aria-label
- Breadcrumbs have proper aria-label
- Current page in breadcrumbs has aria-current

**Run:** `npx playwright test tests/10-section-layout.spec.ts`

---

### 11-article-page

**Purpose:** Test individual article pages (press releases, statements).

**Tests:**
- Press release article has required elements
- Article has proper heading hierarchy
- Article content is readable
- Metadata sidebar is visible
- Metadata contains publication date
- Metadata tags are clickable
- Category tag links to search results
- Article has breadcrumb navigation
- Breadcrumbs show correct hierarchy
- Article has proper landmark structure
- Images in article have alt text
- Links in article are distinguishable
- Article is readable on mobile
- Article text is not too small on mobile
- Can navigate back to news list

**Run:** `npx playwright test tests/11-article-page.spec.ts`

---

### 12-rss-sitemap

**Purpose:** Validate RSS feeds and sitemap.

**Tests:**
- News RSS feed exists and returns XML
- RSS feed has valid structure
- RSS feed contains items with required elements
- RSS feed items have valid dates
- RSS feed has atom:link for self-reference
- Section-specific feeds exist
- sitemap.xml exists and returns XML
- Sitemap has valid XML structure
- Sitemap contains URLs
- Sitemap URLs are valid format
- Sitemap includes key pages
- Sitemap is reasonably sized
- Sitemap has reasonable URL count
- robots.txt exists and has valid format

**Run:** `npx playwright test tests/12-rss-sitemap.spec.ts`

---

### 13-user-preferences

**Purpose:** Test user preference media queries.

**Tests:**
- Respects `prefers-reduced-motion: reduce`
- Slider respects reduced motion
- Page transitions respect reduced motion
- Page loads with dark color scheme
- Text remains readable in dark mode
- Search page works in dark mode
- Page loads with high contrast preference
- Focus indicators visible in high contrast
- Buttons remain distinguishable in high contrast
- Page is usable at 200% zoom
- Text can be resized with browser settings
- Content reflows at narrow widths
- Line height allows text scaling
- Page has print-specific styles
- Article content is visible in print

**Run:** `npx playwright test tests/13-user-preferences.spec.ts`

---

### 14-form-validation

**Purpose:** Test form inputs and validation.

**Tests:**
- Search form accepts valid input
- Search form handles empty submission
- Search form handles special characters
- Search form handles very long input
- Date inputs accept valid dates
- Date range filter applies correctly
- Invalid date range shows appropriate feedback
- Dropdown filters are keyboard accessible
- Selecting multiple filters works
- Form inputs have visible labels
- Error messages are associated with inputs
- Required fields are indicated
- Reset button clears all inputs
- Clearing filters removes active filter tags
- Jump to page input works
- Invalid page number is handled
- Header search toggle works
- Header search redirects to search page

**Run:** `npx playwright test tests/14-form-validation.spec.ts`

---

### 15-meta-seo

**Purpose:** Validate meta tags and SEO elements.

**Tests:**
- Homepage has required meta tags (title, description, viewport)
- Press releases page has appropriate meta tags
- Article pages have unique meta tags
- All pages have canonical URL
- Homepage has Open Graph tags
- Article pages have article OG type
- OG image is specified (if implemented)
- Twitter card tags exist (if implemented)
- Pages have structured data (if implemented)
- Pages have lang attribute
- Pages do not have noindex in production
- 404 page has noindex
- Favicon is present and accessible
- Homepage has exactly one h1
- Heading levels do not skip
- External links have rel="noopener"
- Skip link points to valid target

**Run:** `npx playwright test tests/15-meta-seo.spec.ts`

---

### 16-service-worker

**Purpose:** Test PWA and offline capabilities.

**Tests:**
- Service worker file exists
- Service worker is registered on homepage
- Service worker has valid scope
- Homepage can be cached
- Static assets are cacheable
- Service worker defines cache version
- Service worker handles fetch events
- Service worker has install and activate events
- manifest.json exists (if PWA implemented)
- Manifest is linked in HTML
- Offline page exists (if implemented)
- Page degrades gracefully without JavaScript
- Critical CSS is inlined
- Fonts have fallback
- Critical resources are preloaded
- DNS prefetch for external resources

**Run:** `npx playwright test tests/16-service-worker.spec.ts`

---

## Configuration

### playwright.config.ts

```typescript
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:1313',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox-desktop', use: { ...devices['Desktop Firefox'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 14'] } },
  ],
});
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:1313` | Target URL for tests |
| `CI` | - | Set in CI environments for stricter settings |

---

## Test Fixtures (fixtures.ts)

Common test utilities and page URLs:

```typescript
// Test page URLs
export const TEST_PAGES = {
  home: '/',
  pressReleases: '/news/press-releases/',
  advancedSearch: '/news/search/',
  allNews: '/news/all/',
  notFound: '/this-page-definitely-does-not-exist/',
};

// Viewport sizes
export const VIEWPORTS = {
  mobile: { width: 375, height: 667 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 800 },
};

// Utility functions
export async function waitForPageReady(page);
export function collectConsoleErrors(page);
export function collectCSPViolations(page);
export async function getFocusableElements(page);
export async function hasVisibleFocusIndicator(element);
export async function tabThroughPage(page, maxTabs);
export async function findBrokenImages(page);
export async function hasHorizontalScroll(page);
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Playwright Tests

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start Hugo server
        run: hugo server &
      - name: Run tests
        run: npm test
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Writing New Tests

### Test Template

```typescript
import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('Feature Name - Category', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);
  });

  test('descriptive test name', async ({ page }) => {
    // Arrange
    const element = page.locator('.my-element');
    
    // Act
    await element.click();
    
    // Assert
    await expect(element).toBeVisible();
  });
});
```

### Best Practices

1. **Use descriptive test names** that explain what is being tested
2. **Use `waitForPageReady()`** after navigation for stability
3. **Use locators** instead of raw selectors
4. **Group related tests** in `test.describe` blocks
5. **Use `test.beforeEach`** for common setup
6. **Log useful information** with `console.log()` for debugging
7. **Handle optional features** gracefully (check if element exists)
8. **Avoid hard-coded waits** - use `waitForPageReady` or `expect` with auto-retry

---

## Troubleshooting

### Common Issues

**Tests timeout:**
- Increase timeout in test: `test.setTimeout(60000)`
- Check if Hugo server is running
- Check BASE_URL is correct

**Element not found:**
- Use more specific locators
- Check if element is inside iframe
- Check if element is hidden on current viewport

**CSP errors:**
- Check for inline scripts in templates
- Check for external resources from different origins

**Flaky tests:**
- Use `waitForPageReady()` after navigation
- Use `expect` with auto-retry instead of raw assertions
- Increase retries for CI

### Debug Mode

```bash
# Run with headed browser
npx playwright test --headed

# Run with slow motion
npx playwright test --headed --slowMo=500

# Debug specific test
npx playwright test --debug tests/1-visual-layout.spec.ts

# Generate trace on failure
npx playwright test --trace on
```
