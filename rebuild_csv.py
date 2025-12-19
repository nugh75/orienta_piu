#!/usr/bin/env python3
"""
Rebuild analysis_summary.csv from existing JSON files with corrected partnership/activity counts
"""
import os
import glob
import json
import csv
import pandas as pd

RESULTS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'
INVALSI_DIR = 'data/liste invalsi'

# Load metadata
metadata_cache = {}
if os.path.exists(METADATA_FILE):
    df_meta = pd.read_csv(METADATA_FILE, sep=';', on_bad_lines='skip')
    df_meta.columns = [c.strip().lower() for c in df_meta.columns]
    for _, row in df_meta.iterrows():
        code = str(row.get('istituto', '')).strip()
        if code:
            metadata_cache[code] = row.to_dict()

# Load INVALSI
invalsi_cache = {}
if os.path.exists(INVALSI_DIR):
    csv_files = glob.glob(os.path.join(INVALSI_DIR, "*.csv"))
    if csv_files:
        dfs = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f, sep=';', on_bad_lines='skip', dtype=str))
            except: pass
        if dfs:
            df_invalsi = pd.concat(dfs, ignore_index=True)
            df_invalsi.columns = [c.strip().lower() for c in df_invalsi.columns]
            if 'istituto' in df_invalsi.columns and 'strato' in df_invalsi.columns:
                for _, row in df_invalsi.iterrows():
                    code = str(row['istituto']).strip()
                    strato = str(row['strato']).lower()
                    territorio = 'ND'
                    if 'metro' in strato:
                        territorio = 'Metropolitano'
                    elif 'altro' in strato:
                        territorio = 'Non Metropolitano'
                    invalsi_cache[code] = {'territorio': territorio}

CSV_COLUMNS = [
    'school_id', 'denominazione', 'comune', 'area_geografica', 'tipo_scuola', 'territorio',
    'extraction_status', 'duration_sec', 'analysis_file',
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

# Process all JSON files
json_files = glob.glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
print(f"Found {len(json_files)} JSON files to process")

rows = []
for json_file in json_files:
    school_code = os.path.basename(json_file).replace('_analysis.json', '')
    
    try:
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        
        meta = metadata_cache.get(school_code, {})
        inv_data = invalsi_cache.get(school_code, {})
        
        summary_data = {col: '' for col in CSV_COLUMNS}
        summary_data['school_id'] = school_code
        summary_data['denominazione'] = meta.get('denominazionescuola', 'ND')
        summary_data['comune'] = meta.get('comune', 'ND')
        summary_data['area_geografica'] = inv_data.get('area_geografica', 'ND')
        summary_data['tipo_scuola'] = inv_data.get('tipo_scuola', 'ND')
        summary_data['territorio'] = inv_data.get('territorio', 'ND')
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
with open(SUMMARY_FILE, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✅ Rebuilt {SUMMARY_FILE} with {len(rows)} schools")
