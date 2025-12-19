import pandas as pd
import os
import requests
import logging
import time
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("download.log"),
    logging.StreamHandler()
])

FOUND_CANDIDATES_FILE = 'data/found_ptof_candidates.csv'
OUTPUT_DIR = 'ptof'

# Session for HTTP requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def download_ptof_from_unica(school_code, page_url):
    """
    Navigate to Unica PTOF page and find/download the PDF.
    The Unica portal has download links for PTOF documents.
    """
    try:
        logging.info(f"Fetching PTOF page: {page_url}")
        response = session.get(page_url, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch page: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for PDF download links
        # Unica portal typically has links with 'download' or 'pdf' in href
        pdf_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            if '.pdf' in href.lower() or 'download' in href.lower() or 'ptof' in text:
                # Resolve relative URLs
                if href.startswith('/'):
                    href = 'https://unica.istruzione.gov.it' + href
                elif not href.startswith('http'):
                    href = page_url.rsplit('/', 1)[0] + '/' + href
                
                pdf_links.append(href)
        
        if not pdf_links:
            # Try to find any link with render/document/ptof pattern
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'render/document/ptof' in href or 'prgDoc' in href:
                    if href.startswith('/'):
                        href = 'https://unica.istruzione.gov.it' + href
                    pdf_links.append(href)
        
        if pdf_links:
            # Try to download the first PDF link
            for pdf_url in pdf_links[:3]:  # Try first 3 links
                logging.info(f"Attempting download: {pdf_url}")
                try:
                    pdf_response = session.get(pdf_url, timeout=60)
                    
                    # Check if it's a PDF
                    content_type = pdf_response.headers.get('Content-Type', '')
                    if 'pdf' in content_type.lower() or pdf_url.lower().endswith('.pdf'):
                        filename = f"{school_code}_PTOF.pdf"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(pdf_response.content)
                        
                        logging.info(f"Downloaded: {filename}")
                        return filepath
                except Exception as e:
                    logging.warning(f"Download failed for {pdf_url}: {e}")
                    continue
        
        logging.warning(f"No downloadable PDF found on page")
        return None
        
    except Exception as e:
        logging.error(f"Error processing {page_url}: {e}")
        return None

def main():
    if not os.path.exists(FOUND_CANDIDATES_FILE):
        logging.error(f"Candidates file {FOUND_CANDIDATES_FILE} not found.")
        return
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    df = pd.read_csv(FOUND_CANDIDATES_FILE)
    
    # Filter to only valid URLs (not NOT_FOUND)
    valid_df = df[df['found_url'] != 'NOT_FOUND']
    
    logging.info(f"Found {len(valid_df)} schools with valid PTOF URLs")
    
    downloaded = 0
    failed = 0
    
    for _, row in valid_df.iterrows():
        code = row['istituto']
        url = row['found_url']
        name = row.get('denominazione', 'Unknown')
        
        # Check if already downloaded
        expected_file = os.path.join(OUTPUT_DIR, f"{code}_PTOF.pdf")
        if os.path.exists(expected_file):
            logging.info(f"Already downloaded: {code}")
            downloaded += 1
            continue
        
        logging.info(f"Processing {code} - {name}")
        
        result = download_ptof_from_unica(code, url)
        
        if result:
            downloaded += 1
        else:
            failed += 1
        
        time.sleep(1)  # Polite delay
    
    logging.info(f"Download complete. Success: {downloaded}, Failed: {failed}")

if __name__ == "__main__":
    main()
