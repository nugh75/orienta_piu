#!/usr/bin/env python3
"""
Slow Reviewer - Revisione PTOF con modelli OpenRouter Free
Strategia:
- Usa modelli potenti ma gratuiti (es. gemini-2.0-flash-exp:free)
- Attesa lunga tra le chiamate per evitare rate limit
- Backoff esponenziale in caso di errore
- Persistenza dello stato per riprendere l'esecuzione
"""

import os
import sys
import json
import time
import logging
import argparse
import shutil
import random
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.file_utils import atomic_write

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/slow_review.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurazione
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ANALYSIS_DIR = BASE_DIR / "analysis_results"
MD_DIR = BASE_DIR / "ptof_md"
BACKUP_DIR = ANALYSIS_DIR / "pre_review_backup"
STATUS_FILE = BASE_DIR / "data" / "review_status.json"
API_CONFIG_FILE = BASE_DIR / "data" / "api_config.json"

# Default settings
DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_WAIT = 120  # secondi
MAX_RETRIES = 3

def load_api_config() -> Dict:
    """Carica la configurazione API"""
    if API_CONFIG_FILE.exists():
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Errore caricamento config API: {e}")
    return {}

def get_openrouter_key() -> Optional[str]:
    # Prima prova da .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            return key
    except ImportError:
        logger.warning("python-dotenv non installato, impossibile leggere .env")

    # Fallback su api_config.json se esiste
    config = load_api_config()
    return config.get("openrouter_api_key")

def save_status(status: Dict):
    """Salva lo stato delle revisioni"""
    try:
        atomic_write(STATUS_FILE, json.dumps(status, indent=2))
    except Exception as e:
        logger.error(f"Errore salvataggio stato: {e}")

def load_status() -> Dict:
    """Carica lo stato delle revisioni"""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Errore caricamento stato: {e}")
    return {"reviewed": [], "failed": []}

def call_openrouter(prompt: str, model: str, api_key: str) -> Optional[str]:
    """Chiama OpenRouter con gestione errori e backoff"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/nugh75/LIste",
        "X-Title": "PTOF Analysis Reviewer",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            
            elif response.status_code == 429:
                wait_time = 300 * (attempt + 1)  # 5, 10, 15 minuti
                logger.warning(f"⚠️ Rate limit (429). Attesa {wait_time}s...")
                time.sleep(wait_time)
            
            else:
                # Gestione errore Privacy/Data Policy
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message", "")
                    if "data policy" in err_msg:
                        logger.error(f"❌ ERRORE PRIVACY OPENROUTER: {err_msg}")
                        logger.error("   SOLUZIONE: Vai su https://openrouter.ai/settings/privacy")
                        logger.error("   1. DISATTIVA 'ZDR Endpoints Only'")
                        logger.error("   2. ATTIVA 'Enable free endpoints that may train on inputs'")
                        logger.error("   3. ATTIVA 'Enable free endpoints that may publish prompts'")
                        return None # Inutile riprovare
                except:
                    pass

                logger.error(f"❌ Errore API {response.status_code}: {response.text}")
                time.sleep(10)
                
        except Exception as e:
            logger.error(f"❌ Eccezione chiamata API: {e}")
            time.sleep(10)
            
    return None

def build_enrichment_prompt(source_ptof: str, current_report: str) -> str:
    """Costruisce il prompt per l'arricchimento del report"""
    # Riduco a 300k caratteri per stare dentro i 128k token di Llama 3.3 (circa 85k token)
    truncated_ptof = source_ptof[:300000]
    
    return f"""
SEI UN EDITOR SCOLASTICO ESPERTO E METICOLOSO.
Il tuo compito è ARRICCHIRE il report di analisi esistente (Markdown) integrando dettagli specifici estratti dal documento originale (PTOF), SENZA stravolgere la struttura del report.

DOCUMENTO ORIGINALE (PTOF - Fonte di Verità):
{truncated_ptof} ... [Il testo continua]

REPORT ATTUALE (Bozza da arricchire):
{current_report}

ISTRUZIONI OPERATIVE:
1. CONFRONTA il Report Attuale con il PTOF originale.
2. IDENTIFICA informazioni di valore presenti nel PTOF ma mancanti nel Report, come:
   - Nomi specifici di progetti (es. "Progetto Accoglienza", "Erasmus+").
   - Dati quantitativi (es. budget specifici, numero di ore, percentuali).
   - Metodologie didattiche particolari citate.
   - Collaborazioni con enti specifici o partner territoriali.
3. INTEGRA queste informazioni nel Report, inserendole organicamente nelle sezioni esistenti.
   - USA TASSATIVAMENTE UNO STILE NARRATIVO E DISCORSIVO.
   - EVITA elenchi puntati o numerati se non strettamente necessario; preferisci la prosa.
   - Le nuove informazioni devono fluire naturalmente nel testo esistente, arricchendolo di dettagli.
4. NON CANCELLARE le sezioni esistenti. Mantieni i titoli e la struttura.
5. NON INVENTARE nulla. Usa solo informazioni presenti nel PTOF.
6. Se il report è troppo generico, rendilo più specifico citando il testo originale.
7. CONTROLLO SEZIONE ORIENTAMENTO: Se nel PTOF originale NON esiste un capitolo dedicato all'Orientamento, NON inventarlo e NON scrivere che esiste nella sezione "2.1 Sezione Dedicata". Sii onesto sulla sua assenza.

IMPORTANTE - STRUTTURA OBBLIGATORIA DA PRESERVARE:
Il report finale DEVE contenere ESATTAMENTE questi titoli (non tradurli, non cambiarli):
# Analisi del PTOF [CODICE]
## Report di Valutazione dell'Orientamento
### 1. Sintesi Generale
### 2. Analisi Dimensionale
#### 2.1 Sezione Dedicata all'Orientamento
#### 2.2 Partnership e Reti
#### 2.3 Finalità e Obiettivi
#### 2.4 Governance e Azioni di Sistema
#### 2.5 Didattica Orientativa
#### 2.6 Opportunità Formative
#### 2.7 Registro Dettagliato delle Attività
### 3. Punti di Forza
### 4. Aree di Debolezza
### 5. Gap Analysis
### 6. Conclusioni

OUTPUT RICHIESTO:
Restituisci INTERAMENTE il nuovo contenuto Markdown del report arricchito.
Non includere commenti introduttivi o conclusivi (es. "Ecco il report..."), solo il contenuto del file.
"""

