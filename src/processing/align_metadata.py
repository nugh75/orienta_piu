#!/usr/bin/env python3
"""
Unified Metadata Alignment Script
Aligns metadata across JSON analysis files, CSV summary, and Dashboard.

Usage:
    python src/processing/align_metadata.py
"""
import os
import json
import re
import csv
import pandas as pd
from glob import glob

# Paths
RESULTS_DIR = "analysis_results"
ENRICHMENT_CSV = "data/metadata_enrichment.csv"
SUMMARY_CSV = "data/analysis_summary.csv"
PTOF_DIR = "ptof"

print("=" * 60)
print("🔄 Unified Metadata Alignment Script")
print("=" * 60)

# ============================================
# PHASE 1: Load Metadata Caches
# ============================================

def extract_canonical_code(filename_code):
    """
    Extract standard school code from prefixed filename.
    Italian school codes follow pattern: 2 letters (province) + 2-3 chars (type) + 5-6 chars (number)
    Examples: MIIS08900V, CAIC86800V, RMPL355003, FGIC85400C, NAIC8C000R
    """
    # Remove _PTOF suffix and _analysis suffix first
    clean_code = re.sub(r'_?PTOF.*$|_analysis.*$', '', filename_code.upper())
    
    # Look for standard Italian school code pattern (10-11 chars)
    patterns = [
        r'([A-Z]{2}[A-Z]{2}[0-9]{5,6}[A-Z0-9])',  # Standard: MIIS08900V, CAIC86800V
        r'([A-Z]{2}[A-Z]{1}[A-Z0-9]{1}[0-9]{4,5}[A-Z0-9])',  # Mixed: NAIC8C000R, VTIC82500A
        r'([A-Z]{2}[A-Z]{2}[0-9]{4,5}[A-Z]{1,2})',  # Variant: RMPL355003
        r'([A-Z]{2}[0-9][A-Z][0-9]{5}[A-Z])',  # Special: NA1M03300T, BS1M004009
        r'([A-Z]{2}[A-Z0-9]{8,9})',  # Generic fallback: any 10-11 char code
    ]
    for pattern in patterns:
        match = re.search(pattern, clean_code)
        if match:
            return match.group(1)
    # Fallback: if underscore present, try to get longest part that looks like code
    parts = clean_code.split('_')
    for part in reversed(parts):  # Prefer last parts (usually the code)
        if len(part) >= 8 and re.match(r'^[A-Z]{2}', part):
            return part
    return parts[0] if parts else filename_code

