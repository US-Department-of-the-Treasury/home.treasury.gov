#!/usr/bin/env node
// Fast parallel audit of Hugo vs Drupal pages - generic file input
import { readFileSync, writeFileSync, existsSync } from 'fs';

const CONCURRENT_REQUESTS = 50;
const BASE_URL = 'https://home.treasury.gov';

function extractTitle(html) {
    const match = html.match(/<title>([^<]*)<\/title>/i);
    return match ? match[1].trim() : '';
}

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

async function main() {
    const inputFile = process.argv[2];
    const outputFile = process.argv[3];

    if (!inputFile || !outputFile) {
        console.error('Usage: node audit-file.mjs <input.json> <output.json>');
        process.exit(1);
    }

    if (!existsSync(inputFile)) {
        console.error(`Input file not found: ${inputFile}`);
        process.exit(1);
    }

    console.error(`Auditing ${inputFile}...`);
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
