#!/usr/bin/env python3
"""
Fix Scraped Content Dates

Corrects dates in media-advisories and weekly-public-schedule files
by extracting the original date from the URL ID (which encodes MMDDYYYY).
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"

def extract_date_from_id(url_id: str) -> Optional[str]:
    """
    Extract date from URL ID like '01052012' -> '2012-01-05'
    IDs are in MMDDYYYY format, sometimes with trailing characters.
    """
    # Remove any trailing letters/numbers that aren't part of the date
    clean_id = re.sub(r'[a-zA-Z]+\d*$', '', url_id)
    
    # Try MMDDYYYY format (8 digits)
    if len(clean_id) >= 8:
        date_part = clean_id[:8]
        if date_part.isdigit():
            try:
                month = int(date_part[0:2])
                day = int(date_part[2:4])
                year = int(date_part[4:8])
                
                # Validate reasonable date range
                if 1 <= month <= 12 and 1 <= day <= 31 and 1990 <= year <= 2026:
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                pass
    
    # Try MDDYYYY format (7 digits) - single digit month
    if len(clean_id) >= 7:
        date_part = clean_id[:7]
        if date_part.isdigit():
            try:
                month = int(date_part[0:1])
                day = int(date_part[1:3])
                year = int(date_part[3:7])
                
                if 1 <= month <= 12 and 1 <= day <= 31 and 1990 <= year <= 2026:
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                pass
    
    return None


def fix_dates_in_category(category: str) -> Tuple[int, int]:
    """Fix dates for all files in a category. Returns (fixed, skipped) counts."""
    category_dir = CONTENT_DIR / category
    if not category_dir.exists():
        print(f"  ❌ Category not found: {category}")
        return 0, 0
    
    fixed = 0
    skipped = 0
    
    for file_path in category_dir.glob("*.md"):
        if file_path.name == "_index.md":
            continue
        
        content = file_path.read_text()
        
        # Extract URL from frontmatter
        url_match = re.search(r'url:\s*/news/[^/]+/([^\s\n]+)', content)
        if not url_match:
            skipped += 1
            continue
        
        url_id = url_match.group(1)
        new_date = extract_date_from_id(url_id)
        
        if not new_date:
            skipped += 1
            continue
        
        # Check current date
        date_match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
        if not date_match:
            skipped += 1
            continue
        
        current_date = date_match.group(1)
        
        # Only update if date is different
        if current_date != new_date:
            new_content = re.sub(
                r'^date:\s*\d{4}-\d{2}-\d{2}',
                f'date: {new_date}',
                content,
                count=1,
                flags=re.MULTILINE
            )
            
            # Also update filename
            old_name = file_path.name
            new_name = re.sub(r'^\d{4}-\d{2}-\d{2}', new_date, old_name)
            
            if new_name != old_name:
                new_path = file_path.parent / new_name
                file_path.write_text(new_content)
                file_path.rename(new_path)
            else:
                file_path.write_text(new_content)
            
            fixed += 1
        else:
            skipped += 1
    
    return fixed, skipped


def main():
    categories = ["media-advisories", "weekly-public-schedule"]
    
    print("🔧 Fixing Scraped Content Dates")
    print("=" * 50)
    
    total_fixed = 0
    total_skipped = 0
    
    for category in categories:
        print(f"\n📂 {category}")
        fixed, skipped = fix_dates_in_category(category)
        total_fixed += fixed
        total_skipped += skipped
        print(f"   ✅ Fixed: {fixed}")
        print(f"   ⏭️  Skipped: {skipped}")
    
    print(f"\n{'=' * 50}")
    print(f"✅ Total fixed: {total_fixed}")
    print(f"⏭️  Total skipped: {total_skipped}")


if __name__ == "__main__":
    main()
