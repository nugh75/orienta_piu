import requests
import json
import logging
from pypdf import PdfReader
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
OLLAMA_MODEL = "gpt-oss:20b"

def extract_text_from_pdf(pdf_source):
    """
    Extracts text from a PDF file.
    Args:
        pdf_source: Can be bytes or a file path (str).
    """
    try:
        if isinstance(pdf_source, str):
            # It's a file path
            with open(pdf_source, 'rb') as f:
                reader = PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        else:
            # It's bytes
            reader = PdfReader(BytesIO(pdf_source))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
            
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def analyze_with_ollama(text, school_name):
    """
    Sends the text to Ollama for analysis tailored to 'orientamento'.
    """
    # Truncate text if too long to avoid context limits or timeouts, 
    # though 20b model might handle large context. 
    # Let's take first 20k characters for now as PTOF can be huge.
    # Better strategy: search for "orientamento" keyword context?
    
    # Simple strategy: First 30k chars.
    truncated_text = text[:30000]
    
    prompt = f"""
    Sei un esperto di analisi di documenti scolastici. 
    Analizza il seguente testo estratto dal PTOF della scuola "{school_name}".
    
    Il tuo obiettivo è creare una scheda sintetica sulle attività di ORIENTAMENTO.
    
    Estrai e riassumi i seguenti punti:
    1. Attività di orientamento in entrata.
    2. Attività di orientamento in uscita.
    3. Eventuali progetti specifici o partnership con università/aziende.
    4. Riferimenti a percorsi PCTO (se presenti e rilevanti per l'orientamento).
    
    Se non trovi informazioni su questi punti, scrivi "Non specificato".
    
    TESTO PTOF:
    {truncated_text}
    
    RISPOSTA (Formato Markdown):
    """
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1, # Low temp for factual extraction
            "num_ctx": 4096 # Adjust if needed, default is usually 2048 or 4096
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300) # 5 min timeout for big model
        response.raise_for_status()
        result = response.json()
        return result.get("response", "Errore nella risposta del modello")
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        return f"Errore durante l'analisi LLM: {str(e)}"
