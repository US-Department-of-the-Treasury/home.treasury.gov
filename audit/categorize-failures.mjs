#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'fs';

// Load title differences (actual mismatches needing review)
const diffs = JSON.parse(readFileSync('audit/title-differences.json', 'utf8'));

// Categorize by type of difference
const categories = {
    html_entity_encoding: [],  // & vs &amp;, ' vs &#039;
    abbreviation_added: [],    // Hugo adds (FOIA), (FATF), etc.
    office_prefix: [],         // "Office of X" vs "X"
    treasury_prefix: [],       // "Treasury X" vs "X"
    formatting: [],            // "Top 10" vs "Top Ten", punctuation
    capitalization: [],        // Case differences
    redirect_page: [],         // Drupal shows redirect notice
    other: []                  // Needs manual review
};

for (const d of diffs) {
    const hugo = d.hugo_title || '';
    const drupal = d.drupal_title || '';

    // Check for HTML entity differences
    if (drupal.includes('&amp;') || drupal.includes('&#039;') || drupal.includes('&quot;')) {
        categories.html_entity_encoding.push(d);
    }
    // Check for abbreviation additions
    else if (hugo.match(/\([A-Z]+\)/) && !drupal.match(/\([A-Z]+\)/)) {
        categories.abbreviation_added.push(d);
    }
    // Check for "Office of" prefix
    else if (hugo.startsWith('Office of') && !drupal.startsWith('Office of')) {
        categories.office_prefix.push(d);
    }
    // Check for "Treasury" prefix
    else if (hugo.includes('Treasury ') && !drupal.includes('Treasury ')) {
        categories.treasury_prefix.push(d);
    }
    // Check for redirect page
    else if (drupal.includes('Redirecting to')) {
        categories.redirect_page.push(d);
    }
    // Check for formatting differences
    else if (
        (hugo.includes('10') && drupal.includes('Ten')) ||
        (hugo.includes(' and ') && drupal.includes(' & ')) ||
        (hugo.includes('&') && drupal.includes(' and ')) ||
        (hugo.includes(',') !== drupal.includes(',')) ||
        (hugo.includes('-') !== drupal.includes(':'))
    ) {
        categories.formatting.push(d);
    }
    // Check for capitalization differences only
    else if (hugo.toLowerCase() === drupal.toLowerCase()) {
        categories.capitalization.push(d);
    }
    // Everything else needs manual review
    else {
        categories.other.push(d);
    }
}

// Determine auto-fixable vs needs review
// Auto-fixable: HTML entity encoding (Hugo is correct, Drupal uses entities)
// Needs review: Everything else (intentional changes or unclear)
const fixCandidates = {
    auto_fixable: [],  // Can be auto-fixed (none - Hugo is the source of truth)
    intentional_improvements: [
        ...categories.abbreviation_added,
        ...categories.office_prefix,
        ...categories.treasury_prefix
    ],
    formatting_differences: [
        ...categories.html_entity_encoding,
        ...categories.formatting,
        ...categories.capitalization
    ],
    needs_review: [
        ...categories.redirect_page,
        ...categories.other
    ]
};

// Write outputs
writeFileSync('audit/failures-by-type.json', JSON.stringify({
    total_differences: diffs.length,
    categories: {
        html_entity_encoding: {
            count: categories.html_entity_encoding.length,
            description: "Drupal uses HTML entities (&amp;, &#039;), Hugo uses actual characters",
            items: categories.html_entity_encoding
        },
        abbreviation_added: {
            count: categories.abbreviation_added.length,
            description: "Hugo adds clarifying abbreviations like (FOIA), (FATF), (FSOC)",
            items: categories.abbreviation_added
        },
        office_prefix: {
            count: categories.office_prefix.length,
            description: "Hugo uses 'Office of X' while Drupal uses just 'X'",
            items: categories.office_prefix
        },
        treasury_prefix: {
            count: categories.treasury_prefix.length,
            description: "Hugo adds 'Treasury' prefix for clarity",
            items: categories.treasury_prefix
        },
        formatting: {
            count: categories.formatting.length,
            description: "Minor formatting: numbers, punctuation, conjunctions",
            items: categories.formatting
        },
        capitalization: {
            count: categories.capitalization.length,
            description: "Title case differences only",
            items: categories.capitalization
        },
        redirect_page: {
            count: categories.redirect_page.length,
            description: "Drupal shows redirect notice instead of content",
            items: categories.redirect_page
        },
        other: {
            count: categories.other.length,
            description: "Needs manual review to determine correct title",
            items: categories.other
        }
    }
}, null, 2));

writeFileSync('audit/fix-candidates.json', JSON.stringify(fixCandidates, null, 2));

console.log('=== FAILURE CATEGORIZATION COMPLETE ===\n');
console.log(`Total title differences: ${diffs.length}\n`);
console.log('Categories:');
console.log(`  - HTML entity encoding: ${categories.html_entity_encoding.length}`);
console.log(`  - Abbreviation added: ${categories.abbreviation_added.length}`);
console.log(`  - Office prefix: ${categories.office_prefix.length}`);
console.log(`  - Treasury prefix: ${categories.treasury_prefix.length}`);
console.log(`  - Formatting: ${categories.formatting.length}`);
console.log(`  - Capitalization: ${categories.capitalization.length}`);
console.log(`  - Redirect page: ${categories.redirect_page.length}`);
console.log(`  - Other (needs review): ${categories.other.length}\n`);
console.log('Fix candidates summary:');
console.log(`  - Auto-fixable: ${fixCandidates.auto_fixable.length} (none - Hugo is source of truth)`);
console.log(`  - Intentional improvements: ${fixCandidates.intentional_improvements.length}`);
console.log(`  - Formatting differences: ${fixCandidates.formatting_differences.length}`);
console.log(`  - Needs manual review: ${fixCandidates.needs_review.length}\n`);
console.log('Files written:');
console.log('  - audit/failures-by-type.json');
console.log('  - audit/fix-candidates.json');
