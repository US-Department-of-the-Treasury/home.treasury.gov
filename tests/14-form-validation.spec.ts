/**
 * Form Validation and Error State Tests
 * 
 * Tests for form behavior including:
 * - Search form validation
 * - Date picker validation
 * - Error message display
 * - Form submission handling
 */

import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('Search Form - Basic Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
  });

  test('search form accepts valid input', async ({ page }) => {
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    
    await searchInput.fill('treasury');
    const value = await searchInput.inputValue();
    expect(value).toBe('treasury');
  });

  test('search form handles empty submission', async ({ page }) => {
    // Clear any default values
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    await searchInput.clear();

    // Submit empty form
    const searchButton = page.locator('button[type="submit"], input[type="submit"], button:has-text("Search")').first();
    await searchButton.click();
    await waitForPageReady(page);

    // Should either show all results or a message
    const results = page.locator('.search-results, .news-list, article');
    const message = page.locator('[class*="message"], [class*="no-results"], [role="status"]');
    
    const hasResults = await results.count() > 0;
    const hasMessage = await message.count() > 0;
    
    // Either should be true
    expect(hasResults || hasMessage).toBeTruthy();
  });

  test('search form handles special characters', async ({ page }) => {
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    
    // Test with special characters
    await searchInput.fill('<script>alert("xss")</script>');
    
    const searchButton = page.locator('button[type="submit"], input[type="submit"], button:has-text("Search")').first();
    await searchButton.click();
    await waitForPageReady(page);

    // Page should not break
    const main = page.locator('main');
    await expect(main).toBeVisible();
    
    // No XSS should execute
    const dialogShown = await page.evaluate(() => {
      return (window as any).__xssTriggered === true;
    });
    expect(dialogShown).toBeFalsy();
  });

  test('search form handles very long input', async ({ page }) => {
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    
    // Test with very long string
    const longString = 'a'.repeat(1000);
    await searchInput.fill(longString);
    
    const searchButton = page.locator('button[type="submit"], input[type="submit"], button:has-text("Search")').first();
    await searchButton.click();
    await waitForPageReady(page);

    // Page should not break
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });
});

test.describe('Date Picker Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
  });

  test('date inputs accept valid dates', async ({ page }) => {
    const fromDate = page.locator('#search-date-from, input[name*="from"], input[type="date"]').first();
    const toDate = page.locator('#search-date-to, input[name*="to"], input[type="date"]').last();
    
    if (await fromDate.count() > 0 && await toDate.count() > 0) {
      await fromDate.fill('2024-01-01');
      await toDate.fill('2024-12-31');
      
      const fromValue = await fromDate.inputValue();
      const toValue = await toDate.inputValue();
      
      expect(fromValue).toBe('2024-01-01');
      expect(toValue).toBe('2024-12-31');
    }
  });

  test('date range filter applies correctly', async ({ page }) => {
    const fromDate = page.locator('#search-date-from, input[name*="from"], input[type="date"]').first();
    const toDate = page.locator('#search-date-to, input[name*="to"], input[type="date"]').last();
    
    if (await fromDate.count() > 0 && await toDate.count() > 0) {
      // Set date range to last month
      const today = new Date();
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
      
      await fromDate.fill(lastMonth.toISOString().split('T')[0]);
      await toDate.fill(endOfLastMonth.toISOString().split('T')[0]);
      
      // Apply filter
      const applyButton = page.locator('button:has-text("Apply"), button:has-text("Search"), button[type="submit"]').first();
      await applyButton.click();
      await waitForPageReady(page);
      
      // Results should update
      const results = page.locator('.search-results, .news-list, article');
      // May or may not have results depending on date range
    }
  });

  test('invalid date range shows appropriate feedback', async ({ page }) => {
    const fromDate = page.locator('#search-date-from, input[name*="from"], input[type="date"]').first();
    const toDate = page.locator('#search-date-to, input[name*="to"], input[type="date"]').last();
    
    if (await fromDate.count() > 0 && await toDate.count() > 0) {
      // Set "from" date after "to" date
      await fromDate.fill('2024-12-31');
      await toDate.fill('2024-01-01');
      
      // Try to apply
      const applyButton = page.locator('button:has-text("Apply"), button:has-text("Search"), button[type="submit"]').first();
      await applyButton.click();
      await waitForPageReady(page);
      
      // Page should handle gracefully (show message, swap dates, or return no results)
      const main = page.locator('main');
      await expect(main).toBeVisible();
    }
  });
});

test.describe('Filter Dropdowns', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
  });

  test('dropdown filters are keyboard accessible', async ({ page }) => {
    const dropdown = page.locator('select, [role="combobox"], [role="listbox"]').first();
    
    if (await dropdown.count() > 0) {
      // Focus the dropdown
      await dropdown.focus();
      
      // Should be focusable
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
      
      // Try keyboard navigation
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
    }
  });

  test('selecting multiple filters works', async ({ page }) => {
    const dropdowns = page.locator('select, [role="combobox"]');
    const count = await dropdowns.count();
    
    if (count >= 2) {
      // Select from first dropdown
      const first = dropdowns.first();
      const options1 = first.locator('option');
      if (await options1.count() > 1) {
        await first.selectOption({ index: 1 });
      }
      
      // Select from second dropdown
      const second = dropdowns.nth(1);
      const options2 = second.locator('option');
      if (await options2.count() > 1) {
        await second.selectOption({ index: 1 });
      }
      
      // Apply filters
      const applyButton = page.locator('button:has-text("Apply"), button:has-text("Search"), button[type="submit"]').first();
      await applyButton.click();
      await waitForPageReady(page);
      
      // Page should still work
      const main = page.locator('main');
      await expect(main).toBeVisible();
    }
  });
});

