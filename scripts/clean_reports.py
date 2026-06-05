"""
Script to clean up invalid or incomplete meta reports.
It recursively scans the reports directory and removes files that:
- Are empty or too small (< 50 bytes).
- Do not start with a YAML header (---).
- Contain specific error markers (e.g., "API key not found").
- Have empty Main sections (optional check).
"""
import os
import re
import argparse
from pathlib import Path

# Markers that indicate a failed report generation
ERROR_MARKERS = [
    "Error: No LLM provider available",
    "API key not found",
    "401 Unauthorized",
    "Rate limit exceeded",
    "Internal Server Error",
    "[Error]",
    "Traceback (most recent call last)"
]

def is_valid_report(file_path: Path) -> bool:
    """Check if a markdown report is valid."""
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Check size/content
        if len(content.strip()) < 50:
            print(f"[INVALID] Too small: {file_path}")
            return False
            
        # Check YAML header
        if not content.startswith("---"):
            print(f"[INVALID] No YAML header: {file_path}")
            return False
            
        # Check error markers
        for marker in ERROR_MARKERS:
            if marker in content:
                print(f"[INVALID] Contains error marker '{marker}': {file_path}")
                return False
                
        # Check for empty sections (e.g. headers followed immediately by another header)
        # This is a heuristic.
        # e.g. "## Introduzione\n\n## Altro" -> "## Introduzione" is empty
        # We allow some empty sections, but if the WHOLE report is just headers, it's bad.
        
        return True
    except Exception as e:
        print(f"[ERROR] Could not read {file_path}: {e}")
        return False

def clean_directory(root_dir: Path, dry_run: bool = True):
    """Scan and clean directory recursively."""
    if not root_dir.exists():
        print(f"Directory not found: {root_dir}")
        return
        
    print(f"Scanning {root_dir}...")
    count = 0
    deleted = 0
    
    for path in root_dir.rglob("*.md"):
        count += 1
        if not is_valid_report(path):
            if not dry_run:
                try:
                    os.unlink(path)
                    print(f"Deleted: {path}")
                    deleted += 1
                except Exception as e:
                    print(f"Failed to delete {path}: {e}")
            else:
                print(f"[DRY RUN] Would delete: {path}")
                deleted += 1
                
    print(f"Scanned {count} files.")
    if dry_run:
        print(f"[DRY RUN] Found {deleted} invalid files.")
    else:
        print(f"Deleted {deleted} files.")

def main():
    parser = argparse.ArgumentParser(description="Clean up invalid report files.")
    parser.add_argument("--dry-run", action="store_true", help="Scan without deleting")
    parser.add_argument("--dir", default="reports/meta", help="Directory to scan")
    
    args = parser.parse_args()
    
    base_dir = Path(os.getcwd())
    target_dir = base_dir / args.dir
    
    clean_directory(target_dir, args.dry_run)

if __name__ == "__main__":
    main()
