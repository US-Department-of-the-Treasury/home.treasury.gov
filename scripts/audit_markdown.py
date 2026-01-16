#!/usr/bin/env python3
"""
Audit and fix markdown formatting issues in Treasury content files.

This script scans markdown files for formatting issues that cause bold/italics
to not render properly, outputs a report, and can generate fixed versions
to a staging directory for review before merging.

Usage:
    python scripts/audit_markdown.py --report                    # See issues
    python scripts/audit_markdown.py --fix                       # Generate fixes
    python scripts/audit_markdown.py --merge                     # Merge staged files
    python scripts/audit_markdown.py --fix --section press-releases  # Fix one section
"""

import argparse
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

class MarkdownPattern:
    """Represents a markdown issue pattern with detection and fix logic."""
    
    def __init__(self, name: str, description: str, pattern: str, 
                 replacement: str, flags: int = 0):
        self.name = name
        self.description = description
        self.pattern = re.compile(pattern, flags)
        self.replacement = replacement
    
    def find_all(self, content: str) -> List[re.Match]:
        """Find all matches in content."""
        return list(self.pattern.finditer(content))
    
    def fix(self, content: str) -> Tuple[str, int]:
        """Apply fix and return (fixed_content, count)."""
        fixed, count = self.pattern.subn(self.replacement, content)
        return fixed, count


