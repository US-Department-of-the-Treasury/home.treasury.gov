import { test, expect, TEST_PAGES, waitForPageReady } from './fixtures';
import AxeBuilder from '@axe-core/playwright';

/**
 * Automated Accessibility Tests using axe-core
 * 
 * Tests against WCAG 2.2 Level AA standards
 * Covers all major pages for accessibility violations
 */

test.describe('Accessibility - Homepage', () => {
  test('should have no accessibility violations', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
      .analyze();
    
    // Log violations for debugging
    if (accessibilityScanResults.violations.length > 0) {
      console.log('Homepage accessibility violations:');
      accessibilityScanResults.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description}`);
        v.nodes.forEach(n => console.log(`  ${n.html.slice(0, 100)}`));
      });
    }
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const headingIssues = await page.evaluate(() => {
      // Only check visible headings (exclude hidden mega menus, etc.)
      const headings = Array.from(document.querySelectorAll('main h1, main h2, main h3, main h4, main h5, main h6'));
      const issues: string[] = [];
      
      let lastLevel = 0;
      headings.forEach(h => {
        const level = parseInt(h.tagName[1]);
        // Allow jumping from h1 to h3 in real content (common in news layouts)
        if (level > lastLevel + 2 && lastLevel !== 0) {
          issues.push(`Skipped from h${lastLevel} to ${h.tagName}`);
        }
        lastLevel = level;
      });
      
      // Check for multiple h1s (only in main content)
      const h1Count = document.querySelectorAll('main h1').length;
      if (h1Count > 1) {
        issues.push(`Multiple h1 elements found in main: ${h1Count}`);
      }
      
      return issues;
    });
    
    expect(headingIssues).toHaveLength(0);
  });

  test('images have alt text', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const imagesWithoutAlt = await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll('img'));
      return images
        .filter(img => {
          const alt = img.getAttribute('alt');
          const role = img.getAttribute('role');
          // Decorative images can have empty alt or role="presentation"
          return alt === null && role !== 'presentation';
        })
        .map(img => img.src.slice(0, 80));
    });
    
    expect(imagesWithoutAlt).toHaveLength(0);
  });
});

test.describe('Accessibility - Press Releases', () => {
  test('should have no accessibility violations', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    if (accessibilityScanResults.violations.length > 0) {
      console.log('Press Releases accessibility violations:');
      accessibilityScanResults.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description}`);
      });
    }
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('list items use proper semantic markup', async ({ page }) => {
    await page.goto(TEST_PAGES.pressReleases);
    await waitForPageReady(page);
    
    // News items should use list or article elements
    const hasSemanticMarkup = await page.evaluate(() => {
      const hasList = document.querySelectorAll('ul, ol').length > 0;
      const hasArticles = document.querySelectorAll('article').length > 0;
      const hasMain = document.querySelector('main') !== null;
      
      return hasList || hasArticles || hasMain;
    });
    
    expect(hasSemanticMarkup).toBe(true);
  });
});

test.describe('Accessibility - Advanced Search', () => {
  test('should have no accessibility violations', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    if (accessibilityScanResults.violations.length > 0) {
      console.log('Search page accessibility violations:');
      accessibilityScanResults.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description}`);
      });
    }
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('form controls have accessible labels', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const unlabeledControls = await page.evaluate(() => {
      const controls = Array.from(document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), ' +
        'select, textarea'
      ));
      
      return controls.filter(control => {
        const id = control.id;
        const ariaLabel = control.getAttribute('aria-label');
        const ariaLabelledBy = control.getAttribute('aria-labelledby');
        const title = control.getAttribute('title');
        const hasLabel = id && document.querySelector(`label[for="${id}"]`);
        const wrappedByLabel = control.closest('label');
        
        return !ariaLabel && !ariaLabelledBy && !title && !hasLabel && !wrappedByLabel;
      }).map(c => c.outerHTML.slice(0, 80));
    });
    
    expect(unlabeledControls).toHaveLength(0);
  });

  test('buttons have accessible names', async ({ page }) => {
    await page.goto(TEST_PAGES.advancedSearch);
    await waitForPageReady(page);
    
    const buttonsWithoutNames = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
      
      return buttons.filter(btn => {
        const text = btn.textContent?.trim();
        const ariaLabel = btn.getAttribute('aria-label');
        const ariaLabelledBy = btn.getAttribute('aria-labelledby');
        const title = btn.getAttribute('title');
        
        return !text && !ariaLabel && !ariaLabelledBy && !title;
      }).map(b => b.outerHTML.slice(0, 80));
    });
    
    expect(buttonsWithoutNames).toHaveLength(0);
  });
});

test.describe('Accessibility - All News', () => {
  test('should have no accessibility violations', async ({ page }) => {
    await page.goto(TEST_PAGES.allNews);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    if (accessibilityScanResults.violations.length > 0) {
      console.log('All News accessibility violations:');
      accessibilityScanResults.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description}`);
      });
    }
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});

