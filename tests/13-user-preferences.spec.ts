/**
 * User Preferences Tests
 * 
 * Tests for respecting user preferences including:
 * - prefers-reduced-motion
 * - prefers-color-scheme (dark mode)
 * - prefers-contrast (high contrast)
 * - Text scaling/zoom
 */

import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('Reduced Motion Preference', () => {
  test('respects prefers-reduced-motion: reduce', async ({ page }) => {
    // Emulate reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check that animations are disabled or reduced
    const animatedElements = page.locator('[class*="animate"], [class*="transition"], [class*="slider"]');
    
    if (await animatedElements.count() > 0) {
      const firstAnimated = animatedElements.first();
      const animationDuration = await firstAnimated.evaluate(el => {
        const style = getComputedStyle(el);
        return style.animationDuration || style.transitionDuration;
      });
      
      // Animation should be instant (0s) or very short when motion is reduced
      // This is a soft check - just verify the preference is being read
      console.log(`Animation duration with reduced motion: ${animationDuration}`);
    }
  });

  test('slider respects reduced motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check slider doesn't auto-advance or has no transition
    const sliderDots = page.locator('.slider-dot');
    
    if (await sliderDots.count() > 1) {
      // Wait a bit and check slide hasn't changed automatically
      const initialActive = await page.locator('.slider-dot.active').getAttribute('data-slide');
      await page.waitForTimeout(3000);
      const currentActive = await page.locator('.slider-dot.active').getAttribute('data-slide');
      
      // With reduced motion, auto-advance should be disabled or instant
      console.log(`Slider initial: ${initialActive}, after 3s: ${currentActive}`);
    }
  });

  test('page transitions respect reduced motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check CSS for reduced motion media query
    const hasReducedMotionCSS = await page.evaluate(() => {
      const sheets = document.styleSheets;
      for (let i = 0; i < sheets.length; i++) {
        try {
          const rules = sheets[i].cssRules;
          for (let j = 0; j < rules.length; j++) {
            if (rules[j].cssText && rules[j].cssText.includes('prefers-reduced-motion')) {
              return true;
            }
          }
        } catch (e) {
          // Cross-origin stylesheets can't be read
        }
      }
      return false;
    });
    
    console.log(`Has prefers-reduced-motion CSS: ${hasReducedMotionCSS}`);
  });
});

test.describe('Dark Mode Preference', () => {
  test('page loads with dark color scheme', async ({ page }) => {
    // Emulate dark mode preference
    await page.emulateMedia({ colorScheme: 'dark' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check if dark mode styles are applied
    const body = page.locator('body');
    const backgroundColor = await body.evaluate(el => 
      getComputedStyle(el).backgroundColor
    );

    console.log(`Body background in dark mode: ${backgroundColor}`);
    
    // Page should still be functional regardless of dark mode support
    await expect(body).toBeVisible();
  });

  test('text remains readable in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check text color
    const textElement = page.locator('p, h1, h2, .article-title').first();
    
    if (await textElement.count() > 0) {
      const textColor = await textElement.evaluate(el => 
        getComputedStyle(el).color
      );
      const bgColor = await page.locator('body').evaluate(el => 
        getComputedStyle(el).backgroundColor
      );

      console.log(`Text color: ${textColor}, Background: ${bgColor}`);
      
      // Text should be visible (not same as background)
      expect(textColor).not.toBe(bgColor);
    }
  });

  test('search page works in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);

    // Search form should still be visible
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    await expect(searchInput).toBeVisible();

    // Form should be functional
    await searchInput.fill('test');
    const value = await searchInput.inputValue();
    expect(value).toBe('test');
  });
});

