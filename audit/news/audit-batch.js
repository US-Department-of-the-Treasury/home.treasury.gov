const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function auditBatch(batchNumber) {
  const batchFile = path.join(__dirname, 'batches', `batch-${String(batchNumber).padStart(3, '0')}.json`);
  const resultsFile = path.join(__dirname, 'results', `batch-${String(batchNumber).padStart(3, '0')}.json`);

  // Read batch data
  const batchData = JSON.parse(fs.readFileSync(batchFile, 'utf8'));
  console.log(`Processing ${batchData.length} URLs from batch ${batchNumber}...`);

  // Launch browser
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = [];

  for (let i = 0; i < batchData.length; i++) {
    const item = batchData[i];
    const url = item.url;

    // Extract Hugo title from local file
    let hugoTitle = null;
    try {
      const hugoPath = path.join(__dirname, '..', '..', 'public', url, 'index.html');
      if (fs.existsSync(hugoPath)) {
        const hugoHtml = fs.readFileSync(hugoPath, 'utf8');
        const titleMatch = hugoHtml.match(/<title>([^<]+)<\/title>/);
        if (titleMatch) {
          hugoTitle = titleMatch[1].replace(' | U.S. Department of the Treasury', '').trim();
        }
      } else {
        hugoTitle = 'FILE_NOT_FOUND';
      }
    } catch (e) {
      hugoTitle = `ERROR: ${e.message}`;
    }

    // Navigate to Drupal site and extract title
    let drupalTitle = null;
    try {
      await page.goto(`https://home.treasury.gov${url}`, {
        timeout: 30000,
        waitUntil: 'domcontentloaded'
      });
      const fullTitle = await page.title();
      drupalTitle = fullTitle.replace(' | U.S. Department of the Treasury', '').trim();
    } catch (e) {
      drupalTitle = `ERROR: ${e.message}`;
    }

    const titleMatch = hugoTitle === drupalTitle;

    results.push({
      url: url,
      hugo_title: hugoTitle,
      drupal_title: drupalTitle,
      title_match: titleMatch
    });

    // Progress log
    if ((i + 1) % 10 === 0 || i === batchData.length - 1) {
      console.log(`Processed ${i + 1}/${batchData.length} URLs`);
    }
  }

  await browser.close();

  // Write results
  fs.mkdirSync(path.dirname(resultsFile), { recursive: true });
  fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));

  // Summary
  const matches = results.filter(r => r.title_match === true).length;
  const mismatches = results.filter(r => r.title_match === false).length;
  console.log(`\nCompleted batch ${batchNumber}:`);
  console.log(`  Total: ${results.length}`);
  console.log(`  Matches: ${matches}`);
  console.log(`  Mismatches: ${mismatches}`);
  console.log(`Results saved to: ${resultsFile}`);

  return results;
}

// Run with batch number from command line
const batchNum = parseInt(process.argv[2] || '7');
auditBatch(batchNum).catch(console.error);
