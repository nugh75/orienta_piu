#!/usr/bin/env python3
"""
PTOFValidator - Validazione progressiva documenti PTOF
======================================================

Sistema di validazione in 3 fasi:
1. HEURISTICS (veloce): keywords, struttura, pagine
2. OLLAMA (se ambiguo): analisi intelligente contenuto
3. RECOVERY: sistema per recuperare file scartati erroneamente

Autore: PTOF Analysis System
"""

import os
import sys
import json
import shutil
import logging
import re
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Carica variabili d'ambiente da .env
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from typing import Optional, Dict, Tuple, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import requests
from pypdf import PdfReader

# Aggiungi path progetto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Import per School Database (gestione path)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
try:
    from src.utils.school_database import SchoolDatabase
except ImportError:
    SchoolDatabase = None

# Configurazione import
try:
    from src.utils.file_utils import atomic_write
except ImportError:
    # Fallback if utils not available
    import contextlib
    @contextlib.contextmanager
    def atomic_write(file, mode="w", **kwargs):
        with open(file, mode, **kwargs) as f:
            yield f
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'ptof_validator.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Sopprimi warning rumorosi di pypdf
logging.getLogger("pypdf").setLevel(logging.ERROR)

# =====================================================
# CONFIGURAZIONE
# =====================================================

OLLAMA_URL = os.environ.get("PTOF_OLLAMA_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/generate")
OLLAMA_MODEL = os.environ.get("PTOF_MODEL", "qwen3:32b")  # Modello per validazione

# Directory
DISCARDED_DIR = BASE_DIR / "ptof_discarded"
DISCARDED_NOT_PTOF = DISCARDED_DIR / "not_ptof"
DISCARDED_TOO_SHORT = DISCARDED_DIR / "too_short"
DISCARDED_CORRUPTED = DISCARDED_DIR / "corrupted"
DISCARDED_TO_CHECK = DISCARDED_DIR / "da_controllare"
RECOVERY_LOG = DISCARDED_DIR / "recovery_log.json"
ALLOWLIST_FILE = BASE_DIR / "data" / "ptof_validator_allowlist.txt"
VALIDATION_REGISTRY_FILE = BASE_DIR / "data" / "validation_registry.json"
ANALYSIS_DIR = BASE_DIR / "analysis_results"

# Soglie
MIN_PAGES = 5  # Minimo pagine per un PTOF valido
MIN_CHARS = 3000  # Minimo caratteri estratti
CONFIDENCE_THRESHOLD_HEURISTIC = 0.75  # Se > 0.75, skip LLM (era 0.65)
CONFIDENCE_THRESHOLD_LLM = 0.55  # Se > 0.55 dopo LLM, accetta (era 0.45)


# =====================================================
# REGISTRO VALIDAZIONE
# =====================================================

