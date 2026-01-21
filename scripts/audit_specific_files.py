#!/usr/bin/env python3
"""
Audit specific files against live Treasury.gov

Usage:
    python scripts/audit_specific_files.py /tmp/changed_files.txt
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent.parent
LIVE_SITE = "https://home.treasury.gov"


@dataclass
class Result:
    file: str
    url: str
    status: str
    similarity: float = 0.0
    local_title: str = ""
    live_title: str = ""
    error: str = ""


def extract_frontmatter(content: str):
    """Extract frontmatter from markdown."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = {}
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip("'\"")
            return fm, parts[2].strip()
    return {}, content


def normalize(text):
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text.lower().strip())[:3000]


async def audit_file(browser, file_path: Path, semaphore) -> Result:
    """Audit a single file."""
    async with semaphore:
        result = Result(file=str(file_path), url="", status="ok")
        
        try:
            content = file_path.read_text(encoding="utf-8")
            fm, body = extract_frontmatter(content)
            
            url_path = fm.get("url", "")
            if not url_path:
                rel = file_path.relative_to(BASE_DIR / "content")
                url_path = "/" + str(rel).replace(".md", "")
            
            result.url = url_path
            result.local_title = fm.get("title", "")
            
            context = await browser.new_context()
            try:
                page = await context.new_page()
                url = f"{LIVE_SITE}{url_path}"
                
                resp = await page.goto(url, wait_until="networkidle", timeout=30000)
                
                if resp and resp.status == 404:
                    result.status = "not_found"
                    return result
                
                await asyncio.sleep(0.5)
                
                # Get title
                title = await page.title()
                result.live_title = re.sub(r"\s*\|.*$", "", title).strip()
                
                # Get content
                region = await page.query_selector(".region-content")
                if region:
                    live_text = await region.inner_text()
                    
                    # Clean live text
                    lines = live_text.split("\n")
                    clean_lines = []
                    found_date = False
                    
                    for line in lines:
                        s = line.strip()
                        if not s or s.upper() in ["PRESS RELEASES", "NEWS", "HOME"]:
                            continue
                        if "(Archived Content)" in s:
                            continue
                        
                        if not found_date:
                            for m in ["January", "February", "March", "April", "May", "June",
                                      "July", "August", "September", "October", "November", "December"]:
                                if m in s and len(s) < 50:
                                    found_date = True
                                    break
                            if found_date:
                                continue
                        
                        if found_date:
                            clean_lines.append(s)
                    
                    live_content = " ".join(clean_lines)
                    
                    # Compare
                    sim = SequenceMatcher(None, normalize(body), normalize(live_content)).ratio()
                    result.similarity = sim
                    
                    if sim < 0.3:
                        result.status = "hallucination"
                    elif sim < 0.6:
                        result.status = "mismatch"
                    else:
                        result.status = "ok"
                else:
                    result.status = "no_content"
                    
            finally:
                await context.close()
                
        except Exception as e:
            result.status = "error"
            result.error = str(e)[:100]
        
        return result


async def run_audit(files: list, workers: int = 20):
    """Run audit on all files."""
    print(f"\n{'='*60}")
    print("Auditing Changed Files")
    print(f"{'='*60}")
    print(f"Files: {len(files)}")
    print(f"Workers: {workers}")
    print()
    
    semaphore = asyncio.Semaphore(workers)
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        tasks = [audit_file(browser, f, semaphore) for f in files]
        
        completed = 0
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            completed += 1
            
            icon = "✓" if r.status == "ok" else "⚠️" if r.status == "hallucination" else "⚡" if r.status == "mismatch" else "✗"
            sim = f" ({r.similarity:.0%})" if r.similarity > 0 else ""
            print(f"  {icon} [{completed}/{len(files)}] {r.file}{sim}")
        
        await browser.close()
    
    # Summary
    ok = sum(1 for r in results if r.status == "ok")
    hall = sum(1 for r in results if r.status == "hallucination")
    mis = sum(1 for r in results if r.status == "mismatch")
    err = sum(1 for r in results if r.status in ["error", "not_found", "no_content"])
    
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"OK (>60% match): {ok}")
    print(f"Mismatch (30-60%): {mis}")
    print(f"Hallucination (<30%): {hall}")
    print(f"Errors/Not Found: {err}")
    
    if hall > 0:
        print(f"\n⚠️  {hall} HALLUCINATIONS STILL DETECTED:")
        for r in results:
            if r.status == "hallucination":
                print(f"   - {r.file} ({r.similarity:.0%})")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python audit_specific_files.py <file_list.txt>")
        sys.exit(1)
    
    file_list = Path(sys.argv[1])
    files = []
    
    for line in file_list.read_text().strip().split("\n"):
        f = BASE_DIR / line.strip()
        if f.exists() and f.suffix == ".md":
            files.append(f)
    
    print(f"Found {len(files)} files to audit")
    
    asyncio.run(run_audit(files))


if __name__ == "__main__":
    main()
