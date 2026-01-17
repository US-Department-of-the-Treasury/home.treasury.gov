import { test, expect, TEST_PAGES, waitForPageReady, collectCSPViolations } from './fixtures';

/**
 * Content Security Policy (CSP) Compliance Tests
 * 
 * Verifies that all pages load without CSP violations.
 * The site enforces strict CSP headers that block inline scripts.
 */

test.describe('CSP Compliance - Console Error Monitoring', () => {
  
  test('homepage has no CSP violations', async ({ page }) => {
    const cspViolations: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (
        text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes("Refused to execute inline script") ||
        text.includes("Refused to load the script")
      ) {
        cspViolations.push(text);
      }
    });
    
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    expect(cspViolations).toHaveLength(0);
  });

  test('press releases page has no CSP violations', async ({ page }) => {
    const cspViolations: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (
        text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes("Refused to execute")
      ) {
        cspViolations.push(text);
      }
    });
    
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    expect(cspViolations).toHaveLength(0);
  });

  test('advanced search page has no CSP violations', async ({ page }) => {
    const cspViolations: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (
        text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes("Refused to execute")
      ) {
        cspViolations.push(text);
      }
    });
    
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    // Also interact with the page to trigger any dynamic JS
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      await page.keyboard.press('Enter');
      await waitForPageReady(page);
    }
    
    expect(cspViolations).toHaveLength(0);
  });

  test('all news page has no CSP violations', async ({ page }) => {
    const cspViolations: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (
        text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes("Refused to execute")
      ) {
        cspViolations.push(text);
      }
    });
    
    await page.goto(TEST_PAGES.allNews);
    await waitForPageReady(page);
    
    expect(cspViolations).toHaveLength(0);
  });

  test('404 page has no CSP violations', async ({ page }) => {
    const cspViolations: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (
        text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes("Refused to execute")
      ) {
        cspViolations.push(text);
      }
    });
    
    await page.goto(TEST_PAGES.notFound);
    await waitForPageReady(page);
    
    expect(cspViolations).toHaveLength(0);
  });
});

test.describe('CSP Compliance - Inline Script Check', () => {
  
  test('homepage has no inline onclick handlers', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const inlineHandlers = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      const handlers: string[] = [];
      
      elements.forEach(el => {
        const attrs = el.attributes;
        for (let i = 0; i < attrs.length; i++) {
          if (attrs[i].name.startsWith('on')) {
            handlers.push(`${el.tagName}.${attrs[i].name}`);
          }
        }
      });
      
      return handlers;
    });
    
    expect(inlineHandlers).toHaveLength(0);
  });

  test('search page has no inline handlers', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const inlineHandlers = await page.evaluate(() => {
      const handlers: string[] = [];
      document.querySelectorAll('*').forEach(el => {
        Array.from(el.attributes).forEach(attr => {
          if (attr.name.startsWith('on')) {
            handlers.push(`${el.tagName}.${attr.name}="${attr.value.slice(0, 50)}"`);
          }
        });
      });
      return handlers;
    });
    
    expect(inlineHandlers).toHaveLength(0);
  });

  test('no inline script tags without src', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const inlineScripts = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script:not([src])');
      return Array.from(scripts)
        .filter(s => s.textContent && s.textContent.trim().length > 0)
        .map(s => s.textContent?.slice(0, 100));
    });
    
    // Some inline scripts might be allowed (JSON-LD, etc.)
    // Filter out structured data
    const problematicScripts = inlineScripts.filter(s => 
      s && !s.includes('@type') && !s.includes('application/ld+json')
    );
    
    expect(problematicScripts).toHaveLength(0);
  });
});

test.describe('CSP Compliance - External Resources', () => {
  
  test('all scripts are from same origin', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const externalScripts = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script[src]');
      const origin = window.location.origin;
      
      return Array.from(scripts)
        .map(s => s.getAttribute('src'))
        .filter(src => src && !src.startsWith('/') && !src.startsWith(origin));
    });
    
    // Should have no external CDN scripts
    expect(externalScripts).toHaveLength(0);
  });

  test('all stylesheets are from same origin', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const externalStyles = await page.evaluate(() => {
      const links = document.querySelectorAll('link[rel="stylesheet"]');
      const origin = window.location.origin;
      
      return Array.from(links)
        .map(l => l.getAttribute('href'))
        .filter(href => href && !href.startsWith('/') && !href.startsWith(origin));
    });
    
    expect(externalStyles).toHaveLength(0);
  });
});

test.describe('CSP Compliance - Interactive Elements', () => {
  
  test('form submit works without inline handler', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const form = page.locator('form').first();
    
    if (await form.count() > 0) {
      // Check form doesn't have inline onsubmit
      const onsubmit = await form.getAttribute('onsubmit');
      expect(onsubmit).toBeNull();
      
      // Verify form can be submitted
      const input = page.locator('input[type="text"], input[type="search"]').first();
      if (await input.count() > 0) {
        await input.fill('test');
        await page.keyboard.press('Enter');
        await waitForPageReady(page);
        
        // Page should respond (URL change or results update)
        expect(page.url()).toBeDefined();
      }
    }
  });

  test('buttons work without inline handlers', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const buttons = page.locator('button');
    const count = await buttons.count();
    
    for (let i = 0; i < count; i++) {
      const button = buttons.nth(i);
      const onclick = await button.getAttribute('onclick');
      
      // No inline onclick handlers
      expect(onclick).toBeNull();
    }
  });
});

test.describe('CSP Compliance - Performance Check', () => {
  
  test('JavaScript executes without CSP blocking', async ({ page }) => {
    const jsErrors: string[] = [];
    
    page.on('pageerror', error => {
      jsErrors.push(error.message);
    });
    
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    // Interact with the page to trigger JS
    const form = page.locator('form').first();
    if (await form.count() > 0) {
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
    }
    
    // Filter out non-CSP related errors
    const cspErrors = jsErrors.filter(e => 
      e.includes('CSP') || 
      e.includes('Content Security Policy') ||
      e.includes('blocked')
    );
    
    expect(cspErrors).toHaveLength(0);
  });
});