def _compute_file_hash(file_path: Path) -> str:
    """Calcola hash SHA256 del file."""
    import hashlib
    hash_func = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def load_validation_registry() -> Dict:
    """Carica il registro delle validazioni."""
    if not VALIDATION_REGISTRY_FILE.exists():
        return {"validated_files": {}, "last_updated": None}
    try:
        with open(VALIDATION_REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Errore caricamento registro validazione: {e}")
        return {"validated_files": {}, "last_updated": None}


def save_validation_registry(registry: Dict) -> bool:
    """Salva il registro delle validazioni."""
    try:
        VALIDATION_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        registry["last_updated"] = datetime.now().isoformat()
        with open(VALIDATION_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Errore salvataggio registro validazione: {e}")
        return False


def is_already_validated(pdf_path: Path, registry: Dict = None) -> Tuple[bool, Optional[str]]:
    """
    Verifica se un PDF è già stato validato.
    
    Returns:
        (True, result) se già validato con stesso hash
        (False, None) se nuovo o modificato
    """
    if registry is None:
        registry = load_validation_registry()
    
    validated = registry.get("validated_files", {})
    file_key = pdf_path.name
    
    if file_key not in validated:
        return False, None
    
    entry = validated[file_key]
    try:
        current_hash = _compute_file_hash(pdf_path)
    except Exception:
        return False, None
    
    if current_hash == entry.get("hash"):
        return True, entry.get("result")
    
    return False, None


def register_validation(pdf_path: Path, result: str, confidence: float, 
                        school_code: Optional[str] = None,
                        registry: Dict = None, auto_save: bool = True) -> Dict:
    """Registra una validazione completata."""
    if registry is None:
        registry = load_validation_registry()
    
    try:
        file_hash = _compute_file_hash(pdf_path)
    except Exception:
        file_hash = "error"
    
    entry = {
        "hash": file_hash,
        "result": result,
        "confidence": confidence,
        "validated_at": datetime.now().isoformat()
    }
    
    if school_code:
        entry["school_code"] = school_code
        
    registry["validated_files"][pdf_path.name] = entry
    
    if auto_save:
        save_validation_registry(registry)
    
    return registry


def count_unique_schools(registry: Dict) -> int:
    """Conta le scuole uniche nel registro (valid_ptof)."""
    unique = set()
    for name, entry in registry.get("validated_files", {}).items():
        if entry.get("result") != ValidationResult.VALID_PTOF.value:
            continue
            
        # Usa il codice se salvato
        if entry.get("school_code"):
            unique.add(entry["school_code"])
            continue
            
        # Altrimenti tenta di estrarre dal nome file
        match = re.search(r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})', name)
        if match:
             unique.add(match.group(1))
             
    return len(unique)


class ValidationResult(Enum):
    """Risultato validazione"""
    VALID_PTOF = "valid_ptof"
    NOT_PTOF = "not_ptof"
    TOO_SHORT = "too_short"
    CORRUPTED = "corrupted"
    AMBIGUOUS = "ambiguous"
    DUPLICATE = "duplicate"


@dataclass
class ValidationReport:
    """Report dettagliato validazione"""
    file_path: str
    file_name: str
    result: str
    confidence: float
    phase: str  # 'heuristic', 'llm', 'manual'
    
    # Dettagli euristici
    page_count: int = 0
    char_count: int = 0
    ptof_keywords_found: int = 0
    exclusion_keywords_found: int = 0
    school_code_found: Optional[str] = None
    
    # Dettagli LLM (se usato)
    llm_analysis: Optional[str] = None
    llm_confidence: Optional[float] = None
    
    # Metadati
    timestamp: str = ""
    reason: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


class PTOFValidator:
    """
    Validatore progressivo per documenti PTOF.
    
    Fasi:
    1. Heuristics: analisi veloce basata su keywords e struttura
    2. LLM: analisi intelligente con Ollama (solo se ambiguo)
    3. Recovery: sistema per recuperare file scartati
    """
    
    # Keywords che indicano un PTOF
    PTOF_KEYWORDS = [
        "piano triennale",
        "piano dell'offerta formativa",
        "offerta formativa",
        "ptof",
        "p.t.o.f",
        "triennio",
        "curricolo",
        "curricolo verticale",
        "rav",
        "piano di miglioramento",
        "pdm",
        "mission",
        "vision",
        "organigramma",
        "funzionigramma",
        "organico",
        "docenti",
        "ata",
        "invalsi",
        "competenze",
        "obiettivi formativi",
        "ampliamento offerta",
        "pcto",
        "alternanza scuola",
        "inclusione",
        "bes",
        "dsa",
        "valutazione",
        "certificazione competenze",
        "orientamento",
        "continuità",
        "atto di indirizzo",
        "profilo educativo",
        "indirizzi di studio",
        "piano di formazione",
        "pnsd",
        "piano digitale",
        "animatore digitale",
        "formazione docenti",
        "fabbisogno",
        "risorse umane",
        "infrastrutture",
        "laboratori",
    ]
    PTOF_KEYWORDS_LOWER = [kw.lower() for kw in PTOF_KEYWORDS]
    
    # Keywords che indicano NON è un PTOF
    EXCLUSION_KEYWORDS = [
        "circolare n.",
        "circolare n°",
        "prot. n.",
        "protocollo n.",
        "oggetto:",
        "ai genitori",
        "alle famiglie",
        "verbale",
        "delibera n.",
        "delibera n°",
        "convocazione",
        "modulistica",
        "modulo di",
        "domanda di",
        "richiesta di",
        "autorizzazione",
        "liberatoria",
        "consenso informato",
        "iscrizione",
        "regolamento d'istituto",
        "regolamento disciplinare",
        "carta dei servizi",
        "patto educativo",
        "calendario scolastico",
        "orario delle lezioni",
        "graduatoria",
        "bando",
        "avviso pubblico",
        "determina",
        "decreto",
    ]
    EXCLUSION_KEYWORDS_LOWER = [kw.lower() for kw in EXCLUSION_KEYWORDS]

    STRONG_PTOF_KEYWORDS = [
        "piano triennale dell'offerta formativa",
        "piano triennale",
        "offerta formativa",
        "ptof",
        "p.t.o.f",
    ]
    STRONG_PTOF_KEYWORDS_LOWER = [kw.lower() for kw in STRONG_PTOF_KEYWORDS]
    
    # Keywords forti che indicano SICURAMENTE NON è un PTOF
    STRONG_EXCLUSION_KEYWORDS = [
        "bilancio sociale",
        "rapporto di autovalutazione",
        "rendicontazione sociale",
        "programma annuale",
        "conto consuntivo",
        "piano annuale inclusione",
        "bilancio preventivo",
        "rendiconto finanziario",
        "conto economico",
        "stato patrimoniale",
        "relazione accompagnatoria",
        "piano educativo individualizzato",  # PEI
        "piano didattico personalizzato",    # PDP
    ]
    STRONG_EXCLUSION_KEYWORDS_LOWER = [kw.lower() for kw in STRONG_EXCLUSION_KEYWORDS]
    
    # Pattern nel filename che indicano NON è un PTOF (se "ptof" non è presente)
    EXCLUSION_FILENAME_PATTERNS = [
        "bilancio", "rav_", "rav-", "rav2", "rav1", 
        "pdm_", "pdm-", "pdm2", "pdm1",
        "pai_", "pai-", "pai2", "pai1",
        "rendicont", "consuntiv", "preventiv",
        "regolamento", "circolare", "verbale",
        "delibera", "pei_", "pdp_", "allegato",
        "modulo", "domanda", "iscrizione",
    ]
    
    # Sezioni tipiche che un PTOF dovrebbe avere (almeno 3)
    PTOF_STRUCTURE_KEYWORDS = [
        "analisi del contesto",
        "le scelte strategiche",
        "l'offerta formativa",
        "organizzazione",
        "monitoraggio",
        "curricolo",
        "priorità strategiche",
        "fabbisogno",
    ]
    PTOF_STRUCTURE_KEYWORDS_LOWER = [kw.lower() for kw in PTOF_STRUCTURE_KEYWORDS]

    # Indizi tipici di documenti amministrativi (circolari/avvisi) nelle prime pagine
    ADMIN_HEADER_HINTS = [
        "oggetto:",
        "circolare",
        "comunicazione",
        "avviso",
        "convocazione",
        "verbale",
        "delibera",
        "ordine del giorno",
        "odg",
        "destinatari",
        "ai genitori",
        "alle famiglie",
        "al personale",
        "alunni",
        "docenti",
        "ata",
        "dsga",
        "dirigente scolastico",
    ]
    ADMIN_HEADER_HINTS_LOWER = [kw.lower() for kw in ADMIN_HEADER_HINTS]
    
    OK_SUFFIXES = ("_ok", "-ok", " ok")
    _SCHOOL_CODE_REGEX = re.compile(r'\b([A-Z]{2}[A-Z]{2}\d{6}[A-Z]?)\b', re.IGNORECASE)
    _SCHOOL_CODE_PATTERNS = [
        re.compile(r'codice\s*meccanografico[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})', re.IGNORECASE),
        re.compile(r'cod\.?\s*mecc\.?[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})', re.IGNORECASE),
        _SCHOOL_CODE_REGEX,
    ]
    _TEMPLATE_INSERIRE_RE = re.compile(r'\[inserire|inserire qui|\(inserire|\<inserire')
    _TEMPLATE_DOTS_RE = re.compile(r'(\.{4,}|…{2,}|_{4,})')
    _PROTOCOLLO_RE = re.compile(r'\bprot\.?\s*n\.?\s*\d+', re.IGNORECASE)
    _HEADER_SLICE_LEN = 2000
    _PTOF_TITLE_PATTERNS = [
        re.compile(r'\bpiano\s+triennale\s+(dell[\'’]?\s*)?offerta\s+formativa\b', re.IGNORECASE),
    ]
    
    def __init__(self, ollama_url: str = None, ollama_model: str = None, timeout: int = 60):
        """Inizializza il validatore."""
        self.ollama_url = ollama_url or OLLAMA_URL
        self.ollama_model = ollama_model or OLLAMA_MODEL
        self.timeout = int(timeout) if timeout else 60
        self.allowlist = self._load_allowlist()
        self.allowlist_norm = {item.lower() for item in self.allowlist}
        
        # Crea directory
        for d in [DISCARDED_NOT_PTOF, DISCARDED_TOO_SHORT, DISCARDED_CORRUPTED, DISCARDED_TO_CHECK]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Carica log recuperi
        self.recovery_log = self._load_recovery_log()
        
        logger.info(f"🔍 PTOFValidator inizializzato")
        logger.info(f"   Ollama: {self.ollama_url}")
        logger.info(f"   Modello: {self.ollama_model}")
        logger.info(f"   Timeout: {self.timeout}s")
    
    def _load_recovery_log(self) -> dict:
        """Carica log dei recuperi."""
        if RECOVERY_LOG.exists():
            try:
                with open(RECOVERY_LOG, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"recovered": [], "discarded": []}
    
    def _save_recovery_log(self):
        """Salva log dei recuperi."""
        with open(RECOVERY_LOG, 'w') as f:
            json.dump(self.recovery_log, f, ensure_ascii=False, indent=2)

    def _load_allowlist(self) -> set:
        """Carica allowlist per forzare l'accettazione di file PTOF."""
        if not ALLOWLIST_FILE.exists():
            return set()
        items = set()
        for line in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.add(line)
        return items
    
    def _extract_text_from_pdf(self, pdf_path: Path, max_pages: int = 10) -> Tuple[str, int]:
        """
        Estrae testo dalle prime N pagine del PDF.
        
        Returns:
            (testo_estratto, numero_pagine_totali)
        """
        try:
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            
            text_parts: List[str] = []
            for i, page in enumerate(reader.pages):
                if i >= max_pages:
                    break
                try:
                    extracted = page.extract_text() or ""
                    if extracted:
                        text_parts.append(extracted)
                except Exception:
                    pass

            text = "".join(text_parts)
            return text.strip(), total_pages
            
        except Exception as e:
            logger.error(f"❌ Errore lettura PDF {pdf_path.name}: {e}")
            return "", 0
    
    def _count_keywords(self, text: str, keywords: List[str], text_lower: Optional[str] = None) -> int:
        """Conta quante keywords sono presenti nel testo."""
        text_lower = text_lower if text_lower is not None else text.lower()
        count = 0
        for kw in keywords:
            if kw in text_lower:
                count += 1
        return count
    
    def _extract_school_code(self, text: str) -> Optional[str]:
        """Estrae codice meccanografico dal testo."""
        for pattern in self._SCHOOL_CODE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper()
        return None

    def _extract_school_code_from_name(self, name: str) -> Optional[str]:
        match = self._SCHOOL_CODE_REGEX.search(name)
        if match:
            return match.group(1).upper()
        return None

    def _force_accept_reason(self, pdf_path: Path, text: str = "") -> Optional[str]:
        """Ritorna motivo di accettazione forzata se attivo."""
        stem_lower = pdf_path.stem.lower()
        for suffix in self.OK_SUFFIXES:
            if stem_lower.endswith(suffix):
                return f"Override filename suffix ({suffix})"

        if not self.allowlist_norm:
            return None

        name_lower = pdf_path.name.lower()
        if name_lower in self.allowlist_norm or stem_lower in self.allowlist_norm:
            return "Override allowlist (nome file)"

        code_from_name = self._extract_school_code_from_name(pdf_path.name)
        if code_from_name and code_from_name.lower() in self.allowlist_norm:
            return "Override allowlist (codice)"

        if text:
            code_from_text = self._extract_school_code(text)
            if code_from_text and code_from_text.lower() in self.allowlist_norm:
                return "Override allowlist (codice nel testo)"

        return None

    def _is_ok_filename(self, name: str) -> bool:
        stem_lower = Path(name).stem.lower()
        return any(stem_lower.endswith(suffix) for suffix in self.OK_SUFFIXES)
    
    def _quick_filename_check(self, pdf_path: Path) -> Tuple[Optional[str], float, str]:
        """
        Pre-validazione veloce basata sul nome del file.
        
        Returns:
            (result, confidence, reason) se decidibile
            (None, 0, "") se ambiguo e serve analisi testo
        """
        name_lower = pdf_path.name.lower()
        stem_lower = pdf_path.stem.lower()
        
        # Se contiene "ptof" nel nome, probabilmente è un PTOF
        if "ptof" in name_lower or "pof_" in name_lower:
            return ("likely_ptof", 0.7, "Filename contiene PTOF")
        
        # Controlla pattern di esclusione nel filename
        for pattern in self.EXCLUSION_FILENAME_PATTERNS:
            if pattern in name_lower:
                # Ma solo se "ptof" NON è nel nome
                if "ptof" not in name_lower:
                    return (ValidationResult.NOT_PTOF.value, 0.80, 
                            f"Filename contiene '{pattern}' (non è un PTOF)")
        
        return (None, 0.5, "Filename ambiguo")
    
    def _check_is_template(self, text: str, text_lower: Optional[str] = None) -> Tuple[bool, str]:
        """Rileva se il documento è un template non compilato."""
        text_lower = text_lower if text_lower is not None else text.lower()
        
        # 1. Check "Nome Scuola" repetition
        nome_scuola_count = text_lower.count("nome scuola")
        if nome_scuola_count > 3:
            return True, f"Template vuoto: 'Nome Scuola' appare {nome_scuola_count} volte"
            
        # 2. Check "Inserire" placeholders
        inserire_count = len(self._TEMPLATE_INSERIRE_RE.findall(text_lower))
        if inserire_count > 3:
            return True, f"Template vuoto: placeholder 'Inserire' rilevati ({inserire_count})"
            
        # 3. Check dots/ellipsis density (............... or _________)
        # Usa range [4,] per catturare sequenze lunghe
        # Usa anche \u2026 per ellipsis
        dots_matches = len(self._TEMPLATE_DOTS_RE.findall(text))
        if dots_matches > 30: 
             return True, f"Template vuoto: troppi campi non compilati ({dots_matches})"
             
        # 4. Check "(esempio)"
        esempio_count = text_lower.count("(esempio)")
        if esempio_count > 3:
            return True, f"Template vuoto: diciture '(esempio)' rilevate"
            
        return False, ""

    def _check_strong_exclusions(self, text: str, text_lower: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verifica se il testo contiene keywords che escludono SICURAMENTE un PTOF.
        
        Returns:
            (is_excluded, reason)
        """
        text_lower = text_lower if text_lower is not None else text.lower()
        found = []
        for kw in self.STRONG_EXCLUSION_KEYWORDS_LOWER:
            if kw in text_lower:
                found.append(kw)
        
        if len(found) >= 2:
            return True, f"Trovate keywords esclusione forti: {', '.join(found[:3])}"
        
        # Se trovata 1 keyword forte E nessuna keyword PTOF forte, escludi
        if len(found) >= 1:
            strong_ptof = self._count_keywords(text, self.STRONG_PTOF_KEYWORDS_LOWER, text_lower=text_lower)
            if strong_ptof == 0:
                return True, f"Trovata keyword esclusione '{found[0]}' senza keywords PTOF"
        
        return False, ""

    def _is_duplicate_hash(self, pdf_path: Path) -> bool:
        """Controlla se l'hash del file esiste già nel registro come VALID_PTOF."""
        try:
            # Calcola hash corrente
            current_hash = _compute_file_hash(pdf_path)
            
            # Carica registro
            registry = load_validation_registry()
            
            # Cerca hash nel registro
            for filename, entry in registry.get("validated_files", {}).items():
                if entry.get("hash") == current_hash:
                    # Se è lo stesso file (stesso nome), non è un duplicato "di un altro"
                    if filename == pdf_path.name:
                        continue
                        
                    # Se l'entry trovata era valida, allora questo è un duplicato
                    if entry.get("result") == ValidationResult.VALID_PTOF.value:
                        return True
                        
            return False
        except Exception as e:
            logger.error(f"Errore check duplicati hash: {e}")
            return False
        
        return False, ""
    
    def _check_document_structure(self, text: str) -> Tuple[int, List[str]]:
        """
        Verifica la presenza di sezioni tipiche di un PTOF.
        
        Returns:
            (count, found_sections)
        """
        text_lower = text.lower()
        found = []
        for section in self.PTOF_STRUCTURE_KEYWORDS_LOWER:
            if section in text_lower:
                found.append(section)
        return len(found), found

    def _check_admin_document(self, text: str, text_lower: Optional[str] = None) -> Tuple[bool, str]:
        """Rileva documenti amministrativi (circolari/avvisi) da header e segnali."""
        text_lower = text_lower if text_lower is not None else text.lower()
        strong_ptof = self._count_keywords(text, self.STRONG_PTOF_KEYWORDS_LOWER, text_lower=text_lower)
        if strong_ptof > 0:
            return False, ""

        header = text_lower[: self._HEADER_SLICE_LEN]
        header_hits = []
        for kw in self.ADMIN_HEADER_HINTS_LOWER:
            if kw in header:
                header_hits.append(kw)
        if self._PROTOCOLLO_RE.search(header):
            header_hits.append("prot. n.")

        exclusion_hits = []
        for kw in self.EXCLUSION_KEYWORDS_LOWER:
            if kw in text_lower:
                exclusion_hits.append(kw)

        if len(header_hits) >= 2 and len(exclusion_hits) >= 3:
            return True, f"Documento amministrativo (header: {', '.join(header_hits[:3])})"

        if len(exclusion_hits) >= 8 and len(header_hits) >= 1:
            return True, f"Molti indizi non-PTOF ({len(exclusion_hits)})"

        return False, ""

    def _is_code_already_analyzed(self, school_code: str) -> bool:
        """Verifica se esiste già un'analisi per il codice scuola."""
        if not school_code:
            return False
        try:
            analysis_candidates = [
                ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json",
                ANALYSIS_DIR / f"{school_code}_analysis.json",
            ]
            if any(path.exists() for path in analysis_candidates):
                return True
        except Exception:
            pass

        try:
            from src.utils.analysis_registry import load_registry
            registry = load_registry()
            entry = registry.get("analyzed_files", {}).get(school_code)
            if entry:
                json_path = Path(entry.get("json_path", ""))
                if json_path.exists():
                    return True
        except Exception:
            return False

        return False

    def _rename_pdf_if_code_mismatch(self, pdf_path: Path, school_code: str) -> Path:
        """Rinomina il PDF se il codice non è presente nel nome file."""
        if not pdf_path or not pdf_path.exists() or not school_code:
            return pdf_path

    def _move_to_check(self, pdf_path: Path, reason: str) -> Optional[Path]:
        """Sposta il PDF nella cartella da controllare."""
        if not pdf_path or not pdf_path.exists():
            return None
        dest_path = DISCARDED_TO_CHECK / pdf_path.name
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = DISCARDED_TO_CHECK / f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"
        try:
            shutil.move(str(pdf_path), str(dest_path))
            logger.info(f"   🧾 Da controllare: {pdf_path.name} ({reason})")
            return dest_path
        except Exception as exc:
            logger.warning(f"   ⚠️ Errore spostamento da controllare {pdf_path.name}: {exc}")
            return None
        if school_code.upper() in pdf_path.stem.upper():
            return pdf_path
        target = pdf_path.with_name(f"{school_code}_PTOF{pdf_path.suffix}")
        if target.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = pdf_path.with_name(f"{school_code}_PTOF_{timestamp}{pdf_path.suffix}")
        try:
            pdf_path.rename(target)
            logger.info(f"   ✏️ Rinominato: {pdf_path.name} → {target.name}")
            return target
        except Exception as exc:
            logger.warning(f"   ⚠️ Errore rinomina {pdf_path.name}: {exc}")
            return pdf_path

    def _has_ptof_title(self, text: str) -> bool:
        """Richiede una riga titolo che contenga la dicitura PTOF (varianti comuni) nelle prime righe."""
        header = text[: self._HEADER_SLICE_LEN]
        for line in header.splitlines():
            line_clean = " ".join(line.strip().split())
            if not line_clean:
                continue
            line_clean = line_clean.strip(":-–—|•*·")
            for pattern in self._PTOF_TITLE_PATTERNS:
                if pattern.search(line_clean):
                    return True
        return False
    
    def _heuristic_validation(self, text: str, page_count: int, text_lower: Optional[str] = None) -> Tuple[float, ValidationReport]:
        """
        Fase 1: Validazione euristica veloce.
        
        Returns:
            (confidence, report_parziale)
        """
        # Conta keywords
        text_lower = text_lower if text_lower is not None else text.lower()
        ptof_count = self._count_keywords(text, self.PTOF_KEYWORDS_LOWER, text_lower=text_lower)
        strong_count = self._count_keywords(text, self.STRONG_PTOF_KEYWORDS_LOWER, text_lower=text_lower)
        exclusion_count = self._count_keywords(text, self.EXCLUSION_KEYWORDS_LOWER, text_lower=text_lower)
        school_code = self._extract_school_code(text)
        char_count = len(text)
        
        # Calcola confidence
        confidence = 0.0
        
        # Fattori positivi
        if ptof_count >= 12:
            confidence += 0.4
        elif ptof_count >= 6:
            confidence += 0.25
        elif ptof_count >= 2:
            confidence += 0.12

        if strong_count > 0:
            confidence += 0.2
        
        if page_count >= 50:
            confidence += 0.3
        elif page_count >= 30:
            confidence += 0.25
        elif page_count >= 20:
            confidence += 0.2
        elif page_count >= 10:
            confidence += 0.15
        elif page_count >= MIN_PAGES:
            confidence += 0.1
        
        if school_code:
            confidence += 0.15
        
        if char_count >= 50000:
            confidence += 0.1
        elif char_count >= 20000:
            confidence += 0.05
        
        # Fattori negativi
        if exclusion_count >= 5:
            confidence -= 0.35
        elif exclusion_count >= 2:
            confidence -= 0.1 if ptof_count >= 6 else 0.2
        
        if page_count < MIN_PAGES:
            confidence -= 0.3
        
        # Normalizza
        confidence = max(0.0, min(1.0, confidence))
        
        report = ValidationReport(
            file_path="",
            file_name="",
            result=ValidationResult.AMBIGUOUS.value,
            confidence=confidence,
            phase="heuristic",
            page_count=page_count,
            char_count=char_count,
            ptof_keywords_found=ptof_count,
            exclusion_keywords_found=exclusion_count,
            school_code_found=school_code
        )
        
        return confidence, report
    
    def _llm_validation(self, text: str, heuristic_report: ValidationReport) -> Tuple[float, str]:
        """
        Fase 2: Validazione con Ollama per casi ambigui.
        
        Returns:
            (confidence, analisi_testuale)
        """
        # Prendi solo i primi 5000 caratteri per velocità
        sample_text = text[:5000]
        
        prompt = f"""/no_think
Sei un esperto di documenti scolastici italiani. Analizza questo testo e determina se è un PTOF (Piano Triennale dell'Offerta Formativa).

Un PTOF valido deve contenere:
- Piano triennale dell'offerta formativa
- Informazioni su curricolo, didattica, organizzazione
- Riferimenti a RAV, PDM, obiettivi formativi
- Struttura articolata (non una circolare o modulo)

NON è un PTOF:
- Circolari, comunicazioni
- Moduli, domande, liberatorie
- Regolamenti, verbali
- Documenti brevi o frammentari

TESTO DA ANALIZZARE:
---
{sample_text}
---

INFORMAZIONI EURISTICHE:
- Pagine: {heuristic_report.page_count}
- Keywords PTOF trovate: {heuristic_report.ptof_keywords_found}
- Keywords esclusione trovate: {heuristic_report.exclusion_keywords_found}
- Codice scuola trovato: {heuristic_report.school_code_found or 'No'}

Rispondi SOLO in questo formato JSON:
{{
  "is_ptof": true/false,
  "confidence": 0.0-1.0,
  "reason": "breve spiegazione",
  "document_type": "PTOF/circolare/modulo/altro"
}}"""

        try:
            response = requests.post(
                f"{self.ollama_url}",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 300}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                # Log raw response per debug
                logger.info(f"   🤖 LLM Raw: {result[:500]}..." if len(result) > 500 else f"   🤖 LLM Raw: {result}")
                
                try:
                    # Parse JSON dalla risposta
                    data = json.loads(result)
                    confidence = float(data.get("confidence", 0.5))
                    is_ptof = data.get("is_ptof", False)
                    reason = data.get("reason", "")
                    doc_type = data.get("document_type", "sconosciuto")
                    
                    # Aggiusta confidence basata su is_ptof
                    if not is_ptof:
                        confidence = 1.0 - confidence  # Inverti per "not ptof"
                    
                    analysis = f"{doc_type}: {reason}"
                    return confidence, analysis
                    
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Risposta LLM non è JSON valido")
                    return 0.5, result[:200]
            else:
                logger.error(f"❌ Errore Ollama: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Errore connessione Ollama: {e}")
        
        return 0.5, "Errore analisi LLM"
    
    def validate(self, pdf_path: Path, use_llm_if_ambiguous: bool = True, force_llm: bool = False, check_duplicates: bool = True, registry: Optional[Dict] = None) -> ValidationReport:
        """
        Valida un documento PDF in modo progressivo.
        
        Args:
            pdf_path: Percorso al file PDF
            use_llm_if_ambiguous: Se True, usa LLM per casi ambigui
            force_llm: Se True, forza l'uso dell'LLM anche se l'euristica è positiva
            check_duplicates: Se True, controlla se il file è già stato validato (hash identico)
            
        Returns:
            ValidationReport con risultato e dettagli
        """
        pdf_path = Path(pdf_path)
        logger.info(f"🔍 Validazione: {pdf_path.name}")
        
        # Fase 0: Verifica file esiste
        if not pdf_path.exists():
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=1.0,
                phase="check",
                reason="File non trovato"
            )

        # Fase 0.1: Check Duplicati (Hash check)
        if check_duplicates:
            is_dup, prev_result = is_already_validated(pdf_path, registry)
            if is_dup and prev_result == ValidationResult.VALID_PTOF.value:
                logger.info(f"   ⏭️ Duplicato rilevato (hash identico a file validato)")
                return ValidationReport(
                    file_path=str(pdf_path),
                    file_name=pdf_path.name,
                    result=ValidationResult.DUPLICATE.value,
                    confidence=1.0,
                    phase="duplicate_check",
                    reason="File identico già validato in precedenza"
                )
        
        # Fase 0.4: Controlla codice nel filename (prima di aprire il PDF)
        code_from_name = self._extract_school_code_from_name(pdf_path.name)
        if code_from_name and self._is_code_already_analyzed(code_from_name):
            logger.info(f"   ⛔ Codice {code_from_name} già analizzato (filename): elimino file")
            try:
                pdf_path.unlink()
            except Exception as exc:
                logger.warning(f"   ⚠️ Impossibile eliminare {pdf_path.name}: {exc}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=1.0,
                phase="already_analyzed_code",
                reason=f"Codice {code_from_name} già analizzato"
            )

        # Fase 0.5: Quick filename check (PRIMA di aprire il PDF!)
        fn_result, fn_confidence, fn_reason = self._quick_filename_check(pdf_path)
        if fn_result == ValidationResult.NOT_PTOF.value:
            logger.info(f"   ⚡ Quick reject (filename): {fn_reason}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=fn_confidence,
                phase="filename_check",
                reason=fn_reason
            )
        
        force_reason = self._force_accept_reason(pdf_path)

        # Fase 1: Estrai testo
        text, page_count = self._extract_text_from_pdf(pdf_path)
        
        if page_count == 0:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=1.0,
                phase="extraction",
                reason="Impossibile leggere PDF"
            )

        school_code = self._extract_school_code(text) or code_from_name
        if not school_code:
            self._move_to_check(pdf_path, "Codice non trovato")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=0.95,
                phase="missing_code",
                page_count=page_count,
                char_count=len(text),
                reason="Codice meccanografico non trovato"
            )

        if self._is_code_already_analyzed(school_code):
            logger.info(f"   ⛔ Codice {school_code} già analizzato: elimino file")
            try:
                pdf_path.unlink()
            except Exception as exc:
                logger.warning(f"   ⚠️ Impossibile eliminare {pdf_path.name}: {exc}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=1.0,
                phase="already_analyzed_code",
                page_count=page_count,
                char_count=len(text),
                school_code_found=school_code,
                reason=f"Codice {school_code} già analizzato"
            )

        pdf_path = self._rename_pdf_if_code_mismatch(pdf_path, school_code)

        if not force_reason:
            force_reason = self._force_accept_reason(pdf_path, text=text)

        if force_reason:
            school_code = self._extract_school_code(text)
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.VALID_PTOF.value,
                confidence=1.0,
                phase="override",
                page_count=page_count,
                char_count=len(text),
                school_code_found=school_code,
                reason=force_reason
            )

        # Fase 1.4: Richiede titolo PTOF esatto
        if not self._has_ptof_title(text):
            logger.info("   ❌ Titolo PTOF non trovato in header")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=0.95,
                phase="title_check",
                page_count=page_count,
                char_count=len(text),
                reason="Titolo PTOF non trovato in header"
            )

        # Fase 1.5: Controlla esclusioni forti (PRIMA dell'analisi euristica completa)
        text_lower = text.lower()
        is_excluded, exclusion_reason = self._check_strong_exclusions(text, text_lower=text_lower)
        if is_excluded:
            logger.info(f"   ⚡ Strong exclusion: {exclusion_reason}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=0.85,
                phase="strong_exclusion",
                page_count=page_count,
                char_count=len(text),
                reason=exclusion_reason
            )

        # Fase 1.6: Controlla Template (PRIMA dell'analisi euristica completa)
        is_template, template_reason = self._check_is_template(text, text_lower=text_lower)
        if is_template:
            logger.info(f"   ⚠️ Template rejected: {template_reason}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=0.95,
                phase="template_check",
                page_count=page_count,
                char_count=len(text),
                reason=template_reason
            )

        # Fase 1.7: Controlla documenti amministrativi (circolari/avvisi)
        is_admin_doc, admin_reason = self._check_admin_document(text, text_lower=text_lower)
        if is_admin_doc:
            logger.info(f"   ⚡ Admin doc: {admin_reason}")
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=0.9,
                phase="admin_doc_check",
                page_count=page_count,
                char_count=len(text),
                reason=admin_reason
            )

        if page_count < MIN_PAGES:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.TOO_SHORT.value,
                confidence=0.9,
                phase="heuristic",
                page_count=page_count,
                char_count=len(text),
                reason=f"Solo {page_count} pagine (minimo: {MIN_PAGES})"
            )
        
        if len(text) < MIN_CHARS:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=0.8,
                phase="extraction",
                page_count=page_count,
                char_count=len(text),
                reason=f"Testo insufficiente: {len(text)} caratteri"
            )
            
        # Fase 2: Analisi euristica
        h_confidence, report = self._heuristic_validation(text, page_count, text_lower=text_lower)
        report.file_path = str(pdf_path)
        report.file_name = pdf_path.name
        
        # Se force_llm è attivo, abbassiamo artificialmente la confidenza euristica per forzare fase successiva
        # A meno che non sia già molto decisamente NOT_PTOF (es. confidence < 0.2)
        if force_llm and h_confidence >= 0.2:
             logger.info(f"   ⚠️ Force LLM attivo: ignoro confidenza euristica {h_confidence:.2f}")
             h_confidence = 0.5  # Valore ambiguo che forza LLM
             report.confidence = h_confidence # Update report's confidence
             
        logger.info(f"   📊 Heuristic confidence: {h_confidence:.2f}")
        logger.info(f"      PTOF keywords: {report.ptof_keywords_found}")
        logger.info(f"      Exclusion keywords: {report.exclusion_keywords_found}")
        
        # Decisione basata su heuristics
        if h_confidence >= CONFIDENCE_THRESHOLD_HEURISTIC:
            report.result = ValidationResult.VALID_PTOF.value
            report.reason = f"Alta confidenza euristica ({h_confidence:.2f})"
            logger.info(f"   ✅ PTOF VALIDO (heuristic: {h_confidence:.2f})")
            return report
        
        if h_confidence <= 0.15:
            report.result = ValidationResult.NOT_PTOF.value
            report.reason = f"Bassa confidenza euristica ({h_confidence:.2f})"
            logger.info(f"   ❌ NON PTOF (heuristic: {h_confidence:.2f})")
            return report
        
        # Fase 3: LLM per casi ambigui
        if use_llm_if_ambiguous:
            logger.info(f"   🤖 Caso ambiguo, analisi LLM...")
            llm_confidence, llm_analysis = self._llm_validation(text, report)
            
            report.phase = "llm"
            report.llm_analysis = llm_analysis
            report.llm_confidence = llm_confidence
            
            # Combina confidence (media pesata)
            combined = (h_confidence * 0.4) + (llm_confidence * 0.6)
            report.confidence = combined
            
            logger.info(f"   📊 LLM confidence: {llm_confidence:.2f}")
            logger.info(f"   📊 Combined: {combined:.2f}")
            
            if combined >= CONFIDENCE_THRESHOLD_LLM:
                report.result = ValidationResult.VALID_PTOF.value
                report.reason = f"Validato da LLM ({llm_analysis})"
                logger.info(f"   ✅ PTOF VALIDO (LLM)")
            else:
                report.result = ValidationResult.NOT_PTOF.value
                report.reason = f"Rifiutato da LLM ({llm_analysis})"
                logger.info(f"   ❌ NON PTOF (LLM: {llm_analysis})")
        else:
            report.result = ValidationResult.AMBIGUOUS.value
            report.reason = "Richiede validazione manuale"
        
        return report
    
    def discard(self, pdf_path: Path, report: ValidationReport) -> Path:
        """
        Sposta un file nella directory appropriata di scarto.
        
        Returns:
            Path della destinazione
        """
        pdf_path = Path(pdf_path)
        
        # Determina directory destinazione
        if report.result == ValidationResult.TOO_SHORT.value:
            dest_dir = DISCARDED_TOO_SHORT
        elif report.result == ValidationResult.CORRUPTED.value:
            dest_dir = DISCARDED_CORRUPTED
        else:
            dest_dir = DISCARDED_NOT_PTOF
        
        dest_path = dest_dir / pdf_path.name
        
        # Evita sovrascrittura
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_dir / f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"
        
        # Sposta file
        shutil.move(str(pdf_path), str(dest_path))
        logger.info(f"   🗑️ Spostato in: {dest_path.relative_to(BASE_DIR)}")
        
        # Salva nel log per recovery
        self.recovery_log["discarded"].append({
            "original_path": str(pdf_path),
            "discarded_path": str(dest_path),
            "report": report.to_dict(),
            "timestamp": datetime.now().isoformat()
        })
        self._save_recovery_log()
        
        return dest_path
    
    def validate_batch(self, pdf_dir: Path, move_invalid: bool = True, use_registry: bool = True, force_llm: bool = False, check_duplicates: bool = True) -> Dict:
        """
        Valida tutti i PDF in una directory.
        
        Args:
            pdf_dir: Directory contenente i PDF
            move_invalid: Se True, sposta i file non validi
            use_registry: Se True, salta i file già validati
            force_llm: Se True, forza l'uso dell'LLM anche se l'euristica è positiva
            check_duplicates: Se True, controlla duplicati hash
            
        Returns:
            Dizionario con statistiche e reports
        """
        pdf_dir = Path(pdf_dir)
        results = {
            "valid": [],
            "not_ptof": [],
            "too_short": [],
            "corrupted": [],
            "ambiguous": [],
            "skipped": [],  # File già validati
            "stats": {}
        }
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        logger.info(f"📂 Validazione batch: {len(pdf_files)} PDF in {pdf_dir}")
        
        # Carica registro validazione
        validation_registry = load_validation_registry() if use_registry else None
        skipped_count = 0
        
        for pdf_path in pdf_files:
            # Controlla se già validato
            if use_registry and validation_registry:
                already_validated, cached_result = is_already_validated(pdf_path, validation_registry)
                if already_validated:
                    skipped_count += 1
                    # Aggiungi al risultato appropriato senza rivalidare
                    if cached_result == ValidationResult.VALID_PTOF.value:
                        results["skipped"].append({"file": pdf_path.name, "result": cached_result})
                    # I file non validi dovrebbero già essere stati spostati
                    continue
            
            report = self.validate(
                pdf_path,
                force_llm=force_llm,
                check_duplicates=check_duplicates and not use_registry,
                registry=validation_registry,
            )
            
            # Registra la validazione
            if use_registry:
                validation_registry = register_validation(
                    pdf_path, report.result, report.confidence, 
                    school_code=report.school_code_found,
                    registry=validation_registry, auto_save=False
                )
            
            if report.result == ValidationResult.VALID_PTOF.value:
                results["valid"].append(report)
            elif report.result == ValidationResult.NOT_PTOF.value:
                results["not_ptof"].append(report)
                if move_invalid and pdf_path.exists():
                    self.discard(pdf_path, report)
                elif move_invalid:
                    logger.info(f"   ⚠️ File già rimosso: {pdf_path.name}")
            elif report.result == ValidationResult.TOO_SHORT.value:
                results["too_short"].append(report)
                if move_invalid and pdf_path.exists():
                    self.discard(pdf_path, report)
                elif move_invalid:
                    logger.info(f"   ⚠️ File già rimosso: {pdf_path.name}")
            elif report.result == ValidationResult.CORRUPTED.value:
                results["corrupted"].append(report)
                if move_invalid and pdf_path.exists():
                    self.discard(pdf_path, report)
                elif move_invalid:
                    logger.info(f"   ⚠️ File già rimosso: {pdf_path.name}")
            else:
                results["ambiguous"].append(report)
        
        # Salva registro una volta alla fine
        if use_registry and validation_registry:
            save_validation_registry(validation_registry)
        
        # Statistiche
        total = len(pdf_files)
        results["stats"] = {
            "total": total,
            "valid": len(results["valid"]),
            "not_ptof": len(results["not_ptof"]),
            "too_short": len(results["too_short"]),
            "corrupted": len(results["corrupted"]),
            "duplicates": len(results.get("duplicates", [])),
            "ambiguous": len(results["ambiguous"]),
            "skipped": skipped_count,
            "skipped_already_valid": skipped_count,  # alias più esplicito
            "valid_rate": len(results["valid"]) / total if total > 0 else 0
        }
        
        logger.info(f"📊 Risultati batch:")
        if skipped_count > 0:
            logger.info(f"   ⏭️ Saltati (già validati): {skipped_count}")
        logger.info(f"   ✅ Validi: {results['stats']['valid']}")
        logger.info(f"   ❌ Non PTOF: {results['stats']['not_ptof']}")
        logger.info(f"   📄 Troppo corti: {results['stats']['too_short']}")
        logger.info(f"   🗑️ Duplicati: {results['stats']['duplicates']}")
        logger.info(f"   💔 Corrotti: {results['stats']['corrupted']}")
        logger.info(f"   💔 Corrotti: {results['stats']['corrupted']}")
        logger.info(f"   ❓ Ambigui: {results['stats']['ambiguous']}")
        
        # Statistiche Scuole Uniche e Mancanti
        if use_registry and validation_registry:
            unique_schools = count_unique_schools(validation_registry)
            logger.info(f"   🏫 Scuole uniche validate: {unique_schools}")
            
            if SchoolDatabase:
                try:
                    # Inizializza DB solo se serve
                    if not SchoolDatabase._loaded:
                         SchoolDatabase()
                    
                    total_db = len(SchoolDatabase()._data)
                    missing = max(0, total_db - unique_schools)
                    logger.info(f"   📉 Mancanti (vs DB): {missing} (su {total_db})")
                except Exception as e:
                    logger.debug(f"Impossibile calcolare mancanti: {e}")
        
        return results
    
    # =====================================================
    # SISTEMA DI RECOVERY
    # =====================================================
    
    def list_discarded(self) -> List[Dict]:
        """
        Lista tutti i file scartati che possono essere recuperati.
        
        Returns:
            Lista di dizionari con info sui file scartati
        """
        discarded = []
        
        for category, dir_path in [
            ("not_ptof", DISCARDED_NOT_PTOF),
            ("too_short", DISCARDED_TOO_SHORT),
            ("corrupted", DISCARDED_CORRUPTED),
            ("da_controllare", DISCARDED_TO_CHECK),
        ]:
            for pdf in dir_path.glob("*.pdf"):
                # Cerca report nel log
                report_info = None
                for item in self.recovery_log.get("discarded", []):
                    if item.get("discarded_path") == str(pdf):
                        report_info = item
                        break
                
                discarded.append({
                    "path": str(pdf),
                    "name": pdf.name,
                    "category": category,
                    "report": report_info.get("report") if report_info else None,
                    "timestamp": report_info.get("timestamp") if report_info else None
                })
        
        return discarded
    
    def recover(self, discarded_path: Path, dest_dir: Path = None) -> Optional[Path]:
        """
        Recupera un file scartato, spostandolo nella directory di destinazione.
        
        Args:
            discarded_path: Path del file scartato
            dest_dir: Directory di destinazione (default: ptof_inbox)
            
        Returns:
            Path del file recuperato, o None se fallisce
        """
        discarded_path = Path(discarded_path)
        
        if not discarded_path.exists():
            logger.error(f"❌ File non trovato: {discarded_path}")
            return None
        
        dest_dir = dest_dir or (BASE_DIR / "ptof_inbox")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / discarded_path.name
        
        # Evita sovrascrittura
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_dir / f"{discarded_path.stem}_{timestamp}{discarded_path.suffix}"
        
        # Sposta file
        shutil.move(str(discarded_path), str(dest_path))
        
        # Aggiorna log
        self.recovery_log["recovered"].append({
            "original_discarded": str(discarded_path),
            "recovered_to": str(dest_path),
            "timestamp": datetime.now().isoformat()
        })
        self._save_recovery_log()
        
        logger.info(f"♻️ Recuperato: {discarded_path.name} → {dest_path.relative_to(BASE_DIR)}")
        return dest_path
    
    def recover_all(self, category: str = None, dest_dir: Path = None, only_ok: bool = False) -> List[Path]:
        """
        Recupera tutti i file scartati (opzionalmente filtrati per categoria).
        
        Args:
            category: 'not_ptof', 'too_short', 'corrupted' o None per tutti
            dest_dir: Directory di destinazione
            only_ok: Recupera solo file con suffisso _ok/-ok/ ok
            
        Returns:
            Lista dei path recuperati
        """
        discarded = self.list_discarded()
        
        if category:
            discarded = [d for d in discarded if d["category"] == category]
        if only_ok:
            discarded = [d for d in discarded if self._is_ok_filename(d["name"])]
        
        recovered = []
        for item in discarded:
            path = self.recover(Path(item["path"]), dest_dir)
            if path:
                recovered.append(path)
        
        logger.info(f"♻️ Recuperati {len(recovered)} file")
        return recovered


