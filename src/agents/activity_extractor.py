#!/usr/bin/env python3
"""
Activity Extractor - Estrae e cataloga le attività di orientamento dai file MD dei PTOF.

Strategia:
1. Legge i file MD da ptof_md/ (testo già estratto dai PDF)
2. Usa Ollama per estrarre e categorizzare le attività
3. Salva in data/attivita.csv (dati) e attivita.json (metadata)
4. Traccia il progresso per evitare ri-elaborazioni
"""

import os
import sys
import json
import csv
import uuid
import time
import signal
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

try:
    import requests
except ImportError:
    print("Errore: requests non installato. Esegui: pip install requests")
    sys.exit(1)

# Setup directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PTOF_MD_DIR = BASE_DIR / "ptof_md"
ANALYSIS_DIR = BASE_DIR / "analysis_results"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Output files
OUTPUT_CSV = DATA_DIR / "attivita.csv"
OUTPUT_JSON = DATA_DIR / "attivita.json"  # Solo metadata
REGISTRY_FILE = DATA_DIR / "activity_registry.json"

# Colonne CSV
CSV_COLUMNS = [
    'id', 'codice_meccanografico', 'nome_scuola', 'tipo_scuola', 'ordine_grado',
    'regione', 'provincia', 'comune', 'area_geografica', 'territorio', 'statale_paritaria',
    'categoria', 'titolo', 'descrizione', 'metodologia', 'tipologie_metodologia',
    'ambiti_attivita', 'target', 'citazione_ptof', 'pagina_evidenza',
    'maturity_index', 'partnership_coinvolte', 'extracted_at', 'model_used', 'source_file'
]

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'activity_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ollama settings
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"
DEFAULT_MODEL = "qwen3:32b"
DEFAULT_WAIT = 2
DEFAULT_CHUNK_SIZE = 30000
MAX_RETRIES = 3
REQUEST_TIMEOUT = 300

# Categorie buone pratiche
CATEGORIE = [
    "Metodologie Didattiche Innovative",
    "Progetti e Attività Esemplari",
    "Partnership e Collaborazioni Strategiche",
    "Azioni di Sistema e Governance",
    "Buone Pratiche per l'Inclusione",
    "Esperienze Territoriali Significative"
]

# Tipologie di metodologia didattica
TIPOLOGIE_METODOLOGIA = [
    "STEM/STEAM",
    "Coding e Pensiero Computazionale",
    "Flipped Classroom",
    "Peer Education/Tutoring",
    "Problem Based Learning",
    "Cooperative Learning",
    "Gamification",
    "Debate",
    "Service Learning",
    "Outdoor Education",
    "Didattica Laboratoriale",
    "Didattica Digitale",
    "CLIL",
    "Storytelling",
    "Project Work",
    "Learning by Doing",
    "Mentoring",
    "Altro"
]

# Ambiti di attività
AMBITI_ATTIVITA = [
    "Orientamento",
    "Inclusione e BES",
    "PCTO/Alternanza",
    "Cittadinanza e Legalità",
    "Educazione Civica",
    "Sostenibilità e Ambiente",
    "Digitalizzazione",
    "Lingue Straniere",
    "Arte e Creatività",
    "Musica e Teatro",
    "Sport e Benessere",
    "Scienze e Ricerca",
    "Lettura e Scrittura",
    "Matematica e Logica",
    "Imprenditorialità",
    "Intercultura",
    "Prevenzione Disagio",
    "Continuità e Accoglienza",
    "Valutazione e Autovalutazione",
    "Formazione Docenti",
    "Rapporti con Famiglie",
    "Altro"
]

# Tipologie di istituto
TIPOLOGIE_ISTITUTO = [
    "Liceo Classico",
    "Liceo Scientifico",
    "Liceo Linguistico",
    "Liceo Artistico",
    "Liceo Musicale e Coreutico",
    "Liceo delle Scienze Umane",
    "Istituto Tecnico",
    "Istituto Professionale",
    "Istituto Comprensivo",
    "Circolo Didattico",
    "Scuola Secondaria I Grado",
    "Scuola Primaria",
    "Scuola dell'Infanzia",
    "CPIA",
    "Convitto/Educandato",
    "Altro"
]

