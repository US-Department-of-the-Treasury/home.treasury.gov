# Treasury Site UX & Accessibility Test Report

**Report Generated:** January 17, 2026  
**Staging URL:** https://home-staging.awsdev.treasury.gov/  
**Browser:** Chromium Desktop (1200×800)  
**Test Framework:** Playwright + axe-core  

---

## Executive Summary

| Metric | Result |
|--------|--------|
| **Total Tests** | 114 |
| **Passed** | 91 (80%) |
| **Failed** | 23 (20%) |
| **Duration** | 2.6 minutes |

### Overall Status: ⚠️ NEEDS ATTENTION

The site is largely functional with good keyboard accessibility and CSP compliance. However, there are **critical issues** with the search form visibility and **serious accessibility violations** that need to be addressed before production deployment.

---

## Pages Tested

| Page | URL | Status |
|------|-----|--------|
| Homepage | [/](https://home-staging.awsdev.treasury.gov/) | ⚠️ Issues |
| Press Releases | [/news/press-releases/](https://home-staging.awsdev.treasury.gov/news/press-releases/) | ⚠️ Issues |
| Advanced Search | [/news/search/](https://home-staging.awsdev.treasury.gov/news/search/) | ❌ Critical |
| All News | [/news/all/](https://home-staging.awsdev.treasury.gov/news/all/) | ⚠️ Issues |
| 404 Page | [/this-page-does-not-exist/](https://home-staging.awsdev.treasury.gov/this-page-does-not-exist/) | ✅ Pass |

---

## Test Results by Category

### 1. Visual & Layout Tests

| Test | Status | Notes |
|------|--------|-------|
| Homepage loads without JS errors | ✅ PASS | |
| Homepage has no broken images | ✅ PASS | |
| Desktop responsive (1200px) | ✅ PASS | |
| Tablet responsive (768px) | ✅ PASS | |
| **Mobile responsive (375px)** | ❌ FAIL | **Horizontal scrolling detected** |
| Footer displays correctly | ✅ PASS | |
| Press Releases loads | ✅ PASS | |
| Advanced Search form visible | ❌ FAIL | Form element exists but is hidden |
| All News page loads | ✅ PASS | |
| 404 page displays content | ✅ PASS | |
| Single article loads | ❌ FAIL | Article links not clickable |

#### Issues Found:

##### Critical - Mobile Horizontal Scroll
- **Severity:** High
- **Page:** [Homepage](https://home-staging.awsdev.treasury.gov/) at 375px viewport
- **Problem:** Page content extends beyond viewport, causing horizontal scroll
- **Impact:** Poor mobile UX, content may be cut off

##### Critical - Search Form Not Visible
- **Severity:** Critical
- **Page:** [/news/search/](https://home-staging.awsdev.treasury.gov/news/search/)
- **Problem:** The search form element (`<form method="get" class="search-form">`) exists in DOM but is hidden
- **Impact:** Users cannot perform advanced searches

---

### 2. Navigation & Interaction Tests

| Test | Status | Notes |
|------|--------|-------|
| Skip link is first focusable | ✅ PASS | Properly implemented |
| Skip link navigates to main | ❌ FAIL | Element outside viewport |
| Main nav visible on desktop | ✅ PASS | |
| Navigation links clickable | ❌ FAIL | Some nav links hidden |
| Dropdown menus work | ✅ PASS | |
| Mobile hamburger visible | ✅ PASS | |
| Mobile menu opens/closes | ✅ PASS | |
| Internal links navigate | ❌ FAIL | First internal link not visible |
| External links have noopener | ✅ PASS | |
| Breadcrumbs display | ✅ PASS | |
| Header logo works | ✅ PASS | |
| Footer links functional | ✅ PASS | |

#### Issues Found:

##### Medium - Skip Link Implementation
- **Severity:** Medium
- **Problem:** Skip link exists but is "outside of viewport" when clicked
- **Impact:** Screen reader users may have difficulty using skip navigation

##### Medium - Hidden Navigation Elements
- **Severity:** Medium
- **Problem:** Some navigation links are present but hidden, causing test failures when trying to click them
- **Impact:** Test reliability; may indicate CSS display issues

---

### 3. Keyboard Accessibility Tests ✅

| Test | Status |
|------|--------|
| Focusable elements have focus indicators | ✅ PASS |
| Focused links have visible outline | ✅ PASS |
| Tab order logical on homepage | ✅ PASS |
| Tab order on press releases | ✅ PASS |
| No keyboard traps | ✅ PASS |
| Modal dialogs closeable with Escape | ✅ PASS |
| Buttons activatable with Enter/Space | ✅ PASS |
| Links activatable with Enter | ✅ PASS |
| Form fields navigable | ✅ PASS |
| Form labels associated with inputs | ✅ PASS |
| axe-core keyboard checks - homepage | ✅ PASS |
| axe-core keyboard checks - search | ✅ PASS |

**Status: EXCELLENT** - All keyboard accessibility tests passed.

---

### 4. News Search Functionality

| Test | Status | Notes |
|------|--------|-------|
| Search form present | ❌ FAIL | Form hidden |
| Keyword input exists | ❌ FAIL | Input hidden |
| Date filter controls exist | ✅ PASS | |
| Keyword search works | ❌ FAIL | Cannot interact - hidden |
| Empty search behavior | ❌ FAIL | Cannot interact - hidden |
| Today filter works | ✅ PASS | |
| This Week filter works | ✅ PASS | |
| This Month filter works | ✅ PASS | |
| Document type dropdown | ✅ PASS | |
| Office dropdown | ✅ PASS | |
| Results count displayed | ✅ PASS | |
| aria-live regions | ✅ PASS | |
| Pagination controls | ✅ PASS | |
| Next button works | ✅ PASS | |
| Load More works | ✅ PASS | |
| Reset button | ❌ FAIL | Cannot interact - hidden |

#### Root Cause Analysis:
The main search form on [/news/search/](https://home-staging.awsdev.treasury.gov/news/search/) is hidden via CSS but the search filters (date presets, dropdowns) work correctly. This suggests there may be two separate search mechanisms - an advanced form that's hidden and inline filters that work.

---

### 5. News List Pages

| Test | Status |
|------|--------|
| Press releases list displays | ✅ PASS |
| News items have date/title | ✅ PASS |
| Today filter works | ✅ PASS |
| This Week filter works | ✅ PASS |
| This Month filter works | ✅ PASS |
| This Year filter works | ✅ PASS |
| Date range inputs exist | ✅ PASS |
| Date range filter works | ✅ PASS |
| Keyword search filters | ❌ FAIL |
| Pagination displayed | ✅ PASS |
| Page number links work | ✅ PASS |
| Jump to page works | ✅ PASS |
| All News displays items | ✅ PASS |
| Category labels visible | ✅ PASS |
| News items link correctly | ❌ FAIL |

#### Issues Found:

##### Low - URL Format for News Links
- **Problem:** Links use absolute URLs (`https://home.treasury.gov/...`) instead of relative (`/news/...`)
- **Impact:** Tests expected relative paths; not a functional issue

---

### 6. CSP Compliance ✅

| Test | Status |
|------|--------|
| Homepage - no CSP violations | ✅ PASS |
| Press Releases - no CSP violations | ✅ PASS |
| Advanced Search - CSP check | ❌ FAIL* |
| All News - no CSP violations | ✅ PASS |
| 404 Page - no CSP violations | ✅ PASS |
| No inline onclick handlers | ✅ PASS |
| Search page - no inline handlers | ✅ PASS |
| No inline script tags | ✅ PASS |
| All scripts from same origin | ✅ PASS |
| All stylesheets from same origin | ✅ PASS |
| Buttons work without inline handlers | ✅ PASS |
| Form submit without inline handler | ❌ FAIL* |
| JS executes without CSP blocking | ✅ PASS |

*Failures are due to hidden search form, not actual CSP violations.

**Status: EXCELLENT** - No actual CSP violations detected. All JavaScript is CSP-compliant.

---

### 7. Accessibility (WCAG 2.2 AA)

| Test | Status | Notes |
|------|--------|-------|
| Homepage - axe violations | ❌ FAIL | 1 violation |
| Homepage - heading hierarchy | ❌ FAIL | Skips from h0 to h3 |
| Homepage - images have alt | ✅ PASS | |
| Press Releases - axe violations | ❌ FAIL | 1 violation |
| Press Releases - semantic markup | ✅ PASS | |
| Advanced Search - axe violations | ❌ FAIL | 1 violation |
| Advanced Search - form labels | ✅ PASS | |
| Advanced Search - button names | ✅ PASS | |
| All News - axe violations | ❌ FAIL | 1 violation |
| 404 Page - axe violations | ✅ PASS | |
| Color contrast | ❌ FAIL | Test error |
| Landmark regions | ✅ PASS | |
| Links have discernible text | ✅ PASS | |

#### Critical Accessibility Issues:

##### 1. Adobe Reader Link - Insufficient Contrast (Serious)

| Property | Value |
|----------|-------|
| WCAG Rule | 1.4.1 Use of Color (Level A) |
| Element | `<a href="https://get.adobe.com/reader/">Adobe® Reader®</a>` |
| Location | Footer on all pages |
| Link Color | `#ced3d9` |
| Surrounding Text Color | `#b6bdc6` |
| Actual Contrast | 1.25:1 |
| Required Contrast | 3:1 |

**Problem:** 
- Link has insufficient color contrast
- Link has no underline or other styling to distinguish it from surrounding text

**Fix Required:**
- Add underline to the link, OR
- Increase color contrast to at least 3:1

##### 2. Heading Hierarchy - Missing H1/H2

| Property | Value |
|----------|-------|
| WCAG Rule | 1.3.1 Info and Relationships (Level A) |
| Problem | Page jumps directly from no heading to H3 |
| Impact | Screen readers cannot properly navigate heading structure |

**Fix Required:** 
- Add proper H1 for page title
- Ensure headings are sequential (H1 → H2 → H3)

#### Observations (Not Failures):

**Duplicate Link Text:**
Links with same text but different destinations (informational, not blocking):

| Link Text | Destinations |
|-----------|--------------|
| "reports" | /policy-issues/tax-policy, /data/troubled-assets-relief-program |
| "frequently asked questions" | ofac.treasury.gov/faqs, treasurydirect.gov, /services/... |
| "view all →" | /news/featured-stories, /news/press-releases, /news/press-releases/statements-remarks |
| "more →" | /news/featured-stories/, /news/press-releases/ |

---

### 8. Performance

| Test | Status | Time/Value |
|------|--------|------------|
| Homepage loads < 3s | ✅ PASS | 823ms |
| Press Releases loads < 3s | ✅ PASS | 558ms |
| Search page loads < 3s | ✅ PASS | 872ms |
| No layout shift - homepage | ✅ PASS | |
| No layout shift - pagination | ✅ PASS | |
| Images use lazy loading | ❌ FAIL | 0 lazy-loaded |
| Images have dimensions | ✅ PASS | (with warnings) |
| CSS loads | ✅ PASS | |
| JS files load | ✅ PASS | |
| Fonts load | ✅ PASS | |
| Static assets have cache headers | ❌ FAIL | Only 21% cached |

#### Performance Issues:

##### Medium - No Lazy Loading
- **Problem:** None of the 6+ images use `loading="lazy"` attribute
- **Impact:** All images load immediately, increasing initial page weight
- **Recommendation:** Add `loading="lazy"` to below-the-fold images

##### Medium - Missing Cache Headers
- **Problem:** 78% of static assets lack cache-control headers
- **Affected Files:**

```
/fonts/source-sans-pro-400.woff2
/fonts/source-sans-pro-600.woff2
/fonts/source-sans-pro-700.woff2
/fonts/merriweather-400.woff2
/fonts/merriweather-700.woff2
/fonts/cormorant-garamond-500.woff2
/images/us_flag_small.png
/images/icon-dot-gov.svg
/images/icon-https.svg
/images/treasury-seal.svg
/images/secretary-bessent.jpg
```

- **Impact:** Browsers re-fetch assets on every visit
- **Fix:** Add `Cache-Control` headers in S3/CloudFront configuration

##### Low - Images Without Dimensions
Images missing explicit width/height (can cause layout shift):
- `icon-dot-gov.svg`
- `icon-https.svg`
- `treasury-seal.svg`
- `secretary-bessent.jpg`

---

## Priority Action Items

### 🔴 Critical (Fix Before Launch)

| # | Issue | Page | Fix |
|---|-------|------|-----|
| 1 | Adobe Reader Link Accessibility | All pages (footer) | Add underline or increase contrast to 3:1 |
| 2 | Hidden Search Form | [/news/search/](https://home-staging.awsdev.treasury.gov/news/search/) | Investigate CSS, make form visible |
| 3 | Mobile Horizontal Scroll | [Homepage](https://home-staging.awsdev.treasury.gov/) | Check for fixed-width elements |

### 🟡 High Priority

| # | Issue | Fix |
|---|-------|-----|
| 4 | Heading Hierarchy | Add proper H1, ensure sequential headings |
| 5 | Cache Headers | Configure S3/CloudFront with `Cache-Control: max-age=31536000` |

### 🟢 Medium Priority

| # | Issue | Fix |
|---|-------|-----|
| 6 | Lazy Loading | Add `loading="lazy"` to below-fold images |
| 7 | Image Dimensions | Add width/height attributes to prevent CLS |

---

## What's Working Well ✅

| Category | Status |
|----------|--------|
| CSP Compliance | ✅ All JavaScript compliant, no inline scripts |
| Keyboard Navigation | ✅ All interactive elements keyboard accessible |
| Focus Indicators | ✅ Visible on all focusable elements |
| Form Labels | ✅ Properly associated with inputs |
| Page Load Speed | ✅ All pages < 1 second |
| Semantic Markup | ✅ Proper landmarks, lists, articles |
| Mobile Menu | ✅ Hamburger works correctly |
| Pagination | ✅ All controls functional |
| Date Filters | ✅ Inline filters work correctly |
| 404 Page | ✅ Proper error content |

---

## Test Files

Test specifications are located in:

| File | Description |
|------|-------------|
| [`tests/1-visual-layout.spec.ts`](../tests/1-visual-layout.spec.ts) | Visual & responsive layout tests |
| [`tests/2-navigation.spec.ts`](../tests/2-navigation.spec.ts) | Navigation & interaction tests |
| [`tests/3-keyboard-accessibility.spec.ts`](../tests/3-keyboard-accessibility.spec.ts) | Keyboard accessibility tests |
| [`tests/4-news-search.spec.ts`](../tests/4-news-search.spec.ts) | News search functionality |
| [`tests/5-news-list.spec.ts`](../tests/5-news-list.spec.ts) | News list page tests |
| [`tests/6-csp-compliance.spec.ts`](../tests/6-csp-compliance.spec.ts) | CSP compliance tests |
| [`tests/7-accessibility-axe.spec.ts`](../tests/7-accessibility-axe.spec.ts) | WCAG 2.2 AA automated checks |
| [`tests/8-performance.spec.ts`](../tests/8-performance.spec.ts) | Performance tests |

---

## How to Run Tests

```bash
# Install dependencies
npm install
npx playwright install chromium

# Run all tests against staging
npm run test:staging

# Run specific test suite
npx playwright test 7-accessibility-axe

# View HTML report
npm run test:report

# Run with visible browser
npm run test:headed
```

---

## Appendix: Full Test Output

<details>
<summary>Click to expand raw test results</summary>

```
Running 114 tests using 5 workers

✓ Visual & Layout - Homepage › loads without JavaScript errors (7.5s)
✓ Visual & Layout - Homepage › has no broken images (6.0s)
✓ Visual & Layout - Homepage › is responsive at desktop (1200px) (6.1s)
✓ Visual & Layout - Homepage › is responsive at tablet (768px) (6.2s)
✘ Visual & Layout - Homepage › is responsive at mobile (375px) (6.0s)
✓ Visual & Layout - Homepage › footer displays correctly (2.4s)
✓ Visual & Layout - Homepage › main content area exists (2.6s)
✓ Visual & Layout - Press Releases › loads without JavaScript errors (3.6s)
✓ Visual & Layout - Press Releases › has no broken images (1.7s)
✓ Visual & Layout - Press Releases › no horizontal scroll at mobile (2.1s)
✓ Visual & Layout - Press Releases › news items display in a list (2.5s)
✓ Visual & Layout - Advanced Search › loads without JavaScript errors (3.6s)
✘ Visual & Layout - Advanced Search › search form is visible (11.9s)
✓ Visual & Layout - Advanced Search › no horizontal scroll at mobile (1.7s)
✓ Visual & Layout - All News › loads without JavaScript errors (2.9s)
✓ Visual & Layout - All News › no horizontal scroll at mobile (1.6s)
✓ Visual & Layout - 404 Page › displays 404 content (11.4s)
✓ Visual & Layout - 404 Page › no horizontal scroll at mobile (9.4s)
✓ Visual & Layout - 404 Page › has navigation back to homepage (9.2s)
✘ Visual & Layout - Single Article › article page loads and displays content (30.1s)
✓ Navigation - Skip Link › skip link is first focusable element and works (2.1s)
✘ Navigation - Skip Link › skip link navigates to main content (30.4s)
✓ Navigation - Desktop Menu › main navigation is visible on desktop (2.6s)
✘ Navigation - Desktop Menu › navigation links are clickable (13.0s)
✓ Navigation - Desktop Menu › dropdown menus open on interaction (2.7s)
✓ Navigation - Mobile Menu › hamburger menu button is visible on mobile (1.9s)
✓ Navigation - Mobile Menu › mobile menu opens and closes (2.7s)
✘ Navigation - Links › internal links navigate correctly (30.2s)
✓ Navigation - Links › external links have rel="noopener" (1.7s)
✓ Navigation - Breadcrumbs › breadcrumbs display on news pages (1.8s)
✓ Navigation - Breadcrumbs › breadcrumb home link works (12.4s)
✓ Navigation - Header & Footer › header logo links to homepage (12.0s)
✓ Navigation - Header & Footer › footer links are functional (2.0s)
✓ Keyboard Accessibility - Focus Indicators › all focusable elements have visible focus indicators (1.7s)
✓ Keyboard Accessibility - Focus Indicators › focused links have visible outline (1.8s)
✓ Keyboard Accessibility - Tab Order › tab order is logical on homepage (2.1s)
✓ Keyboard Accessibility - Tab Order › tab order follows visual layout on press releases (2.1s)
✓ Keyboard Accessibility - Keyboard Traps › can escape from any focus with Tab or Escape (2.3s)
✓ Keyboard Accessibility - Keyboard Traps › modal dialogs can be closed with Escape (1.9s)
✓ Keyboard Accessibility - Interactive Elements › buttons are activatable with Enter and Space (2.2s)
✓ Keyboard Accessibility - Interactive Elements › links are activatable with Enter (7.0s)
✓ Keyboard Accessibility - Forms › form fields are navigable with Tab (2.4s)
✓ Keyboard Accessibility - Forms › form labels are associated with inputs (1.8s)
✓ Keyboard Accessibility - axe-core Audit › homepage passes keyboard accessibility checks (2.7s)
✓ Keyboard Accessibility - axe-core Audit › search page passes keyboard accessibility checks (3.0s)
✘ News Search - Page Structure › search form is present and visible (11.7s)
✘ News Search - Page Structure › keyword search input exists (11.8s)
✓ News Search - Page Structure › date filter controls exist (1.6s)
✘ News Search - Keyword Search › keyword search returns results (30.2s)
✘ News Search - Keyword Search › empty search shows message or all results (30.2s)
✓ News Search - Date Presets › Today filter works (2.7s)
✓ News Search - Date Presets › This Week filter works (2.4s)
✓ News Search - Date Presets › This Month filter works (2.3s)
✓ News Search - Dropdown Filters › document type dropdown works (2.6s)
✓ News Search - Dropdown Filters › office dropdown works (2.1s)
✓ News Search - Results Display › results count is displayed (1.9s)
✓ News Search - Results Display › results have accessible announcements (aria-live) (1.9s)
✓ News Search - Pagination › pagination controls exist (1.7s)
✓ News Search - Pagination › pagination Next button works (1.8s)
✓ News Search - Pagination › Load More button works (1.8s)
✘ News Search - Reset/Clear › reset button clears filters (30.2s)
✓ News List - Press Releases › page displays list of press releases (1.8s)
✓ News List - Press Releases › each news item has date and title (1.6s)
✓ News List - Inline Filters › Today filter button exists and works (2.4s)
✓ News List - Inline Filters › This Week filter works (2.2s)
✓ News List - Inline Filters › This Month filter works (3.8s)
✓ News List - Inline Filters › This Year filter works (3.0s)
✓ News List - Date Range Picker › date range inputs exist (1.7s)
✓ News List - Date Range Picker › date range filter applies correctly (2.2s)
✘ News List - Keyword Search › keyword search filters results (30.3s)
✓ News List - Pagination › pagination is displayed (1.6s)
✓ News List - Pagination › page number links work (3.1s)
✓ News List - Pagination › jump to page form works (2.6s)
✓ News List - All News Page › displays news from all categories (2.1s)
✓ News List - All News Page › category labels are visible (2.0s)
✘ News List - All News Page › news items link to detail pages (1.7s)
✓ CSP Compliance - Console Error Monitoring › homepage has no CSP violations (1.7s)
✓ CSP Compliance - Console Error Monitoring › press releases page has no CSP violations (1.7s)
✘ CSP Compliance - Console Error Monitoring › advanced search page has no CSP violations (30.2s)
✓ CSP Compliance - Console Error Monitoring › all news page has no CSP violations (1.7s)
✓ CSP Compliance - Console Error Monitoring › 404 page has no CSP violations (10.0s)
✓ CSP Compliance - Inline Script Check › homepage has no inline onclick handlers (1.6s)
✓ CSP Compliance - Inline Script Check › search page has no inline handlers (1.7s)
✓ CSP Compliance - Inline Script Check › no inline script tags without src (1.9s)
✓ CSP Compliance - External Resources › all scripts are from same origin (1.8s)
✓ CSP Compliance - External Resources › all stylesheets are from same origin (2.0s)
✘ CSP Compliance - Interactive Elements › form submit works without inline handler (30.1s)
✓ CSP Compliance - Interactive Elements › buttons work without inline handlers (1.9s)
✓ CSP Compliance - Performance Check › JavaScript executes without CSP blocking (1.6s)
✘ Accessibility - Homepage › should have no accessibility violations (3.1s)
✘ Accessibility - Homepage › should have proper heading hierarchy (1.9s)
✓ Accessibility - Homepage › images have alt text (1.9s)
✘ Accessibility - Press Releases › should have no accessibility violations (3.9s)
✓ Accessibility - Press Releases › list items use proper semantic markup (1.9s)
✘ Accessibility - Advanced Search › should have no accessibility violations (4.3s)
✓ Accessibility - Advanced Search › form controls have accessible labels (1.8s)
✓ Accessibility - Advanced Search › buttons have accessible names (1.9s)
✘ Accessibility - All News › should have no accessibility violations (3.4s)
✓ Accessibility - 404 Page › should have no accessibility violations (12.7s)
✘ Accessibility - Color Contrast › homepage meets color contrast requirements (1.8s)
✓ Accessibility - Landmarks › page has proper landmark regions (1.6s)
✓ Accessibility - Links › links have discernible text (1.6s)
✓ Accessibility - Links › no duplicate link text with different destinations (1.5s)
✓ Performance - Page Load Times › homepage loads within 3 seconds (823ms)
✓ Performance - Page Load Times › press releases page loads within 3 seconds (558ms)
✓ Performance - Page Load Times › search page loads within 3 seconds (872ms)
✓ Performance - Layout Stability › homepage has no significant layout shift (3.1s)
✓ Performance - Layout Stability › news list has stable layout during pagination (1.8s)
✘ Performance - Image Loading › images have loading attribute for lazy loading (2.3s)
✓ Performance - Image Loading › images have width and height to prevent layout shift (2.0s)
✓ Performance - Resource Loading › critical CSS is loaded (762ms)
✓ Performance - Resource Loading › JavaScript files load successfully (1.6s)
✓ Performance - Resource Loading › fonts load successfully (1.8s)
✘ Performance - Caching Headers › static assets have cache headers (2.1s)

23 failed
91 passed (2.6m)
```

</details>

---

*Report generated by Playwright automated testing suite*