# =====================================================
# FUNZIONI HELPER
# =====================================================

def validate_inbox(move_invalid: bool = True, use_registry: bool = True, force_llm: bool = False, check_duplicates: bool = True) -> Dict:
    """
    Valida tutti i PDF in ptof_inbox/.
    Funzione di convenienza per uso da CLI.
    """
    validator = PTOFValidator()
    inbox_dir = BASE_DIR / "ptof_inbox"
    return validator.validate_batch(inbox_dir, move_invalid=move_invalid, use_registry=use_registry, force_llm=force_llm, check_duplicates=check_duplicates)


def show_discarded():
    """Mostra tutti i file scartati."""
    validator = PTOFValidator()
    discarded = validator.list_discarded()
    
    print(f"\n📂 FILE SCARTATI ({len(discarded)})")
    print("=" * 60)
    
    for item in discarded:
        cat = item["category"]
        name = item["name"]
        ts = item.get("timestamp", "N/A")[:10]
        report = item.get("report", {})
        reason = report.get("reason", "N/A") if report else "N/A"
        
        icon = {"not_ptof": "❌", "too_short": "📄", "corrupted": "💔", "da_controllare": "🧾"}.get(cat, "❓")
        print(f"  {icon} [{cat}] {name}")
        print(f"      Motivo: {reason}")
        print(f"      Data: {ts}")
        print()