# Italian region codes to area mapping
REGION_TO_AREA = {
    # Nord
    'TO': 'Nord', 'VC': 'Nord', 'NO': 'Nord', 'CN': 'Nord', 'AT': 'Nord', 'AL': 'Nord', 'BI': 'Nord', 'VB': 'Nord',  # Piemonte
    'AO': 'Nord',  # Valle d'Aosta
    'VA': 'Nord', 'CO': 'Nord', 'SO': 'Nord', 'MI': 'Nord', 'BG': 'Nord', 'BS': 'Nord', 'PV': 'Nord', 'CR': 'Nord', 'MN': 'Nord', 'LC': 'Nord', 'LO': 'Nord', 'MB': 'Nord',  # Lombardia
    'BZ': 'Nord', 'TN': 'Nord',  # Trentino
    'VR': 'Nord', 'VI': 'Nord', 'BL': 'Nord', 'TV': 'Nord', 'VE': 'Nord', 'PD': 'Nord', 'RO': 'Nord',  # Veneto
    'UD': 'Nord', 'GO': 'Nord', 'TS': 'Nord', 'PN': 'Nord',  # Friuli
    'IM': 'Nord', 'SV': 'Nord', 'GE': 'Nord', 'SP': 'Nord',  # Liguria
    'PC': 'Nord', 'PR': 'Nord', 'RE': 'Nord', 'MO': 'Nord', 'BO': 'Nord', 'FE': 'Nord', 'RA': 'Nord', 'FC': 'Nord', 'RN': 'Nord',  # Emilia-Romagna
    # Nord (include Toscana, Umbria, Marche, Abruzzo)
    'MS': 'Nord', 'LU': 'Nord', 'PT': 'Nord', 'FI': 'Nord', 'LI': 'Nord', 'PI': 'Nord', 'AR': 'Nord', 'SI': 'Nord', 'GR': 'Nord', 'PO': 'Nord',  # Toscana
    'PG': 'Nord', 'TR': 'Nord',  # Umbria
    'PU': 'Nord', 'AN': 'Nord', 'MC': 'Nord', 'AP': 'Nord', 'FM': 'Nord',  # Marche
    'AQ': 'Nord', 'TE': 'Nord', 'PE': 'Nord', 'CH': 'Nord',  # Abruzzo
    # Sud (solo Lazio e regioni meridionali)
    'VT': 'Sud', 'RI': 'Sud', 'RM': 'Sud', 'LT': 'Sud', 'FR': 'Sud',  # Lazio
    'CB': 'Sud', 'IS': 'Sud',  # Molise
    'CE': 'Sud', 'BN': 'Sud', 'NA': 'Sud', 'AV': 'Sud', 'SA': 'Sud',  # Campania
    'FG': 'Sud', 'BA': 'Sud', 'TA': 'Sud', 'BR': 'Sud', 'LE': 'Sud', 'BT': 'Sud',  # Puglia
    'PZ': 'Sud', 'MT': 'Sud',  # Basilicata
    'CS': 'Sud', 'CZ': 'Sud', 'RC': 'Sud', 'KR': 'Sud', 'VV': 'Sud',  # Calabria
    'TP': 'Sud', 'PA': 'Sud', 'ME': 'Sud', 'AG': 'Sud', 'CL': 'Sud', 'EN': 'Sud', 'CT': 'Sud', 'RG': 'Sud', 'SR': 'Sud',  # Sicilia
    'SS': 'Sud', 'NU': 'Sud', 'CA': 'Sud', 'OR': 'Sud', 'OT': 'Sud', 'OG': 'Sud', 'CI': 'Sud', 'VS': 'Sud', 'SU': 'Sud',  # Sardegna
}

def infer_area_from_code(school_code):
    """Infer area geografica from school code prefix."""
    if len(school_code) >= 2:
        prefix = school_code[:2].upper()
        return REGION_TO_AREA.get(prefix, 'ND')
    return 'ND'

def infer_school_type_from_code(school_code):
    """
    Infer ordine_grado and tipo_scuola from school code (positions 3-4).
    Returns (ordine_grado, tipo_scuola)
    """
    if len(school_code) < 4:
        return ('ND', 'ND')
    
    tipo_code = school_code[2:4].upper()
    
    # I Grado (scuole medie e comprensivi)
    if tipo_code in ['IC', 'MM', '1M']:
        return ('I Grado', 'I Grado')
    
    # II Grado - All secondary schools
    # Istituti Superiori generici
    if tipo_code == 'IS':
        return ('II Grado', 'Istituto Superiore')
    
    # II Grado - Professionali
    if tipo_code in ['RI', 'RF', 'RH', 'RA', 'RC', 'RB', 'IP', 'RP']:
        return ('II Grado', 'Professionale')
    
    # II Grado - Tecnici
    if tipo_code in ['TF', 'TL', 'TE', 'TD', 'TB', 'TA', 'TH', 'IT', 'TT']:
        return ('II Grado', 'Tecnico')
    
    # II Grado - Licei (use INVALSI for specific type)
    if tipo_code in ['PS', 'PC', 'PM', 'SL', 'SD', 'PL', 'LI']:
        return ('II Grado', 'ND')  # Licei info from INVALSI
    
    # Primaria
    if tipo_code in ['EE', 'DD']:
        return ('Primaria', 'Primaria')
    
    # Infanzia
    if tipo_code == 'AA':
        return ('Infanzia', 'Infanzia')
    
    return ('ND', 'ND')

enrichment_cache = {}

