#!/usr/bin/env python3
"""
Audit all links on the homepage, including dynamically generated news links.
"""

import re
import sys
import requests
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_homepage_links(base_url: str) -> list:
    """Extract all links from the homepage."""
    response = requests.get(f"{base_url}/")
    html = response.text
    
    # Find all href attributes (handles both quoted and unquoted)
    quoted_links = re.findall(r'href=["\']([^"\']+)["\']', html)
    unquoted_links = re.findall(r'href=([^"\'>\s]+)', html)
    links = quoted_links + unquoted_links
    
    # Deduplicate and categorize
    internal = []
    external = []
    
    for link in set(links):
        if link.startswith('#'):
            continue  # Skip anchors
        elif link.startswith('/'):
            internal.append(link)
        elif link.startswith('http'):
            external.append(link)
    
    return internal, external


def test_link(url: str, base_url: str) -> tuple:
    """Test if a link is accessible."""
    if url.startswith('/'):
        full_url = urljoin(base_url, url)
    else:
        full_url = url
    
    try:
        response = requests.head(full_url, timeout=10, allow_redirects=True)
        if response.status_code in [405, 403]:
            response = requests.get(full_url, timeout=10, allow_redirects=True)
        return url, response.status_code, None
    except Exception as e:
        return url, None, str(e)[:50]


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1313"
    
    print("=" * 80)
    print(f"Homepage Link Audit - {base_url}")
    print("=" * 80)
    print()
    
    internal_links, external_links = get_homepage_links(base_url)
    
    print(f"Internal links: {len(internal_links)}")
    print(f"External links: {len(external_links)}")
    print()
    
    # Test internal links
    print("-" * 80)
    print("TESTING INTERNAL LINKS")
    print("-" * 80)
    
    failed_internal = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_link, url, base_url): url for url in internal_links}
        for future in as_completed(futures):
            url, status, error = future.result()
            if status and status < 400:
                print(f"✓ {status} {url}")
            else:
                failed_internal.append((url, status, error))
                print(f"✗ {status or 'ERROR'} {url} - {error or ''}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Internal links tested: {len(internal_links)}")
    print(f"Failed: {len(failed_internal)}")
    
    if failed_internal:
        print()
        print("Failed links:")
        for url, status, error in failed_internal:
            print(f"  - {url}: {status or error}")
        sys.exit(1)
    else:
        print("\n✅ All homepage internal links are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
