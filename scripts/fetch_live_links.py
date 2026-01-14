#!/usr/bin/env python3
"""
Fetch actual links from the live home.treasury.gov site to find correct URLs
for broken links in our navigation.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import sys

BASE_URL = "https://home.treasury.gov"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Broken links from our test
BROKEN_LINKS = [
    "/about-treasury",
    "/policy-issues",
    "/data",
    "/services",
    "/about/offices/tribal-and-native-affairs",
    "/about/offices/inspectors-general",
    "/policy-issues/coronavirus/american-families-and-workers",
    "/policy-issues/coronavirus/small-businesses",
    "/policy-issues/coronavirus/state-local-and-tribal-governments",
    "/policy-issues/coronavirus/american-industry",
    "/policy-issues/tax-policy/treaties-and-related-documents",
    "/policy-issues/tax-policy/reports",
    "/policy-issues/tax-policy/tax-analysis",
    "/policy-issues/economic-policy/treasury-coupon-issues",
    "/policy-issues/economic-policy/corporate-bond-yield-curve",
    "/policy-issues/economic-policy/social-security-and-medicare",
    "/policy-issues/terrorism-and-illicit-finance/sanctions",
    "/policy-issues/terrorism-and-illicit-finance/asset-forfeiture",
    "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program",
    "/policy-issues/financing-the-government/treasury-securities",
    "/policy-issues/financing-the-government/quarterly-refunding/most-recent-documents",
    "/policy-issues/financing-the-government/quarterly-refunding/archives",
    "/policy-issues/financing-the-government/quarterly-refunding/webcasts",
    "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program",
    "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/making-home-affordable",
    "/policy-issues/international/cfius",
    "/policy-issues/international/us-china-comprehensive-strategic-economic-dialogue",
    "/policy-issues/small-business-programs/state-small-business-credit-initiative",
    "/data/treasury-international-capital-tic-system-home-page",
    "/about/offices/management/office-of-the-chief-data-officer/evidence-act",
    "/services/report-fraud-waste-and-abuse/report-covid-19-scam-attempts",
    "/services/report-fraud-waste-and-abuse/report-fraud-related-to-government-contracts",
    "/services/bonds-and-securities/frequently-asked-questions",
    "/services/bonds-and-securities/cashing-savings-bonds-in-disaster-declared-areas",
    "/services/treasury-payments/lost-or-expired-check",
    "/services/treasury-payments/non-benefit-federal-payments",
    "/services/grant-programs/pay-for-results",
    "/services/kline-miller/applications",
    "/services/kline-miller/frequently-asked-questions",
    "/about/offices/management/treasury-franchise-fund",
    "/about/history/treasury-library",
    "/about/offices/management/shared-services-program",
    "/news/press-contacts",
    "/news/weekly-public-schedule-archive",
    "/news/media-advisories-archive",
    "/about/small-business-contacts",
    "/services/auctions",
    "/resource-center/data-chart-center/interest-rates/",
]


def fetch_page(url):
    """Fetch a page and return BeautifulSoup object."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None


def extract_nav_links(soup):
    """Extract all navigation links from a page."""
    links = {}
    
    # Find all links in the page
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        
        if href and text:
            # Normalize the URL
            if href.startswith('/'):
                full_url = urljoin(BASE_URL, href)
            else:
                full_url = href
            
            links[text.lower()] = {'url': href, 'text': text}
    
    return links


def find_correct_url(broken_url, all_links):
    """Try to find the correct URL for a broken link."""
    # Extract the last part of the path as keyword
    path_parts = broken_url.rstrip('/').split('/')
    keywords = path_parts[-1].replace('-', ' ').lower()
    
    # Also try the full path keywords
    full_keywords = ' '.join(path_parts[1:]).replace('-', ' ').lower()
    
    matches = []
    
    for text, link_info in all_links.items():
        if keywords in text or text in keywords:
            matches.append(link_info)
        elif any(kw in text for kw in keywords.split()):
            matches.append(link_info)
    
    return matches


def check_url_redirect(url):
    """Check if a URL redirects and return the final URL."""
    full_url = urljoin(BASE_URL, url) if url.startswith('/') else url
    try:
        response = requests.head(full_url, headers=HEADERS, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            final_url = response.url
            if final_url != full_url:
                # Extract path from final URL
                parsed = urlparse(final_url)
                if parsed.netloc == 'home.treasury.gov':
                    return parsed.path
                return final_url
            return url
        return None
    except:
        return None


def main():
    print("=" * 80)
    print("Fetching live links from home.treasury.gov")
    print("=" * 80)
    print()
    
    # Fetch the homepage to extract navigation
    print("Fetching homepage...")
    soup = fetch_page(BASE_URL)
    if not soup:
        print("Failed to fetch homepage")
        sys.exit(1)
    
    # Extract all navigation menus
    all_links = extract_nav_links(soup)
    print(f"Found {len(all_links)} links on homepage")
    
    # Also fetch specific sections to get more links
    sections = [
        "/about",
        "/policy-issues/tax-policy",
        "/policy-issues/terrorism-and-illicit-finance", 
        "/policy-issues/financing-the-government",
        "/resource-center/data-chart-center/interest-rates",
        "/services",
        "/news",
    ]
    
    for section in sections:
        print(f"Fetching {section}...")
        section_soup = fetch_page(urljoin(BASE_URL, section))
        if section_soup:
            section_links = extract_nav_links(section_soup)
            all_links.update(section_links)
    
    print(f"\nTotal links collected: {len(all_links)}")
    print()
    
    # Now check each broken URL
    print("=" * 80)
    print("Checking broken URLs for redirects/correct paths")
    print("=" * 80)
    print()
    
    corrections = {}
    still_broken = []
    
    for broken in BROKEN_LINKS:
        full_url = urljoin(BASE_URL, broken)
        print(f"\nChecking: {broken}")
        
        # First, try the URL directly to see if it redirects
        correct = check_url_redirect(broken)
        
        if correct and correct != broken:
            print(f"  → Redirects to: {correct}")
            corrections[broken] = correct
        elif correct == broken:
            print(f"  → Actually works! (might be cached)")
        else:
            # Try to find similar links
            matches = find_correct_url(broken, all_links)
            if matches:
                print(f"  → Possible matches found:")
                for m in matches[:3]:
                    print(f"     - {m['url']} ({m['text']})")
                if len(matches) == 1:
                    corrections[broken] = matches[0]['url']
            else:
                print(f"  ✗ No matches found - needs manual review")
                still_broken.append(broken)
    
    # Print summary
    print()
    print("=" * 80)
    print("CORRECTION SUMMARY")
    print("=" * 80)
    
    if corrections:
        print("\nFound corrections:")
        for old, new in corrections.items():
            print(f"  {old}")
            print(f"    → {new}")
            print()
    
    if still_broken:
        print("\nStill need manual review:")
        for url in still_broken:
            print(f"  - {url}")
    
    # Output as JSON for easy use
    print()
    print("=" * 80)
    print("JSON OUTPUT (for updating navigation.json)")
    print("=" * 80)
    print(json.dumps(corrections, indent=2))


if __name__ == "__main__":
    main()
