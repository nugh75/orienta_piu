import os
import shutil

# Mapping of Old -> New
# Note: Using explicit mapping to avoid errors
moves = {
    # The big switches
    "app/Home.py": "app/pages/03_📈_Dashboard_Sintesi.py",
    "app/pages/01_📘_Il_Progetto.py": "app/Home.py",
    "app/pages/22_📊_Campionamento.py": "app/pages/01_📊_Campionamento.py",
    "app/pages/12_ℹ️_Documentazione.py": "app/pages/02_ℹ️_Documentazione.py",
    
    # Shifting the rest
    "app/pages/02_🏫_Dettaglio_Scuola.py": "app/pages/04_🏫_Dettaglio_Scuola.py",
    "app/pages/03_🔀_Confronto_PTOF.py": "app/pages/05_🔀_Confronto_PTOF.py",
    "app/pages/04_🗺️_Analisi_Territoriale.py": "app/pages/06_🗺️_Analisi_Territoriale.py",
    # 05 skipped/missing
    "app/pages/06_📈_Analytics_Avanzati.py": "app/pages/07_📈_Analytics_Avanzati.py",
    "app/pages/07_🔍_Ricerca_Metodologie.py": "app/pages/08_🔍_Ricerca_Metodologie.py",
    "app/pages/08_📊_Impatto_Metodologie.py": "app/pages/09_📊_Impatto_Metodologie.py",
    "app/pages/09_📊_Analisi_Dimensioni.py": "app/pages/10_📊_Analisi_Dimensioni.py",
    "app/pages/10_🗂️_Gestione_Dati.py": "app/pages/11_🗂️_Gestione_Dati.py",
    "app/pages/11_🎓_Scegli_la_Tua_Scuola.py": "app/pages/12_🎓_Scegli_la_Tua_Scuola.py",
    # 12 was Documentazione, moved to 02
    "app/pages/13_🛠️_Amministrazione.py": "app/pages/13_🛠️_Amministrazione.py", # Keep as is? No, better to keep contiguous if possible, but keeping 13 is fine as gap is filled by 11->12. 
    # Wait, 12 is taken by old 11. 
    # Old 12 moved to 02.
    # Old 11 moved to 12.
    # So 13 can stay 13? Yes.
    
    # Let's check the gap.
    # New sequence:
    # Home (Progetto)
    # 01 (Campionamento)
    # 02 (Documentazione)
    # 03 (Dashboard)
    # 04 (Dettaglio - was 02)
    # 05 (Confronto - was 03)
    # 06 (Territoriale - was 04)
    # 07 (Analytics - was 06)
    # 08 (Ricerca - was 07)
    # 09 (Impatto - was 08)
    # 10 (Dimensioni - was 09)
    # 11 (Gestione Dati - was 10)
    # 12 (Scegli Scuola - was 11)
    # 13 (Amministrazione - was 13) STAYS
    # ... rest stay same?
    # 14 -> 14
    # ...
    # 22 -> moved to 01.
}

# Add the rest that stay the same to ensure no conflicts or handle them implicitly (by not moving)
# But we need to check if 13+ need moving.
# Current 13 matches existing 13.
# Current 14 matches existing 14.
# ...
# Current 21 matches existing 21.

# So effectively only 02-11 need shifting up/down and 22, 12, Home, 01 need special moves.

def execute_moves():
    # Sort keys by length or reverse to handle potential conflicts? 
    # Safest is to move to temp names first, then to final.
    
    print("Starting renaming...")
    temp_moves = {}
    
    # 1. Rename all targets to temporary names to avoid collisions
    for old, new in moves.items():
        if os.path.exists(old):
            temp_name = old + ".temp_moving"
            temp_moves[temp_name] = new
            print(f"Moving {old} -> {temp_name}")
            os.rename(old, temp_name)
        else:
            print(f"WARNING: Source {old} not found!")

    # 2. Rename temp to final
    for temp, final in temp_moves.items():
        print(f"Moving {temp} -> {final}")
        os.rename(temp, final)

if __name__ == "__main__":
    execute_moves()
