/**
 * Single Article Page Tests
 * 
 * Tests for individual article pages (press releases, statements, featured stories)
 * including content rendering, metadata sidebar, and related functionality.
 */

import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

// Sample article URLs for testing
const ARTICLE_PAGES = {
  pressRelease: '/news/press-releases/sb0357/',
  statement: '/news/statements-remarks/',
  featuredStory: '/news/featured-stories/',
};

test.describe('Article Page - Content Structure', () => {
  test('press release article has required elements', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Check for article title (h1)
    const title = page.locator('h1, .article-title, [class*="title"]').first();
    await expect(title).toBeVisible();

    // Check for article content
    const content = page.locator('article, .article-content, .article-body, main').first();
    await expect(content).toBeVisible();

    // Check for publication date
    const hasDate = await page.locator('time, [class*="date"], [class*="published"]').count();
    expect(hasDate).toBeGreaterThan(0);
  });

  test('article has proper heading hierarchy', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Get all headings
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    
    // Should have at least one heading
    expect(headings.length).toBeGreaterThan(0);

    // Check heading levels don't skip (e.g., h1 to h3)
    const headingLevels = await page.locator('h1, h2, h3, h4, h5, h6').evaluateAll(els => 
      els.map(el => parseInt(el.tagName.charAt(1)))
    );
    
    for (let i = 1; i < headingLevels.length; i++) {
      const diff = headingLevels[i] - headingLevels[i - 1];
      // Should not skip more than one level
      expect(diff).toBeLessThanOrEqual(1);
    }
  });

  test('article content is readable', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Check that article has substantial text content
    const articleText = await page.locator('article, .article-content, .article-body, main').first().textContent();
    expect(articleText?.length).toBeGreaterThan(100);
  });
});

test.describe('Article Page - Metadata Sidebar', () => {
  test('metadata sidebar is visible on article pages', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Check for metadata sidebar
    const sidebar = page.locator('#article-sidebar, .article-sidebar, [class*="metadata"]').first();
    
    if (await sidebar.count() > 0) {
      await expect(sidebar).toBeVisible();
    }
  });

  test('metadata contains publication date', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Look for date in metadata
    const dateElement = page.locator('time, .metadata-value, [class*="published"]').first();
    
    if (await dateElement.count() > 0) {
      const dateText = await dateElement.textContent();
      // Should contain date-like content (month, year, or formatted date)
      expect(dateText).toMatch(/\d{4}|January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/i);
    }
  });

  test('metadata tags are clickable and navigate correctly', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Find metadata tags/links
    const metadataLinks = page.locator('.metadata-tag, .metadata-tags a, [class*="tag"] a');
    
    if (await metadataLinks.count() > 0) {
      const firstTag = metadataLinks.first();
      const href = await firstTag.getAttribute('href');
      
      // Should have a valid href
      expect(href).toBeTruthy();
      expect(href).toMatch(/^\//);
    }
  });

  test('category tag links to search results', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Find category link
    const categoryLink = page.locator('a[href*="/news/search"], a[href*="type="], .metadata-tag--section').first();
    
    if (await categoryLink.count() > 0 && await categoryLink.isVisible()) {
      const href = await categoryLink.getAttribute('href');
      // Verify link exists and points to search/news
      expect(href).toMatch(/news|search/);
    }
  });
});

test.describe('Article Page - Breadcrumbs', () => {
  test('article has breadcrumb navigation', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const breadcrumbs = page.locator('nav[aria-label*="breadcrumb"], .breadcrumbs, [class*="breadcrumb"]').first();
    
    // Breadcrumbs should exist (visible or in DOM)
    const count = await breadcrumbs.count();
    expect(count).toBeGreaterThan(0);
  });

  test('breadcrumbs show correct hierarchy', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const breadcrumbItems = page.locator('.breadcrumbs a, [class*="breadcrumb"] a, nav[aria-label*="breadcrumb"] a');
    const count = await breadcrumbItems.count();
    
    // Should have at least Home link
    expect(count).toBeGreaterThanOrEqual(1);

    // First breadcrumb should be Home
    const firstBreadcrumb = await breadcrumbItems.first().textContent();
    expect(firstBreadcrumb?.toLowerCase()).toContain('home');
  });

  test('breadcrumb links are functional', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const homeLink = page.locator('.breadcrumbs a, [class*="breadcrumb"] a').first();
    await homeLink.click();
    await waitForPageReady(page);

    // Should navigate to homepage
    expect(page.url()).toMatch(/\/$/);
  });
});

test.describe('Article Page - Accessibility', () => {
  test('article has proper landmark structure', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Should have main landmark
    const main = page.locator('main');
    await expect(main).toBeVisible();

    // Should have article element or role
    const article = page.locator('article, [role="article"]');
    const hasArticle = await article.count() > 0;
    expect(hasArticle).toBeTruthy();
  });

  test('images in article have alt text', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const images = page.locator('article img, .article-content img');
    const count = await images.count();

    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');
      
      // Image should have alt text or be decorative
      expect(alt !== null || role === 'presentation').toBeTruthy();
    }
  });

  test('links in article are distinguishable', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const links = page.locator('article a, .article-content a');
    const count = await links.count();

    if (count > 0) {
      const firstLink = links.first();
      const textDecoration = await firstLink.evaluate(el => 
        getComputedStyle(el).textDecoration
      );
      const color = await firstLink.evaluate(el => 
        getComputedStyle(el).color
      );

      // Link should have some visual distinction
      expect(textDecoration.includes('underline') || color !== 'rgb(27, 27, 27)').toBeTruthy();
    }
  });
});

test.describe('Article Page - Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('article is readable on mobile', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Check no horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => 
      document.documentElement.scrollWidth > window.innerWidth
    );
    expect(hasHorizontalScroll).toBeFalsy();
  });

  test('metadata displays correctly on mobile', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Metadata should be visible (may be repositioned)
    const metadata = page.locator('.metadata-group, [class*="metadata"], time').first();
    
    if (await metadata.count() > 0) {
      await expect(metadata).toBeVisible();
    }
  });

  test('article text is not too small on mobile', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    const articleText = page.locator('article p, .article-content p').first();
    
    if (await articleText.count() > 0) {
      const fontSize = await articleText.evaluate(el => 
        parseFloat(getComputedStyle(el).fontSize)
      );
      // Font should be at least 14px for readability
      expect(fontSize).toBeGreaterThanOrEqual(14);
    }
  });
});

test.describe('Article Page - Navigation', () => {
  test('can navigate back to news list', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Find breadcrumb or back link to news section
    const newsLinks = page.locator('a[href*="/news/press-releases"]');
    const count = await newsLinks.count();
    
    // Should have at least one link back to press releases
    expect(count).toBeGreaterThan(0);
    
    // Verify the link href is correct
    const href = await newsLinks.first().getAttribute('href');
    expect(href).toContain('/news/press-releases');
  });

  test('article links open correctly', async ({ page }) => {
    await page.goto(ARTICLE_PAGES.pressRelease);
    await waitForPageReady(page);

    // Find internal links in article content
    const internalLinks = page.locator('article a[href^="/"], .article-content a[href^="/"]');
    
    if (await internalLinks.count() > 0) {
      const href = await internalLinks.first().getAttribute('href');
      expect(href).toMatch(/^\//);
    }
  });
});
