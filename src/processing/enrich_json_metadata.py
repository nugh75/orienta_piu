#!/usr/bin/env python3
"""
Standalone script to enrich JSON analysis files with metadata from CSV sources.
Run independently from the main pipeline.
Uses SchoolDatabase to get authoritative data from SCUANAGRAFESTAT and SCUANAGRAFEPAR.
"""
import os
import json
import re
import pandas as pd
from glob import glob

from src.utils.constants import normalize_area_geografica

# Paths
RESULTS_DIR = "analysis_results"
ENRICHMENT_CSV = "data/metadata_enrichment.csv"
PTOF_MD_DIR = "ptof_md"

# Import SchoolDatabase for authoritative data
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.utils.school_database import SchoolDatabase
    SCHOOL_DB = SchoolDatabase()
except Exception as e:
    print(f"⚠️ Warning: Could not load SchoolDatabase: {e}")
    SCHOOL_DB = None

def extract_canonical_code(filename_code):
    """Extract standard school code from prefixed filename."""
    match = re.search(r'([A-Z]{2,4}[A-Z0-9]{5,8}[A-Z0-9])', filename_code.upper())
    return match.group(1) if match else filename_code

def load_metadata_caches():
    """Load metadata from CSV sources."""
    caches = {'enrichment': {}}
    
    # Enrichment (official registry)
    if os.path.exists(ENRICHMENT_CSV):
        try:
            df = pd.read_csv(ENRICHMENT_CSV, dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('school_id', '')).strip()
                if code:
                    caches['enrichment'][code] = row.to_dict()
            print(f"✓ Loaded {len(caches['enrichment'])} records from enrichment CSV")
        except Exception as e:
            print(f"✗ Failed to load enrichment: {e}")
    
    return caches

def is_missing_field(field, value):
    if value is None:
        return True
    raw = str(value).strip()
    if not raw:
        return True
    if raw.lower() in ['nd', 'n/d', 'n/a', 'null', 'none', 'nan']:
        return True
    if field == 'tipo_scuola' and raw.lower() == 'istituto superiore':
        return True
    return False

def infer_school_level_from_text(text):
    if not text:
        return {}
    sample = text[:20000].lower()
    
    types = []
    grades = []
    
    if 'infanzia' in sample or 'materna' in sample:
        types.append('Infanzia')
        grades.append('Infanzia')
        
    if 'primaria' in sample or 'elementare' in sample or 'direzione didattica' in sample:
        types.append('Primaria')
        grades.append('Primaria')
        
    if re.search(r'(scuola\s+media|secondaria\s+di\s+primo|\bi\s*grado\b|\b1\W*grado\b)', sample):
        types.append('I Grado')
        grades.append('I Grado')
        
    if re.search(r'liceo', sample):
        types.append('Liceo')
        grades.append('II Grado')
        
    if re.search(r'(istituto\s+tecnico|\btecnico\b|itis|itc|itg)', sample):
        types.append('Tecnico')
        grades.append('II Grado')
        
    if re.search(r'(istituto\s+professionale|\bprofessionale\b|ipsia|ipc)', sample):
        types.append('Professionale')
        grades.append('II Grado')
        
    if 'comprensivo' in sample:
        if 'Infanzia' not in types: types.append('Infanzia')
        if 'Primaria' not in types: types.append('Primaria')
        if 'I Grado' not in types: types.append('I Grado')
        
        if 'Infanzia' not in grades: grades.append('Infanzia')
        if 'Primaria' not in grades: grades.append('Primaria')
        if 'I Grado' not in grades: grades.append('I Grado')
        if 'Comprensivo' not in grades: grades.append('Comprensivo')

    result = {}
    if types:
        result['tipo_scuola'] = ', '.join(sorted(list(set(types))))
    if grades:
        result['ordine_grado'] = ', '.join(sorted(list(set(grades))))
        
    return result


