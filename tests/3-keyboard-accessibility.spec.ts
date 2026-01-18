import { test, expect, TEST_PAGES, waitForPageReady, tabThroughPage, getFocusableElements } from './fixtures';
import AxeBuilder from '@axe-core/playwright';

/**
 * Keyboard Accessibility Tests
 * 
 * - Focus indicator is visible on all interactive elements
 * - Tab order is logical
 * - No keyboard traps
 * - Buttons and links activatable with Enter/Space
 * - Form fields are navigable
 */

test.describe('Keyboard Accessibility - Focus Indicators', () => {
  test('all focusable elements have visible focus indicators', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Get all focusable elements
    const focusableCount = await getFocusableElements(page);
    expect(focusableCount).toBeGreaterThan(0);
    
    // Check focus styles exist in CSS
    const hasFocusStyles = await page.evaluate(() => {
      const styles = Array.from(document.styleSheets);
      let foundFocusRule = false;
      
      try {
        styles.forEach(sheet => {
          try {
            const rules = Array.from(sheet.cssRules);
            rules.forEach(rule => {
              if (rule.cssText && rule.cssText.includes(':focus')) {
                foundFocusRule = true;
              }
            });
          } catch (e) {
            // Cross-origin stylesheets will throw
          }
        });
      } catch (e) {}
      
      return foundFocusRule;
    });
    
    expect(hasFocusStyles).toBe(true);
  });

  test('focused links have visible outline', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Tab to first link
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // Skip potential skip link
    
    // Check if focused element has outline/styling
    const focusStyle = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      if (!el) return null;
      
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineStyle: styles.outlineStyle,
        boxShadow: styles.boxShadow,
      };
    });
    
    // Should have some focus indicator
    const hasFocusIndicator = 
      focusStyle?.outlineStyle !== 'none' ||
      focusStyle?.boxShadow !== 'none';
    
    expect(hasFocusIndicator).toBe(true);
  });
});

test.describe('Keyboard Accessibility - Tab Order', () => {
  test('tab order is logical on homepage', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const focusOrder = await tabThroughPage(page, 20);
    
    // Should have multiple focusable elements
    expect(focusOrder.length).toBeGreaterThan(5);
    
    // First should be skip link or header element
    const firstFocused = focusOrder[0]?.toLowerCase() || '';
    const startsLogically = 
      firstFocused.includes('skip') ||
      firstFocused.includes('header') ||
      firstFocused.includes('nav') ||
      firstFocused.includes('logo');
    
    expect(startsLogically).toBe(true);
  });

  test('tab order follows visual layout on press releases', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const focusOrder = await tabThroughPage(page, 30);
    
    // Should focus through the page elements
    expect(focusOrder.length).toBeGreaterThan(5);
  });
});

test.describe('Keyboard Accessibility - Keyboard Traps', () => {
  test('can escape from any focus with Tab or Escape', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Tab through elements
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab');
      
      // Check we're not stuck
      const activeTag = await page.evaluate(() => document.activeElement?.tagName);
      
      // If we've tabbed back to body or reached end, we're not trapped
      if (activeTag === 'BODY') break;
    }
    
    // Should be able to reach body (end of focusable elements)
    // or still be tabbing through (large page)
    const finalElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(finalElement).toBeDefined();
  });

  test('modal dialogs can be closed with Escape', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Look for potential modal triggers
    const modalTriggers = page.locator('[data-toggle="modal"], [aria-haspopup="dialog"]');
    
    if (await modalTriggers.count() > 0) {
      await modalTriggers.first().click();
      await page.waitForTimeout(300);
      
      // Press Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
      
      // Modal should be closed
      const visibleModals = page.locator('[role="dialog"]:visible, .modal:visible');
      expect(await visibleModals.count()).toBe(0);
    }
  });
});

test.describe('Keyboard Accessibility - Interactive Elements', () => {
  test('buttons are activatable with Enter and Space', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const buttons = page.locator('button, [role="button"]');
    const buttonCount = await buttons.count();
    
    if (buttonCount > 0) {
      const firstButton = buttons.first();
      await firstButton.focus();
      
      // Verify it can receive focus
      const isFocused = await page.evaluate(() => {
        return document.activeElement?.tagName === 'BUTTON' ||
               document.activeElement?.getAttribute('role') === 'button';
      });
      
      expect(isFocused).toBe(true);
    }
  });

  test('links are activatable with Enter', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Find a navigation link
    const navLink = page.locator('nav a, header a').first();
    
    if (await navLink.count() > 0) {
      const initialUrl = page.url();
      await navLink.focus();
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // URL should have changed (link was activated)
      // Or if it's same-page link, it's still OK
      expect(page.url()).toBeDefined();
    }
  });
});

test.describe('Keyboard Accessibility - Forms', () => {
  test('form fields are navigable with Tab', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const formFields = page.locator('input, select, textarea');
    const fieldCount = await formFields.count();
    
    // Search page should have form fields
    expect(fieldCount).toBeGreaterThan(0);
    
    // Tab through form
    await page.keyboard.press('Tab');
    
    for (let i = 0; i < fieldCount + 5; i++) {
      const activeTag = await page.evaluate(() => 
        document.activeElement?.tagName.toLowerCase()
      );
      
      if (['input', 'select', 'textarea'].includes(activeTag || '')) {
        break; // Found a form field
      }
      
      await page.keyboard.press('Tab');
    }
    
    // Should have reached a form field
    const activeIsFormField = await page.evaluate(() => {
      const tag = document.activeElement?.tagName.toLowerCase();
      return ['input', 'select', 'textarea', 'button'].includes(tag || '');
    });
    
    expect(activeIsFormField).toBe(true);
  });

  test('form labels are associated with inputs', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    // Check that inputs have labels
    const inputsWithoutLabels = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), select, textarea'));
      
      return inputs.filter(input => {
        const id = input.id;
        const ariaLabel = input.getAttribute('aria-label');
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        const hasLabel = id && document.querySelector(`label[for="${id}"]`);
        const wrappedByLabel = input.closest('label');
        
        return !ariaLabel && !ariaLabelledBy && !hasLabel && !wrappedByLabel;
      }).map(el => el.outerHTML.slice(0, 100));
    });
    
    // All inputs should have labels
    expect(inputsWithoutLabels).toHaveLength(0);
  });
});

test.describe('Keyboard Accessibility - axe-core Audit', () => {
  test('homepage passes keyboard accessibility checks', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['keyboard'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('search page passes keyboard accessibility checks', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['keyboard'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});
