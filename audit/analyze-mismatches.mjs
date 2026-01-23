#!/usr/bin/env node
import { readFileSync, readdirSync } from 'fs';

const resultsDir = 'audit/news/results';
const files = readdirSync(resultsDir).filter(f => f.endsWith('.json'));

let allResults = [];
for (const file of files) {
    const data = JSON.parse(readFileSync(`${resultsDir}/${file}`, 'utf8'));
    allResults.push(...data);
}

const mismatches = allResults.filter(r => !r.title_match);

// Categorize mismatches
const categories = {
    fetch_failed: [],
    empty_drupal_title: [],
    http_error: [],
    hugo_not_found: [],
    actual_title_diff: []
};

for (const m of mismatches) {
    if (m.drupal_title === 'FETCH_FAILED') {
        categories.fetch_failed.push(m);
    } else if (m.drupal_title === '' || m.drupal_title === null) {
        categories.empty_drupal_title.push(m);
    } else if (m.drupal_title && m.drupal_title.startsWith('HTTP_')) {
        categories.http_error.push(m);
    } else if (m.hugo_title === 'FILE_NOT_FOUND') {
        categories.hugo_not_found.push(m);
    } else {
        categories.actual_title_diff.push(m);
    }
}

console.log('=== MISMATCH ANALYSIS ===\n');
console.log(`Total URLs: ${allResults.length}`);
console.log(`Matches: ${allResults.filter(r => r.title_match).length}`);
console.log(`Mismatches: ${mismatches.length}\n`);

console.log('=== MISMATCH CATEGORIES ===\n');
console.log(`FETCH_FAILED (Drupal timeout): ${categories.fetch_failed.length}`);
console.log(`Empty Drupal title: ${categories.empty_drupal_title.length}`);
console.log(`HTTP errors (503, etc): ${categories.http_error.length}`);
console.log(`Hugo FILE_NOT_FOUND: ${categories.hugo_not_found.length}`);
console.log(`Actual title differences: ${categories.actual_title_diff.length}\n`);

if (categories.actual_title_diff.length > 0) {
    console.log('=== SAMPLE ACTUAL TITLE DIFFERENCES (first 20) ===\n');
    for (const m of categories.actual_title_diff.slice(0, 20)) {
        console.log(`URL: ${m.url}`);
        console.log(`  Hugo:   ${m.hugo_title.substring(0, 80)}...`);
        console.log(`  Drupal: ${m.drupal_title.substring(0, 80)}...`);
        console.log('');
    }
}

// Write detailed results
const summary = {
    total: allResults.length,
    matches: allResults.filter(r => r.title_match).length,
    mismatches: mismatches.length,
    categories: {
        fetch_failed: categories.fetch_failed.length,
        empty_drupal_title: categories.empty_drupal_title.length,
        http_error: categories.http_error.length,
        hugo_not_found: categories.hugo_not_found.length,
        actual_title_diff: categories.actual_title_diff.length
    },
    actual_differences: categories.actual_title_diff
};

console.log('\n=== Writing detailed results to audit/news/mismatch-analysis.json ===');
import { writeFileSync } from 'fs';
writeFileSync('audit/news/mismatch-analysis.json', JSON.stringify(summary, null, 2));
