#!/usr/bin/env python3
"""
Fix broken italics formatting in markdown files.

Patterns fixed:
1. `word* Text` → `word *Text` (asterisk should have space before, not after)
2. `text*word` → `text* word` (closing asterisk missing space before next word)
"""

import re
import os
from pathlib import Path

def fix_broken_italics(content: str) -> tuple[str, int]:
    """Fix broken italics formatting and return (fixed_content, num_fixes)."""
    fixes = 0
    
    # Pattern 1: word* Text → word *Text
    # Matches: word character, asterisk, space, uppercase letter
    # This is a broken opening italic where asterisk is attached to previous word
    def fix_opening(match):
        nonlocal fixes
        fixes += 1
        return f"{match.group(1)} *{match.group(2)}"
    
    content = re.sub(r'(\w)\* ([A-Z])', fix_opening, content)
    
    # Pattern 2: text*word → text* word (when asterisk closes italic but no space before next word)
    # Matches: space, asterisk, lowercase word character
    def fix_closing_lowercase(match):
        nonlocal fixes
        fixes += 1
        return f"* {match.group(1)}"
    
    content = re.sub(r' \*([a-z])', fix_closing_lowercase, content)
    
    # Pattern 3: Name*is → Name* is (closing asterisk directly followed by lowercase)
    # But be careful not to break valid markdown like *italic*
    def fix_no_space_after_close(match):
        nonlocal fixes
        fixes += 1
        return f"{match.group(1)}* {match.group(2)}"
    
    content = re.sub(r'([A-Za-z0-9])\*([a-z]{2,})', fix_no_space_after_close, content)
    
    return content, fixes


def process_file(filepath: Path) -> int:
    """Process a single file and return number of fixes made."""
    try:
        content = filepath.read_text(encoding='utf-8')
        fixed_content, num_fixes = fix_broken_italics(content)
        
        if num_fixes > 0:
            filepath.write_text(fixed_content, encoding='utf-8')
            print(f"  Fixed {num_fixes} issues in {filepath.name}")
        
        return num_fixes
    except Exception as e:
        print(f"  Error processing {filepath}: {e}")
        return 0


def main():
    # Get content directory
    script_dir = Path(__file__).parent
    content_dir = script_dir.parent / "content"
    
    if not content_dir.exists():
        print(f"Content directory not found: {content_dir}")
        return
    
    # Find all markdown files
    md_files = list(content_dir.rglob("*.md"))
    print(f"Scanning {len(md_files)} markdown files...")
    
    total_fixes = 0
    files_fixed = 0
    
    for filepath in sorted(md_files):
        fixes = process_file(filepath)
        if fixes > 0:
            total_fixes += fixes
            files_fixed += 1
    
    print(f"\nComplete! Fixed {total_fixes} issues across {files_fixed} files.")


if __name__ == "__main__":
    main()
