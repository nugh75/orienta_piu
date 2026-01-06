#!/usr/bin/env python3
"""
Esegue l'analisi PTOF basandosi sulle istruzioni (Prompt) definite in istruzioni/analisi_ptof_prompts.md.
Processa specificamente i file MD validi che sono rimasti 'pendenti' (senza JSON).

Logica:
1. Scansiona ptof_md/ per trovare file senza corrispondente in analysis_results/
2. Filtra quelli validi (size > 1KB)
3. Istanzia la pipeline agentica (Analyst, Reviewer, Refiner, Synthesizer)
4. Esegue l'analisi per ogni file
5. Salva JSON e MD
6. Aggiorna il CSV finale
"""

import sys
import os
import glob
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.agentic_pipeline import (
    AnalystAgent, RefinerAgent, ReviewerAgent, SynthesizerAgent,
    process_single_ptof
)
# from src.processing.rebuild_csv_clean import rebuild_csv (Run as subprocess)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MD_DIR = BASE_DIR / "ptof_md"
ANALYSIS_DIR = BASE_DIR / "analysis_results"

def get_pending_files():
    """Identifica i file MD che non hanno un'analisi JSON completata."""
    all_md = glob.glob(str(MD_DIR / "*_ptof.md"))
    pending = []
    
    for md_path in all_md:
        filename = os.path.basename(md_path)
        school_code = filename.split('_')[0]
        
        # Check if JSON exists
        json_path = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json"
        
        if not json_path.exists():
            # Check validity (filters out empty files)
            if os.path.getsize(md_path) > 1024: # > 1KB
                pending.append((school_code, md_path))
                
    return sorted(pending)

import subprocess

def main():
    print("="*60)
    print(" ESECUZIONE ISTRUZIONI DI ANALISI SU FILE PENDENTI")
    print("="*60)
    
    # 1. Trova file target
    targets = get_pending_files()
    print(f"File markdown pendenti e validi: {len(targets)}")
    
    if not targets:
        print("Nessun file da processare.")
        return

    # 2. Inizializza Agenti
    print("\nInizializzazione Agenti (come da istruzioni)...")
    try:
        analyst = AnalystAgent()
        reviewer = ReviewerAgent()
        refiner = RefinerAgent()
        synthesizer = SynthesizerAgent()
        print("✅ Agenti attivi.")
    except Exception as e:
        print(f"❌ Errore inizializzazione agenti: {e}")
        print("Assicurati che Ollama sia in esecuzione o le API key siano settate.")
        return

    # 3. Processa
    processed_count = 0
    errors = 0
    
    for i, (code, md_path) in enumerate(targets):
        print(f"\n[{i+1}/{len(targets)}] Analisi istruzione per: {code}")
        print(f"   File: {os.path.basename(md_path)}")
        
        try:
            # Esegue la procedura definita nel workflow (process_single_ptof)
            # che internamente usa i Prompt descritti nel file MD
            result = process_single_ptof(
                str(md_path),
                analyst,
                reviewer,
                refiner,
                synthesizer,
                str(ANALYSIS_DIR),
                status_callback=lambda msg: print(f"   > {msg}")
            )
            
            if result:
                print(f"   ✅ Analisi completata e salvata.")
                processed_count += 1
            else:
                print(f"   ⚠️ Analisi fallita (nessun risultato prodotto).")
                errors += 1
                
        except KeyboardInterrupt:
            print("\n🛑 Interruzione manuale.")
            break
        except Exception as e:
            print(f"   ❌ Errore durante l'esecuzione: {e}")
            errors += 1

    # 4. Rigenera CSV
    if processed_count > 0:
        print("\nAggiornamento indice CSV...")
        try:
            subprocess.run([sys.executable, "src/processing/rebuild_csv_clean.py"], cwd=str(BASE_DIR), check=False)
        except Exception as e:
            print(f"⚠️ Errore aggiornamento CSV: {e}")

    print("\n" + "="*60)
    print(f"FINE ESECUZIONE. Processati: {processed_count}, Errori: {errors}")
    print("="*60)

if __name__ == "__main__":
    main()