def recover_file(filename: str) -> bool:
    """
    Recupera un file per nome.
    
    Args:
        filename: Nome del file da recuperare
        
    Returns:
        True se recuperato, False altrimenti
    """
    validator = PTOFValidator()
    discarded = validator.list_discarded()
    
    for item in discarded:
        if item["name"] == filename:
            result = validator.recover(Path(item["path"]))
            return result is not None
    
    print(f"❌ File non trovato: {filename}")
    return False


# =====================================================
# CLI
# =====================================================

if __name__ == "__main__":
    import argparse
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / 'ptof_validator.log', encoding='utf-8')
        ]
    )
    logger = logging.getLogger(__name__)

    # Sopprimi warning rumorosi di pypdf
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    
    parser = argparse.ArgumentParser(description="PTOFValidator - Validazione progressiva PTOF")
    parser.add_argument("action", choices=["validate", "validate-batch", "list", "recover"],
                       help="Azione da eseguire")
    parser.add_argument("target", nargs="?", help="File o directory target")
    parser.add_argument("--no-llm", action="store_true", help="Disabilita LLM per casi ambigui")
    parser.add_argument("--force-llm", action="store_true", help="Forza uso LLM anche se euristica positiva")
    parser.add_argument("--no-duplicates", action="store_true", help="Disabilita controllo duplicati (hash)")
    parser.add_argument("--dry-run", action="store_true", help="Non sposta i file (solo recover/validate-batch)")
    parser.add_argument("--no-move", action="store_true", help="Non sposta file non validi (solo validate-batch)")
    parser.add_argument("--no-registry", action="store_true", help="Ignora registro validazioni (solo validate-batch)")
    parser.add_argument("--category", "-c", choices=["not_ptof", "too_short", "corrupted", "da_controllare"],
                       help="Categoria per recover")
    parser.add_argument("--only-ok", action="store_true",
                       help="Recupera solo file con suffisso _ok/-ok/ ok")
    
    args = parser.parse_args()
    
    if args.action == "validate":
        if not args.target:
            print("❌ Specificare file target per validate")
            sys.exit(1)
            
        validator = PTOFValidator()
        report = validator.validate(
            Path(args.target), 
            use_llm_if_ambiguous=not args.no_llm,
            force_llm=args.force_llm,
            check_duplicates=not args.no_duplicates
        )
        print(f"\nRisultato: {report.result}")
        print(f"Confidence: {report.confidence:.2f}")
        print(f"Reason: {report.reason}")
        
    elif args.action == "validate-batch":
        target_dir = Path(args.target) if args.target else (BASE_DIR / "ptof_inbox")
        if not target_dir.exists():
            print(f"❌ Directory non trovata: {target_dir}")
            sys.exit(1)
            
        validator = PTOFValidator()
        results = validator.validate_batch(
            target_dir, 
            move_invalid=not args.no_move and not args.dry_run,
            use_registry=not args.no_registry,
            force_llm=args.force_llm,
            check_duplicates=not args.no_duplicates
        )
        
    elif args.action == "list":
        show_discarded()
        
    elif args.action == "recover":
        validator = PTOFValidator()
        if args.target:
            # Recupera file specifico
             recover_file(args.target)
        else:
            # Recupera tutti (con filtri opzionali)
            validator.recover_all(
                category=args.category, 
                only_ok=args.only_ok
            )
            validator.recover_all(
                category=args.category, 
                only_ok=args.only_ok
            )
