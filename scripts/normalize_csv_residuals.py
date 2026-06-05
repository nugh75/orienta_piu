#!/usr/bin/env python3
"""
Script di normalizzazione residuale per analysis_summary.csv.
Applica regole di pulizia (nomi regione, doppi apici) a TUTTI i record,
indipendentemente dal match con MIUR.
"""

import sys
import os
import csv
import shutil
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.constants import normalize_regione

CSV_PATH = os.path.join(PROJECT_ROOT, "data/analysis_summary.csv")

def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ File non trovato: {CSV_PATH}")
        sys.exit(1)

    print(f"📂 Analisi {CSV_PATH}...")
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated_count = 0
    updates = {
        'regione': 0,
        'denominazione': 0
    }

    new_rows = []
    for row in rows:
        changed = False

        # 1. Normalizza regione
        old_reg = row.get('regione', '')
        new_reg = normalize_regione(old_reg)
        if old_reg != new_reg:
            row['regione'] = new_reg
            updates['regione'] += 1
            changed = True

        # 2. Strip doppi apici da denominazione
        old_den = row.get('denominazione', '')
        if old_den and '"' in old_den:
            # Rimuove solo se wrapping o doppi
            clean = old_den.strip().strip('"')
            if clean != old_den:
                row['denominazione'] = clean
                updates['denominazione'] += 1
                changed = True
        
        if changed:
            updated_count += 1
        
        new_rows.append(row)

    if updated_count > 0:
        # Backup
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(CSV_PATH, f"{CSV_PATH}.bak.resid.{ts}")
        
        # Write
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(new_rows)
        
        print(f"✅ Aggiornati {updated_count} record.")
        print(f"   - Regioni normalizzate: {updates['regione']}")
        print(f"   - Denominazioni pulite: {updates['denominazione']}")
    else:
        print("✨ Nessuna modifica necessaria.")

if __name__ == "__main__":
    main()
