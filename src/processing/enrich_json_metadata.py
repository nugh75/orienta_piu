#!/usr/bin/env python3
"""
Standalone script to enrich JSON analysis files with metadata from CSV sources.
Run independently from the main pipeline.
"""
import os
import json
import re
import pandas as pd
from glob import glob

# Paths
RESULTS_DIR = "analysis_results"
ENRICHMENT_CSV = "data/metadata_enrichment.csv"
INVALSI_CSV = "data/invalsi_unified.csv"

def extract_canonical_code(filename_code):
    """Extract standard school code from prefixed filename."""
    match = re.search(r'([A-Z]{2,4}[A-Z0-9]{5,8}[A-Z0-9])', filename_code.upper())
    return match.group(1) if match else filename_code

def load_metadata_caches():
    """Load metadata from CSV sources."""
    caches = {'enrichment': {}, 'invalsi': {}}
    
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
    
    # INVALSI
    if os.path.exists(INVALSI_CSV):
        try:
            df = pd.read_csv(INVALSI_CSV, sep=';', dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('istituto', '')).strip()
                if code:
                    caches['invalsi'][code] = row.to_dict()
            print(f"✓ Loaded {len(caches['invalsi'])} records from INVALSI CSV")
        except Exception as e:
            print(f"✗ Failed to load INVALSI: {e}")
    
    return caches

def enrich_json_file(json_path, caches):
    """Enrich a single JSON file with metadata."""
    filename = os.path.basename(json_path)
    school_code_raw = filename.replace('_analysis.json', '')
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        enrich = caches['enrichment'].get(school_code, {})
        invalsi = caches['invalsi'].get(school_code, {})
        
        # Update metadata with priority: enrichment > invalsi > existing
        data['metadata']['school_id'] = school_code
        data['metadata']['denominazione'] = enrich.get('denominazione') or invalsi.get('denominazionescuola') or data['metadata'].get('denominazione', 'ND')
        data['metadata']['comune'] = enrich.get('comune') or invalsi.get('nome_comune') or data['metadata'].get('comune', 'ND')
        data['metadata']['area_geografica'] = enrich.get('area_geografica') or data['metadata'].get('area_geografica', 'ND')
        data['metadata']['ordine_grado'] = enrich.get('ordine_grado') or invalsi.get('grado') or data['metadata'].get('ordine_grado', 'ND')
        data['metadata']['territorio'] = invalsi.get('territorio_std') or data['metadata'].get('territorio', 'ND')
        
        # Get tipo_scuola from sources
        tipo_scuola = invalsi.get('tipo_scuola_std') or data['metadata'].get('tipo_scuola', 'ND')
        
        # For I Grado schools, replace ND with "I Grado" (no subtypes exist)
        ordine = data['metadata'].get('ordine_grado', '')
        if ordine == 'I Grado' and (tipo_scuola == 'ND' or not tipo_scuola):
            data['metadata']['tipo_scuola'] = 'I Grado'
        else:
            data['metadata']['tipo_scuola'] = tipo_scuola
        
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
