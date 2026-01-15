#!/usr/bin/env python3
"""
Test all links from Treasury site navigation, footer, and header.
Verifies that all URLs point to live pages.
"""

import json
import requests
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import re

# Base domain
BASE_URL = "https://home.treasury.gov"

# Request timeout in seconds
TIMEOUT = 15

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_urls_from_navigation(nav_data: dict) -> dict:
    """Extract all URLs from navigation.json with their context."""
    urls = {}
    
    # Main navigation
    for nav_item in nav_data.get("main_nav", []):
        if nav_item.get("url"):
            urls[nav_item["url"]] = f"Main Nav: {nav_item.get('title', 'Unknown')}"
        
        # Columns within each nav item
        for column in nav_item.get("columns", []):
            heading = column.get("heading", "Unknown")
            for link in column.get("links", []):
                if link.get("url"):
                    urls[link["url"]] = f"Mega Menu ({nav_item.get('title', 'Unknown')} > {heading}): {link.get('title', 'Unknown')}"
    
    # Search categories
    search = nav_data.get("search", {})
    for category in search.get("categories", []):
        heading = category.get("heading", "Unknown")
        for link in category.get("links", []):
            if link.get("url"):
                urls[link["url"]] = f"Search Category ({heading}): {link.get('title', 'Unknown')}"
    
    # News sidebar
    for item in nav_data.get("news_sidebar", []):
        if item.get("url"):
            urls[item["url"]] = f"News Sidebar: {item.get('title', 'Unknown')}"
    
    return urls


def extract_urls_from_footer() -> dict:
    """Extract hardcoded URLs from footer.html."""
    urls = {}
    footer_links = [
        # Bureaus
        ("https://www.ttb.gov/", "Footer (Bureaus): TTB"),
        ("https://www.bep.gov/", "Footer (Bureaus): BEP"),
        ("https://www.fiscal.treasury.gov/", "Footer (Bureaus): BFS"),
        ("https://www.fincen.gov/", "Footer (Bureaus): FinCEN"),
        ("https://www.irs.gov/", "Footer (Bureaus): IRS"),
        ("https://www.occ.gov/", "Footer (Bureaus): OCC"),
        ("https://www.usmint.gov/", "Footer (Bureaus): U.S. Mint"),
        
        # Inspector General Sites
        ("https://oig.treasury.gov/", "Footer (IG Sites): OIG"),
        ("https://www.tigta.gov/", "Footer (IG Sites): TIGTA"),
        ("https://home.treasury.gov/services/report-fraud-waste-and-abuse", "Footer (IG Sites): Report Fraud"),
        ("https://www.sigpr.gov/", "Footer (IG Sites): SIGPR"),
        
        # U.S. Government Shared Services
        ("https://arc.fiscal.treasury.gov/", "Footer (Shared Services): ARC"),
        ("https://www.treasurydirect.gov/", "Footer (Shared Services): TreasuryDirect"),
        ("https://www.fiscal.treasury.gov/", "Footer (Shared Services): FM Marketplace"),
        
        # Additional Resources
        ("https://home.treasury.gov/footer/privacy-act", "Footer (Additional Resources): Privacy Act"),
        ("https://home.treasury.gov/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0", "Footer (Additional Resources): Small Business Contacts"),
        ("https://home.treasury.gov/about/budget-financial-reporting-planning-and-performance", "Footer (Additional Resources): Budget and Performance"),
        ("https://www.treasurydirect.gov/", "Footer (Additional Resources): TreasuryDirect"),
        ("https://home.treasury.gov/footer/freedom-of-information-act", "Footer (Additional Resources): FOIA"),
        ("https://home.treasury.gov/footer/no-fear-act", "Footer (Additional Resources): No FEAR Act"),
        ("https://home.treasury.gov/services/report-fraud-waste-and-abuse", "Footer (Additional Resources): Whistleblower Protection"),
        
        # Other Government Sites
        ("https://www.usa.gov/", "Footer (Other Govt Sites): USA.gov"),
        ("https://www.usajobs.gov/", "Footer (Other Govt Sites): USAJOBS.gov"),
        ("https://www.opm.gov/", "Footer (Other Govt Sites): OPM.gov"),
        ("https://www.mymoney.gov/", "Footer (Other Govt Sites): MyMoney.gov"),
        ("https://www.data.gov/", "Footer (Other Govt Sites): Data.gov"),
        ("https://www.forms.gov/", "Footer (Other Govt Sites): Forms.gov"),
        ("https://www.regulations.gov/", "Footer (Other Govt Sites): Regulations.gov"),
        ("https://www.paymentaccuracy.gov/", "Footer (Other Govt Sites): PaymentAccuracy.gov"),
        ("https://www.ssa.gov/myaccount/", "Footer (Other Govt Sites): My Social Security"),
        ("https://vote.gov/", "Footer (Other Govt Sites): Vote.gov"),
        
        # Utility Footer
        ("https://home.treasury.gov/subfooter/privacy-policy", "Footer (Utility): Privacy Policy"),
        ("https://home.treasury.gov/subfooter/google-privacy-policy", "Footer (Utility): Google Privacy"),
        ("https://home.treasury.gov/guidance", "Footer (Utility): Site Policies"),
        ("https://home.treasury.gov/faqs", "Footer (Utility): FAQs"),
        ("https://apps-treas.my.salesforce-sites.com/treasuryforms/Form?templateID=a1Qt0000002aSIKEA2&pageID=0000", "Footer (Utility): Feedback Form"),
        ("https://home.treasury.gov/about/careers-at-treasury", "Footer (Utility): Careers"),
        ("https://home.treasury.gov/utility/accessibility", "Footer (Utility): Accessibility"),
        ("https://home.treasury.gov/utility/contact", "Footer (Utility): Contact"),
        ("https://get.adobe.com/reader/", "Footer (Utility): Adobe Reader"),
        
        # Social Links
        ("https://x.com/USTreasury", "Footer (Social): X/Twitter"),
    ]
    
    for url, context in footer_links:
        urls[url] = context
    
    return urls


