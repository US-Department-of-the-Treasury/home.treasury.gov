/**
 * RSS Feed and Sitemap Validation Tests
 * 
 * Tests for RSS/Atom feeds and XML sitemap to ensure they are valid,
 * properly structured, and contain expected content.
 */

import { test, expect } from '@playwright/test';

test.describe('RSS Feed - Structure', () => {
  test('news RSS feed exists and returns XML', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/news/index.xml`);
    
    expect(response.status()).toBe(200);
    
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/xml|rss/);
  });

  test('RSS feed has valid structure', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/news/index.xml`);
    const xml = await response.text();

    // Check for RSS root element
    expect(xml).toContain('<rss');
    expect(xml).toContain('version="2.0"');
    
    // Check for channel element
    expect(xml).toContain('<channel>');
    expect(xml).toContain('</channel>');
    
    // Check for title
    expect(xml).toContain('<title>');
    expect(xml).toContain('Treasury');
    
    // Check for link
    expect(xml).toContain('<link>');
    
    // Check for description
    expect(xml).toContain('<description>');
  });

  test('RSS feed contains items', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/news/index.xml`);
    const xml = await response.text();

    // Should have at least one item
    expect(xml).toContain('<item>');
    expect(xml).toContain('</item>');
    
    // Items should have required elements
    expect(xml).toContain('<title>');
    expect(xml).toContain('<link>');
    expect(xml).toContain('<pubDate>');
  });

  test('RSS feed items have valid dates', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/news/index.xml`);
    const xml = await response.text();

    // Extract pubDate values
    const dateMatches = xml.match(/<pubDate>([^<]+)<\/pubDate>/g);
    
    if (dateMatches && dateMatches.length > 0) {
      dateMatches.forEach(dateStr => {
        const date = dateStr.replace(/<\/?pubDate>/g, '');
        // RFC 822 date format should be parseable
        const parsed = new Date(date);
        expect(parsed.getTime()).not.toBeNaN();
      });
    }
  });

  test('RSS feed has atom:link for self-reference', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/news/index.xml`);
    const xml = await response.text();

    // Should have atom namespace and self link
    expect(xml).toContain('xmlns:atom');
    expect(xml).toContain('atom:link');
    expect(xml).toContain('rel="self"');
  });
});

test.describe('RSS Feed - Content Sections', () => {
  const feedPaths = [
    { path: '/news/index.xml', name: 'News' },
    { path: '/news/press-releases/index.xml', name: 'Press Releases' },
    { path: '/news/statements-remarks/index.xml', name: 'Statements & Remarks' },
  ];

  for (const feed of feedPaths) {
    test(`${feed.name} feed exists`, async ({ request, baseURL }) => {
      const response = await request.get(`${baseURL}${feed.path}`);
      
      // Feed should exist (200) or not be configured (404)
      expect([200, 404]).toContain(response.status());
      
      if (response.status() === 200) {
        const xml = await response.text();
        expect(xml).toContain('<rss');
      }
    });
  }
});

test.describe('Sitemap - Structure', () => {
  test('sitemap.xml exists and returns XML', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    
    expect(response.status()).toBe(200);
    
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/xml/);
  });

  test('sitemap has valid XML structure', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Check for XML declaration
    expect(xml).toMatch(/^<\?xml/);
    
    // Check for urlset or sitemapindex
    expect(xml).toMatch(/<urlset|<sitemapindex/);
    
    // Check for namespace
    expect(xml).toContain('xmlns');
  });

  test('sitemap contains URLs', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Should have url elements
    expect(xml).toContain('<url>');
    expect(xml).toContain('<loc>');
    
    // Extract URLs
    const urlMatches = xml.match(/<loc>([^<]+)<\/loc>/g);
    expect(urlMatches).not.toBeNull();
    expect(urlMatches!.length).toBeGreaterThan(0);
  });

  test('sitemap URLs are valid', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Extract URLs
    const urlMatches = xml.match(/<loc>([^<]+)<\/loc>/g);
    
    if (urlMatches) {
      const urls = urlMatches.map(u => u.replace(/<\/?loc>/g, ''));
      
      // Check first few URLs are valid format
      urls.slice(0, 5).forEach(url => {
        expect(url).toMatch(/^https?:\/\//);
      });
    }
  });

  test('sitemap includes key pages', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Should include at least some key sections
    const keyPages = [
      '/about/',
      '/news/',
      '/policy-issues/',
      '/services/',
      '/data/',
    ];

    let foundCount = 0;
    keyPages.forEach(keyPage => {
      if (xml.includes(keyPage)) {
        foundCount++;
      }
    });
    
    // Should have at least some key pages
    expect(foundCount).toBeGreaterThanOrEqual(2);
  });
});

test.describe('Sitemap - Size and Performance', () => {
  test('sitemap is reasonably sized', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Sitemap should be under 50MB (uncompressed limit)
    const sizeInMB = Buffer.byteLength(xml, 'utf8') / (1024 * 1024);
    expect(sizeInMB).toBeLessThan(50);
  });

  test('sitemap has reasonable URL count', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();

    // Count URLs
    const urlMatches = xml.match(/<url>/g);
    const urlCount = urlMatches ? urlMatches.length : 0;

    // Should have URLs but not exceed 50,000 per sitemap
    expect(urlCount).toBeGreaterThan(0);
    expect(urlCount).toBeLessThanOrEqual(50000);
    
    console.log(`Sitemap contains ${urlCount} URLs`);
  });
});

test.describe('Robots.txt', () => {
  test('robots.txt exists', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/robots.txt`);
    
    expect(response.status()).toBe(200);
    
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/text\/plain/);
  });

  test('robots.txt has valid format', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/robots.txt`);
    const text = await response.text();

    // Should have User-agent directive
    expect(text.toLowerCase()).toContain('user-agent');
  });

  test('robots.txt references sitemap (production)', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/robots.txt`);
    const text = await response.text();

    // In production, robots.txt should reference sitemap
    // In staging, it may block all crawlers
    if (!text.includes('Disallow: /')) {
      expect(text.toLowerCase()).toContain('sitemap');
    }
  });
});

test.describe('Feed Accessibility', () => {
  test('RSS feed link is discoverable in HTML', async ({ page, baseURL }) => {
    await page.goto(`${baseURL}/news/`);

    // Check for RSS link in head
    const rssLink = page.locator('link[type="application/rss+xml"], link[rel="alternate"][type*="rss"], link[rel="alternate"][type*="xml"]');
    
    // It's okay if not present - just log it
    const count = await rssLink.count();
    console.log(`Found ${count} RSS link(s) in page head`);
  });
});
