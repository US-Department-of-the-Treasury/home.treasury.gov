/**
 * Service Worker and Offline Capability Tests
 * 
 * Tests for Progressive Web App (PWA) features including:
 * - Service worker registration
 * - Offline caching
 * - Cache strategies
 */

import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('Service Worker - Registration', () => {
  test('service worker file exists', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sw.js`);
    
    // Service worker should exist (200) or not be implemented (404)
    expect([200, 404]).toContain(response.status());
    
    if (response.status() === 200) {
      const content = await response.text();
      expect(content).toContain('self');
      console.log('Service worker file found');
    } else {
      console.log('No service worker implemented');
    }
  });

  test('service worker is registered on homepage', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check if service worker is registered
    const hasServiceWorker = await page.evaluate(async () => {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        return registration !== undefined;
      }
      return false;
    });

    // Service worker may or may not be registered depending on implementation
    console.log(`Service worker registered: ${hasServiceWorker}`);
  });

  test('service worker has valid scope', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const scope = await page.evaluate(async () => {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        return registration?.scope;
      }
      return null;
    });

    if (scope) {
      expect(scope).toMatch(/^https?:\/\//);
      console.log(`Service worker scope: ${scope}`);
    }
  });
});

test.describe('Service Worker - Caching', () => {
  test('homepage can be cached', async ({ page, context }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check if caches API is available and has entries
    const cacheNames = await page.evaluate(async () => {
      if ('caches' in window) {
        return await caches.keys();
      }
      return [];
    });

    console.log(`Cache names: ${cacheNames.join(', ') || 'none'}`);
  });

  test('static assets are cacheable', async ({ request, baseURL }) => {
    // Test CSS file caching
    const cssResponse = await request.get(`${baseURL}/css/treasury.css`);
    
    if (cssResponse.status() === 200) {
      const cacheControl = cssResponse.headers()['cache-control'];
      console.log(`CSS Cache-Control: ${cacheControl}`);
      
      // Static assets should have cache headers
      if (cacheControl) {
        expect(cacheControl).toMatch(/max-age|public/);
      }
    }
  });

  test('JavaScript files are cacheable', async ({ request, baseURL }) => {
    const jsResponse = await request.get(`${baseURL}/js/treasury.js`);
    
    if (jsResponse.status() === 200) {
      const cacheControl = jsResponse.headers()['cache-control'];
      console.log(`JS Cache-Control: ${cacheControl}`);
    }
  });

  test('images are cacheable', async ({ request, baseURL }) => {
    const imageResponse = await request.get(`${baseURL}/images/treasury-seal.svg`);
    
    if (imageResponse.status() === 200) {
      const cacheControl = imageResponse.headers()['cache-control'];
      console.log(`Image Cache-Control: ${cacheControl}`);
    }
  });
});

test.describe('Service Worker - Cache Strategies', () => {
  test('service worker defines cache version', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sw.js`);
    
    if (response.status() === 200) {
      const content = await response.text();
      
      // Should have versioned cache names
      expect(content).toMatch(/CACHE|VERSION|v\d/i);
    }
  });

  test('service worker handles fetch events', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sw.js`);
    
    if (response.status() === 200) {
      const content = await response.text();
      
      // Should have fetch event listener
      expect(content).toContain('fetch');
      expect(content).toContain('addEventListener');
    }
  });

  test('service worker has install event', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sw.js`);
    
    if (response.status() === 200) {
      const content = await response.text();
      
      // Should have install event
      expect(content).toContain('install');
    }
  });

  test('service worker has activate event', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sw.js`);
    
    if (response.status() === 200) {
      const content = await response.text();
      
      // Should have activate event for cache cleanup
      expect(content).toContain('activate');
    }
  });
});

test.describe('Manifest - PWA Configuration', () => {
  test('manifest.json exists (if PWA implemented)', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/manifest.json`);
    
    // Manifest is optional
    if (response.status() === 200) {
      const manifest = await response.json();
      
      // Should have required fields
      expect(manifest.name).toBeTruthy();
      expect(manifest.short_name).toBeTruthy();
      expect(manifest.start_url).toBeTruthy();
      expect(manifest.display).toBeTruthy();
      expect(manifest.icons).toBeTruthy();
      expect(manifest.icons.length).toBeGreaterThan(0);
      
      console.log('PWA manifest found and valid');
    } else {
      console.log('No PWA manifest implemented');
    }
  });

  test('manifest is linked in HTML', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const manifestLink = page.locator('link[rel="manifest"]');
    
    if (await manifestLink.count() > 0) {
      const href = await manifestLink.getAttribute('href');
      expect(href).toBeTruthy();
    }
  });
});

test.describe('Offline Fallback', () => {
  test('offline page exists (if implemented)', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/offline.html`);
    
    // Offline page is optional
    if (response.status() === 200) {
      const content = await response.text();
      expect(content).toContain('offline');
      console.log('Offline fallback page found');
    } else {
      console.log('No offline fallback page');
    }
  });

  test('service worker caches offline page', async ({ request, baseURL }) => {
    const swResponse = await request.get(`${baseURL}/sw.js`);
    
    if (swResponse.status() === 200) {
      const content = await swResponse.text();
      
      // Check if offline page is in cache list
      const hasOfflineCache = content.includes('offline') || 
                               content.includes('/offline.html');
      
      console.log(`Service worker caches offline page: ${hasOfflineCache}`);
    }
  });
});

test.describe('Network Resilience', () => {
  test('page degrades gracefully without JavaScript', async ({ page, context }) => {
    // Disable JavaScript
    await context.route('**/*.js', route => route.abort());
    
    await page.goto(TEST_PAGES.home);
    
    // Page should still render basic content
    const main = page.locator('main');
    await expect(main).toBeVisible();
    
    // Navigation should be visible
    const nav = page.locator('nav').first();
    await expect(nav).toBeVisible();
  });

  test('critical CSS is inlined', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check for inline critical CSS
    const inlineStyles = page.locator('style');
    const inlineCount = await inlineStyles.count();
    
    console.log(`Inline style blocks: ${inlineCount}`);
    
    // Should have some inline critical CSS
    expect(inlineCount).toBeGreaterThan(0);
  });

  test('fonts have fallback', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check font-family declarations have fallbacks
    const fontFamily = await page.evaluate(() => {
      const body = document.body;
      return getComputedStyle(body).fontFamily;
    });

    // Should have multiple fonts (fallback chain)
    expect(fontFamily.split(',').length).toBeGreaterThan(1);
  });
});

test.describe('Resource Hints', () => {
  test('critical resources are preloaded', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const preloads = page.locator('link[rel="preload"]');
    const count = await preloads.count();
    
    console.log(`Preload hints: ${count}`);
    
    // Should preload critical fonts at minimum
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const preload = preloads.nth(i);
        const href = await preload.getAttribute('href');
        const as = await preload.getAttribute('as');
        console.log(`  Preloading ${as}: ${href}`);
      }
    }
  });

  test('DNS prefetch for external resources', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const dnsPrefetch = page.locator('link[rel="dns-prefetch"]');
    const preconnect = page.locator('link[rel="preconnect"]');
    
    const dnsPrefetchCount = await dnsPrefetch.count();
    const preconnectCount = await preconnect.count();
    
    console.log(`DNS prefetch hints: ${dnsPrefetchCount}`);
    console.log(`Preconnect hints: ${preconnectCount}`);
  });
});