def find_md_path(school_code):
    candidates = [
        os.path.join(PTOF_MD_DIR, f"{school_code}_ptof.md"),
        os.path.join(PTOF_MD_DIR, f"{school_code}_PTOF.md"),
        os.path.join(PTOF_MD_DIR, f"{school_code}.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def infer_school_level_from_md(md_path):
    if not md_path or not os.path.exists(md_path):
        return {}
    try:
        with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
            return infer_school_level_from_text(f.read())
    except Exception:
        return {}

def enrich_json_file(json_path, caches):
    """Enrich a single JSON file with metadata from SchoolDatabase and enrichment CSV."""
    filename = os.path.basename(json_path)
    school_code_raw = filename.replace('_analysis.json', '')
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        # Get enrichment data from legacy CSV (fallback)
        enrich = caches['enrichment'].get(school_code, {})
        
        # Get authoritative data from SchoolDatabase (SCUANAGRAFESTAT/PAR)
        db_data = SCHOOL_DB.get_school_data(school_code) if SCHOOL_DB else {}
        
        # Helper function: priority is existing (LLM) > SchoolDB > enrichment CSV
        def get_value(field, db_field=None):
            db_field = db_field or field
            existing = data['metadata'].get(field)
            if existing and not is_missing_field(field, existing):
                return existing
            db_val = db_data.get(db_field) if db_data else None
            if db_val and not is_missing_field(field, db_val):
                return db_val
            enrich_val = enrich.get(field)
            if enrich_val and not is_missing_field(field, enrich_val):
                return enrich_val
            return 'ND'
        
        # Update metadata with all available fields
        data['metadata']['school_id'] = school_code
        data['metadata']['denominazione'] = get_value('denominazione')
        data['metadata']['comune'] = get_value('comune')
        data['metadata']['provincia'] = get_value('provincia')
        data['metadata']['regione'] = get_value('regione')
        raw_area = get_value('area_geografica')
        data['metadata']['area_geografica'] = normalize_area_geografica(
            raw_area,
            regione=data['metadata'].get('regione'),
            provincia_sigla=school_code[:2]
        )
        data['metadata']['ordine_grado'] = get_value('ordine_grado')
        data['metadata']['tipo_scuola'] = get_value('tipo_scuola')
        if str(data['metadata'].get('tipo_scuola', '')).strip().lower() == 'istituto superiore':
            data['metadata']['tipo_scuola'] = 'ND'
        data['metadata']['indirizzo'] = get_value('indirizzo')
        data['metadata']['cap'] = get_value('cap')
        data['metadata']['email'] = get_value('email')
        data['metadata']['pec'] = get_value('pec')
        data['metadata']['website'] = get_value('website')
        data['metadata']['statale_paritaria'] = get_value('statale_paritaria')
        
        # Territory mapping based on area_geografica
        area = data['metadata'].get('area_geografica', '').upper()
        territorio_map = {
            'NORD OVEST': 'Nord',
            'NORD EST': 'Nord',
            'NORD': 'Nord',
            'CENTRO': 'Centro',
            'SUD': 'Sud',
            'ISOLE': 'Sud',
        }
        data['metadata']['territorio'] = territorio_map.get(area, get_value('territorio'))

        md_path = find_md_path(school_code)
        md_inferred = infer_school_level_from_md(md_path)
        if is_missing_field('ordine_grado', data['metadata'].get('ordine_grado')) and md_inferred.get('ordine_grado'):
            data['metadata']['ordine_grado'] = md_inferred['ordine_grado']
        if is_missing_field('tipo_scuola', data['metadata'].get('tipo_scuola')) and md_inferred.get('tipo_scuola'):
            data['metadata']['tipo_scuola'] = md_inferred['tipo_scuola']

        ordine = data['metadata'].get('ordine_grado', '')
        tipo_scuola = data['metadata'].get('tipo_scuola', '')
        if ordine in ['Infanzia', 'Primaria'] and (not tipo_scuola or tipo_scuola == 'ND'):
            data['metadata']['tipo_scuola'] = ordine
        if ordine == 'I Grado' and (tipo_scuola == 'ND' or not tipo_scuola):
            data['metadata']['tipo_scuola'] = 'I Grado'
        if tipo_scuola in ['Liceo', 'Tecnico', 'Professionale'] and (not ordine or ordine == 'ND'):
            data['metadata']['ordine_grado'] = 'II Grado'
        if ordine == 'II Grado' and (not tipo_scuola or tipo_scuola == 'ND'):
            data['metadata']['tipo_scuola'] = 'II Grado'

        # Infer Ordine Grado from Denominazione if currently ND or generic
        current_grado = data['metadata']['ordine_grado']
        if current_grado in ['ND', '', None]:
            denom_lower = data['metadata']['denominazione'].lower()
            if 'infanzia' in denom_lower:
                data['metadata']['ordine_grado'] = 'Infanzia'
            elif 'primaria' in denom_lower or 'direzione didattica' in denom_lower or ' d.d.' in denom_lower:
                data['metadata']['ordine_grado'] = 'Primaria'
        
        # For I Grado schools, replace ND tipo_scuola with "I Grado"
        ordine = data['metadata'].get('ordine_grado', '')
        tipo_scuola = data['metadata'].get('tipo_scuola', 'ND')
        if ordine == 'I Grado' and (tipo_scuola == 'ND' or not tipo_scuola):
            data['metadata']['tipo_scuola'] = 'I Grado'
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True, school_code
    except Exception as e:
        return False, f"{school_code}: {e}"

def main():
    print("=" * 50)
    print("JSON Metadata Enrichment Script")
    print("=" * 50)
    
    # Load caches
    caches = load_metadata_caches()
    
    # Find all JSON files
    json_files = glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
    print(f"\nFound {len(json_files)} JSON files to process")
    
    success_count = 0
    error_count = 0
    
    for json_path in json_files:
        success, result = enrich_json_file(json_path, caches)
        if success:
            print(f"✓ Enriched: {result}")
            success_count += 1
        else:
            print(f"✗ Failed: {result}")
            error_count += 1
    
    print(f"\n{'=' * 50}")
    print(f"Completed: {success_count} enriched, {error_count} errors")
    print("=" * 50)

if __name__ == "__main__":
    main()