# Define all patterns to detect and fix
PATTERNS = [
    # 1. Empty bold markers: ** ** or **** or ** **** **
    # Replace with single space to avoid word collisions
    MarkdownPattern(
        name="empty_bold",
        description="Empty or redundant bold markers (** **, ****, etc.)",
        pattern=r'\*\*\s*\*\*(?:\s*\*\*\s*\*\*)*',
        replacement=' ',
    ),
    
    # 2. Standalone **** at start of line
    MarkdownPattern(
        name="quad_asterisk_line",
        description="Quad asterisks at line start (****)",
        pattern=r'^(\*\*\*\*)\s*$',
        replacement='',
        flags=re.MULTILINE,
    ),
    
    # 3. Bold with internal em-dash: **WORD –** → **WORD** –
    MarkdownPattern(
        name="bold_internal_emdash",
        description="Em-dash inside bold closing (**WORD –**)",
        pattern=r'\*\*([A-Z][A-Z\s]*?)\s*[–—-]\s*\*\*',
        replacement=r'**\1** –',
    ),
    
    # 4. Missing space after bold ending with colon: **word:**Text → **word:** Text
    # This must come BEFORE other bold fixes
    MarkdownPattern(
        name="bold_colon_nospace",
        description="Missing space after bold colon (**word:**Text)",
        pattern=r'\*\*([^\*\n]+?):\*\*([A-Za-z])',
        replacement=r'**\1:** \2',
    ),
    
    # 5. Missing space after bold: **text**Word → **text** Word (title case)
    MarkdownPattern(
        name="missing_space_after_bold",
        description="Missing space after bold (**text**Word)",
        pattern=r'\*\*([^\*\n]+?)\*\*([A-Z][a-z])',
        replacement=r'**\1** \2',
    ),
    
    # 5b. Missing space after bold: **text**is → **text** is (lowercase start)
    MarkdownPattern(
        name="missing_space_after_bold_lower",
        description="Missing space after bold, lowercase (**text**is)",
        pattern=r'\*\*([^\*\n]+?)\*\*([a-z]{2})',
        replacement=r'**\1** \2',
    ),
    
    # 5d. Missing space after bold: **text**UPPER → **text** UPPER (all caps)
    MarkdownPattern(
        name="missing_space_after_bold_upper",
        description="Missing space after bold, uppercase (**text**UPPER)",
        pattern=r'\*\*([^\*\n]+?)\*\*([A-Z]{2})',
        replacement=r'**\1** \2',
    ),
    
    # 5e. Missing space after bold: **text**A. → **text** A. (initial with period)
    MarkdownPattern(
        name="missing_space_after_bold_initial",
        description="Missing space after bold, initial (**text**A.)",
        pattern=r'\*\*([^\*\n]+?)\*\*([A-Z]\.)',
        replacement=r'**\1** \2',
    ),
    
    # 5c. Trailing space inside bold before closing: **text ** → **text**
    MarkdownPattern(
        name="trailing_space_in_bold",
        description="Trailing space before closing bold (**text **)",
        pattern=r'\*\*([^\*\n]+?)\s+\*\*',
        replacement=r'**\1**',
    ),
    
    
    
    # 8. Word** – pattern (space issue with datelines)
    MarkdownPattern(
        name="dateline_space_emdash",
        description="Dateline with space before em-dash (WORD** –**)",
        pattern=r'([A-Z]+)\*\*\s*[–—]\s*\*\*',
        replacement=r'**\1** –',
    ),
    
    # 9. **WORD**– missing space after bold before em-dash
    MarkdownPattern(
        name="bold_emdash_nospace",
        description="Missing space between bold and em-dash (**WORD**–)",
        pattern=r'\*\*([A-Z][A-Z\s]*?)\*\*([–—-])',
        replacement=r'**\1** \2',
    ),
    
    # 10. Lines with only asterisks (2 or more) and whitespace - no other content
    MarkdownPattern(
        name="asterisk_only_line",
        description="Lines with only asterisks and whitespace",
        pattern=r'^\s*\*{2,}\s*$',
        replacement='',
        flags=re.MULTILINE,
    ),
    
    # 11. Word collisions - specific known patterns
    MarkdownPattern(
        name="collision_theUnited",
        description="Word collision: theUnited",
        pattern=r'\btheUnited\b',
        replacement='the United',
    ),
    MarkdownPattern(
        name="collision_andthe",
        description="Word collision: andthe",
        pattern=r'\bandthe\b',
        replacement='and the',
    ),
    MarkdownPattern(
        name="collision_ofthe",
        description="Word collision: ofthe",
        pattern=r'\bofthe\b',
        replacement='of the',
    ),
    MarkdownPattern(
        name="collision_inthe",
        description="Word collision: inthe",
        pattern=r'\binthe\b',
        replacement='in the',
    ),
    MarkdownPattern(
        name="collision_tothe",
        description="Word collision: tothe",
        pattern=r'\btothe\b',
        replacement='to the',
    ),
    
    # 12. Multiple consecutive blank lines (more than 3)
    MarkdownPattern(
        name="excessive_blank_lines",
        description="More than 3 consecutive blank lines",
        pattern=r'\n\s*\n\s*\n\s*\n\s*\n',
        replacement='\n\n\n',
    ),
    
    # 12b. Empty bold at start of line followed by content: ** ****Text → Text
    MarkdownPattern(
        name="empty_bold_prefix",
        description="Empty bold markers before content (** ****Text)",
        pattern=r'^\*\*\s*\*{2,}\s*',
        replacement='',
        flags=re.MULTILINE,
    ),
    
    # 13. Broken italic with space: * text* → *text*
    MarkdownPattern(
        name="leading_space_italic",
        description="Leading space inside italic (* text*)",
        pattern=r'(?<!\*)\*\s+([^\*\n]+?)\*(?!\*)',
        replacement=r'*\1*',
    ),
    
    # 14. Broken bold-dash pattern: **–** ** → **–
    MarkdownPattern(
        name="broken_bold_dash",
        description="Broken bold-dash pattern (**–** **)",
        pattern=r'\*\*[–—]\*\*\s*\*\*',
        replacement='**– ',
    ),
    
    # 15. Space after opening italic: * text → *text (single)
    # This is tricky - need to be careful not to break bullet points
    # Skip for now to avoid false positives
]


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_content_dir(project_root: Path) -> Path:
    """Get the content directory path."""
    return project_root / "content" / "news"


def get_sections(content_dir: Path) -> List[str]:
    """Get list of content sections."""
    sections = []
    for item in content_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            sections.append(item.name)
    return sorted(sections)


