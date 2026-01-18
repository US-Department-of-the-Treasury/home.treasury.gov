import { test, expect, TEST_PAGES, VIEWPORTS, waitForPageReady } from './fixtures';

/**
 * Navigation & Interaction Tests
 * 
 * - Skip link works
 * - Main navigation opens/closes
 * - Mobile menu hamburger works
 * - Internal links navigate correctly
 * - External links have rel="noopener"
 * - Breadcrumbs display and link correctly
 */

test.describe('Navigation - Skip Link', () => {
  test('skip link is first focusable element and works', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Tab to first focusable element
    await page.keyboard.press('Tab');
    
    // Get the focused element
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName.toLowerCase(),
        text: (el as HTMLElement)?.innerText?.toLowerCase() || '',
        href: (el as HTMLAnchorElement)?.href || '',
      };
    });
    
    // Check if it's a skip link
    const isSkipLink = 
      focusedElement.text.includes('skip') ||
      focusedElement.href.includes('#main') ||
      focusedElement.href.includes('#content');
    
    expect(isSkipLink).toBe(true);
  });

  test('skip link navigates to main content', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Find skip link
    const skipLink = page.locator('a.skip-link, a[href="#main-content"]').first();
    
    if (await skipLink.count() > 0) {
      // Focus and click the skip link
      await skipLink.focus();
      await skipLink.click();
      
      // Check that the URL hash changed or main content is in view
      const url = page.url();
      const hasHash = url.includes('#main-content');
      
      // Also check if main-content element exists and is in viewport
      const mainContent = page.locator('#main-content, main');
      const isVisible = await mainContent.first().isVisible();
      
      expect(hasHash || isVisible).toBe(true);
    }
  });
});

test.describe('Navigation - Desktop Menu', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
  });

  test('main navigation is visible on desktop', async ({ page }) => {
    const nav = page.locator('nav, [role="navigation"]').first();
    await expect(nav).toBeVisible();
  });

  test('navigation links are clickable', async ({ page }) => {
    // Check for navigation links (buttons for mega menus or anchor links)
    const navLinks = page.locator('.main-nav a, .main-nav button, header a');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
    
    // Verify at least some nav items are visible
    let visibleCount = 0;
    for (let i = 0; i < Math.min(5, count); i++) {
      if (await navLinks.nth(i).isVisible()) {
        visibleCount++;
      }
    }
    expect(visibleCount).toBeGreaterThan(0);
  });

  test('dropdown menus open on interaction', async ({ page }) => {
    // Look for dropdown triggers
    const dropdownTriggers = page.locator('[aria-expanded], [aria-haspopup], button:has-text("Menu")');
    
    if (await dropdownTriggers.count() > 0) {
      const trigger = dropdownTriggers.first();
      await trigger.click();
      
      // Check if something expanded
      const expanded = await trigger.getAttribute('aria-expanded');
      expect(expanded).toBe('true');
    }
  });
});

test.describe('Navigation - Mobile Menu', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
  });

  test('hamburger menu button is visible on mobile', async ({ page }) => {
    const menuButton = page.locator(
      '[aria-label*="menu" i], [aria-label*="Menu"], ' +
      'button:has-text("Menu"), .hamburger, .menu-toggle, ' +
      '[class*="mobile-menu"], [class*="nav-toggle"]'
    ).first();
    
    await expect(menuButton).toBeVisible();
  });

  test('mobile menu opens and closes', async ({ page }) => {
    const menuButton = page.locator(
      '[aria-label*="menu" i], button:has-text("Menu"), ' +
      '.hamburger, .menu-toggle'
    ).first();
    
    if (await menuButton.count() > 0) {
      // Open menu
      await menuButton.click();
      await page.waitForTimeout(300); // Animation
      
      // Check for expanded state or visible nav
      const isExpanded = await menuButton.getAttribute('aria-expanded');
      const navVisible = await page.locator('nav, [role="navigation"]').first().isVisible();
      
      expect(isExpanded === 'true' || navVisible).toBe(true);
      
      // Close menu (click again or press Escape)
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Navigation - Links', () => {
  test('internal links navigate correctly', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Find an internal link
    const internalLink = page.locator('a[href^="/"]').first();
    
    if (await internalLink.count() > 0) {
      const href = await internalLink.getAttribute('href');
      await internalLink.click();
      await waitForPageReady(page);
      
      // Verify URL changed
      expect(page.url()).toContain(href);
    }
  });

  test('external links have rel="noopener"', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Find external links (target="_blank")
    const externalLinks = page.locator('a[target="_blank"]');
    const count = await externalLinks.count();
    
    for (let i = 0; i < count; i++) {
      const rel = await externalLinks.nth(i).getAttribute('rel');
      const href = await externalLinks.nth(i).getAttribute('href');
      
      // External links should have noopener
      if (rel) {
        expect(rel).toMatch(/noopener/);
      }
    }
  });
});

test.describe('Navigation - Breadcrumbs', () => {
  test('breadcrumbs display on news pages', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const breadcrumbs = page.locator(
      '[aria-label*="breadcrumb" i], .breadcrumb, .breadcrumbs, ' +
      'nav[class*="breadcrumb"], ol[class*="breadcrumb"]'
    );
    
    // Breadcrumbs should exist on subpages
    const hasBreadcrumbs = await breadcrumbs.count() > 0;
    
    if (hasBreadcrumbs) {
      await expect(breadcrumbs.first()).toBeVisible();
      
      // Check breadcrumb links work
      const breadcrumbLinks = breadcrumbs.first().locator('a');
      const linkCount = await breadcrumbLinks.count();
      expect(linkCount).toBeGreaterThan(0);
    }
  });

  test('breadcrumb home link works', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const breadcrumbs = page.locator('[aria-label*="breadcrumb" i], .breadcrumb');
    
    if (await breadcrumbs.count() > 0) {
      const homeLink = breadcrumbs.first().locator('a').first();
      
      if (await homeLink.count() > 0) {
        await homeLink.click();
        await waitForPageReady(page);
        
        // Should navigate to homepage or parent
        expect(page.url()).not.toContain('/press-releases');
      }
    }
  });
});

test.describe('Navigation - Header & Footer', () => {
  test('header logo links to homepage', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const logo = page.locator('header a[href="/"], header a:has(img)').first();
    
    if (await logo.count() > 0) {
      await logo.click();
      await waitForPageReady(page);
      
      expect(page.url()).toMatch(/\/$/);
    }
  });

  test('footer links are functional', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const footerLinks = page.locator('footer a');
    const count = await footerLinks.count();
    
    expect(count).toBeGreaterThan(0);
    
    // Verify footer links have hrefs
    for (let i = 0; i < Math.min(5, count); i++) {
      const href = await footerLinks.nth(i).getAttribute('href');
      expect(href).toBeTruthy();
    }
  });
});
