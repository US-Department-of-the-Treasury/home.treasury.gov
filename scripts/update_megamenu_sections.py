#!/usr/bin/env python3
"""
Update mega menu section pages with content from live Treasury.gov.
These are the pages that currently have 0 links.
"""

import subprocess
import re
import os
from pathlib import Path

# Section pages that need content (currently have 0 links)
PAGES_TO_UPDATE = [
    # About section
    ("content/about/budget-financial-reporting-planning-and-performance/_index.md", 
     "/about/budget-financial-reporting-planning-and-performance"),
    ("content/about/careers-at-treasury/_index.md", 
     "/about/careers-at-treasury"),
    ("content/about/general-information/_index.md", 
     "/about/general-information"),
    ("content/about/history/_index.md", 
     "/about/history"),
    ("content/about/offices/management/office-of-the-chief-data-officer.md", 
     "/about/offices/management/office-of-the-chief-data-officer"),
    
    # Data section
    ("content/data/investor-class-auction-allotments.md", 
     "/data/investor-class-auction-allotments"),
    ("content/data/other-programs.md", 
     "/data/other-programs"),
    ("content/data/troubled-assets-relief-program.md", 
     "/data/troubled-assets-relief-program"),
    
    # Policy Issues
    ("content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/_index.md", 
     "/policy-issues/financial-markets-financial-institutions-and-fiscal-service"),
    ("content/policy-issues/tribal-affairs.md", 
     "/policy-issues/tribal-affairs"),
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
    """Extract the main body content with links - specifically from page body, not sidebar"""
    
    # Pattern for Treasury.gov page body - the content is inside a div with 
    # field--name-field-page-body AND field__item classes on the SAME element
    body_match = re.search(
        r'<div[^>]*field--name-field-page-body[^>]*field__item[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if body_match:
        content = body_match.group(1).strip()
        if content and len(content) > 10:
            return content
    
    # Alternative: field--name-field-page-body as container, content inside
    body_match = re.search(
        r'field--name-field-page-body[^>]*>(<p>.*?</p>)',
        html, re.DOTALL
    )
    if body_match:
        content = body_match.group(1).strip()
        if content and len(content) > 10:
            return content
    
    # Try to find abstract field
    abstract_match = re.search(
        r'<div[^>]*field--name-field-page-abstract[^>]*field__item[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if abstract_match:
        return abstract_match.group(1).strip()
    
    # Last resort: Look for main article content
    article_match = re.search(
        r'<article[^>]*class="[^"]*node--type-page[^"]*"[^>]*>.*?<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</article>',
        html, re.DOTALL
    )
    if article_match:
        # Extract just the text content, avoiding navigation
        content = article_match.group(1)
        # Remove sidebar/nav sections
        content = re.sub(r'<aside[^>]*>.*?</aside>', '', content, flags=re.DOTALL)
        content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)
        if content and len(content) > 50:
            return content.strip()
    
    return ""


def html_to_markdown(html: str) -> str:
    """Convert HTML content to markdown with links preserved"""
    # Remove div/span tags
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
        # Clean up text inside link
        link_text = re.sub(r'<[^>]+>', '', link_text)
        link_text = link_text.strip()
        if not link_text:
            return ''
        return f'[{link_text}]({href})'
    
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', convert_link, text, flags=re.DOTALL)
    
    # Convert lists - handle nested structure
    text = re.sub(r'<ul[^>]*>', '\n', text)
    text = re.sub(r'</ul>', '\n', text)
    text = re.sub(r'<ol[^>]*>', '\n', text)
    text = re.sub(r'</ol>', '\n', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
    
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    
    # Convert breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Convert strong/em
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    
    # Clean up list items - remove extra whitespace inside
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            # Clean the list item content
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
    
    # Fetch HTML
    html = fetch_page_content(url)
    if not html or len(html) < 500:
        print(f"  Failed to fetch content (got {len(html)} bytes)")
        return False
    
    # Extract body content
    body_html = extract_body_content(html)
    if not body_html:
        print(f"  No body content found - page may have different structure")
        return False
    
    # Convert to markdown
    markdown = html_to_markdown(body_html)
    if not markdown or len(markdown) < 20:
        print(f"  Failed to convert to markdown (got {len(markdown) if markdown else 0} chars)")
        return False
    
    # Count links in markdown
    link_count = len(re.findall(r'\[([^\]]*)\]\(([^)]+)\)', markdown))
    print(f"  Found {link_count} links in content")
    
    # Get existing frontmatter
    frontmatter = get_frontmatter(local_path)
    if not frontmatter:
        print(f"  No frontmatter found, creating basic one")
        # Create basic frontmatter from URL
        title = url.strip('/').split('/')[-1].replace('-', ' ').title()
        frontmatter = f'---\ntitle: "{title}"\n---\n\n'
    
    # Write updated content
    with open(local_path, 'w') as f:
        f.write(frontmatter + markdown + '\n')
    
    print(f"  ✓ Updated successfully with {link_count} links")
    return True


def main():
    """Main entry point"""
    os.chdir(Path(__file__).parent.parent)
    
    print("=" * 60)
    print("Updating Mega Menu Section Pages")
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
