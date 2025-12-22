#!/usr/bin/env python3
"""
Workflow PTOF - Sistema di processamento automatico
Struttura cartelle:
- ptof_inbox/ : PDF da analizzare
- ptof_processed/ : PDF già analizzati (con timestamp)
- ptof_md/ : File Markdown generati
- analysis_results/ : Risultati analisi JSON
"""

import os
import sys
import shutil
import logging
from datetime import datetime
from glob import glob
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/workflow_ptof.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directory configuration
INBOX_DIR = "ptof_inbox"
PROCESSED_DIR = "ptof_processed"
MD_DIR = "ptof_md"
ANALYSIS_DIR = "analysis_results"
LOGS_DIR = "logs"

# Ensure directories exist
for directory in [INBOX_DIR, PROCESSED_DIR, MD_DIR, ANALYSIS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"📂 Directory verificata: {directory}/")

import re

# Import school database for validation
try:
    from src.utils.school_database import SchoolDatabase
    SCHOOL_DB = SchoolDatabase()
except Exception as e:
    logger.warning(f"⚠️ Impossibile caricare SchoolDatabase: {e}")
    SCHOOL_DB = None

# Import PTOF validator for pre-processing
try:
    from src.validation.ptof_validator import PTOFValidator, ValidationResult
    PTOF_VALIDATOR = PTOFValidator()
except Exception as e:
    logger.warning(f"⚠️ Impossibile caricare PTOFValidator: {e}")
    PTOF_VALIDATOR = None

def extract_school_code_from_filename(filename):
    """
    Estrae il codice scuola canonico dal nome file.
    Es: 'AGPC010001_PTOF.pdf' → 'AGPC010001'
        'AGPC010001.pdf' → 'AGPC010001'
        'MIIS08900V_Piano_Triennale.pdf' → 'MIIS08900V'
    Il codice scuola italiano è tipicamente 10 caratteri alfanumerici.
    """
    basename = os.path.basename(filename)
    name_without_ext = os.path.splitext(basename)[0]
    
    # Pattern: codice scuola italiano (2 lettere regione + 2 lettere tipo + 6 caratteri alfanumerici)
    match = re.match(r'^([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})', name_without_ext.upper())
    if match:
        return match.group(1)
    
    # Fallback: prendi tutto prima del primo underscore o trattino
    parts = re.split(r'[_\-\s]', name_without_ext)
    if parts and len(parts[0]) >= 10:
        return parts[0].upper()[:10]
    
    return name_without_ext.upper()

