#!/usr/bin/env node
// Fast parallel audit of Hugo vs Drupal pages
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { execSync } from 'child_process';

const CONCURRENT_REQUESTS = 50;
const BASE_URL = 'https://home.treasury.gov';

// Extract title from HTML
function extractTitle(html) {
    const match = html.match(/<title>([^<]*)<\/title>/i);
    return match ? match[1].trim() : '';
}

// Read Hugo title from local file
function getHugoTitle(url) {
    let path = `public${url}`;
    if (url.endsWith('/')) {
        path = `public${url}index.html`;
    } else {
        path = `public${url}/index.html`;
    }

    if (!existsSync(path)) {
        return 'FILE_NOT_FOUND';
    }

    const html = readFileSync(path, 'utf8');
    return extractTitle(html);
}

// Fetch Drupal page title
async function getDrupalTitle(url) {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`${BASE_URL}${url}`, {
            signal: controller.signal,
            headers: { 'User-Agent': 'Mozilla/5.0 Treasury Audit Bot' }
        });
        clearTimeout(timeout);

        if (!response.ok) {
            return 'HTTP_' + response.status;
        }

        const html = await response.text();
        return extractTitle(html);
    } catch (e) {
        return 'FETCH_FAILED';
    }
}

// Normalize title for comparison (decode HTML entities, normalize whitespace)
function normalizeTitle(title) {
    return title
        .replace(/&amp;/g, '&')
        .replace(/&#039;/g, "'")
        .replace(/&quot;/g, '"')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/\s+/g, ' ')
        .trim();
}

// Audit a single URL
async function auditUrl(url) {
    const hugoTitle = getHugoTitle(url);
    const drupalTitle = await getDrupalTitle(url);

    const hugoNorm = normalizeTitle(hugoTitle);
    const drupalNorm = normalizeTitle(drupalTitle);

    return {
        url,
        hugo_title: hugoTitle,
        drupal_title: drupalTitle,
        title_match: hugoNorm === drupalNorm
    };
}

// Process URLs in batches
async function processBatch(urls, concurrency) {
    const results = [];
    let processed = 0;

    for (let i = 0; i < urls.length; i += concurrency) {
        const batch = urls.slice(i, i + concurrency);
        const batchResults = await Promise.all(batch.map(u => auditUrl(u.url)));
        results.push(...batchResults);
        processed += batch.length;
        process.stderr.write(`\r${processed}/${urls.length} URLs processed`);
    }
    process.stderr.write('\n');

    return results;
}

// Main
async function main() {
    const batchNum = process.argv[2];
    if (!batchNum) {
        console.error('Usage: node audit-all.mjs <batch-number>');
        process.exit(1);
    }

    const inputFile = `audit/news/batches/batch-${batchNum}.json`;
    const outputFile = `audit/news/results/batch-${batchNum}.json`;

    if (!existsSync(inputFile)) {
        console.error(`Input file not found: ${inputFile}`);
        process.exit(1);
    }

    console.error(`Auditing batch ${batchNum}...`);
    const urls = JSON.parse(readFileSync(inputFile, 'utf8'));
    const results = await processBatch(urls, CONCURRENT_REQUESTS);

    writeFileSync(outputFile, JSON.stringify(results, null, 2));

    const matches = results.filter(r => r.title_match).length;
    console.error(`Done: ${matches}/${results.length} matches`);
    console.log(`${outputFile}: ${matches}/${results.length}`);
}

main().catch(e => {
    console.error(e);
    process.exit(1);
});
