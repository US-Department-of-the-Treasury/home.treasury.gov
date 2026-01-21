#!/usr/bin/env python3
"""
Batch update content pages with links from live Treasury.gov.
"""

import subprocess
import re
import os
from pathlib import Path

# Priority pages to update - mapping local path to live URL
PAGES_TO_UPDATE = [
    # About - Offices
    ("content/about/offices/international-affairs.md", "/about/offices/international-affairs"),
    ("content/about/offices/management.md", "/about/offices/management"),
    ("content/about/offices/public-affairs.md", "/about/offices/public-affairs"),
    ("content/about/offices/economic-policy.md", "/about/offices/economic-policy"),
    ("content/about/offices/general-counsel.md", "/about/offices/general-counsel"),
    
    # About - History
    ("content/about/history/freedmans-bank-building.md", "/about/history/freedmans-bank-building"),
    ("content/about/history/treasurers-of-the-united-states.md", "/about/history/treasurers-of-the-united-states"),
    
    # About - Careers
    ("content/about/careers-at-treasury/top-ten-reasons-to-work-for-treasury.md", 
     "/about/careers-at-treasury/top-ten-reasons-to-work-for-treasury"),
    ("content/about/careers-at-treasury/workforce.md", "/about/careers-at-treasury/workforce"),
    ("content/about/careers-at-treasury/the-fair-chance-to-compete-act.md",
     "/about/careers-at-treasury/the-fair-chance-to-compete-act"),
    ("content/about/careers-at-treasury/studentinternship-programs/pathways-programs.md",
     "/about/careers-at-treasury/studentinternship-programs/pathways-programs"),
    
    # Policy Issues - Consumer/Economic
    ("content/policy-issues/consumer-policy/innovations-in-financial-services.md",
     "/policy-issues/consumer-policy/innovations-in-financial-services"),
    ("content/policy-issues/consumer-policy/featured-research.md",
     "/policy-issues/consumer-policy/featured-research"),
    ("content/policy-issues/economic-policy/total-taxable-resources.md",
     "/policy-issues/economic-policy/total-taxable-resources"),
    ("content/policy-issues/economic-policy/economic-policy-reports.md",
     "/policy-issues/economic-policy/economic-policy-reports"),
    
    # Policy Issues - Financial Markets
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/federal-insurance-office.md",
     "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/federal-insurance-office"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/restore-act.md",
     "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/restore-act"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/cash-and-debt-forecasting.md",
     "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/cash-and-debt-forecasting"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program-payments-for-specified-energy-property-in-lieu-of-tax-credits.md",
     "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program-payments-for-specified-energy-property-in-lieu-of-tax-credits"),
    
    # Data section
    ("content/data/treasury-open-data.md", "/data/treasury-open-data"),
    ("content/data/tic-press-releases-by-topic.md", "/data/tic-press-releases-by-topic"),
    ("content/data/treasury-international-capital-tic-system-home-page/release-dates-of-tic-data-0.md",
     "/data/treasury-international-capital-tic-system-home-page/release-dates-of-tic-data-0"),
    ("content/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve.md",
     "/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve"),
]


def fetch_page_content(url: str) -> str:
    """Fetch page content from live Treasury.gov"""
    full_url = f"https://home.treasury.gov{url}"
    print(f"  Fetching {full_url}...")
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "20", full_url],
            capture_output=True,
            text=True,
            timeout=25
        )
        return result.stdout
    except Exception as e:
        print(f"  Error fetching: {e}")
        return ""


def extract_body_content(html: str) -> str:
    """Extract the main body content with links"""
    # Pattern for Treasury.gov page body
    body_match = re.search(
        r'<div[^>]*field--name-field-page-body[^>]*field__item[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if body_match:
        content = body_match.group(1).strip()
        if content and len(content) > 10:
            return content
    
    # Try with just field--name-field-page-body
    body_match = re.search(
        r'field--name-field-page-body[^>]*>(<.*?</(?:div|p)>)',
        html, re.DOTALL
    )
    if body_match:
        content = body_match.group(1).strip()
        if content and len(content) > 10:
            return content
    
    # Try abstract
    abstract_match = re.search(
        r'<div[^>]*field--name-field-page-abstract[^>]*field__item[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if abstract_match:
        return abstract_match.group(1).strip()
    
    return ""


def html_to_markdown(html: str) -> str:
    """Convert HTML content to markdown with links preserved"""
    text = re.sub(r'<div[^>]*>', '', html)
    text = re.sub(r'</div>', '', text)
    text = re.sub(r'<span[^>]*>', '', text)
    text = re.sub(r'</span>', '', text)
    
    # Convert headers
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text, flags=re.DOTALL)
    
    # Convert links
    def convert_link(match):
        href = match.group(1)
        link_text = match.group(2)
        link_text = re.sub(r'<[^>]+>', '', link_text)
        link_text = link_text.strip()
        if not link_text:
            return ''
        return f'[{link_text}]({href})'
    
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', convert_link, text, flags=re.DOTALL)
    
    # Convert lists
    text = re.sub(r'<ul[^>]*>', '\n', text)
    text = re.sub(r'</ul>', '\n', text)
    text = re.sub(r'<ol[^>]*>', '\n', text)
    text = re.sub(r'</ol>', '\n', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
    
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Convert emphasis
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    
    # Remove remaining HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Clean whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            item = line[2:].strip()
            item = re.sub(r'\s+', ' ', item)
            line = '- ' + item
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def get_frontmatter(filepath: str) -> str:
    """Read existing frontmatter from file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                return f"---\n{match.group(1)}\n---\n\n"
    except Exception as e:
        print(f"  Error reading frontmatter: {e}")
    return ""


def update_page(local_path: str, url: str) -> bool:
    """Update a single page with scraped content"""
    print(f"\nProcessing: {local_path}")
    
    if not os.path.exists(local_path):
        print(f"  File not found!")
        return False
    
    html = fetch_page_content(url)
    if not html or len(html) < 500:
        print(f"  Failed to fetch content")
        return False
    
    body_html = extract_body_content(html)
    if not body_html:
        print(f"  No body content found")
        return False
    
    markdown = html_to_markdown(body_html)
    if not markdown or len(markdown) < 20:
        print(f"  Failed to convert to markdown")
        return False
    
    link_count = len(re.findall(r'\[([^\]]*)\]\(([^)]+)\)', markdown))
    print(f"  Found {link_count} links")
    
    frontmatter = get_frontmatter(local_path)
    if not frontmatter:
        title = url.strip('/').split('/')[-1].replace('-', ' ').title()
        frontmatter = f'---\ntitle: "{title}"\n---\n\n'
    
    with open(local_path, 'w') as f:
        f.write(frontmatter + markdown + '\n')
    
    print(f"  ✓ Updated with {link_count} links")
    return True


def main():
    os.chdir(Path(__file__).parent.parent)
    
    print("=" * 60)
    print("Batch Updating Content Pages")
    print("=" * 60)
    
    success = 0
    failed = 0
    
    for local_path, url in PAGES_TO_UPDATE:
        if update_page(local_path, url):
            success += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Done: {success} updated, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
