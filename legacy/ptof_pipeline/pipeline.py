import pandas as pd
import glob
import logging
import os
import requests
import time
from .scraper import find_school_url, find_ptof_link
from .analyzer import extract_text_from_pdf, analyze_with_ollama

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
RESULTS_FILE = "data/risultati_analisi.csv"

def load_data():
    # Check for discovery file first
    if os.path.exists("data/candidati_ptof.csv"):
        logger.info("Loading discovered schools from data/candidati_ptof.csv")
        try:
             df = pd.read_csv("data/candidati_ptof.csv", sep=';')
             return df
        except Exception as e:
             logger.error(f"Error reading discovery file: {e}")
             
    # Fallback to raw files
    files = glob.glob('data/paccmb_elenc*.csv')
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, sep=';', encoding='latin1')
            dfs.append(df)
        except Exception as e:
            logger.warning(f"Failed to read {f}: {e}")
    
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def sanitize_filename(name):
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")

def process_school(school, idx, total):
    """
    Process a single school row.
    offline-first: checks ptof_downloads/
    """
    # Use 'nome_istituto' which is more descriptive, or fall back to denominazione
    name = school.get('nome_istituto', school.get('denominazionescuola', 'Sconosciuto'))
    city = school.get('nome_comune', '')
    school_id = school.get('istituto', '')
    
    logger.info(f"[{idx}/{total}] Processing: {name} ({city}) Code: {school_id}")
    
    # Check for local file in ptof_downloads
    safe_name = sanitize_filename(name)
    file_name = f"{school_id}_{safe_name}.pdf"
    local_path = os.path.join("ptof_downloads", file_name)
    
    url = school.get('sito_web', 'N/A')
    ptof_link = school.get('ptof_link', 'N/A')
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        logger.info(f"  -> Found local file: {local_path}")
        text = extract_text_from_pdf(local_path)
        
        if not text or not text.strip():
            logger.warning("  -> Local PDF text empty/unreadable.")
            return url, "LOCAL_FILE_EMPTY", "Testo PDF vuoto"
            
        logger.info("  -> Analyzing with Ollama...")
        analysis_text = analyze_with_ollama(text, name)
        return url, "LOCAL_FILE", analysis_text

    logger.warning(f"  -> No local file found at {local_path}")
    return url, "NOT_FOUND", "PTOF non scaricato"

def main():
    logger.info("Starting Pipeline...")
    
    # Load Data
    df = load_data()
    if df.empty:
        logger.error("No data found.")
        return
        
    logger.info(f"Loaded {len(df)} schools.")
    
    # Prepare result columns if not exist
    if 'sito_web' not in df.columns:
        df['sito_web'] = ""
    if 'ptof_link' not in df.columns:
        df['ptof_link'] = ""
    if 'analisi_orientamento' not in df.columns:
        df['analisi_orientamento'] = ""
        
    # Process
    # Check for resumption
    processed_count = 0
    
    # Save periodically
    BATCH_SIZE = 5
    
    for index, row in df.iterrows():
        # Skip if already analyzed (simple check)
        if str(row['analisi_orientamento']) != "" and pd.notna(row['analisi_orientamento']):
             continue
             
        url, ptof, analysis = process_school(row, index + 1, len(df))
        
        df.at[index, 'sito_web'] = url
        df.at[index, 'ptof_link'] = ptof
        df.at[index, 'analisi_orientamento'] = analysis
        
        processed_count += 1
        
        if processed_count % BATCH_SIZE == 0:
            df.to_csv(RESULTS_FILE, sep=';', index=False, encoding='utf-8-sig')
            logger.info(f"Saved interim results to {RESULTS_FILE}")
            
    # Final save
    df.to_csv(RESULTS_FILE, sep=';', index=False, encoding='utf-8-sig')
    logger.info("Pipeline Complete. Results saved.")

if __name__ == "__main__":
    main()
