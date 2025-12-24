#!/usr/bin/env python3
"""
Ollama Report Reviewer - Arricchimento report PTOF con modelli Ollama locali

Strategia:
- Usa modelli Ollama locali (es. qwen3:32b, llama3:70b)
- Chunking intelligente per documenti lunghi
- Verifica incongruenze tra report MD e score JSON
- Focus su sezione orientamento e coerenza
"""

import os
import json
import time
import logging
import argparse
import shutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List

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
BACKUP_DIR = ANALYSIS_DIR / "pre_ollama_report_backup"
LOG_DIR = BASE_DIR / "logs"

# Crea directory logs se non esiste
LOG_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'ollama_report_review.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"
DEFAULT_MODEL = "qwen3:32b"
DEFAULT_WAIT = 2  # Ollama locale, no rate limit
DEFAULT_CHUNK_SIZE = 30000  # ~7500 token
MAX_RETRIES = 3


def call_ollama(prompt: str, model: str, ollama_url: str, json_mode: bool = False) -> Optional[str]:
    """Chiama Ollama API"""
    url = f"{ollama_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192
        }
    }
    
    if json_mode:
        payload["format"] = "json"
    
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


def extract_scores_summary(json_data: Dict) -> str:
    """Estrae un riepilogo degli score dal JSON per il prompt"""
    summary_lines = []
    
    def walk(obj, path=""):
        if isinstance(obj, dict):
            if "score" in obj:
                score = obj["score"]
                note = obj.get("note") or obj.get("evidence_quote") or ""
                note = str(note)[:100] if note else ""
                summary_lines.append(f"- {path}: score={score} | {note}")
            for k, v in obj.items():
                if k not in ["score", "note", "evidence_quote"]:
                    walk(v, f"{path}.{k}" if path else k)
    
    walk(json_data)
    return "\n".join(summary_lines[:50])  # Limita a 50 righe


def build_new_report_prompt(school_code: str, json_data: Dict, ptof_content: str, 
                            orientamento_found: bool, orientamento_details: str) -> str:
    """Costruisce prompt per creare un report da zero"""
    
    # Estrai metadata
    metadata = json_data.get("metadata", {})
    denominazione = metadata.get("denominazione", "Scuola")
    tipo_scuola = metadata.get("tipo_scuola", "")
    comune = metadata.get("comune", "")
    regione = metadata.get("regione", "")
    
    scores_summary = extract_scores_summary(json_data)
    
    orient_instruction = ""
    if orientamento_found:
        orient_instruction = f"""
SEZIONE ORIENTAMENTO TROVATA:
{orientamento_details}
Descrivi accuratamente questa sezione nel report."""
    else:
        orient_instruction = """
ATTENZIONE: Nel PTOF NON è stata trovata una sezione dedicata all'orientamento.
Nella sezione "2.1 Sezione Dedicata all'Orientamento" scrivi onestamente che non esiste un capitolo dedicato."""
    
    # Tronca PTOF per il prompt
    ptof_truncated = ptof_content[:80000]
    
    return f"""SEI UN ANALISTA ESPERTO di documenti scolastici PTOF.
Devi CREARE un report di analisi completo per la scuola {school_code}.

INFORMAZIONI SCUOLA:
- Codice: {school_code}
- Denominazione: {denominazione}
- Tipo: {tipo_scuola}
- Comune: {comune}
- Regione: {regione}

RIEPILOGO SCORE GIÀ CALCOLATI:
{scores_summary}
{orient_instruction}

PTOF ORIGINALE (estratto):
{ptof_truncated}
... [documento troncato]

COMPITO:
Genera un report completo in Markdown seguendo ESATTAMENTE questa struttura:

# Analisi del PTOF {school_code}
## Report di Valutazione dell'Orientamento

### 1. Sintesi Generale
[Panoramica della scuola e del suo PTOF - 3-5 paragrafi narrativi]

### 2. Analisi Dimensionale

#### 2.1 Sezione Dedicata all'Orientamento
[Descrivi se esiste una sezione dedicata, dove si trova, cosa contiene]

#### 2.2 Partnership e Reti
[Elenca e descrivi le partnership con enti, università, aziende]

#### 2.3 Finalità e Obiettivi
[Obiettivi dell'orientamento, sviluppo competenze, etc.]

#### 2.4 Governance e Azioni di Sistema
[Organizzazione, figure di riferimento, commissioni]

#### 2.5 Didattica Orientativa
[Metodologie, approcci didattici per l'orientamento]

#### 2.6 Opportunità Formative
[PCTO, stage, progetti, certificazioni]

#### 2.7 Registro Dettagliato delle Attività
[Elenco progetti e attività specifiche]

### 3. Punti di Forza
[3-5 punti di forza narrativi]

### 4. Aree di Debolezza
[3-5 aree da migliorare]

### 5. Gap Analysis
[Analisi delle lacune rispetto alle linee guida]

### 6. Conclusioni
[Sintesi finale e raccomandazioni]

ISTRUZIONI:
- Usa STILE NARRATIVO E DISCORSIVO
- Cita dettagli specifici dal PTOF (nomi progetti, partner, etc.)
- Sii coerente con gli score JSON
- NON INVENTARE informazioni non presenti nel PTOF

OUTPUT: Restituisci SOLO il report Markdown completo, senza commenti introduttivi."""


