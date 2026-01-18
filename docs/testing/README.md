# Automated UX & Accessibility Testing

This directory contains documentation and reports for automated testing of the Treasury Home website.

## Quick Start

```bash
# From project root
cd /path/to/home.treasury.gov

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install chromium

# Run all tests against staging
npm run test:staging

# Run tests against local Hugo server
npm run test:local

# View HTML report
npm run test:report
```

## Test Suites

| Suite | File | Description |
|-------|------|-------------|
| Visual & Layout | `tests/1-visual-layout.spec.ts` | Page loads, broken images, responsive design |
| Navigation | `tests/2-navigation.spec.ts` | Skip links, menus, breadcrumbs, links |
| Keyboard | `tests/3-keyboard-accessibility.spec.ts` | Focus indicators, tab order, keyboard traps |
| News Search | `tests/4-news-search.spec.ts` | Search filters, results, pagination |
| News Lists | `tests/5-news-list.spec.ts` | List pages, inline filters, date range |
| CSP Compliance | `tests/6-csp-compliance.spec.ts` | Content Security Policy validation |
| Accessibility | `tests/7-accessibility-axe.spec.ts` | WCAG 2.2 AA automated checks |
| Performance | `tests/8-performance.spec.ts` | Load times, layout shift, caching |

## Test Pages

Tests run against these URLs:

| Page | Path |
|------|------|
| Homepage | `/` |
| Press Releases | `/news/press-releases/` |
| Advanced Search | `/news/search/` |
| All News | `/news/all/` |
| 404 Page | `/this-page-does-not-exist/` |

## Running Tests

### Against Staging
```bash
npm run test:staging
# Or explicitly:
BASE_URL=https://home-staging.awsdev.treasury.gov npx playwright test
```

### Against Local Hugo Server
```bash
# Start Hugo server first
hugo server --port 1313

# In another terminal
npm run test:local
# Or explicitly:
BASE_URL=http://localhost:1313 npx playwright test
```

### Specific Test Suites
```bash
# Run only accessibility tests
npx playwright test 7-accessibility-axe

# Run only CSP tests
npx playwright test 6-csp-compliance

# Run only visual tests
npx playwright test 1-visual-layout
```

### Browser Options
```bash
# Run with visible browser
npm run test:headed

# Run with interactive UI
npm run test:ui

# Run in debug mode (pauses on failure)
npm run test:debug
```

### Specific Browsers/Devices
```bash
# Desktop Chrome only
npx playwright test --project=chromium-desktop

# Mobile Chrome
npx playwright test --project=mobile-chrome

# All mobile projects
npx playwright test --project=mobile-chrome --project=mobile-safari
```

## Browser Coverage

Tests run across multiple browsers and viewports:

| Project | Browser | Viewport |
|---------|---------|----------|
| chromium-desktop | Chrome | 1200×800 |
| firefox-desktop | Firefox | 1200×800 |
| webkit-desktop | Safari | 1200×800 |
| tablet | Safari (iPad) | 768×1024 |
| mobile-chrome | Chrome (Pixel 5) | 375×667 |
| mobile-safari | Safari (iPhone 12) | 375×667 |

## Test Reports

### HTML Report
After running tests, view the HTML report:
```bash
npm run test:report
```

### Report Location
Reports are generated in:
- `playwright-report/` - HTML report
- `test-results/` - Screenshots, videos, traces

### Archived Reports
Historical reports are stored in:
- `docs/testing/reports/` - Markdown reports with dates

## Writing New Tests

### Basic Test Structure
```typescript
import { test, expect, TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
  });

  test('does something', async ({ page }) => {
    const element = page.locator('.my-element');
    await expect(element).toBeVisible();
  });
});
```

### Available Helpers (fixtures.ts)

