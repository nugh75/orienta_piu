#!/usr/bin/env python3
"""
Normalize Themes - Normalizza i temi in attivita.csv usando config centrale

Uso: python -m src.processing.normalize_themes [--dry-run]
"""

import argparse
import csv
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Normalizza temi in attivita.csv")
    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa farebbe senza modificare")
    args = parser.parse_args()
    
    # Importa qui per evitare circular imports
    from src.config.themes import normalize_themes_string
    
    # Percorsi
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "attivita.csv"
    backup_path = base_dir / "data" / f"attivita.csv.bak.normalize.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if not csv_path.exists():
        logger.error(f"❌ File non trovato: {csv_path}")
        sys.exit(1)
    
    logger.info(f"📂 Lettura {csv_path}")
    
    # Leggi CSV
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    logger.info(f"📊 {len(rows)} righe totali")
    
    # Conta temi prima
    themes_before = {}
    for row in rows:
        ambiti = row.get("ambiti_attivita", "").strip()
        if ambiti:
            for t in ambiti.split("|"):
                t = t.strip()
                themes_before[t] = themes_before.get(t, 0) + 1
    
    logger.info(f"🔍 Temi unici prima: {len(themes_before)}")
    
    # Normalizza
    changes = 0
    for row in rows:
        ambiti = row.get("ambiti_attivita", "").strip()
        if ambiti:
            normalized = normalize_themes_string(ambiti, "|")
            if normalized != ambiti:
                if args.dry_run and changes < 10:
                    logger.info(f"   '{ambiti[:60]}...' → '{normalized}'")
                row["ambiti_attivita"] = normalized
                changes += 1
    
    # Conta temi dopo
    themes_after = {}
    for row in rows:
        ambiti = row.get("ambiti_attivita", "").strip()
        if ambiti:
            for t in ambiti.split("|"):
                t = t.strip()
                themes_after[t] = themes_after.get(t, 0) + 1
    
    logger.info(f"✨ Temi unici dopo: {len(themes_after)}")
    logger.info(f"📝 {changes} righe modificate")
    
    if args.dry_run:
        logger.info("🔎 DRY RUN - Nessun file modificato")
        return
    
    if changes == 0:
        logger.info("✅ Nessuna modifica necessaria")
        return
    
    # Backup
    logger.info(f"💾 Backup: {backup_path}")
    shutil.copy2(csv_path, backup_path)
    
    # Scrivi CSV
    logger.info(f"✍️ Scrittura {csv_path}")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"✅ Normalizzazione completata! {changes} righe aggiornate")
    logger.info(f"   Temi prima: {len(themes_before)} → dopo: {len(themes_after)}")


if __name__ == "__main__":
    main()
