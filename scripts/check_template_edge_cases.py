#!/usr/bin/env python3
"""
Check Hugo content files for template edge cases that could cause rendering issues.
"""

import os
import re
import sys
from pathlib import Path
import yaml


def check_frontmatter(file_path: Path) -> list:
    """Check frontmatter for issues."""
    issues = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        issues.append(("encoding", "File has encoding issues"))
        return issues
    
    # Check for frontmatter
    if not content.startswith("---"):
        issues.append(("no_frontmatter", "No frontmatter found"))
        return issues
    
    # Extract frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        issues.append(("malformed_frontmatter", "Frontmatter not properly closed"))
        return issues
    
    frontmatter_text = match.group(1)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        issues.append(("yaml_error", f"YAML parse error: {str(e)[:100]}"))
        return issues
    
    if not frontmatter:
        issues.append(("empty_frontmatter", "Frontmatter is empty"))
        return issues
    
    # Check for required fields
    if "title" not in frontmatter:
        issues.append(("missing_title", "Missing 'title' field"))
    elif not frontmatter["title"]:
        issues.append(("empty_title", "Title is empty"))
    elif len(str(frontmatter["title"])) > 200:
        issues.append(("long_title", f"Title is very long ({len(str(frontmatter['title']))} chars)"))
    
    # Check for special characters in title that might break HTML
    if "title" in frontmatter and frontmatter["title"]:
        title = str(frontmatter["title"])
        if '<' in title or '>' in title:
            issues.append(("html_in_title", "Title contains HTML-like characters"))
        if title.count('"') > 0 and title.count("'") > 0:
            issues.append(("mixed_quotes_title", "Title has mixed quote types"))
    
    # Check draft status
    if frontmatter.get("draft") == True:
        issues.append(("draft", "Page is marked as draft"))
    
    # Check date format
    if "date" in frontmatter:
        date_val = frontmatter["date"]
        if isinstance(date_val, str):
            # Check for common date format issues
            if not re.match(r'\d{4}-\d{2}-\d{2}', date_val):
                issues.append(("date_format", f"Date format may be incorrect: {date_val}"))
    
    # Get content after frontmatter
    content_body = content[match.end():].strip()
    
    # Check for empty content
    if not content_body:
        issues.append(("empty_content", "Page has no content body"))
    elif len(content_body) < 50:
        issues.append(("minimal_content", f"Very minimal content ({len(content_body)} chars)"))
    
    return issues


def check_all_content(content_dir: Path) -> dict:
    """Check all content files for edge cases."""
    results = {
        "total_files": 0,
        "files_with_issues": 0,
        "issues_by_type": {},
        "issues": []
    }
    
    for md_file in content_dir.rglob("*.md"):
        results["total_files"] += 1
        
        issues = check_frontmatter(md_file)
        
        if issues:
            results["files_with_issues"] += 1
            rel_path = md_file.relative_to(content_dir)
            
            for issue_type, issue_msg in issues:
                if issue_type not in results["issues_by_type"]:
                    results["issues_by_type"][issue_type] = []
                results["issues_by_type"][issue_type].append({
                    "file": str(rel_path),
                    "message": issue_msg
                })
            
            results["issues"].append({
                "file": str(rel_path),
                "issues": issues
            })
    
    return results


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    content_dir = project_dir / "content"
    
    print("=" * 80)
    print("Hugo Template Edge Case Check")
    print("=" * 80)
    print()
    
    results = check_all_content(content_dir)
    
    print(f"Total content files: {results['total_files']}")
    print(f"Files with issues: {results['files_with_issues']}")
    print()
    
    # Summary by issue type
    print("-" * 80)
    print("ISSUES BY TYPE")
    print("-" * 80)
    print()
    
    critical_types = ["no_frontmatter", "malformed_frontmatter", "yaml_error", "missing_title", "empty_title", "encoding"]
    warning_types = ["empty_content", "minimal_content", "long_title", "html_in_title"]
    info_types = ["draft", "date_format", "mixed_quotes_title"]
    
    has_critical = False
    
    for issue_type in sorted(results["issues_by_type"].keys()):
        count = len(results["issues_by_type"][issue_type])
        
        if issue_type in critical_types:
            prefix = "❌ CRITICAL"
            has_critical = True
        elif issue_type in warning_types:
            prefix = "⚠️  WARNING"
        else:
            prefix = "ℹ️  INFO"
        
        print(f"{prefix}: {issue_type} - {count} files")
        
        # Show first 5 examples
        for item in results["issues_by_type"][issue_type][:5]:
            print(f"    - {item['file']}")
        if count > 5:
            print(f"    ... and {count - 5} more")
        print()
    
    # Show critical issues in detail
    if has_critical:
        print("-" * 80)
        print("CRITICAL ISSUES (must fix)")
        print("-" * 80)
        print()
        
        for issue_type in critical_types:
            if issue_type in results["issues_by_type"]:
                for item in results["issues_by_type"][issue_type]:
                    print(f"File: {item['file']}")
                    print(f"  Issue: {item['message']}")
                    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if has_critical:
        print("\n❌ Critical issues found that may break rendering!")
        sys.exit(1)
    elif results["files_with_issues"] > 0:
        print(f"\n⚠️  {results['files_with_issues']} files have non-critical issues")
        sys.exit(0)
    else:
        print("\n✅ All content files pass edge case checks!")
        sys.exit(0)


if __name__ == "__main__":
    main()
