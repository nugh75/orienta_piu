import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

def test_clts(code):
    # url = f"https://cercalatuascuola.istruzione.it/cercalatuascuola/istituti/{code}/"
    url = f"https://cercalatuascuola.istruzione.it/cercalatuascuola/ricerca/risultati?codiceMeccanografico={code}&radio=codice"
    logging.info(f"Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        logging.info(f"Status: {r.status_code}")
        
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Look for website link
        # It's usually in a specific section.
        # Let's search for any link that contains 'http' and is not internal.
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().strip()
            
            if 'http' in href and 'istruzione.it' not in href:
                logging.info(f"Potential external link: {text} -> {href}")
            
            # Specific check for structure (often "Sito web: ...")
            
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    test_clts("VTIC82500A")
