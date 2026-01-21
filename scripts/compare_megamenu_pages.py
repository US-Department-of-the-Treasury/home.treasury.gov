#!/usr/bin/env python3
"""
Compare mega menu section pages between local Hugo site and live home.treasury.gov.
Checks for missing links and content discrepancies.
"""

import subprocess
import re
import os
from pathlib import Path

# All internal mega menu heading URLs
MEGAMENU_URLS = [
    "/about/budget-financial-reporting-planning-and-performance/",
    "/about/bureaus/",
    "/about/careers-at-treasury/",
    "/about/general-information/",
    "/about/history/",
    "/about/offices/",
    "/about/offices/management/office-of-the-chief-data-officer/",
    "/data/investor-class-auction-allotments/",
    "/data/other-programs/",
    "/data/treasury-coupon-issues-and-corporate-bond-yield-curves/",
    "/data/treasury-international-capital-tic-system/",
    "/data/troubled-assets-relief-program/",
    "/data/us-international-reserve-position/",
    "/news/contacts-for-members-of-the-media/",
    "/news/featured-stories/",
    "/news/press-releases/",
    "/news/statements-remarks/",
    "/policy-issues/consumer-policy/",
    "/policy-issues/consumer-policy/financial-literacy-and-education-commission/",
    "/policy-issues/coronavirus/",
    "/policy-issues/economic-policy/",
    "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/",
    "/policy-issues/financing-the-government/",
    "/policy-issues/financing-the-government/quarterly-refunding/",
    "/policy-issues/international/",
    "/policy-issues/small-business-programs/",
    "/policy-issues/tax-policy/",
    "/policy-issues/terrorism-and-illicit-finance/",
    "/policy-issues/tribal-affairs/",
    "/services/bonds-and-securities/",
    "/services/currency-and-coins/",
    "/services/forms/",
    "/services/government-shared-services/",
    "/services/report-fraud-waste-and-abuse/",
    "/services/taxes/",
    "/services/the-multiemployer-pension-reform-act-of-2014/",
    "/services/tours-and-library/",
    "/services/treasury-auctions/",
    "/services/treasury-payments/",
]

def fetch_live_page(url_path):
    """Fetch page from live home.treasury.gov"""
    full_url = f"https://home.treasury.gov{url_path}"
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '15', full_url],
            capture_output=True, text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def extract_links(html):
    """Extract all href links from HTML"""
    # Find all href attributes
    links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    # Filter to meaningful links (not anchors, js, etc)
    meaningful_links = []
    for link in links:
        if link.startswith('#'):
            continue
        if link.startswith('javascript:'):
            continue
        if link.startswith('mailto:'):
            continue
        if link.startswith('tel:'):
            continue
        meaningful_links.append(link)
    return set(meaningful_links)

