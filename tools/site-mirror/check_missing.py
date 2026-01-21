#!/usr/bin/env python3
"""
Check Missing URLs - Extract missing URLs from comparison report.

Usage:
    python check_missing.py report/text_comparison/text_comparison.json
    python check_missing.py report/text_comparison/text_comparison.json -o missing_urls.txt
    python check_missing.py report/text_comparison/text_comparison.json --focus /news/press-releases
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def load_comparison_report(report_path: Path) -> dict:
    """Load comparison report JSON."""
    with open(report_path) as f:
        return json.load(f)


def get_missing_urls(report: dict, missing_type: str = 'target') -> list[str]:
    """Extract missing URLs from comparison report."""
    missing = []
    status_key = f'missing_{missing_type}'

    for comp in report.get('comparisons', []):
        if comp.get('status') == status_key:
            missing.append(comp.get('url', ''))

    return missing


def main():
    parser = argparse.ArgumentParser(
        description='Extract missing URLs from comparison report'
    )
    parser.add_argument(
        'report',
        type=Path,
        help='Path to text_comparison.json report'
    )
    parser.add_argument(
        '--missing-type',
        choices=['target', 'source'],
        default='target',
        help='Type of missing URLs to extract (default: target)'
    )
    parser.add_argument(
        '--focus', '-f',
        help='Focus on specific path prefix'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('missing_urls.txt'),
        help='Output file (default: missing_urls.txt)'
    )

    args = parser.parse_args()

    # Load report
    if not args.report.exists():
        print(f"Error: Report not found: {args.report}")
        return 1

    report = load_comparison_report(args.report)
    missing_urls = get_missing_urls(report, args.missing_type)

    # Filter by focus path
    if args.focus:
        focus = args.focus.rstrip('/')
        missing_urls = [u for u in missing_urls if u.startswith(focus)]

    # Sort URLs
    missing_urls = sorted(missing_urls)

    # Write to file
    args.output.write_text('\n'.join(missing_urls))

    print(f"Found {len(missing_urls)} URLs missing in {args.missing_type}")
    print(f"Saved to: {args.output}")

    # Show sample
    if missing_urls:
        print(f"\nSample (first 10):")
        for url in missing_urls[:10]:
            print(f"  {url}")
        if len(missing_urls) > 10:
            print(f"  ... and {len(missing_urls) - 10} more")

    return 0


if __name__ == '__main__':
    exit(main())
