#!/usr/bin/env python3
"""Remove duplicate headings from content files where the first heading matches the title."""
import os
import re
from pathlib import Path

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract frontmatter
    if not content.startswith('---'):
        return False
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return False
    
    frontmatter = parts[1]
    body = parts[2]
    
    # Get title from frontmatter
    title_match = re.search(r'^title:\s*["\']?([^"\'\n]+)["\']?', frontmatter, re.MULTILINE)
    if not title_match:
        return False
    
    title = title_match.group(1).strip()
    
    # Check if body starts with a heading that matches title (H1 or H2)
    # Match: ## Title or # Title at start of body (after whitespace)
    heading_pattern = rf'^\s*##?\s*{re.escape(title)}\s*\n'
    match = re.match(heading_pattern, body, re.IGNORECASE)
    
    if match:
        # Remove the duplicate heading
        new_body = body[match.end():]
        new_content = f'---{frontmatter}---{new_body}'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

# Process all markdown files
content_dir = Path('content')
fixed = 0
for filepath in content_dir.rglob('*.md'):
    if fix_file(filepath):
        print(f'Fixed: {filepath}')
        fixed += 1

print(f'\nTotal fixed: {fixed}')
