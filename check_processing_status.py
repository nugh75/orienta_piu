
import os
import csv
import glob
from pathlib import Path

def main():
    ptof_dir = Path("ptof_md")
    summary_file = Path("data/analysis_summary.csv")
    
    # 1. Get all markdown files
    md_files = list(ptof_dir.glob("*_ptof.md"))
    print(f"Total MD files found: {len(md_files)}")
    
    # 2. Extract codes
    file_map = {} # code -> filename
    for p in md_files:
        # Assumes format CODE_ptof.md
        code = p.name.split('_')[0].upper()
        file_map[code] = p.name
        
    print(f"Unique codes extracted from files: {len(file_map)}")
    
    # 3. Get processed codes
    processed_codes = set()
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('school_id'):
                    processed_codes.add(row['school_id'].upper())
    print(f"Processed codes in summary CSV: {len(processed_codes)}")
    
    # 4. Compare
    processed_files = []
    unprocessed_files = []
    
    for code, filename in file_map.items():
        if code in processed_codes:
            processed_files.append(filename)
        else:
            unprocessed_files.append(filename)
            
    # 5. Report
    print(f"\n--- Analysis Results ---")
    print(f"Processed Files: {len(processed_files)}")
    print(f"Unprocessed Files: {len(unprocessed_files)}")
    
    # Save lists
    with open("data/ptof_unprocessed_list.txt", "w") as f:
        for name in sorted(unprocessed_files):
            f.write(f"{name}\n")
            
    print(f"\nUnprocessed list saved to: data/ptof_unprocessed_list.txt")
    print("First 10 unprocessed files:")
    for f in sorted(unprocessed_files)[:10]:
        print(f" - {f}")

if __name__ == "__main__":
    main()
