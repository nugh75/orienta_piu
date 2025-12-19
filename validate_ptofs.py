
import os
import glob
import pandas as pd
import requests
import json
import logging
import shutil
from pypdf import PdfReader, PdfWriter
import time

# --- Configuration ---
PTOF_DIR = 'ptof'
CHUNKS_DIR = 'ptof_chunks'
OUTPUT_FILE = 'data/validated_ptofs.csv'
OLLAMA_URL = 'http://192.168.129.14:11434/api/generate'
OLLAMA_MODEL = 'qwen3:latest' # Configurable model
LOG_FILE = 'validation.log'

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

DISCARD_DIR = 'ptof_discarded'

def setup_dirs():
    if not os.path.exists(CHUNKS_DIR):
        os.makedirs(CHUNKS_DIR)
    if not os.path.exists(DISCARD_DIR):
        os.makedirs(DISCARD_DIR)
    
    # Ensure parsed output dir exists (data/)
    if not os.path.exists('data'):
        os.makedirs('data')

def extract_first_pages(pdf_path, chunk_path, num_pages=2):
    """
    Extracts the first `num_pages` from `pdf_path` and saves to `chunk_path`.
    Returns the extracted text content.
    """
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        extracted_text = ""
        count = 0
        
        for i, page in enumerate(reader.pages):
            if i >= num_pages: 
                break
            writer.add_page(page)
            extracted_text += page.extract_text() + "\n"
            count += 1
            
        if count > 0:
            with open(chunk_path, "wb") as f:
                writer.write(f)
            return extracted_text
    except Exception as e:
        logging.error(f"Error processing PDF {pdf_path}: {e}")
        return None
    return None

def analyze_with_ollama(text):
    """
    Sends text to Ollama to validate PTOF and extract metadata.
    """
    prompt = f"""
    Analyze the following text from a school document.
    
    Task 1: Determine if this is a "Piano Triennale dell'Offerta Formativa" (PTOF) valid for the triennium 2022-2025.
    Task 2: Extract the following school details: 
    - istituto (School Code, usually formatted like AAAB12345C)
    - denominazione (School Name)
    - tipo_scuola (School Type e.g., Liceo, Istituto Comprensivo)
    - grado (Grade Level)
    - area (Geographic Area e.g., Nord, Centro, Sud - infer from city if possible or leave empty)
    - tipo_territorio (Territory Type e.g., Metropolitano - infer or leave empty)
    - website (School Website URL)

    Output strictly valid JSON with no markdown formatting.
    Format:
    {{
        "is_ptof_2022_2025": true/false,
        "istituto": "...",
        "denominazione": "...",
        "tipo_scuola": "...",
        "grado": "...",
        "area": "...",
        "tipo_territorio": "...",
        "website": "..."
    }}

    Text content:
    {text[:4000]} 
    """ # Truncate text to avoid context limits if necessary, though first 2 pages should fit.

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return json.loads(data['response'])
        else:
            logging.error(f"Ollama API Error: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Ollama Connection Error: {e}")
    
    return None

def main():
    setup_dirs()
    
    pdf_files = glob.glob(os.path.join(PTOF_DIR, '*.pdf'))
    logging.info(f"Found {len(pdf_files)} PDFs to check.")
    
    results = []
    
    # Load existing results if any to avoid re-processing (optional, but good practice)
    processed_files = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            if 'original_file' in existing_df.columns:
                processed_files = set(existing_df['original_file'].tolist())
        except:
            pass # Ignore errors reading partial file

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        
        if filename in processed_files:
            continue

        logging.info(f"Processing: {filename}")
        
        chunk_filename = f"{filename}_chunk.pdf"
        chunk_path = os.path.join(CHUNKS_DIR, chunk_filename)
        
        # 1. Chunking
        text = extract_first_pages(pdf_path, chunk_path)
        
        if text and len(text.strip()) > 50: # Basic validity check
            # 2. Analysis
            data = analyze_with_ollama(text)
            
            if data:
                # Add file info
                data['original_file'] = filename
                
                # Check strict PTOF validity
                if data.get('is_ptof_2022_2025'):
                    logging.info(f"✅ Valid PTOF: {data.get('denominazione')}")
                    results.append(data)
                    
                    # Incremental save
                    df = pd.DataFrame(results)
                    df.to_csv(OUTPUT_FILE, index=False)
                else:
                    logging.warning(f"❌ Not a valid 2022-2025 PTOF: {filename}. Moving to {DISCARD_DIR}")
                    shutil.move(pdf_path, os.path.join(DISCARD_DIR, filename))
            else:
                 logging.warning(f"⚠️ Failed to analyze {filename}")
        else:
             logging.warning(f"⚠️ Could not extract text from {filename}")

        # 3. Cleanup
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
            
        # Optional: slight delay to not hammer the local LLM if it's CPU bound
        # time.sleep(0.5)

    logging.info(f"Validation complete. Valid PTOFs: {len(results)}")

if __name__ == "__main__":
    main()
