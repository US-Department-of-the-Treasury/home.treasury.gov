#!/usr/bin/env python3
"""
Normalize press release datelines to consistent bold format.

Targets patterns like:
  **WASHINGTON** –Today ...
  **WASHINGTON**- Today ...
  **WASHINGTON**-- Today ...

Normalizes to:
  **WASHINGTON –** Today ...
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESS_RELEASES_DIR = ROOT / "content" / "news" / "press-releases"

DATELINE_RE = re.compile(r"^\*\*WASHINGTON\*\*\s*[–—-]+\s*", re.UNICODE)
REPLACEMENT = "**WASHINGTON –** "


def normalize_dateline(text: str) -> tuple[str, int]:
    replaced = 0
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        new_line, n = DATELINE_RE.subn(REPLACEMENT, line)
        replaced += n
        new_lines.append(new_line)
    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), replaced


def main() -> int:
    if not PRESS_RELEASES_DIR.exists():
        raise SystemExit(f"Missing directory: {PRESS_RELEASES_DIR}")

    changed_files = []
    total_replacements = 0

    for md in sorted(PRESS_RELEASES_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        updated, count = normalize_dateline(text)
        if count:
            md.write_text(updated, encoding="utf-8")
            changed_files.append(md)
            total_replacements += count

    print(f"Files updated: {len(changed_files)}")
    print(f"Datelines normalized: {total_replacements}")
    if changed_files:
        print("Changed files:")
        for path in changed_files:
            print(f"  - {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
