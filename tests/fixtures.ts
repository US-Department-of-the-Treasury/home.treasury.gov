import { test as base, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Test page URLs
 */
export const TEST_PAGES = {
  homepage: '/',
  pressReleases: '/news/press-releases/',
  advancedSearch: '/news/search/',
  allNews: '/news/all/',
  notFound: '/this-page-does-not-exist/',
} as const;

/**
 * Viewport sizes for responsive testing
 */
export const VIEWPORTS = {
  desktop: { width: 1200, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 375, height: 667 },
} as const;

/**
 * Custom test fixture with accessibility helper
 */
export const test = base.extend<{
  axe: AxeBuilder;
}>({
  axe: async ({ page }, use) => {
    const axeBuilder = new AxeBuilder({ page });
    await use(axeBuilder);
  },
});

export { expect };

/**
 * Helper: Check for console errors
 */
export async function collectConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

/**
 * Helper: Check for CSP violations specifically
 */
export async function collectCSPViolations(page: Page): Promise<string[]> {
  const violations: string[] = [];
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('Content Security Policy') || text.includes('CSP')) {
      violations.push(text);
    }
  });
  return violations;
}

/**
 * Helper: Get all focusable elements
 */
export async function getFocusableElements(page: Page): Promise<number> {
  return await page.evaluate(() => {
    const selector = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
    return document.querySelectorAll(selector).length;
  });
}

/**
 * Helper: Check if element has visible focus indicator
 */
export async function hasVisibleFocusIndicator(page: Page, selector: string): Promise<boolean> {
  return await page.evaluate((sel) => {
    const element = document.querySelector(sel) as HTMLElement;
    if (!element) return false;
    
    element.focus();
    const styles = window.getComputedStyle(element);
    
    // Check for outline, box-shadow, or border changes
    const hasOutline = styles.outlineStyle !== 'none' && styles.outlineWidth !== '0px';
    const hasBoxShadow = styles.boxShadow !== 'none';
    const hasBorder = styles.borderStyle !== 'none';
    
    return hasOutline || hasBoxShadow || hasBorder;
  }, selector);
}

/**
 * Helper: Tab through page and collect focus order
 */
export async function tabThroughPage(page: Page, maxTabs: number = 50): Promise<string[]> {
  const focusOrder: string[] = [];
  
  // Start from body
  await page.keyboard.press('Tab');
  
  for (let i = 0; i < maxTabs; i++) {
    const activeElement = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      
      const tag = el.tagName.toLowerCase();
      const id = el.id ? `#${el.id}` : '';
      const classes = el.className ? `.${el.className.split(' ').join('.')}` : '';
      const text = (el as HTMLElement).innerText?.slice(0, 30) || '';
      
      return `${tag}${id}${classes} "${text}"`;
    });
    
    if (!activeElement) break;
    focusOrder.push(activeElement);
    
    await page.keyboard.press('Tab');
  }
  
  return focusOrder;
}

/**
 * Helper: Check for broken images
 */
export async function findBrokenImages(page: Page): Promise<string[]> {
  return await page.evaluate(() => {
    const images = Array.from(document.querySelectorAll('img'));
    return images
      .filter(img => !img.complete || img.naturalWidth === 0)
      .map(img => img.src || img.getAttribute('data-src') || 'unknown');
  });
}

/**
 * Helper: Check for horizontal scrolling
 */
export async function hasHorizontalScroll(page: Page): Promise<boolean> {
  return await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth;
  });
}

/**
 * Helper: Wait for network idle and hydration
 */
export async function waitForPageReady(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  // Give any JS a moment to execute
  await page.waitForTimeout(500);
}
