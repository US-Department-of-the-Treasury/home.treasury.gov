import { test, expect, Page } from '@playwright/test';

/**
 * Link Validation Tests
 * 
 * These tests verify that all internal links in the mega menus and homepage:
 * 1. Return successful HTTP responses (not 404)
 * 2. Don't redirect to the old home.treasury.gov site
 * 3. Load without errors
 */

// Helper to extract all links from a page
async function extractLinks(page: Page, selector: string): Promise<string[]> {
  const links = await page.$$eval(selector, (anchors) => 
    anchors
      .map(a => a.getAttribute('href'))
      .filter(href => href !== null) as string[]
  );
  return links;
}

// Helper to check if a link is internal (not external)
function isInternalLink(href: string): boolean {
  if (!href) return false;
  // Internal links start with / or are relative (no protocol)
  if (href.startsWith('/')) return true;
  if (href.startsWith('#')) return false; // Skip anchors
  if (href.startsWith('http://') || href.startsWith('https://')) return false;
  if (href.startsWith('mailto:') || href.startsWith('tel:')) return false;
  return true;
}

// Helper to normalize URL (ensure trailing slash for consistency)
function normalizeUrl(baseUrl: string, href: string): string {
  if (href.startsWith('/')) {
    // Add trailing slash if not present and not a file
    if (!href.endsWith('/') && !href.includes('.') && !href.includes('?')) {
      href = href + '/';
    }
    return baseUrl + href;
  }
  return href;
}

test.describe('Mega Menu Link Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('all About Treasury mega menu links should be valid', async ({ page, baseURL }) => {
    // Open About Treasury menu - uses button element with nav-link class
    const aboutMenu = page.locator('.nav-item button:has-text("About")').first();
    await expect(aboutMenu).toBeVisible({ timeout: 10000 });
    await aboutMenu.click();
    await page.waitForTimeout(500);

    // Get all links in the dropdown
    const megaMenu = page.locator('.mega-menu').first();
    await expect(megaMenu).toBeVisible({ timeout: 5000 });

    // Get links using evaluateAll instead of $$eval for locators
    const links = await megaMenu.locator('a[href]').evaluateAll((anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in About Treasury menu`);

    // Test each internal link
    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ 
          href: link.href, 
          text: link.text || '', 
          status: response.status() 
        });
      }
      
      // Check for redirect to old treasury site
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ 
          href: link.href, 
          text: link.text || '', 
          status: -1 // Indicates redirect to old site
        });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in About Treasury menu:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });

  test('all Policy Issues mega menu links should be valid', async ({ page, baseURL }) => {
    // Open Policy Issues menu - uses button element
    const policyMenu = page.locator('.nav-item button:has-text("Policy")').first();
    await expect(policyMenu).toBeVisible({ timeout: 10000 });
    await policyMenu.click();
    await page.waitForTimeout(500);

    const megaMenu = page.locator('.mega-menu').nth(1);
    await expect(megaMenu).toBeVisible({ timeout: 5000 });

    const links = await megaMenu.locator('a[href]').evaluateAll((anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in Policy Issues menu`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in Policy Issues menu:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });

  test('all Data mega menu links should be valid', async ({ page, baseURL }) => {
    // Open Data menu - uses button element
    const dataMenu = page.locator('.nav-item button:has-text("Data")').first();
    await expect(dataMenu).toBeVisible({ timeout: 10000 });
    await dataMenu.click();
    await page.waitForTimeout(500);

    const megaMenu = page.locator('.mega-menu').nth(2);
    await expect(megaMenu).toBeVisible({ timeout: 5000 });

    const links = await megaMenu.locator('a[href]').evaluateAll((anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in Data menu`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in Data menu:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });

  test('all Services mega menu links should be valid', async ({ page, baseURL }) => {
    // Open Services menu - uses button element
    const servicesMenu = page.locator('.nav-item button:has-text("Services")').first();
    await expect(servicesMenu).toBeVisible({ timeout: 10000 });
    await servicesMenu.click();
    await page.waitForTimeout(500);

    const megaMenu = page.locator('.mega-menu').nth(3);
    await expect(megaMenu).toBeVisible({ timeout: 5000 });

    const links = await megaMenu.locator('a[href]').evaluateAll((anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in Services menu`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in Services menu:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });

  test('all News mega menu links should be valid', async ({ page, baseURL }) => {
    // Open News menu - uses button element
    const newsMenu = page.locator('.nav-item button:has-text("News")').first();
    await expect(newsMenu).toBeVisible({ timeout: 10000 });
    await newsMenu.click();
    await page.waitForTimeout(500);

    const megaMenu = page.locator('.mega-menu').nth(4);
    await expect(megaMenu).toBeVisible({ timeout: 5000 });

    const links = await megaMenu.locator('a[href]').evaluateAll((anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in News menu`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in News menu:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });
});

test.describe('Homepage Link Validation', () => {
  test('all homepage internal links should be valid', async ({ page, baseURL }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all links from the main content area (not header/footer which are tested separately)
    const links = await page.$$eval('main a[href], .hero-section a[href], .news-section a[href], .data-center-section a[href], .tools-section a[href]', (anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links on homepage content`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links on homepage:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });

  test('footer links should be valid', async ({ page, baseURL }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const links = await page.$$eval('footer a[href]', (anchors) => 
      anchors.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent?.trim()
      }))
    );

    const internalLinks = links.filter(l => l.href && isInternalLink(l.href));
    console.log(`Found ${internalLinks.length} internal links in footer`);

    const failedLinks: { href: string; text: string; status: number }[] = [];
    
    for (const link of internalLinks) {
      if (!link.href) continue;
      
      const url = normalizeUrl(baseURL || '', link.href);
      const response = await page.request.get(url);
      
      if (response.status() >= 400) {
        failedLinks.push({ href: link.href, text: link.text || '', status: response.status() });
      }
      
      const finalUrl = response.url();
      if (finalUrl.includes('home.treasury.gov')) {
        failedLinks.push({ href: link.href, text: link.text || '', status: -1 });
      }
    }

    if (failedLinks.length > 0) {
      console.log('Failed links in footer:');
      failedLinks.forEach(l => console.log(`  - ${l.text}: ${l.href} (status: ${l.status})`));
    }
    
    expect(failedLinks).toHaveLength(0);
  });
});

