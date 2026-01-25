import os
import re
from pathlib import Path
from pypdf import PdfReader

INBOX = Path("ptof_inbox")
files = list(INBOX.glob("*.pdf"))

print(f"Found {len(files)} files.")

for f in files:
    print(f"\n--- FILE: {f.name} ---")
    try:
        reader = PdfReader(f)
        text = ""
        for i in range(min(3, len(reader.pages))):
            text += reader.pages[i].extract_text() + "\n"
        
        # heuristic check
        is_ptof = "triennale" in text.lower() or "offerta formativa" in text.lower() or "ptof" in text.lower()
        print(f"Is PTOF candidate: {is_ptof}")
        
        # Code search
        # Standard: 2 char, 2 char/digit, 6 digits
        # Relaxed: Look for common patterns near "Codice"
        codes = re.findall(r'[A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6}', text.upper())
        print(f"REGEX codes found: {codes}")
        
        print("PREVIEW (First 500 chars):")
        print(text[:500])
        
    except Exception as e:
        print(f"ERROR reading {f.name}: {e}")
