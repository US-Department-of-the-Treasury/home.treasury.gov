#!/usr/bin/env python3
"""
Fix bold markdown spacing issues.

Correct format: word **bold text** word
- Space before opening ** (after alphanumeric, punctuation like comma/period)
- Space after closing ** (before alphanumeric or opening paren)
- NO space inside ** markers
"""

import re
from pathlib import Path


def fix_bold_spacing(content):
    """Fix bold markdown spacing issues."""
    
    def fix_block(match):
        """Remove internal spaces from bold block."""
        text = match.group(1).strip()
        return f'**{text}**'
    
    # First: normalize all bold blocks - remove internal spaces
    content = re.sub(r'\*\*([^*]+)\*\*', fix_block, content)
    
    def add_external_spacing(match):
        """Add appropriate spacing around bold blocks."""
        before = match.group(1)  # char before **text**
        text = match.group(2)    # text inside
        after = match.group(3)   # char after **text**
        
        result = ''
        
        # Add space before opening ** if preceded by:
        # - alphanumeric (word**bold)
        # - sentence punctuation (sentence.**bold)
        # - comma (list,**bold)
        needs_space_before = before and (before[-1].isalnum() or before[-1] in '.!?),;:')
        if needs_space_before:
            result = before + ' **' + text + '**'
        else:
            result = (before or '') + '**' + text + '**'
        
        # Add space after closing ** if followed by:
        # - alphanumeric (**bold**word)
        # - opening paren (**bold**(note))
        needs_space_after = after and (after[0].isalnum() or after[0] == '(')
        if needs_space_after:
            result += ' ' + after
        else:
            result += (after or '')
        
        return result
    
    # Run multiple passes to catch consecutive bold blocks
    for _ in range(5):
        content = re.sub(r'(.?)\*\*([^*]+)\*\*(.?)', add_external_spacing, content)
    
    # Special case: consecutive bold blocks separated by comma
    # **text**,** -> **text**, **
    content = re.sub(r'\*\*,\*\*', '**, **', content)
    
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
    
    print(f"Processed {total_count} files, fixed {fixed_count} files")


if __name__ == '__main__':
    main()
