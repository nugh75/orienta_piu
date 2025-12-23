
import os
import json
import csv
import glob
import re
import pandas as pd
import logging

from src.utils.constants import normalize_area_geografica

RESULTS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_index_safe():
    """
    Updates the analysis_summary.csv index from JSON files using a SAFE MERGE strategy.
    
    Strategy:
    1. Load existing CSV (if any) to preserve manual edits to metadata (Denominazione, Comune, ecc.)
    2. Load all JSON analysis files.
    3. Update/Insert records:
       - If School ID exists in CSV: 
         - Update ONLY analysis scores, file links, and status.
         - KEEP existing Name, City, Type from CSV (preserves user manual edits).
       - If School ID is new:
         - Insert robustly taking metadata from JSON.
    4. Save back to CSV.
    """
    
    # 1. Load Existing CSV to preserve Metadata
    existing_data = {}
    if os.path.exists(SUMMARY_FILE):
        try:
            df_existing = pd.read_csv(SUMMARY_FILE)
            # Create a dict keyed by school_id for fast lookup
            # We store the whole row as a dict
            if 'school_id' in df_existing.columns:
                for _, row in df_existing.iterrows():
                    sid = str(row['school_id']).strip()
                    if sid:
                        existing_data[sid] = row.to_dict()
            logger.info(f"Loaded {len(existing_data)} existing records from CSV.")
        except Exception as e:
            logger.error(f"Error reading existing CSV: {e}")

    # 2. Load Metadata Cache (fallback for new schools)
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
            logger.error(f"Error loading metadata cache: {e}")

    # 3. Process JSON Files
    json_files = glob.glob(os.path.join(RESULTS_DIR, "*_analysis.json"))
    logger.info(f"Found {len(json_files)} JSON analysis files.")
    
    all_rows = []
    processed_ids = set()

    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                json_data = json.load(f)
                
            json_meta = json_data.get('metadata', {})
            school_code = json_meta.get('school_id', 'Unknown').strip()
            
            if not school_code or school_code == 'Unknown':
                # Try to extract from filename if missing in JSON
                base = os.path.basename(json_file).replace('_analysis.json', '').replace('_PTOF', '')
                # Handle different naming patterns:
                # - MIIS08900V_analysis.json -> MIIS08900V
                # - RHO_MIIS08900V_analysis.json -> MIIS08900V
                # - BAIC818001-202225-202425-20250106_analysis.json -> BAIC818001
                # Try to find a 10-char school code (Italian meccanografico pattern)
                match = re.search(r'[A-Z]{2}[A-Z0-9]{8}', base.upper())
                if match:
                    school_code = match.group(0)
                else:
                    # Fallback: use first part before _ or -
                    parts = re.split(r'[_-]', base)
                    school_code = parts[0] if parts else base

            processed_ids.add(school_code)

            # Prepare New Data from JSON (Scores & Analysis Info)
            analysis_data = {
                'school_id': school_code,
                'analysis_file': json_file.replace('.json', '.md'),
                'extraction_status': json_data.get('extraction_quality', {}).get('status', 'ND')
            }

            # Extrac Scores
            section2 = json_data.get('ptof_section2', {})
            
            def get_score(sec_data):
                if isinstance(sec_data, dict):
                    return sec_data.get('score', 0)
                return 0

            # 2.1 Sezione Dedicata
            sec_2_1 = section2.get('2_1_ptof_orientamento_sezione_dedicata', {})
            analysis_data['2_1_score'] = get_score(sec_2_1)
            
            # Logic for has_sezione_dedicata
            if 'has_sezione_dedicata' in sec_2_1:
                analysis_data['has_sezione_dedicata'] = sec_2_1.get('has_sezione_dedicata', 0)
            else:
                # Fallback: parse MD file for keywords
                md_file = json_file.replace('.json', '.md')
                has_section = 0
                if os.path.exists(md_file):
                    try:
                        with open(md_file, 'r', errors='ignore') as mf:
                            md_text = mf.read().lower()
                        if any(x in md_text for x in ['non essendo esplicitamente', 'non come area autonoma', 'non è presente una sezione', 'assenza di una sezione']):
                            has_section = 0
                        elif any(x in md_text for x in ['sezione dedicat', 'capitolo dedicat', 'area specifica', 'sezione specifica']):
                            has_section = 1
                        else:
                            has_section = 0
                    except: pass
                analysis_data['has_sezione_dedicata'] = has_section

            # 2.2 Partnership
            sec_2_2 = section2.get('2_2_partnership', {})
            analysis_data['partnership_count'] = sec_2_2.get('partnership_count', 0)

            # 2.3 Finalita
            sec_2_3 = section2.get('2_3_finalita', {})
            for key in sec_2_3:
                analysis_data[f"2_3_{key}_score"] = get_score(sec_2_3[key])
            
            # 2.4 Obiettivi
            sec_2_4 = section2.get('2_4_obiettivi', {})
            for key in sec_2_4:
                analysis_data[f"2_4_{key}_score"] = get_score(sec_2_4[key])

            # 2.5 Governance (NEW from original script missing?) 
            # Original script didn't explicitly list 2.5 in 'fixed_order' but iterated dynamic keys.
            # We should include all section 2 keys found.
            sec_2_5 = section2.get('2_5_azioni_sistema', {})
            for key in sec_2_5:
                # Fix key format to match previous CSV style if needed, or just standard
                analysis_data[f"2_5_{key}_score"] = get_score(sec_2_5[key])

            # 2.6 Didattica
            sec_2_6 = section2.get('2_6_didattica_orientativa', {})
            for key in sec_2_6:
                analysis_data[f"2_6_{key}_score"] = get_score(sec_2_6[key])

            # 2.7 Opportunita
            sec_2_7 = section2.get('2_7_opzionali_facoltative', {})
            for key in sec_2_7:
                analysis_data[f"2_7_{key}_score"] = get_score(sec_2_7[key])

            # Activities Count
            # If activities_register is a list
            acts = json_data.get('activities_register', [])
            analysis_data['activities_count'] = len(acts) if isinstance(acts, list) else 0

            # Derived Indices
            derived = json_data.get('derived_indices', {})
            for key, val in derived.items():
                analysis_data[key] = val


            # MERGE STRATEGY
            if school_code in existing_data:
                # SAFE UPDATE: Start with existing row (Metadata preserved)
                merged_row = existing_data[school_code].copy()
                # Update with new analysis data (Scores overwritten)
                merged_row.update(analysis_data)
            else:
                # NEW INSERT: Start with JSON metadata
                meta_from_cache = metadata_cache.get(school_code, {'istituto': school_code})
                
                area_raw = json_meta.get('area_geografica') or meta_from_cache.get('area_geografica') or 'ND'
                area_norm = normalize_area_geografica(
                    area_raw,
                    regione=json_meta.get('regione'),
                    provincia_sigla=school_code[:2]
                )
                merged_row = {
                    'school_id': school_code,
                    'denominazione': json_meta.get('denominazione', meta_from_cache.get('denominazionescuola', 'ND')),
                    'comune': json_meta.get('comune', meta_from_cache.get('nome_comune', 'ND')),
                    'tipo_scuola': json_meta.get('tipo_scuola', 'ND'),
                    'area_geografica': area_norm if area_norm != 'ND' else 'ND',
                    'territorio': json_meta.get('territorio', 'ND'),
                    'ordine_grado': json_meta.get('ordine_grado', 'ND'),
                    'duration_sec': 0
                }
                # Add analysis data
                merged_row.update(analysis_data)
            
            area_norm = normalize_area_geografica(
                merged_row.get('area_geografica'),
                regione=merged_row.get('regione'),
                provincia_sigla=school_code[:2]
            )
            if area_norm != 'ND':
                merged_row['area_geografica'] = area_norm

            all_rows.append(merged_row)

        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")

    if all_rows:
        # Determine Field Names
        # Start with a fixed preferred order for Core columns
        core_cols = [
            'school_id', 'denominazione', 'comune', 'tipo_scuola', 'ordine_grado', 'area_geografica', 'territorio',
            'ptof_orientamento_maturity_index', 'extraction_status', 
            'mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
            'partnership_count', 'activities_count', 'has_sezione_dedicata', '2_1_score', 'analysis_file'
        ]
        
        # Collect all dynamic keys
        all_keys = set()
        for r in all_rows:
            all_keys.update(r.keys())
        
        # Sort extra cols
        extra_cols = sorted([k for k in all_keys if k not in core_cols])
        
        fieldnames = core_cols + extra_cols
        
        # Fill missing with empty string or nan
        for row in all_rows:
            for col in fieldnames:
                if col not in row:
                    row[col] = ''

        try:
            with open(SUMMARY_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
            
            logger.info(f"✅ Safe Update Complete: {len(all_rows)} schools indexed.")
            return True, len(all_rows)
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return False, 0
    else:
        logger.warning("No data found to update.")
        return False, 0

if __name__ == "__main__":
    update_index_safe()
