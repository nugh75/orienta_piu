#!/usr/bin/env python3
"""
PTOF Downloader - Scarica i PTOF dalle anagrafiche MIUR con campionamento stratificato
========================================================================================

Sorgenti dati:
- SCUANAGRAFESTAT: Scuole statali (~50k righe)
- SCUANAGRAFEPAR: Scuole paritarie (~11k righe)

Stratificazione supportata:
- Tipo scuola: statale vs paritaria
- Area geografica: NORD OVEST, NORD EST, CENTRO, SUD, ISOLE
- Provincia: metropolitana vs non metropolitana
- Grado istruzione: infanzia, primaria, sec. primo grado, sec. secondo grado

Strategie di download (in ordine di priorità):
1. API Scuola In Chiaro (cercalatuascuola.istruzione.it)
2. Sito web della scuola (campo SITOWEBSCUOLA)
3. Ricerca via istituto di riferimento (solo statali)

Validazione anti-falsi positivi:
- Verifica header PDF (%PDF)
- Dimensione minima (50KB per PTOF reali)
- Ricerca keyword "PTOF", "Piano Triennale", "Offerta Formativa" nel testo
- Esclusione documenti troppo corti o non pertinenti
"""

import os
import re
import sys
import csv
import json
import time
import hashlib
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Set
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from dataclasses import dataclass, field
import random

# Carica variabili d'ambiente da .env
from dotenv import load_dotenv
load_dotenv()

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from ddgs import DDGS
    HAS_DDG = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDG = True
    except ImportError:
        HAS_DDG = False

# Tavily AI Search (1000 crediti/mese gratis)
try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    HAS_TAVILY = False

# OpenAI per Perplexity (API compatibile)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = BASE_DIR / "ptof_inbox"
LOG_DIR = BASE_DIR / "logs"
STATE_FILE = DATA_DIR / "download_state.json"
DOWNLOAD_LOCK = DOWNLOAD_DIR / ".download_in_progress"
PROCESSED_DIR = BASE_DIR / "ptof_processed"
DISCARDED_DIR = BASE_DIR / "ptof_discarded"

# File anagrafiche MIUR
ANAGRAFE_STAT = DATA_DIR / "SCUANAGRAFESTAT20252620250901.csv"
ANAGRAFE_PAR = DATA_DIR / "SCUANAGRAFEPAR20252620250901.csv"

# Scuola In Chiaro API
# Aggiornato al nuovo portale Unica
SCUOLA_IN_CHIARO_BASE = "https://unica.istruzione.gov.it"
SCUOLA_IN_CHIARO_PTOF = f"{SCUOLA_IN_CHIARO_BASE}/cercalatuascuola/istituti/{{code}}/ptof/"
SCUOLA_IN_CHIARO_DOCS = f"{SCUOLA_IN_CHIARO_BASE}/cercalatuascuola/istituti/{{code}}/documenti/"

# HTTP config
TIMEOUT = 30
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 1.0  # Rate limiting (più conservativo)
MAX_WORKERS = 2  # Parallel downloads (conservativo)

# Validazione PTOF
MIN_PDF_SIZE = 50 * 1024  # 50KB minimo per un PTOF reale
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB massimo
MIN_PTOF_SCORE = 0.80  # Score minimo per accettare un PDF come PTOF valido
PTOF_KEYWORDS = [
    'ptof', 'piano triennale', 'offerta formativa', 
    'curricolo', 'competenze', 'valutazione',
    'inclusione', 'orientamento', 'ampliamento'
]

# Province metropolitane italiane (Città Metropolitane)
PROVINCE_METROPOLITANE = {
    'ROMA', 'MILANO', 'NAPOLI', 'TORINO', 'BARI', 
    'FIRENZE', 'BOLOGNA', 'GENOVA', 'VENEZIA',
    'REGGIO CALABRIA', 'PALERMO', 'CATANIA', 'MESSINA', 'CAGLIARI'
}

# Mapping aree geografiche
AREE_GEOGRAFICHE = ['NORD OVEST', 'NORD EST', 'CENTRO', 'SUD', 'ISOLE']

# Mapping gradi istruzione (normalizzato)
GRADI_ISTRUZIONE = {
    'INFANZIA': ['INFANZIA', 'MATERNA'],
    'PRIMARIA': ['PRIMARIA', 'ELEMENTARE'],
    'SEC_PRIMO': ['PRIMO GRADO', 'MEDIA', 'SECONDARIA DI PRIMO'],
    'SEC_SECONDO': ['SECONDO GRADO', 'SUPERIORE', 'LICEO', 'TECNICO', 'PROFESSIONALE', 'ISTITUTO MAGISTRALE']
}

# Headers HTTP
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
}

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAZIONE API ESTERNE (Search fallback)
# ═══════════════════════════════════════════════════════════════════
# Jina AI (gratuito, rate limited) - https://jina.ai/reader
JINA_SEARCH_URL = "https://s.jina.ai/"
JINA_READER_URL = "https://r.jina.ai/"

# Tavily AI (1000 crediti/mese gratis) - https://tavily.com
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# Brave Search (2000 query/mese gratis) - https://brave.com/search/api/
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Perplexity AI (finale per ricerche difficili) - https://docs.perplexity.ai
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