# Ordine e grado
ORDINI_GRADO = [
    "Infanzia",
    "Primaria",
    "Secondaria I Grado",
    "Secondaria II Grado"
]

# Flag per uscita controllata
EXIT_REQUESTED = False


def graceful_exit_handler(signum, frame):
    """Handler per uscita controllata con Ctrl+C."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED:
        print("\n\nUscita forzata.", flush=True)
        sys.exit(1)
    EXIT_REQUESTED = True
    print("\n\nUSCITA RICHIESTA - Completamento file corrente e salvataggio...", flush=True)


signal.signal(signal.SIGINT, graceful_exit_handler)


def compute_file_hash(file_path: Path) -> str:
    """Calcola hash SHA256 di un file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def extract_school_code_from_filename(filename: str) -> Optional[str]:
    """Estrae il codice meccanografico dal nome del file MD.

    Pattern tipici: RMIC8GA002_ptof.md, AGPC010001_ptof.md
    Il codice meccanografico italiano è di 10 caratteri alfanumerici.
    """
    import re
    # Pattern per file MD: CODICE_ptof.md
    patterns = [
        r'^([A-Z]{2}[A-Z0-9]{8})_ptof\.md$',  # Standard: CODICE_ptof.md
        r'^([A-Z]{2}[A-Z0-9]{8})_',  # Con underscore dopo
        r'^([A-Z]{2}[A-Z0-9]{8})',  # Solo codice all'inizio
    ]

    for pattern in patterns:
        match = re.search(pattern, filename.upper())
        if match:
            return match.group(1)

    return None


