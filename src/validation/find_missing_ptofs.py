import pandas as pd
import glob
import time
import os
import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("discovery.log"),
    logging.StreamHandler()
])

MISSING_FILE = 'data/missing_ptofs.csv'
FOUND_CANDIDATES_FILE = 'data/found_ptof_candidates.csv'
METADATA_FILES = glob.glob('data/liste invalsi/paccmb_elenc*.csv')
CANDIDATI_FILE = 'data/candidati_ptof.csv'
BATCH_SIZE = 10

# Direct Portal URLs
UNICA_PTOF_URL = "https://unica.istruzione.gov.it/cercalatuascuola/istituti/{code}/ptof/"
SCUOLA_IN_CHIARO_URL = "https://cercalatuascuola.istruzione.it/cercalatuascuola/istituti/{code}/"

# Session for HTTP requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def load_full_metadata():
    """Load metadata from paccmb files and candidati_ptof.csv"""
    metadata_list = []
    for f in METADATA_FILES:
        try:
            df = pd.read_csv(f, sep=';', on_bad_lines='skip')
            df.columns = [c.lower() for c in df.columns]
            if 'istituto' in df.columns:
                df['istituto'] = df['istituto'].astype(str).str.strip().str.upper()
            metadata_list.append(df)
        except Exception as e:
            logging.error(f"Error reading {f}: {e}")
    
    full_metadata = pd.concat(metadata_list, ignore_index=True) if metadata_list else pd.DataFrame()
    
    if os.path.exists(CANDIDATI_FILE):
        try:
            cand_df = pd.read_csv(CANDIDATI_FILE, sep=';', on_bad_lines='skip')
            cand_df.columns = [c.lower() for c in cand_df.columns]
            if 'istituto' in cand_df.columns:
                cand_df['istituto'] = cand_df['istituto'].astype(str).str.strip().str.upper()
                cand_df.rename(columns={'denominazionescuola': 'nome_istituto'}, inplace=True)
                cols_to_keep = [c for c in ['istituto', 'nome_istituto', 'nome_comune'] if c in cand_df.columns]
                cand_df = cand_df[cols_to_keep]
                full_metadata = pd.concat([full_metadata, cand_df], ignore_index=True)
        except Exception as e:
            logging.error(f"Error reading {CANDIDATI_FILE}: {e}")

    if 'istituto' in full_metadata.columns:
        full_metadata = full_metadata.sort_values(by=['nome_istituto', 'nome_comune'], na_position='last')
        full_metadata = full_metadata.groupby('istituto').first().reset_index()
        
    return full_metadata

def check_url(url, timeout=10):
    """Check if a URL is accessible and returns relevant content."""
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            # Check if the page contains PTOF-related content
            content = response.text.lower()
            if 'ptof' in content or 'piano triennale' in content:
                return True, response.url
        return False, None
    except requests.RequestException as e:
        logging.debug(f"Request failed for {url}: {e}")
        return False, None

def find_ptof_direct(school_code):
    """Try direct URL access to find PTOF for a school."""
    results = []
    
    # Strategy 1: Unica Portal PTOF page
    unica_url = UNICA_PTOF_URL.format(code=school_code)
    logging.info(f"Checking Unica portal: {unica_url}")
    success, final_url = check_url(unica_url)
    if success:
        results.append({
            'source': 'Unica Portal',
            'url': final_url or unica_url
        })
    
    # Strategy 2: Scuola in Chiaro main page (may contain PTOF link)
    sic_url = SCUOLA_IN_CHIARO_URL.format(code=school_code)
    logging.info(f"Checking Scuola in Chiaro: {sic_url}")
    success, final_url = check_url(sic_url)
    if success:
        results.append({
            'source': 'Scuola in Chiaro',
            'url': final_url or sic_url
        })
    
    # Strategy 3: Try lowercase code variant (some schools use this)
    unica_lower_url = UNICA_PTOF_URL.format(code=school_code.lower())
    if not results:
        logging.info(f"Trying lowercase: {unica_lower_url}")
        success, final_url = check_url(unica_lower_url)
        if success:
            results.append({
                'source': 'Unica Portal (lowercase)',
                'url': final_url or unica_lower_url
            })
    
    time.sleep(0.5)  # Polite delay between requests
    return results

def main():
    if not os.path.exists(MISSING_FILE):
        logging.error(f"Missing file {MISSING_FILE} not found.")
        return

    missing_df = pd.read_csv(MISSING_FILE)
    if missing_df.empty:
        logging.info("No missing schools found.")
        return
        
    logging.info(f"Total missing schools: {len(missing_df)}")
    
    metadata = load_full_metadata()
    
    # Resume logic
    if os.path.exists(FOUND_CANDIDATES_FILE):
        existing_results = pd.read_csv(FOUND_CANDIDATES_FILE)
        processed_schools = set(existing_results['istituto'].unique())
        logging.info(f"Already processed {len(processed_schools)} schools.")
    else:
        existing_results = pd.DataFrame()
        processed_schools = set()

    to_process = missing_df[~missing_df['istituto'].isin(processed_schools)]
    
    if to_process.empty:
        logging.info("All missing schools have been processed.")
        return

    batch = to_process.head(BATCH_SIZE)
    logging.info(f"Processing batch of {len(batch)} schools...")
    
    new_results = []
    
    for _, row in batch.iterrows():
        code = row['istituto']
        
        # Get school details from metadata
        name = "Unknown"
        city = "Unknown"
        
        if not metadata.empty:
            match = metadata[metadata['istituto'] == code]
            if not match.empty:
                name = match.iloc[0].get('nome_istituto', 'Unknown')
                city = match.iloc[0].get('nome_comune', 'Unknown')
        
        logging.info(f"Processing {code} - {name} ({city})")
        
        # Direct portal access
        candidates = find_ptof_direct(code)
        
        if candidates:
            for c in candidates:
                new_results.append({
                    'istituto': code,
                    'denominazione': name,
                    'comune': city,
                    'source': c['source'],
                    'found_url': c['url']
                })
        else:
            new_results.append({
                'istituto': code,
                'denominazione': name,
                'comune': city,
                'source': 'DIRECT_ACCESS',
                'found_url': 'NOT_FOUND'
            })
    
    if new_results:
        new_df = pd.DataFrame(new_results)
        if not os.path.exists(FOUND_CANDIDATES_FILE):
            new_df.to_csv(FOUND_CANDIDATES_FILE, index=False)
        else:
            new_df.to_csv(FOUND_CANDIDATES_FILE, mode='a', header=False, index=False)
        
        logging.info(f"Batch complete. Results saved to {FOUND_CANDIDATES_FILE}")
    else:
        logging.info("Batch complete. No results found.")

if __name__ == "__main__":
    main()
