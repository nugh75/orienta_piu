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

def count_files():
    """Conta file in varie directory."""
    inbox_pdfs = glob(f"{INBOX_DIR}/*.pdf")
    processed_pdfs = glob(f"{PROCESSED_DIR}/**/*.pdf", recursive=True)
    md_files = glob(f"{MD_DIR}/*.md")
    analysis_files = glob(f"{ANALYSIS_DIR}/*.json")
    
    return {
        'inbox': len(inbox_pdfs),
        'processed': len(processed_pdfs),
        'markdown': len(md_files),
        'analysis': len(analysis_files)
    }

def convert_pdfs_to_md():
    """Converti PDF dalla inbox in Markdown."""
    logger.info("="*80)
    logger.info("📝 STEP 1: Conversione PDF → Markdown")
    
    inbox_pdfs = glob(f"{INBOX_DIR}/*.pdf")
    
    if not inbox_pdfs:
        logger.warning("⚠️ Nessun PDF trovato in ptof_inbox/")
        return []
    
    logger.info(f"📄 Trovati {len(inbox_pdfs)} PDF da convertire")
    
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
    for pdf_path in inbox_pdfs:
        try:
            school_code = os.path.basename(pdf_path).replace('.pdf', '')
            md_output = f"{MD_DIR}/{school_code}.md"
            
            # Convert
            if pdf_to_markdown(pdf_path, md_output):
                converted.append(pdf_path)
                logger.info(f"✅ Convertito: {school_code}")
            else:
                logger.error(f"❌ Errore conversione: {school_code}")
            
        except Exception as e:
            logger.error(f"❌ Errore conversione {pdf_path}: {e}")
    
    logger.info(f"📊 Convertiti {len(converted)}/{len(inbox_pdfs)} file")
    return converted

def run_multi_agent_analysis(converted_pdfs):
    """Esegui analisi multi-agente SOLO sui file appena convertiti dalla inbox."""
    logger.info("="*80)
    logger.info("🤖 STEP 2: Analisi Multi-Agente")
    
    if not converted_pdfs:
        logger.info("ℹ️ Nessun file da analizzare")
        return []
    
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
        school_code = os.path.basename(pdf_path).replace('.pdf', '')
        md_file = f"{MD_DIR}/{school_code}.md"
        analysis_file = f"{ANALYSIS_DIR}/{school_code}_analysis.json"
        
        if os.path.exists(md_file):
            if os.path.exists(analysis_file):
                logger.info(f"⏭️ Già analizzato: {school_code}")
            else:
                to_analyze.append(md_file)
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
    for md_file in to_analyze:
        school_code = os.path.basename(md_file).replace('.md', '')
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
    
    if counts['inbox'] == 0:
        logger.warning("\n⚠️ Nessun PDF da processare in ptof_inbox/")
        logger.info("💡 Copia i PDF da analizzare in ptof_inbox/ e riprova")
        return
    
    # STEP 1: Conversione
    converted_pdfs = convert_pdfs_to_md()
    
    # STEP 2: Analisi (solo dei file appena convertiti)
    if converted_pdfs:
        analyzed = run_multi_agent_analysis(converted_pdfs)
    
    # STEP 3: Archiviazione
    if converted_pdfs:
        move_processed_pdfs(converted_pdfs)
    
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
