# Treasury Site UX & Accessibility Tests

Playwright test suite for testing the Treasury Home website against staging.

## Quick Start

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Run all tests against staging
npm run test:staging

# Run tests with UI mode (interactive)
npm run test:ui

# Run tests in headed mode (see browser)
npm run test:headed

# Run tests against local Hugo server
npm run test:local
```

## Test Structure

| File | Coverage |
|------|----------|
| `1-visual-layout.spec.ts` | Page loads, broken images, responsive design, footer |
| `2-navigation.spec.ts` | Skip links, menus, breadcrumbs, internal/external links |
| `3-keyboard-accessibility.spec.ts` | Focus indicators, tab order, keyboard traps, form navigation |
| `4-news-search.spec.ts` | Search filters, results display, pagination, reset |
| `5-news-list.spec.ts` | Inline filters, date range, keyword search, pagination |
| `6-csp-compliance.spec.ts` | CSP violations, inline handlers, external resources |
| `7-accessibility-axe.spec.ts` | WCAG 2.2 AA automated checks via axe-core |
| `8-performance.spec.ts` | Load times, layout stability, image loading |
| `9-link-validation.spec.ts` | Mega menu and homepage link validation, no old treasury.gov redirects |

## Test Pages

Tests run against these pages on staging (`https://home-staging.awsdev.treasury.gov`):

1. **Homepage**: `/`
2. **Press Releases**: `/news/press-releases/`
3. **Advanced Search**: `/news/search/`
4. **All News**: `/news/all/`
5. **404 Page**: `/this-page-does-not-exist/`

## Running Specific Tests

```bash
# Run only visual tests
npx playwright test 1-visual-layout

# Run only accessibility tests
npx playwright test 7-accessibility-axe

# Run only CSP tests
npx playwright test 6-csp-compliance

# Run tests for a specific browser
npx playwright test --project=chromium-desktop

# Run tests for mobile only
npx playwright test --project=mobile-chrome
```

## Browser Coverage

Tests run across multiple browsers/viewports:

- **Desktop**: Chrome, Firefox, Safari (1200×800)
- **Tablet**: iPad Pro (768×1024)
- **Mobile**: Pixel 5, iPhone 12 (375×667)

## Viewing Reports

After running tests:

```bash
# Open HTML report
npm run test:report
```

Reports include:
- Test results with pass/fail status
- Screenshots on failure
- Video recordings on retry
- Trace files for debugging

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Target site URL | `https://home-staging.awsdev.treasury.gov` |

## Continuous Integration

For CI environments:

```bash
# Run tests in CI mode (retries, single worker)
CI=true npm test
```

## Adding New Tests

1. Create a new `.spec.ts` file in the `tests/` directory
2. Import fixtures: `import { test, expect, TEST_PAGES, waitForPageReady } from './fixtures'`
3. Use test pages from `TEST_PAGES` constant
4. Use `waitForPageReady(page)` after navigation

## Debugging Failed Tests

```bash
# Run in debug mode (pauses on failure)
npm run test:debug

# Run with trace viewer
npx playwright test --trace on
npx playwright show-trace trace.zip
```

## CSP Testing Notes

The site enforces strict Content Security Policy. Tests verify:
- No inline `<script>` tags (except JSON-LD)
- No inline event handlers (`onclick`, `onsubmit`, etc.)
- All scripts from same origin
- No console CSP violation errors

## Accessibility Testing Notes

Tests use [axe-core](https://github.com/dequelabs/axe-core) for automated WCAG 2.2 AA checks.

Manual testing is still recommended for:
- Screen reader compatibility
- Complex keyboard interactions
- Color contrast in dynamic states
- Focus management in modals/dialogs
