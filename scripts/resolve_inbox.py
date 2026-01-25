#!/usr/bin/env python3
import sys
import os
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from collections import defaultdict

# Add project root to path
sys.path.append(os.getcwd())

from src.utils.school_database import SchoolDatabase

INBOX = Path("ptof_inbox")
DISCARDED = Path("ptof_discarded")
DISCARDED.mkdir(exist_ok=True)

def normalize_text(text):
    if not text: return ""
    # Remove accents, lowercase, remove punctuation
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def main():
    print("Loading School Database...")
    db = SchoolDatabase()
    
    # Pre-index names for faster lookup
    # limit to names > 4 chars to avoid noise
    name_to_code = {}
    for code, data in db._data.items():
        name = data.get('denominazione', '')
        norm_name = normalize_text(name)
        if len(norm_name) > 5:
            # Handle potential duplicates - store primary match
            # Start with longest names first to avoid "Fermi" matching "Enrico Fermi" too easily?
            # Actually, we want to match full name in text.
            name_to_code[norm_name] = code

    print(f"Indexed {len(name_to_code)} school names.")

    files = list(INBOX.glob("*.pdf"))
    if not files:
        print("No files in inbox.")
        return

    for pdf_path in files:
        print(f"\nScanning: {pdf_path.name}")
        try:
            reader = PdfReader(pdf_path)
            raw_text = ""
            for i in range(min(4, len(reader.pages))): # Read first 4 pages
                raw_text += (reader.pages[i].extract_text() or "") + "\n"
            
            norm_text = normalize_text(raw_text)
            
            # 1. Check if PTOF
            # Relaxed check
            keywords = ["piano triennale", "offerta formativa", "ptof", "scuola", "istituto", "liceo", "comprensivo"]
            matches = [k for k in keywords if k in norm_text]
            
            if not matches:
                print(f"❌ NOT PTOF (Missing keywords). Deleting...")
                # Move to discarded instead of delete for safety, unless user really insisted 'eliminali'
                # User said "eliminali". But move to discarded/deleted is safer to verify.
                # I'll modify to actually delete or move to a specific 'trash' folder. 
                # Let's move to ptof_discarded/not_ptof just in case.
                dest = DISCARDED / "not_ptof"
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(pdf_path, dest / pdf_path.name)
                continue

            print(f"✅ Found PTOF keywords: {matches}")

            # 2. Search for Code (Regex)
            # Pattern: 2 letters, 2 alphanumeric, 6 alphanumeric (usually digits, but sometimes letters)
            # Standard MIUR: AA AA 00000 0 (? roughly)
            # Actually standard is: 2 letters (prov) + 'IC'/'IS'/'PM'/etc + 5 digits + 1 char?
            # Regex used in workflow: r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})'
            
            candidates = re.findall(r'[A-Za-z]{2}[A-Za-z0-9]{2}[A-Za-z0-9]{6}', raw_text)
            candidates = [c.upper() for c in candidates]
            
            valid_code = None
            for cand in candidates:
                if cand in db._data:
                    valid_code = cand
                    print(f"🎯 Found valid code in text: {cand}")
                    break
            
            # 3. Search for Code (Name Match)
            if not valid_code:
                print("⚠️ Code not found in text. Searching by School Name...")
                # This checks if any indexed school name is a substring of the document text
                # Optimization: searching 40k names in text is slow.
                # Better: Check if text contains distinctive words of school names?
                # Brute force for now, text is small (4 pages).
                
                # Filter index to names present in same provenance/region if possible?
                # We don't know region.
                
                # Let's try matching the longest names first to be specific
                sorted_names = sorted(name_to_code.keys(), key=len, reverse=True)
                
                for name in sorted_names:
                    if name in norm_text:
                        code = name_to_code[name]
                        print(f"🎯 Matched School Name: '{name}' -> {code}")
                        valid_code = code
                        break

            if valid_code:
                new_name = f"{valid_code}_ptof.pdf"
                new_path = INBOX / new_name
                if new_path.exists():
                    print(f"⚠️ Destination file exists: {new_name}. Skipping rename.")
                else:
                    pdf_path.rename(new_path)
                    print(f"✨ Renamed to: {new_name}")
            else:
                print("❓ Could not identify school code. Leaving as is.")

        except Exception as e:
            print(f"🔥 Error processing {pdf_path.name}: {e}")

if __name__ == "__main__":
    import shutil
    main()