| Helper | Description |
|--------|-------------|
| `TEST_PAGES` | Object with page URLs |
| `VIEWPORTS` | Object with viewport sizes |
| `waitForPageReady(page)` | Wait for network idle + hydration |
| `collectConsoleErrors(page)` | Collect console error messages |
| `collectCSPViolations(page)` | Collect CSP-specific errors |
| `getFocusableElements(page)` | Count focusable elements |
| `tabThroughPage(page, n)` | Tab through page, return focus order |
| `findBrokenImages(page)` | Find images that failed to load |
| `hasHorizontalScroll(page)` | Check for horizontal overflow |

### Accessibility Testing with axe-core
```typescript
import AxeBuilder from '@axe-core/playwright';

test('should have no accessibility violations', async ({ page }) => {
  await page.goto('/my-page');
  
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  
  expect(results.violations).toHaveLength(0);
});
```

## CSP Compliance Notes

The Treasury site enforces strict Content Security Policy. Tests verify:

- ✅ No inline `<script>` tags (except JSON-LD)
- ✅ No inline event handlers (`onclick`, `onsubmit`, etc.)
- ✅ All scripts from same origin
- ✅ No CSP console errors

When adding new JavaScript, ensure it's CSP-compliant:
```html
<!-- ❌ NOT allowed -->
<button onclick="doSomething()">Click</button>
<script>console.log('inline');</script>

<!-- ✅ Allowed -->
<button id="myBtn">Click</button>
<script src="/js/my-script.js"></script>
```

## Accessibility Testing Notes

### Automated Checks
Tests use [axe-core](https://github.com/dequelabs/axe-core) for WCAG 2.2 AA compliance:
- Color contrast ratios
- Heading hierarchy
- Link text
- Form labels
- Landmark regions
- Keyboard accessibility

### Manual Testing Still Required
Automated tests cannot catch everything. Manual testing recommended for:
- Screen reader compatibility (NVDA, VoiceOver, JAWS)
- Complex keyboard interactions
- Focus management in dynamic content
- Color contrast in hover/focus states
- Cognitive accessibility

## CI/CD Integration

For continuous integration:

```bash
# Run in CI mode (retries, single worker)
CI=true npm test

# Generate JUnit report for CI
npx playwright test --reporter=junit
```

### GitHub Actions Example
```yaml
- name: Run Playwright Tests
  run: |
    npm ci
    npx playwright install chromium
    npm run test:staging
  env:
    CI: true
```

## Troubleshooting

### Tests Timeout
- Increase timeout in `playwright.config.ts`
- Check if staging site is accessible
- Verify network connectivity

### Element Not Visible
- Element may be hidden by CSS
- Check viewport size
- Use `{ force: true }` for hidden elements (not recommended)

### CSP Violations
- Check for inline scripts or handlers
- Verify all scripts are from same origin
- Check DevTools Console for specific errors

### Flaky Tests
- Add `await waitForPageReady(page)` after navigation
- Use `waitForTimeout` sparingly
- Check for race conditions in dynamic content

## File Structure

```
home.treasury.gov/
├── tests/
│   ├── fixtures.ts              # Shared helpers
│   ├── 1-visual-layout.spec.ts
│   ├── 2-navigation.spec.ts
│   ├── 3-keyboard-accessibility.spec.ts
│   ├── 4-news-search.spec.ts
│   ├── 5-news-list.spec.ts
│   ├── 6-csp-compliance.spec.ts
│   ├── 7-accessibility-axe.spec.ts
│   ├── 8-performance.spec.ts
│   └── README.md
├── docs/
│   └── testing/
│       ├── README.md            # This file
│       └── reports/
│           └── *.md             # Historical reports
├── playwright.config.ts         # Playwright configuration
├── package.json                 # npm scripts and dependencies
├── playwright-report/           # Generated HTML reports
└── test-results/                # Screenshots, videos, traces
```

## Related Documentation

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [axe-core Rules](https://dequeuniversity.com/rules/axe/)
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
- [Section 508 Standards](https://www.section508.gov/)
