#!/usr/bin/env python3
"""Fix missing newlines after frontmatter."""
import re
from pathlib import Path

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: ---\nfrontmatter\n---Content (no newline before content)
    # Should be: ---\nfrontmatter\n---\n\nContent
    
    # Find files where --- is immediately followed by non-whitespace
    if re.search(r'^---\n.*?^---[^\n]', content, re.MULTILINE | re.DOTALL):
        # Fix it
        new_content = re.sub(r'^(---\n.*?^---)([^\n\s])', r'\1\n\n\2', content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    return False

content_dir = Path('content')
fixed = 0
for filepath in content_dir.rglob('*.md'):
    if fix_file(filepath):
        print(f'Fixed: {filepath}')
        fixed += 1

print(f'\nTotal fixed: {fixed}')