def extract_urls_from_header() -> dict:
    """Extract hardcoded URLs from header.html."""
    urls = {}
    header_links = [
        ("https://home.treasury.gov/", "Header: Home Logo"),
        ("https://search.usa.gov/search", "Header: Search Action"),
    ]
    
    for url, context in header_links:
        urls[url] = context
    
    return urls


def normalize_url(url: str) -> str:
    """Convert relative URLs to absolute URLs."""
    if url.startswith("/"):
        return urljoin(BASE_URL, url)
    return url


def test_url(url: str, context: str) -> tuple:
    """
    Test if a URL is accessible.
    Returns (url, context, status_code, error_message, is_redirect, final_url)
    """
    normalized_url = normalize_url(url)
    
    try:
        # Use HEAD request first (faster), fall back to GET if needed
        response = requests.head(
            normalized_url, 
            headers=HEADERS, 
            timeout=TIMEOUT, 
            allow_redirects=True
        )
        
        # Some servers don't support HEAD, try GET
        if response.status_code in [405, 403, 400]:
            response = requests.get(
                normalized_url, 
                headers=HEADERS, 
                timeout=TIMEOUT, 
                allow_redirects=True
            )
        
        final_url = response.url if response.url != normalized_url else None
        is_redirect = len(response.history) > 0
        
        return (url, context, response.status_code, None, is_redirect, final_url)
        
    except requests.exceptions.SSLError as e:
        return (url, context, None, f"SSL Error: {str(e)[:100]}", False, None)
    except requests.exceptions.ConnectionError as e:
        return (url, context, None, f"Connection Error: {str(e)[:100]}", False, None)
    except requests.exceptions.Timeout:
        return (url, context, None, "Timeout", False, None)
    except requests.exceptions.TooManyRedirects:
        return (url, context, None, "Too Many Redirects", False, None)
    except requests.exceptions.RequestException as e:
        return (url, context, None, f"Error: {str(e)[:100]}", False, None)


