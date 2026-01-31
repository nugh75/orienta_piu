
import pandas as pd
from pathlib import Path

def main():
    print("--- Investigating Missing Processed Files ---")
    
    # 1. Load processed codes from DB
    summary_path = Path("data/analysis_summary.csv")
    if not summary_path.exists():
        print("Error: data/analysis_summary.csv not found")
        return
        
    df = pd.read_csv(summary_path)
    # Ensure school_id exists and standardize
    if 'school_id' not in df.columns:
         print("Error: school_id column missing in CSV")
         return
         
    processed_codes = set(df['school_id'].dropna().astype(str).str.upper().str.strip())
    print(f"Processed schools in DB: {len(processed_codes)}")

    # 2. Load current ptof_md files
    ptof_dir = Path("ptof_md")
    current_files = list(ptof_dir.glob("*_ptof.md"))
    current_codes = set()
    for f in current_files:
        # Extract code from filename (CODE_ptof.md)
        parts = f.name.split('_')
        if parts:
            current_codes.add(parts[0].upper())
            
    print(f"Files currently in ptof_md: {len(current_codes)}")

    # 3. Identify missing codes (In DB but NOT in ptof_md)
    missing_codes = processed_codes - current_codes
    print(f"Missing codes (in DB but not in ptof_md): {len(missing_codes)}")

    # 4. Check conflicts directory
    conflicts_dir = ptof_dir / "conflicts"
    found_in_conflicts = []
    
    if conflicts_dir.exists():
        conflict_files = list(conflicts_dir.glob("*.md"))
        conflict_codes = set()
        
        # Build map of codes in conflicts
        for f in conflict_files:
             parts = f.name.split('_')
             if parts:
                code = parts[0].upper()
                conflict_codes.add(code)
        
        # Check intersection
        found_in_conflicts = missing_codes.intersection(conflict_codes)
        
    print(f"Found in conflicts folder: {len(found_in_conflicts)}")
    
    # 5. Report remaining missing
    still_missing = missing_codes - found_in_conflicts
    print(f"Still completely missing (not in root, not in conflicts): {len(still_missing)}")
    
    if len(found_in_conflicts) > 0:
        print("\nExamples found in conflicts:")
        for c in list(found_in_conflicts)[:10]:
            print(f" - {c}")

if __name__ == "__main__":
    main()