def extract_school_code_from_content(md_content: str, filename_code: str = None) -> tuple:
    """
    Estrae il codice meccanografico reale dal contenuto del documento.
    Usa LLM per trovare il codice e lo valida contro il database delle scuole.
    
    Returns:
        tuple: (codice_trovato, fonte, is_validated)
        - codice_trovato: il codice meccanografico
        - fonte: 'content' se trovato nel testo, 'filename' se dal nome file
        - is_validated: True se il codice esiste nel database delle scuole
    """
    # Prima prova: cerca pattern di codice meccanografico nel testo
    # Pattern: 2 lettere regione + 2 lettere tipo + 6 caratteri alfanumerici
    patterns = [
        r'\b([A-Z]{2}[A-Z]{2}\d{6}[A-Z]?)\b',  # es. MIIS08900V
        r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})\b',   # es. AGPC010001
        r'[Cc]odice\s*[Mm]eccanografico[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})',
        r'[Cc]od\.?\s*[Mm]ecc\.?[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})',
    ]
    
    found_codes = []
    # Cerca nei primi 50000 caratteri (circa 15-20 pagine)
    search_text = md_content[:50000].upper()
    
    for pattern in patterns:
        matches = re.findall(pattern, search_text)
        for match in matches:
            code = match.upper()
            if len(code) == 10 and code not in found_codes:
                found_codes.append(code)
    
    # Valida i codici trovati contro il database
    validated_code = None
    for code in found_codes:
        if SCHOOL_DB:
            school_data = SCHOOL_DB.get_school_data(code)
            if school_data:
                logger.info(f"✅ Codice {code} validato nel database: {school_data.get('denominazione', 'N/A')}")
                validated_code = code
                return (code, 'content', True)
    
    # Se nessun codice è stato validato, prova con LLM
    if not validated_code and found_codes:
        # Abbiamo trovato codici ma non sono nel database
        # Potrebbe essere un codice nuovo o errato
        logger.warning(f"⚠️ Codici trovati {found_codes} non presenti nel database")
    
    # Fallback: usa LLM per estrarre metadati
    try:
        from src.processing.cloud_review import extract_metadata_from_header, load_api_config
        
        api_config = load_api_config()
        provider = api_config.get('default_provider', 'openrouter')
        api_key = api_config.get(f'{provider}_api_key')
        
        if api_key:
            logger.info("🤖 Usando LLM per estrarre codice meccanografico...")
            meta = extract_metadata_from_header(
                md_content, 
                provider, 
                api_key, 
                "google/gemini-2.0-flash-exp:free" if provider == 'openrouter' else "gemini-2.0-flash-exp",
                school_id=filename_code
            )
            
            if meta and meta.get('school_id'):
                llm_code = meta['school_id'].upper()
                if len(llm_code) == 10:
                    # Valida contro database
                    if SCHOOL_DB:
                        school_data = SCHOOL_DB.get_school_data(llm_code)
                        if school_data:
                            logger.info(f"✅ LLM ha trovato codice {llm_code} - validato: {school_data.get('denominazione', 'N/A')}")
                            return (llm_code, 'llm', True)
                        else:
                            logger.warning(f"⚠️ LLM ha trovato codice {llm_code} ma non è nel database")
                            return (llm_code, 'llm', False)
                    return (llm_code, 'llm', False)
    except Exception as e:
        logger.error(f"❌ Errore estrazione LLM: {e}")
    
    # Ultimo fallback: usa il codice dal filename
    if filename_code:
        if SCHOOL_DB:
            school_data = SCHOOL_DB.get_school_data(filename_code)
            if school_data:
                return (filename_code, 'filename', True)
        return (filename_code, 'filename', False)
    
    # Se abbiamo trovato almeno un codice (anche non validato), usalo
    if found_codes:
        return (found_codes[0], 'content', False)
    
    return (None, None, False)