# Load Enrichment CSV
if os.path.exists(ENRICHMENT_CSV):
    try:
        df = pd.read_csv(ENRICHMENT_CSV, dtype=str)
        for _, row in df.iterrows():
            code = str(row.get('school_id', '')).strip()
            if code:
                enrichment_cache[code] = row.to_dict()
        print(f"✓ Loaded {len(enrichment_cache)} records from enrichment CSV")
    except Exception as e:
        print(f"✗ Failed to load enrichment: {e}")

# ============================================
# PHASE 1b: Load School Registry (Anagrafe)
# ============================================

ANAGRAFE_STAT = "data/SCUANAGRAFESTAT20252620250901.csv"
ANAGRAFE_PAR = "data/SCUANAGRAFEPAR20252620250901.csv"

anagrafe_cache = {}  # code -> {denominazione, comune, area, tipo, ...}
denom_to_code = {}   # denominazione (upper) -> code

def load_anagrafe():
    """Load school registry from MIUR files."""
    global anagrafe_cache, denom_to_code

    for csv_file in [ANAGRAFE_STAT, ANAGRAFE_PAR]:
        if not os.path.exists(csv_file):
            print(f"  ⚠️ File anagrafe non trovato: {csv_file}")
            continue
        try:
            df = pd.read_csv(csv_file, dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('CODICESCUOLA', '')).strip().upper()
                denom = str(row.get('DENOMINAZIONESCUOLA', '')).strip()
                if code:
                    anagrafe_cache[code] = {
                        'denominazione': denom,
                        'comune': row.get('DESCRIZIONECOMUNE', ''),
                        'area_geografica': 'Nord' if 'NORD' in str(row.get('AREAGEOGRAFICA', '')).upper() else 'Sud',
                        'regione': row.get('REGIONE', ''),
                        'provincia': row.get('PROVINCIA', ''),
                        'tipo_grado': row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', ''),
                    }
                    # Build reverse lookup by denomination
                    if denom:
                        denom_upper = denom.upper()
                        denom_to_code[denom_upper] = code
            print(f"  ✓ Caricato {csv_file}: {len(df)} righe")
        except Exception as e:
            print(f"  ✗ Errore caricamento {csv_file}: {e}")

    print(f"✓ Anagrafe totale: {len(anagrafe_cache)} scuole, {len(denom_to_code)} denominazioni")

print("\n📂 PHASE 1b: Loading School Registry (Anagrafe)...")
load_anagrafe()

def find_code_by_denomination(denom):
    """Try to find school code by denomination (fuzzy match)."""
    if not denom:
        return None
    denom_upper = denom.upper().strip()

    # Exact match
    if denom_upper in denom_to_code:
        return denom_to_code[denom_upper]

    # Partial match (denomination contains or is contained)
    for cached_denom, code in denom_to_code.items():
        if denom_upper in cached_denom or cached_denom in denom_upper:
            return code

    return None

def validate_school_code(code):
    """Check if code exists in anagrafe."""
    return code.upper() in anagrafe_cache

# ============================================
# PHASE 2: Deduplicate & Enrich JSON Files
# ============================================

print("\n📁 PHASE 2a: Validating school codes against Anagrafe...")

json_files = glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
print(f"Found {len(json_files)} JSON files (before validation)")

# Validate and fix mismatched codes
mismatched_files = []
for jf in json_files:
    fname = os.path.basename(jf).replace('_analysis.json', '').replace('_PTOF', '')
    code = extract_canonical_code(fname)

    if not validate_school_code(code):
        # Try to find correct code from JSON metadata denominazione
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
            denom = data.get('metadata', {}).get('denominazione', '')
            correct_code = find_code_by_denomination(denom)
            if correct_code:
                mismatched_files.append((jf, code, correct_code, denom))
            else:
                mismatched_files.append((jf, code, None, denom))
        except:
            mismatched_files.append((jf, code, None, ''))

