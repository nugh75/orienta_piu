import pandas as pd
import logging
import time
from ptof_pipeline.pipeline import load_data
from ptof_pipeline.scraper import find_school_url, find_ptof_link

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("discovery.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = "candidati_ptof.csv"

def main():
    logger.info("Starting Discovery Phase...")
    
    # Load Data
    df = load_data()
    if df.empty:
        logger.error("No data found.")
        return
        
    logger.info(f"Loaded {len(df)} schools.")
    
    # Initialize columns if missing
    if 'sito_web' not in df.columns:
        df['sito_web'] = ""
    if 'ptof_link' not in df.columns:
        df['ptof_link'] = ""
        
    total = len(df)
    
    for index, row in df.iterrows():
        raw_name = row.get('nome_istituto', row.get('denominazionescuola', 'Sconosciuto'))
        # Clean name: remove content in parenthesis
        import re
        name = re.sub(r'\(.*?\)', '', raw_name).strip()
        
        city = row.get('nome_comune', '')
        school_id = row.get('istituto', '')
        
        logger.info(f"[{index+1}/{total}] Searching for: {name} ({city}) [Raw: {raw_name}]")
        
        # 1. Find School URL
        url = row.get('sito_web', '')
        if not isinstance(url, str) or not url.startswith('http'):
            try:
                url = find_school_url(name, city, school_id)
            except Exception as e:
                logger.error(f"Scraper error: {e}")
                url = None
                
            if url:
                df.at[index, 'sito_web'] = url
            else:
                 logger.warning(f"  -> Site not found for {name}")
                 continue # Can't find PTOF without site (mostly), unless we do direct search purely? 
                 # Actually find_ptof_link has a fallback for direct search even if base_url is None IF we pass params.
                 # Let's try passing None as base_url to find_ptof_link if site search failed.
                 
        # 2. Find PTOF Link
        # Check if already present?
        existing_ptof = row.get('ptof_link', '')
        if isinstance(existing_ptof, str) and existing_ptof.startswith('http'):
            logger.info(f"  -> Using existing PTOF: {existing_ptof}")
            continue
            
        ptof_url = find_ptof_link(url, name, city)
        
        if ptof_url:
            logger.info(f"  -> Found PTOF: {ptof_url}")
            df.at[index, 'ptof_link'] = ptof_url
        else:
            logger.warning("  -> PTOF not found.")
            df.at[index, 'ptof_link'] = "NOT_FOUND"
            
        # Save periodically
        if (index + 1) % 5 == 0:
            df.to_csv(OUTPUT_FILE, sep=';', index=False, encoding='utf-8-sig')
            logger.info(f"Saved interim results to {OUTPUT_FILE}")
            
        time.sleep(1) # Polite delay
            
    # Final save
    df.to_csv(OUTPUT_FILE, sep=';', index=False, encoding='utf-8-sig')
    logger.info(f"Discovery complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
