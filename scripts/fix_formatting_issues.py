#!/usr/bin/env python3
"""
Fix Formatting Issues in Press Release Markdown Files

Identifies files with orphaned text fragments and re-fetches content
from Treasury.gov to fix the formatting.

Usage:
    python3 scripts/fix_formatting_issues.py --scan          # Identify issues
    python3 scripts/fix_formatting_issues.py --fix           # Fix all issues
    python3 scripts/fix_formatting_issues.py --fix --limit 5 # Fix first 5
    python3 scripts/fix_formatting_issues.py --fix --dry-run # Preview changes
"""

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import requests
from bs4 import BeautifulSoup

# Import the fixed converter
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.apply_missing_content import html_to_markdown


BASE_URL = "https://home.treasury.gov"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
TIMEOUT = 30


def log(msg: str = "", end: str = "\n"):
    """Print with immediate flush for real-time output."""
    print(msg, end=end, flush=True)


def has_formatting_issues(body: str) -> Tuple[bool, str]:
    """Check if the body has formatting issues that need fixing.
    
    Returns (has_issue, reason) tuple.
    """
    lines = body.split('\n')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # Orphaned location (WASHINGTON on its own line)
        if stripped in ['WASHINGTON', 'NEW YORK', 'LONDON', 'PARIS', 'CHICAGO']:
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('—'):
                return True, f"Orphaned location: {stripped}"
        
        # Quote attribution split across lines (ends with "said" then name on next line)
        if stripped.endswith(' said') or stripped.endswith('" said') or stripped.endswith('"" said'):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Next line is likely a name (starts with uppercase, doesn't start with quote)
                if next_line and next_line[0].isupper() and not next_line.startswith(('"', "'", '#', '-', '*', '>')):
                    return True, f"Split quote attribution at line {i+1}"
        
        # Link text orphaned (short line followed by comma/period)
        if len(stripped) < 80 and not stripped.endswith(('.', '!', '?', ':', ';', ',', '—', '-', '"', "'")):
            if not stripped.startswith(('#', '-', '*', '>', '|', '[')):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if next line continues the sentence (starts with lowercase or punctuation)
                    if next_line and (next_line[0] in ',.;:)' or (next_line[0].islower() and len(stripped) < 40)):
                        return True, f"Orphaned text: '{stripped[:50]}...'"
    
    return False, ""


def extract_url_from_frontmatter(content: str) -> str:
    """Extract the URL from frontmatter."""
    match = re.search(r'^url:\s*(/news/[^\s\n]+)', content, re.MULTILINE)
    if match:
        return match.group(1)
    return ""


def fetch_and_convert(url_path: str) -> Optional[str]:
    """Fetch HTML from Treasury.gov and convert to markdown."""
    full_url = f"{BASE_URL}{url_path}"
    
    try:
        resp = requests.get(full_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find the main content
        body = soup.find("div", class_="field--name-field-news-body")
        if not body:
            return None
        
        html_content = str(body)
        markdown = html_to_markdown(html_content)
        
        return markdown
        
    except Exception as e:
        log(f"      Error fetching {url_path}: {e}")
        return None


def extract_frontmatter(content: str) -> Tuple[str, str]:
    """Extract frontmatter and body from markdown file."""
    if not content.startswith("---"):
        return "", content
    
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return "", content
    
    frontmatter = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()
    
    return frontmatter, body


def scan_for_issues(content_dir: Path) -> List[Dict]:
    """Scan all markdown files for formatting issues."""
    issues = []
    
    for md_file in sorted(content_dir.glob("*.md")):
        if md_file.name == "_index.md":
            continue
        
        content = md_file.read_text()
        frontmatter, body = extract_frontmatter(content)
        
        has_issue, reason = has_formatting_issues(body)
        if has_issue:
            url_path = extract_url_from_frontmatter(content)
            issues.append({
                "file": md_file,
                "url": url_path,
                "reason": reason,
            })
    
    return issues


def main():
    parser = argparse.ArgumentParser(description="Fix formatting issues in press releases")
    parser.add_argument("--scan", action="store_true", help="Scan for issues only")
    parser.add_argument("--fix", action="store_true", help="Fix issues by re-fetching from Treasury.gov")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")
    parser.add_argument("--content-dir", default="content/news/press-releases", help="Content directory")
    
    args = parser.parse_args()
    
    if not args.scan and not args.fix:
        parser.print_help()
        sys.exit(1)
    
    workspace = Path(__file__).parent.parent
    content_dir = workspace / args.content_dir
    
    log("=" * 70)
    log("FIX FORMATTING ISSUES IN PRESS RELEASES")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    log()
    
    # Scan for issues
    log("[1/2] SCANNING FOR FORMATTING ISSUES")
    log(f"      Directory: {content_dir}")
    
    issues = scan_for_issues(content_dir)
    
    log(f"      Found {len(issues)} files with issues")
    log()
    
    if args.scan:
        log("-" * 70)
        for i, issue in enumerate(issues, 1):
            log(f"  {i:3}. {issue['file'].name}")
            log(f"       URL: {issue['url']}")
            log(f"       Issue: {issue['reason']}")
            log()
        return
    
    # Fix issues
    if args.fix:
        if args.limit:
            issues = issues[:args.limit]
            log(f"      Limited to {len(issues)} files")
        
        log()
        log("[2/2] FIXING ISSUES")
        log("-" * 70)
        
        fixed = 0
        failed = 0
        
        for i, issue in enumerate(issues, 1):
            md_file = issue["file"]
            url_path = issue["url"]
            
            log()
            log(f"  [{i}/{len(issues)}] {md_file.name}")
            log(f"      URL: {url_path}")
            log(f"      Issue: {issue['reason']}")
            
            if not url_path:
                log("      SKIPPED: No URL in frontmatter")
                failed += 1
                continue
            
            # Fetch and convert
            log("      Fetching from Treasury.gov...")
            new_body = fetch_and_convert(url_path)
            
            if not new_body:
                log("      FAILED: Could not fetch content")
                failed += 1
                continue
            
            log(f"      New content: {len(new_body)} chars")
            
            # Read current file
            content = md_file.read_text()
            frontmatter, old_body = extract_frontmatter(content)
            
            if args.dry_run:
                log("      DRY RUN: Would update file")
                log(f"      --- Old (first 150 chars) ---")
                log(f"      {old_body[:150].replace(chr(10), ' ')}")
                log(f"      --- New (first 150 chars) ---")
                log(f"      {new_body[:150].replace(chr(10), ' ')}")
            else:
                # Write updated content
                updated_content = f"---\n{frontmatter}\n---\n\n{new_body}\n"
                md_file.write_text(updated_content)
                log("      FIXED!")
            
            fixed += 1
            
            # Rate limiting
            if i < len(issues):
                time.sleep(1)
        
        log()
        log("=" * 70)
        log("SUMMARY")
        log(f"  Processed: {len(issues)}")
        log(f"  Fixed: {fixed}")
        log(f"  Failed: {failed}")
        
        if args.dry_run:
            log()
            log("  NOTE: This was a DRY RUN. No files were modified.")
            log("  Run without --dry-run to apply changes.")
        
        log()


if __name__ == "__main__":
    main()
