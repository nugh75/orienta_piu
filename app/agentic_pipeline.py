#!/usr/bin/env python3
"""
Agentic Pipeline for PTOF Analysis
Architecture:
1. Analyst (Gemma-3 27B): Extraction & Drafting
2. Reviewer (Qwen-3 32B): Red Teaming & Critique
3. Refiner (GPT-OSS 20B): Polishing & Fixes
"""
import os
import json
import logging
import requests
import time
import re
from glob import glob
from dotenv import load_dotenv
from src.utils.file_utils import atomic_write, is_valid_markdown, ensure_string_content

# Load environment variables from .env file
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'pipeline_config.json'))

try:
    import src.llm.client
    import importlib
    importlib.reload(src.llm.client)
    from src.llm.client import LLMClient
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import src.llm.client
    import importlib
    importlib.reload(src.llm.client)
    from src.llm.client import LLMClient

def load_pipeline_config():
    default_config = {
        "active_preset": 0,
        "presets": {
            "0": {
                "name": "Local Ollama",
                "type": "ollama",
                "models": {
                    "analyst": "gemma3:27b",
                    "reviewer": "qwen3:32b",
                    "refiner": "gemma3:27b",
                    "synthesizer": "gemma3:27b"
                },
                "ollama_url": "http://192.168.129.14:11434/api/generate"
            }
        },
        "chunking": {
            "chunk_size": 40000,
            "long_doc_threshold": 60000
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                # Deep merge for presets if needed, but simple update is fine for now
                if 'active_preset' in user_config:
                    default_config['active_preset'] = user_config['active_preset']
                if 'presets' in user_config:
                    default_config['presets'].update(user_config['presets'])
                if 'chunking' in user_config:
                    default_config['chunking'].update(user_config['chunking'])
            logging.info(f"Loaded pipeline config from {CONFIG_FILE}")
        except Exception as e:
            logging.warning(f"Error loading config file {CONFIG_FILE}: {e}")
    else:
        logging.info(f"Config file not found at {CONFIG_FILE}, using defaults")
            
    return default_config

PIPELINE_CONFIG = load_pipeline_config()
LLM_CLIENT = LLMClient(PIPELINE_CONFIG)

# Get active models
active_preset = str(PIPELINE_CONFIG.get('active_preset', '0'))
preset_config = PIPELINE_CONFIG.get('presets', {}).get(active_preset, {})
# Fallback to preset 0 if active preset is missing in presets
if not preset_config:
    preset_config = PIPELINE_CONFIG.get('presets', {}).get('0', {})

models_config = preset_config.get('models', {})
OLLAMA_URL = preset_config.get('ollama_url', "http://localhost:11434/api/generate") # Keep for backward compat if needed

MD_DIR = "ptof_md"
RESULTS_DIR = "analysis_results"

# Chunking configuration
CHUNK_SIZE = PIPELINE_CONFIG['chunking']['chunk_size']       # Max chars per chunk for Ollama (smaller context)
LONG_DOC_THRESHOLD = PIPELINE_CONFIG['chunking']['long_doc_threshold']  # Use chunking for docs longer than this

# Import chunker and utilities
try:
    from src.processing.text_chunker import smart_split, get_chunk_info
    from src.utils.school_code_parser import extract_canonical_code
    from src.utils.constants import (
        SIGLA_PROVINCIA_MAP,
        PROVINCE_METROPOLITANE,
        get_territorio,
        get_geo_from_sigla,
        normalize_area_geografica
    )
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.processing.text_chunker import smart_split, get_chunk_info
    from src.utils.school_code_parser import extract_canonical_code
    from src.utils.constants import (
        SIGLA_PROVINCIA_MAP,
        PROVINCE_METROPOLITANE,
        get_territorio,
        get_geo_from_sigla,
        normalize_area_geografica
    )

# Models
MODEL_ANALYST = models_config.get('analyst', 'gemma3:27b')
MODEL_REVIEWER = models_config.get('reviewer', 'qwen3:32b')
MODEL_REFINER = models_config.get('refiner', 'gemma3:27b')
MODEL_SYNTHESIZER = models_config.get('synthesizer', 'gemma3:27b')
METADATA_LLM_MODEL = os.environ.get("METADATA_LLM_MODEL", MODEL_REVIEWER)

try:
    from src.utils.config_loader import load_prompts
except ImportError:
    # Fallback for running as script from app/ dir (though recommended run is from root)
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.utils.config_loader import load_prompts

# Load global prompts
PROMPTS = load_prompts()

# Load Metadata Caches for JSON Enrichment
import pandas as pd

def load_metadata_caches():
    """Load metadata from CSV sources."""
    caches = {'enrichment': {}, 'school_db': None}
    
    # Enrichment (official registry)
    if os.path.exists('data/metadata_enrichment.csv'):
        try:
            df = pd.read_csv('data/metadata_enrichment.csv', dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('school_id', '')).strip()
                if code:
                    caches['enrichment'][code] = row.to_dict()
        except Exception as e:
            logging.warning(f"Failed to load enrichment: {e}")
    
    # Load SchoolDatabase for complete metadata
    try:
        from src.utils.school_database import SchoolDatabase
        caches['school_db'] = SchoolDatabase()
        logging.info(f"Loaded SchoolDatabase with {len(caches['school_db']._data)} schools")
    except Exception as e:
        logging.warning(f"Failed to load SchoolDatabase: {e}")
    
    return caches

METADATA_CACHES = load_metadata_caches()


def _infer_school_level_from_text(text):
    if not text:
        return {}
    sample = text[:20000].lower()
    
    types = []
    grades = []
    
    if 'infanzia' in sample or 'materna' in sample:
        types.append('Infanzia')
        grades.append('Infanzia')
        
    if 'primaria' in sample or 'elementare' in sample or 'direzione didattica' in sample:
        types.append('Primaria')
        grades.append('Primaria')
        
    if re.search(r'(scuola\s+media|secondaria\s+di\s+primo|\bi\s*grado\b|\b1\W*grado\b)', sample):
        types.append('I Grado')
        grades.append('I Grado')
        
    if re.search(r'liceo', sample):
        types.append('Liceo')
        grades.append('II Grado')
        
    if re.search(r'(istituto\s+tecnico|\btecnico\b|itis|itc|itg)', sample):
        types.append('Tecnico')
        grades.append('II Grado')
        
    if re.search(r'(istituto\s+professionale|\bprofessionale\b|ipsia|ipc)', sample):
        types.append('Professionale')
        grades.append('II Grado')
        
    if 'comprensivo' in sample:
        if 'Infanzia' not in types: types.append('Infanzia')
        if 'Primaria' not in types: types.append('Primaria')
        if 'I Grado' not in types: types.append('I Grado')
        
        if 'Infanzia' not in grades: grades.append('Infanzia')
        if 'Primaria' not in grades: grades.append('Primaria')
        if 'I Grado' not in grades: grades.append('I Grado')
        if 'Comprensivo' not in grades: grades.append('Comprensivo')

    result = {}
    if types:
        result['tipo_scuola'] = ', '.join(sorted(list(set(types))))
    if grades:
        result['ordine_grado'] = ', '.join(sorted(list(set(grades))))
        
    return result


def _is_missing_value(value):
    if value is None:
        return True
    raw = str(value).strip()
    if not raw:
        return True
    return raw.lower() in {'nd', 'n/d', 'n/a', 'null', 'none', 'nan'}


def _is_missing_metadata(field, value):
    if _is_missing_value(value):
        return True
    if field == 'tipo_scuola' and str(value).strip().lower() == 'istituto superiore':
        return True
    return False


def _extract_regex_metadata(text):
    data = {}
    if not text:
        return data

    email_re = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    lower = text.lower()

    pec_match = re.search(r'pec\s*[:\-]?\s*(' + email_re + r')', lower)
    if pec_match:
        data['pec'] = pec_match.group(1).strip().lower()

    email_match = re.search(r'email\s*[:\-]?\s*(' + email_re + r')', lower)
    if email_match:
        data['email'] = email_match.group(1).strip().lower()

    if 'email' not in data:
        emails = re.findall(email_re, text)
        if emails:
            data['email'] = emails[0].strip().lower()

    url_match = re.search(r'(https?://\S+|www\.\S+)', text, re.IGNORECASE)
    if url_match:
        url = url_match.group(1).strip().strip(').,;]')
        data['website'] = url.lower()

    cap_match = re.search(r'\bCAP\s*[:\-]?\s*(\d{5})\b', text, re.IGNORECASE)
    if cap_match:
        data['cap'] = cap_match.group(1).strip()

    return data


def _collect_keyword_snippets(text, keywords, window=600, max_snippets=6):
    if not text or not keywords:
        return []

    lower = text.lower()
    spans = []
    for kw in keywords:
        if len(spans) >= max_snippets:
            break
        kw_lower = kw.lower()
        for match in re.finditer(re.escape(kw_lower), lower):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            spans.append((start, end))
            if len(spans) >= max_snippets:
                break

    if not spans:
        return []

    spans.sort()
    merged = []
    for start, end in spans:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return [text[start:end].strip() for start, end in merged]


def _build_llm_context(text, fields):
    keywords_by_field = {
        'denominazione': [
            'istituto comprensivo', 'istituto tecnico', 'istituto professionale',
            'istituto superiore', 'liceo', 'iis', 'i.i.s', 'ipsia', 'itc', 'itcg',
            'direzione didattica', 'scuola'
        ],
        'comune': ['comune di', 'sede', 'indirizzo', 'via', 'viale', 'piazza', 'corso'],
        'indirizzo': ['indirizzo', 'via', 'viale', 'piazza', 'corso', 'sede'],
        'ordine_grado': [
            'infanzia', 'primaria', 'elementare', 'scuola media',
            'secondaria di primo', 'i grado', 'primo grado',
            'secondaria di secondo', 'ii grado', 'secondo grado', 'comprensivo'
        ],
        'tipo_scuola': [
            'liceo', 'tecnico', 'professionale', 'primaria', 'infanzia',
            'scuola media', 'secondaria di primo', 'secondaria di secondo', 'comprensivo',
            'istituto superiore'
        ],
        'statale_paritaria': ['statale', 'paritaria', 'paritario', 'non statale'],
        'provincia': ['provincia'],
        'regione': ['regione'],
        'email': ['email', 'posta elettronica'],
        'pec': ['pec'],
        'website': ['sito', 'www', 'http'],
        'cap': ['cap']
    }

    keywords = []
    for field in fields:
        keywords.extend(keywords_by_field.get(field, []))

    snippets = _collect_keyword_snippets(text, keywords, window=600, max_snippets=6)
    if not snippets:
        return ""

    context = "\n\n---\n\n".join(snippets)
    return context[:6000]


def _call_metadata_llm(context, fields):
    if not context or not fields:
        return {}

    fields_str = ", ".join(fields)
    prompt = (
        "Sei un assistente che estrae metadati da estratti di un PTOF.\n"
        "Devi compilare SOLO questi campi: " + fields_str + ".\n"
        "Regole:\n"
        "- Usa SOLO informazioni presenti negli estratti.\n"
        "- Per ogni campo restituisci un oggetto con \"value\" e \"evidence\".\n"
        "- evidence deve essere una citazione breve COPIATA dagli estratti.\n"
        "- Se non trovi informazioni, usa null per value e evidence.\n"
        "- Non inventare.\n"
        "- tipo_scuola deve essere una di: Infanzia, Primaria, I Grado, Liceo, Tecnico, Professionale.\n"
        "- ordine_grado deve essere una di: Infanzia, Primaria, I Grado, II Grado.\n"
        "- statale_paritaria deve essere una di: Statale, Paritaria.\n"
        "Restituisci SOLO JSON.\n\n"
        "ESTRATTI:\n<<<\n" + context + "\n>>>"
    )

    try:
        raw = LLM_CLIENT.generate(
            model=METADATA_LLM_MODEL,
            prompt=prompt,
            temperature=0.1,
            max_tokens=8192
        )
        if not raw:
            logging.warning(f"Metadata LLM returned empty response")
            return {}
            
        cleaned = sanitize_json(raw)
        return json.loads(cleaned) if cleaned else {}
    except Exception as e:
        logging.warning(f"Metadata LLM exception: {e}")
        return {}


def _normalize_metadata_value(field, value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    lower = raw.lower()

    if field == 'tipo_scuola':
        if 'liceo' in lower:
            return 'Liceo'
        if 'tecnico' in lower:
            return 'Tecnico'
        if 'professionale' in lower:
            return 'Professionale'
        if 'primaria' in lower or 'elementare' in lower:
            return 'Primaria'
        if 'infanzia' in lower:
            return 'Infanzia'
        if 'media' in lower or 'primo grado' in lower or 'i grado' in lower:
            return 'I Grado'
        return None

    if field == 'ordine_grado':
        if 'infanzia' in lower:
            return 'Infanzia'
        if 'primaria' in lower or 'elementare' in lower:
            return 'Primaria'
        if 'primo grado' in lower or 'i grado' in lower:
            return 'I Grado'
        if 'secondo grado' in lower or 'ii grado' in lower:
            return 'II Grado'
        return None

    if field == 'statale_paritaria':
        if 'paritaria' in lower:
            return 'Paritaria'
        if 'statale' in lower:
            return 'Statale'
        return None

    if field in {'email', 'pec', 'website'}:
        return raw.lower()

    if field == 'provincia':
        if len(raw) == 2:
            return raw.upper()
        return raw.title()

    if field in {'comune', 'regione', 'denominazione'}:
        return raw.title()

    return raw


def _evidence_in_context(evidence, context):
    if not evidence or not context:
        return False
    return evidence.strip().lower() in context.lower()


def _apply_metadata_sync(meta, school_code):
    ordine = meta.get('ordine_grado', '')
    tipo_scuola = meta.get('tipo_scuola', '')
    if str(tipo_scuola).strip().lower() == 'istituto superiore':
        meta['tipo_scuola'] = 'ND'
        tipo_scuola = 'ND'

    if ordine in ['Infanzia', 'Primaria'] and (not tipo_scuola or tipo_scuola == 'ND'):
        meta['tipo_scuola'] = ordine
    if ordine == 'I Grado' and (not tipo_scuola or tipo_scuola == 'ND'):
        meta['tipo_scuola'] = 'I Grado'
    if tipo_scuola in ['Liceo', 'Tecnico', 'Professionale'] and (not ordine or ordine == 'ND'):
        meta['ordine_grado'] = 'II Grado'
    if ordine == 'II Grado' and (not tipo_scuola or tipo_scuola == 'ND'):
        meta['tipo_scuola'] = 'II Grado'

    if _is_missing_value(meta.get('area_geografica')):
        try:
            meta['area_geografica'] = normalize_area_geografica(
                meta.get('area_geografica', ''),
                regione=meta.get('regione'),
                provincia_sigla=school_code[:2]
            )
        except TypeError:
            meta['area_geografica'] = normalize_area_geografica(meta.get('area_geografica', ''))

    provincia = meta.get('provincia', '')
    meta['territorio'] = get_territorio(provincia)


def fill_missing_metadata_with_llm(json_path, md_path, school_code, status_callback=None):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logging.warning(f"LLM scan skipped, failed to load {json_path}: {e}")
        return False

    meta = data.get('metadata', {})
    if str(meta.get('tipo_scuola', '')).strip().lower() == 'istituto superiore':
        meta['tipo_scuola'] = 'ND'
        logging.info(f"LLM scan: treating 'Istituto Superiore' as ND for {school_code}")
    scan_fields = [
        'denominazione', 'comune', 'provincia', 'regione', 'ordine_grado',
        'tipo_scuola', 'indirizzo', 'cap', 'email', 'pec', 'website', 'statale_paritaria'
    ]
    missing = [f for f in scan_fields if _is_missing_metadata(f, meta.get(f))]
    if not missing:
        return False

    if not md_path or not os.path.exists(md_path):
        logging.info(f"LLM scan skipped, MD missing for {school_code}")
        return False

    try:
        with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
            md_text = f.read()
    except Exception as e:
        logging.warning(f"LLM scan skipped, failed to read MD for {school_code}: {e}")
        return False

    regex_updates = _extract_regex_metadata(md_text)
    updated = {}
    for field, value in regex_updates.items():
        if field in missing and not _is_missing_value(value):
            meta[field] = _normalize_metadata_value(field, value)
            updated[field] = meta[field]

    missing = [f for f in missing if _is_missing_value(meta.get(f))]
    llm_fields = [f for f in missing if f not in {'cap', 'email', 'pec', 'website'}]

    if llm_fields:
        context = _build_llm_context(md_text, llm_fields)
        if context:
            if status_callback:
                status_callback("LLM metadata scan: extracting missing fields...")
            llm_data = _call_metadata_llm(context, llm_fields)
            if isinstance(llm_data, dict):
                for field in llm_fields:
                    entry = llm_data.get(field)
                    if not isinstance(entry, dict):
                        continue
                    value = entry.get('value')
                    evidence = entry.get('evidence')
                    if _is_missing_value(value) or _is_missing_value(evidence):
                        continue
                    if not _evidence_in_context(str(evidence), context):
                        continue
                    normalized = _normalize_metadata_value(field, value)
                    if normalized:
                        meta[field] = normalized
                        updated[field] = normalized
        else:
            logging.info(f"LLM scan skipped for {school_code}: no keyword context for {llm_fields}")

    remaining = [f for f in scan_fields if _is_missing_metadata(f, meta.get(f))]
    if not updated:
        if remaining:
            logging.info(f"LLM metadata scan found no updates for {school_code}; still missing: {remaining}")
        return False

    _apply_metadata_sync(meta, school_code)
    data['metadata'] = meta

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info(f"LLM metadata updated for {school_code}: {sorted(updated.keys())}")
        return True
    except Exception as e:
        logging.warning(f"LLM metadata write failed for {school_code}: {e}")
        return False


def _find_md_path(school_code):
    candidates = [
        os.path.join(MD_DIR, f"{school_code}_ptof.md"),
        os.path.join(MD_DIR, f"{school_code}_PTOF.md"),
        os.path.join(MD_DIR, f"{school_code}.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _infer_school_level_from_md(md_path):
    if not md_path or not os.path.exists(md_path):
        return {}
    try:
        with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
            return _infer_school_level_from_text(f.read())
    except Exception:
        return {}


def enrich_json_metadata(json_path, school_code_raw, force_school_id=True, md_path=None):
    """
    Enrich JSON file with metadata from SchoolDatabase, enrichment cache, and province code fallback.

    Args:
        json_path: Path to the JSON file to enrich
        school_code_raw: Raw school code (from filename)
        force_school_id: If True, always use school_code from filename (overrides LLM value)

    Priority for fields:
        school_id:       ALWAYS from filename (if force_school_id=True)
        denominazione:   SchoolDB > LLM > enrichment > "ND"
        comune:          SchoolDB > LLM > enrichment > "ND"
        provincia:       SchoolDB > SIGLA fallback (ignores LLM - too unreliable)
        regione:         SchoolDB > SIGLA fallback (ignores LLM - too unreliable)
        area_geografica: SchoolDB > SIGLA fallback (ignores LLM - too unreliable)
        territorio:      Calculated from provincia (Metropolitano/Non Metropolitano)
    """
    school_code = extract_canonical_code(school_code_raw)

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        if 'metadata' not in data:
            data['metadata'] = {}

        enrich = METADATA_CACHES['enrichment'].get(school_code, {})
        school_db = METADATA_CACHES.get('school_db')

        # Get data from SchoolDatabase (most complete source)
        db_data = {}
        if school_db:
            db_data = school_db.get_school_data(school_code) or {}

        # FALLBACK DEFINITIVO: derive from province code (first 2 letters)
        geo_fallback = get_geo_from_sigla(school_code)

        # CRITICAL: school_id MUST come from filename, not from LLM
        if force_school_id:
            data['metadata']['school_id'] = school_code
        else:
            data['metadata']['school_id'] = data['metadata'].get('school_id') or school_code

        # Basic info - SchoolDB has priority over LLM for accuracy
        data['metadata']['denominazione'] = db_data.get('denominazione') or data['metadata'].get('denominazione') or enrich.get('denominazione') or 'ND'
        data['metadata']['comune'] = db_data.get('comune') or data['metadata'].get('comune') or enrich.get('comune') or 'ND'
        data['metadata']['ordine_grado'] = db_data.get('ordine_grado') or data['metadata'].get('ordine_grado') or enrich.get('ordine_grado') or 'ND'
        data['metadata']['tipo_scuola'] = db_data.get('tipo_scuola') or data['metadata'].get('tipo_scuola') or 'ND'
        if str(data['metadata'].get('tipo_scuola', '')).strip().lower() == 'istituto superiore':
            data['metadata']['tipo_scuola'] = 'ND'

        # Geographic fields - SchoolDB > SIGLA fallback (LLM values are unreliable for geography)
        data['metadata']['provincia'] = db_data.get('provincia') or geo_fallback['provincia']
        data['metadata']['regione'] = db_data.get('regione') or geo_fallback['regione']
        area_raw = db_data.get('area_geografica') or geo_fallback['area_geografica']
        try:
            data['metadata']['area_geografica'] = normalize_area_geografica(
                area_raw,
                regione=data['metadata'].get('regione'),
                provincia_sigla=school_code[:2]
            )
        except TypeError:
            data['metadata']['area_geografica'] = normalize_area_geografica(area_raw)

        md_path = md_path or _find_md_path(school_code)
        md_inferred = _infer_school_level_from_md(md_path)
        if data['metadata'].get('ordine_grado') in ['ND', '', None] and md_inferred.get('ordine_grado'):
            data['metadata']['ordine_grado'] = md_inferred['ordine_grado']
        if data['metadata'].get('tipo_scuola') in ['ND', '', None] and md_inferred.get('tipo_scuola'):
            data['metadata']['tipo_scuola'] = md_inferred['tipo_scuola']

        ordine = data['metadata'].get('ordine_grado', '')
        tipo_scuola = data['metadata'].get('tipo_scuola', '')
        if ordine in ['Infanzia', 'Primaria'] and (not tipo_scuola or tipo_scuola == 'ND'):
            data['metadata']['tipo_scuola'] = ordine
        if ordine == 'I Grado' and (not tipo_scuola or tipo_scuola == 'ND'):
            data['metadata']['tipo_scuola'] = 'I Grado'
        if tipo_scuola in ['Liceo', 'Tecnico', 'Professionale'] and (not ordine or ordine == 'ND'):
            data['metadata']['ordine_grado'] = 'II Grado'
        if ordine == 'II Grado' and (not tipo_scuola or tipo_scuola == 'ND'):
            data['metadata']['tipo_scuola'] = 'II Grado'

        # Other fields from SchoolDatabase
        data['metadata']['statale_paritaria'] = db_data.get('statale_paritaria') or data['metadata'].get('statale_paritaria') or 'ND'
        data['metadata']['indirizzo'] = db_data.get('indirizzo') or data['metadata'].get('indirizzo') or 'ND'
        data['metadata']['cap'] = db_data.get('cap') or data['metadata'].get('cap') or 'ND'
        data['metadata']['email'] = db_data.get('email') or data['metadata'].get('email') or 'ND'
        data['metadata']['pec'] = db_data.get('pec') or data['metadata'].get('pec') or 'ND'
        data['metadata']['website'] = db_data.get('website') or data['metadata'].get('website') or 'ND'

        # Calculate territorio from provincia using centralized function
        provincia = data['metadata'].get('provincia', '')
        data['metadata']['territorio'] = get_territorio(provincia)

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"Enriched metadata for {school_code}: provincia={data['metadata'].get('provincia')}, regione={data['metadata'].get('regione')}, territorio={data['metadata'].get('territorio')}")
        return True
    except Exception as e:
        logging.error(f"Failed to enrich {json_path}: {e}")
        return False

class BaseAgent:
    def __init__(self, model_name, role):
        self.model = model_name
        self.role = role

    def call_llm(self, prompt, context=""):
        # Construct system prompt and user prompt separately for better compatibility
        system_prompt = f"Sei un {self.role}."
        user_prompt = f"Context: {context}\nUser: {prompt}"
        
        try:
            response = LLM_CLIENT.generate(
                model=self.model,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=16000
            )
            return response
        except Exception as e:
            logging.error(f"Exception calling {self.model}: {e}")
            return ""

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_ANALYST, "Analista Esperto di PTOF e Documenti Scolastici")

    def draft_report(self, ptof_text):
        logging.info(f"[{self.model}] Drafting report...")
        prompt_template = PROMPTS.get("Analyst", "")
        if not prompt_template:
            logging.error("Analyst prompt missing")
            return ""
            
        return self.call_llm(prompt_template, context=ptof_text)
    
    def draft_chunk(self, chunk_text, chunk_num, total_chunks):
        """Analyze a single chunk of the document."""
        logging.info(f"[{self.model}] Drafting chunk {chunk_num}/{total_chunks}...")
        prompt_template = PROMPTS.get("Analyst", "")
        if not prompt_template:
            return ""
        
        chunk_prompt = f"""{prompt_template}

NOTA: Questa è la SEZIONE {chunk_num} di {total_chunks} del documento PTOF.
Analizza SOLO questa sezione e restituisci i punteggi trovati."""
        
        return self.call_llm(chunk_prompt, context=chunk_text)


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes multiple partial analyses into one."""
    def __init__(self):
        super().__init__(MODEL_SYNTHESIZER, "Sintetizzatore di Analisi Multiple")
    
    def synthesize(self, partial_results):
        """Combine multiple JSON analyses into one unified result."""
        logging.info(f"[{self.model}] Synthesizing {len(partial_results)} partial results...")
        
        synthesis_prompt = f"""Sei un sintetizzatore di analisi PTOF.
Hai ricevuto {len(partial_results)} analisi parziali dello stesso documento PTOF.

ISTRUZIONI:
1. Unifica tutte le analisi in un singolo JSON completo
2. Per ogni indicatore con punteggio, scegli il punteggio PIÙ ALTO trovato
3. Per liste (partner, attività), combina tutti gli elementi unici
4. Per metadata, usa i valori non-ND trovati
5. Restituisci SOLO il JSON unificato, nessun altro testo

ANALISI PARZIALI:
{json.dumps(partial_results, indent=2, ensure_ascii=False)}

JSON UNIFICATO:"""
        
        return self.call_llm(synthesis_prompt)

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REVIEWER, "Revisore Critico e Logico (Red Teaming)")

    def critique_report(self, source_text, draft_report):
        logging.info(f"[{self.model}] Critiquing report...")
        
        if not draft_report:
            logging.error("[Reviewer] draft_report is None or empty!")
            return None
            
        prompt_template = PROMPTS.get("Reviewer", "")
        if not prompt_template:
            logging.error("[Reviewer] Reviewer prompt not found!")
            return None
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", str(draft_report))
        return self.call_llm(prompt, context=source_text)

class RefinerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REFINER, "Editor Finale e Correttore")

    def refine_report(self, draft_report, critique):
        logging.info(f"[{self.model}] Refining report...")
        
        if not draft_report:
            logging.error("[Refiner] draft_report is None or empty!")
            return None
        if not critique:
            logging.warning("[Refiner] critique is None - using empty string")
            critique = ""
            
        prompt_template = PROMPTS.get("Refiner", "")
        if not prompt_template:
            logging.error("[Refiner] Refiner prompt not found!")
            return None
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", str(draft_report)).replace("{{CRITIQUE}}", str(critique))
        return self.call_llm(prompt)

class NarrativeAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REFINER, "Redattore di Report Narrativi PTOF")

    def generate_narrative(self, analysis_json, school_code):
        prompt_template = PROMPTS.get("Narrative", "")
        if not prompt_template:
            prompt_template = (
                "Usa il JSON nel contesto per scrivere un report narrativo in Markdown. "
                "Mantieni la struttura: 1. Sintesi Generale, 2. Analisi Dimensionale "
                "(con sottosezioni 2.1-2.7), 3. Punti di Forza, 4. Aree di Debolezza, "
                "5. Gap Analysis, 6. Conclusioni. "
                "Evita elenchi puntati, usa prosa fluida e metti in **grassetto** "
                "attivita, partner e concetti chiave. "
                "Titolo: # Analisi del PTOF {{SCHOOL_CODE}}."
            )
        prompt = prompt_template.replace("{{SCHOOL_CODE}}", str(school_code))
        return self.call_llm(prompt, context=json.dumps(analysis_json, ensure_ascii=False, indent=2))


def sanitize_json(text):
    """Extract valid JSON object from LLM response."""
    text = text.strip()
    
    # Remove markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Find the JSON object boundaries
    start = text.find('{')
    if start == -1:
        return text
    
    # Find matching closing brace
    depth = 0
    end = start
    for i, char in enumerate(text[start:], start):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    
    return text[start:end+1]


def process_single_ptof(md_file, analyst, reviewer, refiner, synthesizer=None, results_dir=RESULTS_DIR, status_callback=None):
    """
    Process a single PTOF file through the Agentic Pipeline.
    Automatically uses chunked analysis for long documents.
    status_callback: function(msg) to report progress
    """
    md_stem = os.path.splitext(os.path.basename(md_file))[0]
    school_code = extract_canonical_code(md_stem)
    output_base = f"{school_code}_PTOF"
    final_md_path = os.path.join(results_dir, f"{output_base}_analysis.md")
    final_json_path = os.path.join(results_dir, f"{output_base}_analysis.json")
    
    if status_callback: status_callback(f"Processing {school_code}...")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content_size = len(content)
    
    # Check if we need chunked analysis
    if content_size > LONG_DOC_THRESHOLD:
        logging.info(f"[Pipeline] Long document ({content_size} chars) - using chunked analysis")
        if status_callback: status_callback(f"Long doc ({content_size//1000}k chars) - chunking...")
        
        # Split document
        chunks = smart_split(content, CHUNK_SIZE)
        info = get_chunk_info(chunks)
        logging.info(f"[Pipeline] Split into {info['count']} chunks")
        
        # Analyze each chunk
        partial_results = []
        for i, chunk in enumerate(chunks):
            if status_callback: status_callback(f"Analyst: Chunk {i+1}/{len(chunks)}...")
            
            chunk_draft = analyst.draft_chunk(chunk, i+1, len(chunks))
            if chunk_draft:
                chunk_draft = sanitize_json(chunk_draft)
                try:
                    partial_json = json.loads(chunk_draft)
                    partial_results.append(partial_json)
                except:
                    logging.warning(f"[Pipeline] Chunk {i+1} parse failed")
        
        if not partial_results:
            logging.error("[Pipeline] No valid chunk results")
            return None
        
        # Synthesize if we have a synthesizer
        if synthesizer and len(partial_results) > 1:
            if status_callback: status_callback("Synthesizer: Combining results...")
            draft = synthesizer.synthesize(partial_results)
            draft = sanitize_json(draft)
        elif len(partial_results) == 1:
            draft = json.dumps(partial_results[0])
        else:
            # Manual merge if no synthesizer
            from src.processing.cloud_review import merge_partial_analyses
            merged = merge_partial_analyses(partial_results)
            draft = json.dumps(merged)
    else:
        # Standard single-pass analysis
        if status_callback: status_callback("Analyst: Drafting report...")
        draft = analyst.draft_report(content)
        if not draft: return None
        draft = sanitize_json(draft)
    
    # Save Draft JSON (will be enriched AFTER refinement)
    try:
        atomic_write(final_json_path, draft)
    except:
        pass

    # Extract content for review - use full draft if narrative is empty
    narrative_text = ""
    narrative_for_review = draft
    try:
        draft_json = json.loads(draft)
        narrative_text = draft_json.get('narrative', '') or ""
        if narrative_text:
            narrative_for_review = narrative_text
    except Exception:
        pass

    # 2. Critique
    if status_callback: status_callback("Reviewer: Critiquing...")
    critique = reviewer.critique_report(content, narrative_for_review)
    
    if critique:
        logging.info(f"Reviewer says: {critique[:100]}...")
    else:
        logging.warning("Reviewer returned None - skipping review step")
        critique = ""
    
    # 3. Refine (only if critique has content)
    final_output = narrative_text
    refined_json_str = None
    if critique and "APPROVATO" not in critique.upper() and len(critique) > 10:
         if status_callback: status_callback("Refiner: Improving report...")
         refined_json_str = refiner.refine_report(draft, critique)
         
         if refined_json_str:
             refined_json_str = sanitize_json(refined_json_str)
             try:
                 refined_data = json.loads(refined_json_str)
                 atomic_write(final_json_path, refined_json_str)
                 
                 final_output = refined_data.get('narrative', '')
             except Exception as e:
                 logging.error(f"Failed to parse Refiner JSON: {e}")
         else:
             logging.warning("Refiner returned None - keeping original draft")
    else:
         logging.info("Report approved directly or no critique available.")

    # CRITICAL: Enrich JSON with MIUR metadata AFTER all LLM processing is complete
    # This ensures metadata is not overwritten by Refiner output
    if status_callback: status_callback("Enriching metadata from MIUR database...")
    enrich_json_metadata(final_json_path, school_code, force_school_id=True, md_path=md_file)
    fill_missing_metadata_with_llm(final_json_path, md_file, school_code, status_callback=status_callback)

    analysis_data = None
    narrative_from_json = ""
    try:
        with open(final_json_path, 'r') as f:
            analysis_data = json.load(f)
        narrative_from_json = analysis_data.get('narrative', '') or ""
    except Exception:
        analysis_data = None

    # SAFETY CHECK: Calculate Maturity Index and discard if too low (<= 2.0)
    # This prevents saving "garbage" analyses where the model found nothing relevant.
    if analysis_data:
        try:
            # Calculate index locally to avoid dependency on rebuild_csv
            sec2 = analysis_data.get('ptof_section2', {})
            
            def _get_scores(section_key, subsection_keys):
                scores = []
                section = sec2.get(section_key, {})
                for key in subsection_keys:
                    try:
                        val = section.get(key, {}).get('score', 0)
                        scores.append(float(val) if val is not None else 0)
                    except:
                        scores.append(0)
                return scores

            def _calc_avg(scores):
                valid = [s for s in scores if s > 0]
                return sum(valid) / len(valid) if valid else 0

            # 1. Finalita
            s_fin = _get_scores('2_3_finalita', [
                'finalita_attitudini', 'finalita_interessi', 'finalita_progetto_vita',
                'finalita_transizioni_formative', 'finalita_capacita_orientative_opportunita'
            ])
            
            # 2. Obiettivi
            s_obi = _get_scores('2_4_obiettivi', [
                'obiettivo_ridurre_abbandono', 'obiettivo_continuita_territorio',
                'obiettivo_contrastare_neet', 'obiettivo_lifelong_learning'
            ])
            
            # 3. Governance
            s_gov = _get_scores('2_5_azioni_sistema', [
                'azione_coordinamento_servizi', 'azione_dialogo_docenti_studenti',
                'azione_rapporto_scuola_genitori', 'azione_monitoraggio_azioni',
                'azione_sistema_integrato_inclusione_fragilita'
            ])
            
            # 4. Didattica
            s_did = _get_scores('2_6_didattica_orientativa', [
                'didattica_da_esperienza_studenti', 'didattica_laboratoriale',
                'didattica_flessibilita_spazi_tempi', 'didattica_interdisciplinare'
            ])
            
            # 5. Opportunita
            s_opp = _get_scores('2_7_opzionali_facoltative', [
                'opzionali_culturali', 'opzionali_laboratoriali_espressive',
                'opzionali_ludiche_ricreative', 'opzionali_volontariato', 'opzionali_sportive'
            ])
            
            means = [
                _calc_avg(s_fin), _calc_avg(s_obi), _calc_avg(s_gov), 
                _calc_avg(s_did), _calc_avg(s_opp)
            ]
            ro_index = _calc_avg(means)
            
            logging.info(f"Calculated RO Index for {school_code}: {ro_index:.2f}")
            
            if ro_index <= 2.0:
                msg = f"⚠️ SAFETY CHECK: RO Index {ro_index:.2f} is too low (<= 2.0). Discarding analysis for {school_code}."
                logging.warning(msg)
                if status_callback: status_callback(msg)
                
                # Delete artifacts
                if os.path.exists(final_json_path): os.remove(final_json_path)
                if os.path.exists(final_md_path): os.remove(final_md_path)
                
                # Also delete legacy files if any
                legacy_json = os.path.join(output_dir, f"{school_code}_analysis.json")
                legacy_md = os.path.join(output_dir, f"{school_code}_analysis.md")
                if os.path.exists(legacy_json): os.remove(legacy_json)
                if os.path.exists(legacy_md): os.remove(legacy_md)
                
                return None
                
        except Exception as e:
            logging.error(f"Error in Safety Check: {e}")

    if narrative_from_json:
        final_output = narrative_from_json

    # Ensure final_output is a string
    final_output = ensure_string_content(final_output)

    # Check if it's valid markdown (not JSON dump)
    if not final_output or not is_valid_markdown(final_output):
        logging.info(f"Output looks like JSON or is empty. Attempting to generate narrative...")
        if analysis_data:
            narrative_agent = NarrativeAgent()
            generated = narrative_agent.generate_narrative(analysis_data, school_code)
            if generated and str(generated).strip():
                final_output = str(generated).strip()
                analysis_data['narrative'] = final_output
                try:
                    atomic_write(final_json_path, json.dumps(analysis_data, ensure_ascii=False, indent=2))
                except Exception as e:
                    logging.warning(f"Failed to store narrative in JSON: {e}")

    # Final check
    final_output = ensure_string_content(final_output)
    if not final_output or not is_valid_markdown(final_output):
        final_output = "Report narrativo non disponibile. Rigenera l'analisi."

    # Save Final MD
    atomic_write(final_md_path, final_output)
    
    # Return parsed JSON result
    try:
        with open(final_json_path, 'r') as f:
             return json.load(f)
    except:
        return {}

def run_pipeline():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    md_files = glob(os.path.join(MD_DIR, "*.md"))
    logging.info(f"Found {len(md_files)} markdown files to process.")
    
    analyst = AnalystAgent()
    reviewer = ReviewerAgent()
    refiner = RefinerAgent()
    synthesizer = SynthesizerAgent()
    
    for md_file in md_files:
        md_stem = os.path.splitext(os.path.basename(md_file))[0]
        school_code = extract_canonical_code(md_stem)
        output_base = f"{school_code}_PTOF"
        final_md_path = os.path.join(RESULTS_DIR, f"{output_base}_analysis.md")
        legacy_md_path = os.path.join(RESULTS_DIR, f"{school_code}_analysis.md")
        
        if os.path.exists(final_md_path) or os.path.exists(legacy_md_path):
            logging.info(f"Skipping {school_code} (Already completed)")
            continue
            
        logging.info(f"___ Processing {school_code} ___")
        
        process_single_ptof(md_file, analyst, reviewer, refiner, synthesizer)
        
        # Aggiorna CSV per dashboard dopo ogni analisi
        try:
            import subprocess
            result = subprocess.run(
                ['python3', 'src/processing/rebuild_csv_clean.py'],
                capture_output=True,
                timeout=120,
                text=True
            )
            if result.returncode == 0:
                logging.info(f"CSV aggiornato per {school_code}")
            else:
                logging.warning(f"rebuild_csv_clean.py warning: {result.stderr[:200] if result.stderr else 'unknown'}")
        except Exception as e:
            logging.warning(f"CSV rebuild failed: {e}")

if __name__ == "__main__":
    run_pipeline()
