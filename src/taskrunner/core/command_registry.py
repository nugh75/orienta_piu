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
    category: str = "Altro"             # es: "DOWNLOAD PTOF"
    description: str = ""               # descrizione dal help
    variables: List[str] = field(default_factory=list)  # es: ["MAX_DOWNLOADS", "G", "R"]
    defaults: Dict[str, str] = field(default_factory=dict)
    is_long_running: bool = False       # task che girano a lungo
    is_destructive: bool = False        # operazioni che modificano dati
    confirmation_required: bool = False


# Opzioni valide per le variabili (usate per dropdown nella UI)
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
    "MODEL": {
        "label": "Modello AI",
        "options": [
            "",
            "gemma3:27b", "qwen3:32b", "llama3.3:70b", "deepseek-r1:32b",
            "gemini-2.5-flash", "gemini-2.5-pro",
            "google/gemini-2.0-flash-lite-001", "google/gemini-2.0-flash-exp:free"
        ],
        "allow_custom": True,
    },
    "ANALYST": {
        "label": "Modello Analyst",
        "options": ["", "gemma3:27b", "qwen3:32b", "llama3.3:70b"],
        "allow_custom": True,
    },
    "REVIEWER": {
        "label": "Modello Reviewer",
        "options": ["", "gemma3:27b", "qwen3:32b", "llama3.3:70b"],
        "allow_custom": True,
    },
    "REFINER": {
        "label": "Modello Refiner",
        "options": ["", "gemma3:27b", "qwen3:32b", "llama3.3:70b"],
        "allow_custom": True,
    },
    "SYNTHESIZER": {
        "label": "Modello Synthesizer",
        "options": ["", "gemma3:27b", "qwen3:32b", "llama3.3:70b"],
        "allow_custom": True,
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
}


