import requests
from bs4 import BeautifulSoup
import urllib.parse

def custom_search(query):
    print(f"Searching for: {query}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = "https://www.google.com/search"
    params = {'q': query, 'num': 10, 'hl': 'it'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        links = []
        # Google structure changes, but often links are in <div> > <a href> with h3 inside
        # Or look for 'div.g a'
        
        for g in soup.find_all('div', class_='g'):
            a = g.find('a', href=True)
            if a:
                href = a['href']
                title = a.get_text()
                if href.startswith('http'):
                    links.append((title, href))
                    
        # Fallback if class 'g' not found (sometimes different layout)
        if not links:
            print("No class='g' found. Dumping all main links...")
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('http') and 'google' not in href:
                    links.append(("Unknown", href))
                    
        return links
        
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    results = custom_search('PTOF "G. NICOLINI" CAPRANICA filetype:pdf')
    for t, l in results:
        print(f"Found: {t} -> {l}")