class BestPracticeExtractor:
    """Agente per estrarre buone pratiche dai file MD dei PTOF."""

    def __init__(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_MODEL,
        wait_time: int = DEFAULT_WAIT,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.wait_time = wait_time
        self.chunk_size = chunk_size

        # Dati
        self.practices: List[Dict] = []
        self.processed_files: Dict[str, Dict] = {}
        self.schools_metadata: Dict[str, Dict] = {}

        # Carica CSV per metadati
        self._load_schools_csv()

    def _load_schools_csv(self):
        """Carica i metadati delle scuole dal CSV."""
        import csv
        csv_path = DATA_DIR / "analysis_summary.csv"

        if csv_path.exists():
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        school_id = row.get('school_id', '')
                        if school_id:
                            self.schools_metadata[school_id] = {
                                'denominazione': row.get('denominazione', ''),
                                'tipo_scuola': row.get('tipo_scuola', ''),
                                'tipo_scuola_dettaglio': row.get('tipo_scuola_dettaglio', ''),
                                'ordine_grado': row.get('ordine_grado', ''),
                                'regione': row.get('regione', ''),
                                'provincia': row.get('provincia', ''),
                                'comune': row.get('comune', ''),
                                'area_geografica': row.get('area_geografica', ''),
                                'territorio': row.get('territorio', ''),
                                'statale_paritaria': row.get('statale_paritaria', ''),
                                'ptof_orientamento_maturity_index': row.get('ptof_orientamento_maturity_index', ''),
                            }
                logger.info(f"Caricati metadati di {len(self.schools_metadata)} scuole dal CSV")
            except Exception as e:
                logger.warning(f"Errore caricamento CSV: {e}")

    def get_school_metadata(self, school_code: str) -> Dict:
        """Recupera metadati completi per una scuola."""
        metadata = {
            "codice_meccanografico": school_code,
            "nome": "",
            "tipo_scuola": "",
            "tipo_scuola_dettaglio": "",
            "ordine_grado": "",
            "regione": "",
            "provincia": "",
            "comune": "",
            "area_geografica": "",
            "territorio": "",
            "statale_paritaria": ""
        }

        # Prima prova il CSV
        if school_code in self.schools_metadata:
            csv_data = self.schools_metadata[school_code]
            metadata.update({
                "nome": csv_data.get('denominazione', ''),
                "tipo_scuola": csv_data.get('tipo_scuola', ''),
                "tipo_scuola_dettaglio": csv_data.get('tipo_scuola_dettaglio', ''),
                "ordine_grado": csv_data.get('ordine_grado', ''),
                "regione": csv_data.get('regione', ''),
                "provincia": csv_data.get('provincia', ''),
                "comune": csv_data.get('comune', ''),
                "area_geografica": csv_data.get('area_geografica', ''),
                "territorio": csv_data.get('territorio', ''),
                "statale_paritaria": csv_data.get('statale_paritaria', ''),
            })
            return metadata

        # Fallback: prova il JSON di analisi
        json_path = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta = data.get('metadata', {})
                    metadata.update({
                        "nome": meta.get('denominazione', ''),
                        "tipo_scuola": meta.get('tipo_scuola', ''),
                        "tipo_scuola_dettaglio": meta.get('tipo_scuola_dettaglio', ''),
                        "ordine_grado": meta.get('ordine_grado', ''),
                        "regione": meta.get('regione', ''),
                        "provincia": meta.get('provincia', ''),
                        "comune": meta.get('comune', ''),
                        "area_geografica": meta.get('area_geografica', ''),
                        "territorio": meta.get('territorio', ''),
                        "statale_paritaria": meta.get('statale_paritaria', ''),
                    })
            except Exception as e:
                logger.warning(f"Errore lettura JSON per {school_code}: {e}")

        return metadata

    def get_school_context(self, school_code: str) -> Dict:
        """Recupera il contesto (punteggi, partnership) per una scuola."""
        context = {
            "maturity_index": None,
            "punteggi_dimensionali": {},
            "partnership_coinvolte": [],
            "attivita_correlate": []
        }

        # Prova il CSV per maturity index
        if school_code in self.schools_metadata:
            try:
                mi = self.schools_metadata[school_code].get('ptof_orientamento_maturity_index', '')
                if mi:
                    context["maturity_index"] = float(mi)
            except (ValueError, TypeError):
                pass

        # Prova il JSON di analisi per dettagli
        json_path = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sec2 = data.get('ptof_section2', {})

                    # Partnership
                    partners = sec2.get('2_2_partnership', {}).get('partner_nominati', [])
                    if partners:
                        context["partnership_coinvolte"] = partners[:20]  # Max 20

                    # Punteggi dimensionali
                    for key, value in sec2.items():
                        if isinstance(value, dict) and 'score' in value:
                            clean_key = key.replace('2_', '').replace('_', ' ')
                            context["punteggi_dimensionali"][clean_key] = value.get('score')

                    # Attivita dal registro
                    activities = data.get('activities_register', [])
                    if activities:
                        context["attivita_correlate"] = [
                            a.get('titolo_attivita', '') for a in activities[:10]
                            if a.get('titolo_attivita')
                        ]
            except Exception as e:
                logger.warning(f"Errore lettura contesto per {school_code}: {e}")

        return context

    def read_md_file(self, md_path: Path) -> str:
        """Legge il contenuto di un file MD.

        Returns:
            str: testo del file MD
        """
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Errore lettura file {md_path}: {e}")
            return ""

    def smart_split(self, text: str) -> List[str]:
        """Divide il testo in chunk intelligenti basandosi su sezioni markdown."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        current = ""

        # Dividi per sezioni markdown (## o ###)
        import re
        # Split mantenendo i delimitatori
        sections = re.split(r'(^#{2,3}\s+[^\n]+)', text, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            if len(current) + len(section) <= self.chunk_size:
                current += "\n" + section
            else:
                if current:
                    chunks.append(current.strip())

                # Se la sezione singola e troppo grande, dividila per paragrafi
                if len(section) > self.chunk_size:
                    paragraphs = section.split('\n\n')
                    current = ""
                    for para in paragraphs:
                        if len(current) + len(para) <= self.chunk_size:
                            current += "\n\n" + para if current else para
                        else:
                            if current:
                                chunks.append(current.strip())
                            current = para
                else:
                    current = section

        if current:
            chunks.append(current.strip())

        # Assicurati che non ci siano chunk vuoti
        chunks = [c for c in chunks if len(c.strip()) > 100]

        return chunks if chunks else [text[:self.chunk_size]]

    def build_extraction_prompt(self, chunk: str, chunk_num: int, total_chunks: int, school_code: str) -> str:
        """Costruisce il prompt per l'estrazione delle buone pratiche."""
        metodologie_str = ", ".join(TIPOLOGIE_METODOLOGIA[:-1])  # Escludi "Altro"
        ambiti_str = ", ".join(AMBITI_ATTIVITA[:-1])  # Escludi "Altro"

        return f"""/no_think
SEI UN ESPERTO DI PRATICHE EDUCATIVE E ORIENTAMENTO SCOLASTICO.

ANALIZZA questo estratto di PTOF scolastico e IDENTIFICA le BUONE PRATICHE concrete.

SCUOLA: {school_code}
CHUNK: {chunk_num}/{total_chunks}

TESTO DA ANALIZZARE:
{chunk[:25000]}

---

CATEGORIE DISPONIBILI (usa ESATTAMENTE questi nomi):
1. "Metodologie Didattiche Innovative" - tecniche didattiche avanzate, approcci pedagogici innovativi
2. "Progetti e Attività Esemplari" - progetti strutturati, attività significative documentate
3. "Partnership e Collaborazioni Strategiche" - accordi con enti, università, imprese, associazioni
4. "Azioni di Sistema e Governance" - coordinamento, monitoraggio, strutture organizzative
5. "Buone Pratiche per l'Inclusione" - BES, DSA, disabilità, integrazione stranieri
6. "Esperienze Territoriali Significative" - legame col territorio, PCTO, stage

TIPOLOGIE DI METODOLOGIA (scegli UNA o PIU tra queste, oppure "Altro"):
{metodologie_str}

AMBITI DI ATTIVITA (scegli UNO o PIU tra questi, oppure "Altro"):
{ambiti_str}

PER OGNI BUONA PRATICA IDENTIFICATA, ESTRAI:
- "categoria": una delle 6 categorie sopra (ESATTAMENTE come scritto)
- "titolo": nome sintetico della pratica (max 100 caratteri)
- "descrizione": descrizione dettagliata di cosa consiste e come funziona (200-500 caratteri)
- "metodologia_desc": come viene implementata concretamente (testo libero)
- "tipologie_metodologia": ARRAY di tipologie metodologiche applicabili (es: ["STEM/STEAM", "Didattica Laboratoriale"])
- "ambiti_attivita": ARRAY di ambiti di attività (es: ["Orientamento", "Digitalizzazione"])
- "target": a chi è rivolta (studenti, docenti, famiglie, classi specifiche)
- "citazione_ptof": citazione testuale rilevante dal documento (max 200 caratteri)
- "pagina_evidenza": numero di pagina se menzionato (es: "Pagina 15") o "Non specificata"
- "partnership_coinvolte": lista di partner nominati se categoria è Partnership, altrimenti array vuoto

REGOLE FONDAMENTALI:
1. Estrai SOLO pratiche CONCRETE e SPECIFICHE con un nome o una descrizione chiara
2. IGNORA dichiarazioni generiche tipo "la scuola promuove l'orientamento"
3. Ogni pratica DEVE avere evidenze testuali nel documento
4. Se non trovi pratiche significative in questo chunk, rispondi con array vuoto
5. MAX 5 pratiche per chunk (seleziona le piu significative)
6. Il titolo deve essere SPECIFICO (es: "Laboratorio di Robotica Educativa", non "Attivita di laboratorio")
7. tipologie_metodologia e ambiti_attivita devono essere ARRAY di stringhe (anche se c'è un solo elemento)

RISPONDI SOLO con JSON valido (nessun testo prima o dopo):
{{
  "pratiche": [
    {{
      "categoria": "Nome Categoria Esatto",
      "titolo": "Nome Specifico Pratica",
      "descrizione": "Descrizione dettagliata...",
      "metodologia_desc": "Come viene implementata...",
      "tipologie_metodologia": ["STEM/STEAM", "Didattica Laboratoriale"],
      "ambiti_attivita": ["Orientamento", "Digitalizzazione"],
      "target": "A chi è rivolta",
      "citazione_ptof": "Citazione dal documento...",
      "pagina_evidenza": "Pagina X",
      "partnership_coinvolte": []
    }}
  ]
}}

Se non trovi pratiche significative:
{{"pratiche": []}}"""

    def call_ollama(self, prompt: str) -> Optional[str]:
        """Chiama Ollama API con retry."""
        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 16384,
                "num_predict": -1
            }
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', '')
                else:
                    logger.warning(f"Errore Ollama {response.status_code}")
                    time.sleep(5)

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout Ollama (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(10)
            except requests.exceptions.ConnectionError:
                logger.error(f"Connessione fallita a {self.ollama_url}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Errore chiamata Ollama: {e}")
                time.sleep(5)

        return None

    def parse_practices_response(self, response: str) -> List[Dict]:
        """Parsa la risposta JSON da Ollama."""
        if not response:
            return []

        import re

        # Pulisci la risposta
        cleaned = response.strip()

        # Rimuovi eventuali code blocks markdown
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

        # Cerca il JSON
        try:
            # Prima prova parsing diretto
            data = json.loads(cleaned)
            return data.get('pratiche', [])
        except json.JSONDecodeError:
            pass

        # Prova a trovare il JSON nella risposta
        json_match = re.search(r'\{[\s\S]*"pratiche"[\s\S]*\}', cleaned)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data.get('pratiche', [])
            except json.JSONDecodeError:
                pass

        logger.warning("Impossibile parsare risposta JSON")
        return []

    def validate_practice(self, practice: Dict) -> bool:
        """Valida una pratica estratta."""
        # Campi obbligatori
        required = ['categoria', 'titolo', 'descrizione']
        for field in required:
            if not practice.get(field):
                return False

        # Categoria valida
        if practice['categoria'] not in CATEGORIE:
            # Prova a correggere categoria simile
            for cat in CATEGORIE:
                if cat.lower() in practice['categoria'].lower() or practice['categoria'].lower() in cat.lower():
                    practice['categoria'] = cat
                    break
            else:
                return False

        # Titolo non generico
        generic_titles = ['attività', 'progetto', 'laboratorio', 'orientamento', 'formazione']
        if practice['titolo'].lower().strip() in generic_titles:
            return False

        # Descrizione minima
        if len(practice['descrizione']) < 50:
            return False

        return True

    def is_similar_practice(self, p1: Dict, p2: Dict, threshold: float = 0.7) -> bool:
        """Verifica se due pratiche sono simili (potenziali duplicati).

        Usa la similarità dei titoli e delle descrizioni.
        """
        import difflib

        # Confronta titoli
        title1 = p1.get('pratica', {}).get('titolo', '').lower().strip()
        title2 = p2.get('pratica', {}).get('titolo', '').lower().strip()

        # Se i titoli sono identici, sono duplicati
        if title1 == title2:
            return True

        # Calcola similarità del titolo
        title_sim = difflib.SequenceMatcher(None, title1, title2).ratio()
        if title_sim > 0.85:
            return True

        # Se i titoli sono molto simili e stessa categoria, sono duplicati
        cat1 = p1.get('pratica', {}).get('categoria', '')
        cat2 = p2.get('pratica', {}).get('categoria', '')
        if cat1 == cat2 and title_sim > threshold:
            return True

        return False

    def deduplicate_practices(self, practices: List[Dict]) -> List[Dict]:
        """Rimuove pratiche duplicate o molto simili.

        Mantiene la pratica con la descrizione più lunga.
        """
        if not practices:
            return practices

        unique_practices = []

        for practice in practices:
            is_duplicate = False

            for existing in unique_practices:
                if self.is_similar_practice(practice, existing):
                    is_duplicate = True
                    # Se la nuova ha descrizione più lunga, sostituisci
                    new_desc = practice.get('pratica', {}).get('descrizione', '')
                    old_desc = existing.get('pratica', {}).get('descrizione', '')
                    if len(new_desc) > len(old_desc):
                        unique_practices.remove(existing)
                        unique_practices.append(practice)
                    break

            if not is_duplicate:
                unique_practices.append(practice)

        return unique_practices

    def process_md_file(self, md_path: Path) -> List[Dict]:
        """Processa un singolo file MD ed estrae le pratiche."""
        school_code = extract_school_code_from_filename(md_path.name)
        if not school_code:
            logger.warning(f"Impossibile estrarre codice da {md_path.name}")
            return []

        logger.info(f"Lettura file {md_path.name}...")
        text = self.read_md_file(md_path)

        if not text or len(text) < 500:
            logger.warning(f"Testo insufficiente da {md_path.name}")
            return []

        logger.info(f"  {len(text)} caratteri")

        # Chunk il testo
        chunks = self.smart_split(text)
        logger.info(f"  {len(chunks)} chunk da processare")

        # Recupera metadati e contesto
        school_metadata = self.get_school_metadata(school_code)
        school_context = self.get_school_context(school_code)

        all_practices = []

        for i, chunk in enumerate(chunks, 1):
            if EXIT_REQUESTED:
                break

            logger.info(f"  Chunk {i}/{len(chunks)}...")

            prompt = self.build_extraction_prompt(chunk, i, len(chunks), school_code)
            response = self.call_ollama(prompt)

            if response:
                practices = self.parse_practices_response(response)

                for practice in practices:
                    if self.validate_practice(practice):
                        # Normalizza tipologie_metodologia come array
                        tipologie_met = practice.get('tipologie_metodologia', [])
                        if isinstance(tipologie_met, str):
                            tipologie_met = [tipologie_met] if tipologie_met else []

                        # Normalizza ambiti_attivita come array
                        ambiti = practice.get('ambiti_attivita', [])
                        if isinstance(ambiti, str):
                            ambiti = [ambiti] if ambiti else []

                        # Costruisci oggetto completo
                        full_practice = {
                            "id": str(uuid.uuid4()),
                            "school": school_metadata,
                            "pratica": {
                                "categoria": practice.get('categoria', ''),
                                "titolo": practice.get('titolo', ''),
                                "descrizione": practice.get('descrizione', ''),
                                "metodologia": practice.get('metodologia_desc', practice.get('metodologia', '')),
                                "tipologie_metodologia": tipologie_met,
                                "ambiti_attivita": ambiti,
                                "target": practice.get('target', ''),
                                "citazione_ptof": practice.get('citazione_ptof', ''),
                                "pagina_evidenza": practice.get('pagina_evidenza', '')
                            },
                            "contesto": school_context,
                            "metadata": {
                                "extracted_at": datetime.now().isoformat(),
                                "model_used": self.model,
                                "source_file": md_path.name,
                                "chunk_source": i
                            }
                        }

                        # Se la pratica e di tipo Partnership, aggiungi i partner
                        if practice.get('partnership_coinvolte'):
                            full_practice["contesto"]["partnership_coinvolte"] = practice['partnership_coinvolte']

                        all_practices.append(full_practice)

                logger.info(f"    {len(practices)} pratiche estratte ({sum(1 for p in practices if self.validate_practice(p))} valide)")

            # Pausa tra chunk
            if i < len(chunks):
                time.sleep(self.wait_time)

        # Deduplicazione pratiche simili tra i vari chunk
        original_count = len(all_practices)
        all_practices = self.deduplicate_practices(all_practices)
        if original_count != len(all_practices):
            logger.info(f"  Deduplicazione: {original_count} -> {len(all_practices)} pratiche uniche")

        return all_practices

    def _list_to_pipe(self, value):
        """Converte lista in stringa separata da |."""
        if isinstance(value, list):
            return '|'.join(str(v) for v in value if v)
        elif value:
            return str(value)
        return ''

    def _pipe_to_list(self, value):
        """Converte stringa separata da | in lista."""
        if not value or value == '':
            return []
        return [v.strip() for v in str(value).split('|') if v.strip()]

    def _practice_to_row(self, practice: Dict) -> Dict:
        """Converte una pratica nested in una riga flat per CSV."""
        school = practice.get('school', {})
        pratica = practice.get('pratica', {})
        contesto = practice.get('contesto', {})
        metadata = practice.get('metadata', {})

        return {
            'id': practice.get('id', ''),
            'codice_meccanografico': school.get('codice_meccanografico', ''),
            'nome_scuola': school.get('nome', ''),
            'tipo_scuola': school.get('tipo_scuola', ''),
            'ordine_grado': school.get('ordine_grado', ''),
            'regione': school.get('regione', ''),
            'provincia': school.get('provincia', ''),
            'comune': school.get('comune', ''),
            'area_geografica': school.get('area_geografica', ''),
            'territorio': school.get('territorio', ''),
            'statale_paritaria': school.get('statale_paritaria', ''),
            'categoria': pratica.get('categoria', ''),
            'titolo': pratica.get('titolo', ''),
            'descrizione': pratica.get('descrizione', ''),
            'metodologia': pratica.get('metodologia', ''),
            'tipologie_metodologia': self._list_to_pipe(pratica.get('tipologie_metodologia', [])),
            'ambiti_attivita': self._list_to_pipe(pratica.get('ambiti_attivita', [])),
            'target': pratica.get('target', ''),
            'citazione_ptof': pratica.get('citazione_ptof', ''),
            'pagina_evidenza': pratica.get('pagina_evidenza', ''),
            'maturity_index': contesto.get('maturity_index', ''),
            'partnership_coinvolte': self._list_to_pipe(contesto.get('partnership_coinvolte', [])),
            'extracted_at': metadata.get('extracted_at', ''),
            'model_used': metadata.get('model_used', ''),
            'source_file': metadata.get('source_file', '')
        }

    def _row_to_practice(self, row: Dict) -> Dict:
        """Converte una riga CSV in struttura pratica nested."""
        maturity = row.get('maturity_index', '')
        try:
            maturity = float(maturity) if maturity else None
        except (ValueError, TypeError):
            maturity = None

        return {
            'id': row.get('id', ''),
            'school': {
                'codice_meccanografico': row.get('codice_meccanografico', ''),
                'nome': row.get('nome_scuola', ''),
                'tipo_scuola': row.get('tipo_scuola', ''),
                'ordine_grado': row.get('ordine_grado', ''),
                'regione': row.get('regione', ''),
                'provincia': row.get('provincia', ''),
                'comune': row.get('comune', ''),
                'area_geografica': row.get('area_geografica', ''),
                'territorio': row.get('territorio', ''),
                'statale_paritaria': row.get('statale_paritaria', '')
            },
            'pratica': {
                'categoria': row.get('categoria', ''),
                'titolo': row.get('titolo', ''),
                'descrizione': row.get('descrizione', ''),
                'metodologia': row.get('metodologia', ''),
                'tipologie_metodologia': self._pipe_to_list(row.get('tipologie_metodologia', '')),
                'ambiti_attivita': self._pipe_to_list(row.get('ambiti_attivita', '')),
                'target': row.get('target', ''),
                'citazione_ptof': row.get('citazione_ptof', ''),
                'pagina_evidenza': row.get('pagina_evidenza', '')
            },
            'contesto': {
                'maturity_index': maturity,
                'partnership_coinvolte': self._pipe_to_list(row.get('partnership_coinvolte', ''))
            },
            'metadata': {
                'extracted_at': row.get('extracted_at', ''),
                'model_used': row.get('model_used', ''),
                'source_file': row.get('source_file', '')
            }
        }

    def load_progress(self):
        """Carica il progresso e le pratiche esistenti."""
        # Carica registry
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    data = json.load(f)
                    self.processed_files = data.get('processed_files', {})
                logger.info(f"Registry caricato: {len(self.processed_files)} file processati")
            except Exception as e:
                logger.warning(f"Errore caricamento registry: {e}")

        # Carica pratiche esistenti da CSV
        if OUTPUT_CSV.exists():
            try:
                with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.practices = [self._row_to_practice(row) for row in reader]
                logger.info(f"Pratiche esistenti caricate da CSV: {len(self.practices)}")
            except Exception as e:
                logger.warning(f"Errore caricamento pratiche CSV: {e}")

    def save_progress(self):
        """Salva il progresso e le pratiche."""
        # Salva registry
        registry_data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "processed_files": self.processed_files
        }
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(registry_data, f, indent=2)

        # Salva pratiche in CSV
        rows = [self._practice_to_row(p) for p in self.practices]
        with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)

        # Salva metadata in JSON (senza le pratiche)
        schools_processed = len(set(p['school']['codice_meccanografico'] for p in self.practices))
        metadata = {
            "version": "2.0",
            "format": "csv",
            "csv_file": "attivita.csv",
            "last_updated": datetime.now().isoformat(),
            "extraction_model": self.model,
            "total_practices": len(self.practices),
            "schools_processed": schools_processed
        }
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Salvate {len(self.practices)} pratiche in CSV")

    def get_md_files_to_process(self, force: bool = False, target: str = None) -> List[Path]:
        """Ottiene la lista dei file MD da processare."""
        md_files = []

        # Cerca nella directory ptof_md
        if PTOF_MD_DIR.exists():
            for md_file in PTOF_MD_DIR.glob("*_ptof.md"):
                school_code = extract_school_code_from_filename(md_file.name)
                if not school_code:
                    continue

                # Se target specificato, processa solo quello
                if target and school_code.upper() != target.upper():
                    continue

                # Se force, processa tutti
                if force:
                    md_files.append(md_file)
                    continue

                # Controlla se gia processato
                if school_code in self.processed_files:
                    # Verifica se il file e cambiato
                    file_hash = compute_file_hash(md_file)
                    if self.processed_files[school_code].get('file_hash') == file_hash:
                        continue  # Gia processato e non cambiato

                md_files.append(md_file)

        # Ordina per data di modifica
        md_files.sort(key=lambda p: p.stat().st_mtime)

        return md_files

    def run(self, limit: int = None, force: bool = False, target: str = None):
        """Esegue l'estrazione delle attivita."""
        logger.info("Avvio Activity Extractor")
        logger.info(f"  Modello: {self.model}")
        logger.info(f"  Ollama URL: {self.ollama_url}")
        logger.info(f"  Chunk size: {self.chunk_size}")
        logger.info(f"  Directory MD: {PTOF_MD_DIR}")

        # Carica progresso
        self.load_progress()

        # Ottieni file MD da processare
        md_files = self.get_md_files_to_process(force=force, target=target)

        if limit:
            md_files = md_files[:limit]

        logger.info(f"File MD da processare: {len(md_files)}")

        if not md_files:
            logger.info("Nessun nuovo file MD da processare")
            return

        processed_count = 0

        for i, md_file in enumerate(md_files, 1):
            if EXIT_REQUESTED:
                break

            school_code = extract_school_code_from_filename(md_file.name)
            logger.info(f"\n[{i}/{len(md_files)}] {md_file.name} ({school_code})")

            # Processa file MD
            practices = self.process_md_file(md_file)

            if practices:
                # Rimuovi pratiche vecchie per questa scuola
                self.practices = [p for p in self.practices
                                  if p['school']['codice_meccanografico'] != school_code]

                # Aggiungi nuove pratiche
                self.practices.extend(practices)
                logger.info(f"  Aggiunte {len(practices)} pratiche per {school_code}")

            # Aggiorna registry
            self.processed_files[school_code] = {
                "file_hash": compute_file_hash(md_file),
                "processed_at": datetime.now().isoformat(),
                "practices_count": len(practices),
                "model_used": self.model
            }

            # Salva progresso
            self.save_progress()
            processed_count += 1

            # Pausa tra file
            if i < len(md_files):
                time.sleep(self.wait_time)

        # Riepilogo finale
        logger.info("\n" + "=" * 50)
        logger.info(f"COMPLETATO: {processed_count} file MD processati")
        logger.info(f"Totale pratiche: {len(self.practices)}")

        # Statistiche per categoria
        cat_counts = {}
        for p in self.practices:
            cat = p['pratica']['categoria']
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        logger.info("\nDistribuzione per categoria:")
        for cat in CATEGORIE:
            count = cat_counts.get(cat, 0)
            logger.info(f"  {cat}: {count}")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description='Activity Extractor - Estrae attività dai PDF PTOF')
    parser.add_argument('--model', default=DEFAULT_MODEL, help=f'Modello Ollama (default: {DEFAULT_MODEL})')
    parser.add_argument('--ollama-url', default=DEFAULT_OLLAMA_URL, help=f'URL Ollama (default: {DEFAULT_OLLAMA_URL})')
    parser.add_argument('--limit', type=int, help='Limita il numero di PDF da processare')
    parser.add_argument('--wait', type=int, default=DEFAULT_WAIT, help=f'Secondi di attesa tra chunk (default: {DEFAULT_WAIT})')
    parser.add_argument('--chunk-size', type=int, default=DEFAULT_CHUNK_SIZE, help=f'Dimensione chunk (default: {DEFAULT_CHUNK_SIZE})')
    parser.add_argument('--force', action='store_true', help='Forza ri-elaborazione di tutti i PDF')
    parser.add_argument('--target', help='Processa solo questo codice meccanografico')

    args = parser.parse_args()

    extractor = BestPracticeExtractor(
        ollama_url=args.ollama_url,
        model=args.model,
        wait_time=args.wait,
        chunk_size=args.chunk_size
    )

    extractor.run(
        limit=args.limit,
        force=args.force,
        target=args.target
    )


if __name__ == '__main__':
    main()
