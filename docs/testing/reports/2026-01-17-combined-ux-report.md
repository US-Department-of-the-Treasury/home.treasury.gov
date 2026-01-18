# Treasury Site UX & Accessibility Combined Test Report

**Report Date:** January 17, 2026  
**Prepared By:** Automated Testing Suite + Manual Chrome Audit

---

## Executive Summary

Two independent testing methodologies were used to evaluate the Treasury staging site:

| Test Method | Environment | Tests | Pass Rate |
|-------------|-------------|-------|-----------|
| **Playwright Automated** | Staging (CloudFront) | 114 | 80% (91/114) |
| **Manual Chrome Audit** | Local (Hugo Server) | 25+ | 96% (1 issue) |

### Overall Site Status: ⚠️ READY WITH FIXES NEEDED

The site is **production-ready** with excellent keyboard accessibility, CSP compliance, and core functionality. However, **3 critical issues** must be addressed before launch.

---

## Critical Issues Summary

| # | Issue | Severity | Found In | Status |
|---|-------|----------|----------|--------|
| 1 | Adobe Reader link lacks contrast/underline | **Critical** | Playwright | 🔴 Fix Required |
| 2 | Homepage horizontal scroll on mobile | **High** | Playwright | 🔴 Fix Required |
| 3 | 404 page redirects to production (local only) | **Medium** | Chrome | 🟡 Investigate |

---

## Test Results Comparison

### Visual & Layout

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| No console errors | ✅ Pass | ✅ Pass |
| No broken images | ✅ Pass | ✅ Pass |
| Desktop responsive (1200px) | ✅ Pass | ✅ Pass |
| Tablet responsive (768px) | ✅ Pass | ✅ Pass |
| Mobile responsive (375px) | ❌ Horizontal scroll | ✅ Pass |
| Footer displays correctly | ✅ Pass | ✅ Pass |

**Discrepancy Note:** Mobile horizontal scroll was detected on staging but not locally. This may be caused by:
- CloudFront/CDN differences
- Build configuration differences
- Viewport measurement differences

### Navigation & Interaction

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| Skip link present | ✅ Pass | ✅ Pass |
| Skip link works | ⚠️ Outside viewport | ✅ Pass |
| Main navigation visible | ✅ Pass | ✅ Pass |
| Dropdown menus work | ✅ Pass | ✅ Pass |
| Mobile hamburger works | ✅ Pass | ✅ Pass |
| Breadcrumbs work | ✅ Pass | ✅ Pass |
| External links have noopener | ✅ Pass | ✅ Pass |

### Keyboard Accessibility

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| Focus indicators visible | ✅ Pass | ✅ Pass |
| Tab order logical | ✅ Pass | ✅ Pass |
| No keyboard traps | ✅ Pass | ✅ Pass |
| Escape closes menus | ✅ Pass | ✅ Pass |
| Enter activates buttons | ✅ Pass | ✅ Pass |
| Form fields navigable | ✅ Pass | ✅ Pass |

**Status: EXCELLENT** - Both test methods confirm keyboard accessibility is solid.

### News Search & Filters

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| Search form visible | ❌ Hidden | ✅ Pass |
| Keyword search works | ❌ Cannot interact | ✅ Pass |
| Date preset filters | ✅ Pass | ✅ Pass |
| Dropdown filters | ✅ Pass | ✅ Pass |
| Pagination works | ✅ Pass | ✅ Pass |
| Load More works | ✅ Pass | ✅ Pass |

**Discrepancy Note:** The search form on `/news/search/` appears hidden on staging but works locally. This needs investigation - may be a deployment or base URL issue.

### Accessibility (WCAG 2.2 AA)

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| Heading hierarchy | ❌ Skips levels | ✅ H1 → H2 → H3 |
| Images have alt text | ✅ Pass | ✅ Pass |
| Form labels present | ✅ Pass | ✅ Pass |
| Landmark regions | ✅ Pass | ✅ Pass |
| Link text discernible | ✅ Pass | ✅ Pass |
| **Adobe Reader link contrast** | ❌ **1.25:1 (needs 3:1)** | Not tested |

**Discrepancy Note:** Heading hierarchy differs between environments. The nav dropdowns contain H3s that appear before the page H1 in DOM order.

### CSP Compliance

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| No inline scripts | ✅ Pass | ✅ Pass |
| No inline handlers | ✅ Pass | ✅ Pass |
| Scripts from self only | ✅ Pass | ✅ Pass |
| No CSP console errors | ✅ Pass | ✅ Pass |

**Status: EXCELLENT** - Full CSP compliance confirmed by both methods.

### Performance

| Test | Playwright (Staging) | Chrome (Local) |
|------|---------------------|----------------|
| Page load < 3s | ✅ 558-872ms | ✅ Fast |
| No layout shift | ✅ Pass | ✅ Pass |
| Lazy loading images | ❌ None implemented | Not tested |
| Cache headers | ❌ 21% coverage | N/A (local) |

---

## Detailed Findings

### 🔴 Critical Issue #1: Adobe Reader Link Accessibility

