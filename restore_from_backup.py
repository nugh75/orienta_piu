import os
import shutil
from pathlib import Path

ANALYSIS_DIR = Path("analysis_results")
BACKUP_DIR = Path("analysis_results/pre_review_backup")

def is_truncated(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return True
            if content.startswith("```") and not content.endswith("```"):
                return True
            last_char = content[-1]
            # Added '}' and ']' as some valid endings
            if last_char not in ['.', '!', '?', '>', '`', '\n', '}', ']']: 
                return True
            return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def restore_files():
    if not BACKUP_DIR.exists():
        print(f"Backup directory {BACKUP_DIR} does not exist.")
        return

    truncated_count = 0
    restored_count = 0
    
    files = sorted(list(ANALYSIS_DIR.glob("*_PTOF_analysis.md")))
    print(f"Scanning {len(files)} files in {ANALYSIS_DIR}...")

    for file_path in files:
        if is_truncated(file_path):
            truncated_count += 1
            print(f"Truncated: {file_path.name}")
            
            backup_path = BACKUP_DIR / file_path.name
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    print(f"  Restored from backup.")
                    restored_count += 1
                except Exception as e:
                    print(f"  Error restoring from backup: {e}")
            else:
                print(f"  No backup found in {BACKUP_DIR}")

    print(f"\nSummary:")
    print(f"Truncated files found: {truncated_count}")
    print(f"Files restored: {restored_count}")

if __name__ == "__main__":
    restore_files()
