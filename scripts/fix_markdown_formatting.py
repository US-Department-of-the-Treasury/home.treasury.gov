#!/usr/bin/env python3
"""
Fix common markdown formatting issues in scraped content.

Issues fixed:
1. Missing space before link: word[link](url) → word [link](url)
2. Missing space after link: ](url)word → ](url) word
3. Missing space before bold: said**Secretary** → said **Secretary**
4. Missing space after bold: **text**The → **text** The
5. Space inside bold: ** text** → **text** and **text ** → **text**
6. Em-dash patterns: **WASHINGTON –** → **WASHINGTON** –
"""

import re
import argparse
from pathlib import Path


def fix_markdown_content(content: str) -> tuple[str, list[str]]:
    """
    Fix markdown formatting issues in content.
    Returns (fixed_content, list_of_fixes_applied).
    """
    fixes = []

    # ===== LINK FIXES =====
    
    # 1. Missing space BEFORE link: word[link](url) → word [link](url)
    # Matches: letter immediately before opening bracket
    before = content
    content = re.sub(r'([a-zA-Z0-9,.])\[([^\]]+)\]\(', r'\1 [\2](', content)
    if content != before:
        fixes.append("Added space before link")

    # 2. Missing space AFTER link: ](url)word → ](url) word
    # Matches: closing paren immediately before letter
    before = content
    content = re.sub(r'\]\(([^)]+)\)([a-zA-Z])', r'](\1) \2', content)
    if content != before:
        fixes.append("Added space after link")

    # ===== BOLD FIXES =====
    
    # 3. Space after opening **: ** word → **word
    before = content
    content = re.sub(r'\*\* ([a-zA-Z])', r'**\1', content)
    if content != before:
        fixes.append("Removed space after opening **")

    # 4. Space before closing **: word ** → word**
    # Be careful: only match if there's a space before ** and it's closing bold
    # Pattern: letter + space + ** + (space or punctuation or end)
    before = content
    content = re.sub(r'([a-zA-Z]) \*\*(\s|[.,;:!?\-–—]|$)', r'\1**\2', content)
    if content != before:
        fixes.append("Removed space before closing **")

    # 5. Missing space BEFORE bold: word**text → word **text
    # Match: letter/punct immediately before **, then word char
    before = content
    content = re.sub(r'([a-zA-Z0-9,.\'":])\*\*([a-zA-Z])', r'\1 **\2', content)
    if content != before:
        fixes.append("Added space before bold")

    # 6. Missing space AFTER bold: text**Word → text** Word
    # Match: lowercase** followed by uppercase
    before = content
    content = re.sub(r'([a-z])\*\*([A-Z])', r'\1** \2', content)
    if content != before:
        fixes.append("Added space after bold")

    # ===== SPECIAL PATTERNS =====

    # 7. Fix **WORD –** → **WORD** – (em-dash inside bold closing)
    before = content
    content = re.sub(r'\*\*([A-Z]+) –\*\*', r'**\1** –', content)
    if content != before:
        fixes.append("Fixed bold with em-dash")

    # 8. Fix **WORD – ** → **WORD** – (space before closing with em-dash)
    before = content
    content = re.sub(r'\*\*([A-Z]+) – \*\*', r'**\1** – ', content)
    if content != before:
        fixes.append("Fixed bold with em-dash (space)")

    # 9. Fix **–** ** → **– (broken bold-dash pattern)
    before = content
    content = re.sub(r'\*\*–\*\* \*\*', r'**– ', content)
    if content != before:
        fixes.append("Fixed broken bold-dash")

    return content, fixes


def process_file(filepath: Path, dry_run: bool = False) -> tuple[bool, list[str]]:
    """Process a single markdown file."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ❌ Error reading: {e}")
        return False, []

    fixed_content, fixes = fix_markdown_content(content)

    if not fixes:
        return False, []

    if not dry_run:
        try:
            filepath.write_text(fixed_content, encoding='utf-8')
        except Exception as e:
            print(f"  ❌ Error writing: {e}")
            return False, []

    return True, fixes


def main():
    parser = argparse.ArgumentParser(
        description="Fix markdown formatting issues in scraped content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview fixes for all press releases
  python3 scripts/fix_markdown_formatting.py --dry-run

  # Fix all press releases  
  python3 scripts/fix_markdown_formatting.py

  # Fix specific file
  python3 scripts/fix_markdown_formatting.py --file content/news/press-releases/file.md
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--file", type=str, help="Process specific file")
    parser.add_argument("--path", type=str, default="content/news/press-releases", help="Path to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detailed output")

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if args.file:
        files = [project_root / args.file]
    else:
        target_path = project_root / args.path
        if not target_path.exists():
            print(f"❌ Path not found: {target_path}")
            return 1
        files = list(target_path.rglob("*.md"))

    if not files:
        print("No markdown files found.")
        return 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Processing {len(files)} files...")
    print()

    modified_count = 0
    total_fixes = 0

    for filepath in sorted(files):
        was_modified, fixes = process_file(filepath, dry_run=args.dry_run)

        if was_modified:
            modified_count += 1
            total_fixes += len(fixes)
            rel_path = filepath.relative_to(project_root)
            print(f"{'Would fix' if args.dry_run else 'Fixed'}: {rel_path}")
            if args.verbose:
                for fix in fixes:
                    print(f"  - {fix}")

    print()
    print(f"{'Would modify' if args.dry_run else 'Modified'}: {modified_count} files")
    print(f"Total fixes: {total_fixes}")

    return 0


if __name__ == "__main__":
    exit(main())
