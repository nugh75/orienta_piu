import pandas as pd
import logging
from ptof_pipeline.scraper import find_ptof_link

# Update logging to show finding
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INPUT_FILE = "candidati_ptof.csv"

def main():
    logger.info("Starting Augmentation...")
    
    # Read CSV
    # handle reading errors / header
    try:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8')
    except:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='latin1')
        
    updated = False
    
    for index, row in df.iterrows():
        sito = row.get('sito_web')
        ptof = row.get('ptof_link')
        name = row.get('denominazionescuola', 'School')
        city = row.get('nome_comune', 'City')
        
        # If we have a site but NO PTOF link, try to find it
        if pd.notna(sito) and str(sito).startswith('http') and (pd.isna(ptof) or str(ptof).strip() == '' or str(ptof) == 'nan'):
            logger.info(f"Crawling {name} at {sito}...")
            # We pass name/city but they are used for fallback search. 
            # We want to avoid fallback search if possible to avoid blocking.
            # But the scraper implementation does fallback automatically if name is provided.
            # To avoid using search engine, we might pass None for name?
            # No, if crawling fails, we might want to skip search engine.
            # Let's verify scraper.py again.
            # scraper.py:90: find_ptof_link(base_url, school_name=None, city=None)
            # Lines 145: if not best_link and school_name: -> find_direct_ptof_url
            # So if we pass school_name=None, it won't trigger the fallback search!
            # Perfect. We only want site crawling here.
            
            found_link = find_ptof_link(sito, school_name=None, city=None)
            
            if found_link:
                logger.info(f"  -> Found: {found_link}")
                df.at[index, 'ptof_link'] = found_link
                updated = True
            else:
                logger.info(f"  -> No PDF found on site.")
    
    if updated:
        logger.info("Saving updated CSV...")
        df.to_csv(INPUT_FILE, sep=';', index=False)
    else:
        logger.info("No new links found.")

if __name__ == "__main__":
    main()
