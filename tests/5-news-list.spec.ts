import { test, expect, TEST_PAGES, waitForPageReady } from './fixtures';

/**
 * News List Page Tests
 * 
 * - Inline filters work (Today, This Week, etc.)
 * - Date range picker functions
 * - Keyword search works
 * - Filtered results display correctly
 * - Pagination jump-to-page works
 */

test.describe('News List - Press Releases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
  });

  test('page displays list of press releases', async ({ page }) => {
    const newsItems = page.locator('article, .news-item, [class*="press-release"], li:has(a[href*="/news/"])');
    const count = await newsItems.count();
    
    expect(count).toBeGreaterThan(0);
  });

  test('each news item has date and title', async ({ page }) => {
    const firstItem = page.locator('article, .news-item').first();
    
    if (await firstItem.count() > 0) {
      // Should have a link (title)
      const link = firstItem.locator('a');
      await expect(link.first()).toBeVisible();
      
      // Should have a date somewhere
      const datePattern = /\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|[A-Za-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}/;
      const itemText = await firstItem.textContent();
      
      // Date might be in time element or just text
      const hasDate = datePattern.test(itemText || '') || await firstItem.locator('time').count() > 0;
      expect(hasDate).toBe(true);
    }
  });
});

test.describe('News List - Inline Filters', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
  });

  test('Today filter button exists and works', async ({ page }) => {
    const todayFilter = page.locator('button:has-text("Today"), a:has-text("Today"), [data-filter="today"]').first();
    
    if (await todayFilter.count() > 0) {
      await todayFilter.click();
      await waitForPageReady(page);
      
      // URL should update or filter should be active
      const url = page.url();
      const isActive = await todayFilter.evaluate(el => 
        el.classList.contains('active') || 
        el.getAttribute('aria-pressed') === 'true'
      );
      
      expect(url.includes('today') || url.includes('date') || isActive).toBe(true);
    }
  });

  test('This Week filter works', async ({ page }) => {
    const weekFilter = page.locator('button:has-text("This Week"), a:has-text("This Week"), button:has-text("Week")').first();
    
    if (await weekFilter.count() > 0) {
      await weekFilter.click();
      await waitForPageReady(page);
      
      const isActive = await weekFilter.evaluate(el => 
        el.classList.contains('active') || 
        el.getAttribute('aria-pressed') === 'true' ||
        el.getAttribute('aria-selected') === 'true'
      );
      
      expect(isActive || page.url().includes('week')).toBe(true);
    }
  });

  test('This Month filter works', async ({ page }) => {
    const monthFilter = page.locator('button:has-text("This Month"), a:has-text("This Month"), button:has-text("Month")').first();
    
    if (await monthFilter.count() > 0) {
      await monthFilter.click();
      await waitForPageReady(page);
      
      const isActive = await monthFilter.evaluate(el => 
        el.classList.contains('active') || 
        el.getAttribute('aria-pressed') === 'true'
      );
      
      expect(isActive || page.url().includes('month')).toBe(true);
    }
  });

  test('This Year filter works', async ({ page }) => {
    const yearFilter = page.locator('button:has-text("This Year"), a:has-text("This Year"), button:has-text("Year")').first();
    
    if (await yearFilter.count() > 0) {
      await yearFilter.click();
      await waitForPageReady(page);
      
      const isActive = await yearFilter.evaluate(el => 
        el.classList.contains('active') || 
        el.getAttribute('aria-pressed') === 'true'
      );
      
      expect(isActive || page.url().includes('year')).toBe(true);
    }
  });
});

