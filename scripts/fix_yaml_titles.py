#!/usr/bin/env python3
"""
Fix YAML titles that contain special characters needing proper quoting.
"""
import re
from pathlib import Path

def fix_titles(content_dir: Path) -> int:
    """Fix titles with special characters in markdown files."""
    fixed = 0
    
    for md_file in content_dir.glob('*.md'):
        if md_file.name == '_index.md':
            continue
        
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue
        
        # Check if title needs fixing
        match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        if not match:
            continue
        
        title = match.group(1).strip()
        original_line = match.group(0)
        
        # Skip if already properly quoted
        if (title.startswith("'") and title.endswith("'")) or (title.startswith('"') and title.endswith('"')):
            continue
        
        # Check if title has special chars that need quoting
        special_chars = ['*', ':', '"', "'", '#', '[', ']', '{', '}', '>', '|', '&', '!', '%', '@', '`']
        needs_quoting = any(c in title for c in special_chars)
        
        if needs_quoting:
            # Escape single quotes by doubling them and wrap in single quotes
            escaped_title = title.replace("'", "''")
            new_title_line = f"title: '{escaped_title}'"
            
            # Simple string replacement instead of regex sub
            new_content = content.replace(original_line, new_title_line, 1)
            md_file.write_text(new_content, encoding='utf-8')
            fixed += 1
    
    return fixed

if __name__ == "__main__":
    import sys
    
    # Process all news categories
    base = Path(__file__).parent.parent / "content" / "news"
    
    total = 0
    for category in ["press-releases", "featured-stories", "statements-remarks", "readouts", "testimonies"]:
        cat_dir = base / category
        if cat_dir.exists():
            count = fix_titles(cat_dir)
            if count > 0:
                print(f"  {category}: {count} fixed")
            total += count
    
    print(f"\nTotal: {total} files fixed")
