#!/usr/bin/env python3
"""
Gemini Reviewer - Revisione PTOF con modelli Google Gemini
Strategia:
- Usa modelli Google ufficiali (es. gemini-1.5-pro)
- Gestione rate limit specifica per Google AI Studio
- Backoff esponenziale
- Persistenza dello stato
"""

import os
import sys
import json
import time
import signal
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

# Import registry
try:
    from utils.analysis_registry import register_review
except ImportError:
    from src.utils.analysis_registry import register_review

# Flag per uscita controllata
EXIT_REQUESTED = False

def graceful_exit_handler(signum, frame):
    """Handler per uscita controllata con Ctrl+C."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED:
        print("\n\n⚠️ Uscita forzata.", flush=True)
        sys.exit(1)
    EXIT_REQUESTED = True
    print("\n\n🛑 USCITA RICHIESTA - Completamento file corrente...", flush=True)
    print("   (Premi Ctrl+C di nuovo per uscita forzata)", flush=True)

# Registra handler
signal.signal(signal.SIGINT, graceful_exit_handler)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/gemini_review.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurazione
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ANALYSIS_DIR = BASE_DIR / "analysis_results"
MD_DIR = BASE_DIR / "ptof_md"
STATUS_FILE = BASE_DIR / "data" / "review_status_gemini.json"
API_CONFIG_FILE = BASE_DIR / "data" / "api_config.json"

# Default settings
DEFAULT_MODEL = "gemini-3-flash-preview"  # Aggiornato Dic 2025 - latest, advanced reasoning
DEFAULT_WAIT = 10  # Flash è molto veloce e ha limiti alti
MAX_RETRIES = 3

def load_api_config() -> Dict:
    """Carica la configurazione API"""
    config = {}
    if API_CONFIG_FILE.exists():
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Errore caricamento config API: {e}")
            
    # Override con env vars
    try:
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv("GEMINI_API_KEY"):
            config["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
    except ImportError:
        pass
        
    return config

def get_gemini_key() -> Optional[str]:
    config = load_api_config()
    return config.get("gemini_api_key")

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

# Costanti per rate limit Gemini
RATE_LIMIT_MAX_RETRIES = 20  # Retry molto più alto per rate limit
RATE_LIMIT_BASE_WAIT = 60    # Attesa base (finestra mobile 60s)
RATE_LIMIT_MAX_WAIT = 600    # Max 10 minuti

def call_gemini(prompt: str, model: str, api_key: str) -> Optional[str]:
    """Chiama Google Gemini API.
    
    IMPORTANTE: In caso di rate limit (429), NON passa al prossimo file
    ma continua a riprovare con backoff esponenziale sullo stesso file.
    
    Gemini API limits (free tier):
    - RPM (Requests Per Minute): finestra mobile 60s
    - TPM (Tokens Per Minute): finestra mobile 60s
    - RPD (Requests Per Day): reset a mezzanotte Pacific Time (PT)
      → In Italia ~09:00 CET
    
    I limiti variano per modello (pro ha limiti più bassi nel free tier).
    """
    # Sanitize model name for Google API (remove OpenRouter prefixes/suffixes)
    clean_model = model.replace("google/", "").replace(":free", "")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }
    
    rate_limit_retries = 0
    other_retries = 0
    
    while other_retries < MAX_RETRIES:
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    logger.error(f"❌ Risposta imprevista da Gemini: {result}")
                    return None
            
            elif response.status_code == 429:
                rate_limit_retries += 1
                
                # Controlla se è limite giornaliero (RPD)
                try:
                    err_text = response.text.lower()
                    if "daily" in err_text or "quota" in err_text and "day" in err_text:
                        logger.error("❌ LIMITE GIORNALIERO GEMINI RAGGIUNTO!")
                        logger.error("   Reset: mezzanotte Pacific Time (PT)")
                        logger.error("   → In Italia circa alle 09:00 CET")
                        logger.error("   Suggerimento: attendi il reset o usa un altro progetto")
                        return None  # Non ha senso riprovare per ore
                except:
                    pass
                
                if rate_limit_retries > RATE_LIMIT_MAX_RETRIES:
                    logger.error(f"❌ Troppi rate limit consecutivi ({rate_limit_retries}). Possibile limite giornaliero.")
                    return None
                
                # Leggi Retry-After se presente
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                        logger.info(f"⏱️ Retry-After header: {wait_time}s")
                    except ValueError:
                        wait_time = RATE_LIMIT_BASE_WAIT
                else:
                    # Backoff esponenziale: 60, 120, 240... max 600s
                    wait_time = min(RATE_LIMIT_BASE_WAIT * (2 ** (rate_limit_retries - 1)), RATE_LIMIT_MAX_WAIT)
                
                # Aggiungi jitter
                jitter = random.randint(-5, 5)
                wait_time = max(30, wait_time + jitter)
                
                logger.warning(f"⚠️ Rate limit (429). Retry {rate_limit_retries}/{RATE_LIMIT_MAX_RETRIES}. Attesa {wait_time}s...")
                logger.info("   💡 RIMANGO sullo stesso PTOF (non passo al prossimo)")
                time.sleep(wait_time)
                continue  # Riprova STESSO file
            
            else:
                other_retries += 1
                logger.error(f"❌ Errore API {response.status_code}: {response.text}")
                time.sleep(10)
                
        except Exception as e:
            other_retries += 1
            logger.error(f"❌ Eccezione chiamata API: {e}")
            time.sleep(10)
            
    return None

def build_enrichment_prompt(source_ptof: str, current_report: str) -> str:
    """Costruisce il prompt per l'arricchimento del report"""
    return f"""
SEI UN EDITOR SCOLASTICO ESPERTO E METICOLOSO.
Il tuo compito è ARRICCHIRE il report di analisi esistente (Markdown) integrando dettagli specifici estratti dal documento originale (PTOF), SENZA stravolgere la struttura del report.

DOCUMENTO ORIGINALE (PTOF - Fonte di Verità):
{source_ptof[:500000]} ... [Il testo continua]

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
    parser = argparse.ArgumentParser(description="Gemini Reviewer per PTOF")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modello Gemini da usare")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="Secondi di attesa tra chiamate")
    parser.add_argument("--limit", type=int, default=100, help="Limite file da processare")
    parser.add_argument("--target", help="Codice scuola specifico da processare (ignora status)")
    args = parser.parse_args()
    
    api_key = get_gemini_key()
    if not api_key:
        logger.error("❌ API Key Gemini non trovata in .env o data/api_config.json")
        return

    logger.info(f"🚀 Avvio Gemini Enrichment con modello: {args.model}")
    logger.info(f"💡 Premi Ctrl+C per uscita controllata")
    
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
        # Controllo uscita richiesta
        if EXIT_REQUESTED:
            logger.info("\n🛑 Uscita controllata richiesta. Salvataggio...")
            break
        
        if count >= args.limit:
            break
            
        logger.info(f"\n✨ Arricchimento {school_code} ({count+1}/{min(len(candidates), args.limit)})")
        
        try:
            # Backup handled by atomic_write
            # shutil.copy2(report_path, BACKUP_DIR / report_path.name)
            
            # Read files
            with open(report_path, 'r') as f:
                current_report = f.read()
            
            with open(source_path, 'r') as f:
                source_content = f.read()
            
            # Call API
            prompt = build_enrichment_prompt(source_content, current_report)
            result_str = call_gemini(prompt, args.model, api_key)
            
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
                
                # Registra nel registry centralizzato
                register_review(school_code, "gemini_review", args.model, "completed", {
                    "report_enriched": True
                })
                
                count += 1
            else:
                logger.error(f"❌ {school_code}: Nessuna risposta dall'API")
                status['failed'].append(school_code)
                register_review(school_code, "gemini_review", args.model, "failed", {
                    "error": "no_response"
                })
                
        except Exception as e:
            logger.error(f"❌ {school_code}: Errore generico: {e}")
            status['failed'].append(school_code)
            register_review(school_code, "gemini_review", args.model, "failed", {
                "error": str(e)
            })
        
        # Wait with jitter
        jitter = random.randint(-2, 2)
        wait_time = max(2, args.wait + jitter)
        logger.info(f"💤 Dormo per {wait_time}s...")
        time.sleep(wait_time)

    logger.info("🏁 Sessione di arricchimento completata")

if __name__ == "__main__":
    main()