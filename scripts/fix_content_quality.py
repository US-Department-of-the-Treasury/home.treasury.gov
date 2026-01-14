#!/usr/bin/env python3
"""
Fix content quality issues in scraped markdown files.

Issues fixed:
1. Missing space before links: "a[link]" -> "a [link]"
2. Missing space after links: "](url)today" -> "](url) today"
3. Broken bold formatting: "said** Name" -> "said **Name"
4. Extract press_release_number from URL if missing

Usage:
    python scripts/fix_content_quality.py --dry-run    # Preview changes
    python scripts/fix_content_quality.py              # Apply fixes
    python scripts/fix_content_quality.py --section press-releases  # Fix one section
"""

import argparse
import os
import re
from pathlib import Path


from typing import Optional, Tuple


def fix_link_spacing_before(content: str) -> Tuple[str, int]:
    """Fix missing space before markdown links: 'word[link]' -> 'word [link]'"""
    # Match word character followed by [ but not already preceded by space
    pattern = r'([a-zA-Z])(\[[^\]]+\]\([^)]+\))'
    fixed = re.sub(pattern, r'\1 \2', content)
    count = len(re.findall(pattern, content))
    return fixed, count


def fix_link_spacing_after(content: str) -> Tuple[str, int]:
    """Fix missing space after markdown links: '](url)word' -> '](url) word'"""
    # Match closing paren followed by word character
    pattern = r'(\]\([^)]+\))([a-zA-Z])'
    fixed = re.sub(pattern, r'\1 \2', content)
    count = len(re.findall(pattern, content))
    return fixed, count


def fix_broken_bold(content: str) -> Tuple[str, int]:
    """Fix various broken bold patterns"""
    count = 0
    
    # Fix double asterisks: **** -> ** (when closing and opening bold merge)
    pattern1 = r'\*\*\*\*'
    matches1 = len(re.findall(pattern1, content))
    if matches1:
        content = re.sub(pattern1, '** **', content)
        count += matches1
    
    # Fix "word** Word" pattern (e.g., "the** Egyptian" -> "the **Egyptian")
    pattern2 = r'(\w)\*\*\s+(\w)'
    matches2 = len(re.findall(pattern2, content))
    if matches2:
        content = re.sub(pattern2, r'\1 **\2', content)
        count += matches2
    
    # Fix "and**Word" -> "and **Word"
    pattern3 = r'and\*\*([A-Z])'
    matches3 = len(re.findall(pattern3, content))
    if matches3:
        content = re.sub(pattern3, r'and **\1', content)
        count += matches3
    
    # Fix trailing space before closing bold: "word **" -> "word**"
    pattern4 = r'(\w)\s+\*\*([,\.\s])'
    matches4 = len(re.findall(pattern4, content))
    if matches4:
        content = re.sub(pattern4, r'\1**\2', content)
        count += matches4
    
    return content, count


def extract_press_release_number(url: str) -> Optional[str]:
    """Extract press release number from URL like /news/press-releases/jy1234"""
    match = re.search(r'/news/press-releases/([a-z]{2}\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def fix_front_matter(content: str) -> Tuple[str, bool]:
    """Add press_release_number if missing and URL contains it."""
    # Check if press_release_number already exists
    if re.search(r'^press_release_number:', content, re.MULTILINE):
        return content, False
    
    # Find URL in front matter
    url_match = re.search(r'^url:\s*(/news/press-releases/[a-z]{2}\d+)', content, re.MULTILINE | re.IGNORECASE)
    if not url_match:
        return content, False
    
    url = url_match.group(1)
    pr_number = extract_press_release_number(url)
    if not pr_number:
        return content, False
    
    # Insert press_release_number after url line
    pattern = r'(^url:\s*[^\n]+\n)'
    replacement = f'\\1press_release_number: {pr_number}\n'
    fixed = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    
    return fixed, True


def process_file(filepath: Path, dry_run: bool = False) -> dict:
    """Process a single markdown file and return stats."""
    stats = {
        'filepath': str(filepath),
        'link_before': 0,
        'link_after': 0,
        'broken_bold': 0,
        'pr_number_added': False,
        'modified': False,
    }
    
    try:
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # Apply fixes
        content, count = fix_link_spacing_before(content)
        stats['link_before'] = count
        
        content, count = fix_link_spacing_after(content)
        stats['link_after'] = count
        
        content, count = fix_broken_bold(content)
        stats['broken_bold'] = count
        
        content, added = fix_front_matter(content)
        stats['pr_number_added'] = added
        
        # Check if modified
        if content != original:
            stats['modified'] = True
            if not dry_run:
                filepath.write_text(content, encoding='utf-8')
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Fix content quality issues in scraped markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files',
    )
    parser.add_argument(
        '--section',
        type=str,
        default=None,
        help='Only process a specific section (e.g., press-releases)',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show details for each modified file',
    )
    
    args = parser.parse_args()
    
    # Find content directory
    script_dir = Path(__file__).parent
    content_dir = script_dir.parent / 'content' / 'news'
    
    if not content_dir.exists():
        print(f"Error: Content directory not found: {content_dir}")
        return 1
    
    # Determine sections to process
    if args.section:
        sections = [args.section]
    else:
        sections = ['press-releases', 'readouts', 'statements-remarks', 'testimonies', 'featured-stories']
    
    # Stats
    total_files = 0
    modified_files = 0
    total_link_before = 0
    total_link_after = 0
    total_broken_bold = 0
    total_pr_numbers = 0
    
    print("=" * 60)
    print("CONTENT QUALITY FIXER")
    print("=" * 60)
    if args.dry_run:
        print("MODE: DRY RUN (no files will be modified)")
    else:
        print("MODE: APPLYING FIXES")
    print("=" * 60)
    print()
    
    for section in sections:
        section_dir = content_dir / section
        if not section_dir.exists():
            print(f"Skipping {section} (not found)")
            continue
        
        print(f"\n📁 Processing {section}...")
        
        md_files = list(section_dir.glob('*.md'))
        section_modified = 0
        
        for filepath in md_files:
            if filepath.name == '_index.md':
                continue
            
            total_files += 1
            stats = process_file(filepath, dry_run=args.dry_run)
            
            if stats.get('modified'):
                modified_files += 1
                section_modified += 1
                total_link_before += stats['link_before']
                total_link_after += stats['link_after']
                total_broken_bold += stats['broken_bold']
                if stats['pr_number_added']:
                    total_pr_numbers += 1
                
                if args.verbose:
                    print(f"  ✓ {filepath.name}")
                    if stats['link_before']:
                        print(f"      - Fixed {stats['link_before']} link spacing (before)")
                    if stats['link_after']:
                        print(f"      - Fixed {stats['link_after']} link spacing (after)")
                    if stats['broken_bold']:
                        print(f"      - Fixed {stats['broken_bold']} broken bold")
                    if stats['pr_number_added']:
                        print(f"      - Added press_release_number")
        
        print(f"   {section_modified} files modified")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files scanned:     {total_files}")
    print(f"Files modified:          {modified_files}")
    print()
    print("Fixes applied:")
    print(f"  - Link spacing (before): {total_link_before}")
    print(f"  - Link spacing (after):  {total_link_after}")
    print(f"  - Broken bold:           {total_broken_bold}")
    print(f"  - PR numbers added:      {total_pr_numbers}")
    print()
    
    if args.dry_run:
        print("✋ DRY RUN - No files were modified")
        print("   Run without --dry-run to apply fixes")
    else:
        print("✅ Fixes applied successfully")
    
    return 0


if __name__ == '__main__':
    exit(main())
