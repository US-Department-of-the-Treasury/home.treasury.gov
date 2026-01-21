#!/usr/bin/env python3
"""
Rescrape section pages from live Treasury.gov to add proper links.
"""

import subprocess
import re
import os
from pathlib import Path

# Pages to rescrape - mapping local path to live URL
PAGES_TO_RESCRAPE = [
    # === MEGA MENU SECTION INDEX PAGES (no links currently) ===
    ("content/about/budget-financial-reporting-planning-and-performance/_index.md", "/about/budget-financial-reporting-planning-and-performance"),
    ("content/about/careers-at-treasury/_index.md", "/about/careers-at-treasury"),
    ("content/about/general-information/_index.md", "/about/general-information"),
    ("content/about/history/_index.md", "/about/history"),
    ("content/about/offices/management/office-of-the-chief-data-officer.md", "/about/offices/management/office-of-the-chief-data-officer"),
    ("content/data/investor-class-auction-allotments.md", "/data/investor-class-auction-allotments"),
    ("content/data/other-programs.md", "/data/other-programs"),
    ("content/data/troubled-assets-relief-program.md", "/data/troubled-assets-relief-program"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/_index.md", "/policy-issues/financial-markets-financial-institutions-and-fiscal-service"),
    ("content/policy-issues/tribal-affairs.md", "/policy-issues/tribal-affairs"),
    
    # Re-run first batch with fixed formatting
    ("content/about/general-information/role-of-the-treasury.md", "/about/general-information/role-of-the-treasury"),
    ("content/about/general-information/officials.md", "/about/general-information/officials"),
    ("content/about/general-information/orders-and-directives.md", "/about/general-information/orders-and-directives"),
    ("content/about/budget-financial-reporting-planning-and-performance/strategic-plan.md", "/about/budget-financial-reporting-planning-and-performance/strategic-plan"),
    ("content/about/budget-financial-reporting-planning-and-performance/agency-financial-report.md", "/about/budget-financial-reporting-planning-and-performance/agency-financial-report"),
    ("content/about/history/history-overview.md", "/about/history/history-overview"),
    ("content/about/history/prior-secretaries.md", "/about/history/prior-secretaries"),
    ("content/about/history/the-treasury-building.md", "/about/history/the-treasury-building"),
    ("content/about/careers-at-treasury/careers-at-headquarters.md", "/about/careers-at-treasury/careers-at-headquarters"),
    ("content/about/careers-at-treasury/careers-at-our-bureaus.md", "/about/careers-at-treasury/careers-at-our-bureaus"),
    ("content/policy-issues/tax-policy/tax-expenditures.md", "/policy-issues/tax-policy/tax-expenditures"),
    ("content/policy-issues/tax-policy/revenue-proposals.md", "/policy-issues/tax-policy/revenue-proposals"),
    ("content/policy-issues/tax-policy/international-tax.md", "/policy-issues/tax-policy/international-tax"),
    ("content/policy-issues/tax-policy/treaties.md", "/policy-issues/tax-policy/treaties"),
    ("content/policy-issues/financing-the-government/quarterly-refunding.md", "/policy-issues/financing-the-government/quarterly-refunding"),
    ("content/policy-issues/financing-the-government/interest-rate-statistics.md", "/policy-issues/financing-the-government/interest-rate-statistics"),
    ("content/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius.md", "/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius"),
    ("content/policy-issues/terrorism-and-illicit-finance/sanctions.md", "/policy-issues/terrorism-and-illicit-finance/sanctions"),
    ("content/data/treasury-international-capital-tic-system.md", "/data/treasury-international-capital-tic-system"),
    ("content/data/us-international-reserve-position.md", "/data/us-international-reserve-position"),
    
    # About section - additional pages
    ("content/about/history/curator.md", "/about/history/curator"),
    ("content/about/history/collection.md", "/about/history/collection"),
    ("content/about/history/freedmans-bank-building.md", "/about/history/freedmans-bank-building"),
    ("content/about/offices/domestic-finance.md", "/about/offices/domestic-finance"),
    ("content/about/offices/economic-policy.md", "/about/offices/economic-policy"),
    ("content/about/offices/international-affairs.md", "/about/offices/international-affairs"),
    ("content/about/offices/tax-policy.md", "/about/offices/tax-policy"),
    ("content/about/offices/terrorism-and-financial-intelligence.md", "/about/offices/terrorism-and-financial-intelligence"),
    ("content/about/careers-at-treasury/benefits-and-growth.md", "/about/careers-at-treasury/benefits-and-growth"),
    ("content/about/careers-at-treasury/how-to-apply.md", "/about/careers-at-treasury/how-to-apply"),
    ("content/about/careers-at-treasury/veterans-employment.md", "/about/careers-at-treasury/veterans-employment"),
    ("content/about/budget-financial-reporting-planning-and-performance/inspector-general-audits-and-investigative-reports.md", "/about/budget-financial-reporting-planning-and-performance/inspector-general-audits-and-investigative-reports"),
    
    # Policy Issues - additional pages
    ("content/policy-issues/tax-policy/foreign-account-tax-compliance-act.md", "/policy-issues/tax-policy/foreign-account-tax-compliance-act"),
    ("content/policy-issues/tax-policy/tax-regulatory-process.md", "/policy-issues/tax-policy/tax-regulatory-process"),
    ("content/policy-issues/financing-the-government/debt-management-research.md", "/policy-issues/financing-the-government/debt-management-research"),
    ("content/policy-issues/financing-the-government/treasury-investor-data.md", "/policy-issues/financing-the-government/treasury-investor-data"),
    ("content/policy-issues/international/exchange-stabilization-fund.md", "/policy-issues/international/exchange-stabilization-fund"),
    ("content/policy-issues/international/g-7-and-g-20.md", "/policy-issues/international/g-7-and-g-20"),
    ("content/policy-issues/international/international-monetary-fund.md", "/policy-issues/international/international-monetary-fund"),
    ("content/policy-issues/international/multilateral-development-banks.md", "/policy-issues/international/multilateral-development-banks"),
    ("content/policy-issues/terrorism-and-illicit-finance/311-actions.md", "/policy-issues/terrorism-and-illicit-finance/311-actions"),
    ("content/policy-issues/terrorism-and-illicit-finance/money-laundering.md", "/policy-issues/terrorism-and-illicit-finance/money-laundering"),
    ("content/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program-tftp.md", "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program-tftp"),
    ("content/policy-issues/consumer-policy/financial-literacy-and-education-commission.md", "/policy-issues/consumer-policy/financial-literacy-and-education-commission"),
    ("content/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci.md", "/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/fsoc.md", "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/fsoc"),
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/debt-limit.md", "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/debt-limit"),
    
    # Data section - additional pages
    ("content/data/treasury-coupon-issues-and-corporate-bond-yield-curves.md", "/data/treasury-coupon-issues-and-corporate-bond-yield-curves"),
    ("content/data/investor-class-auction-allotments.md", "/data/investor-class-auction-allotments"),
]


def fetch_page_content(url: str) -> str:
    """Fetch page content from live Treasury.gov"""
    full_url = f"https://home.treasury.gov{url}"
    try:
        result = subprocess.run(
            ["curl", "-s", full_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        print(f"Error fetching {full_url}: {e}")
        return ""


def extract_body_content(html: str) -> str:
    """Extract the main body content with links"""
    # Try to find the page body field
    match = re.search(r'field--name-field-page-body[^>]*>(.*?)</div>\s*(?:<h3 id="block|<aside|<footer)', html, re.DOTALL)
    if match:
        return match.group(1)
    
    # Fallback to abstract + body
    abstract_match = re.search(r'field--name-field-page-abstract[^>]*>(.*?)</div>', html, re.DOTALL)
    body_match = re.search(r'field--name-field-page-body[^>]*>(.*?)</div>', html, re.DOTALL)
    
    content = ""
    if abstract_match:
        content += abstract_match.group(1)
    if body_match:
        content += body_match.group(1)
    
    return content


def html_to_markdown(html: str) -> str:
    """Convert HTML content to markdown with links preserved"""
    # Remove div tags
    text = re.sub(r'<div[^>]*>', '', html)
    text = re.sub(r'</div>', '', text)
    
    # Convert headers
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text)
    
    # Convert links - handle links inside headers
    def convert_link(match):
        href = match.group(1)
        text = match.group(2)
        # Clean up text
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()
        return f'[{text}]({href})'
    
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', convert_link, text, flags=re.DOTALL)
    
    # Convert lists
    text = re.sub(r'<ul[^>]*>', '\n', text)
    text = re.sub(r'</ul>', '\n', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
    
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    
    # Convert breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    
    # Clean up list items
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            line = '- ' + line[2:].strip()
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
    except:
        pass
    return ""


def update_page(local_path: str, url: str):
    """Update a single page with scraped content"""
    print(f"Processing: {local_path}")
    
    # Fetch HTML
    html = fetch_page_content(url)
    if not html:
        print(f"  Failed to fetch content")
        return False
    
    # Extract body content
    body_html = extract_body_content(html)
    if not body_html:
        print(f"  No body content found")
        return False
    
    # Convert to markdown
    markdown = html_to_markdown(body_html)
    if not markdown:
        print(f"  Failed to convert to markdown")
        return False
    
    # Get existing frontmatter
    frontmatter = get_frontmatter(local_path)
    if not frontmatter:
        print(f"  No frontmatter found, skipping")
        return False
    
    # Write updated content
    with open(local_path, 'w') as f:
        f.write(frontmatter + markdown + '\n')
    
    print(f"  Updated successfully")
    return True


def main():
    """Main entry point"""
    os.chdir(Path(__file__).parent.parent)
    
    success = 0
    failed = 0
    
    for local_path, url in PAGES_TO_RESCRAPE:
        if os.path.exists(local_path):
            if update_page(local_path, url):
                success += 1
            else:
                failed += 1
        else:
            print(f"File not found: {local_path}")
            failed += 1
    
    print(f"\nDone: {success} updated, {failed} failed")


if __name__ == "__main__":
    main()