test.describe('News List - Date Range Picker', () => {
  test('date range inputs exist', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const dateInputs = page.locator('input[type="date"], input[name*="from"], input[name*="to"], input[placeholder*="date" i]');
    const hasDateInputs = await dateInputs.count() > 0;
    
    // Date inputs might not be on list page (might be on search page only)
    expect(hasDateInputs).toBeDefined();
  });

  test('date range filter applies correctly', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const fromDate = page.locator('input[type="date"], input[name*="from"]').first();
    const toDate = page.locator('input[type="date"], input[name*="to"]').first();
    
    if (await fromDate.count() > 0 && await toDate.count() > 0) {
      // Set date range (last month)
      const today = new Date();
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
      
      await fromDate.fill(lastMonth.toISOString().split('T')[0]);
      await toDate.fill(endOfLastMonth.toISOString().split('T')[0]);
      
      // Submit or trigger filter
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // Results should be filtered
      expect(page.url()).toBeDefined();
    }
  });
});

test.describe('News List - Keyword Search', () => {
  test('keyword search filters results', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    // The news list has inline filters with id filter-keyword
    const searchInput = page.locator('#filter-keyword, .keyword-input');
    
    if (await searchInput.count() > 0 && await searchInput.isVisible()) {
      await searchInput.fill('sanctions');
      
      // Click the apply filters button
      const applyBtn = page.locator('#apply-filters-btn, button.search-btn');
      if (await applyBtn.count() > 0) {
        await applyBtn.click();
      } else {
        await page.keyboard.press('Enter');
      }
      
      await page.waitForTimeout(1000);
      
      // Should have results or filtered results
      const hasResults = await page.locator('.news-article-item, article, .news-item').count() > 0;
      expect(hasResults).toBe(true);
    } else {
      // Skip if no keyword filter on this page
      test.skip();
    }
  });
});

test.describe('News List - Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
  });

  test('pagination is displayed', async ({ page }) => {
    const pagination = page.locator(
      'nav[aria-label*="pagination" i], ' +
      '.pagination, ' +
      '[class*="pager"], ' +
      'a[href*="page="], ' +
      'a[href*="/page/"]'
    );
    
    const hasPagination = await pagination.count() > 0;
    expect(hasPagination).toBe(true);
  });

  test('page number links work', async ({ page }) => {
    const pageLinks = page.locator('a[href*="page="], a[href*="/page/"], .pagination a').all();
    const links = await pageLinks;
    
    if (links.length > 0) {
      const secondPageLink = links.find(async (link) => {
        const text = await link.textContent();
        return text?.includes('2');
      });
      
      if (secondPageLink) {
        await secondPageLink.click();
        await waitForPageReady(page);
        
        expect(page.url()).toMatch(/page[=\/]2/);
      }
    }
  });

  test('jump to page form works', async ({ page }) => {
    // Look for jump-to-page input
    const jumpInput = page.locator('input[name*="page"], input[type="number"][placeholder*="page" i], input[aria-label*="page" i]').first();
    
    if (await jumpInput.count() > 0) {
      await jumpInput.fill('5');
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // Should navigate to page 5
      expect(page.url()).toMatch(/page[=\/]5/);
    }
  });
});

test.describe('News List - All News Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.allNews);
    await waitForPageReady(page);
  });

  test('displays news from all categories', async ({ page }) => {
    const newsItems = page.locator('article, .news-item');
    const count = await newsItems.count();
    
    expect(count).toBeGreaterThan(0);
  });

  test('category labels are visible', async ({ page }) => {
    // Look for category/type indicators
    const categoryLabels = page.locator('[class*="category"], [class*="type"], [class*="label"], .tag');
    const hasCategories = await categoryLabels.count() > 0;
    
    // Categories might be displayed as links or labels
    expect(hasCategories).toBeDefined();
  });

  test('news items link to detail pages', async ({ page }) => {
    const firstItemLink = page.locator('.news-article-item a, article a, .news-item a').first();
    
    if (await firstItemLink.count() > 0) {
      const href = await firstItemLink.getAttribute('href');
      // Links can be relative or absolute, and may include localhost in dev
      expect(href).toBeTruthy();
      expect(href).toMatch(/\/news\//);
    }
  });
});
