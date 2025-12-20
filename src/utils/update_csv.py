import os
import json
import csv
import glob
import pandas as pd

RESULTS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'

# Load Metadata
metadata_cache = {}
if os.path.exists(METADATA_FILE):
    try:
        df_meta = pd.read_csv(METADATA_FILE, sep=';', on_bad_lines='skip')
        df_meta.columns = [c.strip().lower() for c in df_meta.columns]
        for _, row in df_meta.iterrows():
            code = str(row.get('istituto', '')).strip()
            if code:
                metadata_cache[code] = row.to_dict()
    except Exception as e:
        print(f"Error loading metadata: {e}")

all_data = []

json_files = glob.glob(os.path.join(RESULTS_DIR, "*_analysis.json"))
print(f"Found {len(json_files)} JSON files.")

for json_file in json_files:
    try:
        with open(json_file, 'r') as f:
            json_data = json.load(f)
            
        school_code = json_data.get('metadata', {}).get('school_id', 'Unknown')
        json_metadata = json_data.get('metadata', {})
        meta = metadata_cache.get(school_code, {'istituto': school_code})
        
        # Base Data - prefer JSON metadata if available
        row = {
            'school_id': school_code,
            'denominazione': json_metadata.get('denominazione', meta.get('denominazionescuola', 'ND')),
            'comune': meta.get('nome_comune', 'ND'),
            'analysis_file': json_file.replace('.json', '.md'),
            'duration_sec': 0,
            'extraction_status': json_data.get('extraction_quality', {}).get('status', 'ND')
        }
        
        # Scores
        section2 = json_data.get('ptof_section2', {})
        def get_score(sec_data):
            if isinstance(sec_data, dict):
                return sec_data.get('score', 0)
            return 0

        sec_2_1 = section2.get('2_1_ptof_orientamento_sezione_dedicata', {})
        row['2_1_score'] = get_score(sec_2_1)
        
        # Extract has_sezione_dedicata from JSON or infer from MD
        if 'has_sezione_dedicata' in sec_2_1:
            row['has_sezione_dedicata'] = sec_2_1.get('has_sezione_dedicata', 0)
        else:
            # Fallback: parse MD file for keywords
            md_file = json_file.replace('.json', '.md')
            has_section = 0
            if os.path.exists(md_file):
                with open(md_file, 'r') as mf:
                    md_text = mf.read().lower()
                    # If text says "non esiste sezione" or similar -> 0
                    if any(x in md_text for x in ['non essendo esplicitamente', 'non come area autonoma', 'non è presente una sezione', 'assenza di una sezione']):
                        has_section = 0
                    elif any(x in md_text for x in ['sezione dedicat', 'capitolo dedicat', 'area specifica', 'sezione specifica']):
                        has_section = 1
                    else:
                        has_section = 0  # Default to 0 if unclear
            row['has_sezione_dedicata'] = has_section
        
        sec_2_3 = section2.get('2_3_finalita', {})
        for key in sec_2_3:
            row[f"2_3_{key}_score"] = get_score(sec_2_3[key])
            
        sec_2_4 = section2.get('2_4_obiettivi', {})
        for key in sec_2_4:
            row[f"2_4_{key}_score"] = get_score(sec_2_4[key])
            
        # Derived Indices (Decimals)
        derived = json_data.get('derived_indices', {})
        for key, val in derived.items():
            row[key] = val
            
        all_data.append(row)
        
    except Exception as e:
        print(f"Error processing {json_file}: {e}")

if all_data:
    # Define fixed column order
    fixed_order = [
        'school_id', 'denominazione', 'comune', 'extraction_status', 'duration_sec', 'analysis_file',
        'has_sezione_dedicata', '2_1_score',
        '2_3_finalita_attitudini_score', '2_3_finalita_interessi_score', '2_3_finalita_progetto_vita_score',
        '2_3_finalita_transizioni_formative_score', '2_3_finalita_capacita_orientative_opportunita_score',
        '2_4_obiettivo_ridurre_abbandono_score', '2_4_obiettivo_continuita_territorio_score',
        '2_4_obiettivo_contrastare_neet_score', '2_4_obiettivo_lifelong_learning_score',
        'mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
        'partnership_count', 'activities_count', 'ptof_orientamento_maturity_index'
    ]
    
    # Collect any additional columns not in fixed order
    all_cols = set()
    for row in all_data:
        all_cols.update(row.keys())
    extra_cols = sorted([c for c in all_cols if c not in fixed_order])
    
    fieldnames = fixed_order + extra_cols
    
    # Ensure all rows have all columns (fill missing with '')
    for row in all_data:
        for col in fieldnames:
            if col not in row:
                row[col] = ''

    with open(SUMMARY_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    print(f"✅ Rebuilt summary CSV with {len(all_data)} rows and {len(fieldnames)} columns.")
else:
    print("No data found.")
