# Section 508 & WCAG 2.2 Level AA Accessibility Audit Report

**Audit Date:** January 14, 2026  
**Audited Site:** U.S. Department of the Treasury Hugo Site  
**Auditor:** Accessibility-508-Auditor Agent  
**Standards:** Section 508, WCAG 2.2 Level AA

---

## Executive Summary

| Severity | Count |
|----------|-------|
| **Critical** | 1 |
| **Serious** | 5 |
| **Moderate** | 4 |
| **Minor** | 3 |

### Overall Assessment
The Treasury Hugo site demonstrates good foundational accessibility practices including:
- ✅ Skip link to main content
- ✅ Language attribute on `<html>` element
- ✅ Proper heading hierarchy within sections
- ✅ ARIA labels on navigation regions
- ✅ Form labels for date inputs
- ✅ Keyboard-accessible mega menus with Escape key support
- ✅ Focus indicators on form inputs

**Key Blockers Before Deployment:**
1. Multiple `<main>` landmarks (Critical)
2. Missing alt text on informational images
3. Insufficient focus indicator visibility on some interactive elements

---

## Detailed Findings

### CRITICAL VIOLATIONS

---

#### [CRITICAL] WCAG 1.3.1, 4.1.1: Multiple Main Landmarks

**Location:** `themes/treasury/layouts/news/list.html:26`

**Issue:** The page contains two `<main>` elements:
1. `<main id="main-content">` in `baseof.html`
2. `<main class="news-main-content">` in `news/list.html`

This confuses screen readers and violates the HTML5 specification which requires only one main landmark per page.

**Impact:** Screen reader users cannot reliably navigate to the main content area. JAWS and NVDA will announce "main" multiple times.

**Current Code:**
```html
<!-- In news/list.html -->
<main class="news-main-content">
  ...
</main>
```

**Fixed Code:**
```html
<!-- In news/list.html -->
<div class="news-main-content">
  ...
</div>
```

**Testing:** Use a screen reader (NVDA/JAWS) to navigate landmarks with `D` key. Verify only one main landmark is announced.

---

### SERIOUS VIOLATIONS

---

#### [SERIOUS] WCAG 1.1.1: Missing Alternative Text on Informational Images

**Location:** `themes/treasury/layouts/partials/usa-banner.html:18, 25`

**Issue:** The .gov and HTTPS icons use empty `alt` attributes (`alt=""`) but are informational images that support the adjacent text content.

**Impact:** Screen reader users miss context about what the icons represent.

**Current Code:**
```html
<img class="usa-banner-icon-large" src="/images/icon-dot-gov.svg" alt="">
...
<img class="usa-banner-icon-large" src="/images/icon-https.svg" alt="">
```

**Fixed Code:**
```html
<img class="usa-banner-icon-large" src="/images/icon-dot-gov.svg" alt="Dot gov icon">
...
<img class="usa-banner-icon-large" src="/images/icon-https.svg" alt="Lock icon">
```

**Note:** Alternatively, these could remain `alt=""` if the text content is self-sufficient, but the standard USWDS pattern includes descriptive alt text.

---

#### [SERIOUS] WCAG 2.4.7, 2.4.11: Insufficient Focus Indicator on Navigation Links

**Location:** `themes/treasury/static/css/treasury.css` - `.nav-link` styles

**Issue:** Navigation links in the main nav rely only on background color change on hover/focus. The focus state needs a visible outline or border that meets the minimum 2px width and 3:1 contrast ratio requirement per WCAG 2.4.11.

**Impact:** Keyboard users may lose track of focus position in the navigation.

**Current Code:**
```css
.nav-link:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}
```

**Fixed Code:**
```css
.nav-link:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}

.nav-link:focus {
  outline: 2px solid #ffbe2e;
  outline-offset: -2px;
}

.nav-link:focus-visible {
  outline: 2px solid #ffbe2e;
  outline-offset: -2px;
}
```

---

#### [SERIOUS] WCAG 3.3.2: Missing Visible Label for Keyword Search

**Location:** `themes/treasury/layouts/partials/news-search-sidebar.html:9-14`

**Issue:** The keyword search input has only an `aria-label` but no visible label. While `aria-label` provides accessibility, a visible label benefits all users including those with cognitive disabilities.

**Impact:** Users may be unsure what to enter in the field.

**Current Code:**
```html
<div class="filter-field">
  <input type="text" 
         name="title" 
         id="keyword-search" 
         class="filter-input"
         placeholder=""
         aria-label="Search by keyword">
</div>
```