def main():
    print("=" * 80)
    print("Treasury Website Link Checker")
    print("=" * 80)
    print()
    
    # Load navigation.json
    script_dir = Path(__file__).parent
    nav_file = script_dir.parent / "data" / "navigation.json"
    
    if not nav_file.exists():
        print(f"Error: Navigation file not found at {nav_file}")
        sys.exit(1)
    
    with open(nav_file, "r") as f:
        nav_data = json.load(f)
    
    # Collect all URLs
    all_urls = {}
    
    print("Extracting URLs from navigation.json...")
    nav_urls = extract_urls_from_navigation(nav_data)
    all_urls.update(nav_urls)
    print(f"  Found {len(nav_urls)} URLs")
    
    print("Extracting URLs from footer.html...")
    footer_urls = extract_urls_from_footer()
    all_urls.update(footer_urls)
    print(f"  Found {len(footer_urls)} URLs")
    
    print("Extracting URLs from header.html...")
    header_urls = extract_urls_from_header()
    all_urls.update(header_urls)
    print(f"  Found {len(header_urls)} URLs")
    
    print()
    print(f"Total unique URLs to test: {len(all_urls)}")
    print("-" * 80)
    print()
    
    # Categorize URLs
    treasury_urls = {k: v for k, v in all_urls.items() if "treasury.gov" in k or k.startswith("/")}
    external_urls = {k: v for k, v in all_urls.items() if k not in treasury_urls}
    
    print(f"Treasury domain URLs: {len(treasury_urls)}")
    print(f"External URLs: {len(external_urls)}")
    print()
    
    # Test all URLs in parallel
    results = []
    errors = []
    redirects = []
    successes = []
    
    print("Testing URLs (this may take a moment)...")
    print()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {
            executor.submit(test_url, url, context): url 
            for url, context in all_urls.items()
        }
        
        completed = 0
        total = len(future_to_url)
        
        for future in as_completed(future_to_url):
            completed += 1
            result = future.result()
            url, context, status, error, is_redirect, final_url = result
            results.append(result)
            
            # Print progress
            if status and 200 <= status < 400:
                if is_redirect:
                    redirects.append(result)
                    print(f"[{completed}/{total}] ✓ REDIRECT ({status}): {url}")
                else:
                    successes.append(result)
                    print(f"[{completed}/{total}] ✓ OK ({status}): {url}")
            else:
                errors.append(result)
                if error:
                    print(f"[{completed}/{total}] ✗ FAILED ({error}): {url}")
                else:
                    print(f"[{completed}/{total}] ✗ FAILED ({status}): {url}")
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total URLs tested: {len(results)}")
    print(f"Successful (2xx): {len(successes)}")
    print(f"Redirects (3xx): {len(redirects)}")
    print(f"Errors/Broken: {len(errors)}")
    print()
    
    # Report broken links
    if errors:
        print("-" * 80)
        print("BROKEN/PROBLEMATIC LINKS")
        print("-" * 80)
        print()
        for url, context, status, error, is_redirect, final_url in sorted(errors, key=lambda x: x[1]):
            print(f"URL: {url}")
            print(f"  Context: {context}")
            if error:
                print(f"  Error: {error}")
            else:
                print(f"  Status: {status}")
            print()
    
    # Report redirects (informational)
    if redirects:
        print("-" * 80)
        print("REDIRECTS (for review)")
        print("-" * 80)
        print()
        for url, context, status, error, is_redirect, final_url in sorted(redirects, key=lambda x: x[1]):
            print(f"URL: {url}")
            print(f"  Context: {context}")
            print(f"  Redirects to: {final_url}")
            print()
    
    # Exit with error code if there are broken links
    if errors:
        print(f"\n❌ Found {len(errors)} broken/problematic links!")
        sys.exit(1)
    else:
        print("\n✅ All links are working!")
        sys.exit(0)


if __name__ == "__main__":
    main()
