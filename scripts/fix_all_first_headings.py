#!/usr/bin/env python3
"""Remove the first H2 heading from content files if it appears at the start of the body."""
import re
from pathlib import Path

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not content.startswith('---'):
        return False
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return False
    
    frontmatter = parts[1]
    body = parts[2]
    
    # Check if body starts with ## heading (after whitespace)
    # This removes any H2 that's the first thing in the content
    match = re.match(r'^\s*##\s+[^\n]+\n+', body)
    
    if match:
        new_body = body[match.end():]
        new_content = f'---{frontmatter}---\n\n{new_body.lstrip()}'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

# Process content files (exclude news which has different structure)
content_dir = Path('content')
fixed = 0
for filepath in content_dir.rglob('*.md'):
    # Skip news articles - they have different structure
    if '/news/press-releases/' in str(filepath) or '/news/statements-remarks/' in str(filepath) or '/news/featured-stories/' in str(filepath):
        continue
    if fix_file(filepath):
        print(f'Fixed: {filepath}')
        fixed += 1

print(f'\nTotal fixed: {fixed}')
