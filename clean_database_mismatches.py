
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime

def main():
    print("--- Database Cleanup: Removing Impostor Entries ---")
    
    summary_path = Path("data/analysis_summary.csv")
    ptof_dir = Path("ptof_md")
    conflicts_dir = ptof_dir / "conflicts"
    
    if not summary_path.exists():
        print("Error: data/analysis_summary.csv not found")
        return

    # 1. Load Database
    df = pd.read_csv(summary_path)
    original_count = len(df)
    print(f"Original Database Entries: {original_count}")
    
    # 2. Identify Invalid Codes
    # Strategy: Any code in DB that does NOT exist in ptof_md (root) AND DOES exist in conflicts
    # is an "impostor" entry (data generated from a file that had the wrong content).
    
    current_files = list(ptof_dir.glob("*_ptof.md"))
    current_codes = set()
    for f in current_files:
        current_codes.add(f.name.split('_')[0].upper())
        
    db_codes = set(df['school_id'].dropna().astype(str).str.upper().str.strip())
    
    # Missing from root
    missing_from_root = db_codes - current_codes
    
    # Confirm they are in conflicts (to be safe we only delete known conflicts)
    conflict_codes = set()
    if conflicts_dir.exists():
        for f in conflicts_dir.glob("*.md"):
            conflict_codes.add(f.name.split('_')[0].upper())
            
    # Intersection: Codes in DB, Missing from Root, Present in Conflicts
    to_remove = missing_from_root.intersection(conflict_codes)
    
    print(f"Entries identifying as 'Impostors' (invalid data source): {len(to_remove)}")
    
    if len(to_remove) == 0:
        print("No entries to remove. Database seems clean or consistent with file system.")
        return

    # 3. Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = summary_path.with_suffix(f".bak.{timestamp}.csv")
    shutil.copy(summary_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    # 4. Filter and Save
    df_clean = df[~df['school_id'].astype(str).str.upper().str.strip().isin(to_remove)]
    new_count = len(df_clean)
    
    df_clean.to_csv(summary_path, index=False)
    
    print(f"\n--- Cleanup Complete ---")
    print(f"Rows Removed: {original_count - new_count}")
    print(f"New Database Size: {new_count}")
    
    # Save list of removed codes
    removed_log = Path("data/removed_impostors_log.txt")
    with open(removed_log, "w") as f:
        f.write("\n".join(sorted(to_remove)))
    print(f"List of removed codes saved to: {removed_log}")

if __name__ == "__main__":
    main()