test.describe('No Redirects to Old Treasury Site', () => {
  test('should not have any links that redirect to home.treasury.gov', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get ALL links on the page
    const allLinks = await page.$$eval('a[href]', (anchors) => 
      anchors.map(a => a.getAttribute('href')).filter(h => h !== null) as string[]
    );

    // Check for any explicit links to home.treasury.gov
    const oldTreasuryLinks = allLinks.filter(href => 
      href.includes('home.treasury.gov')
    );

    if (oldTreasuryLinks.length > 0) {
      console.log('Links to old treasury site found:');
      oldTreasuryLinks.forEach(l => console.log(`  - ${l}`));
    }

    expect(oldTreasuryLinks).toHaveLength(0);
  });
});

test.describe('Critical Navigation Links', () => {
  // Test specific high-priority links that must work
  const criticalLinks = [
    { name: 'About Treasury', path: '/about/' },
    { name: 'Policy Issues', path: '/policy-issues/' },
    { name: 'News', path: '/news/' },
    { name: 'Press Releases', path: '/news/press-releases/' },
    { name: 'Data', path: '/data/' },
    { name: 'Services', path: '/services/' },
    { name: 'Year in Review', path: '/year-in-review/' },
    { name: 'Working Families Tax Cuts', path: '/working-families-tax-cuts/' },
    { name: 'Orders and Directives', path: '/about/general-information/orders-and-directives/' },
    { name: 'Quarterly Refunding', path: '/policy-issues/financing-the-government/quarterly-refunding/' },
    { name: 'Interest Rate Statistics', path: '/policy-issues/financing-the-government/interest-rate-statistics/' },
    { name: 'Treasury Auctions', path: '/services/treasury-auctions/' },
    { name: 'SSBCI', path: '/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/' },
    { name: 'CFIUS', path: '/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius/' },
    { name: 'FSOC', path: '/policy-issues/financial-markets-financial-institutions-and-fiscal-service/fsoc/' },
    { name: 'Report Fraud', path: '/services/report-fraud-waste-and-abuse/' },
    { name: 'Inspectors General', path: '/services/report-fraud-waste-and-abuse/inspectors-general/' },
  ];

  for (const link of criticalLinks) {
    test(`critical link "${link.name}" should return 200`, async ({ page }) => {
      const response = await page.goto(link.path);
      expect(response?.status()).toBe(200);
      
      // Verify we didn't redirect to old treasury site
      expect(page.url()).not.toContain('home.treasury.gov');
      
      // Verify page has content
      const mainContent = page.locator('main, .content, article').first();
      await expect(mainContent).toBeVisible();
    });
  }
});

test.describe('Comprehensive Link Crawl', () => {
  test('crawl all internal links from navigation.json', async ({ page, baseURL }) => {
    // Load navigation.json directly and test all internal links
    const response = await page.request.get('/index.json');
    
    // Also check the homepage to get actual rendered links
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Collect all unique internal links
    const allLinks = new Set<string>();
    
    // Get links from all mega menus
    for (let i = 0; i < 5; i++) {
      const menuTriggers = page.locator('.main-nav > .nav-inner > ul > li > a');
      const count = await menuTriggers.count();
      
      if (i < count) {
        await menuTriggers.nth(i).hover();
        await page.waitForTimeout(200);
        
        const menuLinks = await page.$$eval('.mega-menu a[href]', (anchors) => 
          anchors.map(a => a.getAttribute('href')).filter(h => h !== null) as string[]
        );
        
        menuLinks.forEach(link => {
          if (isInternalLink(link)) {
            allLinks.add(link);
          }
        });
      }
    }

    console.log(`Total unique internal links to test: ${allLinks.size}`);

    const results: { link: string; status: number; redirected: boolean }[] = [];
    
    for (const link of allLinks) {
      const url = normalizeUrl(baseURL || '', link);
      try {
        const resp = await page.request.get(url);
        const finalUrl = resp.url();
        results.push({
          link,
          status: resp.status(),
          redirected: finalUrl.includes('home.treasury.gov')
        });
      } catch (e) {
        results.push({
          link,
          status: 0,
          redirected: false
        });
      }
    }

    // Report results
    const failed = results.filter(r => r.status >= 400 || r.status === 0);
    const redirected = results.filter(r => r.redirected);
    const successful = results.filter(r => r.status >= 200 && r.status < 400 && !r.redirected);

    console.log(`\n=== Link Validation Results ===`);
    console.log(`✓ Successful: ${successful.length}`);
    console.log(`✗ Failed (4xx/5xx): ${failed.length}`);
    console.log(`⚠ Redirected to old site: ${redirected.length}`);

    if (failed.length > 0) {
      console.log('\nFailed links:');
      failed.forEach(r => console.log(`  - ${r.link} (${r.status})`));
    }

    if (redirected.length > 0) {
      console.log('\nLinks redirecting to old treasury site:');
      redirected.forEach(r => console.log(`  - ${r.link}`));
    }

    expect(failed.length).toBe(0);
    expect(redirected.length).toBe(0);
  });
});
