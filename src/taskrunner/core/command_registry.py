"""
Registry dei comandi Make disponibili.
Parsa il Makefile e crea un registro strutturato.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import re


@dataclass
class MakeCommand:
    """Rappresenta un comando Make disponibile."""
    name: str                           # es: "strata-cycle"
    display_name: str = ""              # nome leggibile es: "Ciclo Stratificato"
    category: str = "Altro"             # es: "DOWNLOAD PTOF"
    description: str = ""               # descrizione dal help
    variables: List[str] = field(default_factory=list)  # es: ["MAX_DOWNLOADS", "G", "R"]
    defaults: Dict[str, str] = field(default_factory=dict)
    is_long_running: bool = False       # task che girano a lungo
    is_destructive: bool = False        # operazioni che modificano dati
    confirmation_required: bool = False


# Opzioni valide per le variabili (usate per dropdown nella UI)
PROVIDER_MODELS = {
    "ollama": [
        "gemma3:27b", "qwen3:32b", "llama3.3:70b", "deepseek-r1:32b",
        "phi-4:14b", "mistral-small"
    ],
    "openrouter": [
        "google/gemini-2.0-flash-lite-001",
        "google/gemini-2.0-flash-001",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-r1:free"
    ],
    "gemini": [
        "gemini-2.5-flash", 
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ],
    "auto": [],  # Auto deciderà a runtime
    "": []
}

VARIABLE_OPTIONS = {
    "G": {
        "label": "Grado scolastico",
        "options": ["", "INFANZIA", "PRIMARIA", "SEC_PRIMO", "SEC_SECONDO", "ALTRO"],
        "allow_custom": False,
    },
    "R": {
        "label": "Regione",
        "options": [
            "", "ABRUZZO", "BASILICATA", "CALABRIA", "CAMPANIA",
            "EMILIA ROMAGNA", "FRIULI-VENEZIA G.", "LAZIO", "LIGURIA",
            "LOMBARDIA", "MARCHE", "MOLISE", "PIEMONTE", "PUGLIA",
            "SARDEGNA", "SICILIA", "TOSCANA", "TRENTINO-ALTO ADIGE",
            "UMBRIA", "VALLE D'AOSTA", "VENETO"
        ],
        "allow_custom": False,
    },
    "GESTIONE": {
        "label": "Tipo gestione",
        "options": ["", "Statale", "Paritaria"],
        "allow_custom": False,
    },
    "PROVIDER": {
        "label": "Provider AI",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_SCHOOL": {
        "label": "Provider per scuole",
        "options": ["", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_SYNTHESIS": {
        "label": "Provider per sintesi",
        "options": ["", "openrouter", "gemini", "ollama"],
        "allow_custom": False,
    },
    "PROVIDER_WORKFLOW": {
        "label": "Provider workflow",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_ANALYST": {
        "label": "Provider Analyst",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_REVIEWER": {
        "label": "Provider Reviewer",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_REFINER": {
        "label": "Provider Refiner",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "PROVIDER_SYNTHESIZER": {
        "label": "Provider Synthesizer",
        "options": ["", "auto", "ollama", "openrouter", "gemini"],
        "allow_custom": False,
    },
    "MODEL": {
        "label": "Modello AI",
        "options": [],  # Saranno riempiti dinamicamente se c'è provider
        "allow_custom": True,
        "depends_on": {
            "field": "PROVIDER",
            "options_map": PROVIDER_MODELS
        }
    },
    "ANALYST": {
        "label": "Modello Analyst",
        "options": [],
        "allow_custom": True,
        "depends_on": {
            "field": "PROVIDER_ANALYST",
            "options_map": PROVIDER_MODELS
        }
    },
    "REVIEWER": {
        "label": "Modello Reviewer",
        "options": [],
        "allow_custom": True,
        "depends_on": {
            "field": "PROVIDER_REVIEWER",
            "options_map": PROVIDER_MODELS
        }
    },
    "REFINER": {
        "label": "Modello Refiner",
        "options": [],
        "allow_custom": True,
        "depends_on": {
            "field": "PROVIDER_REFINER",
            "options_map": PROVIDER_MODELS
        }
    },
    "SYNTHESIZER": {
        "label": "Modello Synthesizer",
        "options": [],
        "allow_custom": True,
        "depends_on": {
            "field": "PROVIDER_SYNTHESIZER",
            "options_map": PROVIDER_MODELS
        }
    },
    "DIM": {
        "label": "Dimensione report",
        "options": [
            "", "orientamento", "inclusione", "competenze_digitali",
            "competenze_stem", "educazione_civica", "valutazione",
            "continuita", "alternanza", "innovazione_didattica"
        ],
        "allow_custom": True,
    },
    "ORDINE": {
        "label": "Ordine/Grado",
        "options": ["", "I Grado", "II Grado", "Infanzia", "Primaria"],
        "allow_custom": False,
    },
    "REGIONE": {
        "label": "Regione",
        "options": [
            "", "Abruzzo", "Basilicata", "Calabria", "Campania",
            "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria",
            "Lombardia", "Marche", "Molise", "Piemonte", "Puglia",
            "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige",
            "Umbria", "Valle d'Aosta", "Veneto"
        ],
        "allow_custom": False,
    },
    "N": {
        "label": "Numero",
        "options": ["", "5", "10", "20", "50", "100"],
        "allow_custom": True,
    },
    "MAX_DOWNLOADS": {
        "label": "Max downloads",
        "options": ["", "10", "25", "50", "100", "200"],
        "allow_custom": True,
    },
    "MAX_CYCLES": {
        "label": "Max cicli",
        "options": ["", "1", "2", "3", "5", "10"],
        "allow_custom": True,
    },
    "TARGET_TOTAL": {
        "label": "Target totale",
        "options": ["", "1000", "3000", "6000", "10000"],
        "allow_custom": True,
    },
    "TARGET_STEP": {
        "label": "Target per step",
        "options": ["", "100", "200", "300", "500"],
        "allow_custom": True,
    },
    "LIMIT": {
        "label": "Limite",
        "options": ["", "5", "10", "20", "50", "100"],
        "allow_custom": True,
    },
    "INTERVAL": {
        "label": "Intervallo (sec)",
        "options": ["", "60", "120", "300", "600", "900"],
        "allow_custom": True,
    },
    "LOW": {
        "label": "Soglia bassa",
        "options": ["", "1", "2", "3"],
        "allow_custom": True,
    },
    "HIGH": {
        "label": "Soglia alta",
        "options": ["", "5", "6", "7"],
        "allow_custom": True,
    },
    "OLLAMA_URL": {
        "label": "Ollama URL",
        "options": ["", "http://localhost:11434", "http://192.168.129.14:11434"],
        "allow_custom": True,
    },
    "MIN_ATTEMPTS": {
        "label": "Min tentativi",
        "options": ["", "1", "2", "3"],
        "allow_custom": True,
    },
    "MAX_ATTEMPTS": {
        "label": "Max tentativi",
        "options": ["", "3", "5", "10", "20"],
        "allow_custom": True,
    },
    "PRESET": {
        "label": "Preset Configurazione",
        "options": [],  # Saranno riempiti dinamicamente da API
        "allow_custom": False,
    },
}


class CommandRegistry:
    """Registro dei comandi Make con parsing del Makefile."""

    # Comandi noti con metadati manuali
    COMMAND_METADATA = {
        # Download
        "strata-cycle": {
            "display_name": "Scarica PTOF Stratificato",
            "category": "DOWNLOAD PTOF",
            "description": "Scarica PTOF da scuole usando campionamento stratificato proporzionale ai dati MIUR. Bilancia automaticamente per regione, grado e tipo gestione.",
            "variables": ["TARGET_TOTAL", "TARGET_STEP", "MAX_CYCLES", "MAX_DOWNLOADS", "G", "R", "GESTIONE", "PROVIDER_WORKFLOW", "MODEL_WORKFLOW", "PROVIDER_ANALYST", "ANALYST", "PROVIDER_REVIEWER", "REVIEWER", "PROVIDER_REFINER", "REFINER", "PROVIDER_SYNTHESIZER", "SYNTHESIZER"],
            "is_long_running": True,
        },
        "download-sample": {
            "display_name": "Scarica Campione Base",
            "category": "DOWNLOAD PTOF",
            "description": "Scarica un piccolo campione di 5 PTOF per ogni strato. Utile per test rapidi.",
            "variables": [],
        },
        "download-strato": {
            "display_name": "Scarica N per Strato",
            "category": "DOWNLOAD PTOF",
            "description": "Scarica un numero fisso di PTOF per ogni combinazione di strato (regione/grado/gestione).",
            "variables": ["N"],
        },
        "download-regione": {
            "display_name": "Scarica per Regione",
            "category": "DOWNLOAD PTOF",
            "description": "Scarica tutti i PTOF disponibili di una specifica regione italiana.",
            "variables": ["R"],
        },
        "download-retry": {
            "display_name": "Riprova Download Falliti",
            "category": "DOWNLOAD PTOF",
            "description": "Ritenta il download dei PTOF che hanno fallito in precedenza. Utile per recuperare errori di rete.",
            "variables": ["N", "MIN_ATTEMPTS", "MAX_ATTEMPTS"],
            "is_long_running": True,
        },
        "sync-sampling": {
            "display_name": "Sincronizza Campionamento",
            "category": "DATI",
            "description": "Allinea i dati di campionamento con i download effettivamente completati.",
            "variables": [],
        },
        # Analisi
        "workflow": {
            "display_name": "Analizza PTOF",
            "category": "ANALISI",
            "description": "Analisi completa dei PTOF con AI: estrae indicatori, genera report e punteggi. Elabora una scuola alla volta.",
            "variables": ["PRESET", "MODEL", "PROVIDER", "PROVIDER_ANALYST", "ANALYST", "PROVIDER_REVIEWER", "REVIEWER", "PROVIDER_REFINER", "REFINER", "PROVIDER_SYNTHESIZER", "SYNTHESIZER", "OLLAMA_URL"],
            "is_long_running": True,
        },
        "run": {
            "display_name": "Analisi Rapida",
            "category": "ANALISI",
            "description": "Avvia analisi PTOF in modalita' parallela (piu' veloce ma usa piu' risorse).",
            "variables": ["PRESET", "CONF"],
            "is_long_running": True,
        },
        "run-force": {
            "display_name": "Ri-Analizza Tutto",
            "category": "ANALISI",
            "description": "Forza la ri-analisi di tutti i PTOF, ignorando le analisi precedenti.",
            "variables": [],
            "is_long_running": True,
        },
        "run-force-code": {
            "display_name": "Ri-Analizza Scuola",
            "category": "ANALISI",
            "description": "Ri-analizza solo una specifica scuola identificata dal codice meccanografico.",
            "variables": ["CODE"],
        },
        # Attivita
        "activity-extract": {
            "display_name": "Estrai Attivita'",
            "category": "CATALOGO ATTIVITA'",
            "description": "Estrae le attivita' didattiche innovative dai PDF PTOF usando AI. Genera il catalogo delle buone pratiche.",
            "variables": ["PROVIDER", "MODEL", "LIMIT", "MAX_COST"],
            "is_long_running": True,
        },
        # Review
        "review-report-openrouter": {
            "display_name": "Migliora Report (OpenRouter)",
            "category": "REVISIONE",
            "description": "Arricchisce i report Markdown con analisi aggiuntive usando modelli OpenRouter (cloud).",
            "variables": ["MODEL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-report-gemini": {
            "display_name": "Migliora Report (Gemini)",
            "category": "REVISIONE",
            "description": "Arricchisce i report Markdown con analisi aggiuntive usando Google Gemini.",
            "variables": ["MODEL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-report-ollama": {
            "display_name": "Migliora Report (Ollama)",
            "category": "REVISIONE",
            "description": "Arricchisce i report Markdown con analisi aggiuntive usando Ollama (locale).",
            "variables": ["MODEL", "OLLAMA_URL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-scores-openrouter": {
            "display_name": "Rivedi Punteggi (OpenRouter)",
            "category": "REVISIONE",
            "description": "Revisiona i punteggi estremi (troppo alti o bassi) per verificarne l'accuratezza.",
            "variables": ["MODEL", "LOW", "HIGH", "TARGET"],
            "is_long_running": True,
        },
        "review-scores-ollama": {
            "display_name": "Rivedi Punteggi (Ollama)",
            "category": "REVISIONE",
            "description": "Revisiona i punteggi estremi usando Ollama locale.",
            "variables": ["MODEL", "OLLAMA_URL", "LOW", "HIGH", "TARGET"],
            "is_long_running": True,
        },
        # Dashboard e dati
        "dashboard": {
            "display_name": "Avvia Dashboard",
            "category": "DASHBOARD",
            "description": "Avvia la dashboard interattiva Streamlit per esplorare i dati e i report.",
            "variables": [],
            "is_long_running": True,
        },
        "csv": {
            "display_name": "Rigenera CSV",
            "category": "DATI",
            "description": "Ricostruisce il file CSV riepilogativo partendo dai JSON delle analisi.",
            "variables": [],
        },
        "csv-watch": {
            "display_name": "Aggiorna CSV Periodico",
            "category": "DATI",
            "description": "Rigenera automaticamente il CSV a intervalli regolari. Utile durante analisi lunghe.",
            "variables": ["INTERVAL"],
            "is_long_running": True,
        },
        "backfill": {
            "display_name": "Completa Metadati",
            "category": "DATI",
            "description": "Recupera metadati mancanti (nome scuola, indirizzo, etc.) usando AI.",
            "variables": [],
            "is_long_running": True,
        },
        # Meta Report
        "meta-skeleton": {
            "display_name": "Genera Report Tematico",
            "category": "META REPORT",
            "description": "Genera un report comparativo su un tema specifico (es. orientamento, inclusione) aggregando dati da piu' scuole.",
            "variables": ["DIM", "REGIONE", "ORDINE", "PROVIDER_SCHOOL", "PROVIDER_SYNTHESIS"],
            "is_long_running": True,
        },
        "meta-school": {
            "display_name": "Report Singola Scuola",
            "category": "META REPORT",
            "description": "Genera un report approfondito per una singola scuola.",
            "variables": ["CODE", "PROVIDER"],
        },
        "meta-batch": {
            "display_name": "Report Batch",
            "category": "META REPORT",
            "description": "Genera report per piu' scuole in sequenza.",
            "variables": ["N", "PROVIDER"],
            "is_long_running": True,
        },
        # Manutenzione
        "registry-status": {
            "display_name": "Stato Registro",
            "category": "MANUTENZIONE",
            "description": "Mostra statistiche sul registro delle analisi: quante completate, in attesa, fallite.",
            "variables": [],
        },
        "registry-clear": {
            "display_name": "Pulisci Registro",
            "category": "MANUTENZIONE",
            "description": "Svuota il registro analisi. ATTENZIONE: forzera' la ri-analisi di tutti i PTOF!",
            "variables": [],
            "is_destructive": True,
            "confirmation_required": True,
        },
        "cleanup": {
            "display_name": "Elimina File Obsoleti",
            "category": "MANUTENZIONE",
            "description": "Rimuove file temporanei, cache e backup vecchi per liberare spazio.",
            "variables": [],
            "is_destructive": True,
            "confirmation_required": True,
        },
        "cleanup-dry": {
            "display_name": "Anteprima Pulizia",
            "category": "MANUTENZIONE",
            "description": "Mostra quali file verrebbero eliminati senza cancellarli realmente.",
            "variables": [],
        },
        # Git
        "git-auto": {
            "display_name": "Commit Automatico",
            "category": "GIT",
            "description": "Esegue commit e push automatici a intervalli regolari. Utile per backup durante elaborazioni lunghe.",
            "variables": ["INTERVAL"],
            "is_long_running": True,
        },
        "git-status": {
            "display_name": "Stato Repository",
            "category": "GIT",
            "description": "Mostra lo stato corrente del repository Git (modifiche, branch, etc.).",
            "variables": [],
        },
        "git-commit": {
            "display_name": "Crea Commit",
            "category": "GIT",
            "description": "Crea un commit con tutte le modifiche correnti.",
            "variables": ["MSG"],
        },
    }

    # Ordine delle categorie per UI
    CATEGORY_ORDER = [
        "DOWNLOAD PTOF",
        "ANALISI",
        "CATALOGO ATTIVITA'",
        "REVISIONE",
        "DATI",
        "META REPORT",
        "DASHBOARD",
        "MANUTENZIONE",
        "GIT",
        "Altro",
    ]

    def __init__(self, makefile_path: Optional[Path] = None):
        self.makefile_path = makefile_path or Path(__file__).parents[3] / "Makefile"
        self.commands: Dict[str, MakeCommand] = {}
        self._load_commands()

    def _load_commands(self):
        """Carica comandi dal metadata e verifica esistenza nel Makefile."""
        # Carica tutti i comandi noti
        for name, meta in self.COMMAND_METADATA.items():
            cmd = MakeCommand(
                name=name,
                display_name=meta.get("display_name", name),
                category=meta.get("category", "Altro"),
                description=meta.get("description", ""),
                variables=meta.get("variables", []),
                defaults=meta.get("defaults", {}),
                is_long_running=meta.get("is_long_running", False),
                is_destructive=meta.get("is_destructive", False),
                confirmation_required=meta.get("confirmation_required", False),
            )
            self.commands[name] = cmd

    def get_command(self, name: str) -> Optional[MakeCommand]:
        """Ritorna un comando per nome."""
        return self.commands.get(name)

    def get_by_category(self, category: str) -> List[MakeCommand]:
        """Ritorna tutti i comandi di una categoria."""
        return [c for c in self.commands.values() if c.category == category]

    def get_categories(self) -> List[str]:
        """Ritorna le categorie ordinate."""
        categories = set(c.category for c in self.commands.values())
        # Ordina secondo CATEGORY_ORDER
        ordered = []
        for cat in self.CATEGORY_ORDER:
            if cat in categories:
                ordered.append(cat)
                categories.remove(cat)
        # Aggiungi eventuali categorie non in ordine
        ordered.extend(sorted(categories))
        return ordered

    def get_all_commands(self) -> List[MakeCommand]:
        """Ritorna tutti i comandi."""
        return list(self.commands.values())

    def get_long_running_commands(self) -> List[MakeCommand]:
        """Ritorna solo i comandi long-running."""
        return [c for c in self.commands.values() if c.is_long_running]
