import json

settings = {
  "default_page": "Home.py",
  "sections": [
    {"id": "progetto", "label": "📘 PROGETTO"},
    {"id": "analisi", "label": "📊 ANALISI"},
    {"id": "esplorazione", "label": "🌟 ESPLORAZIONE"},
    {"id": "servizi", "label": "🎓 SERVIZI"},
    {"id": "admin", "label": "🛠️ ADMIN"}
  ],
  "pages": {
    "Home.py": {
      "label": "Progetto",
      "visible": True,
      "order": 0,
      "section": "progetto"
    },
    "pages/01_Campionamento.py": {
      "label": "Campionamento",
      "visible": True,
      "order": 1,
      "section": "progetto"
    },
    "pages/02_Documentazione.py": {
      "label": "Documentazione",
      "visible": True,
      "order": 2,
      "section": "progetto"
    },
    
    # SEZIONE ANALISI
    "pages/03_Sintesi.py": {
      "label": "Sintesi",
      "visible": True,
      "order": 3,
      "section": "analisi"
    },
    "pages/04_Territorio.py": {
      "label": "Territorio",
      "visible": True,
      "order": 4,
      "section": "analisi"
    },
    "pages/05_Dimensioni.py": {
      "label": "Dimensioni",
      "visible": True,
      "order": 5,
      "section": "analisi"
    },
    "pages/06_Analytics.py": {
      "label": "Analytics",
      "visible": True,
      "order": 6,
      "section": "analisi"
    },
    
    # SEZIONE ESPLORAZIONE
    "pages/07_Scuola.py": {
      "label": "Scuola",
      "visible": True,
      "order": 7,
      "section": "esplorazione"
    },
    "pages/08_Confronto.py": {
      "label": "Confronto",
      "visible": True,
      "order": 8,
      "section": "esplorazione"
    },
    "pages/09_Attivita.py": {
      "label": "Attività",
      "visible": True,
      "order": 9,
      "section": "esplorazione"
    },
    "pages/10_Ricerca.py": {
      "label": "Ricerca",
      "visible": True,
      "order": 10,
      "section": "esplorazione"
    },
    "pages/11_Impatto.py": {
      "label": "Impatto",
      "visible": True,
      "order": 11,
      "section": "esplorazione"
    },
    "pages/12_Meta.py": {
      "label": "Meta",
      "visible": True,
      "order": 12,
      "section": "esplorazione"
    },
    
    # SEZIONE SERVIZI
    "pages/13_Orientamento.py": {
      "label": "Orientamento",
      "visible": True,
      "order": 13,
      "section": "servizi"
    },
    "pages/14_Invio.py": {
      "label": "Invio",
      "visible": True,
      "order": 14,
      "section": "servizi"
    },
    "pages/15_Verifica.py": {
      "label": "Verifica",
      "visible": True,
      "order": 15,
      "section": "servizi"
    },
    "pages/16_Revisione.py": {
      "label": "Revisione",
      "visible": True,
      "order": 16,
      "section": "servizi"
    },
    
    # SEZIONE ADMIN (Visibili false di default)
    "pages/17_Amministrazione.py": {
      "label": "Amministrazione",
      "visible": False,
      "order": 17,
      "section": "admin"
    },
    "pages/18_Dati.py": {
      "label": "Dati",
      "visible": False,
      "order": 18,
      "section": "admin"
    },
    "pages/19_Invii.py": {
      "label": "Invii",
      "visible": False,
      "order": 19,
      "section": "admin"
    },
    "pages/20_Revisioni.py": {
      "label": "Revisioni",
      "visible": False,
      "order": 20,
      "section": "admin"
    },
    "pages/21_Pesi.py": {
      "label": "Pesi",
      "visible": False,
      "order": 21,
      "section": "admin"
    }
  }
}

import json
with open("config/page_settings.json", "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
