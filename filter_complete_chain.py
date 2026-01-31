
import pandas as pd
import shutil
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def main():
    print("--- STRICT DATASET FILTERING (The Golden List) ---")
    
    # Paths
    summary_path = Path("data/analysis_summary.csv")
    attivita_path = Path("data/attivita.csv")
    
    ptof_dirs = [Path("ptof_processed"), Path("ptof_inbox"), Path("ptof_discarded")]
    md_dir = Path("ptof_md")
    analysis_dir = Path("analysis_results")
    
    if not summary_path.exists():
        print("Error: analysis_summary.csv not found")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Map all artifacts
    print("1. Mapping artifacts...")
    
    # PDFs
    pdf_codes = set()
    for d in ptof_dirs:
        if d.exists():
            for p in d.rglob("*.pdf"):
                parts = p.name.split('_')
                if parts: pdf_codes.add(parts[0].upper())
    print(f" - Found PDFs for {len(pdf_codes)} unique codes")
    
    # MDs
    md_codes = set()
    for p in md_dir.glob("*_ptof.md"):
        md_codes.add(p.name.split('_')[0].upper())
    print(f" - Found MDs for {len(md_codes)} unique codes")
    
    # Reports (Check for JSON or MD report)
    report_codes = set()
    for p in analysis_dir.glob("*_PTOF_analysis.json"):
        report_codes.add(p.name.split('_')[0].upper())
    # Supplement with .md reports if json missing (legacy support)
    for p in analysis_dir.glob("*_PTOF_analysis.md"):
        report_codes.add(p.name.split('_')[0].upper())
    print(f" - Found Analysis Reports for {len(report_codes)} unique codes")
    
    # Activities (Check which codes have activities)
    act_codes = set()
    if attivita_path.exists():
        try:
            df_act = pd.read_csv(attivita_path)
            if 'codice_meccanografico' in df_act.columns:
                act_codes = set(df_act['codice_meccanografico'].dropna().astype(str).str.upper().str.strip())
        except Exception:
            pass
    print(f" - Found Activities for {len(act_codes)} unique codes")

    # 2. Identify Complete Chains
    # Intersection of ALL sets
    golden_codes = pdf_codes.intersection(md_codes).intersection(report_codes).intersection(act_codes)
    print(f"\n✅ GOLDEN SET (Complete Chain): {len(golden_codes)} schools")
    
    if len(golden_codes) == 0:
        print("WARNING: Golden set is empty! Aborting to prevent deleting everything.")
        return

    # 3. Filter Database
    print("\n3. Filtering Databases...")
    
    # Summary CSV
    df_summary = pd.read_csv(summary_path)
    original_sum_len = len(df_summary)
    
    # Filter
    df_summary_clean = df_summary[df_summary['school_id'].astype(str).str.upper().str.strip().isin(golden_codes)]
    new_sum_len = len(df_summary_clean)
    
    # Attivita CSV
    df_act_clean = pd.DataFrame()
    original_act_len = 0
    new_act_len = 0
    
    if activating_path := attivita_path.exists(): # walrus just for check
        df_act = pd.read_csv(attivita_path)
        original_act_len = len(df_act)
        df_act_clean = df_act[df_act['codice_meccanografico'].astype(str).str.upper().str.strip().isin(golden_codes)]
        new_act_len = len(df_act_clean)

    print(f" - Summary: {original_sum_len} -> {new_sum_len} (Removing {original_sum_len - new_sum_len})")
    print(f" - Activities: {original_act_len} -> {new_act_len} (Removing {original_act_len - new_act_len})")
    
    # 4. Save Backups and Apply
    # Summary
    if new_sum_len < original_sum_len:
        bk_sum = summary_path.with_suffix(f".bak.strict.{timestamp}.csv")
        shutil.copy(summary_path, bk_sum)
        df_summary_clean.to_csv(summary_path, index=False)
        print(f" - Applied to analysis_summary.csv (Backup: {bk_sum})")
        
    # Activities
    if new_act_len < original_act_len:
        bk_act = attivita_path.with_suffix(f".bak.strict.{timestamp}.csv")
        shutil.copy(attivita_path, bk_act)
        df_act_clean.to_csv(attivita_path, index=False)
        print(f" - Applied to attivita.csv (Backup: {bk_act})")

    # 5. Log removed
    kept_log = Path("data/golden_chain_schools.txt")
    with open(kept_log, "w") as f:
        f.write("\n".join(sorted(golden_codes)))
    print(f"\nList of kept schools saved to: {kept_log}")

if __name__ == "__main__":
    main()
