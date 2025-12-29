#!/usr/bin/env python3
"""
Rebuild analysis_summary.csv from existing JSON files with corrected partnership/activity counts
"""
import os
import glob
import json
import csv
import pandas as pd
import sys
from pathlib import Path
import io

# Fix imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Add root
sys.path.append(os.path.dirname(__file__)) # Add current dir

from src.utils.file_utils import atomic_write
from src.utils.constants import normalize_area_geografica, get_territorio

# Now imports should work if analyze_ptofs is in root
try:
    from analyze_ptofs import get_score, get_has_sezione, PTOF_DIR
except ImportError:
    # Fallback if analyze_ptofs is gone/moved
    PTOF_DIR = 'ptof'
    def get_score(*args): return 0
    def get_has_sezione(*args): return 0
from extract_pdf_metadata import extract_metadata_from_pdf

RESULTS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'

# Load metadata
metadata_cache = {}
if os.path.exists(METADATA_FILE):
    df_meta = pd.read_csv(METADATA_FILE, sep=';', on_bad_lines='skip')
    df_meta.columns = [c.strip().lower() for c in df_meta.columns]
    for _, row in df_meta.iterrows():
        code = str(row.get('istituto', '')).strip()
        if code:
            metadata_cache[code] = row.to_dict()

# Load ENRICHMENT (Official Registry)
enrichment_cache = {}
ENRICHMENT_FILE = 'data/metadata_enrichment.csv'
if os.path.exists(ENRICHMENT_FILE):
    try:
        df_enr = pd.read_csv(ENRICHMENT_FILE, dtype=str)
        # school_id,ordine_grado,area_geografica,comune,denominazione
        for _, row in df_enr.iterrows():
            code = str(row.get('school_id', '')).strip()
            if code:
                enrichment_cache[code] = row.to_dict()
        print(f"Loaded enrichment metadata for {len(enrichment_cache)} schools")
    except Exception as e:
        print(f"Error loading enrichment: {e}")

CSV_COLUMNS = [
    'school_id', 'denominazione', 'comune', 'provincia', 'regione', 'area_geografica', 
    'tipo_scuola', 'territorio', 'ordine_grado', 'indirizzo', 'cap', 'email', 'pec', 'website',
    'statale_paritaria', 'extraction_status', 'duration_sec', 'analysis_file',

    'has_sezione_dedicata', '2_1_score',
    '2_3_finalita_attitudini_score', '2_3_finalita_interessi_score', '2_3_finalita_progetto_vita_score',
    '2_3_finalita_transizioni_formative_score', '2_3_finalita_capacita_orientative_opportunita_score',
    '2_4_obiettivo_ridurre_abbandono_score', '2_4_obiettivo_continuita_territorio_score',
    '2_4_obiettivo_contrastare_neet_score', '2_4_obiettivo_lifelong_learning_score',
    '2_5_azione_coordinamento_servizi_score', '2_5_azione_dialogo_docenti_studenti_score',
    '2_5_azione_rapporto_scuola_genitori_score', '2_5_azione_monitoraggio_azioni_score',
    '2_5_azione_sistema_integrato_inclusione_fragilita_score',
    '2_6_didattica_da_esperienza_studenti_score', '2_6_didattica_laboratoriale_score',
    '2_6_didattica_flessibilita_spazi_tempi_score', '2_6_didattica_interdisciplinare_score',
    '2_7_opzionali_culturali_score', '2_7_opzionali_laboratoriali_espressive_score',
    '2_7_opzionali_ludiche_ricreative_score', '2_7_opzionali_volontariato_score',
    '2_7_opzionali_sportive_score',
    'mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
    'partnership_count', 'activities_count', 'ptof_orientamento_maturity_index'
]

def calc_avg(scores):
    valid = [s for s in scores if s > 0]
    return sum(valid) / len(valid) if valid else 0

import re
def extract_canonical_code(filename_code):
    """
    Extract the canonical school code (e.g., MIIS08900V) from filename.
    Handles prefixes like RHO_, CAGLIARI_, etc.
    """
    # Match standard Italian school codes: 2-4 letters + 5-7 alphanumerics + 1 letter
    match = re.search(r'([A-Z]{2,4}[A-Z0-9]{5,8}[A-Z0-9])', filename_code.upper())
    if match:
        return match.group(1)
    # Fallback: return as-is
    return filename_code

# Process all JSON files (deduplicate by school code)
json_files = glob.glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
print(f"Found {len(json_files)} JSON files to process")


def candidate_rank(path: str) -> tuple:
    file_path = Path(path)
    is_ptof = path.endswith('_PTOF_analysis.json')
    size = file_path.stat().st_size if file_path.exists() else 0
    mtime = file_path.stat().st_mtime if file_path.exists() else 0
    return (1 if is_ptof else 0, size, mtime)


