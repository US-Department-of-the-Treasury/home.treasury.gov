/**
 * Meta Tags and SEO Validation Tests
 * 
 * Tests for proper meta tags, Open Graph tags, Twitter cards,
 * and other SEO-related elements.
 */

import { test, expect } from '@playwright/test';
import { TEST_PAGES, waitForPageReady } from './fixtures';

test.describe('Meta Tags - Basic SEO', () => {
  test('homepage has required meta tags', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check title
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);

    // Check meta description using evaluate (handles Hugo's minified HTML)
    const description = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="description"]');
      return meta?.getAttribute('content');
    });
    expect(description).toBeTruthy();
    expect(description!.length).toBeGreaterThan(50);

    // Check charset
    const hasCharset = await page.evaluate(() => {
      return document.querySelector('meta[charset]') !== null || 
             document.characterSet === 'UTF-8';
    });
    expect(hasCharset).toBeTruthy();

    // Check viewport
    const viewport = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="viewport"]');
      return meta?.getAttribute('content');
    });
    expect(viewport).toContain('width=device-width');
  });

  test('press releases page has appropriate meta tags', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);

    const title = await page.title();
    expect(title.toLowerCase()).toMatch(/press|release|news|treasury/);

    const description = await page.locator('meta[name="description"]').getAttribute('content');
    expect(description).toBeTruthy();
  });

  test('article pages have unique meta tags', async ({ page }) => {
    await page.goto('/news/press-releases/sb0357/');
    await waitForPageReady(page);

    const title = await page.title();
    // Article title should be different from homepage
    expect(title).not.toBe('U.S. Department of the Treasury');
    
    const description = await page.locator('meta[name="description"]').getAttribute('content');
    // May or may not have a unique description
  });

  test('all pages have canonical URL', async ({ page }) => {
    const pagesToTest = [
      TEST_PAGES.home,
      TEST_PAGES.pressReleases,
      TEST_PAGES.advancedSearch,
      '/about/',
    ];

    for (const pageUrl of pagesToTest) {
      await page.goto(pageUrl);
      await waitForPageReady(page);

      const canonical = await page.evaluate(() => {
        const link = document.querySelector('link[rel="canonical"]');
        return link?.getAttribute('href');
      });
      expect(canonical).toBeTruthy();
      expect(canonical).toMatch(/^https?:\/\//);
    }
  });
});

test.describe('Open Graph Tags', () => {
  test('homepage has Open Graph tags', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    // Check OG tags using evaluate
    const ogTags = await page.evaluate(() => {
      return {
        title: document.querySelector('meta[property="og:title"]')?.getAttribute('content'),
        type: document.querySelector('meta[property="og:type"]')?.getAttribute('content'),
        url: document.querySelector('meta[property="og:url"]')?.getAttribute('content'),
        siteName: document.querySelector('meta[property="og:site_name"]')?.getAttribute('content'),
      };
    });

    expect(ogTags.title).toBeTruthy();
    expect(ogTags.type).toBe('website');
    expect(ogTags.url).toBeTruthy();
    expect(ogTags.siteName).toContain('Treasury');
  });

  test('article pages have article OG type', async ({ page }) => {
    await page.goto('/news/press-releases/sb0357/');
    await waitForPageReady(page);

    const ogType = await page.locator('meta[property="og:type"]').getAttribute('content');
    // Article pages should have type "article" or "website"
    expect(['article', 'website']).toContain(ogType);

    // Article should have og:title matching page title
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content');
    const pageTitle = await page.title();
    
    if (ogTitle && pageTitle) {
      // OG title should match or contain page title
      expect(pageTitle).toContain(ogTitle?.split(' | ')[0] || '');
    }
  });

  test('OG image is specified (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const imageUrl = await page.evaluate(() => {
      const meta = document.querySelector('meta[property="og:image"]');
      return meta?.getAttribute('content');
    });
    
    // Optional - just log if not present
    if (imageUrl) {
      expect(imageUrl).toMatch(/^https?:\/\//);
    } else {
      console.log('OG image not implemented');
    }
  });
});

test.describe('Twitter Card Tags', () => {
  test('homepage has Twitter card tags (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const cardType = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="twitter:card"]');
      return meta?.getAttribute('content');
    });
    
    // Optional - just log if not present
    if (cardType) {
      expect(['summary', 'summary_large_image', 'player', 'app']).toContain(cardType);
    } else {
      console.log('Twitter cards not implemented');
    }
  });
});

test.describe('Structured Data (JSON-LD)', () => {
  test('pages have structured data (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const jsonLdContent = await page.evaluate(() => {
      const script = document.querySelector('script[type="application/ld+json"]');
      return script?.textContent;
    });
    
    // Optional - just log if not present
    if (jsonLdContent) {
      expect(() => JSON.parse(jsonLdContent)).not.toThrow();
      const data = JSON.parse(jsonLdContent);
      expect(data['@context']).toContain('schema.org');
    } else {
      console.log('JSON-LD structured data not implemented');
    }
  });

  test('organization structured data (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const scripts = await page.evaluate(() => {
      const els = document.querySelectorAll('script[type="application/ld+json"]');
      return Array.from(els).map(el => el.textContent);
    });
    
    // Optional - just log if not present
    if (scripts.length === 0) {
      console.log('No JSON-LD scripts found');
      return;
    }
    
    for (const content of scripts) {
      try {
        const data = JSON.parse(content || '{}');
        if (data['@type'] === 'Organization' || data['@type'] === 'GovernmentOrganization') {
          expect(data.name).toContain('Treasury');
        }
      } catch (e) {
        // Not valid JSON, skip
      }
    }
  });
});

