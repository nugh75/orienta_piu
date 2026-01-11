#!/usr/bin/env python3
"""
Theme Backfill - Inferisce temi mancanti usando LLM

Questo script:
1. Legge attivita.csv
2. Per righe con ambiti_attivita vuoto, chiede al LLM di inferire un tema
3. Aggiorna il CSV con i temi inferiti

Uso: python -m src.processing.theme_backfill [--dry-run] [--limit N]
"""

import argparse
import csv
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://192.168.129.14:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:32b")
MAX_RETRIES = 3

# Lista temi validi (da fornire al LLM per consistenza)
VALID_THEMES = [
    "Orientamento",
    "Cittadinanza e Legalità",
    "Valutazione e Autovalutazione",
    "PCTO/Alternanza",
    "Inclusione e BES",
    "STEM e Ricerca",
    "Digitalizzazione",
    "Lingue Straniere",
    "Continuità e Accoglienza",
    "Sostenibilità e Ambiente",
    "Imprenditorialità",
    "Intercultura e Lingue",
    "Rapporti con Famiglie",
    "Arte e Creatività",
    "Prevenzione Disagio",
    "Formazione Docenti",
    "Matematica e Logica",
    "Sport e Benessere",
    "Lettura e Scrittura",
    "Geografia",
    "Storia",
    "Filosofia",
    "Comunicazione",
    "Salute e Benessere",
    "Tecnologia",
]


def call_ollama(prompt: str, model: str, ollama_url: str) -> Optional[str]:
    """Chiama Ollama API."""
    url = f"{ollama_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096
        }
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                logger.error(f"❌ Errore Ollama {response.status_code}: {response.text}")
                time.sleep(2)
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout (attempt {attempt+1}/{MAX_RETRIES})")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Eccezione Ollama: {e}")
            time.sleep(2)
            
    return None


def build_theme_prompt(titolo: str, descrizione: str, categoria: str) -> str:
    """Costruisce il prompt per inferire il tema."""
    themes_list = "\n".join(f"- {t}" for t in VALID_THEMES)
    
    return f"""Analizza questa attività scolastica e assegna UN SOLO tema dalla lista fornita.

ATTIVITÀ:
- Titolo: {titolo}
- Descrizione: {descrizione[:500] if descrizione else 'Non disponibile'}
- Categoria: {categoria}

TEMI VALIDI (scegli SOLO da questa lista):
{themes_list}

Rispondi con UNA SOLA PAROLA o frase che corrisponde esattamente a uno dei temi nella lista.
Non aggiungere spiegazioni, solo il tema.

Tema:"""


def infer_theme(row: dict, model: str, ollama_url: str) -> Optional[str]:
    """Inferisce il tema per una riga del CSV."""
    titolo = row.get("titolo", "")
    descrizione = row.get("descrizione", "")
    categoria = row.get("categoria", "")
    
    if not titolo:
        return None
    
    prompt = build_theme_prompt(titolo, descrizione, categoria)
    response = call_ollama(prompt, model, ollama_url)
    
    if not response:
        return None
    
    # Pulisci la risposta
    theme = response.strip().strip('"').strip("'").strip()
    
    # Verifica che sia un tema valido
    theme_lower = theme.lower()
    for valid_theme in VALID_THEMES:
        if valid_theme.lower() == theme_lower or valid_theme.lower() in theme_lower:
            return valid_theme
    
    # Se non trova corrispondenza esatta, cerca parziale
    for valid_theme in VALID_THEMES:
        if any(word.lower() in theme_lower for word in valid_theme.split()):
            return valid_theme
    
    logger.warning(f"⚠️ Tema non riconosciuto: '{theme}' per '{titolo[:50]}...'")
    return theme  # Ritorna comunque il tema inferito


def main():
    parser = argparse.ArgumentParser(description="Backfill temi mancanti in attivita.csv")
    parser.add_argument("--dry-run", action="store_true", help="Non modifica il CSV, solo mostra cosa farebbe")
    parser.add_argument("--limit", type=int, default=0, help="Limita il numero di righe da processare")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Modello Ollama")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL, help="URL Ollama")
    args = parser.parse_args()
    
    # Percorsi
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "attivita.csv"
    backup_path = base_dir / "data" / f"attivita.csv.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
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
    
    # Trova righe senza tema
    rows_to_update = []
    for i, row in enumerate(rows):
        ambiti = row.get("ambiti_attivita", "").strip()
        if not ambiti:
            rows_to_update.append((i, row))
    
    logger.info(f"🔍 {len(rows_to_update)} righe senza ambiti_attivita")
    
    if not rows_to_update:
        logger.info("✅ Nessuna riga da aggiornare")
        return
    
    if args.limit > 0:
        rows_to_update = rows_to_update[:args.limit]
        logger.info(f"⚙️ Limitato a {len(rows_to_update)} righe")
    
    if args.dry_run:
        logger.info("🔎 DRY RUN - Nessuna modifica verrà applicata")
    
    # Processa righe
    updated_count = 0
    for idx, (row_idx, row) in enumerate(rows_to_update):
        titolo = row.get("titolo", "")[:60]
        logger.info(f"[{idx+1}/{len(rows_to_update)}] Processando: {titolo}...")
        
        theme = infer_theme(row, args.model, args.ollama_url)
        
        if theme:
            logger.info(f"   → Tema inferito: {theme}")
            if not args.dry_run:
                rows[row_idx]["ambiti_attivita"] = theme
            updated_count += 1
        else:
            logger.warning(f"   → Impossibile inferire tema")
        
        time.sleep(0.5)  # Rate limiting leggero
    
    logger.info(f"\n📈 {updated_count}/{len(rows_to_update)} temi inferiti")
    
    if args.dry_run:
        logger.info("🔎 DRY RUN completato - Nessun file modificato")
        return
    
    # Backup
    logger.info(f"💾 Backup: {backup_path}")
    shutil.copy2(csv_path, backup_path)
    
    # Scrivi CSV aggiornato
    logger.info(f"✍️ Scrittura {csv_path}")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"✅ Completato! {updated_count} temi aggiunti")


if __name__ == "__main__":
    main()
