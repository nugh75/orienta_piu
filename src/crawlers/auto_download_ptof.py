"""
Automated PTOF Discovery and Download Script v2

Strategy:
1. Find official school website (.edu.it domain) from search
2. Do site-specific search: "site:school.edu.it PTOF filetype:pdf"
3. Fallback: "site:school.edu.it offerta formativa"
4. Download PDFs directly

Author: Automated by Antigravity
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import time
import re
import logging
import glob
from urllib.parse import urljoin, urlparse
from duckduckgo_search import DDGS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ptof_discovery.log"),
        logging.StreamHandler()
    ]
)

# Configuration
MISSING_FILE = 'data/missing_ptofs.csv'
RESULTS_FILE = 'data/auto_download_results.csv'
OUTPUT_DIR = 'ptof'
METADATA_FILES = glob.glob('data/liste invalsi/paccmb_elenc*.csv')
CANDIDATI_FILE = 'data/candidati_ptof.csv'
BATCH_SIZE = 10

# HTTP Session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})


def load_metadata():
    """Load and merge metadata from all CSV sources."""
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
                cols = [c for c in ['istituto', 'nome_istituto', 'nome_comune'] if c in cand_df.columns]
                full_metadata = pd.concat([full_metadata, cand_df[cols]], ignore_index=True)
        except Exception as e:
            logging.error(f"Error reading {CANDIDATI_FILE}: {e}")

    if 'istituto' in full_metadata.columns:
        full_metadata = full_metadata.sort_values(by=['nome_istituto', 'nome_comune'], na_position='last')
        full_metadata = full_metadata.groupby('istituto').first().reset_index()
        
    return full_metadata


def find_school_domain(school_name, city, school_code):
    """
    Step 1: Find the school's official domain.
    More flexible matching to improve success rate.
    """
    # Clean school name for search
    clean_name = re.sub(r'[^\w\s]', ' ', school_name).strip()
    
    queries = [
        f'{clean_name} {city} sito ufficiale',
        f'{school_code} sito ufficiale',
        f'{clean_name} {city}',
        f'{school_code} scuola',
    ]
    
    candidates = []
    
    with DDGS() as ddgs:
        for q in queries:
            try:
                logging.info(f"Finding domain: {q}")
                results = list(ddgs.text(q, max_results=10))
                
                for r in results:
                    url = r['href']
                    domain = urlparse(url).netloc
                    title = r['title'].lower()
                    
                    # Skip known non-school domains
                    skip_domains = ['google', 'facebook', 'instagram', 'twitter', 
                                    'youtube', 'wikipedia', 'linkedin', 'miur.gov.it',
                                    'istruzione.gov.it', 'unica.istruzione', 'bing.']
                    
                    if any(s in domain for s in skip_domains):
                        continue
                    
                    # Score the domain
                    score = 0
                    
                    # .edu.it is ideal
                    if '.edu.it' in domain:
                        score += 20
                    
                    # School-related domains
                    if any(kw in domain for kw in ['scuola', 'istituto', 'liceo', 'ic', 'iis', 'itis', 'ips']):
                        score += 10
                    
                    # Match school name in domain or title
                    name_parts = clean_name.lower().split()
                    for part in name_parts:
                        if len(part) > 3 and part in domain.lower():
                            score += 5
                        if len(part) > 3 and part in title:
                            score += 3
                    
                    # Match city
                    if city.lower() in domain.lower() or city.lower() in title:
                        score += 5
                    
                    if score > 0:
                        candidates.append({'domain': domain, 'score': score, 'url': url})
                
                time.sleep(1)
                
            except Exception as e:
                logging.warning(f"Search failed: {e}")
    
    # Sort by score and return best match
    if candidates:
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]
        logging.info(f"Found domain: {best['domain']} (score: {best['score']})")
        return best['domain']
    
    return None


def search_site_for_ptof(domain, school_code):
    """
    Step 2: Search within the school's site for PTOF PDF.
    Uses: site:domain PTOF filetype:pdf
    Fallback: site:domain offerta formativa
    """
    queries = [
        f'site:{domain} PTOF filetype:pdf',
        f'site:{domain} offerta formativa filetype:pdf',
        f'site:{domain} PTOF',
        f'site:{domain} piano triennale offerta formativa',
    ]
    
    pdf_urls = []
    
    with DDGS() as ddgs:
        for q in queries:
            try:
                logging.info(f"Site search: {q}")
                results = list(ddgs.text(q, max_results=5))
                
                for r in results:
                    url = r['href']
                    title = r['title'].lower()
                    
                    # Check if it's a PDF or PTOF-related
                    if url.lower().endswith('.pdf'):
                        pdf_urls.append({
                            'url': url,
                            'title': r['title'],
                            'type': 'pdf'
                        })
                    elif 'ptof' in title or 'offerta formativa' in title or 'piano triennale' in title:
                        pdf_urls.append({
                            'url': url,
                            'title': r['title'],
                            'type': 'page'
                        })
                
                time.sleep(1)
                
                # If we found PDFs, stop searching
                if any(p['type'] == 'pdf' for p in pdf_urls):
                    break
                    
            except Exception as e:
                logging.warning(f"Site search failed: {e}")
    
    return pdf_urls


def extract_pdfs_from_page(page_url):
    """
    If search returns a page (not PDF), visit it and find PDF links.
    """
    pdf_links = []
    
    try:
        response = session.get(page_url, timeout=15)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            if href.lower().endswith('.pdf'):
                full_url = urljoin(page_url, href)
                
                # Check if it's PTOF-related
                if 'ptof' in href.lower() or 'ptof' in text or 'piano' in text or 'offerta' in text:
                    pdf_links.append(full_url)
        
    except Exception as e:
        logging.warning(f"Error extracting PDFs from {page_url}: {e}")
    
    return pdf_links


def download_pdf(pdf_url, school_code, output_dir):
    """Download PDF and save."""
    try:
        response = session.get(pdf_url, timeout=30)
        
        if response.status_code == 200:
            # Verify it's a PDF
            if response.content[:4] == b'%PDF':
                filename = f"{school_code}_PTOF.pdf"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                logging.info(f"✓ Downloaded: {filename} ({len(response.content)} bytes)")
                return filepath
    
    except Exception as e:
        logging.warning(f"Download failed: {e}")
    
    return None


def process_school(school_code, school_name, city):
    """Main processing function for a single school."""
    result = {
        'istituto': school_code,
        'denominazione': school_name,
        'comune': city,
        'status': 'NOT_FOUND',
        'domain': None,
        'pdf_url': None
    }
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Processing: {school_code} - {school_name} ({city})")
    logging.info(f"{'='*60}")
    
    # Step 1: Find school domain
    domain = find_school_domain(school_name, city, school_code)
    
    if not domain:
        logging.warning(f"✗ No domain found for {school_code}")
        return result
    
    result['domain'] = domain
    
    # Step 2: Site-specific search for PTOF
    ptof_results = search_site_for_ptof(domain, school_code)
    
    if not ptof_results:
        logging.warning(f"✗ No PTOF found on {domain}")
        return result
    
    # Step 3: Download PDFs
    for item in ptof_results:
        if item['type'] == 'pdf':
            # Direct PDF download
            filepath = download_pdf(item['url'], school_code, OUTPUT_DIR)
            if filepath:
                result['status'] = 'DOWNLOADED'
                result['pdf_url'] = item['url']
                return result
        
        else:
            # It's a page, extract PDFs from it
            pdf_links = extract_pdfs_from_page(item['url'])
            for pdf_url in pdf_links:
                filepath = download_pdf(pdf_url, school_code, OUTPUT_DIR)
                if filepath:
                    result['status'] = 'DOWNLOADED'
                    result['pdf_url'] = pdf_url
                    return result
    
    return result


def main():
    """Main execution function."""
    if not os.path.exists(MISSING_FILE):
        logging.error(f"File not found: {MISSING_FILE}")
        return
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Load data
    missing_df = pd.read_csv(MISSING_FILE)
    metadata = load_metadata()
    
    logging.info(f"Total missing schools: {len(missing_df)}")
    
    # Check already downloaded
    downloaded = set()
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('_PTOF.pdf'):
            code = f.replace('_PTOF.pdf', '')
            downloaded.add(code)
    
    logging.info(f"Already downloaded: {len(downloaded)} PTOFs")
    
    # Filter to remaining schools
    to_process = missing_df[~missing_df['istituto'].isin(downloaded)]
    
    if to_process.empty:
        logging.info("All schools have been processed!")
        return
    
    # Process batch
    batch = to_process.head(BATCH_SIZE)
    logging.info(f"\nProcessing batch of {len(batch)} schools...\n")
    
    results = []
    
    for _, row in batch.iterrows():
        code = row['istituto']
        
        # Get metadata
        name = "Unknown"
        city = "Unknown"
        
        if not metadata.empty:
            match = metadata[metadata['istituto'] == code]
            if not match.empty:
                name = str(match.iloc[0].get('nome_istituto', 'Unknown'))
                city = str(match.iloc[0].get('nome_comune', 'Unknown'))
        
        result = process_school(code, name, city)
        results.append(result)
        
        time.sleep(2)  # Polite delay
    
    # Save results
    if results:
        results_df = pd.DataFrame(results)
        
        if not os.path.exists(RESULTS_FILE):
            results_df.to_csv(RESULTS_FILE, index=False)
        else:
            results_df.to_csv(RESULTS_FILE, mode='a', header=False, index=False)
        
        downloaded_count = len([r for r in results if r['status'] == 'DOWNLOADED'])
        logging.info(f"\n{'='*60}")
        logging.info(f"BATCH COMPLETE: Downloaded {downloaded_count}/{len(results)}")
        logging.info(f"Results saved to {RESULTS_FILE}")
        logging.info(f"{'='*60}")


if __name__ == "__main__":
    main()
