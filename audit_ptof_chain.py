
import os
import csv
import glob
from pathlib import Path
from collections import defaultdict

def main():
    print("--- PTOF Data Chain Audit ---")
    
    # Paths
    ptof_processed_dir = Path("ptof_processed")
    ptof_inbox_dir = Path("ptof_inbox") 
    ptof_discarded_dir = Path("ptof_discarded")
    md_dir = Path("ptof_md")
    attivita_path = Path("data/attivita.csv")
    
    # Data Structures
    chain = defaultdict(lambda: {"pdf": [], "md": None, "activities": 0})
    
    # 1. Scan PDFs (recursively in ptof_processed)
    print("Scanning PDFs...")
    pdf_count = 0
    
    # Scan processed
    for pdf in ptof_processed_dir.rglob("*.pdf"):
        # Expecting CODE_... format or just CODE...
        name = pdf.name
        # Extract code: usually first part before underscore or just the name
        # Strategy: Look for the code pattern in filename
        parts = name.split('_')
        if parts:
            code = parts[0].upper()
            if len(code) >= 10: # Basic validation
                chain[code]["pdf"].append(str(pdf))
                pdf_count += 1
                
    # Also check Inbox
    if ptof_inbox_dir.exists():
        for pdf in ptof_inbox_dir.glob("*.pdf"):
             parts = pdf.name.split('_')
             if parts:
                code = parts[0].upper()
                if len(code) >= 10:
                    chain[code]["pdf"].append(str(pdf))
                    pdf_count += 1

    # Also check Discarded
    if ptof_discarded_dir.exists():
        for pdf in ptof_discarded_dir.glob("*.pdf"):
             parts = pdf.name.split('_')
             if parts:
                code = parts[0].upper()
                if len(code) >= 10:
                    chain[code]["pdf"].append(str(pdf))
                    pdf_count += 1
    
    print(f" - Found {pdf_count} PDFs for {len(chain)} unique codes.")

    # 2. Scan MDs
    print("Scanning Markdown files...")
    md_count = 0
    for md in md_dir.glob("*_ptof.md"):
        code = md.name.split('_')[0].upper()
        if code in chain:
            chain[code]["md"] = str(md)
        else:
            # MD without PDF (orphaned MD? or PDF not in processed)
            chain[code]["md"] = str(md)
        md_count += 1
            
    print(f" - Found {md_count} Markdown files.")

    # 3. Scan Activities
    print("Scanning Activities...")
    act_count = 0
    if attivita_path.exists():
        with open(attivita_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('codice_meccanografico')
                if code:
                    code = code.upper()
                    chain[code]["activities"] += 1
                    act_count += 1
    print(f" - Found {act_count} activities.")

    # 4. Analyze Results
    print("\n--- Chain Consistency Report ---")
    
    missing_md = []
    missing_pdf = []
    missing_act = []
    complete_chain = []
    
    for code, data in chain.items():
        has_pdf = len(data["pdf"]) > 0
        has_md = data["md"] is not None
        has_act = data["activities"] > 0
        
        if has_pdf and has_md and has_act:
            complete_chain.append(code)
        
        if has_pdf and not has_md:
            missing_md.append(code)
            
        if has_md and not has_pdf:
            missing_pdf.append(code)
            
        if has_md and not has_act:
            missing_act.append(code)

    print(f"\n✅ Complete Chains (PDF + MD + Act): {len(complete_chain)}")
    
    print(f"\n⚠️  PDF exist but Missing Markdown: {len(missing_md)}")
    if len(missing_md) > 0:
        print(f"    Examples: {missing_md[:5]}")
        
    print(f"\n⚠️  Markdown exist but Missing PDF (in scanned dirs): {len(missing_pdf)}")
    if len(missing_pdf) > 0:
         print(f"    Examples: {missing_pdf[:5]}")
         
    print(f"\n⚠️  Markdown exist but No Activities extracted: {len(missing_act)}")
    if len(missing_act) > 0:
         print(f"    Examples: {missing_act[:5]}")

    # Save details
    with open("data/audit_missing_md.txt", "w") as f:
        f.write("\n".join(missing_md))
    with open("data/audit_no_activities.txt", "w") as f:
        f.write("\n".join(missing_act))
        
    print("\nDetailed lists saved to data/audit_*.txt")

if __name__ == "__main__":
    main()
