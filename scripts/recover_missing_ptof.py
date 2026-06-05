#!/usr/bin/env python3
import os
import sys
import csv
import glob
import shutil
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Aggiungi la root del progetto al path per importare i moduli src
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.processing.convert_pdfs_to_md import pdf_to_markdown
from src.downloaders.ptof_downloader import PTOFDownloader, DownloadState, SchoolRecord
from src.utils.school_database import SchoolDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurazione directory
DATA_DIR = BASE_DIR / "data"
MD_DIR = BASE_DIR / "ptof_md"
PDF_DIRS = [
    BASE_DIR / "ptof",
    BASE_DIR / "ptof_inbox",
    BASE_DIR / "ptof_processed",
    BASE_DIR / "ptof_docs"
]
CSV_FILE = DATA_DIR / "analysis_summary.csv"
STATE_FILE = DATA_DIR / "download_state.json"

def get_missing_schools():
    """Identifica le scuole presenti nel CSV ma senza MD."""
    if not CSV_FILE.exists():
        logger.error(f"File CSV non trovato: {CSV_FILE}")
        return set()

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_schools = {row['school_id'] for row in reader}

    if not MD_DIR.exists():
        MD_DIR.mkdir(parents=True, exist_ok=True)
        return csv_schools

    md_files = {f.split('_')[0] for f in os.listdir(MD_DIR) if f.endswith('_ptof.md')}
    missing = csv_schools - md_files
    logger.info(f"Scuole totali in CSV: {len(csv_schools)}")
    logger.info(f"File MD presenti: {len(md_files)}")
    logger.info(f"Scuole mancanti: {len(missing)}")
    return missing

def find_pdf(school_code):
    """Cerca il PDF della scuola nelle directory note."""
    for directory in PDF_DIRS:
        if not directory.exists():
            continue
        # Cerca file che iniziano con il codice scuola
        candidates = list(directory.glob(f"{school_code}*.pdf"))
        if candidates:
            # Preferisci file che finiscono con _ptof.pdf o _PTOF.pdf
            preferred = [c for c in candidates if '_ptof.pdf' in c.name.lower()]
            return preferred[0] if preferred else candidates[0]
    return None

def recover_school(school_code, downloader, school_db):
    """Tenta di recuperare il PTOF per una singola scuola."""
    logger.info(f"Recupero per {school_code}...")
    
    # 1. Cerca PDF locale
    pdf_path = find_pdf(school_code)
    
    # 2. Se non trovato, scarica
    if not pdf_path:
        logger.info(f"  PDF non trovato localmente. Tentativo di download...")
        
        # FIX: Se lo stato dice che è scaricato ma noi non lo troviamo, resettiamo lo stato
        if downloader.state.is_downloaded(school_code) or downloader.state.is_rejected(school_code) or downloader.state.is_failed(school_code):
             logger.info(f"  Reset stato per {school_code} (stato disallineato con file system)")
             if school_code in downloader.state.state["downloaded"]:
                 del downloader.state.state["downloaded"][school_code]
             if school_code in downloader.state.state["rejected"]:
                 del downloader.state.state["rejected"][school_code]
             if school_code in downloader.state.state["failed"]:
                 del downloader.state.state["failed"][school_code]
             downloader.state.save()

        data = school_db.get_school_data(school_code)
        if not data:
            logger.warning(f"  Dati MIUR non trovati per {school_code}. Impossibile scaricare.")
            return False
            
        # Crea oggetto SchoolRecord
        school_record = SchoolRecord(
            codice=school_code,
            denominazione=data.get('denominazione', ''),
            indirizzo=data.get('indirizzo', ''),
            cap=data.get('cap', ''),
            comune=data.get('comune', ''),
            provincia=data.get('provincia', ''),
            regione=data.get('regione', ''),
            area_geografica=data.get('area_geografica', ''),
            tipologia=data.get('tipologia', ''),
            email=data.get('email', ''),
            pec=data.get('pec', ''),
            sito_web=data.get('sito_web', ''),
            is_statale=(data.get('statale_paritaria', 'Statale') == 'Statale'),
            codice_istituto=data.get('codice_istituto_riferimento', school_code),
            denominazione_istituto=data.get('denominazione_istituto_riferimento', '')
        )
        
        result = downloader.download_ptof(school_record)
        if result.success and result.file_path:
            pdf_path = Path(result.file_path)
            logger.info(f"  Download completato: {pdf_path}")
        else:
            logger.error(f"  Download fallito: {result.message}")
            return False

    # 3. Converti in Markdown
    if pdf_path and pdf_path.exists():
        md_filename = f"{school_code}_ptof.md"
        md_path = MD_DIR / md_filename
        logger.info(f"  Conversione PDF -> MD: {md_path}")
        try:
            success = pdf_to_markdown(pdf_path, md_path)
            if success:
                logger.info(f"  SUCCESS: {school_code} recuperato.")
                return True
            else:
                logger.error(f"  Errore conversione PDF per {school_code}")
        except Exception as e:
            logger.error(f"  Eccezione conversione {school_code}: {e}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Recupera PTOF mancanti (PDF -> MD)")
    parser.add_argument("--limit", type=int, default=0, help="Limite numero scuole da processare (0=tutte)")
    parser.add_argument("--workers", type=int, default=4, help="Numero thread paralleli")
    args = parser.parse_args()

    missing_schools = list(get_missing_schools())
    if not missing_schools:
        logger.info("Nessuna scuola mancante. Uscita.")
        return

    if args.limit > 0:
        missing_schools = missing_schools[:args.limit]
        logger.info(f"Processo prime {args.limit} scuole mancanti.")

    # Init database e downloader
    logger.info("Inizializzazione database e downloader...")
    school_db = SchoolDatabase()
    
    # Crea directory download se non esiste
    download_dir = BASE_DIR / "ptof_inbox"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    state = DownloadState(STATE_FILE)
    downloader = PTOFDownloader(state, download_dir)

    success_count = 0
    fail_count = 0

    # Elaborazione
    # Nota: PTOFDownloader usa requests.Session che non è thread-safe per chiamate concorrenti
    # se condividiamo lo stesso oggetto session. 
    # Per semplicità, processiamo sequenzialmente o con attenzione.
    # Dato che PTOFDownloader in init crea una sessione, meglio istanziarne uno per thread o usare lock.
    # Ma qui per semplicità e visto che il collo di bottiglia è spesso il JS rendering o il network,
    # e requests session non è thread safe, usiamo un solo thread per il download se usiamo la stessa istanza.
    # O meglio: eseguiamo sequenzialmente per evitare problemi complessi, tanto sono ~200 scuole.
    # Oppure: usiamo ThreadPoolExecutor ma creiamo nuovi downloader (costoso init DB?).
    # SchoolDatabase è singleton, ok.
    # Facciamo sequenziale per sicurezza e stabilità.
    
    logger.info("Avvio recupero...")
    
    for i, school_code in enumerate(missing_schools, 1):
        logger.info(f"[{i}/{len(missing_schools)}] Processing {school_code}...")
        if recover_school(school_code, downloader, school_db):
            success_count += 1
        else:
            fail_count += 1

    logger.info("="*50)
    logger.info(f"RECUPERO COMPLETATO")
    logger.info(f"Successi: {success_count}")
    logger.info(f"Falliti: {fail_count}")
    logger.info("="*50)

if __name__ == "__main__":
    main()
