import pandas as pd
import subprocess
import os
import logging
import time
from pypdf import PdfReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

INPUT_FILE = "data/candidati_ptof.csv"
DOWNLOAD_DIR = "ptof_downloads"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def sanitize_filename(name):
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")

def validate_pdf(file_path):
    """
    Checks if the downloaded file is a valid PDF using pypdf.
    Returns True if valid, False otherwise.
    """
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    logger.warning(f"File {file_path} does not start with %PDF header.")
                    return False
            
            # Use pypdf to check structure (lightweight check)
            reader = PdfReader(file_path)
            # Try accessing a page to ensure it's readable
            if len(reader.pages) > 0:
                return True
    except Exception as e:
        logger.warning(f"PDF Validation failed for {file_path}: {e}")
    
    return False

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    if not os.path.exists(INPUT_FILE):
        logger.error(f"{INPUT_FILE} not found.")
        return

    # Try reading with different encodings
    try:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8')
    except:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='latin1')
    
    for index, row in df.iterrows():
        ptof_url = row.get('ptof_link', '')
        school_name = row.get('denominazionescuola', 'Unknown')
        school_id = row.get('istituto', 'Unknown')
        
        if pd.isna(ptof_url) or not str(ptof_url).startswith('http'):
            continue
            
        safe_name = sanitize_filename(school_name)
        # Handle potential float/nan school_id
        if pd.isna(school_id):
            school_id = "UNKNOWN_ID"
            
        file_name = f"{school_id}_{safe_name}.pdf"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # Check if already exists and is VALID
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            # We specifically want to re-validate current files if they might be bad
            # But for speed, let's assume if it's there it might have been checked?
            # No, user reported issues. Let's re-validate existing files too.
            if validate_pdf(file_path):
                logger.info(f"Skipping {school_name}, already downloaded and valid.")
                continue
            else:
                logger.warning(f"Unreadable file found for {school_name}. Re-downloading...")
                os.remove(file_path)
            
        logger.info(f"Downloading PTOF for {school_name} ({school_id})...")
        
        cmd = [
            "curl", "-L", "-k", 
            "-A", USER_AGENT,
            "-o", file_path, 
            "--max-time", "60", 
            str(ptof_url)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if validate_pdf(file_path):
                    logger.info(f"  -> Downloaded and Validated: {file_path}")
                else:
                    logger.error(f"  -> Downloaded invalid PDF: {file_path}. Removing.")
                    if os.path.exists(file_path):
                        os.remove(file_path)
            else:
                logger.error(f"  -> Failed to download: {result.stderr}")
        except Exception as e:
            logger.error(f"  -> Error executing curl: {e}")
            
if __name__ == "__main__":
    main()
