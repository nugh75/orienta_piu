import json
import os

SCHOOLS = ['RMTD087023', 'RMIC8CN00V', 'PG1E00400E']
RESULTS_DIR = 'analysis_results'

for school_id in SCHOOLS:
    json_path = os.path.join(RESULTS_DIR, f"{school_id}_PTOF_analysis.json")
    md_path = os.path.join(RESULTS_DIR, f"{school_id}_PTOF_analysis.md")
    
    if not os.path.exists(json_path):
        print(f"ERROR: JSON not found for {school_id} at {json_path}")
        continue
        
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        narrative = data.get('narrative')
        if not narrative:
            print(f"WARNING: No 'narrative' field in JSON for {school_id}")
            # Fallback or skip? Let's skip for now and report
            continue
            
        with open(md_path, 'w') as f:
            f.write(narrative)
        print(f"SUCCESS: Generated {md_path}")
        
    except Exception as e:
        print(f"ERROR processing {school_id}: {e}")