**Fixed Code:**
```html
<div class="filter-field">
  <label for="keyword-search" class="visually-hidden">Search by keyword</label>
  <input type="text" 
         name="title" 
         id="keyword-search" 
         class="filter-input"
         placeholder="Enter keywords"
         aria-label="Search by keyword">
</div>
```

**Note:** Using `visually-hidden` class maintains visual design while providing accessible label. Alternatively, add a visible label above the input.

---

#### [SERIOUS] WCAG 2.4.4: Non-Descriptive Link Text in Pagination

**Location:** `themes/treasury/layouts/news/list.html:84`

**Issue:** The pagination "next" arrow uses only `→` as link text with `aria-label="Next page"`. While the aria-label helps, the link could be more descriptive.

**Impact:** When links are listed out of context, `→` provides no meaning.

**Current Code:**
```html
<a href="{{ $paginator.Next.URL }}" class="page-arrow next" aria-label="Next page">→</a>
```

**Fixed Code:**
```html
<a href="{{ $paginator.Next.URL }}" class="page-arrow next" aria-label="Go to next page of press releases">
  <span aria-hidden="true">→</span>
  <span class="visually-hidden">Next page</span>
</a>
```

---

#### [SERIOUS] WCAG 1.3.1: News Sidebar Multiple Lists Without Grouping

**Location:** `themes/treasury/layouts/partials/news-sidebar.html`

**Issue:** The news sidebar contains multiple `<ul>` elements without clear grouping. While functional, this could be confusing for screen reader users navigating by list.

**Impact:** Screen readers announce multiple lists, which may disorient users.

**Recommendation:** Consider using a single `<ul>` with logical grouping, or add headings between sections.

---

### MODERATE VIOLATIONS

---

#### [MODERATE] WCAG 2.5.8: Touch Target Size

**Location:** `themes/treasury/static/css/treasury.css` - Various links

**Issue:** Some footer links and news navigation links may have touch targets smaller than the WCAG 2.2 minimum of 24x24 CSS pixels.

**Testing Required:** Measure actual touch targets in browser DevTools. Links should have at least 24px height.

**Recommendation:**
```css
.footer-column a,
.news-nav-list li a {
  display: block;
  min-height: 24px;
  padding: 0.25rem 0;
}
```

---

#### [MODERATE] WCAG 4.1.2: Button in Mega Menu Lacks State Announcement

**Location:** `themes/treasury/layouts/partials/header.html:40-42`

**Issue:** While the mega menu buttons have `aria-expanded` and `aria-haspopup`, screen readers may not announce the expanded state change clearly.

**Recommendation:** Test with NVDA/JAWS to ensure state changes are announced. Consider adding `aria-controls` pointing to the mega menu ID.

**Current Code:**
```html
<button class="nav-link" aria-expanded="false" aria-haspopup="true">
  {{ .title }}
</button>
```

**Improved Code:**
```html
<button class="nav-link" aria-expanded="false" aria-haspopup="menu" aria-controls="mega-menu-{{ .title | urlize }}">
  {{ .title }}
</button>
<div class="mega-menu" id="mega-menu-{{ .title | urlize }}" role="menu">
```

---

#### [MODERATE] WCAG 2.4.6: Page Title Could Be More Descriptive

**Location:** `themes/treasury/layouts/_default/baseof.html:8`

**Issue:** Press release detail pages should include the release number in the title for easier identification.

**Current Code:**
```html
<title>{{ if .IsHome }}{{ site.Title }}{{ else }}{{ .Title }} | {{ site.Title }}{{ end }}</title>
```

**Recommendation:** For news items, consider including date or release number in title.

---

#### [MODERATE] WCAG 1.4.3: Verify Color Contrast Ratios

**Location:** Various CSS selectors

**Items to Verify:**
1. `.news-nav-list li.sub-item a` (color: `var(--gray-600)` on white) - Verify 4.5:1 ratio
2. `.article-category` text color
3. `.page-ellipsis` color (`var(--gray-600)`)
4. Placeholder text in inputs

**Tool:** Use Chrome DevTools contrast checker or WebAIM Contrast Checker.

---

### MINOR VIOLATIONS

---

#### [MINOR] WCAG 2.4.1: Skip Link Could Target More Precisely

**Location:** `themes/treasury/layouts/_default/baseof.html:41`

**Issue:** The skip link targets `#main-content` which works, but consider also providing a "Skip to News" link on news pages.

---

#### [MINOR] Best Practice: Empty Placeholder Attribute

**Location:** `themes/treasury/layouts/partials/news-search-sidebar.html:13`

**Issue:** `placeholder=""` creates an empty attribute. Either remove it or provide helpful placeholder text.

**Fixed Code:**
```html
<input type="text" 
       name="title" 
       id="keyword-search" 
       class="filter-input"
       placeholder="Enter search terms"
       aria-label="Search by keyword">
```