def extract_body_links(html):
    """Extract links from main content area only"""
    # Try to find the main content section
    body_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        body_match = re.search(r'class="[^"]*content[^"]*"[^>]*>(.*?)</(?:div|section|article)', html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        # Fallback: look for article or main-content
        body_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
    
    if body_match:
        return extract_links(body_match.group(1))
    return set()

def get_local_content(url_path):
    """Get local markdown file content"""
    # Convert URL path to file path
    # /about/general-information/ -> content/about/general-information/_index.md or .md
    
    path = url_path.strip('/')
    base_dir = Path('/Users/ludwitt/home.treasury.gov/content')
    
    # Check for _index.md first (section index)
    index_path = base_dir / path / '_index.md'
    if index_path.exists():
        return index_path.read_text()
    
    # Check for direct .md file
    md_path = base_dir / f"{path}.md"
    if md_path.exists():
        return md_path.read_text()
    
    # Check parent with filename
    parts = path.rsplit('/', 1)
    if len(parts) == 2:
        parent, name = parts
        alt_path = base_dir / parent / f"{name}.md"
        if alt_path.exists():
            return alt_path.read_text()
    
    return None

def extract_md_links(content):
    """Extract links from markdown content"""
    # Markdown links: [text](url)
    md_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
    # HTML links in markdown
    html_links = re.findall(r'href=["\']([^"\']+)["\']', content)
    
    all_links = set()
    for _, url in md_links:
        all_links.add(url)
    for url in html_links:
        all_links.add(url)
    
    return all_links

def compare_page(url_path):
    """Compare a single page between local and live"""
    print(f"\n{'='*60}")
    print(f"Comparing: {url_path}")
    print('='*60)
    
    # Get local content
    local_content = get_local_content(url_path)
    if local_content is None:
        print(f"  ❌ LOCAL FILE NOT FOUND")
        return {'status': 'missing', 'url': url_path}
    
    local_links = extract_md_links(local_content)
    print(f"  Local links found: {len(local_links)}")
    
    # Get live content
    live_html = fetch_live_page(url_path)
    if live_html.startswith('Error:') or len(live_html) < 100:
        print(f"  ⚠️  Could not fetch live page")
        return {'status': 'fetch_error', 'url': url_path}
    
    live_links = extract_body_links(live_html)
    print(f"  Live links found: {len(live_links)}")
    
    # Check if local has any links at all
    if len(local_links) == 0:
        print(f"  ⚠️  NO LINKS IN LOCAL FILE - needs content")
        return {'status': 'no_links', 'url': url_path, 'live_links': len(live_links)}
    
    # Compare - find links on live that aren't in local
    # Normalize links for comparison
    def normalize(link):
        # Remove trailing slashes, make lowercase for comparison
        link = link.rstrip('/')
        if link.startswith('https://home.treasury.gov'):
            link = link.replace('https://home.treasury.gov', '')
        return link.lower()
    
    local_normalized = {normalize(l) for l in local_links}
    
    missing_from_local = []
    for live_link in live_links:
        norm = normalize(live_link)
        if norm not in local_normalized:
            # Skip common noise
            if '/sites/default/files/' in live_link:
                continue
            if 'node/' in live_link:
                continue
            missing_from_local.append(live_link)
    
    if missing_from_local:
        print(f"  ⚠️  {len(missing_from_local)} links on live not in local:")
        for link in missing_from_local[:10]:  # Show first 10
            print(f"      - {link}")
        if len(missing_from_local) > 10:
            print(f"      ... and {len(missing_from_local) - 10} more")
    else:
        print(f"  ✓ Links appear complete")
    
    return {
        'status': 'ok' if not missing_from_local else 'missing_links',
        'url': url_path,
        'local_links': len(local_links),
        'live_links': len(live_links),
        'missing': missing_from_local
    }

def main():
    print("Mega Menu Section Pages Comparison")
    print("=" * 60)
    print(f"Comparing {len(MEGAMENU_URLS)} pages...")
    
    results = {
        'missing_file': [],
        'no_links': [],
        'missing_links': [],
        'ok': [],
        'error': []
    }
    
    for url in MEGAMENU_URLS:
        result = compare_page(url)
        
        if result['status'] == 'missing':
            results['missing_file'].append(url)
        elif result['status'] == 'no_links':
            results['no_links'].append(url)
        elif result['status'] == 'missing_links':
            results['missing_links'].append(result)
        elif result['status'] == 'ok':
            results['ok'].append(url)
        else:
            results['error'].append(url)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Complete: {len(results['ok'])}")
    print(f"⚠️  Missing local file: {len(results['missing_file'])}")
    print(f"⚠️  No links in local: {len(results['no_links'])}")
    print(f"⚠️  Missing some links: {len(results['missing_links'])}")
    print(f"❌ Errors: {len(results['error'])}")
    
    if results['missing_file']:
        print("\nPages missing local files:")
        for url in results['missing_file']:
            print(f"  - {url}")
    
    if results['no_links']:
        print("\nPages with no links (need content):")
        for url in results['no_links']:
            print(f"  - {url}")
    
    if results['missing_links']:
        print("\nPages missing some links:")
        for r in results['missing_links']:
            print(f"  - {r['url']} ({len(r['missing'])} missing)")

if __name__ == '__main__':
    main()
