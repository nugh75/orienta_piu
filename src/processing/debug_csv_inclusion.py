import os
import json
import glob
from pathlib import Path
import sys

# Mock imports or add path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.school_code_parser import extract_canonical_code

TARGET_SCHOOLS = ['BGMM818013', 'BG1M02500P', 'BATD105005', 'BATD665005']
RESULTS_DIR = 'analysis_results'

print(f"Checking {len(TARGET_SCHOOLS)} target schools in {RESULTS_DIR}")

for school in TARGET_SCHOOLS:
    pattern = os.path.join(RESULTS_DIR, f"*{school}*_analysis.json")
    files = glob.glob(pattern)
    print(f"\n--- School: {school} ---")
    print(f"Glob pattern: {pattern}")
    print(f"Found {len(files)} files: {files}")
    
    for fpath in files:
        print(f"  Checking {fpath}...")
        
        # Test 1: Code extraction
        raw = os.path.basename(fpath).replace('_analysis.json', '')
        extracted = extract_canonical_code(raw)
        print(f"    Raw base: '{raw}', Extracted: '{extracted}'")
        if extracted != school:
            print(f"    !! MISMATCH: Extracted '{extracted}' != Target '{school}'")
            
        # Test 2: JSON Load
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            print("    JSON Load: OK")
            
            # Test 3: Metadata Check
            meta = data.get('metadata', {})
            print(f"    Metadata keys: {list(meta.keys())}")
            print(f"    ID in Metadata: {meta.get('school_id')}")
            
        except Exception as e:
            print(f"    !! JSON Load FAILED: {e}")
