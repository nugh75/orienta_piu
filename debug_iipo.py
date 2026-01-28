#!/usr/bin/env python3
import sys
import os
import json
import logging
import shutil
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Config logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_debug(pdf_path, school_code):
    print(f"🔍 DEBUG ANALISI IIPO: {pdf_path}")
    print(f"   Codice Scuola: {school_code}")
    print("-" * 50)
    
    # 1. Convert PDF to MD
    md_dir = BASE_DIR / "ptof_md"
    md_dir.mkdir(exist_ok=True)
    md_file = md_dir / f"{school_code}_ptof.md"
    
    print(f"📝 STEP 1: Conversione PDF -> MD")
    try:
        from src.processing.convert_pdfs_to_md import pdf_to_markdown
        if not pdf_to_markdown(str(pdf_path), str(md_file)):
            print("❌ Errore conversione PDF -> MD")
            return
        print(f"   ✅ MD creato: {md_file}")
    except Exception as e:
        print(f"❌ Errore import conversione: {e}")
        return

    # 2. Setup Analysis
    print(f"\n🤖 STEP 2: Analisi Multi-Agente")
    
    # Force threshold processing (even if low) by setting env var for this process
    os.environ["IIPO_MIN_THRESHOLD"] = "0.0" 
    
    try:
        from app.agentic_pipeline import (
            AnalystAgent, RefinerAgent, ReviewerAgent, SynthesizerAgent,
            process_single_ptof
        )
        
        analyst = AnalystAgent()
        refiner = RefinerAgent()
        reviewer = ReviewerAgent()
        synthesizer = SynthesizerAgent()
        
        analysis_dir = BASE_DIR / "analysis_results_debug"
        analysis_dir.mkdir(exist_ok=True)

        def status_cb(msg):
            print(f"   [STATUS] {msg}")

        result = process_single_ptof(
            str(md_file),
            analyst,
            reviewer,
            refiner,
            synthesizer,
            str(analysis_dir),
            status_callback=status_cb
        )
        
        if result:
            print("\n✅ RISULTATO ANALISI (Raw JSON):")
            # Calculate IIPO locally to show what it would be
            if result and isinstance(result, dict) and result.get('_not_ptof'):
                 print("   🚫 SKIP: Non è un PTOF")
            else:
                 # Helper to compute score (copied logic)
                 def compute_maturity_index(analysis_data):
                     sec2 = analysis_data.get('ptof_section2', {}) if analysis_data else {}
                     def get_score(section_key, field_key):
                         return sec2.get(section_key, {}).get(field_key, {}).get('score', 0) or 0
                     def calc_avg(scores):
                         valid = [s for s in scores if s > 0]
                         return sum(valid) / len(valid) if valid else 0
                     
                     finalita_scores = [
                        get_score('2_3_finalita', 'finalita_attitudini'),
                        get_score('2_3_finalita', 'finalita_interessi'),
                        get_score('2_3_finalita', 'finalita_progetto_vita'),
                        get_score('2_3_finalita', 'finalita_transizioni_formative'),
                        get_score('2_3_finalita', 'finalita_capacita_orientative_opportunita'),
                     ]
                     obiettivi_scores = [
                        get_score('2_4_obiettivi', 'obiettivo_ridurre_abbandono'),
                        get_score('2_4_obiettivi', 'obiettivo_continuita_territorio'),
                        get_score('2_4_obiettivi', 'obiettivo_contrastare_neet'),
                        get_score('2_4_obiettivi', 'obiettivo_lifelong_learning'),
                     ]
                     governance_scores = [
                        get_score('2_5_azioni_sistema', 'azione_coordinamento_servizi'),
                        get_score('2_5_azioni_sistema', 'azione_dialogo_docenti_studenti'),
                        get_score('2_5_azioni_sistema', 'azione_rapporto_scuola_genitori'),
                        get_score('2_5_azioni_sistema', 'azione_monitoraggio_azioni'),
                        get_score('2_5_azioni_sistema', 'azione_sistema_integrato_inclusione_fragilita'),
                     ]
                     didattica_scores = [
                        get_score('2_6_didattica_orientativa', 'didattica_da_esperienza_studenti'),
                        get_score('2_6_didattica_orientativa', 'didattica_laboratoriale'),
                        get_score('2_6_didattica_orientativa', 'didattica_flessibilita_spazi_tempi'),
                        get_score('2_6_didattica_orientativa', 'didattica_interdisciplinare'),
                     ]
                     opportunita_scores = [
                        get_score('2_7_opzionali_facoltative', 'opzionali_culturali'),
                        get_score('2_7_opzionali_facoltative', 'opzionali_laboratoriali_espressive'),
                        get_score('2_7_opzionali_facoltative', 'opzionali_ludiche_ricreative'),
                        get_score('2_7_opzionali_facoltative', 'opzionali_volontariato'),
                        get_score('2_7_opzionali_facoltative', 'opzionali_sportive'),
                     ]
                     mean_finalita = calc_avg(finalita_scores)
                     mean_obiettivi = calc_avg(obiettivi_scores)
                     mean_governance = calc_avg(governance_scores)
                     mean_didattica = calc_avg(didattica_scores)
                     mean_opportunita = calc_avg(opportunita_scores)
                     
                     s_strut = float(sec2.get('2_1_ptof_orientamento_sezione_dedicata', {}).get('score', 0) or 0)
                     s_part = float(sec2.get('2_2_partnership', {}).get('score', 0) or 0)

                     return calc_avg([s_strut, s_part, mean_finalita, mean_obiettivi, mean_governance, mean_didattica, mean_opportunita])

                 ro_index = compute_maturity_index(result)
                 print(f"   📊 IIPO Index Calcolato: {ro_index}")
            
            # Print scores
            print("\n📊 DETTAGLIO PUNTEGGI:")
            if 'ptof_section2' in result:
                for k, v in result['ptof_section2'].items():
                    print(f"   Sezione {k}:")
                    for subk, subv in v.items():
                        if isinstance(subv, dict) and 'score' in subv:
                            print(f"     - {subk}: {subv['score']} ({subv.get('reasoning', '')[:50]}...)")
                            
        else:
            print("\n❌ ANALISI FALLITA (Return None)")
            
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_iipo.py <pdf_path> <school_code>")
        sys.exit(1)
        
    run_debug(Path(sys.argv[1]), sys.argv[2])