---

#### [MINOR] Best Practice: Footer Semantic Structure

**Location:** `themes/treasury/layouts/partials/footer.html`

**Issue:** Footer columns use `<nav>` elements with `aria-label`. This is correct, but consider whether all these are true navigation regions or if some should be simple `<div>` elements with headings.

---

## Automated Testing Configuration

### package.json scripts
```json
{
  "scripts": {
    "test:a11y": "pa11y-ci --config .pa11yci.json",
    "audit:a11y": "npx axe-cli http://localhost:1313/news/press-releases/ --tags wcag2a,wcag2aa,wcag22aa"
  }
}
```

### .pa11yci.json
```json
{
  "defaults": {
    "standard": "WCAG2AA",
    "timeout": 30000,
    "wait": 1000,
    "chromeLaunchConfig": {
      "args": ["--no-sandbox"]
    }
  },
  "urls": [
    "http://localhost:1313/news/press-releases/",
    "http://localhost:1313/news/press-releases/sb0357/",
    "http://localhost:1313/news/press-releases/page/2/"
  ]
}
```

---

## Manual Testing Checklist

### Keyboard Navigation
- [ ] Tab through all interactive elements in logical order
- [ ] Verify focus indicator is visible on ALL elements (min 2px, 3:1 contrast)
- [ ] Test mega menu with Enter/Space to open, Escape to close
- [ ] Verify no keyboard traps in dropdowns or modals
- [ ] Test skip link functionality (Tab to reveal, Enter to activate)
- [ ] Verify pagination links are keyboard accessible

### Screen Reader Testing (NVDA/JAWS on Windows, VoiceOver on Mac)
- [ ] Navigate by landmarks (D key) - verify only ONE main landmark
- [ ] Verify all images announce appropriate alt text
- [ ] Form fields announce their labels and purpose
- [ ] Mega menu state changes are announced
- [ ] Breadcrumbs announce correctly
- [ ] Links announce their destination
- [ ] Page title is announced on load

### Visual/Cognitive Testing  
- [ ] Zoom to 200% - verify no content loss or horizontal scrolling
- [ ] Verify information is not conveyed by color alone
- [ ] Check color contrast with browser DevTools
- [ ] Verify focus order matches visual layout
- [ ] Test with Windows High Contrast Mode

### Mobile Accessibility (TalkBack/VoiceOver)
- [ ] Hamburger menu is accessible
- [ ] Touch targets are minimum 24x24px
- [ ] All functionality available via touch
- [ ] Test landscape and portrait orientations

---

## Remediation Priority

### Must Fix Before Deployment (Critical/Serious)
1. Change `<main class="news-main-content">` to `<div>` in news templates
2. Add alt text to USA banner icons
3. Add visible focus indicators to navigation links
4. Add visible label or placeholder to keyword search

### Should Fix (Moderate)
5. Verify and fix any color contrast failures
6. Ensure touch targets meet 24x24px minimum
7. Add aria-controls to mega menu buttons

### Nice to Have (Minor)
8. Improve placeholder text
9. Review footer semantic structure
10. Consider additional skip links

---

## Fixes Applied (January 14, 2026)

### Critical Fixes
1. ✅ **Multiple main landmarks** - Changed `<main class="news-main-content">` to `<div role="region">` in `news/list.html` and `news/single.html`

### Serious Fixes  
2. ✅ **Missing alt text** - Added `alt="Dot gov icon"` and `alt="Lock icon"` to USA banner icons
3. ✅ **Focus indicators** - Added gold outline focus styles for all navigation links and interactive elements
4. ✅ **Keyword search label** - Added `visually-hidden` label and improved placeholder text
5. ✅ **Pagination accessibility** - Added aria-labels to pagination links

---

## Testing Tools Used

- Manual HTML/CSS code review
- curl for HTML output inspection
- WCAG 2.2 AA criteria checklist

## Recommended Tools for Ongoing Testing

1. **axe DevTools** (browser extension) - Automated WCAG testing
2. **WAVE** (browser extension) - Visual accessibility checker
3. **pa11y-ci** - CI/CD accessibility testing
4. **NVDA** (Windows) - Free screen reader
5. **VoiceOver** (Mac) - Built-in screen reader
6. **Colour Contrast Analyser** - Manual contrast checking

---

## Appendix: Government Accessibility Resources

- [Section508.gov](https://www.section508.gov/) - Official U.S. Government accessibility portal
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [GSA Section 508 Testing](https://www.section508.gov/test/)
- [DHS Trusted Tester Program](https://www.dhs.gov/trusted-tester)
