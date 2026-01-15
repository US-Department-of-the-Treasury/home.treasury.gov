# Section 508 & WCAG 2.2 Level AA Accessibility Audit Report

**Audit Date:** January 14, 2026  
**Audited System:** `home.treasury.gov` Hugo site repository (local Hugo render)  
**Auditor:** accessibility-508-auditor (automated + documented manual checks)  
**Standards:** Section 508, WCAG 2.2 Level AA (automated baseline: WCAG 2.1 AA / WCAG2AA ruleset via pa11y)

---

## Executive Summary

### Automated scan result (local pages)

| Severity | Count |
|----------|-------|
| **Critical** | 0 |
| **Serious** | 0 |
| **Moderate** | 0 |
| **Minor** | 0 |

**Overall:** ✅ **No WCAG2AA errors detected on the locally-rendered pages tested** (details below).

### Important scope note (homepage `/`)

This repository’s homepage template (`themes/treasury/layouts/index.html`) **intentionally redirects to the production site** (`https://home.treasury.gov/`). As a result:

- Automated tools run against `http://localhost:1313/` will effectively scan the **production** homepage after the redirect.
- Those findings are **out of scope for remediation in this repo** unless/until the repo implements a real local homepage (i.e., removes the redirect).

---

## Automated Testing Details

### Tooling

- **pa11y-ci** (`WCAG2AA`) using repo config: `.pa11yci.json`
- **pa11y** (`WCAG2AA`) for an expanded representative URL set

### URLs tested (pa11y-ci via `.pa11yci.json`)

- `http://localhost:1313/news/press-releases/`
- `http://localhost:1313/news/press-releases/sb0357/`
- `http://localhost:1313/news/press-releases/sb0350/`

**Result:** ✅ **3/3 passed (0 errors)**

### URLs tested (expanded representative set)

- `http://localhost:1313/news/`
- `http://localhost:1313/news/press-releases/`
- `http://localhost:1313/news/press-releases/sb0357/`
- `http://localhost:1313/news/press-releases/sb0350/`
- `http://localhost:1313/news/featured-stories/`
- `http://localhost:1313/news/featured-stories/american-rescue-plan-centering-equity-in-policymaking/`
- `http://localhost:1313/offices/`
- `http://localhost:1313/topics/`
- `http://localhost:1313/tags/`
- `http://localhost:1313/document-types/`
- `http://localhost:1313/categories/`

**Result:** ✅ **All passed (0 errors)**

---

## Remediation Completed During This Audit

### Fixed: Empty heading in press release content (WCAG 1.3.1 / H42.2)

**Issue:** pa11y flagged an empty heading (`<h3></h3>`) on `http://localhost:1313/news/press-releases/sb0357/`.  
**Root cause:** Trailing empty Markdown heading (`###`) at end of the source markdown file.  
**Fix:** Removed the trailing `###`.

**File:** `content/news/press-releases/2026-01-13-sb0357.md`

**Retest:** ✅ No issues found on `/news/press-releases/sb0357/`

---

## Manual Testing Checklist (recommended for sign-off)

Automated tools do not fully validate WCAG 2.2 behaviors (especially focus visibility/obscuring and pointer target size). Before deploy, manually verify:

### Keyboard navigation
- [ ] Tab order is logical across header nav, mega menus, search, and pagination
- [ ] Focus indicator is always visible (WCAG 2.4.7, 2.4.11)
- [ ] Focus is not obscured by sticky header/overlays (WCAG 2.4.11)
- [ ] No keyboard traps; Escape closes menus/overlays where appropriate
- [ ] Skip link works and lands on meaningful main content

### Screen reader (NVDA/JAWS/VoiceOver)
- [ ] Landmarks are correct and non-duplicative (one `<main>`)
- [ ] Menu buttons announce expanded/collapsed state (`aria-expanded`)
- [ ] Search field has an accessible name and submits correctly
- [ ] Headings provide a sensible structure on list + article pages

### WCAG 2.2 target size (2.5.8)
- [ ] Primary navigation targets are at least 24x24 CSS px
- [ ] Pagination controls are at least 24x24 CSS px

---

## Notes / Follow-ups

- If/when the repo implements a real local homepage (removes the redirect), re-run this audit including `http://localhost:1313/`.
