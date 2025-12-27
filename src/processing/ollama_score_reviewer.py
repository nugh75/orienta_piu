#!/usr/bin/env python3
"""
Ollama Score Reviewer - Revisione punteggi PTOF con modelli Ollama locali

Strategia:
- Usa modelli Ollama locali (es. qwen3:32b, llama3:70b)
- Chunking intelligente per documenti lunghi
- Verifica incongruenze tra score JSON e contenuto report MD
- Focus su sezione orientamento
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import shutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.file_utils import atomic_write

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

# Import chunker (stesso package)
try:
    from .text_chunker import smart_split, get_chunk_info
except ImportError:
    from text_chunker import smart_split, get_chunk_info

# Import registry
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from utils.analysis_registry import register_review, was_reviewed, load_registry
except ImportError:
    from src.utils.analysis_registry import register_review, was_reviewed, load_registry

# Configurazione
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ANALYSIS_DIR = BASE_DIR / "analysis_results"
MD_DIR = BASE_DIR / "ptof_md"
LOG_DIR = BASE_DIR / "logs"

# Crea directory logs se non esiste
LOG_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'ollama_score_review.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"
DEFAULT_MODEL = "qwen3:32b"
DEFAULT_WAIT = 2  # Ollama locale, no rate limit
DEFAULT_CHUNK_SIZE = 30000  # ~7500 token
DEFAULT_LOW_THRESHOLD = 2
DEFAULT_HIGH_THRESHOLD = 6
MAX_RETRIES = 3


def call_ollama(prompt: str, model: str, ollama_url: str) -> Optional[str]:
    """Chiama Ollama API"""
    url = f"{ollama_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192
        }
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, timeout=300)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                logger.error(f"❌ Errore Ollama {response.status_code}: {response.text}")
                time.sleep(5)
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout (attempt {attempt+1}/{MAX_RETRIES})")
            time.sleep(10)
        except Exception as e:
            logger.error(f"❌ Eccezione Ollama: {e}")
            time.sleep(5)
            
    return None


def extract_score_items(data: Any, path: str = "") -> List[Dict[str, Any]]:
    """Estrae tutti gli score dal JSON"""
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        if "score" in data and isinstance(data.get("score"), (int, float)):
            context = {k: v for k, v in data.items() if k != "score"}
            items.append({
                "path": f"{path}.score" if path else "score",
                "score": data.get("score"),
                "context": context
            })
        for key, value in data.items():
            if key == "score":
                continue
            child_path = f"{path}.{key}" if path else key
            items.extend(extract_score_items(value, child_path))
    return items


def filter_extreme_scores(items: List[Dict[str, Any]], low: int, high: int) -> List[Dict[str, Any]]:
    """Filtra score estremi"""
    return [
        item for item in items
        if isinstance(item.get("score"), (int, float))
        and (item["score"] <= low or item["score"] >= high)
    ]


def check_orientamento_section(json_data: Dict, md_content: str) -> Dict[str, Any]:
    """Verifica coerenza sezione orientamento tra JSON e MD"""
    result = {
        "has_issue": False,
        "json_says_dedicated": False,
        "md_has_section": False,
        "recommendation": None
    }
    
    # Check JSON
    try:
        ptof_section = json_data.get("ptof_section2", {})
        orientamento = ptof_section.get("2_1_ptof_orientamento_sezione_dedicata", {})
        result["json_says_dedicated"] = orientamento.get("has_sezione_dedicata", 0) == 1
        result["orientamento_score"] = orientamento.get("score", 0)
    except:
        pass
    
    # Check MD per sezione dedicata orientamento
    md_lower = md_content.lower()
    orientamento_patterns = [
        "## orientamento",
        "### orientamento", 
        "# orientamento",
        "sezione orientamento",
        "capitolo orientamento",
        "## continuità e orientamento",
        "### continuità e orientamento"
    ]
    result["md_has_section"] = any(p in md_lower for p in orientamento_patterns)
    
    # Verifica incongruenza
    if result["json_says_dedicated"] and not result["md_has_section"]:
        result["has_issue"] = True
        result["recommendation"] = "JSON dice sezione dedicata ma MD non ha capitolo → abbassare score a 1-2"
    elif not result["json_says_dedicated"] and result["md_has_section"]:
        result["has_issue"] = True
        result["recommendation"] = "MD ha capitolo orientamento ma JSON dice no → alzare score"
        
    return result


def build_chunk_review_prompt(chunk: str, score_items: List[Dict], chunk_num: int, total_chunks: int, low: int, high: int) -> str:
    """Costruisce prompt per revisione chunk"""
    scores_json = json.dumps(score_items, ensure_ascii=False, indent=2)
    
    return f"""SEI UN REVISORE CRITICO di documenti scolastici PTOF.
