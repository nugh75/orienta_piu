#!/usr/bin/env python3
"""
Convert all PTOF PDFs to Markdown for better usability and analysis.
"""
import os
import glob
import fitz  # PyMuPDF
import re

PDF_DIR = 'ptof'
MD_DIR = 'ptof_md'

def clean_text(text):
    # Basic cleaning
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def pdf_to_markdown(pdf_path, output_path):
    try:
        doc = fitz.open(pdf_path)
        md_content = f"# Contenuto PTOF: {os.path.basename(pdf_path)}\n\n"
        
        for i, page in enumerate(doc):
            text = page.get_text("text")
            # Heuristic formatting
            # Convert obvious headers (all caps lines, short lines) to MD headers
            lines = text.split('\n')
            formatted_lines = []
            for line in lines:
                clean = line.strip()
                if not clean: continue
                
                # Check for header-like properties
                if len(clean) < 80 and clean.isupper() and len(clean) > 3:
                     formatted_lines.append(f"\n## {clean.title()}\n")
                else:
                     formatted_lines.append(clean)
            
            page_content = "\n".join(formatted_lines)
            md_content += f"## Pagina {i+1}\n\n{page_content}\n\n---\n\n"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        return True
    except Exception as e:
        print(f"Error converting {pdf_path}: {e}")
        return False

def main():
    if not os.path.exists(MD_DIR):
        os.makedirs(MD_DIR)
        
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    total = len(pdf_files)
    print(f"Found {total} PDF files to convert.")
    
    count = 0
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path).replace('.pdf', '.md')
        output_path = os.path.join(MD_DIR, filename)
        
        # Skip if exists? User said "transform all", usually implies creating them. 
        # But we can skip if already done to save time on re-runs.
        # Let's overwrite for now to be sure we have the latest strategy.
        
        if pdf_to_markdown(pdf_path, output_path):
            count += 1
            if count % 10 == 0:
                print(f"Converted {count}/{total} files...")
                
    print(f"✅ Conversion complete. {count} files saved to {MD_DIR}/")

if __name__ == '__main__':
    main()