if mismatched_files:
    print(f"\n⚠️ Trovati {len(mismatched_files)} file con codici non validi:")
    renamed_count = 0
    for jf, old_code, new_code, denom in mismatched_files:
        if new_code:
            print(f"  {old_code} -> {new_code} ({denom[:40]}...)")
            # Rename JSON file
            old_path = jf
            new_fname = os.path.basename(jf).replace(old_code, new_code)
            # Handle case where old_code might not be in filename directly
            if old_code not in os.path.basename(jf):
                new_fname = f"{new_code}_analysis.json"
            new_path = os.path.join(os.path.dirname(jf), new_fname)

            try:
                os.rename(old_path, new_path)
                renamed_count += 1

                # Also rename corresponding MD file if exists
                old_md = old_path.replace('.json', '.md')
                if os.path.exists(old_md):
                    new_md = new_path.replace('.json', '.md')
                    os.rename(old_md, new_md)

                # Update JSON metadata with correct code
                with open(new_path, 'r') as f:
                    data = json.load(f)
                data['metadata']['school_id'] = new_code
                # Also update from anagrafe
                if new_code in anagrafe_cache:
                    info = anagrafe_cache[new_code]
                    if not data['metadata'].get('denominazione') or data['metadata'].get('denominazione') == 'ND':
                        data['metadata']['denominazione'] = info['denominazione']
                    if not data['metadata'].get('comune') or data['metadata'].get('comune') == 'ND':
                        data['metadata']['comune'] = info['comune']
                    if not data['metadata'].get('area_geografica') or data['metadata'].get('area_geografica') == 'ND':
                        data['metadata']['area_geografica'] = info['area_geografica']
                with open(new_path, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"    ❌ Errore rinomina: {e}")
        else:
            print(f"  ❌ {old_code}: Nessun match trovato in anagrafe ({denom[:40] if denom else 'no denom'})")

    print(f"✅ Rinominati {renamed_count} file")

    # Refresh file list after renames
    json_files = glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
else:
    print("✅ Tutti i codici sono validi")

print("\n📁 PHASE 2b: Deduplicating JSON files...")

# --- DEDUPLICATION LOGIC ---
files_by_code = {}
for jf in json_files:
    fname = os.path.basename(jf)
    code = extract_canonical_code(fname.replace('_analysis.json', ''))
    if code not in files_by_code:
        files_by_code[code] = []
    files_by_code[code].append(jf)

duplicates_removed = 0
final_json_list = []

for code, files in files_by_code.items():
    if len(files) > 1:
        # Strategy: Prefer exact match "{CODE}_analysis.json"
        # If not, prefer shortest filename (likely cleaner) or most recent?
        # Let's go with: Exact match > Shortest Filename > Most Recent
        
        canonical_name = f"{code}_analysis.json"
        target_file = None
        
        # 1. Check for exact canonical name
        for f in files:
            if os.path.basename(f) == canonical_name:
                target_file = f
                break
        
        # 2. If not found, sort by length (ascending) then mtime (descending)
        if not target_file:
            # Sort: Length increases -> older mtime increases
            # We want shortest length. If tie, we probably want recent. 
            # Actually, standardizing on shortest name is safer for "clean" names.
            files.sort(key=lambda x: (len(os.path.basename(x)), -os.path.getmtime(x)))
            target_file = files[0]
            
        print(f"  ⚠️ Duplicate found for {code}:")
        for f in files:
            if f != target_file:
                print(f"     🗑️ Removing redundant: {os.path.basename(f)}")
                try:
                    os.remove(f)
                    duplicates_removed += 1
                except Exception as e:
                    print(f"     ❌ Error removing {os.path.basename(f)}: {e}")
        
        final_json_list.append(target_file)
    else:
        final_json_list.append(files[0])

if duplicates_removed > 0:
    print(f"🧹 Checked duplicates: Removed {duplicates_removed} files.")
    # Refresh list
    json_files = final_json_list
else:
    print("✅ No duplicates found.")

json_success = 0
json_errors = 0