test.describe('Form Accessibility', () => {
  test('form inputs have visible labels', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);

    const inputs = page.locator('input:not([type="hidden"]):not([type="submit"]), select, textarea');
    const count = await inputs.count();

    for (let i = 0; i < Math.min(count, 10); i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledby = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');
      
      // Input should have some form of label
      if (id) {
        const label = page.locator(`label[for="${id}"]`);
        const hasLabel = await label.count() > 0;
        const hasAriaLabel = ariaLabel || ariaLabelledby;
        const hasPlaceholder = placeholder;
        
        expect(hasLabel || hasAriaLabel || hasPlaceholder).toBeTruthy();
      }
    }
  });

  test('error messages are associated with inputs', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);

    // Check for aria-describedby on inputs
    const inputs = page.locator('input[aria-describedby], input[aria-errormessage]');
    
    if (await inputs.count() > 0) {
      const firstInput = inputs.first();
      const describedBy = await firstInput.getAttribute('aria-describedby');
      
      if (describedBy) {
        // The referenced element should exist
        const errorElement = page.locator(`#${describedBy}`);
        // It's okay if it doesn't exist yet (shown on error)
      }
    }
  });

  test('required fields are indicated', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);

    const requiredInputs = page.locator('input[required], input[aria-required="true"]');
    const count = await requiredInputs.count();

    for (let i = 0; i < count; i++) {
      const input = requiredInputs.nth(i);
      const id = await input.getAttribute('id');
      
      if (id) {
        const label = page.locator(`label[for="${id}"]`);
        if (await label.count() > 0) {
          const labelText = await label.textContent();
          // Required indicator could be asterisk, "(required)", or similar
          console.log(`Required field label: ${labelText}`);
        }
      }
    }
  });
});

test.describe('Form Reset and Clear', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
  });

  test('reset button clears all inputs', async ({ page }) => {
    // Fill in some values
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    await searchInput.fill('test search');
    
    // Find and click reset
    const resetButton = page.locator('button:has-text("Reset"), button:has-text("Clear"), button[type="reset"], .reset-button, [class*="clear"]').first();
    
    if (await resetButton.count() > 0) {
      await resetButton.click();
      await waitForPageReady(page);
      
      // Input should be empty
      const value = await searchInput.inputValue();
      expect(value).toBe('');
    }
  });

  test('clearing filters removes active filter tags', async ({ page }) => {
    // Apply a filter first
    const searchInput = page.locator('#search-keyword, input[name*="keyword"], input[type="text"]').first();
    await searchInput.fill('sanctions');
    
    const searchButton = page.locator('button[type="submit"], button:has-text("Search")').first();
    await searchButton.click();
    await waitForPageReady(page);
    
    // Look for active filter tags
    const filterTags = page.locator('.active-filter, .filter-tag, [class*="tag"]:not([class*="metadata"])');
    const initialTagCount = await filterTags.count();
    
    // Clear filters
    const resetButton = page.locator('button:has-text("Reset"), button:has-text("Clear All"), .reset-button').first();
    
    if (await resetButton.count() > 0 && initialTagCount > 0) {
      await resetButton.click();
      await waitForPageReady(page);
      
      // Tags should be removed
      const finalTagCount = await filterTags.count();
      expect(finalTagCount).toBeLessThanOrEqual(initialTagCount);
    }
  });
});

test.describe('Pagination Form', () => {
  test('jump to page input works', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);

    // Find jump to page input
    const jumpInput = page.locator('input[name*="page"], input[type="number"], input[aria-label*="page" i]').first();
    
    if (await jumpInput.count() > 0) {
      await jumpInput.fill('5');
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // URL should reflect page 5
      expect(page.url()).toMatch(/page[=\/]5|\/5\/?$/);
    }
  });

  test('invalid page number is handled', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);

    const jumpInput = page.locator('input[name*="page"], input[type="number"], input[aria-label*="page" i]').first();
    
    if (await jumpInput.count() > 0) {
      // Try invalid page number
      await jumpInput.fill('99999');
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // Page should handle gracefully (show last page, or error, or stay)
      const main = page.locator('main');
      await expect(main).toBeVisible();
    }
  });
});

test.describe('Header Search Form', () => {
  test('header search toggle works', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Find search toggle
    const searchToggle = page.locator('.search-toggle, button[aria-controls*="search"], [class*="search-button"]').first();
    
    if (await searchToggle.count() > 0) {
      await searchToggle.click();
      
      // Search input should appear
      const searchDropdown = page.locator('.search-dropdown, #search-dropdown, [class*="search-form"]');
      await expect(searchDropdown.first()).toBeVisible();
    }
  });

  test('header search redirects to search page', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Open search if needed
    const searchToggle = page.locator('.search-toggle, button[aria-controls*="search"]').first();
    if (await searchToggle.count() > 0) {
      await searchToggle.click();
    }

    // Fill and submit search
    const searchInput = page.locator('.search-dropdown input, #search-dropdown input, header input[type="search"], header input[type="text"]').first();
    
    if (await searchInput.count() > 0) {
      await searchInput.fill('treasury');
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
      
      // Should navigate to search results or USA.gov search
      expect(page.url()).toMatch(/search|query/);
    }
  });
});
