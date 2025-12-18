import pandas as pd
import requests
import re
import os
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings()

def sanitize_filename(name):
    return "".join([c if c.isalnum() else "_" for c in name])

def find_ptof_link(html, base_url):
    # Regex to find hrefs with "ptof" and ending in "pdf" (case insensitive)
    # Simple heuristic
    links = re.findall(r'href=["\'](.*?)["\']', html, re.IGNORECASE)
    candidates = []
    for link in links:
        if "ptof" in link.lower() and "pdf" in link.lower():
            candidates.append(link)
        elif "piano" in link.lower() and "offerta" in link.lower() and "pdf" in link.lower():
            candidates.append(link)
            
    # Normalize
    full_links = [urljoin(base_url, l) for l in candidates]
    return full_links

def download_file(url, filepath):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, verify=False, timeout=15)
        if r.status_code == 200 and 'application/pdf' in r.headers.get('Content-Type', ''):
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            # Try to read start of file to see if it's PDF
            content_sample = r.content[:4]
            if content_sample == b'%PDF':
                 with open(filepath, 'wb') as f:
                    f.write(r.content)
                 return True
            print(f"  -> Not a PDF or status {r.status_code}: {url}")
            return False
    except Exception as e:
        print(f"  -> Error downloading {url}: {e}")
        return False

def main():
    if not os.path.exists("candidati_ptof.csv"):
        print("CSV not found.")
        return
        
    try:
        df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='utf-8', on_bad_lines='skip')
    except:
        df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='latin1', on_bad_lines='skip')

    # Filter for schools NOT in ptof_downloads (conceptually, or just overwrite/fill gaps)
    # We will use the identify_missing logic inside
    
    download_dir = "scuola_in_chiaro" # As requested by user "cartella scuola in chiaro"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    existing_files = os.listdir("ptof_downloads") if os.path.exists("ptof_downloads") else []
    
    # We assume candidati_ptof contains: Name;City;Code;URL...
    # Let's handle the column index carefully.
    
    count = 0
    for idx, row in df.iterrows():
        # Heuristic to find Code and URL columns
        code = None
        url = None
        city = None
        
        for item in row:
            s = str(item).strip()
            if re.match(r'^[A-Z]{2}[A-Z0-9]{8}$', s):
                code = s
            elif s.startswith('http'):
                url = s
            # City is harder, usually col 1 or 2.
        
        # Fallback to fixed indices if heuristic fails or for safety
        if not code and len(row) > 2:
             # Based on batch19: Code, Name, City, URL
             # Based on candidati_ptof standard: Name, City, Code, URL
             # Let's rely on the previous fix
             pass
             
        # Let's just use the column indices 
        # Standard: 0=Name, 1=City, 2=Code, 3=URL
        try:
            name_val = str(row.iloc[0])
            city_val = str(row.iloc[1])
            code_val = str(row.iloc[2])
            url_val = str(row.iloc[3]) if len(row) > 3 else ""
            
            if re.match(r'^[A-Z]{2}[A-Z0-9]{8}$', code_val):
                code = code_val
                city = city_val
                url = url_val
            elif re.match(r'^[A-Z]{2}[A-Z0-9]{8}$', name_val): # Swapped?
                code = name_val
                city = row.iloc[2]
                url = row.iloc[3]
        except:
            continue
            
        if not code or not city: continue
        
        safe_city = sanitize_filename(city)
        safe_code = sanitize_filename(code)
        target_filename = f"{safe_city}_{safe_code}.pdf"
        target_path = os.path.join(download_dir, target_filename)
        
        # Check if already downloaded in MAIN folder
        if target_filename in existing_files:
            # print(f"Skipping {code}, already have it.")
            continue
            
        if not url or "http" not in url:
            print(f"Skipping {code}, no URL.")
            continue
            
        print(f"Processing {code} ({city}) URL: {url}")
        
        try:
            # Visit homepage
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, verify=False, timeout=15)
            ptof_links = find_ptof_link(r.text, url)
            
            if not ptof_links:
                # Try adding /ptof or /didattica/ptof
                common_paths = ["/ptof", "/didattica/ptof", "/scuola/ptof", "/istituto/ptof"]
                for p in common_paths:
                    try:
                        sub_url = urljoin(url, p)
                        r2 = requests.get(sub_url, headers=headers, verify=False, timeout=10)
                        if r2.status_code == 200:
                            ptof_links.extend(find_ptof_link(r2.text, sub_url))
                    except: pass
            
            if ptof_links:
                # Try the first valid pdf
                success = False
                for pl in ptof_links:
                    print(f"  Found candidate: {pl}")
                    if download_file(pl, target_path):
                        print(f"  DOWNLOADED: {target_filename}")
                        success = True
                        count += 1
                        break
                if not success:
                    print(f"  Failed to download valid PDF for {code}")
            else:
                print(f"  No PTOF links found for {code}")
                
        except Exception as e:
            print(f"  Error accessing {url}: {e}")

    print(f"Crawler finished. Downloaded {count} new files.")

if __name__ == "__main__":
    main()
