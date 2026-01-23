#!/usr/bin/env node
import { readFileSync } from 'fs';

const results = JSON.parse(readFileSync('audit/other-sections-results.json', 'utf8'));
const diffs = results.filter(r =>
    !r.title_match &&
    r.drupal_title !== 'HTTP_404' &&
    r.drupal_title !== 'FETCH_FAILED' &&
    r.hugo_title !== 'FILE_NOT_FOUND'
);

console.log(`\n=== Actual Title Differences: ${diffs.length} ===\n`);

for (const d of diffs) {
    console.log(`URL: ${d.url}`);
    console.log(`  Hugo:   ${d.hugo_title}`);
    console.log(`  Drupal: ${d.drupal_title}`);
    console.log('');
}
