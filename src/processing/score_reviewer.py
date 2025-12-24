#!/usr/bin/env python3
"""
Score Reviewer - review extreme scores in PTOF analysis JSON files.
Focuses on scores that are too low or too high, confirms or adjusts them.
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
from typing import Dict, Optional, Any, List, Set

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
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/score_review.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ANALYSIS_DIR = BASE_DIR / "analysis_results"
MD_DIR = BASE_DIR / "ptof_md"
BACKUP_DIR = ANALYSIS_DIR / "pre_score_review_backup"
STATUS_FILE = BASE_DIR / "data" / "score_review_status.json"
API_CONFIG_FILE = BASE_DIR / "data" / "api_config.json"

# Defaults
DEFAULT_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
DEFAULT_WAIT = 120  # seconds
DEFAULT_LOW_THRESHOLD = 2
DEFAULT_HIGH_THRESHOLD = 6
DEFAULT_MAX_CHARS = 60000
MAX_RETRIES = 3


def load_api_config() -> Dict[str, Any]:
    """Load API config from JSON file."""
    if API_CONFIG_FILE.exists():
        try:
            with open(API_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"API config load error: {e}")
    return {}


def get_openrouter_key() -> Optional[str]:
    # Try .env first
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            return key
    except ImportError:
        logger.warning("python-dotenv not installed; cannot read .env")

    # Fallback to api_config.json
    config = load_api_config()
    return config.get("openrouter_api_key")


def get_gemini_key() -> Optional[str]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("GEMINI_API_KEY")
        if key:
            return key
    except ImportError:
        logger.warning("python-dotenv not installed; cannot read .env")

    config = load_api_config()
    return config.get("gemini_api_key")


def save_status(status: Dict[str, Any]) -> None:
    """Save review status to disk."""
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Status save error: {e}")


def load_status() -> Dict[str, List[str]]:
    """Load review status."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Status load error: {e}")
    return {"reviewed": [], "failed": []}


def call_openrouter(prompt: str, model: str, api_key: str) -> Optional[str]:
    """Call OpenRouter with retry/backoff."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/nugh75/LIste",
        "X-Title": "PTOF Score Reviewer",
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
                return response.json()["choices"][0]["message"]["content"]
            if response.status_code == 429:
                wait_time = 300 * (attempt + 1)
                logger.warning(f"Rate limit (429). Waiting {wait_time}s...")
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
                        return None
                except:
                    pass

                logger.error(f"API error {response.status_code}: {response.text}")
                time.sleep(10)
        except Exception as e:
            logger.error(f"API exception: {e}")
            time.sleep(10)

    return None


def call_gemini(prompt: str, model: str, api_key: str) -> Optional[str]:
    """Call Google Gemini API with retry/backoff."""
    # Sanitize model name for Google API (remove OpenRouter prefixes/suffixes)
    clean_model = model.replace("google/", "").replace(":free", "")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            if response.status_code == 200:
                result = response.json()
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    logger.error(f"Unexpected Gemini response: {result}")
                    return None
            if response.status_code == 429:
                wait_time = 60 * (attempt + 1)
                logger.warning(f"Rate limit (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Gemini API error {response.status_code}: {response.text}")
                time.sleep(10)
        except Exception as e:
            logger.error(f"Gemini API exception: {e}")
            time.sleep(10)

    return None


def extract_score_items(data: Any, path: str = "") -> List[Dict[str, Any]]:
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
    return [
        item for item in items
        if isinstance(item.get("score"), (int, float))
        and (item["score"] <= low or item["score"] >= high)
    ]


def build_extreme_review_prompt(
    md_content: str,
    score_items: List[Dict[str, Any]],
    low: int,
    high: int,
    max_chars: int
) -> str:
    scores_json = json.dumps(score_items, ensure_ascii=False, indent=2)
    truncated_md = md_content[:max_chars]
    return f"""
SEI UN REVISORE CRITICO. Devi verificare SOLO i punteggi estremi (<= {low} o >= {high}).
Conferma o modifica i punteggi usando il testo come fonte di verita.

ISTRUZIONE SPECIALE - SEZIONE ORIENTAMENTO:
Verifica con ESTREMA ATTENZIONE se esiste un capitolo o una sezione esplicitamente intitolata "Orientamento" (o variazioni chiare come "Continuità e Orientamento").
Se il punteggio relativo alla sezione dedicata è alto (>= {high}) ma nel testo NON c'è un capitolo specifico, DEVI abbassare il punteggio a 1 o 2.
NON considerare "dedicata" una sezione se l'orientamento è solo menzionato in paragrafi sparsi.

DOCUMENTO ORIGINALE (Markdown, estratto):
{truncated_md} ... [troncato se troppo lungo]

PUNTEGGI DA REVISIONARE (JSON):
{scores_json}

CRITERI PUNTEGGIO (1-7):
1 = Assente (nessun riferimento)
2 = Generico (menzione vaga)
3 = Limitato (intenzione senza dettagli)
4 = Sufficiente (azioni chiare ma basilari)
5 = Buono (azioni strutturate, metodologie definite)
6 = Ottimo (azioni integrate, innovative e monitorate)
7 = Eccellente (best practice sistemica, valutata e migliorata)

FORMATO OUTPUT (solo JSON valido):
{{
  "score_updates": [
    {{
      "path": "ptof_section2.2_3_finalita.finalita_attitudini.score",
      "old_score": 2,
      "new_score": 3,
      "action": "modify",
      "reason": "Spiega in breve."
    }}
  ],
  "review_notes": "Nota generale opzionale."
}}

