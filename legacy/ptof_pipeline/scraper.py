import requests
from bs4 import BeautifulSoup
import logging
import urllib.parse
import time

# Configure logging if not already
logger = logging.getLogger(__name__)

def ddg_html_search(query, max_results=5):
    """
    Performs a search using html.duckduckgo.com (no JS).
    """
    url = "https://html.duckduckgo.com/html/"
    data = {'q': query}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    results = []
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for a in soup.find_all('a', class_='result__a'):
                href = a['href']
                
                # DDG links might be wrapped/redirects but result__a usually works
                if href.startswith('//'):
                    href = 'https:' + href
                
                # Filter out ad bumps if any
                if 'duckduckgo' not in href:
                    results.append(href)
                    if len(results) >= max_results:
                        break
    except Exception as e:
        logger.warning(f"DDG HTML Search error: {e}")
    
    return results

def find_school_url(school_name, city, school_code=None):
    """
    Finds school website using DDG HTML.
    """
    logger.info(f"Searching URL for {school_name} {city}")
    
    # 1. Try rigid search with code if available
    if school_code:
        query = f"{school_code} {city} sito ufficiale"
        urls = ddg_html_search(query)
        for url in urls:
             if ('edu.it' in url or 'gov.it' in url):
                  if 'istruzione.gov.it' not in url and 'cercalatuascuola' not in url and 'tuttitalia' not in url:
                      logger.info(f"  -> Found High Conf URL (Code): {url}")
                      return url

    # 2. Search by name + city
    query = f"scuola {school_name} {city} sito web"
    urls = ddg_html_search(query)
    logger.info(f"  [DEBUG] Raw URLs for {school_name}: {urls}")
    
    for url in urls:
        if ('edu.it' in url or 'gov.it' in url):
            if 'istruzione.gov.it' not in url and 'cercalatuascuola' not in url and 'tuttitalia' not in url:
                logger.info(f"  -> Found High Conf URL (Name): {url}")
                return url
    
    # Fallback
    for url in urls:
         if '.it' in url and 'facebook' not in url and 'instagram' not in url and 'tuttitalia' not in url:
             logger.info(f"  -> Found URL (Fallback): {url}")
             return url
    
    return None

def find_direct_ptof_url(school_name, city):
    """
    Searches directly for the PDF file on DDG HTML.
    Query: "{school_name} {city} PTOF 2024 2025 filetype:pdf"
    """
    query = f"{school_name} {city} PTOF 2022 2025 filetype:pdf"
    urls = ddg_html_search(query, max_results=10)
    
    for url in urls:
        if url.lower().endswith('.pdf'):
            logger.info(f"  -> Found Direct PDF: {url}")
            return url
            
    return None
    
def find_ptof_link(base_url, school_name=None, city=None):
    """
    Crawls the school website to find the PTOF PDF link.
    If fails, tries direct Google search for the PDF.
    """
    
    # 1. Try crawling base_url if provided
    best_link = None
    if base_url:
        try:
            # Handle DDG redirects if potentially raw
            if 'duckduckgo.com/l/?' in base_url:
                 try:
                     head = requests.head(base_url, allow_redirects=True, timeout=5)
                     base_url = head.url
                 except:
                     pass

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            try:
                response = requests.get(base_url, headers=headers, timeout=10, verify=False)
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                keywords = ['ptof', 'piano triennale', 'offerta formativa', 'triennale']
                candidates = []
                
                for a in soup.find_all('a', href=True):
                    text = a.get_text().lower()
                    href = a['href']
                    
                    score = 0
                    if any(k in text for k in keywords):
                        score += 5
                    if 'ptof' in href.lower():
                        score += 3
                    if href.lower().endswith('.pdf'):
                        score += 5
                    
                    if score >= 5: 
                        absolute_url = urllib.parse.urljoin(base_url, href)
                        candidates.append((score, absolute_url))
                
                candidates.sort(key=lambda x: x[0], reverse=True)
                
                if candidates:
                    best_link = candidates[0][1]
                    logger.info(f"  -> Found PTOF in page: {best_link}")
                    
            except Exception as e:
                logger.warning(f"Crawling {base_url} failed: {e}")
        except Exception:
            pass
            
    # 2. If crawling failed or found nothing, try Direct PDF Search
    if not best_link and school_name:
        logger.info("  -> Site crawl empty/failed. Trying direct PDF search...")
        best_link = find_direct_ptof_url(school_name, city)
        
    return best_link
