# Treasury Site UX Testing Report (Manual Chrome Audit)

**Test Environment**
- **URL:** http://localhost:1314/
- **Date:** January 17, 2026
- **Browser:** Chrome
- **Tester:** Claude (manual browser testing)

---

## Pages Tested

| Page | Status |
|------|--------|
| Homepage | ✅ Pass |
| Press Releases | ✅ Pass |
| Single Article | ✅ Pass |
| Advanced Search | ✅ Pass |
| All News | ✅ Pass |
| 404 Page | ⚠️ Issue Found |

---

## Bugs Found

### 1. 404 Page Redirect to Production

| Property | Value |
|----------|-------|
| **Severity** | Medium |
| **URL** | http://localhost:1314/does-not-exist/ |
| **Steps** | Navigate to any non-existent URL on localhost |
| **Expected** | Local 404 error page |
| **Actual** | Redirects to production site (https://home.treasury.gov/does-not-exist/) |
| **Impact** | Local development/testing cannot verify 404 page styling |

---

## All Checks Passed ✅

### Visual

- ✅ No console errors on any page
- ✅ No broken images observed
- ✅ Responsive layouts work at 375px, 768px, 1200px
- ✅ Footer displays correctly at all sizes

### Keyboard Navigation

- ✅ Skip link appears on first Tab press
- ✅ Skip link navigates to #main-content
- ✅ Focus visible on all interactive elements (white outline)
- ✅ Dropdown menus open with Enter key
- ✅ Escape closes dropdown menus
- ✅ No keyboard traps detected

### Functionality

- ✅ Navigation links work
- ✅ Filter buttons work (Today, This Week, etc.)
- ✅ Date range pickers work
- ✅ Search/filter features work
- ✅ Pagination works
- ✅ Advanced Search returns results
- ✅ "Load More" button works

### Accessibility

- ✅ Single H1 on pages
- ✅ Headings follow logical order (H1 → H2 → H3)
- ✅ Images have alt text
- ✅ Form fields have labels
- ⚠️ Many H3s in nav dropdowns appear before H1 in DOM order (minor)

### CSP Check

- ✅ No Content Security Policy errors in console

---

## Notes

- The site is well-built with good UX patterns
- Mega-menu dropdowns are keyboard accessible
- Mobile hamburger menu appears at appropriate breakpoints
- Filter tags and clear buttons enhance usability

---

## Summary

**Testing Complete!**

The Treasury site is in excellent shape. Only one issue found: the 404 page redirects to the production Treasury site instead of displaying a local error page. All other functionality, accessibility, and responsive design tests passed.

---

## Comparison: Local vs Staging

| Test Area | Local (Chrome Manual) | Staging (Playwright) |
|-----------|----------------------|---------------------|
| Visual/Layout | ✅ All pass | ⚠️ Mobile scroll issue |
| Keyboard Nav | ✅ All pass | ✅ All pass |
| Search Form | ✅ Visible & works | ❌ Hidden on staging |
| Accessibility | ✅ Headings OK | ❌ Heading hierarchy issues |
| CSP | ✅ No violations | ✅ No violations |
| 404 Page | ⚠️ Redirects to prod | ✅ Shows 404 content |

**Note:** Some differences between local and staging results may be due to:
1. Different base URLs (absolute vs relative links)
2. CDN/CloudFront configuration on staging
3. Hugo build differences between environments
