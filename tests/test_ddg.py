import requests
from bs4 import BeautifulSoup

def test_ddg_html(query):
    print(f"Searching DDG HTML for: {query}")
    url = "https://html.duckduckgo.com/html/"
    data = {'q': query}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # DDG HTML results are usually in <a class="result__a">
        found = False
        for a in soup.find_all('a', class_='result__a'):
            print(f"Found: {a.get_text()} -> {a['href']}")
            found = True
            
        if not found:
            print("No results found in DDG HTML.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ddg_html("PTOF G. NICOLINI CAPRANICA filetype:pdf")