REGOLE:
- Includi un elemento in score_updates per OGNI path ricevuto.
- Se confermi: new_score = old_score e action = "confirm".
- new_score deve essere un intero 1-7.
- Non aggiungere nuovi campi o percorsi.
- Nessun testo extra, solo JSON.
"""


def extract_json_block(text: str) -> str:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1]
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0]
    cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return cleaned


def normalize_score(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def set_json_path(data: Dict[str, Any], path: str, value: int) -> bool:
    parts = path.split(".")
    cursor: Any = data
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            return False
        cursor = cursor[part]
    last = parts[-1]
    if not isinstance(cursor, dict) or last not in cursor:
        return False
    cursor[last] = value
    return True


def apply_score_updates(
    data: Dict[str, Any],
    updates: List[Dict[str, Any]],
    allowed_paths: Set[str]
) -> int:
    applied = 0
    for update in updates:
        path = update.get("path")
        if path not in allowed_paths:
            continue
        new_score = normalize_score(update.get("new_score"))
        if new_score is None or not (1 <= new_score <= 7):
            continue
        if set_json_path(data, path, new_score):
            applied += 1
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Reviewer for PTOF analyses")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, choices=["openrouter", "gemini"], help="LLM provider")
    parser.add_argument("--model", default=None, help="Model name (provider-specific)")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="Wait seconds between calls")
    parser.add_argument("--limit", type=int, default=100, help="Max files to process")
    parser.add_argument("--target", help="Specific school code to process (ignores status)")
    parser.add_argument("--low-threshold", type=int, default=DEFAULT_LOW_THRESHOLD, help="Low score threshold (<=)")
    parser.add_argument("--high-threshold", type=int, default=DEFAULT_HIGH_THRESHOLD, help="High score threshold (>=)")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="Max PTOF chars in prompt")
    args = parser.parse_args()

    if args.provider == "gemini":
        api_key = get_gemini_key()
        model_name = args.model or DEFAULT_GEMINI_MODEL
        call_llm = call_gemini
    else:
        api_key = get_openrouter_key()
        model_name = args.model or DEFAULT_OPENROUTER_MODEL
        call_llm = call_openrouter

    if not api_key:
        logger.error(f"{args.provider} API key not found in .env or data/api_config.json")
        return

    logger.info(f"Starting score review with provider: {args.provider} model: {model_name}")
    logger.info(f"Base wait: {args.wait}s")
    logger.info(f"💡 Premi Ctrl+C per uscita controllata")

    BACKUP_DIR.mkdir(exist_ok=True)

    status = load_status()
    reviewed_set = set(status["reviewed"])

    json_files = list(ANALYSIS_DIR.glob("*_PTOF_analysis.json"))
    candidates = []

    for jf in json_files:
        school_code = jf.stem.split("_")[0]

        if args.target:
            if school_code == args.target:
                md_file = MD_DIR / f"{school_code}_ptof.md"
                if md_file.exists():
                    candidates.append((school_code, jf, md_file))
                break
            continue

        if school_code in reviewed_set:
            continue

        md_file = MD_DIR / f"{school_code}_ptof.md"
        if not md_file.exists():
            continue

        candidates.append((school_code, jf, md_file))

    logger.info(f"Found {len(candidates)} files to review")

    count = 0
    for school_code, json_path, md_path in candidates:
        # Controllo uscita richiesta
        if EXIT_REQUESTED:
            logger.info("\n🛑 Uscita controllata richiesta. Salvataggio...")
            break
        
        if count >= args.limit:
            break

        logger.info(f"Reviewing {school_code} ({count + 1}/{min(len(candidates), args.limit)})")
        called_api = False

        try:
            with open(json_path, "r") as f:
                current_json = json.load(f)

            with open(md_path, "r") as f:
                md_content = f.read()

            score_items = extract_score_items(current_json)
            extreme_items = filter_extreme_scores(
                score_items, args.low_threshold, args.high_threshold
            )

            if not extreme_items:
                logger.info(f"No extreme scores found for {school_code}, skipping API call.")
                status["reviewed"].append(school_code)
                save_status(status)
                count += 1
                continue

            shutil.copy2(json_path, BACKUP_DIR / json_path.name)

            prompt = build_extreme_review_prompt(
                md_content, extreme_items, args.low_threshold, args.high_threshold, args.max_chars
            )
            called_api = True
            result_str = call_llm(prompt, model_name, api_key)

            if result_str:
                cleaned = extract_json_block(result_str)
                parsed = json.loads(cleaned)

                updates = parsed.get("score_updates")
                if not isinstance(updates, list):
                    raise ValueError("Invalid response: score_updates missing or not a list")

                allowed_paths = {item.get("path") for item in extreme_items if item.get("path")}
                applied = apply_score_updates(current_json, updates, allowed_paths)

                review_notes = parsed.get("review_notes")
                if isinstance(review_notes, str) and review_notes.strip():
                    current_json["review_notes"] = review_notes.strip()

                with open(json_path, "w") as f:
                    json.dump(current_json, f, indent=2, ensure_ascii=False)

                logger.info(f"{school_code}: applied {applied}/{len(allowed_paths)} updates")
                status["reviewed"].append(school_code)
                save_status(status)
                count += 1
            else:
                logger.error(f"{school_code}: no response from API")
                status["failed"].append(school_code)

        except Exception as e:
            logger.error(f"{school_code}: error during review: {e}")
            status["failed"].append(school_code)

        if called_api:
            jitter = random.randint(-15, 15)
            wait_time = max(30, args.wait + jitter)
            logger.info(f"Sleeping {wait_time}s...")
            time.sleep(wait_time)

    logger.info("Score review session completed")


if __name__ == "__main__":
    main()
