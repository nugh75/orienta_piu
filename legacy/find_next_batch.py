import pandas as pd
import os

def main():
    # Load processed schools
    if os.path.exists("candidati_ptof.csv"):
        try:
            processed_df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='utf-8', on_bad_lines='skip')
        except:
            processed_df = pd.read_csv("candidati_ptof.csv", sep=';', encoding='latin1', on_bad_lines='skip')
        processed_codes = set(processed_df['istituto'].astype(str).str.strip().unique())
    else:
        processed_codes = set()

    # Load missing schools candidate list
    # Assuming missing_schools.csv has no header or specific header. 
    # Let's inspect first lines to be sure. But usually it's Code;Name;City...
    # We'll assume standard CSV format without header or with 'istituto' if present.
    # To be safe, let's try to read it as a raw list and infer columns.
    
    try:
        # Try reading with header
        candidates_df = pd.read_csv("missing_schools.csv", sep=';', encoding='utf-8', on_bad_lines='skip')
        # Check if 'istituto' column exists
        if 'istituto' not in candidates_df.columns:
            # If not, maybe it's headerless. Reload.
             candidates_df = pd.read_csv("missing_schools.csv", sep=';', encoding='utf-8', header=None, on_bad_lines='skip')
             # Assume col 0 is code, col 1 name, col 2 city
             candidates_df.columns = ['istituto', 'denominazionescuola', 'comunescuola'] + [f'col_{i}' for i in range(3, len(candidates_df.columns))]
    except:
         # Fallback latin1
         candidates_df = pd.read_csv("missing_schools.csv", sep=';', encoding='latin1', header=None, on_bad_lines='skip')
         candidates_df.columns = ['istituto', 'denominazionescuola', 'comunescuola'] + [f'col_{i}' for i in range(3, len(candidates_df.columns))]

    candidates_df['istituto'] = candidates_df['istituto'].astype(str).str.strip()

    # robust filtering
    verified_missing = candidates_df[~candidates_df['istituto'].isin(processed_codes)]
    
    print(f"Total candidates in missing_schools.csv: {len(candidates_df)}")
    print(f"Total processed in candidati_ptof.csv: {len(processed_codes)}")
    print(f"True missing count: {len(verified_missing)}")
    
    print("--- NEXT BATCH (First 20) ---")
    for idx, row in verified_missing.head(20).iterrows():
        # Handle column names dynamically or mapped
        ist = row.get('istituto')
        name = row.get('nome') if 'nome' in row else row.get('denominazionescuola')
        city = row.get('citta') if 'citta' in row else row.get('comunescuola')
        print(f"{ist}|{name}|{city}")

if __name__ == "__main__":
    main()
