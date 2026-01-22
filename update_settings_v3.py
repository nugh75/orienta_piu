
import json
from pathlib import Path

SETTINGS_PATH = Path("config/page_settings.json")

def update_settings():
    if not SETTINGS_PATH.exists():
        print("Settings file not found!")
        return

    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    
    # Remove old entries
    pages_to_remove = [
        "pages/10_Ricerca.py", 
        "pages/11_Impatto.py", 
        "pages/12_Meta.py"
    ]
    
    for p in pages_to_remove:
        if p in data["pages"]:
            del data["pages"][p]

    # Add new entries
    new_pages = {
        "pages/10_Report.py": {
            "label": "Report",
            "visible": True,
            "order": 10,
            "section": "esplorazione"
        },
        "pages/11_Metodologie.py": {
            "label": "Metodologie e Progetti",
            "visible": True,
            "order": 11,
            "section": "esplorazione"
        },
        "pages/12_Impatto.py": {
            "label": "Impatto Metodologie e Progetti",
            "visible": True,
            "order": 12,
            "section": "esplorazione"
        }
    }
    
    data["pages"].update(new_pages)
    
    # Write back
    SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Updated page_settings.json")

if __name__ == "__main__":
    update_settings()
