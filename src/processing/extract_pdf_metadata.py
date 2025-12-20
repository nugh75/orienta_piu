import fitz  # PyMuPDF
import re
import os

def extract_metadata_from_pdf(pdf_path):
    """
    Attempts to extract School Name and City from the first 2 pages of the PDF.
    """
    if not os.path.exists(pdf_path):
        return {}

    info = {}
    try:
        doc = fitz.open(pdf_path)
        text = ""
        # Read first 2 pages
        for i in range(min(2, len(doc))):
            text += doc[i].get_text()
        
        # Normalize
        text = text.replace('\n', ' ').strip()
        
        # 1. Extract Denominazione (Pattern: "ISTITUTO ...")
        # Look for typical headers
        # "Istituto Comprensivo ...", "Liceo Scientifico ...", "Direzione Didattica ..."
        name_match = re.search(r'(ISTITUTO COMPRENSIVO\s+[A-Z\s"]+|LICEO\s+[A-Z\s"]+|DIREZIONE DIDATTICA\s+[A-Z\s"]+|I\.I\.S\.\s+[A-Z\s"]+)', text, re.IGNORECASE)
        if name_match:
            # Clean up match
            raw_name = name_match.group(1).strip()
            # Stop at common delimiters like zip code, 'via', or too long
            if len(raw_name) > 60: raw_name = raw_name[:60]
            info['denominazione'] = raw_name.title()
            
        # 2. Extract City/Comune
        # Pattern: "Comune di [City]" or "Via ... [Zip] [City]"
        # Look for Zip Code (5 digits) followed by City
        zip_match = re.search(r'\b(\d{5})\s+([A-ZÀ-U\s]+)', text)
        if zip_match:
            city_candidate = zip_match.group(2).strip()
            # exclude generic words if matched accidentally
            if len(city_candidate) > 2 and city_candidate.upper() not in ['TEL', 'FAX', 'EMAIL']:
                 info['comune'] = city_candidate.title()
        
        return info

    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return {}