for json_path in json_files:
    filename = os.path.basename(json_path)
    school_code_raw = filename.replace('_analysis.json', '')
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'metadata' not in data:
            data['metadata'] = {}
            
        enrich = enrichment_cache.get(school_code, {})
        # Invalsi source REMOVED as per request
        
        # --- SAFE UPDATE MECHANISM ---
        # Only update if current value is Missing or ND
        def safe_update(key, new_val):
            curr = str(data['metadata'].get(key, '')).strip()
            is_curr_valid = curr and curr.lower() not in ['nd', 'nan', 'none', '']
            
            # New value must be valid to overwrite even ND
            if new_val:
                new_str = str(new_val).strip()
                is_new_valid = new_str and new_str.lower() not in ['nd', 'nan', 'none', '']
                
                if not is_curr_valid and is_new_valid:
                    data['metadata'][key] = new_str
        
        # Always ensure ID is correct
        data['metadata']['school_id'] = school_code

        # Apply safe updates from Encryption ONLY (Manual/Legacy)
        safe_update('denominazione', enrich.get('denominazione'))
        safe_update('comune', enrich.get('comune'))
        
        # area_geografica
        possible_area = enrich.get('area_geografica') or infer_area_from_code(school_code)
        safe_update('area_geografica', possible_area)
        
        # ordine_grado
        possible_ordine = enrich.get('ordine_grado')
        safe_update('ordine_grado', possible_ordine)
        
        # Territorio (Invalsi removed, so rely on extraction/enrich)
        # No source for territorio currently other than what's in JSON
        
        # tipo_scuola 
        # Logic simplified: Rely on Enrich or Preserve. extraction will fill this later.
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        json_success += 1
    except Exception as e:
        print(f"  ✗ {school_code}: {e}")
        json_errors += 1

print(f"JSON: {json_success} enriched, {json_errors} errors")

# ============================================
# PHASE 3: Rebuild CSV for Dashboard
# ============================================

print("\n📊 PHASE 3: Rebuilding CSV...")

CSV_COLUMNS = [
    'school_id', 'denominazione', 'comune', 'area_geografica', 'tipo_scuola', 'territorio', 'ordine_grado',
    'extraction_status', 'duration_sec', 'analysis_file', 'has_sezione_dedicata',
    '2_1_score', '2_3_finalita_attitudini_score', '2_3_finalita_interessi_score',
    '2_3_finalita_progetto_vita_score', '2_3_finalita_transizioni_formative_score',
    '2_3_finalita_capacita_orientative_opportunita_score', '2_4_obiettivo_ridurre_abbandono_score',
    '2_4_obiettivo_continuita_territorio_score', '2_4_obiettivo_contrastare_neet_score',
    '2_4_obiettivo_lifelong_learning_score', '2_5_azione_coordinamento_servizi_score',
    '2_5_azione_dialogo_docenti_studenti_score', '2_5_azione_rapporto_scuola_genitori_score',
    '2_5_azione_monitoraggio_azioni_score', '2_5_azione_sistema_integrato_inclusione_fragilita_score',
    '2_6_didattica_da_esperienza_studenti_score', '2_6_didattica_laboratoriale_score',
    '2_6_didattica_flessibilita_spazi_tempi_score', '2_6_didattica_interdisciplinare_score',
    '2_7_opzionali_culturali_score', '2_7_opzionali_laboratoriali_espressive_score',
    '2_7_opzionali_ludiche_ricreative_score', '2_7_opzionali_volontariato_score',
    '2_7_opzionali_sportive_score', 'mean_finalita', 'mean_obiettivi', 'mean_governance',
    'mean_didattica_orientativa', 'mean_opportunita', 'partnership_count', 'activities_count',
    'ptof_orientamento_maturity_index'
]

def calc_avg(scores):
    valid = [s for s in scores if s > 0]
    return round(sum(valid) / len(valid), 2) if valid else 0

