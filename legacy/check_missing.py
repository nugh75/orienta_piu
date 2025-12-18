import pandas as pd
import glob
import os

def load_all_data():
    files = glob.glob('paccmb_elenc*.csv')
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, sep=';', encoding='latin1')
            dfs.append(df)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
    
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def main():
    all_df = load_all_data()
    print(f"Total input schools: {len(all_df)}")
    
    if os.path.exists("candidati_ptof.csv"):
        processed_df = pd.read_csv("candidati_ptof.csv", sep=';')
        processed_ids = set(processed_df['istituto'].astype(str))
        print(f"Processed schools: {len(processed_df)}")
    else:
        processed_ids = set()
        print("No processed schools found.")
        
    missing = []
    for index, row in all_df.iterrows():
        sid = str(row.get('istituto', '')).strip()
        if sid not in processed_ids:
            name = row.get('nome_istituto', row.get('denominazionescuola', 'Unknown'))
            city = row.get('nome_comune', 'Unknown')
            missing.append(f"{sid};{name};{city}")
            
    print(f"Missing schools: {len(missing)}")
    
    with open("missing_schools.csv", "w") as f:
        f.write("istituto;nome;citta\n")
        for m in missing:
            f.write(m + "\n")

if __name__ == "__main__":
    main()