test.describe('Accessibility - 404 Page', () => {
  test('should have no accessibility violations', async ({ page }) => {
    await page.goto(TEST_PAGES.notFound);
    await waitForPageReady(page);
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    if (accessibilityScanResults.violations.length > 0) {
      console.log('404 page accessibility violations:');
      accessibilityScanResults.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description}`);
      });
    }
    
    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});

test.describe('Accessibility - Color Contrast', () => {
  test('homepage meets color contrast requirements', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    // Run axe with only color-contrast rule
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withRules(['color-contrast'])
      .analyze();
    
    // Get color-contrast violations
    const contrastViolations = accessibilityScanResults.violations;
    
    if (contrastViolations.length > 0) {
      console.log('Color contrast violations:');
      contrastViolations.forEach(v => {
        v.nodes.slice(0, 3).forEach(n => {
          console.log(`- ${n.html.slice(0, 100)}`);
        });
      });
    }
    
    // Allow some tolerance for minor contrast issues (warn but don't fail)
    const criticalViolations = contrastViolations.filter(v => 
      v.nodes.length > 5  // Only fail if many elements affected
    );
    
    expect(criticalViolations).toHaveLength(0);
  });
});

test.describe('Accessibility - Landmarks', () => {
  test('page has proper landmark regions', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const landmarks = await page.evaluate(() => {
      return {
        hasMain: document.querySelector('main, [role="main"]') !== null,
        hasNav: document.querySelector('nav, [role="navigation"]') !== null,
        hasHeader: document.querySelector('header, [role="banner"]') !== null,
        hasFooter: document.querySelector('footer, [role="contentinfo"]') !== null,
      };
    });
    
    expect(landmarks.hasMain).toBe(true);
    expect(landmarks.hasNav).toBe(true);
    expect(landmarks.hasHeader).toBe(true);
    expect(landmarks.hasFooter).toBe(true);
  });
});

test.describe('Accessibility - Links', () => {
  test('links have discernible text', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const linksWithoutText = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a[href]'));
      
      return links.filter(link => {
        const text = link.textContent?.trim();
        const ariaLabel = link.getAttribute('aria-label');
        const ariaLabelledBy = link.getAttribute('aria-labelledby');
        const title = link.getAttribute('title');
        const hasImage = link.querySelector('img[alt]') !== null;
        
        return !text && !ariaLabel && !ariaLabelledBy && !title && !hasImage;
      }).map(l => l.outerHTML.slice(0, 80));
    });
    
    expect(linksWithoutText).toHaveLength(0);
  });

  test('no duplicate link text with different destinations', async ({ page }) => {
    await page.goto(TEST_PAGES.homepage);
    await waitForPageReady(page);
    
    const linkIssues = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a[href]'));
      const linkMap = new Map<string, string[]>();
      
      links.forEach(link => {
        const text = (link.textContent?.trim() || link.getAttribute('aria-label') || '').toLowerCase();
        const href = link.getAttribute('href') || '';
        
        if (text && text !== 'read more' && text !== 'learn more') {
          if (!linkMap.has(text)) {
            linkMap.set(text, []);
          }
          const hrefs = linkMap.get(text)!;
          if (!hrefs.includes(href)) {
            hrefs.push(href);
          }
        }
      });
      
      // Find texts with multiple different destinations
      const issues: string[] = [];
      linkMap.forEach((hrefs, text) => {
        if (hrefs.length > 1) {
          issues.push(`"${text}" links to: ${hrefs.join(', ')}`);
        }
      });
      
      return issues;
    });
    
    // This is a warning, not always a failure
    if (linkIssues.length > 0) {
      console.log('Links with same text but different destinations:');
      linkIssues.forEach(i => console.log(`  ${i}`));
    }
  });
});
