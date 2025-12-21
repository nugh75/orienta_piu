
import pandas as pd
import json
import os

SUMMARY_FILE = 'data/analysis_summary.csv'
REGION_MAP_FILE = 'config/region_map.json'

def test_loading():
    print("Testing data loading and region mapping...")
    
    if not os.path.exists(SUMMARY_FILE):
        print(f"Error: {SUMMARY_FILE} not found")
        return

    df = pd.read_csv(SUMMARY_FILE)
    print(f"Loaded {len(df)} rows from CSV.")
    
    if os.path.exists(REGION_MAP_FILE) and 'comune' in df.columns:
        try:
            with open(REGION_MAP_FILE, 'r') as f:
                r_map = json.load(f)
            mapping = r_map.get('comuni', {})
            
            # Map values
            df['regione'] = df['comune'].astype(str).str.upper().map(mapping)
            df['regione'] = df['regione'].fillna('DA VERIFICARE')
            
            print("\nSample mapping results (Comune -> Regione):")
            print(df[['comune', 'regione']].head(10).to_string(index=False))
            
            mapped_count = df[df['regione'] != 'DA VERIFICARE'].shape[0]
            print(f"\nSuccessfully mapped regions: {mapped_count}/{len(df)}")
            
        except Exception as e:
            print(f"Error mapping regions: {e}")
    else:
        print("Region map file missing or 'comune' column missing.")

if __name__ == "__main__":
    test_loading()
