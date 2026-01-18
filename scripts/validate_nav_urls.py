#!/usr/bin/env python3
"""
Validate all internal URLs in navigation.json against content files.
Checks that every internal link has a corresponding Hugo content file.
"""

import json
from pathlib import Path
import re
import sys
import subprocess


def get_all_urls_from_nav(nav_data: dict) -> list:
    """Extract all internal URLs from navigation.json with context."""
    urls = []
    
    # Main navigation
    for nav_item in nav_data.get("main_nav", []):
        if nav_item.get("url") and nav_item["url"].startswith("/"):
            urls.append({
                "url": nav_item["url"],
                "title": nav_item.get("title", "Unknown"),
                "context": f"Main Nav: {nav_item.get('title', 'Unknown')}"
            })
        
        # Columns within each nav item
        for column in nav_item.get("columns", []):
            heading = column.get("heading", "Unknown")
            for link in column.get("links", []):
                if link.get("url") and link["url"].startswith("/"):
                    urls.append({
                        "url": link["url"],
                        "title": link.get("title", "Unknown"),
                        "context": f"{nav_item.get('title', 'Unknown')} > {heading}"
                    })
    
    # Search categories
    search = nav_data.get("search", {})
    for category in search.get("categories", []):
        heading = category.get("heading", "Unknown")
        for link in category.get("links", []):
            if link.get("url") and link["url"].startswith("/"):
                urls.append({
                    "url": link["url"],
                    "title": link.get("title", "Unknown"),
                    "context": f"Search: {heading}"
                })
    
    # News sidebar
    for item in nav_data.get("news_sidebar", []):
        if item.get("url") and item["url"].startswith("/"):
            urls.append({
                "url": item["url"],
                "title": item.get("title", "Unknown"),
                "context": "News Sidebar"
            })
    
    return urls


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    # Remove trailing slash
    url = url.rstrip("/")
    # Remove query parameters
    if "?" in url:
        url = url.split("?")[0]
    return url


def find_content_file(url: str, content_dir: Path):
    """
    Find the content file that would generate the given URL.
    Hugo generates URLs based on file paths and frontmatter.
    """
    url = normalize_url(url)
    
    # Remove leading slash
    path = url.lstrip("/")
    
    # Possible file locations
    candidates = [
        content_dir / f"{path}.md",
        content_dir / path / "_index.md",
        content_dir / path / "index.md",
        content_dir / f"{path}/index.md",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    return None


def check_url_in_frontmatter(url: str, content_dir: Path) -> bool:
    """
    Check if any content file has this URL in its frontmatter.
    This handles cases where the URL doesn't match the file path.
    """
    url = url.rstrip("/")
    url_with_slash = url + "/"
    
    # Search for url: in frontmatter
    try:
        result = subprocess.run(
            ["grep", "-r", f"url: {url}", str(content_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True
            
        result = subprocess.run(
            ["grep", "-r", f"url: {url_with_slash}", str(content_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    
    return False


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    nav_file = project_dir / "data" / "navigation.json"
    content_dir = project_dir / "content"
    
    if not nav_file.exists():
        print(f"Error: {nav_file} not found")
        sys.exit(1)
    
    print("=" * 80)
    print("Navigation.json URL Validation")
    print("=" * 80)
    print()
    
    with open(nav_file) as f:
        nav_data = json.load(f)
    
    urls = get_all_urls_from_nav(nav_data)
    print(f"Found {len(urls)} internal URLs in navigation.json")
    print()
    
    # Deduplicate URLs while keeping context
    unique_urls = {}
    for item in urls:
        url = normalize_url(item["url"])
        if url not in unique_urls:
            unique_urls[url] = item
    
    print(f"Unique URLs to validate: {len(unique_urls)}")
    print("-" * 80)
    print()
    
    valid = []
    missing = []
    
    for url, item in unique_urls.items():
        content_file = find_content_file(url, content_dir)
        if content_file:
            valid.append({**item, "file": str(content_file)})
        elif check_url_in_frontmatter(url, content_dir):
            valid.append({**item, "file": "(frontmatter URL)"})
        else:
            missing.append(item)
    
    # Report results
    print(f"✓ Valid URLs: {len(valid)}")
    print(f"✗ Missing content: {len(missing)}")
    print()
    
    if missing:
        print("-" * 80)
        print("MISSING CONTENT FILES")
        print("-" * 80)
        print()
        for item in sorted(missing, key=lambda x: x["url"]):
            print(f"URL: {item['url']}")
            print(f"  Title: {item['title']}")
            print(f"  Context: {item['context']}")
            print()
    
    if valid:
        print("-" * 80)
        print("VALID URLS (sample)")
        print("-" * 80)
        print()
        for item in sorted(valid, key=lambda x: x["url"])[:10]:
            print(f"✓ {item['url']}")
        if len(valid) > 10:
            print(f"  ... and {len(valid) - 10} more")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total internal URLs: {len(unique_urls)}")
    print(f"Valid: {len(valid)}")
    print(f"Missing: {len(missing)}")
    
    if missing:
        print(f"\n❌ Found {len(missing)} missing content files!")
        sys.exit(1)
    else:
        print("\n✅ All navigation URLs have corresponding content!")
        sys.exit(0)


if __name__ == "__main__":
    main()