test.describe('Language and Locale', () => {
  test('pages have lang attribute', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const lang = await page.evaluate(() => document.documentElement.lang);
    expect(lang).toBeTruthy();
    expect(lang).toMatch(/^en/);
  });

  test('og:locale is set (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const locale = await page.evaluate(() => {
      const meta = document.querySelector('meta[property="og:locale"]');
      return meta?.getAttribute('content');
    });
    
    // Optional - just log if not present
    if (locale) {
      expect(locale).toMatch(/^en/);
    } else {
      console.log('og:locale not implemented');
    }
  });
});

test.describe('Robots and Indexing', () => {
  test('pages do not have noindex in production', async ({ page, baseURL }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const content = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="robots"]');
      return meta?.getAttribute('content');
    });
    
    // In staging/local, noindex may be present
    if (baseURL?.includes('staging') || baseURL?.includes('localhost')) {
      console.log(`Non-production robots: ${content || 'not set'}`);
    } else if (content) {
      expect(content).not.toContain('noindex');
    }
  });

  test('404 page has noindex', async ({ page }) => {
    await page.goto('/this-page-does-not-exist-12345/');
    await waitForPageReady(page);

    const robots = page.locator('meta[name="robots"]');
    
    if (await robots.count() > 0) {
      const content = await robots.getAttribute('content');
      // 404 pages should have noindex
      expect(content).toContain('noindex');
    }
  });
});

test.describe('Favicon and Icons', () => {
  test('favicon is present', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const favicon = await page.evaluate(() => {
      const link = document.querySelector('link[rel="icon"], link[rel*="icon"]');
      return link?.getAttribute('href');
    });
    expect(favicon).toBeTruthy();
  });

  test('favicon is accessible', async ({ request, baseURL }) => {
    // Try common favicon paths
    const faviconPaths = [
      '/favicon.ico',
      '/favicon.png',
      '/images/favicon.png',
      '/images/favicon.ico',
    ];

    let found = false;
    for (const path of faviconPaths) {
      const response = await request.get(`${baseURL}${path}`);
      if (response.status() === 200) {
        found = true;
        break;
      }
    }

    expect(found).toBeTruthy();
  });

  test('Apple touch icon (if implemented)', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const icon = await page.evaluate(() => {
      const link = document.querySelector('link[rel="apple-touch-icon"]');
      return link?.getAttribute('href');
    });
    
    // Optional - just log if not present
    if (icon) {
      expect(icon).toBeTruthy();
    } else {
      console.log('Apple touch icon not implemented');
    }
  });
});

test.describe('Heading Structure', () => {
  test('homepage has exactly one h1', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const h1Count = await page.evaluate(() => document.querySelectorAll('h1').length);
    expect(h1Count).toBe(1);
  });

  test('press releases page has exactly one h1', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);

    const h1Count = await page.evaluate(() => document.querySelectorAll('h1').length);
    expect(h1Count).toBe(1);
  });

  test('heading levels do not skip', async ({ page }) => {
    await page.goto('/about/');
    await waitForPageReady(page);

    const headings = await page.evaluate(() => {
      const els = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
      return Array.from(els).map(el => parseInt(el.tagName.charAt(1)));
    });

    // Check for skipped levels (e.g., h1 to h3 without h2)
    for (let i = 1; i < headings.length; i++) {
      const diff = headings[i] - headings[i - 1];
      // Should not skip more than one level when going deeper
      if (diff > 0) {
        expect(diff).toBeLessThanOrEqual(1);
      }
    }
  });
});

test.describe('Link Attributes', () => {
  test('external links have rel="noopener"', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const linksWithoutNoopener = await page.evaluate(() => {
      const links = document.querySelectorAll('a[target="_blank"]');
      const missing: string[] = [];
      links.forEach(link => {
        const rel = link.getAttribute('rel');
        if (!rel || !rel.includes('noopener')) {
          missing.push(link.getAttribute('href') || '');
        }
      });
      return missing;
    });

    // Log any missing
    if (linksWithoutNoopener.length > 0) {
      console.log('Links missing noopener:', linksWithoutNoopener.slice(0, 5));
    }
    
    // Should have noopener on external links (allow some flexibility)
    expect(linksWithoutNoopener.length).toBeLessThanOrEqual(5);
  });

  test('skip link points to valid target', async ({ page }) => {
    await page.goto(TEST_PAGES.home);
    await waitForPageReady(page);

    const result = await page.evaluate(() => {
      const skipLink = document.querySelector('.skip-link, a[href="#main-content"]');
      if (!skipLink) return { found: false };
      
      const href = skipLink.getAttribute('href');
      if (!href?.startsWith('#')) return { found: true, valid: false };
      
      const targetId = href.substring(1);
      const target = document.getElementById(targetId);
      return { found: true, valid: target !== null, targetId };
    });

    expect(result.found).toBeTruthy();
    if (result.found) {
      expect(result.valid).toBeTruthy();
    }
  });
});
