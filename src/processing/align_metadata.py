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
INVALSI_CSV = "data/invalsi_unified.csv"
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
    # Centro
    'MS': 'Centro', 'LU': 'Centro', 'PT': 'Centro', 'FI': 'Centro', 'LI': 'Centro', 'PI': 'Centro', 'AR': 'Centro', 'SI': 'Centro', 'GR': 'Centro', 'PO': 'Centro',  # Toscana
    'PG': 'Centro', 'TR': 'Centro',  # Umbria
    'PU': 'Centro', 'AN': 'Centro', 'MC': 'Centro', 'AP': 'Centro', 'FM': 'Centro',  # Marche
    'VT': 'Centro', 'RI': 'Centro', 'RM': 'Centro', 'LT': 'Centro', 'FR': 'Centro',  # Lazio
    # Sud
    'AQ': 'Sud', 'TE': 'Sud', 'PE': 'Sud', 'CH': 'Sud',  # Abruzzo
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
invalsi_cache = {}

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

# Load INVALSI CSV
if os.path.exists(INVALSI_CSV):
    try:
        df = pd.read_csv(INVALSI_CSV, sep=';', dtype=str)
        for _, row in df.iterrows():
            code = str(row.get('istituto', '')).strip()
            if code:
                invalsi_cache[code] = row.to_dict()
        print(f"✓ Loaded {len(invalsi_cache)} records from INVALSI CSV")
    except Exception as e:
        print(f"✗ Failed to load INVALSI: {e}")

# ============================================
# PHASE 2: Enrich JSON Files
# ============================================

print("\n📁 PHASE 2: Enriching JSON files...")

json_files = glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
print(f"Found {len(json_files)} JSON files")

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
        invalsi = invalsi_cache.get(school_code, {})
        
        # Update metadata
        data['metadata']['school_id'] = school_code
        data['metadata']['denominazione'] = enrich.get('denominazione') or invalsi.get('denominazionescuola') or data['metadata'].get('denominazione', 'ND')
        data['metadata']['comune'] = enrich.get('comune') or invalsi.get('nome_comune') or data['metadata'].get('comune', 'ND')
        
        # area_geografica: INVALSI > enrichment > infer from code (keep for area only)
        data['metadata']['area_geografica'] = invalsi.get('area_geografica') or enrich.get('area_geografica') or infer_area_from_code(school_code) or 'ND'
        
        # ordine_grado: enrichment > INVALSI
        ordine = enrich.get('ordine_grado') or invalsi.get('grado') or 'ND'
        data['metadata']['ordine_grado'] = ordine
        
        # territorio from INVALSI
        data['metadata']['territorio'] = invalsi.get('territorio_std') or 'ND'
        
        # tipo_scuola: INVALSI tipo_scuola_std > percorso2 > plesso (for IC)
        invalsi_tipo = invalsi.get('tipo_scuola_std')
        percorso = str(invalsi.get('percorso2', '') or '').strip()
        plesso = str(invalsi.get('plesso', '') or '').strip()
        
        # Check for IC indicator in percorso2 or plesso fields
        is_ic = percorso.upper() == 'IC' or plesso.upper() == 'IC'
        
        if invalsi_tipo and invalsi_tipo != 'ND':
            data['metadata']['tipo_scuola'] = invalsi_tipo
        elif is_ic:
            data['metadata']['tipo_scuola'] = 'I Grado'
        elif percorso:
            # Map percorso2 to tipo_scuola
            percorso_map = {
                'licei_trad': 'Liceo',
                'licei_altri': 'Liceo',
                'IT': 'Tecnico',
                'IP': 'Professionale',
            }
            data['metadata']['tipo_scuola'] = percorso_map.get(percorso, 'ND')
        else:
            data['metadata']['tipo_scuola'] = 'ND'
        
        # If ordine_grado is I Grado, tipo_scuola must also be I Grado
        if ordine == 'I Grado':
            data['metadata']['tipo_scuola'] = 'I Grado'
        
        # If tipo_scuola is I Grado, ordine_grado must also be I Grado
        if data['metadata']['tipo_scuola'] == 'I Grado':
            data['metadata']['ordine_grado'] = 'I Grado'
        
        # Derive ordine_grado from tipo_scuola if still ND (for II Grado)
        if data['metadata']['ordine_grado'] == 'ND':
            tipo = data['metadata']['tipo_scuola']
            if tipo in ['Liceo', 'Tecnico', 'Professionale']:
                data['metadata']['ordine_grado'] = 'II Grado'
        
        # Derive tipo_scuola from ordine_grado if tipo_scuola is still ND
        if data['metadata']['tipo_scuola'] == 'ND':
            ordine = data['metadata']['ordine_grado']
            if ordine == 'I Grado':
                data['metadata']['tipo_scuola'] = 'I Grado'
            elif ordine == 'II Grado':
                data['metadata']['tipo_scuola'] = 'II Grado'
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ {school_code}")
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
        invalsi = invalsi_cache.get(school_code, {})
        
        row = {col: '' for col in CSV_COLUMNS}
        row['school_id'] = school_code
        row['denominazione'] = meta.get('denominazione', 'ND')
        row['comune'] = meta.get('comune', 'ND')
        row['area_geografica'] = meta.get('area_geografica') or enrich.get('area_geografica') or infer_area_from_code(school_code) or 'ND'
        row['territorio'] = meta.get('territorio', 'ND')
        
        # ordine_grado: enrichment > meta (from JSON)
        ordine = enrich.get('ordine_grado') or meta.get('ordine_grado', 'ND')
        row['ordine_grado'] = ordine
        
        # tipo_scuola from meta, but if ordine_grado is I Grado, tipo_scuola must be I Grado
        row['tipo_scuola'] = meta.get('tipo_scuola', 'ND')
        if ordine == 'I Grado':
            row['tipo_scuola'] = 'I Grado'
        
        # If tipo_scuola is I Grado, ordine_grado must also be I Grado
        if row['tipo_scuola'] == 'I Grado':
            row['ordine_grado'] = 'I Grado'
        
        # Derive ordine_grado from tipo_scuola if ND
        if row['ordine_grado'] == 'ND' and row['tipo_scuola'] in ['Liceo', 'Tecnico', 'Professionale']:
            row['ordine_grado'] = 'II Grado'
        
        # Derive tipo_scuola from ordine_grado if tipo_scuola is still ND
        if row['tipo_scuola'] == 'ND':
            if row['ordine_grado'] == 'I Grado':
                row['tipo_scuola'] = 'I Grado'
            elif row['ordine_grado'] == 'II Grado':
                row['tipo_scuola'] = 'II Grado'
        
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