candidates_by_code = {}
for json_file in json_files:
    school_code_raw = os.path.basename(json_file).replace('_analysis.json', '')
    school_code = extract_canonical_code(school_code_raw)
    candidates_by_code.setdefault(school_code, []).append(json_file)

selected_entries = []
skipped_duplicates = 0
for school_code, candidates in candidates_by_code.items():
    sorted_candidates = sorted(candidates, key=candidate_rank, reverse=True)
    chosen_path = None
    json_data = None
    for path in sorted_candidates:
        try:
            with open(path, 'r') as f:
                json_data = json.load(f)
            chosen_path = path
            break
        except Exception:
            continue
    if not chosen_path:
        print(f"✗ {school_code}: no valid JSON among {len(sorted_candidates)} files")
        continue
    if len(sorted_candidates) > 1:
        skipped_duplicates += len(sorted_candidates) - 1
    selected_entries.append((school_code, chosen_path, json_data))

print(f"Selected {len(selected_entries)} unique schools (skipped {skipped_duplicates} duplicates)")

rows = []
for school_code, json_file, json_data in selected_entries:
    try:
        
        meta = metadata_cache.get(school_code, {})
        enrich_data = enrichment_cache.get(school_code, {})
        json_meta = json_data.get('metadata', {})
        
        summary_data = {col: '' for col in CSV_COLUMNS}
        summary_data['school_id'] = school_code
        
        # Denominazione: JSON (LLM) > Enrichment > PDF > Meta > 'ND'
        denominazione = json_meta.get('denominazione') or enrich_data.get('denominazione')
        if not denominazione or denominazione == 'ND':
             # Try PDF
             pdf_path = os.path.join(PTOF_DIR, f"{school_code}.pdf")
             pdf_meta = extract_metadata_from_pdf(pdf_path) if os.path.exists(pdf_path) else {}
             denominazione = pdf_meta.get('denominazione') or meta.get('denominazionescuola') or 'ND'
        summary_data['denominazione'] = denominazione
        
        # Comune: JSON (LLM) > Enrichment > PDF > Meta > 'ND'
        comune = json_meta.get('comune') or enrich_data.get('comune')
        if not comune or comune == 'ND':
             # Try PDF (re-use if extracted)
             if 'pdf_meta' not in locals():
                 pdf_path = os.path.join(PTOF_DIR, f"{school_code}.pdf")
                 pdf_meta = extract_metadata_from_pdf(pdf_path) if os.path.exists(pdf_path) else {}
             comune = pdf_meta.get('comune') or meta.get('comune') or 'ND'
        summary_data['comune'] = comune
        
        # Area: JSON (LLM) > Enrichment > Normalized
        raw_area = json_meta.get('area_geografica') or enrich_data.get('area_geografica')
        area_norm = normalize_area_geografica(
            raw_area,
            regione=json_meta.get('regione') or enrich_data.get('regione'),
            provincia_sigla=school_code[:2]
        )
        summary_data['area_geografica'] = area_norm if area_norm != 'ND' else 'ND'
        
        # Nuovi campi da anagrafi ufficiali
        summary_data['provincia'] = json_meta.get('provincia') or enrich_data.get('provincia') or 'ND'
        summary_data['regione'] = json_meta.get('regione') or enrich_data.get('regione') or 'ND'
        summary_data['indirizzo'] = json_meta.get('indirizzo') or enrich_data.get('indirizzo') or 'ND'
        summary_data['cap'] = json_meta.get('cap') or enrich_data.get('cap') or 'ND'
        summary_data['email'] = json_meta.get('email') or enrich_data.get('email') or 'ND'
        summary_data['pec'] = json_meta.get('pec') or enrich_data.get('pec') or 'ND'
        summary_data['website'] = json_meta.get('website') or enrich_data.get('website') or 'ND'
        summary_data['statale_paritaria'] = json_meta.get('statale_paritaria') or enrich_data.get('statale_paritaria') or 'ND'
        
        # Tipo: JSON (LLM) > 'ND'
        # Allow multi-values if comma present
        tipo_scuola = json_meta.get('tipo_scuola', 'ND')
        
        # Territorio: calcolato dalla provincia (Metropolitano/Non Metropolitano)
        provincia = json_meta.get('provincia') or enrich_data.get('provincia') or 'ND'
        summary_data['territorio'] = get_territorio(provincia)
        
        # Grado: Enrichment > JSON (LLM) Inferred
        # We need to be careful: if JSON has "I Grado, II Grado" (richer info), we might want to prefer it over "Comprensivo" or single value in enrichment.
        # Strategy: If JSON has comma, use JSON. Else check Enrichment.
        
        json_grado = json_meta.get('ordine_grado', 'ND')
        if ',' in str(json_grado):
             summary_data['ordine_grado'] = json_grado
        elif enrich_data.get('ordine_grado') and enrich_data['ordine_grado'] != 'ND':
            summary_data['ordine_grado'] = enrich_data['ordine_grado']
        elif json_grado and json_grado != 'ND':
            summary_data['ordine_grado'] = json_grado
        else:
             # Fallback to JSON logic (normalized) - only if not found above
            raw_grado = json_data.get('metadata', {}).get('ordine_grado', 'ND').replace('_', ' ')
            if 'II' in raw_grado.upper() and 'GRADO' in raw_grado.upper():
                summary_data['ordine_grado'] = 'II Grado'
            elif 'I' in raw_grado.upper() and 'GRADO' in raw_grado.upper() and 'II' not in raw_grado.upper():
                summary_data['ordine_grado'] = 'I Grado'
            elif 'INFANZIA' in raw_grado.upper():
                summary_data['ordine_grado'] = 'Infanzia'
            else:
                if raw_grado.upper() in ['ND', '']:
                    summary_data['ordine_grado'] = 'ND'
                else:
                    summary_data['ordine_grado'] = raw_grado.title()


        # For I Grado schools, if tipo_scuola is ND, set it to I Grado
        # Careful not to overwrite if we have specific types
        ordine = summary_data.get('ordine_grado', '')
        if ordine == 'I Grado' and (tipo_scuola == 'ND' or not tipo_scuola):
            summary_data['tipo_scuola'] = 'I Grado'
        else:
            summary_data['tipo_scuola'] = tipo_scuola

        summary_data['extraction_status'] = 'ok'
        summary_data['duration_sec'] = 0
        summary_data['analysis_file'] = json_file
        
        # Extract scores
        sec2 = json_data.get('ptof_section2', {})
        
        # Sezione dedicata
        sez_ded = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
        summary_data['has_sezione_dedicata'] = sez_ded.get('has_sezione_dedicata', 0)
        summary_data['2_1_score'] = sez_ded.get('score', 0)
        
        # Finalità
        fin = sec2.get('2_3_finalita', {})
        summary_data['2_3_finalita_attitudini_score'] = fin.get('finalita_attitudini', {}).get('score', 0)
        summary_data['2_3_finalita_interessi_score'] = fin.get('finalita_interessi', {}).get('score', 0)
        summary_data['2_3_finalita_progetto_vita_score'] = fin.get('finalita_progetto_vita', {}).get('score', 0)
        summary_data['2_3_finalita_transizioni_formative_score'] = fin.get('finalita_transizioni_formative', {}).get('score', 0)
        summary_data['2_3_finalita_capacita_orientative_opportunita_score'] = fin.get('finalita_capacita_orientative_opportunita', {}).get('score', 0)
        
        # Obiettivi
        obi = sec2.get('2_4_obiettivi', {})
        summary_data['2_4_obiettivo_ridurre_abbandono_score'] = obi.get('obiettivo_ridurre_abbandono', {}).get('score', 0)
        summary_data['2_4_obiettivo_continuita_territorio_score'] = obi.get('obiettivo_continuita_territorio', {}).get('score', 0)
        summary_data['2_4_obiettivo_contrastare_neet_score'] = obi.get('obiettivo_contrastare_neet', {}).get('score', 0)
        summary_data['2_4_obiettivo_lifelong_learning_score'] = obi.get('obiettivo_lifelong_learning', {}).get('score', 0)
        
        # Governance
        gov = sec2.get('2_5_azioni_sistema', {})
        summary_data['2_5_azione_coordinamento_servizi_score'] = gov.get('azione_coordinamento_servizi', {}).get('score', 0)
        summary_data['2_5_azione_dialogo_docenti_studenti_score'] = gov.get('azione_dialogo_docenti_studenti', {}).get('score', 0)
        summary_data['2_5_azione_rapporto_scuola_genitori_score'] = gov.get('azione_rapporto_scuola_genitori', {}).get('score', 0)
        summary_data['2_5_azione_monitoraggio_azioni_score'] = gov.get('azione_monitoraggio_azioni', {}).get('score', 0)
        summary_data['2_5_azione_sistema_integrato_inclusione_fragilita_score'] = gov.get('azione_sistema_integrato_inclusione_fragilita', {}).get('score', 0)
        
        # Didattica
        did = sec2.get('2_6_didattica_orientativa', {})
        summary_data['2_6_didattica_da_esperienza_studenti_score'] = did.get('didattica_da_esperienza_studenti', {}).get('score', 0)
        summary_data['2_6_didattica_laboratoriale_score'] = did.get('didattica_laboratoriale', {}).get('score', 0)
        summary_data['2_6_didattica_flessibilita_spazi_tempi_score'] = did.get('didattica_flessibilita_spazi_tempi', {}).get('score', 0)
        summary_data['2_6_didattica_interdisciplinare_score'] = did.get('didattica_interdisciplinare', {}).get('score', 0)
        
        # Opportunità
        opp = sec2.get('2_7_opzionali_facoltative', {})
        summary_data['2_7_opzionali_culturali_score'] = opp.get('opzionali_culturali', {}).get('score', 0)
        summary_data['2_7_opzionali_laboratoriali_espressive_score'] = opp.get('opzionali_laboratoriali_espressive', {}).get('score', 0)
        summary_data['2_7_opzionali_ludiche_ricreative_score'] = opp.get('opzionali_ludiche_ricreative', {}).get('score', 0)
        summary_data['2_7_opzionali_volontariato_score'] = opp.get('opzionali_volontariato', {}).get('score', 0)
        summary_data['2_7_opzionali_sportive_score'] = opp.get('opzionali_sportive', {}).get('score', 0)
        
        # Calculate means
        finalita_scores = [
            summary_data['2_3_finalita_attitudini_score'],
            summary_data['2_3_finalita_interessi_score'],
            summary_data['2_3_finalita_progetto_vita_score'],
            summary_data['2_3_finalita_transizioni_formative_score'],
            summary_data['2_3_finalita_capacita_orientative_opportunita_score']
        ]
        obiettivi_scores = [
            summary_data['2_4_obiettivo_ridurre_abbandono_score'],
            summary_data['2_4_obiettivo_continuita_territorio_score'],
            summary_data['2_4_obiettivo_contrastare_neet_score'],
            summary_data['2_4_obiettivo_lifelong_learning_score']
        ]
        governance_scores = [
            summary_data['2_5_azione_coordinamento_servizi_score'],
            summary_data['2_5_azione_dialogo_docenti_studenti_score'],
            summary_data['2_5_azione_rapporto_scuola_genitori_score'],
            summary_data['2_5_azione_monitoraggio_azioni_score'],
            summary_data['2_5_azione_sistema_integrato_inclusione_fragilita_score']
        ]
        didattica_scores = [
            summary_data['2_6_didattica_da_esperienza_studenti_score'],
            summary_data['2_6_didattica_laboratoriale_score'],
            summary_data['2_6_didattica_flessibilita_spazi_tempi_score'],
            summary_data['2_6_didattica_interdisciplinare_score']
        ]
        opportunita_scores = [
            summary_data['2_7_opzionali_culturali_score'],
            summary_data['2_7_opzionali_laboratoriali_espressive_score'],
            summary_data['2_7_opzionali_ludiche_ricreative_score'],
            summary_data['2_7_opzionali_volontariato_score'],
            summary_data['2_7_opzionali_sportive_score']
        ]
        
        mean_finalita = calc_avg(finalita_scores)
        mean_obiettivi = calc_avg(obiettivi_scores)
        mean_governance = calc_avg(governance_scores)
        mean_didattica = calc_avg(didattica_scores)
        mean_opportunita = calc_avg(opportunita_scores)
        
        summary_data['mean_finalita'] = round(mean_finalita, 2)
        summary_data['mean_obiettivi'] = round(mean_obiettivi, 2)
        summary_data['mean_governance'] = round(mean_governance, 2)
        summary_data['mean_didattica_orientativa'] = round(mean_didattica, 2)
        summary_data['mean_opportunita'] = round(mean_opportunita, 2)
        
        # Robustness index
        all_means = [mean_finalita, mean_obiettivi, mean_governance, mean_didattica, mean_opportunita]
        robustness_index = calc_avg(all_means)
        summary_data['ptof_orientamento_maturity_index'] = round(robustness_index, 2)
        
        # CORRECTED: Calculate from actual data
        partnership_data = sec2.get('2_2_partnership', {})
        partner_nominati = partnership_data.get('partner_nominati', [])
        summary_data['partnership_count'] = len(partner_nominati) if isinstance(partner_nominati, list) else 0
        
        activities_register = json_data.get('activities_register', [])
        summary_data['activities_count'] = len(activities_register) if isinstance(activities_register, list) else 0
        
        rows.append(summary_data)
        print(f"✓ {school_code}: {summary_data['partnership_count']} partners, {summary_data['activities_count']} activities")
        
    except Exception as e:
        print(f"✗ {school_code}: {e}")

# Write CSV
output = io.StringIO()
writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
writer.writeheader()
writer.writerows(rows)
atomic_write(SUMMARY_FILE, output.getvalue())

print(f"\n✅ Rebuilt {SUMMARY_FILE} with {len(rows)} schools")
