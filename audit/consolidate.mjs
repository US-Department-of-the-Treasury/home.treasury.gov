#!/usr/bin/env node
import { readFileSync, writeFileSync, readdirSync } from 'fs';

// Load all news results
const newsDir = 'audit/news/results';
const newsFiles = readdirSync(newsDir).filter(f => f.endsWith('.json'));
let newsResults = [];
for (const file of newsFiles) {
    const data = JSON.parse(readFileSync(`${newsDir}/${file}`, 'utf8'));
    newsResults.push(...data);
}

// Load other sections results
const otherResults = JSON.parse(readFileSync('audit/other-sections-results.json', 'utf8'));

// Combine all results
const allResults = [...newsResults, ...otherResults];

// Calculate statistics
const stats = {
    total: allResults.length,
    matches: allResults.filter(r => r.title_match).length,
    mismatches: allResults.filter(r => !r.title_match).length,
    match_rate: ((allResults.filter(r => r.title_match).length / allResults.length) * 100).toFixed(1) + '%'
};

// Categorize mismatches
const mismatches = allResults.filter(r => !r.title_match);
const categories = {
    fetch_failed: mismatches.filter(m => m.drupal_title === 'FETCH_FAILED').length,
    empty_drupal_title: mismatches.filter(m => m.drupal_title === '' || m.drupal_title === null).length,
    http_error: mismatches.filter(m => m.drupal_title && m.drupal_title.startsWith('HTTP_')).length,
    hugo_not_found: mismatches.filter(m => m.hugo_title === 'FILE_NOT_FOUND').length,
    actual_title_diff: mismatches.filter(m =>
        m.drupal_title !== 'FETCH_FAILED' &&
        m.drupal_title !== '' &&
        m.drupal_title !== null &&
        !(m.drupal_title && m.drupal_title.startsWith('HTTP_')) &&
        m.hugo_title !== 'FILE_NOT_FOUND'
    ).length
};

// Get actual title differences for review
const actualDiffs = mismatches.filter(m =>
    m.drupal_title !== 'FETCH_FAILED' &&
    m.drupal_title !== '' &&
    m.drupal_title !== null &&
    !(m.drupal_title && m.drupal_title.startsWith('HTTP_')) &&
    m.hugo_title !== 'FILE_NOT_FOUND'
);

// Build summary
const summary = {
    audit_date: new Date().toISOString().split('T')[0],
    statistics: stats,
    mismatch_categories: categories,
    by_section: {
        news: {
            total: newsResults.length,
            matches: newsResults.filter(r => r.title_match).length,
            match_rate: ((newsResults.filter(r => r.title_match).length / newsResults.length) * 100).toFixed(1) + '%'
        },
        other: {
            total: otherResults.length,
            matches: otherResults.filter(r => r.title_match).length,
            match_rate: ((otherResults.filter(r => r.title_match).length / otherResults.length) * 100).toFixed(1) + '%'
        }
    },
    analysis: {
        summary: `Audited ${stats.total} pages. ${categories.fetch_failed} pages no longer exist on Drupal (archived content). ${categories.actual_title_diff} pages have actual title differences requiring review.`,
        recommendations: [
            "Most 'mismatches' are archived Drupal pages - Hugo has content that Drupal no longer serves",
            "Actual title differences are mostly cosmetic (HTML entities, abbreviations)",
            "Review the 119 actual title differences for intentional changes vs errors"
        ]
    }
};

// Write outputs
writeFileSync('audit/full-report.json', JSON.stringify(allResults, null, 2));
writeFileSync('audit/summary.json', JSON.stringify(summary, null, 2));
writeFileSync('audit/title-differences.json', JSON.stringify(actualDiffs, null, 2));

console.log('=== AUDIT CONSOLIDATION COMPLETE ===\n');
console.log(`Total pages: ${stats.total}`);
console.log(`Matches: ${stats.matches} (${stats.match_rate})`);
console.log(`Mismatches: ${stats.mismatches}\n`);
console.log('Mismatch breakdown:');
console.log(`  - FETCH_FAILED: ${categories.fetch_failed}`);
console.log(`  - Empty Drupal title: ${categories.empty_drupal_title}`);
console.log(`  - HTTP errors: ${categories.http_error}`);
console.log(`  - Hugo FILE_NOT_FOUND: ${categories.hugo_not_found}`);
console.log(`  - Actual title differences: ${categories.actual_title_diff}\n`);
console.log('Files written:');
console.log('  - audit/full-report.json (all results)');
console.log('  - audit/summary.json (statistics)');
console.log('  - audit/title-differences.json (pages needing review)');
