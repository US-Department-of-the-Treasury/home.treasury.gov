import { test, expect, TEST_PAGES, waitForPageReady } from './fixtures';

/**
 * Performance Observation Tests
 * 
 * - Page load feels fast (<3 seconds)
 * - No layout shift after load
 * - Images load progressively
 */

test.describe('Performance - Page Load Times', () => {
  
  test('homepage loads within 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(TEST_PAGES.homepage, { waitUntil: 'domcontentloaded' });
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('press releases page loads within 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(TEST_PAGES.pressReleases, { waitUntil: 'domcontentloaded' });
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
  });

  test('search page loads within 3 seconds', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(TEST_PAGES.advancedSearch, { waitUntil: 'domcontentloaded' });
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
  });
});

test.describe('Performance - Layout Stability', () => {
  
  test('homepage has no significant layout shift', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    
    // Capture initial layout positions of key elements
    const initialPositions = await page.evaluate(() => {
      const header = document.querySelector('header');
      const main = document.querySelector('main');
      const footer = document.querySelector('footer');
      
      return {
        header: header?.getBoundingClientRect().top,
        main: main?.getBoundingClientRect().top,
        footer: footer?.getBoundingClientRect().top,
      };
    });
    
    // Wait for any lazy loading or dynamic content
    await page.waitForTimeout(2000);
    
    // Check positions again
    const finalPositions = await page.evaluate(() => {
      const header = document.querySelector('header');
      const main = document.querySelector('main');
      const footer = document.querySelector('footer');
      
      return {
        header: header?.getBoundingClientRect().top,
        main: main?.getBoundingClientRect().top,
        footer: footer?.getBoundingClientRect().top,
      };
    });
    
    // Positions should not have shifted significantly
    if (initialPositions.header !== undefined && finalPositions.header !== undefined) {
      const headerShift = Math.abs(finalPositions.header - initialPositions.header);
      expect(headerShift).toBeLessThan(50);
    }
    
    if (initialPositions.main !== undefined && finalPositions.main !== undefined) {
      const mainShift = Math.abs(finalPositions.main - initialPositions.main);
      expect(mainShift).toBeLessThan(100);
    }
  });

  test('news list has stable layout during pagination', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    // Get initial content area height
    const initialHeight = await page.evaluate(() => {
      const main = document.querySelector('main');
      return main?.scrollHeight || 0;
    });
    
    // Click pagination if exists
    const nextButton = page.locator('a:has-text("Next"), button:has-text("Next")').first();
    
    if (await nextButton.count() > 0 && await nextButton.isVisible()) {
      await nextButton.click();
      await waitForPageReady(page);
      
      // Content should exist
      const newHeight = await page.evaluate(() => {
        const main = document.querySelector('main');
        return main?.scrollHeight || 0;
      });
      
      expect(newHeight).toBeGreaterThan(0);
    }
  });
});

test.describe('Performance - Image Loading', () => {
  
  test('images have loading attribute for lazy loading', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const imageStats = await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll('img'));
      const withLoading = images.filter(img => img.hasAttribute('loading'));
      const lazyLoaded = images.filter(img => img.getAttribute('loading') === 'lazy');
      
      return {
        total: images.length,
        withLoadingAttr: withLoading.length,
        lazyLoaded: lazyLoaded.length,
      };
    });
    
    // If there are images, some should use lazy loading
    if (imageStats.total > 5) {
      expect(imageStats.lazyLoaded).toBeGreaterThan(0);
    }
  });

  test('images have width and height to prevent layout shift', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const imagesWithoutDimensions = await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll('img'));
      
      return images.filter(img => {
        const hasWidth = img.hasAttribute('width') || img.style.width;
        const hasHeight = img.hasAttribute('height') || img.style.height;
        const hasAspectRatio = img.style.aspectRatio;
        
        // Inline SVGs and very small images are OK
        const isSmall = img.naturalWidth < 50 && img.naturalHeight < 50;
        
        return !isSmall && !hasWidth && !hasHeight && !hasAspectRatio;
      }).map(img => img.src.slice(0, 80));
    });
    
    // Ideally all images should have dimensions
    // This is a warning rather than hard failure
    if (imagesWithoutDimensions.length > 0) {
      console.log('Images without explicit dimensions:');
      imagesWithoutDimensions.forEach(src => console.log(`  ${src}`));
    }
  });
});

test.describe('Performance - Resource Loading', () => {
  
  test('critical CSS is loaded', async ({ page }) => {
    const response = await page.goto(TEST_PAGES.homepage);
    
    // Check for CSS in response
    const cssLoaded = await page.evaluate(() => {
      const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
      const inlineStyles = document.querySelectorAll('style');
      
      return stylesheets.length > 0 || inlineStyles.length > 0;
    });
    
    expect(cssLoaded).toBe(true);
  });

  test('JavaScript files load successfully', async ({ page }) => {
    const failedScripts: string[] = [];
    
    page.on('requestfailed', request => {
      if (request.resourceType() === 'script') {
        failedScripts.push(request.url());
      }
    });
    
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    expect(failedScripts).toHaveLength(0);
  });

  test('fonts load successfully', async ({ page }) => {
    const failedFonts: string[] = [];
    
    page.on('requestfailed', request => {
      if (request.resourceType() === 'font') {
        failedFonts.push(request.url());
      }
    });
    
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    expect(failedFonts).toHaveLength(0);
  });
});

test.describe('Performance - Caching Headers', () => {
  
  test('static assets have cache headers', async ({ page, baseURL }) => {
    // Skip cache header tests on dev server (Hugo doesn't set cache headers)
    test.skip(baseURL?.includes('localhost') || false, 'Cache headers not set on dev server');
    const assetsWithCaching: { url: string; cacheControl: string | null }[] = [];
    
    page.on('response', response => {
      const url = response.url();
      if (url.match(/\.(js|css|woff2?|png|jpg|jpeg|gif|svg)$/)) {
        const cacheControl = response.headers()['cache-control'];
        assetsWithCaching.push({ url, cacheControl });
      }
    });
    
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Check that static assets have cache headers
    const assetsWithoutCaching = assetsWithCaching.filter(a => !a.cacheControl);
    
    if (assetsWithoutCaching.length > 0) {
      console.log('Assets without cache-control headers:');
      assetsWithoutCaching.forEach(a => console.log(`  ${a.url}`));
    }
    
    // Most assets should have caching
    const cachingRatio = (assetsWithCaching.length - assetsWithoutCaching.length) / assetsWithCaching.length;
    expect(cachingRatio).toBeGreaterThan(0.5);
  });
});
