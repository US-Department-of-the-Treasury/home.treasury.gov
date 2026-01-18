import { test, expect } from '@playwright/test';

/**
 * Section Layout Tests
 * Verifies that all section index pages have consistent layout:
 * - Breadcrumbs above content
 * - Two-column layout with sidebar on left
 * - Proper heading structure
 */

const sectionPages = [
  { name: 'About Treasury', url: '/about/' },
  { name: 'General Information', url: '/about/general-information/' },
  { name: 'Careers at Treasury', url: '/about/careers-at-treasury/' },
  { name: 'History', url: '/about/history/' },
  { name: 'Offices', url: '/about/offices/' },
  { name: 'Budget & Performance', url: '/about/budget-financial-reporting-planning-and-performance/' },
  { name: 'Policy Issues', url: '/policy-issues/' },
  { name: 'Tax Policy', url: '/policy-issues/tax-policy/' },
  { name: 'Economic Policy', url: '/policy-issues/economic-policy/' },
  { name: 'Financing the Government', url: '/policy-issues/financing-the-government/' },
  { name: 'Data', url: '/data/' },
  { name: 'Services', url: '/services/' },
];

const contentPages = [
  { name: 'Officials', url: '/about/general-information/officials/' },
  { name: 'Organizational Chart', url: '/about/general-information/organizational-chart/' },
  { name: 'Role of the Treasury', url: '/about/general-information/role-of-the-treasury/' },
  { name: 'Orders and Directives', url: '/about/general-information/orders-and-directives/' },
  { name: 'The Treasury Building', url: '/about/history/the-treasury-building/' },
];

test.describe('Section Layout - Structure', () => {
  for (const page of sectionPages) {
    test(`${page.name} has correct layout structure`, async ({ page: browserPage }) => {
      await browserPage.goto(page.url);
      await browserPage.waitForLoadState('domcontentloaded');

      // Should have breadcrumbs
      const breadcrumbs = browserPage.locator('.breadcrumbs');
      await expect(breadcrumbs).toBeVisible();

      // Should have content-page-layout (two-column grid)
      const layout = browserPage.locator('.content-page-layout');
      await expect(layout).toBeVisible();

      // Should have section-sidebar
      const sidebar = browserPage.locator('.section-sidebar');
      await expect(sidebar).toBeVisible();

      // Should have sidebar heading
      const sidebarHeading = browserPage.locator('.sidebar-heading');
      await expect(sidebarHeading).toBeVisible();

      // Should have main content area
      const mainContent = browserPage.locator('.content-page-main');
      await expect(mainContent).toBeVisible();

      // Should have H1 title
      const h1 = browserPage.locator('.content-page-main h1');
      await expect(h1).toBeVisible();

      // Should have title underline
      const titleUnderline = browserPage.locator('.title-underline');
      await expect(titleUnderline).toBeVisible();
    });
  }
});

test.describe('Content Page Layout - Structure', () => {
  for (const page of contentPages) {
    test(`${page.name} has correct layout structure`, async ({ page: browserPage }) => {
      await browserPage.goto(page.url);
      await browserPage.waitForLoadState('domcontentloaded');

      // Should have breadcrumbs
      const breadcrumbs = browserPage.locator('.breadcrumbs');
      await expect(breadcrumbs).toBeVisible();

      // Should have content-page-layout (two-column grid)
      const layout = browserPage.locator('.content-page-layout');
      await expect(layout).toBeVisible();

      // Should have section-sidebar
      const sidebar = browserPage.locator('.section-sidebar');
      await expect(sidebar).toBeVisible();

      // Should have sidebar heading
      const sidebarHeading = browserPage.locator('.sidebar-heading');
      await expect(sidebarHeading).toBeVisible();

      // Should have main content area
      const mainContent = browserPage.locator('.content-page-main');
      await expect(mainContent).toBeVisible();

      // Should have H1 title
      const h1 = browserPage.locator('.content-page-main h1');
      await expect(h1).toBeVisible();
    });
  }
});

