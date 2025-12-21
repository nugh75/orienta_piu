
import sys
import os
import logging
sys.path.append(os.getcwd())

from src.processing.cloud_review import extract_metadata_from_header, load_api_config

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_extraction():
    # Load config
    config = load_api_config()
    api_key = config.get('gemini_api_key')
    if not api_key:
        print("Skipping test: No Gemini API key found.")
        return

    # Mock PTOF content (simulating a file with missing metadata in header)
    # Using a real school name but minimal text to trigger web search
    mock_ptof_content = """
    PTOF 2022-2025
    
    Il presente piano dell'offerta formativa è redatto ai sensi della legge 107/2015.
    
    Indice:
    1. Analisi del contesto
    2. Obiettivi
    
    ...testo generico...
    
    (Nessun nome scuola esplicito qui, se non forse nel filename che non passiamo qui)
    Ma proviamo con un nome parziale: "Liceo Scientifico Galileo Galilei" (ce ne sono tanti, vedremo se ne trova uno o chiede)
    Anzi, proviamo con un codice meccanografico noto ma senza nome: "Codice: NAIC80800G"
    """
    
    print("Testing extraction with minimal content (Triggering Web Search)...")
    result = extract_metadata_from_header(mock_ptof_content, 'gemini', api_key, 'gemini-2.0-flash-exp')
    
    print("\nResult:")
    import json
    print(json.dumps(result, indent=2))
    
    # Check if web search was likely used (school details filled)
    if result and result.get('denominazione') and result.get('denominazione') != "null":
        print("\nSUCCESS: Metadata extracted (likely via web search or inference).")
    else:
        print("\nWARNING: Metadata incomplete.")

if __name__ == "__main__":
    test_extraction()
