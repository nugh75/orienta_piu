import os
import re

# New mapping based on executed moves
replacements = {
    # Old String -> New String
    "pages/01_📊_Campionamento.py": "pages/01_Campionamento.py",
    "pages/02_ℹ️_Documentazione.py": "pages/02_Documentazione.py",
    "pages/03_📈_Dashboard_Sintesi.py": "pages/03_Sintesi.py",
    "pages/06_🗺️_Analisi_Territoriale.py": "pages/04_Territorio.py",
    "pages/10_📊_Analisi_Dimensioni.py": "pages/05_Dimensioni.py",
    "pages/07_📈_Analytics_Avanzati.py": "pages/06_Analytics.py",
    "pages/04_🏫_Dettaglio_Scuola.py": "pages/07_Scuola.py",
    "pages/05_🔀_Confronto_PTOF.py": "pages/08_Confronto.py",
    "pages/19_🌟_Attivita.py": "pages/09_Attivita.py",
    "pages/08_🔍_Ricerca_Metodologie.py": "pages/10_Ricerca.py",
    "pages/09_📊_Impatto_Metodologie.py": "pages/11_Impatto.py",
    "pages/20_📄_Meta_Report.py": "pages/12_Meta.py",
    "pages/12_🎓_Scegli_la_Tua_Scuola.py": "pages/13_Orientamento.py",
    "pages/14_📤_Invia_PTOF.py": "pages/14_Invio.py",
    "pages/15_🔎_Verifica_Invio.py": "pages/15_Verifica.py",
    "pages/17_📝_Richiedi_Revisione.py": "pages/16_Revisione.py",
    "pages/13_🛠️_Amministrazione.py": "pages/17_Amministrazione.py",
    "pages/11_🗂️_Gestione_Dati.py": "pages/18_Dati.py",
    "pages/16_📥_Gestione_Invii.py": "pages/19_Invii.py",
    "pages/18_📋_Gestione_Revisioni.py": "pages/20_Revisioni.py",
    "pages/21_⚖️_Gestione_Pesi.py": "pages/21_Pesi.py",
}

def update_references():
    base_dir = "app"
    print("Updating file references...")
    
    # Iterate all files in app
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            
            with open(path, "r") as f:
                content = f.read()
                
            original_content = content
            
            for old, new in replacements.items():
                content = content.replace(f'"{old}"', f'"{new}"')
                content = content.replace(f"'{old}'", f"'{new}'")
            
            # Special check for setup_page in renamed files where the file path itself changed
            # E.g. in app/pages/03_Sintesi.py (was Dashboard)
            # The file name in setup_page("...") might still be the old one if it was hardcoded and not covered by replace above?
            # Replace above covers literal strings in the code, which SHOULD match setup_page("pages/03_...py").
            
            if content != original_content:
                print(f"Updating {path}")
                with open(path, "w") as f:
                    f.write(content)

if __name__ == "__main__":
    update_references()