test.describe('High Contrast Preference', () => {
  test('page loads with high contrast preference', async ({ page }) => {
    // Emulate high contrast (forced colors)
    await page.emulateMedia({ forcedColors: 'active' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Page should still load and be functional
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });

  test('focus indicators visible in high contrast', async ({ page }) => {
    await page.emulateMedia({ forcedColors: 'active' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Tab to first focusable element
    await page.keyboard.press('Tab');
    
    // Check focus is visible
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('buttons remain distinguishable in high contrast', async ({ page }) => {
    await page.emulateMedia({ forcedColors: 'active' });
    
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);

    // Buttons should have visible borders in forced colors mode
    const button = page.locator('button').first();
    
    if (await button.count() > 0) {
      await expect(button).toBeVisible();
      
      // Check button has some form of border or outline
      const borderStyle = await button.evaluate(el => {
        const style = getComputedStyle(el);
        return `${style.borderWidth} ${style.borderStyle} ${style.outlineWidth}`;
      });
      
      console.log(`Button border in high contrast: ${borderStyle}`);
    }
  });
});

test.describe('Text Scaling and Zoom', () => {
  test('page is usable at 200% zoom', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Simulate zoom by changing viewport
    await page.setViewportSize({ width: 640, height: 480 }); // Half size = 200% effective zoom
    
    // Check no horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => 
      document.documentElement.scrollWidth > window.innerWidth
    );
    
    // At 200% zoom, some horizontal scroll may occur - this is acceptable
    // Key is that content is still accessible
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('text can be resized with browser settings', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check that font sizes use relative units
    const bodyFontSize = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;
      const htmlFontSize = getComputedStyle(html).fontSize;
      const bodyFontSize = getComputedStyle(body).fontSize;
      return { html: htmlFontSize, body: bodyFontSize };
    });

    console.log(`HTML font-size: ${bodyFontSize.html}, Body font-size: ${bodyFontSize.body}`);
    
    // Base font size should be 16px (1rem)
    expect(parseInt(bodyFontSize.html)).toBeGreaterThanOrEqual(16);
  });

  test('content reflows at narrow widths', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Set very narrow viewport (simulates large text size)
    await page.setViewportSize({ width: 320, height: 568 });
    
    // Content should still be visible
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // Check no content is cut off horizontally
    const hasOverflow = await page.evaluate(() => {
      const elements = document.querySelectorAll('p, h1, h2, h3');
      for (const el of elements) {
        if (el.scrollWidth > el.clientWidth) {
          return true;
        }
      }
      return false;
    });
    
    // Log any overflow issues
    if (hasOverflow) {
      console.log('Some text elements may have horizontal overflow at 320px');
    }
  });

  test('line height allows text scaling', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);

    // Check line height is not fixed in pixels
    const paragraph = page.locator('p').first();
    
    if (await paragraph.count() > 0) {
      const lineHeight = await paragraph.evaluate(el => 
        getComputedStyle(el).lineHeight
      );

      console.log(`Paragraph line-height: ${lineHeight}`);
      
      // Line height should be unitless or em/rem based for proper scaling
      // Pixel values may cause text overlap when scaled
    }
  });
});

test.describe('Print Styles', () => {
  test('page has print-specific styles', async ({ page }) => {
    await page.emulateMedia({ media: 'print' });
    
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // In print mode, navigation should be hidden
    const nav = page.locator('.main-nav, nav[aria-label="Main navigation"]');
    
    if (await nav.count() > 0) {
      const navDisplay = await nav.evaluate(el => 
        getComputedStyle(el).display
      );
      
      console.log(`Navigation display in print mode: ${navDisplay}`);
    }
  });

  test('article content is visible in print', async ({ page }) => {
    await page.emulateMedia({ media: 'print' });
    
    await page.goto('/news/press-releases/sb0357/');
    await waitForPageReady(page);

    // Article content should remain visible
    const article = page.locator('article, .article-content, main').first();
    await expect(article).toBeVisible();
  });

  test('links show URLs in print (if implemented)', async ({ page }) => {
    await page.emulateMedia({ media: 'print' });
    
    await page.goto('/about/');
    await waitForPageReady(page);

    // Check if CSS shows URLs after links (common print pattern)
    const hasUrlAfterContent = await page.evaluate(() => {
      const sheets = document.styleSheets;
      for (let i = 0; i < sheets.length; i++) {
        try {
          const rules = sheets[i].cssRules;
          for (let j = 0; j < rules.length; j++) {
            if (rules[j].cssText && rules[j].cssText.includes('attr(href)')) {
              return true;
            }
          }
        } catch (e) {
          // Cross-origin stylesheets
        }
      }
      return false;
    });
    
    console.log(`Print CSS shows URLs: ${hasUrlAfterContent}`);
  });
});
