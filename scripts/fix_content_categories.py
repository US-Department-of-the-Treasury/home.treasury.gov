#!/usr/bin/env python3
"""
Fix Content Categories

Analyzes existing content and moves files to correct category folders
based on title and content analysis, while preserving original URLs.

Usage:
    python scripts/fix_content_categories.py --dry-run
    python scripts/fix_content_categories.py --apply
"""

import argparse
import re
import shutil
from pathlib import Path
from typing import List, Optional


CONTENT_DIR = Path(__file__).parent.parent / "content" / "news"

# Category detection patterns
CATEGORY_PATTERNS = {
    "readouts": [
        r"^Readout",
        r"^READOUT",
    ],
    "statements-remarks": [
        r"^Statement by",
        r"^STATEMENT BY",
        r"^Joint Statement",
        r"^JOINT STATEMENT",
        r"^Remarks by",
        r"^REMARKS BY",
    ],
    "testimonies": [
        r"^Testimony",
        r"^TESTIMONY",
        r"testifies before",
        r"TESTIFIES BEFORE",
    ],
}


def detect_category_from_title(title: str) -> Optional[str]:
    """Detect the correct category based on title patterns."""
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return category
    return None


def analyze_file(filepath: Path) -> dict:
    """Analyze a markdown file and return its metadata."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract front matter
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    url_match = re.search(r'^url:\s*(.+)$', content, re.MULTILINE)
    
    title = title_match.group(1).strip("'\"") if title_match else ""
    url = url_match.group(1).strip() if url_match else ""
    
    current_category = filepath.parent.name
    detected_category = detect_category_from_title(title)
    
    return {
        "filepath": filepath,
        "title": title,
        "url": url,
        "current_category": current_category,
        "detected_category": detected_category,
        "needs_move": detected_category and detected_category != current_category,
    }


def find_miscategorized_files() -> List[dict]:
    """Find all files that appear to be in the wrong category."""
    miscategorized = []
    
    for category_dir in CONTENT_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for md_file in category_dir.glob("*.md"):
            if md_file.name == "_index.md":
                continue
            
            try:
                info = analyze_file(md_file)
                if info["needs_move"]:
                    miscategorized.append(info)
            except Exception as e:
                print(f"Error analyzing {md_file}: {e}")
    
    return miscategorized


def move_file(info: dict, dry_run: bool = True) -> bool:
    """Move a file to its correct category folder."""
    src = info["filepath"]
    dest_dir = CONTENT_DIR / info["detected_category"]
    dest = dest_dir / src.name
    
    if dry_run:
        print(f"  Would move: {src.name}")
        print(f"    From: {info['current_category']}/")
        print(f"    To:   {info['detected_category']}/")
        print(f"    Title: {info['title'][:60]}")
        return True
    
    # Create destination directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if destination exists
    if dest.exists():
        print(f"  ⚠️ Destination exists, skipping: {dest}")
        return False
    
    # Move the file
    shutil.move(str(src), str(dest))
    print(f"  ✅ Moved: {src.name} → {info['detected_category']}/")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fix miscategorized news content",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually move files (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    print("🔍 Scanning for miscategorized content...")
    print(f"📁 Content directory: {CONTENT_DIR}")
    print()
    
    miscategorized = find_miscategorized_files()
    
    if not miscategorized:
        print("✅ No miscategorized files found!")
        return
    
    # Group by detected category
    by_category = {}
    for info in miscategorized:
        cat = info["detected_category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(info)
    
    print(f"Found {len(miscategorized)} miscategorized files:\n")
    
    for category, files in sorted(by_category.items()):
        print(f"📂 Should be in '{category}' ({len(files)} files):")
        for info in files:
            print(f"  • {info['filepath'].name}")
            print(f"    Title: {info['title'][:70]}")
        print()
    
    if dry_run:
        print("=" * 50)
        print("🔍 DRY RUN - No changes made")
        print("Run with --apply to move files")
    else:
        print("=" * 50)
        print("📦 Moving files...")
        print()
        
        moved = 0
        for info in miscategorized:
            if move_file(info, dry_run=False):
                moved += 1
        
        print()
        print(f"✅ Moved {moved} files to correct categories")


if __name__ == "__main__":
    main()
