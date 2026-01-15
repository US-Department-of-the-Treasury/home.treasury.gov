# Section 508 Accessibility Testing

This document outlines how to test the Treasury Hugo site for Section 508 / WCAG 2.1 AA compliance.

## Quick Start

### Option 1: Automated Testing with pa11y

```bash
# Fix npm permissions if needed
sudo chown -R $(whoami) ~/.npm

# Install pa11y
npm install -g pa11y pa11y-ci

# Run tests (requires Hugo server running)
make serve &  # Start server in background
make test-508 # Run accessibility tests
```

### Option 2: Browser-Based Testing

1. **WAVE Extension** (Recommended)
   - Install: [WAVE for Chrome](https://chrome.google.com/webstore/detail/wave-evaluation-tool)
   - Visit `http://localhost:1313/news/press-releases/`
   - Click the WAVE icon to scan

2. **axe DevTools**
   - Install: [axe DevTools for Chrome](https://chrome.google.com/webstore/detail/axe-devtools)
   - Open DevTools (F12) → axe DevTools tab
   - Click "Scan ALL of my page"

3. **ANDI Bookmarklet** (Government standard)
   - Visit: https://www.ssa.gov/accessibility/andi/help/install.html
   - Drag bookmarklet to bookmarks bar
   - Click while viewing any page

---

## WCAG 2.1 AA Requirements

Section 508 requires WCAG 2.1 Level AA compliance. Key areas:

### 1. Perceivable

| Requirement | How to Test |
|-------------|-------------|
| **Images have alt text** | Check `<img>` tags have meaningful `alt` attributes |
| **Color contrast 4.5:1** | Use WAVE or axe to check text contrast |
| **No color-only info** | Ensure meaning isn't conveyed by color alone |
| **Captions for video** | N/A for this site |

### 2. Operable

| Requirement | How to Test |
|-------------|-------------|
| **Keyboard navigation** | Tab through page, ensure all interactive elements focusable |
| **Skip navigation** | Check for "Skip to main content" link |
| **Focus visible** | Tab through - focus indicator should be visible |
| **No keyboard traps** | Ensure you can Tab out of any element |

### 3. Understandable

| Requirement | How to Test |
|-------------|-------------|
| **Language defined** | Check `<html lang="en">` |
| **Form labels** | All inputs have associated `<label>` |
| **Error identification** | Form errors clearly described |

### 4. Robust

| Requirement | How to Test |
|-------------|-------------|
| **Valid HTML** | Run through W3C validator |
| **ARIA used correctly** | Check ARIA roles match element purpose |

---

## Pages to Test

| URL | Description |
|-----|-------------|
| `/news/press-releases/` | List page with pagination |
| `/news/press-releases/sb0357/` | Individual article |
| `/news/press-releases/?page=1` | Pagination page 2 |

---

## Common Issues & Fixes

### Missing Alt Text

```html
<!-- Bad -->
<img src="seal.svg">

<!-- Good -->
<img src="seal.svg" alt="U.S. Department of the Treasury Seal">

<!-- Decorative (no alt needed) -->
<img src="decoration.svg" alt="" aria-hidden="true">
```

### Color Contrast

Ensure text has 4.5:1 contrast ratio against background:

```css
/* Check these combinations */
--treasury-navy: #112e51;  /* on white = 12.6:1 ✓ */
color: rgba(255,255,255,0.7);  /* on #112e51 = 7.8:1 ✓ */
color: rgba(255,255,255,0.5);  /* on #112e51 = 4.2:1 ✗ */
```

### Form Labels

```html
<!-- Bad -->
<input type="text" name="search">

<!-- Good -->
<label for="search">Search</label>
<input type="text" id="search" name="search">

<!-- Or with aria-label -->
<input type="text" name="search" aria-label="Search by keyword">
```

### Skip Navigation

Already implemented in `baseof.html`:
```html
<a href="#main-content" class="skip-link">Skip to main content</a>
```

### Keyboard Focus

```css
/* Ensure focus is visible */
a:focus, button:focus, input:focus {
  outline: 2px solid var(--treasury-gold);
  outline-offset: 2px;
}
```

---

## Automated Test Configuration

### pa11y-ci Configuration

File: `.pa11yci.json`

```json
{
  "defaults": {
    "standard": "WCAG2AA",
    "timeout": 30000
  },
  "urls": [
    "http://localhost:1313/news/press-releases/",
    "http://localhost:1313/news/press-releases/sb0357/"
  ]
}
```

### Running Tests

```bash
# Full test suite
pa11y-ci

# Single page with details
pa11y http://localhost:1313/news/press-releases/ --standard WCAG2AA

# Generate HTML report
pa11y http://localhost:1313/news/press-releases/ --reporter html > report.html
```

---

## Government Resources

- [Section508.gov Testing](https://www.section508.gov/test/)
- [DHS Trusted Tester Program](https://www.dhs.gov/508-testing)
- [ANDI Tool](https://www.ssa.gov/accessibility/andi/)
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)

---

## Reporting

After testing, document:

1. **Tool used**: pa11y, WAVE, axe, ANDI
2. **Pages tested**: List all URLs
3. **Issues found**: Error type, location, WCAG criterion
4. **Remediation**: How each issue was fixed
5. **Retest results**: Confirm issues resolved
