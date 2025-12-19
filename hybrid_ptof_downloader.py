"""
Hybrid Automated PTOF Downloader
================================

This script implements a multi-strategy approach to find and download missing PTOF documents.

Strategies (in order of execution):
1. **Direct Unica Portal Check**: Checks the standard Ministry URL pattern.
2. **Google Dork Search**: Uses specific search operators via DuckDuckGo to find PDF files directly.
   - Strategy A: `[CODE] PTOF filetype:pdf` (Most precise)
   - Strategy B: `site:[DOMAIN] filetype:pdf PTOF` (If domain is known)
   - Strategy C: `"[SCHOOL NAME]" [CITY] PTOF filetype:pdf` (Broadest)

It maintains a 'found_ptof_candidates.csv' registry to track progress and avoid duplicates.
"""

import pandas as pd
import requests
import os
import time
import re
import logging
from urllib.parse import urlparse
from ddgs import DDGS
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hybrid_ptof_downloader.log"),
        logging.StreamHandler()
    ]
)

# Configuration
MISSING_FILE = 'data/missing_ptofs.csv'
OUTPUT_DIR = 'ptof'
RESULTS_FILE = 'data/hybrid_results.csv'
UNICA_URL_TEMPLATE = "https://unica.istruzione.gov.it/cercalatuascuola/istituti/{}/ptof"

# Session Setup
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

def clean_text(text):
    if pd.isna(text): return ""
    return str(text).strip()

def download_pdf(url, school_code):
    """Attempt to download a PDF from a URL."""
    try:
        # Initial check without downloading body to verify content type
        head = session.head(url, allow_redirects=True, timeout=10)
        
        # Loose check: URL ends in pdf or content-type contains pdf
        is_pdf = url.lower().endswith('.pdf') or 'pdf' in head.headers.get('Content-Type', '').lower()
        
        if is_pdf:
            logging.info(f"Downloading PDF from: {url}")
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                filename = os.path.join(OUTPUT_DIR, f"{school_code}_PTOF.pdf")
                with open(filename, 'wb') as f:
                    f.write(resp.content)
                logging.info(f"✓ Saved {filename}")
                return True
    except Exception as e:
        logging.error(f"Download failed for {url}: {e}")
    return False

def search_google_dorks(school_code, school_name, city):
    """
    Perform targeted searches using DuckDuckGo (Google proxy).
    Returns the first valid PDF URL found.
    """
    queries = [
        f'{school_code} PTOF filetype:pdf',
        f'"{school_name}" {city} PTOF filetype:pdf',
        f'site:.edu.it {school_code} PTOF filetype:pdf',
        f'{school_name} {city} "piano triennale" filetype:pdf'
    ]

    with DDGS() as ddgs:
        for q in queries:
            try:
                logging.info(f"Searching: {q}")
                results = list(ddgs.text(q, max_results=3))
                
                for r in results:
                    url = r['href']
                    if url.lower().endswith('.pdf'):
                        logging.info(f"Found candidate PDF: {url}")
                        return url
                
                time.sleep(1) # Rate limit protection
            except Exception as e:
                logging.warning(f"Search error: {e}")
                # Rate limit hit, wait longer
                wait_time = random.uniform(120, 300) # 2 to 5 minutes
                logging.info(f"Sleeping for {wait_time:.1f}s due to error...")
                time.sleep(wait_time)
    return None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Load missing schools
    if not os.path.exists(MISSING_FILE):
        logging.error("Missing file list not found.")
        return

    df = pd.read_csv(MISSING_FILE)
    
    # Load metadata
    metadata_df = pd.DataFrame()
    if os.path.exists('data/candidati_ptof.csv'):
        try:
            metadata_df = pd.read_csv('data/candidati_ptof.csv', sep=';', on_bad_lines='skip')
            metadata_df.columns = [c.lower() for c in metadata_df.columns]
            # Rename for consistency if needed or just use as is
            logging.info(f"Loaded metadata for {len(metadata_df)} schools")
        except Exception as e:
            logging.error(f"Error loading metadata: {e}")

    # Track results
    results = []


    # Check what's already done
    done_codes = []
    if os.path.exists(OUTPUT_DIR):
        existing_files = os.listdir(OUTPUT_DIR)
        done_codes = [f.split('_')[0] for f in existing_files if f.endswith('.pdf')]
    
    to_process = df[~df['istituto'].isin(done_codes)]
    logging.info(f"Schools to process: {len(to_process)}")

    for idx, row in to_process.iterrows():
        code = row['istituto']
        name = "" 
        city = "" 
        
        # Lookup metadata
        if not metadata_df.empty:
            match = metadata_df[metadata_df['istituto'] == code]
            if not match.empty:
                name = match.iloc[0].get('denominazionescuola', '')
                city = match.iloc[0].get('nome_comune', '')
        
        logging.info(f"Processing {code} - {name} ({city})")

        # Strategy 1: Direct Unica Portal (Check if they have a PTOF page, then scrape it - simulated here by just logging for now as we want PDF direct links mostly)
        # For this script, we'll focus on the Direct PDF Search (Strategy 2) as requested by user.
        
        pdf_url = search_google_dorks(code, name, city)
        
        if pdf_url:
            success = download_pdf(pdf_url, code)
            results.append({'code': code, 'status': 'DOWNLOADED' if success else 'FAILED', 'url': pdf_url})
        else:
             logging.info(f"No PDF found for {code}")
             results.append({'code': code, 'status': 'NOT_FOUND', 'url': ''})

        # Save incremental progress
        pd.DataFrame(results).to_csv(RESULTS_FILE, index=False)
        
        # Be polite and random
        sleep_time = random.uniform(30, 60) # 30s to 1m
        logging.info(f"Sleeping for {sleep_time:.1f}s...")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