Stai analizzando il CHUNK {chunk_num}/{total_chunks} del documento.

TESTO DEL CHUNK:
{chunk}

PUNTEGGI DA VERIFICARE:
{scores_json}

COMPITO:
1. Verifica se i punteggi estremi (<= {low} o >= {high}) sono giustificati dal testo
2. ATTENZIONE SPECIALE alla sezione orientamento:
   - Se score alto (>=5) per "sezione dedicata" ma nel testo NON c'è un capitolo esplicito → ABBASSA
   - Se score basso ma il testo mostra attività concrete → ALZA
3. Cerca incongruenze: punteggi alti senza evidenze, punteggi bassi con evidenze presenti

CRITERI (1-7):
1=Assente, 2=Generico, 3=Limitato, 4=Sufficiente, 5=Buono, 6=Ottimo, 7=Eccellente

RISPONDI SOLO con JSON valido:
{{
  "chunk_findings": [
    {{
      "path": "percorso.score",
      "current_score": X,
      "suggested_score": Y,
      "action": "confirm|raise|lower",
      "evidence": "breve citazione o motivo"
    }}
  ],
  "orientamento_found": true/false,
  "orientamento_details": "descrizione se trovato"
}}

Se non trovi evidenze rilevanti per nessuno score, rispondi con chunk_findings vuoto."""


def aggregate_chunk_results(results: List[Dict]) -> Dict:
    """Aggrega i risultati di tutti i chunk"""
    aggregated = {
        "score_updates": {},
        "orientamento_found": False,
        "orientamento_details": []
    }
    
    for r in results:
        if not r:
            continue
            
        # Orientamento
        if r.get("orientamento_found"):
            aggregated["orientamento_found"] = True
            if r.get("orientamento_details"):
                aggregated["orientamento_details"].append(r.get("orientamento_details"))
        
        # Score findings
        for finding in r.get("chunk_findings", []):
            path = finding.get("path", "")
            if path:
                # Tieni l'ultima modifica (o la più significativa)
                if path not in aggregated["score_updates"]:
                    aggregated["score_updates"][path] = finding
                else:
                    # Preferisci modifiche a conferme
                    if finding.get("action") != "confirm":
                        aggregated["score_updates"][path] = finding
    
    return aggregated


def apply_score_updates(json_data: Dict, updates: Dict) -> Dict:
    """Applica gli aggiornamenti agli score nel JSON"""
    updated = json.loads(json.dumps(json_data))  # Deep copy
    
    for path, finding in updates.items():
        if finding.get("action") == "confirm":
            continue
            
        new_score = finding.get("suggested_score")
        if not isinstance(new_score, int) or new_score < 1 or new_score > 7:
            continue
            
        # Naviga al path e aggiorna
        parts = path.replace(".score", "").split(".")
        obj = updated
        try:
            for part in parts[:-1]:
                obj = obj[part]
            if parts[-1] in obj and "score" in obj[parts[-1]]:
                old_score = obj[parts[-1]]["score"]
                obj[parts[-1]]["score"] = new_score
                logger.info(f"  📝 {path}: {old_score} → {new_score}")
        except (KeyError, TypeError):
            pass
            
    return updated


def extract_json_from_response(text: str) -> Optional[Dict]:
    """Estrae JSON dalla risposta"""
    try:
        # Prova parsing diretto
        return json.loads(text)
    except:
        pass
    
    # Cerca blocco JSON
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    # Trova { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Ollama Score Reviewer per PTOF")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modello Ollama")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="URL server Ollama")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Dimensione chunk")
    parser.add_argument("--low-threshold", type=int, default=DEFAULT_LOW_THRESHOLD, help="Soglia bassa")
    parser.add_argument("--high-threshold", type=int, default=DEFAULT_HIGH_THRESHOLD, help="Soglia alta")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="Secondi tra chiamate")
    parser.add_argument("--limit", type=int, default=100, help="Limite file")
    parser.add_argument("--target", help="Codice scuola specifico")
    args = parser.parse_args()
    
    logger.info(f"🚀 Avvio Ollama Score Reviewer")
    logger.info(f"   Modello: {args.model}")
    logger.info(f"   URL: {args.ollama_url}")
    logger.info(f"   Chunk size: {args.chunk_size}")
    logger.info(f"   Soglie: low={args.low_threshold}, high={args.high_threshold}")
    logger.info(f"💡 Premi Ctrl+C per uscita controllata")
    
    # Test connessione Ollama
    try:
        resp = requests.get(f"{args.ollama_url}/api/tags", timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Ollama non raggiungibile: {resp.status_code}")
            return
        models = [m["name"] for m in resp.json().get("models", [])]
        logger.info(f"✅ Ollama connesso. Modelli: {', '.join(models[:5])}...")
    except Exception as e:
        logger.error(f"❌ Impossibile connettersi a Ollama: {e}")
        return
    
    # Load registry (usato al posto dello status file locale)
    registry = load_registry()
    
    # Find candidates
    json_files = list(ANALYSIS_DIR.glob("*_PTOF_analysis.json"))
    candidates = []
    
    for jf in json_files:
        school_code = jf.stem.split('_')[0]
        
        if args.target:
            if school_code == args.target:
                md_file = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md"
                ptof_md_file = MD_DIR / f"{school_code}_ptof.md"
                if md_file.exists():
                    candidates.append((school_code, jf, md_file, ptof_md_file))
                break
            continue
        
        # Controlla se già revisionato nel registro centrale
        if was_reviewed(school_code, "ollama_score_review", registry):
            continue
        
        md_file = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md"
        if not md_file.exists():
            continue
        
        ptof_md_file = MD_DIR / f"{school_code}_ptof.md"
        candidates.append((school_code, jf, md_file, ptof_md_file))
    
    logger.info(f"📋 Trovati {len(candidates)} file da revisionare")
    
    count = 0
    for school_code, json_path, md_path, ptof_md_path in candidates:
        # Controllo uscita richiesta
        if EXIT_REQUESTED:
            logger.info("\n🛑 Uscita controllata richiesta. Salvataggio...")
            break
        
        if count >= args.limit:
            break
            
        logger.info(f"\n🔍 Revisione {school_code} ({count+1}/{min(len(candidates), args.limit)})")
        
        try:
            # Leggi file
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            with open(md_path, 'r') as f:
                md_content = f.read()
            
            # Leggi anche PTOF originale se esiste
            ptof_content = ""
            if ptof_md_path.exists():
                with open(ptof_md_path, 'r') as f:
                    ptof_content = f.read()
            
            # Combina MD report + PTOF per analisi completa
            full_content = md_content + "\n\n--- PTOF ORIGINALE ---\n\n" + ptof_content
            
            # Check orientamento
            orient_check = check_orientamento_section(json_data, full_content)
            if orient_check["has_issue"]:
                logger.warning(f"⚠️ [scores:{school_code}] incongruenza orientamento: {orient_check['recommendation']}")
            
            # Estrai e filtra score estremi
            all_scores = extract_score_items(json_data)
            extreme_scores = filter_extreme_scores(all_scores, args.low_threshold, args.high_threshold)
            
            if not extreme_scores:
                logger.info(f"✅ {school_code}: Nessuno score estremo da revisionare")
                # Registra nel registro centrale anche se nessuno score da verificare
                register_review(school_code, "ollama_score_review", args.model, "completed", {
                    "note": "Nessuno score estremo da revisionare",
                    "orientamento_issue": orient_check["has_issue"]
                })
                count += 1
                continue
            
            logger.info(f"   📊 [scores:{school_code}] score estremi da verificare: {len(extreme_scores)}")
            
            # Chunka il documento
            chunks = smart_split(full_content, max_chars=args.chunk_size)
            chunk_info = get_chunk_info(chunks)
            logger.info(f"   📄 [scores:{school_code}] documento diviso in {chunk_info['count']} chunks")
            
            # Analizza ogni chunk
            chunk_results = []
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"   🔄 [scores:{school_code}] chunk {i}/{len(chunks)}")
                
                prompt = build_chunk_review_prompt(
                    chunk, extreme_scores, i, len(chunks),
                    args.low_threshold, args.high_threshold
                )
                
                response = call_ollama(prompt, args.model, args.ollama_url)
                
                if response:
                    parsed = extract_json_from_response(response)
                    if parsed:
                        chunk_results.append(parsed)
                    else:
                        logger.warning(f"   ⚠️ [scores:{school_code}] chunk {i}: risposta non parsabile")
                else:
                    logger.warning(f"   ⚠️ [scores:{school_code}] chunk {i}: nessuna risposta")
                
                time.sleep(args.wait)
            
            # Aggrega risultati
            aggregated = aggregate_chunk_results(chunk_results)
            
            # Log orientamento
            if aggregated["orientamento_found"]:
                logger.info(f"   ✅ Sezione orientamento trovata nel documento")
            else:
                logger.info(f"   ⚠️ Sezione orientamento NON trovata nel documento")
            
            # Applica aggiornamenti
            if aggregated["score_updates"]:
                logger.info(f"   📝 Applicazione {len(aggregated['score_updates'])} modifiche score...")
                updated_json = apply_score_updates(json_data, aggregated["score_updates"])
                
                # Aggiungi entry nel processing_history
                if "processing_history" not in updated_json:
                    updated_json["processing_history"] = []
                
                # Dettagli delle modifiche
                score_changes = []
                for path, finding in aggregated["score_updates"].items():
                    if finding.get("action") != "confirm":
                        score_changes.append({
                            "path": path,
                            "old": finding.get("current_score"),
                            "new": finding.get("suggested_score"),
                            "reason": finding.get("evidence", "")[:100]
                        })
                
                updated_json["processing_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "activity": "ollama_score_review",
                    "model": args.model,
                    "status": "completed",
                    "details": {
                        "chunks_analyzed": len(chunks),
                        "extreme_scores_checked": len(extreme_scores),
                        "scores_modified": len(score_changes),
                        "orientamento_found": aggregated["orientamento_found"],
                        "changes": score_changes
                    }
                })
                
                # Mantieni anche review_history per retrocompatibilità
                if "review_history" not in updated_json:
                    updated_json["review_history"] = []
                updated_json["review_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "reviewer": f"ollama/{args.model}",
                    "type": "score_review",
                    "changes": len(score_changes)
                })
                
                # Salva
                atomic_write(json_path, json.dumps(updated_json, indent=2, ensure_ascii=False), backup=True)
                
                logger.info(f"✅ {school_code}: JSON aggiornato")
                
                # Registra nel registro centrale
                register_review(school_code, "ollama_score_review", args.model, "completed", {
                    "chunks_analyzed": len(chunks),
                    "extreme_scores_checked": len(extreme_scores),
                    "scores_modified": len(score_changes),
                    "orientamento_found": aggregated["orientamento_found"]
                })
            else:
                # Anche se non ci sono modifiche, registra l'attività
                if "processing_history" not in json_data:
                    json_data["processing_history"] = []
                json_data["processing_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "activity": "ollama_score_review",
                    "model": args.model,
                    "status": "completed",
                    "details": {
                        "chunks_analyzed": len(chunks),
                        "extreme_scores_checked": len(extreme_scores),
                        "scores_modified": 0,
                        "orientamento_found": aggregated["orientamento_found"],
                        "note": "Nessuna modifica necessaria"
                    }
                })
                atomic_write(json_path, json.dumps(json_data, indent=2, ensure_ascii=False))
                logger.info(f"✅ {school_code}: Nessuna modifica necessaria (attività registrata)")
                
                # Registra nel registro centrale
                register_review(school_code, "ollama_score_review", args.model, "completed", {
                    "chunks_analyzed": len(chunks),
                    "extreme_scores_checked": len(extreme_scores),
                    "scores_modified": 0,
                    "orientamento_found": aggregated["orientamento_found"],
                    "note": "Nessuna modifica necessaria"
                })
            
            count += 1
            
        except Exception as e:
            logger.error(f"❌ {school_code}: Errore - {e}")
            # Registra fallimento nel registro centrale
            register_review(school_code, "ollama_score_review", args.model, "failed", {
                "error": str(e)
            })
        
        time.sleep(args.wait)
    
    logger.info(f"\n🏁 Sessione completata: {count} file revisionati")


if __name__ == "__main__":
    main()
