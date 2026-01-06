import os
import glob
from collections import Counter

# Configuration
MD_DIR = 'ptof_md'
RESULTS_DIR = 'analysis_results'

# Keywords that suggest it IS a PTOF
VALID_KEYWORDS = ['piano', 'triennale', 'offerta', 'formativa', 'ptof', 'scuola', 'istituto', 'orientamento']
# Keywords that suggest it is an ERROR or INDEX page
INVALID_KEYWORDS = ['404', 'not found', 'error', 'non presente', 'accedi', 'login']

def get_status(filepath):
    try:
        size = os.path.getsize(filepath)
        if size < 500: # Less than 500 bytes is suspicious
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
            if any(k in content for k in INVALID_KEYWORDS):
                return "ERROR_MSG"
            return "TOO_SMALL"
            
        # Read first 2KB for header check
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(2048).lower()
            
        if any(k in head for k in VALID_KEYWORDS):
            return "VALID_PTOF"
            
        return "UNCERTAIN"
    except Exception as e:
        return f"READ_ERROR"

def main():
    # 1. Identify pending
    md_files = glob.glob(os.path.join(MD_DIR, '*_ptof.md'))
    json_files = glob.glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
    
    md_map = {os.path.basename(f).split('_')[0]: f for f in md_files}
    json_codes = {os.path.basename(f).split('_')[0] for f in json_files}
    
    pending_codes = set(md_map.keys()) - json_codes
    
    print(f"Analyzing {len(pending_codes)} pending files...\n")
    
    stats = Counter()
    details = {
        "VALID_PTOF": [],
        "TOO_SMALL": [],
        "ERROR_MSG": [],
        "UNCERTAIN": [],
        "READ_ERROR": []
    }
    
    for code in pending_codes:
        fpath = md_map[code]
        status = get_status(fpath)
        stats[status] += 1
        details[status].append(code)
        
    # Report
    print("--- Assessment Summary ---")
    for category, count in stats.items():
        print(f"{category}: {count}")
        
    print("\n--- Details ---")
    if details['VALID_PTOF']:
        print(f"\n[VALID_PTOF] ({len(details['VALID_PTOF'])} files):")
        print(f"Top 10: {', '.join(sorted(details['VALID_PTOF'])[:10])}")
        
    if details['UNCERTAIN']:
        print(f"\n[UNCERTAIN] ({len(details['UNCERTAIN'])} files):")
        # Print path and size for uncertain ones
        for code in sorted(details['UNCERTAIN'])[:5]:
            path = md_map[code]
            print(f"- {code}: {os.path.basename(path)} ({os.path.getsize(path)} bytes)")

    if details['TOO_SMALL']:
        print(f"\n[TOO_SMALL/EMPTY] ({len(details['TOO_SMALL'])} files):")
        print(f"Top 5: {', '.join(sorted(details['TOO_SMALL'])[:5])}")

if __name__ == "__main__":
    main()