# ═══════════════════════════════════════════════════════════════════
# SETUP LOGGING
# ═══════════════════════════════════════════════════════════════════
def setup_logging(log_dir: Path) -> logging.Logger:
    """Configura logging su file e console."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('ptof_downloader')
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    
    # File handler
    log_file = log_dir / f"ptof_download_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging(LOG_DIR)

def _set_download_lock(active: bool) -> None:
    if active:
        try:
            DOWNLOAD_LOCK.parent.mkdir(parents=True, exist_ok=True)
            DOWNLOAD_LOCK.write_text(datetime.now().isoformat(), encoding='utf-8')
        except Exception as e:
            logger.warning(f"⚠️ Impossibile creare lock download: {e}")
    else:
        try:
            if DOWNLOAD_LOCK.exists():
                DOWNLOAD_LOCK.unlink()
        except Exception as e:
            logger.warning(f"⚠️ Impossibile rimuovere lock download: {e}")


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SchoolRecord:
    """Record di una scuola da anagrafe MIUR."""
    codice: str
    denominazione: str
    indirizzo: str
    cap: str
    comune: str
    provincia: str
    regione: str
    area_geografica: str
    tipologia: str
    email: str
    pec: str
    sito_web: Optional[str]
    is_statale: bool
    codice_istituto: Optional[str] = None  # Solo per statali
    denominazione_istituto: Optional[str] = None
    
    # Campi calcolati
    is_metropolitana: bool = field(init=False)
    grado_normalizzato: str = field(init=False)
    
    def __post_init__(self):
        self.is_metropolitana = self.provincia.upper() in PROVINCE_METROPOLITANE
        self.grado_normalizzato = self._normalizza_grado()
    
    def _normalizza_grado(self) -> str:
        """Normalizza il grado di istruzione."""
        tipo_upper = self.tipologia.upper()
        for grado, keywords in GRADI_ISTRUZIONE.items():
            if any(kw in tipo_upper for kw in keywords):
                return grado
        return 'ALTRO'
    
    @property
    def has_website(self) -> bool:
        return self.sito_web is not None
    
    @property
    def strato(self) -> str:
        """Chiave di stratificazione univoca (basata su REGIONE)."""
        tipo = 'STAT' if self.is_statale else 'PAR'
        metro = 'METRO' if self.is_metropolitana else 'NON_METRO'
        # Normalizza regione: 'EMILIA ROMAGNA' -> 'EMILIA_ROMAGNA'
        reg_norm = self.regione.upper().replace(' ', '_').replace('-', '_')
        return f"{tipo}_{reg_norm}_{metro}_{self.grado_normalizzato}"
    
    def __repr__(self):
        return f"School({self.codice}, {self.denominazione[:30]}, {self.strato})"


@dataclass
class DownloadResult:
    """Risultato di un tentativo di download."""
    success: bool
    message: str
    source: str = ""
    file_path: Optional[str] = None
    file_size: int = 0
    validation_score: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# GESTIONE STATO
# ═══════════════════════════════════════════════════════════════════

class DownloadState:
    """Gestisce lo stato dei download per permettere resume."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self._load()
    
    def _load(self) -> Dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Stato corrotto, ricreo")
        return {
            "downloaded": {},
            "failed": {},
            "rejected": {},  # PDF scaricati ma non validi come PTOF
            "last_run": None,
            "stats_per_strato": {}
        }
    
    def save(self):
        self.state["last_run"] = datetime.now().isoformat()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def is_downloaded(self, code: str) -> bool:
        return code in self.state["downloaded"]
    
    def is_failed(self, code: str) -> bool:
        return code in self.state["failed"]
    
    def is_rejected(self, code: str) -> bool:
        return code in self.state["rejected"]
    
    def mark_downloaded(self, code: str, path: str, source: str, strato: str, size: int):
        self.state["downloaded"][code] = {
            "path": path,
            "source": source,
            "strato": strato,
            "size": size,
            "timestamp": datetime.now().isoformat()
        }
        # Aggiorna stats per strato
        if strato not in self.state["stats_per_strato"]:
            self.state["stats_per_strato"][strato] = {"downloaded": 0, "failed": 0}
        self.state["stats_per_strato"][strato]["downloaded"] += 1
    
    def mark_failed(self, code: str, reason: str, strato: str):
        if code in self.state["failed"]:
            self.state["failed"][code]["attempts"] += 1
        else:
            self.state["failed"][code] = {"reason": reason, "attempts": 1, "strato": strato}
        self.state["failed"][code]["last_attempt"] = datetime.now().isoformat()
        
        if strato not in self.state["stats_per_strato"]:
            self.state["stats_per_strato"][strato] = {"downloaded": 0, "failed": 0}
        self.state["stats_per_strato"][strato]["failed"] += 1
    
    def mark_rejected(self, code: str, reason: str, strato: str):
        """Marca un PDF come scaricato ma non valido come PTOF."""
        self.state["rejected"][code] = {
            "reason": reason,
            "strato": strato,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        return {
            "downloaded": len(self.state["downloaded"]),
            "failed": len(self.state["failed"]),
            "rejected": len(self.state["rejected"]),
            "per_strato": self.state["stats_per_strato"]
        }


# ═══════════════════════════════════════════════════════════════════
# VALIDATORE PTOF
# ═══════════════════════════════════════════════════════════════════

class PTOFValidator:
    """Valida che un PDF sia effettivamente un PTOF."""
    
    @staticmethod
    def validate_pdf_header(content: bytes) -> bool:
        """Verifica che il file inizi con %PDF."""
        return content[:4] == b'%PDF'
    
    @staticmethod
    def validate_size(size: int) -> Tuple[bool, str]:
        """Verifica dimensione ragionevole per un PTOF."""
        if size < MIN_PDF_SIZE:
            return False, f"Troppo piccolo ({size/1024:.1f}KB < {MIN_PDF_SIZE/1024}KB)"
        if size > MAX_PDF_SIZE:
            return False, f"Troppo grande ({size/1024/1024:.1f}MB)"
        return True, "OK"
    
    @staticmethod
    def extract_text_sample(pdf_path: Path, max_pages: int = 5) -> str:
        """Estrae testo dalle prime pagine del PDF."""
        text_parts = []
        
        if HAS_PYPDF:
            try:
                reader = PdfReader(str(pdf_path))
                for i, page in enumerate(reader.pages[:max_pages]):
                    try:
                        text_parts.append(page.extract_text() or "")
                    except:
                        continue
            except Exception as e:
                logger.debug(f"pypdf fallito: {e}")
        
        if not text_parts and HAS_FITZ:
            try:
                doc = fitz.open(str(pdf_path))
                for i in range(min(max_pages, len(doc))):
                    text_parts.append(doc[i].get_text("text") or "")
                doc.close()
            except Exception as e:
                logger.debug(f"fitz fallito: {e}")
        
        return "\n".join(text_parts).lower()
    
    @classmethod
    def calculate_ptof_score(cls, pdf_path: Path) -> Tuple[float, str]:
        """
        Calcola uno score 0-1 che indica quanto il documento sembra un PTOF.
        Ritorna (score, reason).
        """
        if not pdf_path.exists():
            return 0.0, "File non esiste"
        
        # Verifica dimensione
        size = pdf_path.stat().st_size
        size_ok, size_msg = cls.validate_size(size)
        if not size_ok:
            return 0.0, size_msg
        
        # Estrai testo
        text = cls.extract_text_sample(pdf_path)
        if len(text) < 500:
            return 0.1, "Testo insufficiente estratto"
        
        # Conta keyword PTOF
        keyword_count = 0
        found_keywords = []
        for kw in PTOF_KEYWORDS:
            count = text.count(kw)
            if count > 0:
                keyword_count += min(count, 5)  # Cap per keyword
                found_keywords.append(kw)
        
        # Calcola score
        if keyword_count == 0:
            return 0.1, "Nessuna keyword PTOF trovata"
        
        # Score base su keyword (max 0.6)
        score = min(keyword_count / 20, 0.6)
        
        # Bonus per keyword critiche
        if 'ptof' in found_keywords or 'piano triennale' in found_keywords:
            score += 0.3
        if 'offerta formativa' in found_keywords:
            score += 0.1
        
        score = min(score, 1.0)
        
        if score >= 0.5:
            return score, f"PTOF probabile (score={score:.2f}, keywords={found_keywords[:5]})"
        else:
            return score, f"Documento generico (score={score:.2f})"
    
    @classmethod
    def is_valid_ptof(cls, pdf_path: Path, min_score: float = MIN_PTOF_SCORE) -> Tuple[bool, float, str]:
        """
        Determina se il PDF è un PTOF valido.
        Ritorna (is_valid, score, reason).
        Soglia minima: 0.80 per evitare falsi positivi.
        """
        score, reason = cls.calculate_ptof_score(pdf_path)
        return score >= min_score, score, reason


# ═══════════════════════════════════════════════════════════════════
# DOWNLOADER
# ═══════════════════════════════════════════════════════════════════

class PTOFDownloader:
    """Downloader principale per i PTOF."""
    
    def __init__(self, state: DownloadState, download_dir: Path):
        self.state = state
        self.download_dir = download_dir
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.validator = PTOFValidator()
        self.stats = {
            "total": 0,
            "downloaded": 0,
            "validated": 0,
            "rejected": 0,
            "failed": 0,
            "skipped": 0,
            "already_done": 0
        }
    
    def download_ptof(self, school: SchoolRecord) -> DownloadResult:
        """
        Tenta di scaricare il PTOF di una scuola.
        """
        code = school.codice
        strato = school.strato
        
        # Skip se già processato
        if self.state.is_downloaded(code):
            self.stats["already_done"] += 1
            return DownloadResult(True, "Già scaricato", "cache")
        
        if self.state.is_rejected(code):
            self.stats["skipped"] += 1
            return DownloadResult(False, "Già rifiutato", "cache")
        
        # Verifica se file esiste già nel progetto (inbox, processed, discarded)
        check_dirs = [self.download_dir, PROCESSED_DIR, DISCARDED_DIR]
        for d in check_dirs:
            if d.exists():
                existing = list(d.glob(f"*{code}*.pdf"))
                if existing:
                    # Se trovato, consideralo come già fatto
                    self.state.mark_downloaded(code, str(existing[0]), "existing", strato, existing[0].stat().st_size)
                    self.stats["already_done"] += 1
                    return DownloadResult(True, f"File già presente in {d.name}: {existing[0].name}", "existing")
        
        # Strategia 1: API Scuola In Chiaro
        result = self._try_scuola_in_chiaro(school)
        if result.success:
            return result
        
        # Strategia 2: Sito web scuola
        if school.has_website:
            result = self._try_website_crawl(school)
            if result.success:
                return result
        
        # Strategia 3: Per scuole statali, prova con codice istituto
        if school.is_statale and school.codice_istituto and school.codice_istituto != code:
            result = self._try_scuola_in_chiaro_istituto(school)
            if result.success:
                return result
        
        # Strategia 4: Ricerca Web (DuckDuckGo)
        if HAS_DDG:
            result = self._try_search_engine(school)
            if result.success:
                return result
        
        # ═══════════════════════════════════════════════════════════════════
        # STRATEGIE AVANZATE (API esterne) - per PTOF non trovati
        # ═══════════════════════════════════════════════════════════════════
        
        # Strategia 5: Jina AI Search (gratuito, illimitato con rate limit)
        result = self._try_jina_search(school)
        if result.success:
            return result
        
        # Strategia 6: Tavily AI (1000 crediti/mese gratis)
        if TAVILY_API_KEY:
            result = self._try_tavily_search(school)
            if result.success:
                return result
        
        # Strategia 7: Brave Search API (2000 query/mese gratis)
        if BRAVE_API_KEY:
            result = self._try_brave_search(school)
            if result.success:
                return result
        
        # Strategia 8 (FINALE): Perplexity AI per ricerche difficili
        if PERPLEXITY_API_KEY:
            result = self._try_perplexity_search(school)
            if result.success:
                return result
        
        self.state.mark_failed(code, "Nessuna strategia ha funzionato", strato)
        self.stats["failed"] += 1
        return DownloadResult(False, "PTOF non trovato")
    
    def _try_scuola_in_chiaro(self, school: SchoolRecord) -> DownloadResult:
        """Cerca PTOF su cercalatuascuola.istruzione.it"""
        code = school.codice
        
        # Prova prima la pagina PTOF diretta
        ptof_url = SCUOLA_IN_CHIARO_PTOF.format(code=code)
        
        try:
            resp = self.session.get(ptof_url, timeout=TIMEOUT, verify=False)
            if resp.status_code == 200:
                pdf_links = self._find_pdf_links(resp.text, ptof_url)
                for pdf_url in pdf_links:
                    result = self._download_and_validate(pdf_url, school, "scuola_in_chiaro")
                    if result.success:
                        return result
            
            # Prova la pagina documenti
            docs_url = SCUOLA_IN_CHIARO_DOCS.format(code=code)
            resp = self.session.get(docs_url, timeout=TIMEOUT, verify=False)
            if resp.status_code == 200:
                pdf_links = self._find_ptof_links(resp.text, docs_url)
                for pdf_url in pdf_links:
                    result = self._download_and_validate(pdf_url, school, "scuola_in_chiaro_docs")
                    if result.success:
                        return result
            
            return DownloadResult(False, "Nessun PTOF su Scuola In Chiaro")
            
        except Exception as e:
            logger.debug(f"{code}: Errore Scuola In Chiaro: {e}")
            return DownloadResult(False, f"Errore: {e}")
    
    def _try_scuola_in_chiaro_istituto(self, school: SchoolRecord) -> DownloadResult:
        """Per plessi, prova con il codice istituto di riferimento."""
        code_ist = school.codice_istituto
        ptof_url = SCUOLA_IN_CHIARO_PTOF.format(code=code_ist)
        
        try:
            resp = self.session.get(ptof_url, timeout=TIMEOUT, verify=False)
            if resp.status_code == 200:
                pdf_links = self._find_pdf_links(resp.text, ptof_url)
                for pdf_url in pdf_links:
                    result = self._download_and_validate(pdf_url, school, f"istituto_{code_ist}")
                    if result.success:
                        return result
            
            return DownloadResult(False, f"Nessun PTOF da istituto {code_ist}")
            
        except Exception as e:
            return DownloadResult(False, f"Errore istituto: {e}")
    
    def _try_website_crawl(self, school: SchoolRecord) -> DownloadResult:
        """Cerca PTOF sul sito web della scuola."""
        base_url = school.sito_web
        
        try:
            resp = self.session.get(base_url, timeout=TIMEOUT, verify=False)
            if resp.status_code != 200:
                return DownloadResult(False, f"Sito non raggiungibile ({resp.status_code})")
            
            # Cerca link PTOF nella homepage
            pdf_links = self._find_ptof_links(resp.text, base_url)
            
            # Se non trovato, prova percorsi comuni
            if not pdf_links:
                common_paths = [
                    '/ptof', '/didattica/ptof', '/la-scuola/ptof',
                    '/istituto/ptof', '/documenti/ptof', '/offerta-formativa/ptof',
                    '/piano-triennale', '/pof', '/ptof-rav', '/chi-siamo/ptof',
                    '/scuola/ptof', '/amministrazione-trasparente/ptof'
                ]
                for path in common_paths:
                    try:
                        sub_url = urljoin(base_url, path)
                        resp2 = self.session.get(sub_url, timeout=10, verify=False)
                        if resp2.status_code == 200:
                            pdf_links.extend(self._find_ptof_links(resp2.text, sub_url))
                            if pdf_links:
                                break
                    except:
                        continue
            
            for pdf_url in pdf_links[:5]:  # Max 5 tentativi
                result = self._download_and_validate(pdf_url, school, "website")
                if result.success:
                    return result
            
            return DownloadResult(False, "Nessun PTOF valido sul sito")
            
        except Exception as e:
            return DownloadResult(False, f"Errore sito: {e}")
    
    def _try_search_engine(self, school: SchoolRecord) -> DownloadResult:
        """Strategia 4: Cerca il PTOF usando DuckDuckGo."""
        try:
            # Query specifica per trovare PDF
            query = f"{school.codice} PTOF piano triennale offerta formativa filetype:pdf"
            
            with DDGS() as ddgs:
                # Cerchiamo i primi 5 risultati
                results = list(ddgs.text(query, max_results=5))
                
            for res in results:
                url = res['href']
                # Spesso i link di Google/DDG sono puliti, ma verifichiamo
                if url.lower().endswith('.pdf'):
                     result = self._download_and_validate(url, school, "duckduckgo")
                     if result.success:
                         return result
            
            return DownloadResult(False, "Nessun PDF valido trovato via ricerca")
        except Exception as e:
             return DownloadResult(False, f"Errore ricerca: {e}")

    def _try_jina_search(self, school: SchoolRecord) -> DownloadResult:
        """Strategia 5: Cerca il PTOF usando Jina AI Search (gratuito)."""
        try:
            # Query per Jina Search
            query = f"{school.codice} {school.denominazione} PTOF piano triennale offerta formativa"
            search_url = f"{JINA_SEARCH_URL}{requests.utils.quote(query)}"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': HEADERS['User-Agent']
            }
            
            resp = self.session.get(search_url, headers=headers, timeout=TIMEOUT)
            if resp.status_code != 200:
                return DownloadResult(False, f"Jina Search errore: {resp.status_code}")
            
            # Jina restituisce markdown, cerchiamo URL PDF
            content = resp.text
            pdf_urls = re.findall(r'https?://[^\s\)\"\']+\.pdf', content, re.IGNORECASE)
            
            for url in pdf_urls[:5]:
                result = self._download_and_validate(url, school, "jina_search")
                if result.success:
                    return result
            
            return DownloadResult(False, "Nessun PDF valido trovato via Jina")
        except Exception as e:
            return DownloadResult(False, f"Errore Jina Search: {e}")

    def _try_tavily_search(self, school: SchoolRecord) -> DownloadResult:
        """Strategia 6: Cerca il PTOF usando Tavily AI (1000/mese gratis)."""
        if not TAVILY_API_KEY:
            return DownloadResult(False, "TAVILY_API_KEY non configurata")
        
        try:
            if HAS_TAVILY:
                client = TavilyClient(api_key=TAVILY_API_KEY)
                query = f"{school.codice} {school.denominazione} PTOF piano triennale offerta formativa filetype:pdf"
                response = client.search(query, max_results=5)
                results = response.get('results', [])
            else:
                # Fallback: chiamata HTTP diretta
                headers = {
                    'Authorization': f'Bearer {TAVILY_API_KEY}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    'query': f"{school.codice} {school.denominazione} PTOF piano triennale filetype:pdf",
                    'max_results': 5,
                    'search_depth': 'basic'
                }
                resp = self.session.post(
                    'https://api.tavily.com/search',
                    headers=headers,
                    json=payload,
                    timeout=TIMEOUT
                )
                if resp.status_code != 200:
                    return DownloadResult(False, f"Tavily errore: {resp.status_code}")
                results = resp.json().get('results', [])
            
            for res in results:
                url = res.get('url', '')
                if url.lower().endswith('.pdf'):
                    result = self._download_and_validate(url, school, "tavily")
                    if result.success:
                        return result
                # Prova anche a cercare PDF nel contenuto
                content = res.get('content', '') + ' ' + res.get('raw_content', '')
                pdf_urls = re.findall(r'https?://[^\s\)\"\']+\.pdf', content, re.IGNORECASE)
                for pdf_url in pdf_urls[:2]:
                    result = self._download_and_validate(pdf_url, school, "tavily")
                    if result.success:
                        return result
            
            return DownloadResult(False, "Nessun PDF valido trovato via Tavily")
        except Exception as e:
            return DownloadResult(False, f"Errore Tavily: {e}")

    def _try_brave_search(self, school: SchoolRecord) -> DownloadResult:
        """Strategia 7: Cerca il PTOF usando Brave Search API (2000/mese gratis)."""
        if not BRAVE_API_KEY:
            return DownloadResult(False, "BRAVE_API_KEY non configurata")
        
        try:
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': BRAVE_API_KEY
            }
            params = {
                'q': f"{school.codice} {school.denominazione} PTOF piano triennale offerta formativa filetype:pdf",
                'count': 10,
                'country': 'IT',
                'search_lang': 'it'
            }
            
            resp = self.session.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=TIMEOUT)
            if resp.status_code != 200:
                return DownloadResult(False, f"Brave Search errore: {resp.status_code}")
            
            data = resp.json()
            web_results = data.get('web', {}).get('results', [])
            
            for res in web_results:
                url = res.get('url', '')
                if url.lower().endswith('.pdf'):
                    result = self._download_and_validate(url, school, "brave")
                    if result.success:
                        return result
                # Cerca PDF nella descrizione
                description = res.get('description', '')
                pdf_urls = re.findall(r'https?://[^\s\)\"\']+\.pdf', description, re.IGNORECASE)
                for pdf_url in pdf_urls[:2]:
                    result = self._download_and_validate(pdf_url, school, "brave")
                    if result.success:
                        return result
            
            return DownloadResult(False, "Nessun PDF valido trovato via Brave")
        except Exception as e:
            return DownloadResult(False, f"Errore Brave Search: {e}")

    def _try_perplexity_search(self, school: SchoolRecord) -> DownloadResult:
        """Strategia 8 (FINALE): Usa Perplexity AI per ricerche difficili."""
        if not PERPLEXITY_API_KEY:
            return DownloadResult(False, "PERPLEXITY_API_KEY non configurata")
        
        try:
            headers = {
                'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            # Prompt specifico per trovare il PTOF
            prompt = f"""Trova il link diretto al PDF del PTOF (Piano Triennale dell'Offerta Formativa) 
della scuola italiana con codice meccanografico {school.codice}.
Nome scuola: {school.denominazione}
Comune: {school.comune}, Provincia: {school.provincia}

Cerca su:
1. Sito ufficiale della scuola
2. Portale Scuola In Chiaro (cercalatuascuola.istruzione.it)
3. Altri siti istituzionali

Rispondi SOLO con l'URL diretto al file PDF del PTOF, senza spiegazioni.
Se non trovi il PDF, rispondi "NON TROVATO"."""

            payload = {
                'model': 'sonar',  # Modello base gratuito/economico
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 500,
                'temperature': 0.1
            }
            
            resp = self.session.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                return DownloadResult(False, f"Perplexity errore: {resp.status_code}")
            
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if 'NON TROVATO' in content.upper():
                return DownloadResult(False, "Perplexity: PTOF non trovato")
            
            # Estrai URL dal contenuto
            pdf_urls = re.findall(r'https?://[^\s\)\"\'<>]+\.pdf', content, re.IGNORECASE)
            
            for url in pdf_urls[:3]:
                # Pulisci l'URL da eventuali caratteri extra
                url = url.rstrip('.,;:)')
                result = self._download_and_validate(url, school, "perplexity")
                if result.success:
                    return result
            
            return DownloadResult(False, "Nessun PDF valido trovato via Perplexity")
        except Exception as e:
            return DownloadResult(False, f"Errore Perplexity: {e}")

    def _find_pdf_links(self, html: str, base_url: str) -> List[str]:
        """Trova tutti i link a PDF nella pagina."""
        links = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
        return list(set(urljoin(base_url, link) for link in links))
    
    def _find_ptof_links(self, html: str, base_url: str) -> List[str]:
        """Trova link a PDF che sembrano PTOF (prioritizzati)."""
        all_links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        
        ptof_pattern = r'ptof|piano.{0,10}triennale|offerta.{0,10}formativa|p\.?t\.?o\.?f'
        
        # Priorità: PDF con keyword PTOF nel nome
        high_priority = []
        medium_priority = []
        
        for link in all_links:
            link_lower = link.lower()
            
            if '.pdf' in link_lower:
                if re.search(ptof_pattern, link_lower):
                    high_priority.append(link)
                elif any(kw in link_lower for kw in ['piano', 'offerta', 'triennale']):
                    medium_priority.append(link)
        
        # Ordina: prima high priority, poi medium
        candidates = high_priority + medium_priority
        return list(set(urljoin(base_url, c) for c in candidates))
    
    def _download_and_validate(self, url: str, school: SchoolRecord, source: str) -> DownloadResult:
        """Scarica un PDF, lo valida e lo salva se è un PTOF valido."""
        code = school.codice
        strato = school.strato
        
        try:
            resp = self.session.get(url, timeout=TIMEOUT, verify=False, stream=True)
            
            if resp.status_code != 200:
                return DownloadResult(False, f"HTTP {resp.status_code}")
            
            # Verifica content-type o header PDF
            content = resp.content
            if not self.validator.validate_pdf_header(content):
                return DownloadResult(False, "Non è un PDF")
            
            # Verifica dimensione
            size = len(content)
            size_ok, size_msg = self.validator.validate_size(size)
            if not size_ok:
                return DownloadResult(False, size_msg)
            
            # Salva temporaneamente per validazione
            temp_path = self.download_dir / f".temp_{code}.pdf"
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Valida contenuto PTOF
            is_valid, score, reason = self.validator.is_valid_ptof(temp_path)
            
            if not is_valid:
                temp_path.unlink()
                self.state.mark_rejected(code, reason, strato)
                self.stats["rejected"] += 1
                logger.debug(f"{code}: PDF rifiutato - {reason}")
                return DownloadResult(False, f"Non PTOF: {reason}", validation_score=score)
            
            # Rinomina al path finale
            final_path = self.download_dir / f"{code}_PTOF.pdf"
            temp_path.rename(final_path)
            
            self.state.mark_downloaded(code, str(final_path), source, strato, size)
            self.stats["downloaded"] += 1
            self.stats["validated"] += 1
            
            logger.info(f"✅ {code}: Scaricato e validato ({size/1024:.1f}KB, score={score:.2f}) [{source}]")
            
            return DownloadResult(
                success=True,
                message=f"Scaricato da {source}",
                source=source,
                file_path=str(final_path),
                file_size=size,
                validation_score=score
            )
            
        except Exception as e:
            logger.debug(f"{code}: Errore download {url}: {e}")
            return DownloadResult(False, f"Errore: {e}")


# ═══════════════════════════════════════════════════════════════════
# CARICAMENTO E STRATIFICAZIONE
# ═══════════════════════════════════════════════════════════════════

def load_schools_statali(file_path: Path) -> List[SchoolRecord]:
    """Carica scuole statali da CSV MIUR."""
    schools = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codice = row.get('CODICESCUOLA', '').strip()
            if not codice:
                continue
            
            sito_web = row.get('SITOWEBSCUOLA', '').strip()
            if not sito_web or sito_web == 'Non Disponibile':
                sito_web = None
            elif not sito_web.startswith(('http://', 'https://')):
                sito_web = 'https://' + sito_web
            
            school = SchoolRecord(
                codice=codice,
                denominazione=row.get('DENOMINAZIONESCUOLA', ''),
                indirizzo=row.get('INDIRIZZOSCUOLA', ''),
                cap=row.get('CAPSCUOLA', ''),
                comune=row.get('DESCRIZIONECOMUNE', ''),
                provincia=row.get('PROVINCIA', ''),
                regione=row.get('REGIONE', ''),
                area_geografica=row.get('AREAGEOGRAFICA', ''),
                tipologia=row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', ''),
                email=row.get('INDIRIZZOEMAILSCUOLA', ''),
                pec=row.get('INDIRIZZOPECSCUOLA', ''),
                sito_web=sito_web,
                is_statale=True,
                codice_istituto=row.get('CODICEISTITUTORIFERIMENTO', ''),
                denominazione_istituto=row.get('DENOMINAZIONEISTITUTORIFERIMENTO', '')
            )
            schools.append(school)
    
    return schools


def load_schools_paritarie(file_path: Path) -> List[SchoolRecord]:
    """Carica scuole paritarie da CSV MIUR."""
    schools = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codice = row.get('CODICESCUOLA', '').strip()
            if not codice:
                continue
            
            sito_web = row.get('SITOWEBSCUOLA', '').strip()
            if not sito_web or sito_web == 'Non Disponibile':
                sito_web = None
            elif not sito_web.startswith(('http://', 'https://')):
                sito_web = 'https://' + sito_web
            
            school = SchoolRecord(
                codice=codice,
                denominazione=row.get('DENOMINAZIONESCUOLA', ''),
                indirizzo=row.get('INDIRIZZOSCUOLA', ''),
                cap=row.get('CAPSCUOLA', ''),
                comune=row.get('DESCRIZIONECOMUNE', ''),
                provincia=row.get('PROVINCIA', ''),
                regione=row.get('REGIONE', ''),
                area_geografica=row.get('AREAGEOGRAFICA', ''),
                tipologia=row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', ''),
                email=row.get('INDIRIZZOEMAILSCUOLA', ''),
                pec=row.get('INDIRIZZOPECSCUOLA', ''),
                sito_web=sito_web,
                is_statale=False
            )
            schools.append(school)
    
    return schools


def stratify_schools(schools: List[SchoolRecord]) -> Dict[str, List[SchoolRecord]]:
    """Raggruppa scuole per strato."""
    strata = defaultdict(list)
    for school in schools:
        strata[school.strato].append(school)
    return dict(strata)


def sample_stratified(
    strata: Dict[str, List[SchoolRecord]],
    n_per_stratum: Optional[int] = None,
    total_n: Optional[int] = None,
    proportional: bool = True
) -> List[SchoolRecord]:
    """
    Campionamento stratificato.
    
    Args:
        strata: Dict strato -> lista scuole
        n_per_stratum: Numero fisso per strato (se specificato)
        total_n: Numero totale da campionare (usato con proportional)
        proportional: Se True, campiona proporzionalmente alla dimensione degli strati
    """
    sampled = []
    total_schools = sum(len(v) for v in strata.values())
    
    if n_per_stratum:
        # Campionamento fisso per strato
        for stratum, schools in strata.items():
            n = min(n_per_stratum, len(schools))
            sampled.extend(random.sample(schools, n))
    
    elif total_n and proportional:
        # Campionamento proporzionale
        for stratum, schools in strata.items():
            proportion = len(schools) / total_schools
            n = max(1, int(total_n * proportion))
            n = min(n, len(schools))
            sampled.extend(random.sample(schools, n))
    
    else:
        # Tutte le scuole
        for schools in strata.values():
            sampled.extend(schools)
    
    return sampled


def print_stratification_summary(strata: Dict[str, List[SchoolRecord]]):
    """Stampa riepilogo della stratificazione."""
    logger.info("\n" + "="*70)
    logger.info("📊 RIEPILOGO STRATIFICAZIONE")
    logger.info("="*70)
    
    # Raggruppa per dimensioni
    by_tipo = defaultdict(int)
    by_area = defaultdict(int)
    by_metro = defaultdict(int)
    by_grado = defaultdict(int)
    
    for strato, schools in strata.items():
        parts = strato.split('_')
        if len(parts) >= 4:
            tipo = parts[0]
            area = '_'.join(parts[1:-2])  # Gestisce "NORD OVEST" etc
            metro = parts[-2]
            grado = parts[-1]
            
            by_tipo[tipo] += len(schools)
            by_area[area] += len(schools)
            by_metro[metro] += len(schools)
            by_grado[grado] += len(schools)
    
    logger.info(f"\n📌 Per tipo scuola:")
    for k, v in sorted(by_tipo.items()):
        logger.info(f"   {k}: {v}")
    
    logger.info(f"\n📌 Per area geografica:")
    for k, v in sorted(by_area.items()):
        logger.info(f"   {k}: {v}")
    
    logger.info(f"\n📌 Per tipo provincia:")
    for k, v in sorted(by_metro.items()):
        label = "Metropolitane" if k == "METRO" else "Non metropolitane"
        logger.info(f"   {label}: {v}")
    
    logger.info(f"\n📌 Per grado istruzione:")
    for k, v in sorted(by_grado.items()):
        logger.info(f"   {k}: {v}")
    
    logger.info(f"\n📌 Totale strati: {len(strata)}")
    logger.info(f"📌 Totale scuole: {sum(len(v) for v in strata.values())}")
    logger.info("="*70 + "\n")


# ═══════════════════════════════════════════════════════════════════
# ESECUZIONE DOWNLOAD
# ═══════════════════════════════════════════════════════════════════

def run_download(
    schools: List[SchoolRecord],
    state: DownloadState,
    download_dir: Path
):
    """Esegue il download dei PTOF."""
    downloader = PTOFDownloader(state, download_dir)
    
    total = len(schools)
    logger.info(f"📚 Inizio download di {total} scuole...")
    
    for i, school in enumerate(schools, 1):
        result = downloader.download_ptof(school)
        
        if i % 25 == 0 or i == total:
            stats = downloader.stats
            logger.info(
                f"Progresso: {i}/{total} | "
                f"✅ {stats['downloaded']} | "
                f"❌ {stats['failed']} | "
                f"🚫 {stats['rejected']} | "
                f"⏭️ {stats['already_done']}"
            )
            state.save()
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    state.save()
    
    # Report finale
    stats = downloader.stats
    logger.info("\n" + "="*70)
    logger.info("📊 RIEPILOGO DOWNLOAD")
    logger.info("="*70)
    logger.info(f"Totale scuole processate: {total}")
    logger.info(f"✅ Scaricati e validati: {stats['downloaded']}")
    logger.info(f"⏭️  Già presenti: {stats['already_done']}")
    logger.info(f"🚫 Rifiutati (non PTOF): {stats['rejected']}")
    logger.info(f"❌ Falliti: {stats['failed']}")
    logger.info(f"\n📁 Directory output: {download_dir}")
    
    # Stats per strato
    state_stats = state.get_stats()
    if state_stats["per_strato"]:
        logger.info("\n📊 Dettaglio per strato:")
        for strato, s in sorted(state_stats["per_strato"].items()):
            logger.info(f"   {strato}: ✅{s.get('downloaded',0)} ❌{s.get('failed',0)}")
    
    logger.info("="*70)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Scarica PTOF dalle anagrafiche MIUR con campionamento stratificato",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Scarica tutte le scuole statali del Lazio
  python ptof_downloader.py --statali --regioni LAZIO

  # Campione stratificato: 5 scuole per ogni strato
  python ptof_downloader.py --tutte --sample-per-strato 5

  # Campione proporzionale di 500 scuole totali
  python ptof_downloader.py --tutte --sample-total 500

  # Solo licei delle province metropolitane
  python ptof_downloader.py --statali --gradi SEC_SECONDO --solo-metropolitane

  # Solo scuole primarie NON metropolitane del Sud
  python ptof_downloader.py --statali --gradi PRIMARIA --solo-non-metropolitane --aree SUD

  # Mostra stratificazione senza scaricare
  python ptof_downloader.py --tutte --dry-run
        """
    )
    
    # Tipo scuole
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--statali', action='store_true', help='Solo scuole statali')
    source.add_argument('--paritarie', action='store_true', help='Solo scuole paritarie')
    source.add_argument('--tutte', action='store_true', help='Tutte le scuole')
    
    # Filtri geografici
    parser.add_argument('--regioni', nargs='+', help='Filtra per regioni')
    parser.add_argument('--province', nargs='+', help='Filtra per province')
    parser.add_argument('--aree', nargs='+', choices=AREE_GEOGRAFICHE, help='Filtra per aree geografiche')
    
    # Filtri metropolitane
    metro = parser.add_mutually_exclusive_group()
    metro.add_argument('--solo-metropolitane', action='store_true', help='Solo province metropolitane')
    metro.add_argument('--solo-non-metropolitane', action='store_true', help='Solo province NON metropolitane')
    
    # Filtri grado
    parser.add_argument('--gradi', nargs='+', choices=list(GRADI_ISTRUZIONE.keys()) + ['ALTRO'],
                       help='Filtra per grado istruzione')
    
    # Campionamento
    parser.add_argument('--sample-per-strato', type=int, help='N scuole per ogni strato')
    parser.add_argument('--sample-total', type=int, help='N totale campionate proporzionalmente')
    parser.add_argument('--max', type=int, help='Numero massimo assoluto')
    
    # Opzioni
    parser.add_argument('--reset', action='store_true', help='Reset stato e ricomincia')
    parser.add_argument('--dry-run', action='store_true', help='Mostra stratificazione senza scaricare')
    parser.add_argument('--seed', type=int, default=42, help='Seed per riproducibilità')
    
    args = parser.parse_args()
    
    # Seed per riproducibilità
    random.seed(args.seed)
    
    # Crea directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Stato
    if args.reset and STATE_FILE.exists():
        STATE_FILE.unlink()
        logger.info("🔄 Stato resettato")
    
    state = DownloadState(STATE_FILE)
    
    # Carica scuole
    schools = []
    
    if args.statali or args.tutte:
        if ANAGRAFE_STAT.exists():
            logger.info(f"📖 Caricamento scuole statali da {ANAGRAFE_STAT.name}...")
            schools.extend(load_schools_statali(ANAGRAFE_STAT))
        else:
            logger.error(f"File non trovato: {ANAGRAFE_STAT}")
    
    if args.paritarie or args.tutte:
        if ANAGRAFE_PAR.exists():
            logger.info(f"📖 Caricamento scuole paritarie da {ANAGRAFE_PAR.name}...")
            schools.extend(load_schools_paritarie(ANAGRAFE_PAR))
        else:
            logger.error(f"File non trovato: {ANAGRAFE_PAR}")
    
    if not schools:
        logger.error("Nessuna scuola caricata!")
        return
    
    logger.info(f"📚 Totale scuole caricate: {len(schools)}")
    
    # Applica filtri
    if args.regioni:
        regioni_upper = [r.upper() for r in args.regioni]
        schools = [s for s in schools if s.regione.upper() in regioni_upper]
        logger.info(f"🔍 Dopo filtro regioni: {len(schools)}")
    
    if args.province:
        province_upper = [p.upper() for p in args.province]
        schools = [s for s in schools if s.provincia.upper() in province_upper]
        logger.info(f"🔍 Dopo filtro province: {len(schools)}")
    
    if args.aree:
        schools = [s for s in schools if s.area_geografica in args.aree]
        logger.info(f"🔍 Dopo filtro aree: {len(schools)}")
    
    if args.solo_metropolitane:
        schools = [s for s in schools if s.is_metropolitana]
        logger.info(f"🔍 Dopo filtro metropolitane: {len(schools)}")
    
    if args.solo_non_metropolitane:
        schools = [s for s in schools if not s.is_metropolitana]
        logger.info(f"🔍 Dopo filtro non-metropolitane: {len(schools)}")
    
    if args.gradi:
        schools = [s for s in schools if s.grado_normalizzato in args.gradi]
        logger.info(f"🔍 Dopo filtro gradi: {len(schools)}")
    
    if not schools:
        logger.warning("Nessuna scuola dopo i filtri!")
        return
    
    # Stratifica
    strata = stratify_schools(schools)
    print_stratification_summary(strata)
    
    # Campionamento
    if args.sample_per_strato:
        schools = sample_stratified(strata, n_per_stratum=args.sample_per_strato)
        logger.info(f"🎲 Campionamento: {args.sample_per_strato} per strato → {len(schools)} scuole")
    elif args.sample_total:
        schools = sample_stratified(strata, total_n=args.sample_total, proportional=True)
        logger.info(f"🎲 Campionamento proporzionale: {len(schools)} scuole")
    
    # Limite massimo
    if args.max and len(schools) > args.max:
        schools = schools[:args.max]
        logger.info(f"✂️ Limitato a {args.max} scuole")
    
    if args.dry_run:
        logger.info("\n🔍 DRY RUN - Nessun download")
        logger.info(f"Scuole da processare: {len(schools)}")
        
        # Mostra alcuni esempi per strato
        strata_sample = stratify_schools(schools)
        for strato, strato_schools in list(strata_sample.items())[:5]:
            logger.info(f"\n📌 {strato} ({len(strato_schools)} scuole):")
            for s in strato_schools[:2]:
                logger.info(f"   {s.codice}: {s.denominazione[:40]}")
        
        if len(strata_sample) > 5:
            logger.info(f"\n   ... e altri {len(strata_sample)-5} strati")
        return
    
    # Esegui download
    _set_download_lock(True)
    try:
        run_download(schools, state, DOWNLOAD_DIR)
    finally:
        _set_download_lock(False)


if __name__ == "__main__":
    main()
