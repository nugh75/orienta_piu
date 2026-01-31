
import os
import glob
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Cleanup Filesystem Orphans")
    parser.add_argument("--delete", action="store_true", help="Actually delete files (default is DRY RUN)")
    args = parser.parse_args()

    print("--- FILESYSTEM CLEANUP (Orphan Removal) ---")
    
    # 1. Load Valid Codes
    golden_list_path = Path("data/golden_chain_schools.txt")
    if not golden_list_path.exists():
        print("Error: data/golden_chain_schools.txt not found. Run filter_complete_chain.py first.")
        return
        
    with open(golden_list_path, "r") as f:
        valid_codes = set(line.strip().upper() for line in f if line.strip())
        
    print(f"Loaded {len(valid_codes)} valid 'Golden' codes.")
    
    # 2. Define Scanning Paths
    # (Path, Glob Pattern, Extraction Func)
    targets = [
        # PDFs
        (Path("ptof_processed"), "**/*.pdf", lambda p: p.name.split('_')[0].upper()),
        (Path("ptof_inbox"), "*.pdf", lambda p: p.name.split('_')[0].upper()),
        (Path("ptof_discarded"), "*.pdf", lambda p: p.name.split('_')[0].upper()),
        # MDs
        (Path("ptof_md"), "*.md", lambda p: p.name.split('_')[0].upper()),
        (Path("ptof_md/conflicts"), "*.md", lambda p: p.name.split('_')[0].upper()),
        # Analysis
        (Path("analysis_results"), "*_PTOF_analysis.json", lambda p: p.name.split('_')[0].upper()),
        (Path("analysis_results"), "*_PTOF_analysis.md", lambda p: p.name.split('_')[0].upper()),
        (Path("ptof_processed"), "**/*.json", lambda p: p.name.split('.')[0].upper() if len(p.name.split('.')[0]) >= 10 else None) # Processed JSONs
    ]
    
    deleted_count = 0
    total_size_mb = 0
    
    print("\nScanning for orphans...")
    
    for base_dir, pattern, extractor in targets:
        if not base_dir.exists():
            continue
            
        # Recursive glob if pattern has **
        if "**" in pattern:
            files = list(base_dir.rglob(pattern.replace("**/" , "")))
        else:
            files = list(base_dir.glob(pattern))
            
        for f in files:
            if f.is_dir(): continue
            
            try:
                code = extractor(f)
            except Exception:
                code = None
                
            # If code is invalid or NOT in valid_codes -> DELETE
            if not code or code not in valid_codes:
                size_mb = f.stat().st_size / (1024 * 1024)
                total_size_mb += size_mb
                deleted_count += 1
                
                if args.delete:
                    try:
                        f.unlink()
                        # print(f"Deleted: {f}")
                    except Exception as e:
                        print(f"Error deleting {f}: {e}")
                else:
                    # Dry run log (sample)
                    if deleted_count <= 5:
                        print(f" [DRY RUN] Would delete: {f} ({code})")
    
    action = "DELETED" if args.delete else "WOULD DELETE"
    
    print(f"\n--- Summary ---")
    print(f"Files to be {action}: {deleted_count}")
    print(f"Disk space to reclaim: {total_size_mb:.2f} MB")
    
    if not args.delete:
        print("\n*** DRY RUN COMPLETE ***")
        print("To verify and actually delete, run with: --delete")
    else:
        print("\n*** CLEANUP COMPLETE ***")

if __name__ == "__main__":
    main()