def find_markdown_files(content_dir: Path, section: Optional[str] = None) -> List[Path]:
    """Find all markdown files in content directory."""
    if section:
        search_dir = content_dir / section
        if not search_dir.exists():
            print(f"Section not found: {section}")
            return []
    else:
        search_dir = content_dir
    
    files = []
    for md_file in search_dir.rglob("*.md"):
        # Skip _index.md files
        if md_file.name == "_index.md":
            continue
        files.append(md_file)
    
    return sorted(files)


def analyze_file(filepath: Path) -> Dict[str, List[re.Match]]:
    """Analyze a file for markdown issues."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return {}
    
    issues = {}
    for pattern in PATTERNS:
        matches = pattern.find_all(content)
        if matches:
            issues[pattern.name] = matches
    
    return issues


def fix_file_content(content: str) -> Tuple[str, Dict[str, int]]:
    """Apply all fixes to content and return (fixed_content, fix_counts)."""
    fix_counts = {}
    
    for pattern in PATTERNS:
        content, count = pattern.fix(content)
        if count > 0:
            fix_counts[pattern.name] = count
    
    # Clean up multiple consecutive blank lines that may have been created
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove trailing whitespace on lines
    content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    
    return content, fix_counts


def generate_report(project_root: Path, section: Optional[str] = None, 
                   verbose: bool = False) -> Dict:
    """Generate a report of all markdown issues."""
    content_dir = get_content_dir(project_root)
    files = find_markdown_files(content_dir, section)
    
    print(f"Scanning {len(files)} markdown files...")
    print()
    
    # Aggregate stats
    total_issues = defaultdict(int)
    files_with_issues = defaultdict(list)
    
    for filepath in files:
        issues = analyze_file(filepath)
        
        if issues:
            rel_path = filepath.relative_to(project_root)
            for issue_type, matches in issues.items():
                total_issues[issue_type] += len(matches)
                files_with_issues[issue_type].append((rel_path, len(matches)))
                
                if verbose:
                    print(f"  {rel_path}: {issue_type} ({len(matches)} occurrences)")
    
    # Print summary
    print("=" * 60)
    print("MARKDOWN AUDIT REPORT")
    print("=" * 60)
    print()
    
    if not total_issues:
        print("No issues found!")
        return {"total_files": len(files), "issues": {}}
    
    print(f"Files scanned: {len(files)}")
    print(f"Files with issues: {len(set(f for files in files_with_issues.values() for f, _ in files))}")
    print()
    
    print("Issues by type:")
    print("-" * 40)
    
    # Get pattern descriptions
    pattern_map = {p.name: p.description for p in PATTERNS}
    
    for issue_type, count in sorted(total_issues.items(), key=lambda x: -x[1]):
        desc = pattern_map.get(issue_type, issue_type)
        affected = len(files_with_issues[issue_type])
        print(f"  {desc}")
        print(f"    Count: {count} | Files affected: {affected}")
        print()
    
    print("-" * 40)
    print(f"Total issues: {sum(total_issues.values())}")
    
    return {
        "total_files": len(files),
        "issues": dict(total_issues),
        "files_with_issues": {k: [(str(f), c) for f, c in v] 
                             for k, v in files_with_issues.items()}
    }


def generate_fixes(project_root: Path, staging_dir: Path, 
                  section: Optional[str] = None, verbose: bool = False) -> Dict:
    """Generate fixed files to staging directory."""
    content_dir = get_content_dir(project_root)
    files = find_markdown_files(content_dir, section)
    
    print(f"Processing {len(files)} markdown files...")
    print(f"Staging directory: {staging_dir}")
    print()
    
    # Ensure staging dir exists
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    files_fixed = 0
    total_fixes = defaultdict(int)
    
    for filepath in files:
        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")
            continue
        
        fixed_content, fix_counts = fix_file_content(content)
        
        # Only write if content changed
        if fixed_content != content:
            files_fixed += 1
            
            # Calculate relative path from content dir
            rel_path = filepath.relative_to(project_root)
            staged_path = staging_dir / rel_path
            
            # Create parent directories
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write fixed content
            staged_path.write_text(fixed_content, encoding='utf-8')
            
            # Accumulate stats
            for fix_type, count in fix_counts.items():
                total_fixes[fix_type] += count
            
            if verbose:
                print(f"  Fixed: {rel_path}")
                for fix_type, count in fix_counts.items():
                    print(f"    - {fix_type}: {count}")
    
    # Print summary
    print()
    print("=" * 60)
    print("FIX GENERATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Files scanned: {len(files)}")
    print(f"Files with fixes: {files_fixed}")
    print()
    
    if total_fixes:
        print("Fixes applied:")
        pattern_map = {p.name: p.description for p in PATTERNS}
        for fix_type, count in sorted(total_fixes.items(), key=lambda x: -x[1]):
            desc = pattern_map.get(fix_type, fix_type)
            print(f"  {desc}: {count}")
    
    print()
    print(f"Staged files written to: {staging_dir}")
    print()
    print("Next steps:")
    print("  1. Review staged files:")
    print(f"     diff -r {staging_dir}/content content/")
    print("  2. Merge when satisfied:")
    print(f"     python scripts/audit_markdown.py --merge --staging-dir {staging_dir}")
    
    return {
        "files_scanned": len(files),
        "files_fixed": files_fixed,
        "fixes": dict(total_fixes)
    }


def merge_staged_files(project_root: Path, staging_dir: Path, 
                      verbose: bool = False) -> int:
    """Merge staged files back to content directory."""
    if not staging_dir.exists():
        print(f"Staging directory not found: {staging_dir}")
        return 1
    
    # Find all staged files
    staged_files = list(staging_dir.rglob("*.md"))
    
    if not staged_files:
        print("No staged files found to merge.")
        return 0
    
    print(f"Merging {len(staged_files)} staged files...")
    print()
    
    merged = 0
    for staged_path in staged_files:
        # Calculate original path
        rel_path = staged_path.relative_to(staging_dir)
        original_path = project_root / rel_path
        
        if verbose:
            print(f"  {rel_path}")
        
        # Copy staged file to original location
        try:
            shutil.copy2(staged_path, original_path)
            merged += 1
        except Exception as e:
            print(f"  Error copying {rel_path}: {e}")
    
    print()
    print(f"Merged {merged} files to content directory.")
    print()
    print("Next steps:")
    print("  1. Build site: hugo serve")
    print("  2. Spot-check rendered pages")
    print("  3. Run 508 accessibility checks")
    print()
    print(f"To clean up staging: rm -rf {staging_dir}")
    
    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Audit and fix markdown formatting issues in Treasury content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report of all issues
  python scripts/audit_markdown.py --report
  
  # Generate report for specific section
  python scripts/audit_markdown.py --report --section press-releases
  
  # Generate fixes to staging directory
  python scripts/audit_markdown.py --fix
  
  # Merge staged files to content
  python scripts/audit_markdown.py --merge
        """
    )
    
    # Action arguments
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--report", 
        action="store_true",
        help="Generate issue report only (default action)"
    )
    action_group.add_argument(
        "--fix", 
        action="store_true",
        help="Generate fixed files to staging directory"
    )
    action_group.add_argument(
        "--merge", 
        action="store_true",
        help="Merge staged files to content directory"
    )
    
    # Options
    parser.add_argument(
        "--staging-dir",
        type=str,
        default=".staging",
        help="Staging directory for fixed files (default: .staging)"
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Only process specific section (e.g., press-releases, readouts)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output for each file"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    staging_dir = project_root / args.staging_dir
    
    # Default to report if no action specified
    if not args.fix and not args.merge:
        args.report = True
    
    # Execute action
    if args.report:
        generate_report(project_root, args.section, args.verbose)
    elif args.fix:
        generate_fixes(project_root, staging_dir, args.section, args.verbose)
    elif args.merge:
        return merge_staged_files(project_root, staging_dir, args.verbose)
    
    return 0


if __name__ == "__main__":
    exit(main())