rows = []
for json_path in json_files:
    school_code_raw = os.path.basename(json_path).replace('_analysis.json', '')
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        meta = data.get('metadata', {})
        enrich = enrichment_cache.get(school_code, {})
        
        row = {col: '' for col in CSV_COLUMNS}
        row['school_id'] = school_code
        row['denominazione'] = meta.get('denominazione', 'ND')
        row['comune'] = meta.get('comune', 'ND')
        row['area_geografica'] = meta.get('area_geografica') or enrich.get('area_geografica') or infer_area_from_code(school_code) or 'ND'
        row['territorio'] = meta.get('territorio', 'ND')
        
        # ordine_grado: enrichment > meta (from JSON)
        ordine = enrich.get('ordine_grado') or meta.get('ordine_grado', 'ND')
        row['ordine_grado'] = ordine
        
        # tipo_scuola from meta
        row['tipo_scuola'] = meta.get('tipo_scuola', 'ND')
        
        # Logic to infer ND values, but respect existing ones
        if row['tipo_scuola'] == 'ND':
            if ordine == 'I Grado':
                row['tipo_scuola'] = 'I Grado'
            elif ordine == 'Comprensivo':
                row['tipo_scuola'] = 'Infanzia, Primaria, I Grado'
            elif ordine == 'II Grado':
                # Attempt to guess if still ND? Usually handled by manual input
                pass
        
        # Logic to infer ordine_grado if ND
        if row['ordine_grado'] == 'ND':
            if 'Liceo' in row['tipo_scuola'] or 'Tecnico' in row['tipo_scuola']:
                row['ordine_grado'] = 'II Grado'
            elif 'I Grado' in row['tipo_scuola'] and not 'Liceo' in row['tipo_scuola']:
                 # If only I Grado or mixed lower
                 row['ordine_grado'] = 'I Grado'
                 if 'Primaria' in row['tipo_scuola']:
                     row['ordine_grado'] = 'Comprensivo'
        
        row['extraction_status'] = 'ok'
        row['analysis_file'] = json_path
        
        # Scores - parse new nested JSON structure
        sec2 = data.get('ptof_section2', {})
        
        # 2.1 Sezione dedicata
        s21 = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
        row['has_sezione_dedicata'] = 1 if s21.get('has_sezione_dedicata') else 0
        row['2_1_score'] = s21.get('score', 0)
        
        # 2.3 Finalita
        finalita = sec2.get('2_3_finalita', {})
        row['2_3_finalita_attitudini_score'] = finalita.get('finalita_attitudini', {}).get('score', 0)
        row['2_3_finalita_interessi_score'] = finalita.get('finalita_interessi', {}).get('score', 0)
        row['2_3_finalita_progetto_vita_score'] = finalita.get('finalita_progetto_vita', {}).get('score', 0)
        row['2_3_finalita_transizioni_formative_score'] = finalita.get('finalita_transizioni_formative', {}).get('score', 0)
        row['2_3_finalita_capacita_orientative_opportunita_score'] = finalita.get('finalita_capacita_orientative_opportunita', {}).get('score', 0)
        
        # 2.4 Obiettivi
        obiettivi = sec2.get('2_4_obiettivi', {})
        row['2_4_obiettivo_ridurre_abbandono_score'] = obiettivi.get('obiettivo_ridurre_abbandono', {}).get('score', 0)
        row['2_4_obiettivo_continuita_territorio_score'] = obiettivi.get('obiettivo_continuita_territorio', {}).get('score', 0)
        row['2_4_obiettivo_contrastare_neet_score'] = obiettivi.get('obiettivo_contrastare_neet', {}).get('score', 0)
        row['2_4_obiettivo_lifelong_learning_score'] = obiettivi.get('obiettivo_lifelong_learning', {}).get('score', 0)
        
        # 2.5 Governance/Azioni sistema
        governance = sec2.get('2_5_azioni_sistema', {})
        row['2_5_azione_coordinamento_servizi_score'] = governance.get('azione_coordinamento_servizi', {}).get('score', 0)
        row['2_5_azione_dialogo_docenti_studenti_score'] = governance.get('azione_dialogo_docenti_studenti', {}).get('score', 0)
        row['2_5_azione_rapporto_scuola_genitori_score'] = governance.get('azione_rapporto_scuola_genitori', {}).get('score', 0)
        row['2_5_azione_monitoraggio_azioni_score'] = governance.get('azione_monitoraggio_azioni', {}).get('score', 0)
        row['2_5_azione_sistema_integrato_inclusione_fragilita_score'] = governance.get('azione_sistema_integrato_inclusione_fragilita', {}).get('score', 0)
        
        # 2.6 Didattica orientativa
        didattica = sec2.get('2_6_didattica_orientativa', {})
        row['2_6_didattica_da_esperienza_studenti_score'] = didattica.get('didattica_da_esperienza_studenti', {}).get('score', 0)
        row['2_6_didattica_laboratoriale_score'] = didattica.get('didattica_laboratoriale', {}).get('score', 0)
        row['2_6_didattica_flessibilita_spazi_tempi_score'] = didattica.get('didattica_flessibilita_spazi_tempi', {}).get('score', 0)
        row['2_6_didattica_interdisciplinare_score'] = didattica.get('didattica_interdisciplinare', {}).get('score', 0)
        
        # 2.7 Opportunita formative
        # 2.7 Opportunita formative (check both possible names)
        opportunita = sec2.get('2_7_opportunita_formative', {}) or sec2.get('2_7_opzionali_facoltative', {})
        row['2_7_opzionali_culturali_score'] = opportunita.get('opzionali_culturali', {}).get('score', 0)
        row['2_7_opzionali_laboratoriali_espressive_score'] = opportunita.get('opzionali_laboratoriali_espressive', {}).get('score', 0)
        row['2_7_opzionali_ludiche_ricreative_score'] = opportunita.get('opzionali_ludiche_ricreative', {}).get('score', 0)
        row['2_7_opzionali_volontariato_score'] = opportunita.get('opzionali_volontariato', {}).get('score', 0)
        row['2_7_opzionali_sportive_score'] = opportunita.get('opzionali_sportive', {}).get('score', 0)
        
        # Means
        row['mean_finalita'] = calc_avg([row[f'2_3_finalita_{k}_score'] for k in ['attitudini', 'interessi', 'progetto_vita', 'transizioni_formative', 'capacita_orientative_opportunita']])
        row['mean_obiettivi'] = calc_avg([row[f'2_4_obiettivo_{k}_score'] for k in ['ridurre_abbandono', 'continuita_territorio', 'contrastare_neet', 'lifelong_learning']])
        row['mean_governance'] = calc_avg([row[f'2_5_azione_{k}_score'] for k in ['coordinamento_servizi', 'dialogo_docenti_studenti', 'rapporto_scuola_genitori', 'monitoraggio_azioni', 'sistema_integrato_inclusione_fragilita']])
        row['mean_didattica_orientativa'] = calc_avg([row[f'2_6_didattica_{k}_score'] for k in ['da_esperienza_studenti', 'laboratoriale', 'flessibilita_spazi_tempi', 'interdisciplinare']])
        row['mean_opportunita'] = calc_avg([row[f'2_7_opzionali_{k}_score'] for k in ['culturali', 'laboratoriali_espressive', 'ludiche_ricreative', 'volontariato', 'sportive']])
        
        # Counts - from new JSON structure
        partnership = sec2.get('2_2_partnership', {})
        row['partnership_count'] = partnership.get('partnership_count', 0)
        activities = sec2.get('2_8_attivita', {})
        row['activities_count'] = activities.get('activities_count', 0) if isinstance(activities, dict) else 0
        
        # Maturity Index
        all_means = [row['mean_finalita'], row['mean_obiettivi'], row['mean_governance'], row['mean_didattica_orientativa'], row['mean_opportunita']]
        row['ptof_orientamento_maturity_index'] = calc_avg([m for m in all_means if m > 0])
        
        rows.append(row)
        print(f"  ✓ {school_code}")
    except Exception as e:
        print(f"  ✗ {school_code}: {e}")

# Write CSV
with open(SUMMARY_CSV, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✅ Rebuilt {SUMMARY_CSV} with {len(rows)} schools")

# ============================================
# SUMMARY
# ============================================

print("\n" + "=" * 60)
print("✅ ALIGNMENT COMPLETE")
print(f"   - JSON files enriched: {json_success}")
print(f"   - CSV rows generated: {len(rows)}")
print("   - Dashboard ready at: http://localhost:8501")
print("=" * 60)
