#!/usr/bin/env python3
"""
Fix bold markdown spacing issues.
Rules:
1. Add space before opening ** if preceded by a word character (not whitespace/punctuation/start)
2. Add space after closing ** if followed by a word character (not whitespace/punctuation/end)
"""

import re
import os
import sys
from pathlib import Path

def fix_bold_spacing(content):
    """Fix bold markdown spacing issues."""
    original = content
    
    # Pattern to find bold text: **text**
    # We need to handle cases where:
    # 1. word**bold** -> word **bold**
    # 2. **bold**word -> **bold** word
    # 3. word**bold**word -> word **bold** word
    
    # Step 1: Add space before opening ** if preceded by word character
    # Match: word character followed by ** that starts bold (has matching closing **)
    # But be careful not to match ** that are closing
    
    # First, let's find all bold sections and fix spacing around them
    def fix_bold_match(match):
        before = match.group(1) or ''
        bold_content = match.group(2)
        after = match.group(3) or ''
        
        result = ''
        
        # Check if we need space before
        if before and before[-1].isalnum():
            result = before + ' **' + bold_content + '**'
        else:
            result = before + '**' + bold_content + '**'
        
        # Check if we need space after
        if after and after[0].isalnum():
            result = result + ' ' + after
        else:
            result = result + after
        
        return result
    
    # Pattern: optional chars before, **, content, **, optional chars after
    # This is tricky because ** can be nested or adjacent
    
    # Simpler approach: fix specific common patterns
    
    # 1. Fix: word**Bold -> word **Bold (add space before opening **)
    content = re.sub(r'(\w)\*\*([A-Z])', r'\1 **\2', content)
    
    # 2. Fix: **Bold**word -> **Bold** word (add space after closing **)
    # Match **content** followed by a letter
    content = re.sub(r'\*\*([^*]+)\*\*([a-zA-Z])', r'**\1** \2', content)
    
    # 3. Fix: **WORD**– or **WORD**- (dash directly after bold, including en-dash and em-dash)
    content = re.sub(r'\*\*([^*]+)\*\*([-–—])', r'**\1** \2', content)
    
    # 4. Fix: )** -> ) ** - closing paren before bold
    # Actually this is closing bold, not opening, so skip
    
    # 5. Fix: **word**. should stay as is (punctuation ok)
    # **word**, should stay as is
    
    # 6. Fix: :**text** -> : **text** (colon before bold, but not if already has space)
    content = re.sub(r':(\*\*[^*]+\*\*)', r': \1', content)
    # Fix double space that might result
    content = re.sub(r':  \*\*', r': **', content)
    
    # 7. Fix multiple ** issues like **word****word** 
    # This is malformed, try to fix: **word** **word**
    content = re.sub(r'\*\*\*\*', '** **', content)
    
    # 8. Fix: **WORD**[link] -> **WORD** [link] (brackets after bold)
    content = re.sub(r'\*\*([^*]+)\*\*(\[)', r'**\1** \2', content)
    
    # 9. Fix: **WORD**(text -> **WORD** (text (paren after bold opening content)
    content = re.sub(r'\*\*([^*]+)\*\*(\()', r'**\1** \2', content)
    
    return content


def process_file(filepath):
    """Process a single markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed = fix_bold_spacing(content)
        
        if fixed != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    content_dir = Path('/Users/ludwitt/home.treasury.gov/content/news')
    
    fixed_count = 0
    total_count = 0
    
    for md_file in content_dir.rglob('*.md'):
        total_count += 1
        if process_file(md_file):
            fixed_count += 1
            print(f"Fixed: {md_file.name}")
    
    print(f"\nProcessed {total_count} files, fixed {fixed_count} files")


if __name__ == '__main__':
    main()
