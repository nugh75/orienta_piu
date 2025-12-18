import os
import pandas as pd

def check_missing_downloads():
    if not os.path.exists("candidati_ptof.csv"):
        print("candidati_ptof.csv not found.")
        return

    try:
        df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='utf-8', on_bad_lines='skip')
    except:
        df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='latin1', on_bad_lines='skip')

    # Expected columns: denominazionescuola;nome_comune;istituto;sito_web;ptof_link
    # We care about 'istituto' (Code) and 'nome_comune' (City)
    
    missing_list = []
    
    # Check ptof_downloads/
    downloaded_files = os.listdir("ptof_downloads") if os.path.exists("ptof_downloads") else []
    
    # We need to match the filename pattern used by download_ptofs.py
    # Pattern: f"{city}_{code}.pdf" (sanitized)
    
    print(f"Total schools in CSV: {len(df)}")
    
    for idx, row in df.iterrows():
        if len(row) < 3: continue
        
        # Adjust indices if needed based on fix_csv_format
        # fix_csv_format prioritized: Name;City;Code;URL...
        # Let's try to detect column by length/content if headers are messy
        
        # Standard: 0=Name, 1=City, 2=Code
        code = str(row.iloc[2]).strip()
        city = str(row.iloc[1]).strip()
        
        # Sanitize for filename check
        safe_city = "".join([c if c.isalnum() else "_" for c in city])
        safe_code = "".join([c if c.isalnum() else "_" for c in code])
        
        filename = f"{safe_city}_{safe_code}.pdf"
        
        # Check simple presence (validation is done by download_ptofs, assuming present=valid for now or we check size)
        found = False
        for f in downloaded_files:
            if f == filename:
                found = True
                break
        
        if not found:
            missing_list.append(row)

    print(f"Missing downloads: {len(missing_list)}")
    print("--- First 5 Missing ---")
    for row in missing_list[:5]:
        print(f"{row.iloc[2]}|{row.iloc[0]}|{row.iloc[1]}")

if __name__ == "__main__":
    check_missing_downloads()
