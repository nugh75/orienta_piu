import requests
import os

def download_file(url, filepath):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        print(f"Downloading {url} to {filepath}...")
        r = requests.get(url, headers=headers, stream=True, verify=False, timeout=30)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("  -> Success")
        else:
            print(f"  -> Failed with status {r.status_code}")
    except Exception as e:
        print(f"  -> Error: {e}")

def main():
    download_dir = "scuola_in_chiaro"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # BGIC87900D - CAROLI STEZZANO (Corrected URL via Madisoft)
    url_bg = "https://nuvola.madisoft.it/bacheca-digitale/32959-ic-caroli/allegati/ptof_ic_caroli_22-25-aggiornamento_24-25.pdf"
    download_file(url_bg, os.path.join(download_dir, "STEZZANO_BGIC87900D.pdf"))

    # PEIC83300G - PESCARA 3
    # Still need valid URL. Skipping for now or using placeholder.

    # RAIC82800B - RAVENNA CERVIA (Andrea Canevaro)
    # Placeholder for update

    
    # MIIC85700P - Done by crawler.
    
    # VTIC82500A - Done by crawler.

if __name__ == "__main__":
    main()
