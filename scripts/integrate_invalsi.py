
import pandas as pd
import glob
import os

# Configuration
INVALSI_DIR = 'data/liste invalsi'
SUMMARY_FILE = 'data/analysis_summary.csv'
OUTPUT_FILE = 'data/analysis_summary.csv' # Overwrite

def parse_strato(strato):
    """
    Parse the 'strato' field to extract area and type.
    Examples: 'nord_metro', 'nord_altro', 'licei_trad_nord_metro', 'IT_sud_altro'
    """
    if pd.isna(strato):
        return 'ND', 'ND'
    
    strato = str(strato).lower()
    
    # Area Geografica & Tipologia Territorio
    area = 'ND'
    if 'nord' in strato:
        area = 'Nord'
    elif 'sud' in strato:
        area = 'Sud'
    elif 'centro' in strato: # Assuming generic handling if it appears, though validation showed mainly nord/sud
        area = 'Centro'
        
    territorio = 'Altro'
    if 'metro' in strato:
        territorio = 'Metropolitano'
        
    # Tipo Scuola
    tipo = 'Altro'
    if 'licei' in strato:
        tipo = 'Liceo'
    elif 'it_' in strato or strato.startswith('it_') or 'tecnici' in strato: # IT_ prefix
        tipo = 'Tecnico'
    elif 'ip_' in strato or strato.startswith('ip_') or 'professionali' in strato: # IP_ prefix
        tipo = 'Professionale'
    elif 'ic' in strato or 'comprensivo' in strato: # Based on some potential data, though analysis showed mostly II grade codes
        tipo = 'Istituto Comprensivo'
    
    # Fallback/Infer from school code if needed (not implemented here, relying on INVALSI)
    
    return area, tipo, territorio

def main():
    print("🚀 Starting INVALSI Data Integration...")
    
    # 1. Load INVALSI Data
    csv_files = glob.glob(os.path.join(INVALSI_DIR, "*.csv"))
    if not csv_files:
        print("❌ No INVALSI CSV files found!")
        return
        
    dfs = []
    print(f"📂 Found {len(csv_files)} INVALSI files.")
    for f in csv_files:
        try:
            # Try reading with semicolon sep
            df = pd.read_csv(f, sep=';', on_bad_lines='skip', dtype=str)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Error reading {f}: {e}")
            
    if not dfs:
        print("❌ Could not read any INVALSI data.")
        return

    df_invalsi = pd.concat(dfs, ignore_index=True)
    
    # Normalize columns
    df_invalsi.columns = [c.strip().lower() for c in df_invalsi.columns]
    
    # Ensure distinct on 'istituto'
    if 'istituto' not in df_invalsi.columns:
        print("❌ 'istituto' column missing in INVALSI data.")
        return
        
    df_invalsi = df_invalsi.drop_duplicates(subset=['istituto'])
    print(f"✅ Loaded {len(df_invalsi)} unique INVALSI records.")
    
    # 2. Extract Fields
    print("⚙️ Processing strata...")
    extracted_data = df_invalsi['strato'].apply(parse_strato)
    
    df_invalsi['area_geografica'] = [x[0] for x in extracted_data]
    df_invalsi['tipo_scuola'] = [x[1] for x in extracted_data]
    df_invalsi['territorio'] = [x[2] for x in extracted_data]
    
    # Keep only relevant columns for merge
    cols_to_keep = ['istituto', 'area_geografica', 'tipo_scuola', 'territorio', 'nome_comune']
    # If nome_comune already in analysis, might not need it, but good to have.
    # Rename nome_comune to avoid conflict or use it to fill gaps?
    # Analysis summary already has 'comune'. Let's rename to 'comune_invalsi' just in case
    
    df_merge = df_invalsi[cols_to_keep].rename(columns={'istituto': 'school_id'})
    
    # 3. Load Analysis Summary
    if not os.path.exists(SUMMARY_FILE):
        print(f"❌ Summary file {SUMMARY_FILE} not found.")
        return
        
    df_summary = pd.read_csv(SUMMARY_FILE)
    print(f"📄 Loaded {len(df_summary)} rows from analysis summary.")
    
    # 4. Merge
    print("🔄 Merging data...")
    
    # Remove existing enriched columns if they exist (to re-enrich)
    for col in ['area_geografica', 'tipo_scuola', 'territorio']:
        if col in df_summary.columns:
            df_summary = df_summary.drop(columns=[col])
            
    # Left join to keep all analyzed schools
    df_enriched = pd.merge(df_summary, df_merge, on='school_id', how='left')
    
    # Fill NaN values for non-matching schools
    df_enriched['area_geografica'] = df_enriched['area_geografica'].fillna('ND')
    df_enriched['tipo_scuola'] = df_enriched['tipo_scuola'].fillna('ND')
    df_enriched['territorio'] = df_enriched['territorio'].fillna('ND')
    
    # Check coverage
    matched = df_enriched[df_enriched['area_geografica'] != 'ND']
    print(f"✅ Enriched {len(matched)} / {len(df_enriched)} schools with INVALSI data.")
    
    # 5. Save
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved enriched CSV to {OUTPUT_FILE}")
    
    # Update master metadata? Optional, but good practice. Not doing it now to keep it simple.

if __name__ == "__main__":
    main()