**Location:** Footer on all pages  
**Element:** `<a href="https://get.adobe.com/reader/">Adobe® Reader®</a>`

| Property | Current | Required |
|----------|---------|----------|
| Color Contrast | 1.25:1 | 3:1 minimum |
| Link Styling | None | Underline or other indicator |
| WCAG Rule | 1.4.1 Use of Color | Level A |

**Fix Options:**
1. Add `text-decoration: underline` to the link
2. Change link color to meet 3:1 contrast ratio
3. Add an icon or other non-color indicator

**Recommended CSS Fix:**
```css
.required-plugins a {
  text-decoration: underline;
  color: #ffffff; /* or another high-contrast color */
}
```

---

### 🔴 Critical Issue #2: Mobile Horizontal Scroll

**Location:** Homepage at 375px viewport  
**Impact:** Content extends beyond viewport on mobile devices

**Possible Causes:**
- Fixed-width elements in header or content
- Images without max-width: 100%
- Tables or code blocks without overflow handling

**Investigation Steps:**
1. Open DevTools at 375px width
2. Use "Elements" panel to find element extending beyond viewport
3. Add appropriate CSS constraints

---

### 🟡 Medium Issue #3: 404 Redirect (Local Only)

**Location:** Any non-existent URL on localhost  
**Behavior:** Redirects to production https://home.treasury.gov/

**Root Cause:** Likely in `redirect-404.js` or Hugo 404 template configuration

**Note:** This only affects local development, not production. Lower priority but should be fixed for proper local testing.

---

## Environment Comparison

| Aspect | Local (Hugo Server) | Staging (CloudFront) |
|--------|--------------------|--------------------|
| Base URL | http://localhost:1314/ | https://home-staging.awsdev.treasury.gov/ |
| Link Format | Relative (`/news/...`) | Absolute (`https://home.treasury.gov/...`) |
| 404 Handling | Redirects to prod | Shows 404 page |
| Search Form | Visible | Hidden |
| Cache Headers | N/A | Missing on 78% of assets |

---

## Action Items by Priority

### Before Production Launch 🔴

| # | Action | Owner | Est. Effort |
|---|--------|-------|-------------|
| 1 | Fix Adobe Reader link accessibility | Frontend | 15 min |
| 2 | Fix mobile horizontal scroll | Frontend | 1 hour |
| 3 | Add cache headers to S3/CloudFront | DevOps | 30 min |

### High Priority 🟡

| # | Action | Owner | Est. Effort |
|---|--------|-------|-------------|
| 4 | Investigate staging search form visibility | Frontend | 1 hour |
| 5 | Review heading hierarchy in nav | Frontend | 30 min |
| 6 | Add lazy loading to images | Frontend | 30 min |

### Nice to Have 🟢

| # | Action | Owner | Est. Effort |
|---|--------|-------|-------------|
| 7 | Fix 404 redirect in local dev | Frontend | 1 hour |
| 8 | Add explicit dimensions to images | Frontend | 1 hour |

---

## What's Working Excellently ✅

| Area | Confidence |
|------|------------|
| **CSP Compliance** | 100% - No violations in either environment |
| **Keyboard Accessibility** | 100% - All tests pass |
| **Page Load Performance** | Excellent - All pages < 1 second |
| **Core Navigation** | Excellent - Menus, links, breadcrumbs work |
| **News Filtering** | Excellent - Date presets, dropdowns, pagination |
| **Semantic Markup** | Good - Proper landmarks, lists, articles |
| **Form Accessibility** | Good - Labels properly associated |

---

## Testing Methodology

### Playwright Automated Tests
- **Framework:** Playwright 1.40.1 + axe-core 4.8.2
- **Browser:** Chromium Desktop (1200×800)
- **Tests:** 114 across 8 test suites
- **Coverage:** Visual, navigation, keyboard, search, lists, CSP, a11y, performance

### Manual Chrome Audit
- **Browser:** Chrome (latest)
- **Viewport Sizes:** 375px, 768px, 1200px
- **Tests:** Visual inspection, keyboard navigation, functionality verification
- **Tools:** DevTools Console, Accessibility Inspector

---

## Report Files

| Report | Description |
|--------|-------------|
| [2026-01-17-ux-accessibility-report.md](./2026-01-17-ux-accessibility-report.md) | Full Playwright automated test results |
| [2026-01-17-claude-chrome-manual-report.md](./2026-01-17-claude-chrome-manual-report.md) | Manual Chrome browser audit |
| [2026-01-17-combined-ux-report.md](./2026-01-17-combined-ux-report.md) | This combined report |

---

## Conclusion

The Treasury site demonstrates **strong fundamentals** in accessibility, performance, and CSP compliance. The three critical issues identified are straightforward to fix:

1. **Adobe Reader link** - Add underline (CSS one-liner)
2. **Mobile scroll** - Find and constrain overflow element
3. **Cache headers** - CloudFront configuration update

Once these are addressed, the site is **ready for production deployment**.

---

*Report generated January 17, 2026*
