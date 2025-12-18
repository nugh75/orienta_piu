import os
import pandas as pd
import re
import shutil
from pypdf import PdfReader
import glob

# Constants
SOURCE_DIRS = ['ptof_downloads', 'scuola_in_chiaro']
OUTPUT_DIR = 'ptof'
REPORT_FILE = 'data/ptof_report.csv'
METADATA_FILES = glob.glob('data/paccmb_elenc*.csv') + ['data/campione_scuole.csv']

# Patterns
SCHOOL_CODE_PATTERN = re.compile(r'[A-Z0-9]{10}')

def load_metadata():
    metadata_list = []
    for f in METADATA_FILES:
        try:
            # Try to read with semicolon separator
            df = pd.read_csv(f, sep=';', on_bad_lines='skip')
            # Normalize column names to lowercase
            df.columns = [c.lower() for c in df.columns]
            # Ensure istituto is cleaned up immediately
            if 'istituto' in df.columns:
                df['istituto'] = df['istituto'].astype(str).str.strip().str.upper()
            metadata_list.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    if not metadata_list:
        return pd.DataFrame()
    
    full_metadata = pd.concat(metadata_list, ignore_index=True)
    
    # Merge records for the same school code, keeping the first non-NaN value for each column
    if 'istituto' in full_metadata.columns:
        # Filter out rows where istituto is empty/nan
        full_metadata = full_metadata[full_metadata['istituto'].notna() & (full_metadata['istituto'] != 'NAN')]
        full_metadata = full_metadata.groupby('istituto').first().reset_index()
        return full_metadata
    return pd.DataFrame()

def is_valid_ptof(file_path):
    """
    Checks if the PDF is valid and contains keywords typical of a PTOF.
    """
    file_name = os.path.basename(file_path).upper()
    # Trust filename if it contains explicit PTOF indications
    if "PTOF" in file_name or "PIANO_TRIENNALE" in file_name or "OFFERTA_FORMATIVA" in file_name:
         return True, "Valid PTOF (filename match)"

    try:
        reader = PdfReader(file_path)
        if len(reader.pages) == 0:
            return False, "Empty PDF"
        
        # Check first 30 pages for keywords
        text = ""
        for i in range(min(30, len(reader.pages))): 
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
        
        text = text.upper()
        
        # Keywords regex patterns for flexibility
        patterns = [
            r"P\s*\.?\s*T\s*\.?\s*O\s*\.?\s*F", # Matches PTOF, P.T.O.F., P T O F
            r"PIANO\s+TRIENNALE",
            r"OFFERTA\s+FORMATIVA",
            r"PIANO\s+DELL.?\s*OFFERTA\s+FORMATIVA", # Piano dell'Offerta Formativa
            r"RENDICONTAZIONE\s+SOCIALE",
            r"RAV",
            r"RAPPORTO\s+DI\s+AUTOVALUTAZIONE"
        ]
        
        for pat in patterns:
            if re.search(pat, text):
                return True, f"Valid PTOF (found pattern {pat})"
        
        # Heuristic: if text is very short but file is large, might be image-based.
        # But we can't reliably say yes.
        if len(text) < 100:
             return False, "Text not extracted (scanned PDF?)"
             
        return False, "Keywords not found"
    except Exception as e:
        return False, f"Invalid PDF: {e}"

def extract_school_code(file_name, metadata_codes):
    """
    Extract school code from filename, prioritizing codes that exist in metadata.
    """
    codes = SCHOOL_CODE_PATTERN.findall(file_name.upper())
    if not codes:
        return None
    
    # Check if any detected code is in metadata
    for c in codes:
        if c in metadata_codes:
            return c
            
    # If none in metadata, return the one that looks most like a code (e.g. has digits)
    # But usually the one at the end or separated by _ is better.
    # Let's try to find one that matches the Italian school code structure if possible,
    # or just the last one found.
    return codes[-1] 

def parse_stratum(stratum):
    if pd.isna(stratum) or not isinstance(stratum, str):
        return "Unknown", "Unknown"
    
    stratum = stratum.lower()
    
    # Area
    if 'nord' in stratum:
        area = 'Nord'
    elif 'sud' in stratum:
        area = 'Sud'
    elif 'centro' in stratum:
        area = 'Centro'
    else:
        area = 'Altro'
    
    # Territory
    if 'metro' in stratum:
        territorio = 'Metropolitano'
    elif 'altro' in stratum:
        territorio = 'Non Metropolitano'
    else:
        territorio = 'Altro'
        
    return area, territorio

def process():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    metadata = load_metadata()
    metadata_codes = set(metadata['istituto'].tolist()) if not metadata.empty and 'istituto' in metadata.columns else set()
    print(f"Loaded {len(metadata)} metadata entries.")
    
    report_data = []
    
    for source in SOURCE_DIRS:
        if not os.path.exists(source):
            continue
            
        files = glob.glob(os.path.join(source, "*.pdf"))
        print(f"Processing {len(files)} files in {source}...")
        
        for f in files:
            file_name = os.path.basename(f)
            school_code = extract_school_code(file_name, metadata_codes)
            
            is_ptof, reason = is_valid_ptof(f)
            
            # Get metadata
            school_info = {}
            if school_code and not metadata.empty and 'istituto' in metadata.columns:
                match = metadata[metadata['istituto'] == school_code]
                if not match.empty:
                    row = match.iloc[0]
                    school_info['istituto'] = school_code
                    school_info['denominazione'] = row.get('nome_istituto', row.get('denominazionescuola', 'Unknown'))
                    school_info['tipo_scuola'] = row.get('percorso2', 'Unknown')
                    school_info['grado'] = row.get('grado', 'Unknown')
                    
                    stratum = row.get('strato', '')
                    area, territorio = parse_stratum(stratum)
                    school_info['area'] = area
                    school_info['tipo_territorio'] = territorio
                else:
                    school_info = {'istituto': school_code, 'denominazione': 'Not Found', 'tipo_scuola': 'Unknown', 'grado': 'Unknown', 'area': 'Unknown', 'tipo_territorio': 'Unknown'}
            else:
                school_info = {'istituto': school_code or 'Unknown', 'denominazione': 'No Metadata', 'tipo_scuola': 'Unknown', 'grado': 'Unknown', 'area': 'Unknown', 'tipo_territorio': 'Unknown'}
            
            school_info['original_file'] = file_name
            
            if is_ptof:
                school_info['status'] = 'PTOF'
                # Copy file to organized dir
                target_path = os.path.join(OUTPUT_DIR, file_name)
                shutil.copy2(f, target_path)
                report_data.append(school_info)
                print(f"OK: {file_name} -> {school_code} ({reason})")
            else:
                school_info['status'] = f'Non-PTOF ({reason})'
                report_data.append(school_info)
                print(f"SKIP: {file_name} - {reason}")

    df_report = pd.DataFrame(report_data)
    df_report.to_csv(REPORT_FILE, index=False, sep=';')
    print(f"Report generated: {REPORT_FILE}")

    df_report = pd.DataFrame(report_data)
    df_report.to_csv(REPORT_FILE, index=False, sep=';')
    print(f"Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    process()
