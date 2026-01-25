#!/usr/bin/env python3
"""
Aggiorna reports/strata_failures.csv sincronizzandolo con data/download_state.json.
Uso: python scripts/update_failures_report.py
"""

import json
import csv
import logging
from pathlib import Path
from datetime import datetime

# Config
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
STATE_FILE = DATA_DIR / "download_state.json"
FAIL_REPORT = REPORTS_DIR / "strata_failures.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_failures_report():
    if not STATE_FILE.exists():
        logger.error(f"File stato non trovato: {STATE_FILE}")
        return

    logger.info(f"Leggendo stato da {STATE_FILE}...")
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        logger.error(f"Errore lettura JSON: {e}")
        return

    failed = state.get("failed", {})
    if not failed:
        logger.info("Nessun fallimento registrato nello stato.")
        # Se vogliamo svuotare il file report in caso di 0 fallimenti:
        # FAIL_REPORT.write_text("cycle_id,school_code,strato,reason,attempt,last_seen\n", encoding='utf-8')
        return

    logger.info(f"Trovati {len(failed)} fallimenti attivi.")

    # Prepara righe per CSV
    rows = []
    for code, info in failed.items():
        # Cerca di recuperare cycle_id se presente, altrimenti default
        cycle_id = info.get("last_cycle", "synced")
        
        row = {
            "cycle_id": str(cycle_id),
            "school_code": code,
            "strato": info.get("strato", "UNKNOWN"),
            "reason": info.get("reason", "Unknown"),
            "attempt": str(info.get("attempts", 1)),
            "last_seen": info.get("last_attempt", datetime.now().isoformat())
        }
        rows.append(row)

    # Ordina per last_seen decrescente
    rows.sort(key=lambda x: x["last_seen"], reverse=True)

    # Scrivi CSV
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cycle_id", "school_code", "strato", "reason", "attempt", "last_seen"]
    
    with open(FAIL_REPORT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"✅ Report aggiornato: {FAIL_REPORT} ({len(rows)} righe)")

if __name__ == "__main__":
    update_failures_report()