def check_report_score_coherence(report: str, json_data: Dict) -> List[Dict]:
    """Verifica coerenza tra report e score"""
    issues = []
    
    report_lower = report.lower()
    
    # Check orientamento
    ptof_section = json_data.get("ptof_section2", {})
    orient = ptof_section.get("2_1_ptof_orientamento_sezione_dedicata", {})
    orient_score = orient.get("score", 0)
    has_dedicated = orient.get("has_sezione_dedicata", 0)
    
    # Pattern nel report che indicano sezione dedicata
    report_says_dedicated = any(p in report_lower for p in [
        "sezione dedicata all'orientamento",
        "capitolo dedicato all'orientamento",
        "esiste una sezione",
        "presenta una sezione specifica"
    ])
    
    report_says_no_section = any(p in report_lower for p in [
        "non esiste una sezione",
        "non presenta una sezione",
        "assenza di una sezione",
        "manca una sezione dedicata"
    ])
    
    if has_dedicated == 1 and report_says_no_section:
        issues.append({
            "type": "orientamento_mismatch",
            "detail": "JSON dice sezione dedicata esiste ma report dice no",
            "action": "Verificare e correggere report o score"
        })
    elif has_dedicated == 0 and report_says_dedicated:
        issues.append({
            "type": "orientamento_mismatch", 
            "detail": "Report dice sezione dedicata esiste ma JSON dice no",
            "action": "Verificare e correggere report o score"
        })
    
    # Check score alti vs contenuto generico
    if orient_score >= 5 and "generico" in report_lower and "orientamento" in report_lower:
        issues.append({
            "type": "score_vs_content",
            "detail": f"Score orientamento alto ({orient_score}) ma report menziona contenuto generico",
            "action": "Verificare se score è giustificato"
        })
    
    return issues


def build_chunk_enrichment_prompt(chunk: str, current_report: str, scores_summary: str, 
                                   chunk_num: int, total_chunks: int, issues: List[Dict]) -> str:
    """Costruisce prompt per arricchimento chunk"""
    
    issues_text = ""
    if issues:
        issues_text = "\n\nINCONGRUENZE RILEVATE DA CORREGGERE:\n"
        for i in issues:
            issues_text += f"- {i['type']}: {i['detail']} → {i['action']}\n"
    
    return f"""SEI UN EDITOR SCOLASTICO ESPERTO.
Stai analizzando il CHUNK {chunk_num}/{total_chunks} del documento PTOF originale.

COMPITO: Trova informazioni utili per ARRICCHIRE il report esistente.
{issues_text}
CHUNK DEL PTOF ORIGINALE:
{chunk}

REPORT ATTUALE (da arricchire):
{current_report[:5000]}... [troncato]

RIEPILOGO SCORE JSON:
{scores_summary[:2000]}

ISTRUZIONI:
1. Cerca informazioni SPECIFICHE nel chunk che mancano nel report:
   - Nomi di progetti concreti
   - Dati quantitativi (ore, budget, percentuali)
   - Partner e collaborazioni
   - Metodologie didattiche specifiche
2. VERIFICA ORIENTAMENTO: Se questo chunk contiene un capitolo/sezione dedicata all'orientamento, segnalalo
3. SEGNALA incongruenze se trovi che il report dice cose non supportate dal PTOF
4. NON INVENTARE - usa solo informazioni presenti nel chunk

RISPONDI con JSON:
{{
  "enrichments": [
    {{
      "section": "nome sezione report da arricchire",
      "addition": "testo da aggiungere (stile narrativo, non elenchi)",
      "source_quote": "citazione breve dal PTOF"
    }}
  ],
  "orientamento_section_found": true/false,
  "orientamento_details": "se trovato, descrivi la sezione",
  "corrections": [
    {{
      "issue": "cosa va corretto nel report",
      "reason": "perché (basato su PTOF)"
    }}
  ]
}}

Se il chunk non contiene informazioni utili, rispondi con enrichments e corrections vuoti."""


