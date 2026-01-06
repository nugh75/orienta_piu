import pandas as pd
import os
import glob

CSV_FILE = 'data/analysis_summary.csv'
RESULTS_DIR = 'analysis_results'

print(f"Reading {CSV_FILE}...")
try:
    df = pd.read_csv(CSV_FILE)
    print(f"Loaded {len(df)} rows.")
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit(1)

missing_md = []
for index, row in df.iterrows():
    school_id = row.get('school_id')
    if not school_id:
        continue
    
    # Expected MD path
    # Pattern: *{school_id}*_analysis.md
    # We can try to construct the exact name if we know it, or glob
    # The convention seems to be {SCHOOL_ID}_PTOF_analysis.md usually, but sometimes different prefix?
    # Let's use glob to be safe like the dashboard
    md_pattern = os.path.join(RESULTS_DIR, f"*{school_id}*_analysis.md")
    found = glob.glob(md_pattern)
    
    if not found:
        # Check specific name
        specific_md = os.path.join(RESULTS_DIR, f"{school_id}_PTOF_analysis.md")
        if not os.path.exists(specific_md):
            missing_md.append(school_id)
            print(f"MISSING MD for: {school_id}")

if not missing_md:
    print("ALL schools in CSV have a corresponding MD file.")
else:
    print(f"Found {len(missing_md)} schools missing MD files.")
    print(missing_md)
