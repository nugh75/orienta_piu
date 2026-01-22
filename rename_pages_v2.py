import os
import shutil

# Current File -> New File
# Ensure strict mapping based on step 96 output
moves = {
    # Progetto (Home stays Home.py)
    # 01 Campionamento
    "app/pages/01_📊_Campionamento.py": "app/pages/01_Campionamento.py",
    # 02 Documentazione
    "app/pages/02_ℹ️_Documentazione.py": "app/pages/02_Documentazione.py",
    
    # 03 Sintesi (ex Dashboard)
    "app/pages/03_📈_Dashboard_Sintesi.py": "app/pages/03_Sintesi.py",
    
    # 04 Territorio (ex 06)
    "app/pages/06_🗺️_Analisi_Territoriale.py": "app/pages/04_Territorio.py",
    
    # 05 Dimensioni (ex 10)
    "app/pages/10_📊_Analisi_Dimensioni.py": "app/pages/05_Dimensioni.py",
    
    # 06 Analytics (ex 07)
    "app/pages/07_📈_Analytics_Avanzati.py": "app/pages/06_Analytics.py",
    
    # 07 Scuola (ex 04)
    "app/pages/04_🏫_Dettaglio_Scuola.py": "app/pages/07_Scuola.py",
    
    # 08 Confronto (ex 05)
    "app/pages/05_🔀_Confronto_PTOF.py": "app/pages/08_Confronto.py",
    
    # 09 Attivita (ex 19)
    "app/pages/19_🌟_Attivita.py": "app/pages/09_Attivita.py",
    
    # 10 Ricerca (ex 08)
    "app/pages/08_🔍_Ricerca_Metodologie.py": "app/pages/10_Ricerca.py",
    
    # 11 Impatto (ex 09)
    "app/pages/09_📊_Impatto_Metodologie.py": "app/pages/11_Impatto.py",
    
    # 12 Meta (ex 20)
    "app/pages/20_📄_Meta_Report.py": "app/pages/12_Meta.py",
    
    # 13 Orientamento (ex 12 Scegli)
    "app/pages/12_🎓_Scegli_la_Tua_Scuola.py": "app/pages/13_Orientamento.py",
    
    # 14 Invio (ex 14)
    "app/pages/14_📤_Invia_PTOF.py": "app/pages/14_Invio.py",
    
    # 15 Verifica (ex 15)
    "app/pages/15_🔎_Verifica_Invio.py": "app/pages/15_Verifica.py",
    
    # 16 Revisione (ex 17 Richiedi)
    "app/pages/17_📝_Richiedi_Revisione.py": "app/pages/16_Revisione.py",
    
    # 17 Amministrazione (ex 13)
    "app/pages/13_🛠️_Amministrazione.py": "app/pages/17_Amministrazione.py",
    
    # 18 Dati (ex 11 Gestione Dati)
    "app/pages/11_🗂️_Gestione_Dati.py": "app/pages/18_Dati.py",
    
    # 19 Invii (ex 16 Gestione Invii)
    "app/pages/16_📥_Gestione_Invii.py": "app/pages/19_Invii.py",
    
    # 20 Revisioni (ex 18 Gestione Revisioni)
    "app/pages/18_📋_Gestione_Revisioni.py": "app/pages/20_Revisioni.py",
    
    # 21 Pesi (ex 21)
    "app/pages/21_⚖️_Gestione_Pesi.py": "app/pages/21_Pesi.py"
}

def execute_moves():
    print("Starting renaming...")
    temp_moves = {}
    
    # verify source existence
    for old, new in moves.items():
        if not os.path.exists(old):
            print(f"ERROR: Source {old} not found. Skipping.")
            continue
            
    # 1. Rename to temp
    for old, new in moves.items():
        temp_name = old + ".moving"
        temp_moves[temp_name] = new
        print(f"TEMP: {old} -> {temp_name}")
        os.rename(old, temp_name)

    # 2. Rename to final
    for temp, final in temp_moves.items():
        print(f"FINAL: {temp} -> {final}")
        os.rename(temp, final)

if __name__ == "__main__":
    execute_moves()
