import os
import re

# Mapping of Old String -> New String
replacements = {
    # setup_page calls
    'setup_page("Home.py")': 'setup_page("pages/03_📈_Dashboard_Sintesi.py")', # In the old Home file only? Careful.
    # Actually, the new Home.py uses setup_page("pages/01..."). I need to fix that too.
    
    # Let's be more specific with replacements or regex.
    
    # Page filenames in switch_page or string literals
    "Home.py": "pages/03_📈_Dashboard_Sintesi.py", # This is risky if it replaces the import or other things.
    # The new Home is just "Home.py".
    # The old Home references need to point to the new location.
    
    "pages/01_📘_Il_Progetto.py": "Home.py",
    "pages/22_📊_Campionamento.py": "pages/01_📊_Campionamento.py",
    "pages/12_ℹ️_Documentazione.py": "pages/02_ℹ️_Documentazione.py",
    "pages/02_🏫_Dettaglio_Scuola.py": "pages/04_🏫_Dettaglio_Scuola.py",
    "pages/03_🔀_Confronto_PTOF.py": "pages/05_🔀_Confronto_PTOF.py",
    "pages/04_🗺️_Analisi_Territoriale.py": "pages/06_🗺️_Analisi_Territoriale.py",
    "pages/06_📈_Analytics_Avanzati.py": "pages/07_📈_Analytics_Avanzati.py",
    "pages/07_🔍_Ricerca_Metodologie.py": "pages/08_🔍_Ricerca_Metodologie.py",
    "pages/08_📊_Impatto_Metodologie.py": "pages/09_📊_Impatto_Metodologie.py",
    "pages/09_📊_Analisi_Dimensioni.py": "pages/10_📊_Analisi_Dimensioni.py",
    "pages/10_🗂️_Gestione_Dati.py": "pages/11_🗂️_Gestione_Dati.py",
    "pages/11_🎓_Scegli_la_Tua_Scuola.py": "pages/12_🎓_Scegli_la_Tua_Scuola.py",
}

# Special handling for setup_page in specific files
# 1. In app/Home.py (New Home): should be setup_page("Home.py")
# 2. In app/pages/03... (Old Home): should be setup_page("pages/03_📈_Dashboard_Sintesi.py")

def update_files():
    base_dir = "app"
    
    # 1. Update the new Home.py specifically first
    with open("app/Home.py", "r") as f:
        content = f.read()
    # It currently has `setup_page("pages/01_📘_Il_Progetto.py")`. Change to "Home.py"
    content = content.replace('setup_page("pages/01_📘_Il_Progetto.py")', 'setup_page("Home.py")')
    with open("app/Home.py", "w") as f:
        f.write(content)
        
    # 2. Update the old Home (now 03_Dashboard)
    dashboard_path = "app/pages/03_📈_Dashboard_Sintesi.py"
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r") as f:
            content = f.read()
        # It has `setup_page("Home.py")`. Change to its own name.
        content = content.replace('setup_page("Home.py")', 'setup_page("pages/03_📈_Dashboard_Sintesi.py")')
        
        # It also has checks for default_page that might reference "Home.py".
        # `default_page = settings.get("default_page", "Home.py")` -> this is fine, Home is default.
        # `if default_page != "Home.py" ...` -> fine.
        
        with open(dashboard_path, "w") as f:
            f.write(content)

    # 3. Global replacement for switch_page references
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            
            with open(path, "r") as f:
                content = f.read()
                
            original_content = content
            
            for old, new in replacements.items():
                # Replace only string literals
                # Using simple replace is risky if strings overlap, but these are fairly unique paths.
                # However, "Home.py" is a substring of "app/Home.py".
                # We should replace longest matches first? 
                # Or just be careful.
                pass
            
            # Let's just do specific known `switch_page("...")` patterns
            # Or strings inside quotes.
            
            for old, new in replacements.items():
                content = content.replace(f'"{old}"', f'"{new}"')
                content = content.replace(f"'{old}'", f"'{new}'")
            
            if content != original_content:
                print(f"Updating {path}")
                with open(path, "w") as f:
                    f.write(content)

if __name__ == "__main__":
    update_files()