def main():
    parser = argparse.ArgumentParser(description="Slow Reviewer per PTOF")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modello OpenRouter da usare")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="Secondi di attesa tra chiamate")
    parser.add_argument("--limit", type=int, default=100, help="Limite file da processare")
    parser.add_argument("--target", help="Codice scuola specifico da processare (ignora status)")
    args = parser.parse_args()
    
    api_key = get_openrouter_key()
    if not api_key:
        logger.error("❌ API Key OpenRouter non trovata in .env o data/api_config.json")
        return

    logger.info(f"🚀 Avvio Slow Enrichment con modello: {args.model}")
    logger.info(f"⏱️ Attesa base: {args.wait}s")
    
    # Setup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Load status
    status = load_status()
    reviewed_set = set(status['reviewed'])
    
    # Find candidates (cerchiamo i file MD del report)
    report_files = list(ANALYSIS_DIR.glob("*_PTOF_analysis.md"))
    candidates = []
    
    for rf in report_files:
        school_code = rf.stem.split('_')[0]
        
        # Se c'è un target, processa solo quello ignorando lo status
        if args.target:
            if school_code == args.target:
                source_md_file = MD_DIR / f"{school_code}_ptof.md"
                if source_md_file.exists():
                    candidates.append((school_code, rf, source_md_file))
                break
            continue

        if school_code in reviewed_set:
            continue
            
        source_md_file = MD_DIR / f"{school_code}_ptof.md"
        if not source_md_file.exists():
            continue
            
        candidates.append((school_code, rf, source_md_file))
    
    logger.info(f"📋 Trovati {len(candidates)} report da arricchire")
    
    count = 0
    for school_code, report_path, source_path in candidates:
        if count >= args.limit:
            break
            
        logger.info(f"\n✨ Arricchimento {school_code} ({count+1}/{min(len(candidates), args.limit)})")
        
        try:
            # Backup handled by atomic_write now
            # shutil.copy2(report_path, BACKUP_DIR / report_path.name)
            
            # Read files
            with open(report_path, 'r') as f:
                current_report = f.read()
            
            with open(source_path, 'r') as f:
                source_content = f.read()
            
            # Call API
            prompt = build_enrichment_prompt(source_content, current_report)
            result_str = call_openrouter(prompt, args.model, api_key)
            
            if result_str:
                # Clean markdown code blocks if present
                if result_str.startswith("```markdown"):
                    result_str = result_str.replace("```markdown", "", 1)
                if result_str.startswith("```"):
                    result_str = result_str.replace("```", "", 1)
                if result_str.endswith("```"):
                    result_str = result_str[:-3]
                
                result_str = result_str.strip()
                
                # Save enriched report with backup
                atomic_write(report_path, result_str, backup=True)
                
                logger.info(f"✅ {school_code}: Report arricchito e salvato")
                status['reviewed'].append(school_code)
                save_status(status)
                count += 1
            else:
                logger.error(f"❌ {school_code}: Nessuna risposta dall'API")
                status['failed'].append(school_code)
                
        except Exception as e:
            logger.error(f"❌ {school_code}: Errore generico: {e}")
            status['failed'].append(school_code)
        
        # Wait with jitter
        jitter = random.randint(-15, 15)
        wait_time = max(30, args.wait + jitter)
        logger.info(f"💤 Dormo per {wait_time}s...")
        time.sleep(wait_time)

    logger.info("🏁 Sessione completata")

if __name__ == "__main__":
    main()
