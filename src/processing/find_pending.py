import os
import glob
from pathlib import Path

# Paths
MD_DIR = 'ptof_md'
RESULTS_DIR = 'analysis_results'

def get_school_code_from_md(filename):
    # Format: SchoolCode_ptof.md or similar
    # e.g., BGMM818013_ptof.md
    base = os.path.basename(filename)
    return base.split('_')[0]

def get_school_code_from_json(filename):
    # Format: SchoolCode_PTOF_analysis.json
    base = os.path.basename(filename)
    return base.split('_')[0]

def main():
    md_files = glob.glob(os.path.join(MD_DIR, '*_ptof.md'))
    json_files = glob.glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
    
    md_codes = {get_school_code_from_md(f) for f in md_files}
    json_codes = {get_school_code_from_json(f) for f in json_files}
    
    pending = md_codes - json_codes
    
    print(f"Total MD files (Downloads): {len(md_codes)}")
    print(f"Total JSON files (Analyses): {len(json_codes)}")
    print(f"Pending Analysis: {len(pending)}")
    
    if pending:
        print("\n--- Pending Schools (Top 20) ---")
        for code in sorted(list(pending))[:20]:
            # Get file size to see if they are 'large' files
            md_path = os.path.join(MD_DIR, f"{code}_ptof.md")
            size_mb = os.path.getsize(md_path) / (1024 * 1024)
            print(f"- {code} ({size_mb:.2f} MB)")
            
        print("\n(Run with --all to see full list)")

if __name__ == "__main__":
    main()