def build_final_enrichment_prompt(current_report: str, all_enrichments: List[Dict], 
                                   all_corrections: List[Dict], orientamento_found: bool) -> str:
    """Costruisce prompt per generare report finale arricchito"""
    
    enrichments_text = json.dumps(all_enrichments, ensure_ascii=False, indent=2)
    corrections_text = json.dumps(all_corrections, ensure_ascii=False, indent=2)
    
    orient_instruction = ""
    if not orientamento_found:
        orient_instruction = """
ATTENZIONE SEZIONE ORIENTAMENTO:
Nel PTOF originale NON è stata trovata una sezione dedicata all'orientamento.
Se il report attuale dice che esiste, CORREGGI questa affermazione.
Nella sezione "2.1 Sezione Dedicata all'Orientamento" scrivi onestamente che non esiste un capitolo dedicato."""
    
    return f"""SEI UN EDITOR SCOLASTICO ESPERTO.
Devi produrre la versione FINALE ARRICCHITA del report.

REPORT ATTUALE:
{current_report}

ARRICCHIMENTI DA INTEGRARE:
{enrichments_text}

CORREZIONI DA APPLICARE:
{corrections_text}
{orient_instruction}

ISTRUZIONI:
1. Integra gli arricchimenti nelle sezioni appropriate del report
2. Usa STILE NARRATIVO E DISCORSIVO (no elenchi puntati se possibile)
3. Applica le correzioni segnalate
4. MANTIENI la struttura esistente del report
5. NON rimuovere sezioni esistenti

STRUTTURA OBBLIGATORIA DA PRESERVARE:
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

OUTPUT: Restituisci SOLO il report Markdown completo arricchito, senza commenti."""


def extract_json_from_response(text: str) -> Optional[Dict]:
    """Estrae JSON dalla risposta"""
    try:
        return json.loads(text)
    except:
        pass
    
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    
    return None


