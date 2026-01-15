#!/usr/bin/env python3
"""
Apply targeted accessibility fixes based on pa11y log output.

Currently handles:
- Empty headings (<h3></h3>) caused by blank markdown heading lines (e.g., "###")
- Broken in-page anchor links like [4](#4) without a matching anchor target

Usage:
  python scripts/fix_508_from_pa11y.py /tmp/pa11y-all-pages.log
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"

URL_LINE = re.compile(r"^Errors in (https?://.+):$")
HEADING_ERR = "Heading tag found with no content"
ANCHOR_ERR = re.compile(r'link points to a named anchor "([^"]+)"', re.IGNORECASE)


def parse_frontmatter_url(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    front = parts[1].splitlines()
    for line in front:
        if line.strip().startswith("url:"):
            _, value = line.split(":", 1)
            value = value.strip().strip('"').strip("'")
            return value
    return None


def build_url_index() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for md in CONTENT_DIR.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        url = parse_frontmatter_url(text)
        if not url:
            continue
        # Normalize url to include leading slash and no trailing slash.
        if not url.startswith("/"):
            url = "/" + url
        url = url.rstrip("/")
        mapping[url] = md
    return mapping


def has_anchor_target(text: str, anchor: str) -> bool:
    patterns = [
        rf'id="{re.escape(anchor)}"',
        rf'name="{re.escape(anchor)}"',
        rf"\{{#\s*{re.escape(anchor)}\s*\}}",
        rf"<a[^>]+id=[\"']{re.escape(anchor)}[\"']",
        rf"<a[^>]+name=[\"']{re.escape(anchor)}[\"']",
    ]
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def fix_empty_headings(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    new_lines = []
    removed = 0
    for line in lines:
        if re.match(r"^\s*#{2,6}\s*$", line):
            removed += 1
            continue
        new_lines.append(line)
    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), removed


def fix_broken_anchor_links(text: str, anchor: str) -> tuple[str, int]:
    # Replace [4](#4) -> [4], [[4]](#4) -> [4]
    replacements = 0

    def repl(match: re.Match) -> str:
        nonlocal replacements
        replacements += 1
        label = match.group(1)
        return f"[{label}]"

    text, n1 = re.subn(rf"\[\[([^\]]+)\]\]\(#{re.escape(anchor)}\)", repl, text)
    replacements += n1
    text, n2 = re.subn(rf"\[([^\]]+)\]\(#{re.escape(anchor)}\)", repl, text)
    replacements += n2
    return text, replacements


def main() -> int:
    args = sys.argv[1:]
    all_content = False
    if "--all-content" in args:
        all_content = True
        args = [a for a in args if a != "--all-content"]
    if len(args) != 1:
        print("Usage: python scripts/fix_508_from_pa11y.py /path/to/pa11y.log [--all-content]", file=sys.stderr)
        return 2

    log_path = Path(args[0])
    if not log_path.exists():
        print(f"Log file not found: {log_path}", file=sys.stderr)
        return 2

    url_errors: dict[str, dict[str, list[str]]] = {}
    current_url: str | None = None

    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = URL_LINE.match(line.strip())
        if m:
            current_url = m.group(1)
            url_errors.setdefault(current_url, {"heading": [], "anchor": []})
            continue
        if current_url is None:
            continue
        if HEADING_ERR in line:
            url_errors[current_url]["heading"].append(line.strip())
        m = ANCHOR_ERR.search(line)
        if m:
            url_errors[current_url]["anchor"].append(m.group(1))

    if not url_errors and not all_content:
        print("No errors found in log. Re-run with --all-content to apply global fixes.")
        return 0

    url_index = build_url_index()
    updated_files = 0
    total_heading_fixes = 0
    total_anchor_fixes = 0
    unresolved: list[str] = []

    for url, errors in url_errors.items():
        path = "/" + url.split("://", 1)[-1].split("/", 1)[-1]
        path = "/" + path.lstrip("/")
        path = path.rstrip("/")
        md = url_index.get(path)
        if not md:
            unresolved.append(url)
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            unresolved.append(url)
            continue

        changed = False

        if errors["heading"]:
            new_text, removed = fix_empty_headings(text)
            if removed > 0:
                text = new_text
                total_heading_fixes += removed
                changed = True

        for anchor in errors["anchor"]:
            if has_anchor_target(text, anchor):
                continue
            new_text, reps = fix_broken_anchor_links(text, anchor)
            if reps > 0:
                text = new_text
                total_anchor_fixes += reps
                changed = True

        if changed:
            md.write_text(text, encoding="utf-8")
            updated_files += 1

    if all_content:
        # Global pass to catch empty headings and orphaned numeric anchors across all content.
        for md in CONTENT_DIR.rglob("*.md"):
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue

            changed = False
            new_text, removed = fix_empty_headings(text)
            if removed > 0:
                text = new_text
                total_heading_fixes += removed
                changed = True

            # Fix orphaned numeric anchors like [4](#4) when no matching target exists.
            for anchor in set(re.findall(r"\(#(\d+)\)", text)):
                if has_anchor_target(text, anchor):
                    continue
                new_text, reps = fix_broken_anchor_links(text, anchor)
                if reps > 0:
                    text = new_text
                    total_anchor_fixes += reps
                    changed = True

            if changed:
                md.write_text(text, encoding="utf-8")
                updated_files += 1

    print(f"Updated files: {updated_files}")
    print(f"Empty heading lines removed: {total_heading_fixes}")
    print(f"Broken anchor links fixed: {total_anchor_fixes}")
    if unresolved:
        print("Unresolved URLs (no matching content file):")
        for url in unresolved:
            print(f"  - {url}")

    # Return non-zero if there are unresolved URLs or no fixes applied.
    if unresolved:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
