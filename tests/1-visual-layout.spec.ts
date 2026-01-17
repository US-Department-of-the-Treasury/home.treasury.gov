import { test, expect, TEST_PAGES, VIEWPORTS, collectConsoleErrors, findBrokenImages, hasHorizontalScroll, waitForPageReady } from './fixtures';

/**
 * Visual & Layout Tests
 * 
 * Tests for each page:
 * - Page loads without JavaScript errors
 * - No broken images or missing assets
 * - Layout is responsive (1200px, 768px, 375px)
 * - Text is readable
 * - No horizontal scrolling on mobile
 * - Footer displays correctly
 */

test.describe('Visual & Layout - Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
  });

  test('loads without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.reload();
    await waitForPageReady(page);
    
    // Filter out non-critical errors (like favicon 404s)
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('404') &&
      !e.includes('Failed to load resource')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('has no broken images', async ({ page }) => {
    const brokenImages = await findBrokenImages(page);
    expect(brokenImages).toHaveLength(0);
  });

  test('is responsive at desktop (1200px)', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await expect(page.locator('body')).toBeVisible();
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test('is responsive at tablet (768px)', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await expect(page.locator('body')).toBeVisible();
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test('is responsive at mobile (375px)', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await expect(page.locator('body')).toBeVisible();
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test('footer displays correctly', async ({ page }) => {
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
    
    // Check footer has content
    const footerText = await footer.textContent();
    expect(footerText?.length).toBeGreaterThan(0);
  });

  test('main content area exists', async ({ page }) => {
    const main = page.locator('main, [role="main"], #main-content');
    await expect(main.first()).toBeVisible();
  });
});

test.describe('Visual & Layout - Press Releases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
  });

  test('loads without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.reload();
    await waitForPageReady(page);
    
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('404')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('has no broken images', async ({ page }) => {
    const brokenImages = await findBrokenImages(page);
    expect(brokenImages).toHaveLength(0);
  });

  test('no horizontal scroll at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test('news items display in a list', async ({ page }) => {
    const newsItems = page.locator('article, .news-item, [class*="press-release"]');
    const count = await newsItems.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Visual & Layout - Advanced Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await page.waitForLoadState('domcontentloaded');
  });

  test('loads without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('404')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('search form is visible', async ({ page }) => {
    // Advanced search uses div-based form, not <form> element
    const searchForm = page.locator('#advanced-search-form, .advanced-search-form');
    await expect(searchForm.first()).toBeVisible({ timeout: 10000 });
  });

  test('no horizontal scroll at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    expect(await hasHorizontalScroll(page)).toBe(false);
  });
});

test.describe('Visual & Layout - All News', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.allNews);
    await waitForPageReady(page);
  });

  test('loads without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.reload();
    await waitForPageReady(page);
    
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('404')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('no horizontal scroll at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    expect(await hasHorizontalScroll(page)).toBe(false);
  });
});

test.describe('Visual & Layout - 404 Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.notFound);
    await waitForPageReady(page);
  });

  test('displays 404 content', async ({ page }) => {
    // Check for 404-related text
    const pageContent = await page.textContent('body');
    const has404Content = 
      pageContent?.includes('404') ||
      pageContent?.includes('not found') ||
      pageContent?.includes('Not Found') ||
      pageContent?.includes("doesn't exist") ||
      pageContent?.includes('page cannot be found');
    
    expect(has404Content).toBe(true);
  });

  test('no horizontal scroll at mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test('has navigation back to homepage', async ({ page }) => {
    const homeLink = page.locator('a[href="/"], a[href*="home"]').first();
    await expect(homeLink).toBeVisible();
  });
});

test.describe('Visual & Layout - Single Article', () => {
  test('article page loads and displays content', async ({ page }) => {
    // Go directly to a known press release article
    await page.goto('/news/press-releases/');
    await page.waitForLoadState('domcontentloaded');
    
    // Get first article link href
    const firstArticleLink = page.locator('.news-article-item a, article a, a[href*="/news/press-releases/"]').first();
    const href = await firstArticleLink.getAttribute('href');
    
    if (href) {
      // Navigate directly to avoid click issues
      await page.goto(href);
      await page.waitForLoadState('domcontentloaded');
      
      // Verify article content exists
      const articleContent = page.locator('main, article, .content');
      await expect(articleContent.first()).toBeVisible();
      
      // Check for heading
      const heading = page.locator('h1');
      await expect(heading.first()).toBeVisible();
    }
  });
});