def clean_markdown_response(text: str) -> str:
    """Pulisce la risposta markdown"""
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[11:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Ollama Report Reviewer per PTOF")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modello Ollama")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="URL server Ollama")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Dimensione chunk")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="Secondi tra chiamate")
    parser.add_argument("--limit", type=int, default=100, help="Limite file")
    parser.add_argument("--target", help="Codice scuola specifico")
    args = parser.parse_args()
    
    logger.info(f"🚀 Avvio Ollama Report Reviewer")
    logger.info(f"   Modello: {args.model}")
    logger.info(f"   URL: {args.ollama_url}")
    logger.info(f"   Chunk size: {args.chunk_size}")
    
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
    
    # Setup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Load registry (usato al posto dello status file locale)
    registry = load_registry()
    
    # Find candidates - cerca JSON (non report MD) per trovare anche quelli senza report
    json_files = list(ANALYSIS_DIR.glob("*_PTOF_analysis.json"))
    candidates = []
    
    for jf in json_files:
        school_code = jf.stem.split('_')[0]
        
        if args.target:
            if school_code == args.target:
                report_file = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md"
                ptof_md = MD_DIR / f"{school_code}_ptof.md"
                if ptof_md.exists():
                    # report_file può non esistere - verrà creato
                    candidates.append((school_code, report_file, jf, ptof_md, report_file.exists()))
                break
            continue
        
        # Controlla se già revisionato nel registro centrale
        if was_reviewed(school_code, "ollama_report_review", registry):
            continue
        
        report_file = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md"
        ptof_md = MD_DIR / f"{school_code}_ptof.md"
        
        if not ptof_md.exists():
            continue
        
        # report_file può non esistere - verrà creato
        candidates.append((school_code, report_file, jf, ptof_md, report_file.exists()))
    
    # Conta quanti report mancano
    missing_reports = sum(1 for c in candidates if not c[4])
    logger.info(f"📋 Trovati {len(candidates)} candidati ({missing_reports} senza report MD)")
    
    count = 0
    for school_code, report_path, json_path, ptof_path, report_exists in candidates:
        if count >= args.limit:
            break
        
        action = "Arricchimento" if report_exists else "Creazione"
        logger.info(f"\n✨ {action} {school_code} ({count+1}/{min(len(candidates), args.limit)})")
        
        try:
            # Backup report se esiste
            if report_exists:
                shutil.copy2(report_path, BACKUP_DIR / report_path.name)
            
            # Leggi JSON
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Leggi PTOF
            with open(ptof_path, 'r') as f:
                ptof_content = f.read()
            
            # Leggi report esistente o usa placeholder
            if report_exists:
                with open(report_path, 'r') as f:
                    current_report = f.read()
            else:
                current_report = ""  # Report da creare
            
            # Verifica coerenza iniziale (solo se report esiste)
            initial_issues = []
            if report_exists:
                initial_issues = check_report_score_coherence(current_report, json_data)
                if initial_issues:
                    logger.warning(f"   ⚠️ Incongruenze trovate: {len(initial_issues)}")
                    for issue in initial_issues:
                        logger.warning(f"      - {issue['type']}: {issue['detail']}")
            
            # Estrai riepilogo score
            scores_summary = extract_scores_summary(json_data)
            
            # Chunka il PTOF
            chunks = smart_split(ptof_content, max_chars=args.chunk_size)
            chunk_info = get_chunk_info(chunks)
            logger.info(f"   📄 PTOF diviso in {chunk_info['count']} chunks")
            
            # Analizza ogni chunk per trovare info e orientamento
            all_enrichments = []
            all_corrections = []
            orientamento_found = False
            orientamento_details = ""
            
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"   🔄 Analisi chunk {i}/{len(chunks)}...")
                
                prompt = build_chunk_enrichment_prompt(
                    chunk, current_report if report_exists else "[REPORT DA CREARE]", 
                    scores_summary, i, len(chunks), initial_issues
                )
                
                response = call_ollama(prompt, args.model, args.ollama_url, json_mode=True)
                
                if response:
                    parsed = extract_json_from_response(response)
                    if parsed:
                        all_enrichments.extend(parsed.get("enrichments", []))
                        all_corrections.extend(parsed.get("corrections", []))
                        if parsed.get("orientamento_section_found"):
                            orientamento_found = True
                            if parsed.get("orientamento_details"):
                                orientamento_details += parsed.get("orientamento_details") + "\n"
                            logger.info(f"      ✅ Sezione orientamento trovata in chunk {i}")
                    else:
                        logger.warning(f"   ⚠️ Chunk {i}: risposta non parsabile")
                else:
                    logger.warning(f"   ⚠️ Chunk {i}: nessuna risposta")
                
                time.sleep(args.wait)
            
            logger.info(f"   📊 Raccolti {len(all_enrichments)} arricchimenti, {len(all_corrections)} correzioni")
            
            if not orientamento_found:
                logger.warning(f"   ⚠️ Nessuna sezione orientamento trovata nel PTOF")
            
            # Variabili per tracking
            activity_status = "completed"
            activity_action = None
            report_created = False
            report_enriched = False
            
            # Genera report
            if not report_exists:
                # CREAZIONE NUOVO REPORT
                logger.info(f"   ✍️ Creazione nuovo report...")
                activity_action = "create"
                
                new_report_prompt = build_new_report_prompt(
                    school_code, json_data, ptof_content, 
                    orientamento_found, orientamento_details
                )
                
                final_response = call_ollama(new_report_prompt, args.model, args.ollama_url, json_mode=False)
                
                if final_response:
                    new_report = clean_markdown_response(final_response)
                    
                    if "# Analisi del PTOF" in new_report or "## Report di Valutazione" in new_report:
                        with open(report_path, 'w') as f:
                            f.write(new_report)
                        logger.info(f"✅ {school_code}: Nuovo report creato!")
                        report_created = True
                    else:
                        logger.warning(f"⚠️ {school_code}: Report generato non valido")
                        activity_status = "failed"
                else:
                    logger.warning(f"⚠️ {school_code}: Nessuna risposta per creazione report")
                    activity_status = "failed"
                    
            elif all_enrichments or all_corrections:
                # ARRICCHIMENTO REPORT ESISTENTE
                logger.info(f"   ✍️ Generazione report arricchito...")
                activity_action = "enrich"
                
                final_prompt = build_final_enrichment_prompt(
                    current_report, all_enrichments, all_corrections, orientamento_found
                )
                
                final_response = call_ollama(final_prompt, args.model, args.ollama_url, json_mode=False)
                
                if final_response:
                    enriched_report = clean_markdown_response(final_response)
                    
                    # Verifica che abbia le sezioni chiave
                    if "# Analisi del PTOF" in enriched_report or "## Report di Valutazione" in enriched_report:
                        with open(report_path, 'w') as f:
                            f.write(enriched_report)
                        logger.info(f"✅ {school_code}: Report arricchito salvato")
                        report_enriched = True
                    else:
                        logger.warning(f"⚠️ {school_code}: Report generato non valido, mantengo originale")
                        activity_status = "partial"
                else:
                    logger.warning(f"⚠️ {school_code}: Nessuna risposta per report finale")
                    activity_status = "failed"
            else:
                activity_action = "check"
                logger.info(f"✅ {school_code}: Nessun arricchimento necessario")
            
            # Aggiorna JSON con processing_history
            if "processing_history" not in json_data:
                json_data["processing_history"] = []
            
            json_data["processing_history"].append({
                "timestamp": datetime.now().isoformat(),
                "activity": "ollama_report_review",
                "model": args.model,
                "status": activity_status,
                "details": {
                    "action": activity_action,
                    "chunks_analyzed": len(chunks),
                    "enrichments_found": len(all_enrichments),
                    "corrections_found": len(all_corrections),
                    "orientamento_found": orientamento_found,
                    "report_created": report_created,
                    "report_enriched": report_enriched,
                    "initial_issues": len(initial_issues) if initial_issues else 0
                }
            })
            
            # Salva JSON aggiornato
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Registra nel registro centrale
            register_review(school_code, "ollama_report_review", args.model, activity_status, {
                "action": activity_action,
                "chunks_analyzed": len(chunks),
                "enrichments_found": len(all_enrichments),
                "corrections_found": len(all_corrections),
                "orientamento_found": orientamento_found,
                "report_created": report_created,
                "report_enriched": report_enriched,
                "initial_issues": len(initial_issues) if initial_issues else 0
            })
            count += 1
            
        except Exception as e:
            logger.error(f"❌ {school_code}: Errore - {e}")
            import traceback
            traceback.print_exc()
            
            # Registra anche errori nel JSON
            try:
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                if "processing_history" not in json_data:
                    json_data["processing_history"] = []
                json_data["processing_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "activity": "ollama_report_review",
                    "model": args.model,
                    "status": "error",
                    "details": {
                        "error": str(e)
                    }
                })
                with open(json_path, 'w') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
            except:
                pass
            
            # Registra fallimento nel registro centrale
            register_review(school_code, "ollama_report_review", args.model, "failed", {
                "error": str(e)
            })
        
        time.sleep(args.wait)
    
    logger.info(f"\n🏁 Sessione completata: {count} report elaborati")


if __name__ == "__main__":
    main()