test.describe('Section Layout - Sidebar Navigation', () => {
  test('About Treasury sidebar shows child sections', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const sidebarLinks = page.locator('.section-nav ul li a');
    const linkCount = await sidebarLinks.count();

    // Should have at least 5 child sections (General Info, Careers, History, Offices, Budget)
    expect(linkCount).toBeGreaterThanOrEqual(5);
  });

  test('Subsection has back link to parent', async ({ page }) => {
    await page.goto('/about/general-information/');
    await page.waitForLoadState('domcontentloaded');

    // Should have "Back to About Treasury" link
    const backLink = page.locator('.section-nav a:has-text("Back to")');
    await expect(backLink).toBeVisible();
  });

  test('Content page sidebar shows sibling pages', async ({ page }) => {
    await page.goto('/about/general-information/officials/');
    await page.waitForLoadState('domcontentloaded');

    const sidebarLinks = page.locator('.section-nav ul li a');
    const linkCount = await sidebarLinks.count();

    // Should have siblings (Orders and Directives, Org Chart, Role of Treasury, etc.)
    expect(linkCount).toBeGreaterThanOrEqual(3);
  });

  test('Active page is highlighted in sidebar', async ({ page }) => {
    await page.goto('/about/general-information/officials/');
    await page.waitForLoadState('domcontentloaded');

    // Should have an active link
    const activeLink = page.locator('.section-nav a.active');
    await expect(activeLink).toBeVisible();
    
    // Active link should contain "Officials"
    await expect(activeLink).toContainText('Officials');
  });
});

test.describe('Section Layout - Breadcrumbs', () => {
  test('Breadcrumbs show correct hierarchy for section page', async ({ page }) => {
    await page.goto('/about/general-information/');
    await page.waitForLoadState('domcontentloaded');

    const breadcrumbs = page.locator('.breadcrumbs-list');
    
    // Should have HOME link
    await expect(breadcrumbs.locator('a:has-text("HOME")')).toBeVisible();
    
    // Should have About Treasury link
    await expect(breadcrumbs.locator('a:has-text("ABOUT TREASURY")')).toBeVisible();
    
    // Should have current page (General Information) as non-link
    await expect(breadcrumbs.locator('span:has-text("GENERAL INFORMATION")')).toBeVisible();
  });

  test('Breadcrumbs show correct hierarchy for content page', async ({ page }) => {
    await page.goto('/about/general-information/officials/');
    await page.waitForLoadState('domcontentloaded');

    const breadcrumbs = page.locator('.breadcrumbs-list');
    
    // Should have HOME link
    await expect(breadcrumbs.locator('a:has-text("HOME")')).toBeVisible();
    
    // Should have About Treasury link
    await expect(breadcrumbs.locator('a:has-text("ABOUT TREASURY")')).toBeVisible();
    
    // Should have General Information link
    await expect(breadcrumbs.locator('a:has-text("GENERAL INFORMATION")')).toBeVisible();
    
    // Should have current page as non-link
    await expect(breadcrumbs.locator('span:has-text("OFFICIALS")')).toBeVisible();
  });
});

test.describe('Section Layout - Content Cards', () => {
  test('Section page shows content cards for child pages', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const contentCards = page.locator('.content-cards .content-card');
    const cardCount = await contentCards.count();

    // Should have content cards for child sections
    expect(cardCount).toBeGreaterThanOrEqual(5);
  });

  test('Content cards are links to child pages', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const firstCard = page.locator('.content-cards .content-card').first();
    const href = await firstCard.getAttribute('href');

    // Should have href attribute
    expect(href).toBeTruthy();
    expect(href).toContain('/about/');
  });
});

test.describe('Section Layout - Responsive', () => {
  test('Layout is responsive at mobile width', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    // Page should load without errors
    await expect(page.locator('h1')).toBeVisible();
    
    // Content should still be accessible
    await expect(page.locator('.content-page-main')).toBeVisible();
  });

  test('Layout is responsive at tablet width', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    // Page should load without errors
    await expect(page.locator('h1')).toBeVisible();
    
    // Sidebar should still be visible at tablet
    await expect(page.locator('.section-sidebar')).toBeVisible();
  });
});

test.describe('Section Layout - Accessibility', () => {
  test('Sidebar has proper aria-label', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const sidebar = page.locator('.section-sidebar');
    const ariaLabel = await sidebar.getAttribute('aria-label');

    expect(ariaLabel).toBe('Section navigation');
  });

  test('Breadcrumbs have proper aria-label', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const breadcrumbNav = page.locator('.breadcrumbs nav');
    const ariaLabel = await breadcrumbNav.getAttribute('aria-label');

    expect(ariaLabel).toBe('Breadcrumb');
  });

  test('Current page in breadcrumbs has aria-current', async ({ page }) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');

    const currentPage = page.locator('.breadcrumbs-list span[aria-current="page"]');
    await expect(currentPage).toBeVisible();
  });
});