def rename_analysis_files(old_code: str, new_code: str) -> dict:
    """
    Rinomina i file di analisi (JSON e MD) dal vecchio codice al nuovo.
    Usato quando il codice estratto dal contenuto è diverso dal nome file.
    
    Returns:
        dict con i file rinominati
    """
    renamed = {
        'json': None,
        'md': None,
        'ptof_md': None
    }
    
    # Rinomina JSON analisi
    old_json = f"{ANALYSIS_DIR}/{old_code}_analysis.json"
    new_json = f"{ANALYSIS_DIR}/{new_code}_analysis.json"
    if os.path.exists(old_json) and not os.path.exists(new_json):
        os.rename(old_json, new_json)
        renamed['json'] = new_json
        logger.info(f"  📝 Rinominato: {old_code}_analysis.json → {new_code}_analysis.json")
    
    # Rinomina MD analisi
    old_analysis_md = f"{ANALYSIS_DIR}/{old_code}_analysis.md"
    new_analysis_md = f"{ANALYSIS_DIR}/{new_code}_analysis.md"
    if os.path.exists(old_analysis_md) and not os.path.exists(new_analysis_md):
        os.rename(old_analysis_md, new_analysis_md)
        renamed['md'] = new_analysis_md
        logger.info(f"  📝 Rinominato: {old_code}_analysis.md → {new_code}_analysis.md")
    
    # Rinomina MD sorgente in ptof_md
    old_ptof_md = f"{MD_DIR}/{old_code}.md"
    new_ptof_md = f"{MD_DIR}/{new_code}.md"
    if os.path.exists(old_ptof_md) and not os.path.exists(new_ptof_md):
        os.rename(old_ptof_md, new_ptof_md)
        renamed['ptof_md'] = new_ptof_md
        logger.info(f"  📝 Rinominato: {old_code}.md → {new_code}.md")
    
    # Aggiorna school_id nel JSON se rinominato
    if renamed['json'] and os.path.exists(renamed['json']):
        try:
            import json
            with open(renamed['json'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'metadata' in data:
                data['metadata']['school_id'] = new_code
            else:
                data['metadata'] = {'school_id': new_code}
            
            with open(renamed['json'], 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ Aggiornato school_id nel JSON: {new_code}")
        except Exception as e:
            logger.warning(f"  ⚠️ Errore aggiornamento JSON: {e}")
    
    return renamed

def extract_school_code(filename):
    """
    Wrapper per retrocompatibilità - estrae codice dal nome file.
    Per estrazione completa dal contenuto usa extract_school_code_from_content().
    """
    return extract_school_code_from_filename(filename)

def check_already_processed(school_code):
    """
    Verifica se una scuola è già stata processata.
    Ritorna un dict con info sui file esistenti.
    """
    existing = {
        'has_analysis': False,
        'has_markdown': False,
        'has_processed_pdf': False,
        'analysis_path': None,
        'markdown_path': None,
        'processed_pdf_path': None
    }
    
    # Cerca analisi esistente
    analysis_patterns = [
        f"{ANALYSIS_DIR}/{school_code}_analysis.json",
        f"{ANALYSIS_DIR}/{school_code}_PTOF_analysis.json",
    ]
    for pattern in analysis_patterns:
        matches = glob(pattern)
        if matches:
            existing['has_analysis'] = True
            existing['analysis_path'] = matches[0]
            break
    
    # Cerca anche con glob più ampio
    if not existing['has_analysis']:
        all_analysis = glob(f"{ANALYSIS_DIR}/*{school_code}*_analysis.json")
        if all_analysis:
            existing['has_analysis'] = True
            existing['analysis_path'] = all_analysis[0]
    
    # Cerca markdown esistente
    md_patterns = [
        f"{MD_DIR}/{school_code}.md",
        f"{MD_DIR}/{school_code}_PTOF.md",
    ]
    for pattern in md_patterns:
        if os.path.exists(pattern):
            existing['has_markdown'] = True
            existing['markdown_path'] = pattern
            break
    
    if not existing['has_markdown']:
        all_md = glob(f"{MD_DIR}/*{school_code}*.md")
        if all_md:
            existing['has_markdown'] = True
            existing['markdown_path'] = all_md[0]
    
    # Cerca PDF già processato
    processed_pdfs = glob(f"{PROCESSED_DIR}/**/*{school_code}*.pdf", recursive=True)
    if processed_pdfs:
        existing['has_processed_pdf'] = True
        existing['processed_pdf_path'] = processed_pdfs[0]
    
    return existing

def count_files():
    """Conta file in varie directory."""
    inbox_pdfs = glob(f"{INBOX_DIR}/*.pdf")
    processed_pdfs = glob(f"{PROCESSED_DIR}/**/*.pdf", recursive=True)
    md_files = glob(f"{MD_DIR}/*.md")
    analysis_files = glob(f"{ANALYSIS_DIR}/*.json")
    
    # Conta anche scartati
    discarded_pdfs = glob("ptof_discarded/**/*.pdf", recursive=True)
    
    return {
        'inbox': len(inbox_pdfs),
        'processed': len(processed_pdfs),
        'markdown': len(md_files),
        'analysis': len(analysis_files),
        'discarded': len(discarded_pdfs)
    }

def validate_inbox_pdfs():
    """
    Pre-valida i PDF in inbox per identificare documenti non-PTOF.
    Usa validazione progressiva: heuristics → LLM (se ambiguo).
    
    Returns:
        dict con 'valid', 'discarded', 'stats'
    """
    logger.info("="*80)
    logger.info("🔍 STEP 0: Pre-Validazione PTOF (heuristics → LLM)")
    
    if not PTOF_VALIDATOR:
        logger.warning("⚠️ PTOFValidator non disponibile, skip validazione")
        return {'valid': glob(f"{INBOX_DIR}/*.pdf"), 'discarded': [], 'stats': {}}
    
    inbox_pdfs = glob(f"{INBOX_DIR}/*.pdf")
    
    if not inbox_pdfs:
        logger.info("ℹ️ Nessun PDF in inbox")
        return {'valid': [], 'discarded': [], 'stats': {}}
    
    logger.info(f"📄 PDF da validare: {len(inbox_pdfs)}")
    
    valid_pdfs = []
    discarded_info = []
    
    for pdf_path in inbox_pdfs:
        logger.info(f"\n📄 Validando: {os.path.basename(pdf_path)}")
        
        # Validazione progressiva
        report = PTOF_VALIDATOR.validate(pdf_path, use_llm_if_ambiguous=True)
        
        if report.result == ValidationResult.VALID_PTOF.value:
            logger.info(f"   ✅ PTOF VALIDO (confidence: {report.confidence:.2f})")
            valid_pdfs.append(pdf_path)
        else:
            logger.warning(f"   ❌ SCARTATO: {report.reason}")
            # Sposta in directory appropriata
            dest_path = PTOF_VALIDATOR.discard(pdf_path, report)
            discarded_info.append({
                'original': pdf_path,
                'destination': str(dest_path),
                'reason': report.reason,
                'result': report.result,
                'confidence': report.confidence,
                'phase': report.phase
            })
    
    # Statistiche
    stats = {
        'total': len(inbox_pdfs),
        'valid': len(valid_pdfs),
        'discarded': len(discarded_info),
        'valid_rate': len(valid_pdfs) / len(inbox_pdfs) if inbox_pdfs else 0
    }
    
    logger.info(f"\n📊 RISULTATI PRE-VALIDAZIONE:")
    logger.info(f"   ✅ Validi: {stats['valid']}")
    logger.info(f"   ❌ Scartati: {stats['discarded']}")
    
    if discarded_info:
        logger.info(f"\n📂 File scartati spostati in ptof_discarded/")
        logger.info("   💡 Per recuperarli: python src/validation/ptof_validator.py recover --file NOME.pdf")
    
    return {
        'valid': valid_pdfs,
        'discarded': discarded_info,
        'stats': stats
    }

def convert_pdfs_to_md(validated_pdfs=None):
    """
    Converti PDF in Markdown.
    
    Args:
        validated_pdfs: Lista di PDF già validati (opzionale).
                       Se None, legge tutti i PDF da inbox.
    """
    logger.info("="*80)
    logger.info("📝 STEP 1: Conversione PDF → Markdown")
    
    # Usa PDF validati se forniti, altrimenti leggi da inbox
    if validated_pdfs is not None:
        inbox_pdfs = validated_pdfs
        logger.info(f"📄 PDF pre-validati da convertire: {len(inbox_pdfs)}")
    else:
        inbox_pdfs = glob(f"{INBOX_DIR}/*.pdf")
        logger.info(f"📄 Trovati {len(inbox_pdfs)} PDF in inbox")
    
    if not inbox_pdfs:
        logger.warning("⚠️ Nessun PDF da convertire")
        return [], [], {}
    
    # Pre-check per duplicati
    duplicates = []
    new_files = []
    
    for pdf_path in inbox_pdfs:
        school_code = extract_school_code(pdf_path)
        existing = check_already_processed(school_code)
        
        if existing['has_analysis'] or existing['has_processed_pdf']:
            duplicates.append({
                'pdf_path': pdf_path,
                'school_code': school_code,
                'existing': existing
            })
        else:
            new_files.append(pdf_path)
    
    # Report duplicati
    if duplicates:
        logger.warning("="*80)
        logger.warning(f"⚠️ ATTENZIONE: {len(duplicates)} scuole già processate!")
        logger.warning("="*80)
        for dup in duplicates:
            logger.warning(f"  🔄 {dup['school_code']} ({os.path.basename(dup['pdf_path'])})")
            if dup['existing']['analysis_path']:
                logger.warning(f"     └─ Analisi esistente: {dup['existing']['analysis_path']}")
            if dup['existing']['processed_pdf_path']:
                logger.warning(f"     └─ PDF già processato: {dup['existing']['processed_pdf_path']}")
        logger.warning("")
        logger.warning("💡 Questi file verranno SALTATI. Per ri-analizzare:")
        logger.warning("   1. Elimina i file JSON in analysis_results/")
        logger.warning("   2. Oppure usa l'opzione --force (se implementata)")
        logger.warning("="*80)
    
    if not new_files:
        logger.info("ℹ️ Tutti i PDF sono di scuole già processate")
        return [], duplicates
    
    logger.info(f"📄 PDF nuovi da processare: {len(new_files)}")
    
    # Import conversion function
    try:
        from src.processing.convert_pdfs_to_md import pdf_to_markdown
    except ImportError:
        # Fallback: import diretto
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from src.processing.convert_pdfs_to_md import pdf_to_markdown
        except ImportError:
            logger.error("❌ Impossibile importare pdf_to_markdown")
            # Fallback manuale con PyMuPDF
            import fitz
            def pdf_to_markdown(pdf_path, output_path):
                try:
                    doc = fitz.open(pdf_path)
                    md_content = f"# Contenuto PTOF: {os.path.basename(pdf_path)}\n\n"
                    for i, page in enumerate(doc):
                        text = page.get_text("text")
                        md_content += f"## Pagina {i+1}\n\n{text}\n\n---\n\n"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    return True
                except Exception as e:
                    logger.error(f"Errore: {e}")
                    return False
    
    converted = []
    code_mapping = {}  # Mappa pdf_path -> codice_reale
    
    for pdf_path in new_files:
        try:
            # Prima converti con nome temporaneo basato sul filename
            filename_code = extract_school_code_from_filename(pdf_path)
            temp_md_output = f"{MD_DIR}/_temp_{filename_code}.md"
            
            # Convert PDF to MD
            if pdf_to_markdown(pdf_path, temp_md_output):
                # Leggi il contenuto MD per estrarre il codice reale
                with open(temp_md_output, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Estrai il codice meccanografico reale dal contenuto
                real_code, source, is_validated = extract_school_code_from_content(md_content, filename_code)
                
                if real_code and real_code != filename_code:
                    logger.info(f"🔍 Codice corretto trovato: {filename_code} → {real_code} (fonte: {source}, validato: {is_validated})")
                elif real_code:
                    logger.info(f"✅ Codice confermato: {real_code} (fonte: {source}, validato: {is_validated})")
                else:
                    logger.warning(f"⚠️ Nessun codice trovato nel contenuto, uso filename: {filename_code}")
                    real_code = filename_code
                
                # Verifica se con il codice reale è un duplicato
                existing = check_already_processed(real_code)
                if existing['has_analysis'] or existing['has_processed_pdf']:
                    logger.warning(f"⚠️ DUPLICATO RILEVATO: {real_code} esiste già!")
                    logger.warning(f"   └─ Il file {os.path.basename(pdf_path)} contiene il codice {real_code}")
                    if existing['analysis_path']:
                        logger.warning(f"   └─ Analisi esistente: {existing['analysis_path']}")
                    # Rimuovi file temporaneo
                    os.remove(temp_md_output)
                    # Aggiungi ai duplicati
                    duplicates.append({
                        'pdf_path': pdf_path,
                        'school_code': real_code,
                        'filename_code': filename_code,
                        'existing': existing,
                        'detected_in_content': True
                    })
                    continue
                
                # Rinomina al nome corretto
                final_md_output = f"{MD_DIR}/{real_code}.md"
                if os.path.exists(final_md_output) and final_md_output != temp_md_output:
                    logger.warning(f"⚠️ File MD esiste già: {final_md_output}")
                    os.remove(temp_md_output)
                    continue
                    
                os.rename(temp_md_output, final_md_output)
                
                converted.append(pdf_path)
                code_mapping[pdf_path] = real_code
                logger.info(f"✅ Convertito: {os.path.basename(pdf_path)} → {real_code}.md")
            else:
                logger.error(f"❌ Errore conversione: {os.path.basename(pdf_path)}")
            
        except Exception as e:
            logger.error(f"❌ Errore conversione {pdf_path}: {e}")
            # Pulisci file temporanei se esistono
            temp_path = f"{MD_DIR}/_temp_{extract_school_code_from_filename(pdf_path)}.md"
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    logger.info(f"📊 Convertiti {len(converted)}/{len(new_files)} file")
    return converted, duplicates, code_mapping

def run_multi_agent_analysis(converted_pdfs, code_mapping=None):
    """Esegui analisi multi-agente SOLO sui file appena convertiti dalla inbox."""
    logger.info("="*80)
    logger.info("🤖 STEP 2: Analisi Multi-Agente")
    
    if not converted_pdfs:
        logger.info("ℹ️ Nessun file da analizzare")
        return []
    
    code_mapping = code_mapping or {}
    
    from app.agentic_pipeline import (
        AnalystAgent,
        ReviewerAgent,
        RefinerAgent,
        SynthesizerAgent,
        process_single_ptof
    )
    
    # Analizza SOLO i file appena convertiti dalla inbox
    to_analyze = []
    for pdf_path in converted_pdfs:
        # Usa il codice reale dal mapping, altrimenti estrai dal filename
        school_code = code_mapping.get(pdf_path) or extract_school_code_from_filename(pdf_path)
        md_file = f"{MD_DIR}/{school_code}.md"
        analysis_file = f"{ANALYSIS_DIR}/{school_code}_analysis.json"
        
        if os.path.exists(md_file):
            if os.path.exists(analysis_file):
                logger.info(f"⏭️ Già analizzato: {school_code}")
            else:
                to_analyze.append((md_file, school_code))
        else:
            logger.warning(f"⚠️ MD non trovato: {school_code}")
    
    if not to_analyze:
        logger.info("ℹ️ Tutti i file sono già stati analizzati")
        return []
    
    logger.info(f"📄 File da analizzare: {len(to_analyze)}")
    
    # Inizializza agenti
    analyst = AnalystAgent()
    reviewer = ReviewerAgent()
    refiner = RefinerAgent()
    synthesizer = SynthesizerAgent()
    
    def status_callback(msg):
        logger.info(f"  [PIPELINE] {msg}")
    
    analyzed = []
    for md_file, school_code in to_analyze:
        logger.info(f"🔄 Processando: {school_code}")
        
        try:
            result = process_single_ptof(
                md_file=md_file,
                analyst=analyst,
                reviewer=reviewer,
                refiner=refiner,
                synthesizer=synthesizer,
                status_callback=status_callback
            )
            
            if result:
                analyzed.append(school_code)
                logger.info(f"✅ Completato: {school_code}")
                
                # AGGIORNAMENTO INCREMENTALE CSV - dopo ogni PTOF
                try:
                    import subprocess
                    csv_result = subprocess.run(
                        ['python', 'src/processing/rebuild_csv.py'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if csv_result.returncode == 0:
                        # Conta scuole nel CSV
                        import pandas as pd
                        if os.path.exists('data/analysis_summary.csv'):
                            df = pd.read_csv('data/analysis_summary.csv')
                            logger.info(f"  📊 CSV aggiornato: {len(df)} scuole totali")
                except Exception as csv_e:
                    logger.warning(f"  ⚠️ CSV update: {csv_e}")
            else:
                logger.warning(f"⚠️ Nessun risultato per: {school_code}")
                
        except Exception as e:
            logger.error(f"❌ Errore analisi {school_code}: {e}")
    
    logger.info(f"📊 Analizzati {len(analyzed)}/{len(to_analyze)} file")
    return analyzed

def move_processed_pdfs(converted_pdfs):
    """Sposta PDF processati dalla inbox a processed/."""
    logger.info("="*80)
    logger.info("📦 STEP 3: Archiviazione PDF Processati")
    
    if not converted_pdfs:
        logger.info("ℹ️ Nessun PDF da archiviare")
        return
    
    # Crea subdirectory con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = f"{PROCESSED_DIR}/batch_{timestamp}"
    os.makedirs(batch_dir, exist_ok=True)
    
    logger.info(f"📁 Directory batch: {batch_dir}")
    
    moved = 0
    for pdf_path in converted_pdfs:
        try:
            basename = os.path.basename(pdf_path)
            dest_path = f"{batch_dir}/{basename}"
            
            shutil.move(pdf_path, dest_path)
            logger.info(f"✅ Archiviato: {basename}")
            moved += 1
            
        except Exception as e:
            logger.error(f"❌ Errore spostamento {pdf_path}: {e}")
    
    logger.info(f"📊 Archiviati {moved}/{len(converted_pdfs)} PDF")
    
    # Crea file di riepilogo batch
    summary_file = f"{batch_dir}/README.txt"
    with open(summary_file, 'w') as f:
        f.write(f"Batch processato il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File processati: {moved}\n\n")
        f.write("File:\n")
        for pdf in converted_pdfs:
            f.write(f"  - {os.path.basename(pdf)}\n")
    
    logger.info(f"📄 Creato riepilogo: {summary_file}")

def fix_existing_analysis_names():
    """
    Scansiona i file di analisi esistenti e corregge i nomi se il codice
    nel contenuto è diverso dal nome file.
    """
    logger.info("="*80)
    logger.info("🔧 Correzione nomi file analisi esistenti")
    
    import json
    
    json_files = glob(f"{ANALYSIS_DIR}/*.json")
    fixed_count = 0
    
    for json_path in json_files:
        try:
            filename = os.path.basename(json_path)
            if not filename.endswith('_analysis.json'):
                continue
                
            file_code = filename.replace('_analysis.json', '')
            
            # Leggi il JSON per vedere il codice nel metadata
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            meta_code = data.get('metadata', {}).get('school_id', '').upper()
            
            if meta_code and meta_code != file_code and len(meta_code) == 10:
                # Valida il codice nel metadata
                if SCHOOL_DB:
                    school_data = SCHOOL_DB.get_school_data(meta_code)
                    if school_data:
                        logger.info(f"🔍 Trovato codice errato: {file_code} → {meta_code}")
                        renamed = rename_analysis_files(file_code, meta_code)
                        if any(renamed.values()):
                            fixed_count += 1
                    else:
                        logger.warning(f"⚠️ Codice {meta_code} nel JSON {filename} non trovato nel database")
                else:
                    # Senza database, rinomina comunque
                    logger.info(f"🔍 Trovato codice errato: {file_code} → {meta_code}")
                    renamed = rename_analysis_files(file_code, meta_code)
                    if any(renamed.values()):
                        fixed_count += 1
                        
        except Exception as e:
            logger.error(f"❌ Errore processando {json_path}: {e}")
    
    if fixed_count > 0:
        logger.info(f"✅ Corretti {fixed_count} file")
    else:
        logger.info("✅ Nessun file da correggere")
    
    return fixed_count

def enrich_all_metadata():
    """
    Arricchisce tutti i file JSON con metadati ufficiali dalle anagrafi
    SCUANAGRAFESTAT e SCUANAGRAFEPAR.
    """
    logger.info("="*80)
    logger.info("📚 Arricchimento metadati da anagrafi ufficiali")
    
    import json
    
    if not SCHOOL_DB:
        logger.warning("⚠️ SchoolDatabase non disponibile, skip arricchimento")
        return 0
    
    json_files = glob(f"{ANALYSIS_DIR}/*.json")
    enriched_count = 0
    
    for json_path in json_files:
        try:
            filename = os.path.basename(json_path)
            if not filename.endswith('_analysis.json'):
                continue
            
            school_code = filename.replace('_analysis.json', '').upper()
            
            # Get data from SchoolDatabase
            db_data = SCHOOL_DB.get_school_data(school_code)
            if not db_data:
                continue
            
            # Read current JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'metadata' not in data:
                data['metadata'] = {}
            
            # Enrich with official data - priority: existing (LLM) > SchoolDB
            fields_to_enrich = [
                'denominazione', 'comune', 'provincia', 'regione', 
                'area_geografica', 'ordine_grado', 'tipo_scuola',
                'indirizzo', 'cap', 'email', 'pec', 'website',
                'statale_paritaria', 'tipo_istruzione_raw'
            ]
            
            updated = False
            for field in fields_to_enrich:
                current_val = data['metadata'].get(field, '')
                db_val = db_data.get(field, '')
                
                # Update if current is empty/ND and DB has value
                if db_val and db_val not in ['ND', '', None]:
                    if not current_val or current_val in ['ND', '', None, 'null']:
                        data['metadata'][field] = db_val
                        updated = True
            
            # Map territory from area_geografica
            area = data['metadata'].get('area_geografica', '').upper()
            territorio_map = {
                'NORD OVEST': 'Nord',
                'NORD EST': 'Nord', 
                'NORD': 'Nord',
                'CENTRO': 'Centro',
                'SUD': 'Sud',
                'ISOLE': 'Sud',
            }
            if area in territorio_map:
                data['metadata']['territorio'] = territorio_map[area]
                updated = True
            
            if updated:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                enriched_count += 1
                logger.debug(f"  ✅ Arricchito: {school_code}")
                
        except Exception as e:
            logger.error(f"❌ Errore arricchimento {json_path}: {e}")
    
    if enriched_count > 0:
        logger.info(f"✅ Arricchiti {enriched_count} file con metadati ufficiali")
    else:
        logger.info("✅ Tutti i file hanno già metadati completi")
    
    return enriched_count

def rebuild_csv():
    """Ricostruisci CSV summary."""
    logger.info("="*80)
    logger.info("📊 STEP 4: Ricostruzione CSV")
    
    import subprocess
    
    result = subprocess.run(
        ['python', 'src/processing/rebuild_csv.py'],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode == 0:
        logger.info("✅ CSV ricostruito con successo")
    else:
        logger.error(f"❌ Errore rebuild CSV: {result.stderr}")
    
    return result.returncode == 0

def run_workflow():
    """Esegui workflow completo."""
    logger.info("="*80)
    logger.info("🚀 AVVIO WORKFLOW PTOF COMPLETO")
    logger.info(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Status iniziale
    counts = count_files()
    logger.info(f"\n📊 STATO INIZIALE:")
    logger.info(f"  PDF in inbox: {counts['inbox']}")
    logger.info(f"  PDF processati: {counts['processed']}")
    logger.info(f"  File Markdown: {counts['markdown']}")
    logger.info(f"  File analisi: {counts['analysis']}")
    logger.info(f"  File scartati: {counts.get('discarded', 0)}")
    
    if counts['inbox'] == 0:
        logger.warning("\n⚠️ Nessun PDF da processare in ptof_inbox/")
        logger.info("💡 Copia i PDF da analizzare in ptof_inbox/ e riprova")
        return
    
    # STEP 0: Pre-validazione PTOF (heuristics → LLM)
    # Identifica e scarta documenti che non sono PTOF
    validation_result = validate_inbox_pdfs()
    valid_pdfs = validation_result['valid']
    
    if not valid_pdfs:
        logger.warning("\n⚠️ Nessun PTOF valido trovato dopo la pre-validazione")
        if validation_result['discarded']:
            logger.info(f"📂 {len(validation_result['discarded'])} file scartati in ptof_discarded/")
            logger.info("💡 Per recuperare: python src/validation/ptof_validator.py list")
        return
    
    # STEP 1: Conversione (solo PDF validi, con rilevamento duplicati)
    # Passa solo i PDF che hanno superato la validazione
    converted_pdfs, duplicates, code_mapping = convert_pdfs_to_md(valid_pdfs)
    
    # STEP 2: Analisi (solo dei file appena convertiti)
    analyzed = []
    if converted_pdfs:
        analyzed = run_multi_agent_analysis(converted_pdfs, code_mapping)
    
    # STEP 3: Archiviazione
    if converted_pdfs:
        move_processed_pdfs(converted_pdfs)
    
    # Gestione duplicati: sposta anche i PDF duplicati in una cartella separata
    if duplicates:
        dup_dir = f"{PROCESSED_DIR}/duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(dup_dir, exist_ok=True)
        logger.info(f"📁 Spostamento duplicati in: {dup_dir}")
        for dup in duplicates:
            try:
                src = dup['pdf_path']
                dst = os.path.join(dup_dir, os.path.basename(src))
                shutil.move(src, dst)
                logger.info(f"  ➡️ {os.path.basename(src)} → duplicates/")
            except Exception as e:
                logger.error(f"  ❌ Errore spostamento {os.path.basename(dup['pdf_path'])}: {e}")
    
    # STEP 3.5: Correggi nomi file esistenti con codice errato
    fix_existing_analysis_names()
    
    # STEP 3.6: Arricchisci metadati con dati ufficiali dalle anagrafi
    enrich_all_metadata()
    
    # STEP 4: Rebuild CSV
    rebuild_csv()
    
    # Status finale
    counts_final = count_files()
    logger.info("\n" + "="*80)
    logger.info("📊 STATO FINALE:")
    logger.info(f"  PDF in inbox: {counts_final['inbox']}")
    logger.info(f"  PDF processati: {counts_final['processed']}")
    logger.info(f"  File Markdown: {counts_final['markdown']}")
    logger.info(f"  File analisi: {counts_final['analysis']}")
    logger.info(f"  File scartati: {counts_final.get('discarded', 0)}")
    
    if duplicates:
        logger.info(f"\n⚠️ Duplicati rilevati: {len(duplicates)} (spostati in {dup_dir})")
    
    if validation_result.get('discarded'):
        logger.info(f"\n🗑️ Pre-validazione: {len(validation_result['discarded'])} documenti non-PTOF scartati")
        logger.info("   💡 Per recuperare: python src/validation/ptof_validator.py list")
    
    logger.info("\n" + "="*80)
    logger.info("✅ WORKFLOW COMPLETATO!")
    logger.info("📋 Log salvato in: logs/workflow_ptof.log")
    logger.info("📊 Verifica risultati su Dashboard → Pagina ⚙️ Gestione")
    logger.info("="*80)

if __name__ == "__main__":
    try:
        run_workflow()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Workflow interrotto dall'utente")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Errore critico: {e}", exc_info=True)
        sys.exit(1)