class CommandRegistry:
    """Registro dei comandi Make con parsing del Makefile."""

    # Comandi noti con metadati manuali
    COMMAND_METADATA = {
        # Download
        "strata-cycle": {
            "category": "DOWNLOAD PTOF",
            "description": "Ciclo incrementale stratificato (target MIUR proporzionale)",
            "variables": ["TARGET_TOTAL", "TARGET_STEP", "MAX_CYCLES", "MAX_DOWNLOADS", "G", "R", "GESTIONE"],
            "is_long_running": True,
        },
        "download-sample": {
            "category": "DOWNLOAD PTOF",
            "description": "Scarica campione stratificato (5 per strato)",
            "variables": [],
        },
        "download-strato": {
            "category": "DOWNLOAD PTOF",
            "description": "Scarica N scuole per ogni strato",
            "variables": ["N"],
        },
        "download-regione": {
            "category": "DOWNLOAD PTOF",
            "description": "Scarica scuole di una regione",
            "variables": ["R"],
        },
        "download-retry": {
            "category": "DOWNLOAD PTOF",
            "description": "Riprova download falliti",
            "variables": ["N", "MIN_ATTEMPTS", "MAX_ATTEMPTS"],
            "is_long_running": True,
        },
        "sync-sampling": {
            "category": "DATI",
            "description": "Sincronizza campionamento con download effettivi",
            "variables": [],
        },
        # Analisi
        "workflow": {
            "category": "ANALISI",
            "description": "Analisi PTOF pulita (una scuola alla volta)",
            "variables": ["MODEL", "ANALYST", "REVIEWER", "REFINER", "SYNTHESIZER", "PROVIDER", "OLLAMA_URL"],
            "is_long_running": True,
        },
        "run": {
            "category": "ANALISI",
            "description": "Esegue analisi PTOF",
            "variables": ["CONF"],
            "is_long_running": True,
        },
        "run-force": {
            "category": "ANALISI",
            "description": "Forza ri-analisi di tutti i file",
            "variables": [],
            "is_long_running": True,
        },
        "run-force-code": {
            "category": "ANALISI",
            "description": "Ri-analizza una scuola specifica",
            "variables": ["CODE"],
        },
        # Attivita
        "activity-extract": {
            "category": "ATTIVITA",
            "description": "Estrae attivita dai PDF PTOF",
            "variables": ["PROVIDER", "MODEL", "LIMIT", "MAX_COST"],
            "is_long_running": True,
        },
        # Review
        "review-report-openrouter": {
            "category": "REVISIONE",
            "description": "Revisione report con OpenRouter",
            "variables": ["MODEL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-report-gemini": {
            "category": "REVISIONE",
            "description": "Revisione report con Gemini",
            "variables": ["MODEL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-report-ollama": {
            "category": "REVISIONE",
            "description": "Revisione report con Ollama",
            "variables": ["MODEL", "OLLAMA_URL", "TARGET", "LIMIT"],
            "is_long_running": True,
        },
        "review-scores-openrouter": {
            "category": "REVISIONE",
            "description": "Revisione scores con OpenRouter",
            "variables": ["MODEL", "LOW", "HIGH", "TARGET"],
            "is_long_running": True,
        },
        "review-scores-ollama": {
            "category": "REVISIONE",
            "description": "Revisione scores con Ollama",
            "variables": ["MODEL", "OLLAMA_URL", "LOW", "HIGH", "TARGET"],
            "is_long_running": True,
        },
        # Dashboard e dati
        "dashboard": {
            "category": "DASHBOARD",
            "description": "Avvia la dashboard Streamlit",
            "variables": [],
            "is_long_running": True,
        },
        "csv": {
            "category": "DATI",
            "description": "Rigenera il CSV dai file JSON",
            "variables": [],
        },
        "csv-watch": {
            "category": "DATI",
            "description": "Rigenera CSV ogni N secondi",
            "variables": ["INTERVAL"],
            "is_long_running": True,
        },
        "backfill": {
            "category": "DATI",
            "description": "Backfill metadati mancanti con LLM",
            "variables": [],
            "is_long_running": True,
        },
        # Meta Report
        "meta-skeleton": {
            "category": "META REPORT",
            "description": "Report tematico skeleton-first",
            "variables": ["DIM", "REGIONE", "ORDINE", "PROVIDER_SCHOOL", "PROVIDER_SYNTHESIS"],
            "is_long_running": True,
        },
        "meta-school": {
            "category": "META REPORT",
            "description": "Genera report singola scuola",
            "variables": ["CODE", "PROVIDER"],
        },
        "meta-batch": {
            "category": "META REPORT",
            "description": "Genera N report pendenti",
            "variables": ["N", "PROVIDER"],
            "is_long_running": True,
        },
        # Manutenzione
        "registry-status": {
            "category": "MANUTENZIONE",
            "description": "Mostra stato del registro analisi",
            "variables": [],
        },
        "registry-clear": {
            "category": "MANUTENZIONE",
            "description": "Pulisce il registro (forza ri-analisi)",
            "variables": [],
            "is_destructive": True,
            "confirmation_required": True,
        },
        "cleanup": {
            "category": "MANUTENZIONE",
            "description": "Elimina file obsoleti",
            "variables": [],
            "is_destructive": True,
            "confirmation_required": True,
        },
        "cleanup-dry": {
            "category": "MANUTENZIONE",
            "description": "Mostra cosa verrebbe eliminato (dry-run)",
            "variables": [],
        },
        # Git
        "git-auto": {
            "category": "GIT",
            "description": "Add/commit/push ogni N secondi",
            "variables": ["INTERVAL"],
            "is_long_running": True,
        },
        "git-status": {
            "category": "GIT",
            "description": "Mostra stato git",
            "variables": [],
        },
        "git-commit": {
            "category": "GIT",
            "description": "Commit con messaggio",
            "variables": ["MSG"],
        },
    }

    # Ordine delle categorie per UI
    CATEGORY_ORDER = [
        "DOWNLOAD PTOF",
        "ANALISI",
        "ATTIVITA",
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
