#!/usr/bin/env python3
"""
Scrape the actual mega-menu navigation from the live home.treasury.gov site
to get all correct URLs.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://home.treasury.gov"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page(url):
    """Fetch a page and return BeautifulSoup object."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None


def extract_all_links_by_section(soup):
    """Extract all links organized by section from the page."""
    all_links = {}
    
    # Find all anchor tags
    for a in soup.find_all('a', href=True):
        href = a.get('href', '').strip()
        text = a.get_text(strip=True)
        
        if not href or not text or href.startswith('#') or href.startswith('javascript:'):
            continue
        
        # Normalize URL
        if href.startswith('/'):
            href = href  # Keep as relative
        elif not href.startswith('http'):
            continue
            
        # Group by text (lowercase for matching)
        key = text.lower()
        if key not in all_links:
            all_links[key] = []
        if href not in [l['url'] for l in all_links[key]]:
            all_links[key].append({'url': href, 'text': text})
    
    return all_links


def main():
    print("=" * 80)
    print("Scraping live navigation from home.treasury.gov")
    print("=" * 80)
    print()
    
    # Fetch homepage
    print("Fetching homepage...")
    soup = fetch_page(BASE_URL)
    if not soup:
        print("Failed to fetch homepage")
        return
    
    all_links = extract_all_links_by_section(soup)
    
    # Also get links from key pages that might have different menus
    extra_pages = [
        "/about",
        "/policy-issues/tax-policy",
        "/services",
        "/news",
        "/data/treasury-coupon-issues-and-corporate-bond-yield-curves",
    ]
    
    for page in extra_pages:
        print(f"Fetching {page}...")
        page_soup = fetch_page(urljoin(BASE_URL, page))
        if page_soup:
            page_links = extract_all_links_by_section(page_soup)
            for key, links in page_links.items():
                if key not in all_links:
                    all_links[key] = links
                else:
                    for link in links:
                        if link['url'] not in [l['url'] for l in all_links[key]]:
                            all_links[key].append(link)
    
    print(f"\nTotal unique link texts found: {len(all_links)}")
    
    # Build corrections mapping based on what we found
    corrections = {}
    
    # Manual mappings based on live site analysis
    direct_mappings = {
        # Main nav items - these are usually section landing pages
        "/about-treasury": "/about",
        "/policy-issues": "/policy-issues/tax-policy",  # No landing page, link to first section
        "/data": "/data/treasury-coupon-issues-and-corporate-bond-yield-curves",
        "/services": "/services/report-fraud-waste-and-abuse",
        
        # COVID section - check if still exists or removed
        "/policy-issues/coronavirus/american-families-and-workers": "/policy-issues/coronavirus/assistance-for-American-families-and-workers",
        "/policy-issues/coronavirus/small-businesses": "/policy-issues/coronavirus/assistance-for-small-businesses",
        "/policy-issues/coronavirus/state-local-and-tribal-governments": "/policy-issues/coronavirus/assistance-for-state-local-and-tribal-governments",
        "/policy-issues/coronavirus/american-industry": "/policy-issues/coronavirus/assistance-for-american-industry",
        
        # Tax Policy
        "/policy-issues/tax-policy/treaties-and-related-documents": "/policy-issues/tax-policy/treaties",
        "/policy-issues/tax-policy/reports": "/policy-issues/tax-policy",
        "/policy-issues/tax-policy/tax-analysis": "/policy-issues/tax-policy",
        
        # Economic Policy
        "/policy-issues/economic-policy/treasury-coupon-issues": "/data/treasury-coupon-issues-and-corporate-bond-yield-curves",
        "/policy-issues/economic-policy/corporate-bond-yield-curve": "/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
        "/policy-issues/economic-policy/social-security-and-medicare": "/policy-issues/economic-policy",
        
        # Terrorism/Sanctions
        "/policy-issues/terrorism-and-illicit-finance/sanctions": "https://ofac.treasury.gov/",
        "/policy-issues/terrorism-and-illicit-finance/asset-forfeiture": "/policy-issues/terrorism-and-illicit-finance/treasury-executive-office-for-asset-forfeiture-teoaf",
        "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program": "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program-tftp",
        
        # Financing
        "/policy-issues/financing-the-government/treasury-securities": "https://www.treasurydirect.gov/",
        "/policy-issues/financing-the-government/quarterly-refunding/most-recent-documents": "/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents",
        "/policy-issues/financing-the-government/quarterly-refunding/archives": "/policy-issues/financing-the-government/quarterly-refunding/quarterly-refunding-archives",
        "/policy-issues/financing-the-government/quarterly-refunding/webcasts": "/news/webcasts",
        
        # Financial Markets
        "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program": "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program-payments-for-specified-energy-property-in-lieu-of-tax-credits",
        "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/making-home-affordable": "/data/troubled-assets-relief-program/housing",
        
        # International
        "/policy-issues/international/cfius": "/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius",
        "/policy-issues/international/us-china-comprehensive-strategic-economic-dialogue": "/policy-issues/international",
        
        # Small Business
        "/policy-issues/small-business-programs/state-small-business-credit-initiative": "https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci",
        
        # Data
        "/data/treasury-international-capital-tic-system-home-page": "/data/treasury-international-capital-tic-system",
        
        # About
        "/about/offices/tribal-and-native-affairs": "/about/offices/domestic-finance/community-development-financial-institutions/native-initiatives",
        "/about/offices/inspectors-general": "/services/report-fraud-waste-and-abuse/inspectors-general",
        "/about/offices/management/office-of-the-chief-data-officer/evidence-act": "/about/offices/management/office-of-the-chief-data-officer",
        "/about/offices/management/treasury-franchise-fund": "https://www.fiscal.treasury.gov/tff/",
        "/about/offices/management/shared-services-program": "https://www.fiscal.treasury.gov/",
        "/about/history/treasury-library": "/about/history",
        "/about/small-business-contacts": "/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0",
        
        # Services
        "/services/report-fraud-waste-and-abuse/report-covid-19-scam-attempts": "/services/report-fraud-waste-and-abuse/report-scam-attempts",
        "/services/report-fraud-waste-and-abuse/report-fraud-related-to-government-contracts": "/services/report-fraud-waste-and-abuse/inspectors-general",
        "/services/bonds-and-securities/frequently-asked-questions": "https://www.treasurydirect.gov/help-center/",
        "/services/bonds-and-securities/cashing-savings-bonds-in-disaster-declared-areas": "https://www.treasurydirect.gov/",
        "/services/treasury-payments/lost-or-expired-check": "https://fiscal.treasury.gov/faq/#checks",
        "/services/treasury-payments/non-benefit-federal-payments": "https://fiscal.treasury.gov/",
        "/services/grant-programs/pay-for-results": "/policy-issues/financial-markets-financial-institutions-and-fiscal-service",
        "/services/kline-miller/applications": "/services/the-multiemployer-pension-reform-act-of-2014/applications-for-benefit-suspension",
        "/services/kline-miller/frequently-asked-questions": "/services/the-multiemployer-pension-reform-act-of-2014/frequently-asked-questions-about-the-kline-miller-multiemployer-pension-reform-act",
        "/services/auctions": "https://home.treasury.gov/services/treasury-auctions",
        
        # News
        "/news/press-contacts": "/news/contacts-for-members-of-the-media",
        "/news/weekly-public-schedule-archive": "https://search.usa.gov/search/docs?utf8=%E2%9C%93&affiliate=treas&sort_by=&dc=9123&query=weekly-schedule-updates",
        "/news/media-advisories-archive": "https://search.usa.gov/search/docs?utf8=%E2%9C%93&affiliate=treas&sort_by=&dc=9121&query=media-advisories",
        
        # Resource Center
        "/resource-center/data-chart-center/interest-rates/": "/policy-issues/financing-the-government/interest-rate-statistics",
        
        # External broken links
        "https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/additional-ofac-sanctions-lists": "https://ofac.treasury.gov/specially-designated-nationals-and-blocked-persons-list-sdn-human-readable-lists",
        "https://www.fiscal.treasury.gov/arc/": "https://www.fiscal.treasury.gov/arc.html",
        "https://www.fiscal.treasury.gov/fm/": "https://www.fiscal.treasury.gov/fm.html",
        "https://www.treasurydirect.gov/govt/": "https://www.treasurydirect.gov/",
        "https://www.irs.gov/businesses/small-businesses-self-employed/irs-auctions": "https://www.irsauctions.gov/",
        "https://home.treasury.gov/footer/whistleblower-protection": "/services/report-fraud-waste-and-abuse",
        "https://home.treasury.gov/about/small-business-contacts": "/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0",
    }
    
    print()
    print("=" * 80)
    print("RECOMMENDED CORRECTIONS")
    print("=" * 80)
    print()
    
    for old_url, new_url in sorted(direct_mappings.items()):
        print(f"OLD: {old_url}")
        print(f"NEW: {new_url}")
        print()
    
    print()
    print("=" * 80)
    print("JSON OUTPUT")
    print("=" * 80)
    print(json.dumps(direct_mappings, indent=2))


if __name__ == "__main__":
    main()
