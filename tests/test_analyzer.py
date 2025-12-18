from ptof_pipeline.analyzer import analyze_with_ollama, extract_text_from_pdf
from io import BytesIO
from pypdf import PdfWriter

def create_dummy_pdf():
    # Create a simple PDF via pypdf
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Adding text is hard with pypdf writers, it's mostly for manipulation.
    # We'll just mock the text extraction or assume we have text.
    return b"%PDF-1.4..."

def test_ollama():
    print("Testing Ollama connection...")
    
    # Mock text similar to a PTOF
    mock_text = """
    PIANO TRIENNALE DELL'OFFERTA FORMATIVA
    ISTITUTO COMPRENSIVO G. NICOLINI
    
    ORIENTAMENTO
    La scuola organizza attività di continuità con la scuola primaria e l'infanzia.
    Per l'orientamento in uscita verso le scuole superiori, vengono organizzati incontri con i docenti delle scuole secondarie di II grado.
    Inoltre, si effettuano stage presso aziende locali e open day.
    Progetto "Orientiamoci al futuro".
    """
    
    print("Sending text to Ollama...")
    result = analyze_with_ollama(mock_text, "IC G. NICOLINI")
    print("\n--- Result ---")
    print(result)
    print("--------------")

if __name__ == "__main__":
    test_ollama()
