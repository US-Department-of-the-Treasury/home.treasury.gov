#!/usr/bin/env python3
"""
Fix bold markdown spacing issues.

Correct: word **bold text** word
Wrong: word**bold text**word (missing spaces outside)
Wrong: word ** bold text ** word (extra spaces inside)
"""

import re
from pathlib import Path


def fix_bold_spacing(content):
    """Fix bold markdown spacing issues."""
    
    def fix_bold_match(match):
        before = match.group(1)  # char before opening **
        text = match.group(2)    # text inside **...**
        after = match.group(3)   # char after closing **
        
        # Strip any spaces from inside the bold markers
        text = text.strip()
        
        result = ''
        
        # Add space before opening ** if preceded by alphanumeric
        if before.isalnum():
            result = before + ' **' + text + '**'
        else:
            result = before + '**' + text + '**'
        
        # Add space after closing ** if followed by alphanumeric
        if after.isalnum():
            result += ' ' + after
        else:
            result += after
        
        return result
    
    # Match: one char, **, content (no newlines or ** inside), **, one char
    # The content can have spaces, just not newlines or **
    content = re.sub(r'(.)\*\*([^*\n]+?)\*\*(.)', fix_bold_match, content)
    
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
