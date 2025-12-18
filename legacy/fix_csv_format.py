import pandas as pd
import re
import shutil

INPUT_FILE = "candidati_ptof.csv"
BACKUP_FILE = "candidati_ptof_backup.csv"

def is_school_code(s):
    # Basic check: 10 chars, starts with 2 letters, usually alphanumeric
    # e.g. BGIC87900D
    if not isinstance(s, str):
        return False
    s = s.strip()
    # Must have at least one digit to distinguish from 10-letter city names
    has_digit = any(c.isdigit() for c in s)
    return has_digit and bool(re.match(r'^[A-Z]{2}[A-Z0-9]{8}$', s))

def main():
    shutil.copy(INPUT_FILE, BACKUP_FILE)
    
    # Read as list of strings first to handle potentially different column counts cleanly
    with open(INPUT_FILE, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    header = lines[0].strip().split(';')
    # Expected: denominazionescuola;nome_comune;istituto;sito_web;ptof_link
    # Index:    0                    1            2         3         4
    
    fixed_lines = [lines[0]] # Keep header
    
    count_fixed = 0
    
    for line in lines[1:]:
        parts = line.strip().split(';')
        if len(parts) < 3:
            fixed_lines.append(line)
            continue
            
        col0 = parts[0] # Currently Denominazione
        col1 = parts[1] # Currently Comune
        col2 = parts[2] # Currently Istituto
        
        # Check if Col0 looks like a code AND Col2 does NOT
        if is_school_code(col0) and not is_school_code(col2):
            print(f"Fixing line: {line.strip()[:50]}...")
            new_parts = list(parts)
            new_parts[0] = parts[1] # Name
            new_parts[1] = parts[2] # City
            new_parts[2] = parts[0] # Code
            
            line_to_add = ";".join(new_parts) + "\n"
        else:
             if "CHIC80700E" in col0:
                 print(f"DEBUG: Found CHIC80700E in col0 but is_school_code(col0)={is_school_code(col0)} is_school_code(col2)={is_school_code(col2)} col2='{col2}'")
             line_to_add = line
            
        # Deduplication based on Code (index 2 usually)
        # We need to be careful. Let's just normalize first.
        fixed_lines.append(line_to_add)

    # DEDUPLICATION PHASE
    print("Normalizing done. Deduplicating...")
    unique_lines = []
    seen_codes = set()
    
    # Header
    unique_lines.append(fixed_lines[0])
    
    for line in fixed_lines[1:]:
        p = line.strip().split(';')
        if len(p) >= 3:
            # Assume Col 2 is code after fix
            code = p[2].strip()
            if is_school_code(code):
                if code in seen_codes:
                    continue # Skip duplicate
                seen_codes.add(code)
                unique_lines.append(line)
            else:
                # Maybe code is in col 0?
                if is_school_code(p[0].strip()):
                     c = p[0].strip()
                     if c in seen_codes: continue
                     seen_codes.add(c)
                     unique_lines.append(line)
                else:
                    # Keep lines we can't parse just in case
                    unique_lines.append(line)
        else:
             unique_lines.append(line)
    
    fixed_lines = unique_lines
    count_fixed = len(lines) - len(fixed_lines) # Rough metric of dupes removed
    print(f"Removed {count_fixed} duplicates/bad lines.")
            
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
        
    print(f"Fixed {count_fixed} lines.")

if __name__ == "__main__":
    main()
