"""Thematic report generator (by dimension) - reads from attivita.csv/json."""

import csv
import hashlib
import json
import os
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


# Soglia minima casi per generare sezione tema dedicata (configurabile via env)
MIN_THEME_CASES = int(os.getenv("META_REPORT_MIN_THEME_CASES", "5"))

# Fase 1.2: Abilita/disabilita caching dei chunk (default: attivo)
ENABLE_CHUNK_CACHE = os.getenv("META_REPORT_CHUNK_CACHE", "1").strip().lower() in ("1", "true", "yes")

# Fase 3.1: Abilita chunking semantico (default: attivo)
ENABLE_SEMANTIC_CHUNKING = os.getenv("META_REPORT_SEMANTIC_CHUNKING", "1").strip().lower() in ("1", "true", "yes")

# Fase 3.1: Strategia di chunking semantico (region, tipo_scuola, mixed)
SEMANTIC_CHUNKING_STRATEGY = os.getenv("META_REPORT_CHUNKING_STRATEGY", "region")

# Fase 3.2: Abilita contesto cumulativo tra chunk (default: attivo)
ENABLE_CUMULATIVE_CONTEXT = os.getenv("META_REPORT_CUMULATIVE_CONTEXT", "1").strip().lower() in ("1", "true", "yes")

# Nota metodologica da inserire all'inizio di ogni report tematico
METHODOLOGY_SECTION = """
### Nota Metodologica

Il presente report offre un'analisi monografica delle attività di orientamento estratte dai PTOF (Piani Triennali dell'Offerta Formativa) degli istituti scolastici italiani, catalogate nel dataset `attivita.csv`. L'elaborazione si basa su un'analisi qualitativa automatizzata supportata da modelli linguistici avanzati (LLM), che hanno classificato ogni iniziativa secondo una tassonomia standardizzata in **sei categorie chiave**:

| Categoria | Descrizione e Obiettivi |
|-----------|-------------------------|
| 🎯 **Progetti e Attività Esemplari** | Iniziative di eccellenza, innovative e ad alto impatto, potenzialmente replicabili in altri contesti. |
| 📚 **Metodologie Didattiche Innovative** | Adozione di nuovi approcci pedagogici (es. debate, peer tutoring, gamification) per rendere l'orientamento attivo e coinvolgente. |
| 🤝 **Partnership e Collaborazioni** | Reti strategiche con Università, ITS, aziende ed enti territoriali per connettere scuola e mondo del lavoro. |
| ⚙️ **Azioni di Sistema** | Interventi strutturali di governance, coordinamento dei dipartimenti e formazione dedicata ai docenti referenti. |
| 🌈 **Inclusione e BES** | Strategie specifiche per garantire l'accessibilità dei percorsi orientativi a studenti con BES, DSA e disabilità. |
| 🗺️ **Esperienze Territoriali** | Progetti radicati nel tessuto socio-economico locale che valorizzano le specificità geografiche e culturali. |

L'obiettivo è restituire una narrazione coerente che non si limiti a un elenco di attività, ma evidenzi le **direttrici strategiche**, le **interconnessioni multidisciplinari** e le **specificità territoriali**, fornendo ai decisori una base informativa solida per la valutazione e la pianificazione di interventi futuri.

### Come leggere questo report

- **Panoramica temi**: Tabella riassuntiva con conteggi per tema
- **Analisi per tematiche**: Sintesi narrativa per ogni tema principale (≥5 casi)
- **Altri temi emergenti**: Temi minori elencati in forma compatta
- **Sintesi finale**: Raccomandazioni e trend principali

I dati sono analizzati per **distribuzione geografica** (regione e provincia) quando disponibili i filtri.
"""

# Importa temi canonici da config centrale
from src.config.themes import DIMENSIONS as _BASE_DIMENSIONS, normalize_theme, normalize_themes_string

# Dimension names mapping - estende config centrale con dimensioni legacy
DIMENSIONS = dict(_BASE_DIMENSIONS)
DIMENSIONS.update({
    # Dimensioni Strutturali (non nei temi canonici)
    "finalita": "Finalità Orientative",
    "obiettivi": "Obiettivi e Risultati Attesi",
    "governance": "Governance e Organizzazione",
    "didattica": "Didattica Orientativa",
    "partnership": "Partnership e Reti",

    # Dimensioni Opportunità (legacy)
    "stage": "Stage e Tirocini",
    "openday": "Open Day",
    "visite": "Visite Aziendali e Universitarie",
    "laboratori": "Laboratori Orientativi e Simulazioni",
    "testimonianze": "Testimonianze e Incontri con Esperti",
    "counseling": "Counseling e Percorsi Individualizzati",
    "alumni": "Rete Alumni e Mentoring",
})

# Mapping categorie -> dimension key (per dimensioni strutturali + opportunità)
CATEGORY_TO_DIM = {
    "Finalità Orientative": "finalita",
    "Obiettivi e Risultati Attesi": "obiettivi",
    "Governance e Organizzazione": "governance",
    "Didattica Orientativa": "didattica",
    "Partnership e Reti": "partnership",
    "Partnership e Collaborazioni Strategiche": "partnership",  # alias legacy
    "Esperienze Territoriali": "territorio",  # dimensione opportunità
}

# Keywords per cercare nelle attività correlate
ACTIVITY_KEYWORDS = {
    # Dimensioni Strutturali
    "finalita": ["finalità", "mission", "scopo orientativo", "obiettivo formativo", "vision"],
    "obiettivi": ["obiettivi", "risultati attesi", "traguardi", "competenze in uscita", "esiti"],
    "governance": ["governance", "organizzazione", "coordinamento", "referente", "commissione", "gruppo di lavoro"],
    "didattica": ["didattica orientativa", "orientamento didattico", "competenze orientative", "modulo orientativo", "UDA orientativ"],

    # Dimensioni Opportunità (Granulari)
    "pcto": ["pcto", "alternanza", "scuola-lavoro", "scuola lavoro"],
    "stage": ["stage", "tirocinio", "tirocini", "esperienza lavorativa"],
    "openday": ["open day", "orientamento in entrata", "accoglienza", "presentazione scuola"],
    "visite": ["visite guidate", "visite aziendali", "visita universit", "viaggi di istruzione", "uscite didattiche"],
    "laboratori": ["laboratori orientativi", "simulazione", "job shadowing", "role playing", "laboratorio pratico"],
    "testimonianze": ["testimonianze", "incontri con esperti", "professionisti", "imprenditori", "testimonial"],
    "counseling": ["counseling", "orientamento individuale", "colloquio orientativo", "percorso personalizzato", "bilancio competenze"],
    "alumni": ["ex alunni", "ex-alunni", "alumni", "diplomati", "mentoring", "rete diplomati"],

    # Dimensioni Tematiche
    "valutazione": ["valutazione", "autovalutazione", "invalsi", "verifiche", "monitoraggio apprendimenti", "rubriche valutative"],
    "formazione_docenti": ["formazione docenti", "aggiornamento professionale", "formazione insegnanti", "sviluppo professionale", "corso docenti"],
    "cittadinanza": ["cittadinanza", "legalità", "educazione civica", "costituzione", "diritti", "doveri", "democrazia"],
    "digitalizzazione": ["digitale", "digitalizzazione", "competenze digitali", "coding", "robotica", "informatica", "tecnologie"],
    "inclusione": ["inclusione", "bes", "bisogni educativi speciali", "disabilità", "dsa", "sostegno", "integrazione"],
    "continuita": ["continuità", "accoglienza", "passaggio", "raccordo", "verticale", "orizzontale", "inserimento"],
    "famiglie": ["famiglie", "genitori", "rapporti scuola-famiglia", "coinvolgimento genitori", "patto educativo"],
    "lettura": ["lettura", "scrittura", "biblioteca", "letteratura", "comprensione testo", "produzione scritta"],
    "orientamento": ["orientamento", "scelta scolastica", "percorso formativo", "consapevolezza", "progetto di vita"],
    "arte": ["arte", "creatività", "musica", "teatro", "espressione artistica", "educazione estetica"],
    "lingue": ["lingue straniere", "inglese", "francese", "spagnolo", "tedesco", "certificazioni linguistiche", "clil"],
    "stem": ["stem", "steam", "scienze", "ricerca", "sperimentazione", "metodo scientifico", "laboratorio scientifico"],
    "matematica": ["matematica", "logica", "problem solving", "calcolo", "geometria", "algebra", "giochi matematici"],
    "disagio": ["disagio", "prevenzione", "bullismo", "cyberbullismo", "dispersione", "abbandono scolastico", "sportello ascolto"],
    "intercultura": ["intercultura", "multiculturalità", "integrazione stranieri", "mediazione culturale", "alfabetizzazione"],
    "sostenibilita": ["sostenibilità", "ambiente", "ecologia", "educazione ambientale", "sviluppo sostenibile", "agenda 2030"],
    "sport": ["sport", "benessere", "educazione fisica", "motoria", "salute", "alimentazione", "stili di vita"],
    "imprenditorialita": ["imprenditorialità", "impresa", "autoimprenditorialità", "start up", "business", "economia"],
    "sistema": ["azioni di sistema", "governance", "organigramma", "funzioni strumentali", "coordinamento", "piano triennale"],
}

# Mapping per raggruppare temi affini (normalizzazione)
THEME_ALIASES = {
    # Salute e benessere
    "salute": "Salute e Benessere",
    "benessere": "Salute e Benessere",
    "salute e benessere": "Salute e Benessere",
    "sport e benessere": "Sport e Benessere",
    # STEM
    "stem": "STEM e Ricerca",
    "steam": "STEM e Ricerca",
    "stem/steam": "STEM e Ricerca",
    "stem e ricerca": "STEM e Ricerca",
    "scienze e ricerca": "STEM e Ricerca",
    # Digitalizzazione
    "digitale": "Digitalizzazione",
    "digitalizzazione": "Digitalizzazione",
    "competenze digitali": "Digitalizzazione",
    # Inclusione
    "inclusione": "Inclusione e BES",
    "bes": "Inclusione e BES",
    "inclusione e bes": "Inclusione e BES",
    "buone pratiche per l'inclusione": "Inclusione e BES",
    # Cittadinanza
    "cittadinanza": "Cittadinanza e Legalità",
    "legalità": "Cittadinanza e Legalità",
    "cittadinanza e legalità": "Cittadinanza e Legalità",
    "educazione civica": "Cittadinanza e Legalità",
    # Lingue
    "lingue": "Lingue Straniere",
    "lingue straniere": "Lingue Straniere",
    "intercultura": "Intercultura e Lingue",
    # Arte
    "arte": "Arte e Creatività",
    "creatività": "Arte e Creatività",
    "arte e creatività": "Arte e Creatività",
    "musica": "Arte e Creatività",
    "teatro": "Arte e Creatività",
    "musica e teatro": "Arte e Creatività",
}

# Blocklist for generic governance activities that should be excluded from thematic analysis
# These activities appear in all categories because they are too vague/structural
GENERIC_ACTIVITY_BLOCKLIST = [
    "piano triennale dell'offerta formativa",
    "ptof",
    "piano di miglioramento",
    "pdm",
    "piano di formazione del personale docente",
    "analisi del contesto e dei bisogni del territorio",
    "rav",
    "rapporto di autovalutazione",
    "rendicontazione sociale",
    "bilancio sociale",
    "organigramma",
    "funzionigramma",
]

# Keywords for assigning activities to their PRIMARY category (priority order matters)
CATEGORY_ASSIGNMENT_KEYWORDS = {
    "Progetti e Attività Esemplari": [
        "eccellenza", "innovazione", "best practice", "replicabile", "modello",
        "progetto pilota", "sperimentazione", "premio", "riconoscimento",
        "global teaching", "interscambio", "erasmus", "start up", "startup"
    ],
    "Metodologie Didattiche Innovative": [
        "clil", "flipped", "cooperative learning", "peer tutoring", "peer education",
        "didattica laboratoriale", "project work", "learning by doing", "debate",
        "gamification", "coding", "stem", "steam", "montessori", "dada"
    ],
    "Partnership e Collaborazioni": [
        "convenzione", "protocollo d'intesa", "accordo di rete", "partnership",
        "collaborazione con", "università", "ateneo", "its", "azienda", "impresa",
        "ente locale", "museo", "associazione", "fondazione"
    ],
    "Azioni di Sistema": [
        "funzione strumentale", "coordinamento", "commissione", "gruppo di lavoro",
        "governance", "staff", "dipartimento", "referente", "tutor",
        "monitoraggio", "valutazione interna"
    ],
    "Inclusione e BES": [
        "bes", "dsa", "disabilità", "inclusione", "pei", "pdp", "sostegno",
        "bisogni educativi speciali", "alunni stranieri", "alfabetizzazione",
        "recupero", "sportello", "ascolto", "disagio", "dispersione"
    ],
    "Esperienze Territoriali": [
        "territorio", "locale", "provinciale", "regionale", "comunità",
        "museo", "biblioteca", "orto", "ambiente", "sostenibilità",
        "legalità", "mafia", "cittadinanza attiva"
    ],
}


class ThematicReporter(BaseReporter):
    """Generate thematic report for a specific dimension from attivita.csv/json."""

    report_type = "thematic"

    def __init__(self, provider, base_dir: Optional[Path] = None):
        super().__init__(provider, base_dir)
        self.activities_meta_file = self.base_dir / "data" / "attivita.json"
        self.activities_csv_file = self.base_dir / "data" / "attivita.csv"
        # Cache for category assignments
        self._activity_categories = {}

    def _filter_generic_activities(self, practices: list[dict]) -> list[dict]:
        """Filter out generic governance activities that shouldn't appear in thematic analysis."""
        filtered = []
        removed_count = 0
        for p in practices:
            title = (p.get("titolo") or p.get("title") or "").lower()
            # Check if title matches any blocklist term
            is_generic = any(term in title for term in GENERIC_ACTIVITY_BLOCKLIST)
            if not is_generic:
                filtered.append(p)
            else:
                removed_count += 1
        if removed_count > 0:
            print(f"[thematic] Filtered out {removed_count} generic governance activities")
        return filtered

    def _assign_primary_category(self, practice: dict) -> tuple[str, list[str]]:
        """
        Assign a PRIMARY category to an activity.
        Uses the 'categoria' field from CSV if available, otherwise falls back to keyword matching.
        Returns (primary_category, secondary_categories).
        """
        # First, check if category is already defined in CSV
        csv_category = practice.get("pratica", {}).get("categoria", "")
        
        # Valid categories
        valid_categories = [
            "Progetti e Attività Esemplari",
            "Metodologie Didattiche Innovative",
            "Partnership e Collaborazioni",
            "Azioni di Sistema",
            "Inclusione e BES",
            "Esperienze Territoriali"
        ]
        
        # Normalize and match CSV category
        if csv_category:
            csv_category_lower = csv_category.lower().strip()
            for valid_cat in valid_categories:
                if valid_cat.lower() in csv_category_lower or csv_category_lower in valid_cat.lower():
                    # Found a match - use CSV category as primary
                    # For now, no secondary categories from CSV
                    return (valid_cat, [])
        
        # Fallback to keyword matching if no CSV category
        title = (practice.get("pratica", {}).get("titolo") or practice.get("titolo") or practice.get("title") or "").lower()
        description = (practice.get("pratica", {}).get("descrizione") or practice.get("descrizione") or practice.get("description") or "").lower()
        text = f"{title} {description}"
        
        # Priority order for categories
        priority_order = [
            "Progetti e Attività Esemplari",
            "Metodologie Didattiche Innovative", 
            "Partnership e Collaborazioni",
            "Inclusione e BES",
            "Esperienze Territoriali",
            "Azioni di Sistema",  # Lowest priority - catch-all
        ]
        
        matched_categories = []
        for category in priority_order:
            keywords = CATEGORY_ASSIGNMENT_KEYWORDS.get(category, [])
            if any(kw in text for kw in keywords):
                matched_categories.append(category)
        
        if not matched_categories:
            # Default to "Azioni di Sistema" if no match
            return ("Azioni di Sistema", [])
        
        primary = matched_categories[0]
        secondary = matched_categories[1:] if len(matched_categories) > 1 else []
        return (primary, secondary)

    def _preprocess_activities(self, practices: list[dict]) -> dict:
        """
        Pre-process all activities: filter generics and assign primary categories.
        Returns dict mapping activity_id -> (practice, primary_category, secondary_categories)
        """
        # Step 1: Filter generic activities
        filtered = self._filter_generic_activities(practices)
        
        # Step 2: Assign primary category to each activity
        result = {}
        for p in filtered:
            activity_id = p.get("id") or f"{p.get('school', {}).get('codice_meccanografico', '')}_{p.get('titolo', '')[:30]}"
            primary, secondary = self._assign_primary_category(p)
            result[activity_id] = {
                "practice": p,
                "primary_category": primary,
                "secondary_categories": secondary
            }
            self._activity_categories[activity_id] = (primary, secondary)
        
        print(f"[thematic] Preprocessed {len(result)} activities with primary category assignments")
        return result

    def get_output_path(
        self,
        dimension: str,
        filters: Optional[dict] = None,
        prompt_profile: Optional[str] = None,
        **kwargs
    ) -> Path:
        """Get output path for thematic report."""
        suffix = self._build_report_suffix(filters or {}, prompt_profile)
        return self.reports_dir / "thematic" / f"{dimension}{suffix}_attivita.md"

    def load_best_practices(self) -> list[dict]:
        """Load practices from JSON (legacy) or CSV (current)."""
        if self.activities_meta_file.exists():
            try:
                data = json.loads(self.activities_meta_file.read_text(encoding="utf-8"))
                practices = data.get("practices", [])
                if isinstance(practices, list) and practices:
                    return practices
            except Exception as e:
                print(f"[thematic] Error loading attivita.json: {e}")

        if not self.activities_csv_file.exists():
            print(f"[thematic] File not found: {self.activities_csv_file}")
            return []

        def pipe_to_list(val: str) -> list[str]:
            if not val:
                return []
            return [v.strip() for v in str(val).split("|") if v.strip()]

        practices = []
        try:
            with self.activities_csv_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    maturity = row.get("maturity_index")
                    try:
                        maturity = float(maturity) if maturity else None
                    except (ValueError, TypeError):
                        maturity = None

                    ambiti = pipe_to_list(row.get("ambiti_attivita", ""))
                    practices.append({
                        "id": row.get("id", ""),
                        "school": {
                            "codice_meccanografico": row.get("codice_meccanografico", ""),
                            "nome": row.get("nome_scuola", ""),
                            "tipo_scuola": row.get("tipo_scuola", ""),
                            "ordine_grado": row.get("ordine_grado", ""),
                            "regione": row.get("regione", ""),
                            "provincia": row.get("provincia", ""),
                            "comune": row.get("comune", ""),
                            "area_geografica": row.get("area_geografica", ""),
                            "territorio": row.get("territorio", ""),
                            "statale_paritaria": row.get("statale_paritaria", ""),
                        },
                        "pratica": {
                            "categoria": row.get("categoria", ""),
                            "titolo": row.get("titolo", ""),
                            "descrizione": row.get("descrizione", ""),
                            "metodologia": row.get("metodologia", ""),
                            "tipologie_metodologia": pipe_to_list(row.get("tipologie_metodologia", "")),
                            "ambiti_attivita": ambiti,
                            "target": row.get("target", ""),
                            "citazione_ptof": row.get("citazione_ptof", ""),
                            "pagina_evidenza": row.get("pagina_evidenza", ""),
                        },
                        "contesto": {
                            "maturity_index": maturity,
                            "partnership_coinvolte": pipe_to_list(row.get("partnership_coinvolte", "")),
                            "attivita_correlate": ambiti,
                        },
                        "metadata": {
                            "extracted_at": row.get("extracted_at", ""),
                            "model_used": row.get("model_used", ""),
                            "source_file": row.get("source_file", ""),
                        },
                    })
        except Exception as e:
            print(f"[thematic] Error loading attivita.csv: {e}")
            return []

        return practices

    def _build_case_record(self, practice: dict) -> dict:
        """Build a lean case record for analysis prompts."""
        school = practice.get("school", {})
        pratica = practice.get("pratica", {})
        contesto = practice.get("contesto", {})

        return {
            "scuola": {
                "nome": school.get("nome", ""),
                "codice": school.get("codice_meccanografico", ""),
                "tipo_scuola": school.get("tipo_scuola", ""),
                "ordine_grado": school.get("ordine_grado", ""),
                "regione": school.get("regione", ""),
                "provincia": school.get("provincia", ""),
                "comune": school.get("comune", ""),
                "area_geografica": school.get("area_geografica", ""),
                "territorio": school.get("territorio", ""),
                "statale_paritaria": school.get("statale_paritaria", ""),
            },
            "pratica": {
                "categoria": pratica.get("categoria", ""),
                "titolo": pratica.get("titolo", ""),
                "descrizione": pratica.get("descrizione", ""),
                "metodologia": pratica.get("metodologia", ""),
                "tipologie_metodologia": pratica.get("tipologie_metodologia", []),
                "ambiti_attivita": pratica.get("ambiti_attivita", []),
                "target": pratica.get("target", ""),
                "citazione_ptof": pratica.get("citazione_ptof", ""),
                "pagina_evidenza": pratica.get("pagina_evidenza", ""),
            },
            "contesto": {
                "maturity_index": contesto.get("maturity_index"),
                "partnership_coinvolte": contesto.get("partnership_coinvolte", []),
                "attivita_correlate": contesto.get("attivita_correlate", []),
            },
        }

    def _format_case_label(self, case: dict, include_description: bool = True) -> str:
        """Build a compact label for inventory listings."""
        scuola = case.get("scuola", {})
        pratica = case.get("pratica", {})

        nome = scuola.get("nome") or "Scuola"
        codice = scuola.get("codice") or scuola.get("codice_meccanografico") or "ND"
        titolo = pratica.get("titolo") or "Attivita"
        descrizione = pratica.get("descrizione") or ""
        
        # Tronca descrizione a 150 caratteri
        if include_description and descrizione:
            descrizione_breve = descrizione[:150].strip()
            if len(descrizione) > 150:
                descrizione_breve += "..."
        else:
            descrizione_breve = ""
            
        meta_parts = [
            scuola.get("provincia"),
            scuola.get("regione"),
            scuola.get("ordine_grado"),
            scuola.get("tipo_scuola"),
            pratica.get("categoria"),
        ]
        meta = ", ".join([p for p in meta_parts if p])
        label = f"{nome} ({codice}) - {titolo}"
        if meta:
            label = f"{label} [{meta}]"
        if descrizione_breve:
            label = f"{label}: {descrizione_breve}"
        return label

    def _group_labels_by_region(self, cases: list[dict]) -> dict:
        """Group case labels by region (or province if single region)."""
        # First pass to detect unique regions
        regions = set()
        for case in cases:
            r = case.get("scuola", {}).get("regione")
            if r: regions.add(r)
        
        use_province = len(regions) == 1
        
        grouped = defaultdict(list)
        for case in cases:
            if use_province:
                key = case.get("scuola", {}).get("provincia") or "Provincia Non specificata"
            else:
                key = case.get("scuola", {}).get("regione") or "Regione Non specificata"
            
            grouped[key].append(self._format_case_label(case))
        return grouped

    def _group_labels_by_category(self, cases: list[dict]) -> dict:
        """Group case labels by category."""
        grouped = defaultdict(list)
        for case in cases:
            categoria = case.get("pratica", {}).get("categoria") or "Altre pratiche"
            grouped[categoria].append(self._format_case_label(case))
        return grouped

    def _case_key(self, case: dict) -> tuple[str, str]:
        scuola = case.get("scuola", {})
        pratica = case.get("pratica", {})
        return (
            scuola.get("codice") or scuola.get("codice_meccanografico") or "",
            pratica.get("titolo") or "",
        )

    def _normalize_theme(self, theme: str) -> str:
        """Normalize theme name using aliases."""
        if not theme:
            return "Altre attività"
        theme_lower = theme.strip().lower()
        return THEME_ALIASES.get(theme_lower, theme.strip())

    def _extract_themes(self, case: dict) -> list[str]:
        pratica = case.get("pratica", {})
        raw_themes = [t.strip() for t in pratica.get("ambiti_attivita", []) if t and t.strip()]
        if not raw_themes:
            categoria = pratica.get("categoria")
            if categoria:
                raw_themes = [categoria.strip()]
        if not raw_themes:
            return ["Altre attività"]
        # Normalizza e deduplica
        normalized = []
        seen = set()
        for t in raw_themes:
            norm = self._normalize_theme(t)
            if norm.lower() not in seen:
                seen.add(norm.lower())
                normalized.append(norm)
        return normalized or ["Altre attività"]

    def _group_cases_by_theme(self, cases: list[dict]) -> dict:
        grouped = defaultdict(list)
        seen = defaultdict(set)
        for case in cases:
            key = self._case_key(case)
            for theme in self._extract_themes(case):
                if key in seen[theme]:
                    continue
                seen[theme].add(key)
                grouped[theme].append(case)
        return grouped

    def _group_cases_by_region(self, cases: list[dict]) -> dict:
        grouped = defaultdict(list)
        for case in cases:
            region = case.get("scuola", {}).get("regione") or "Non specificata"
            grouped[region].append(case)
        return grouped

    def _chunk_cases(self, cases: list[dict], chunk_size: int) -> list[list[dict]]:
        """Split cases into chunks."""
        return [cases[i:i + chunk_size] for i in range(0, len(cases), chunk_size)]

    # =========================================================================
    # Fase 3.1: Chunking Semantico
    # =========================================================================

    def _semantic_chunk_cases(
        self,
        cases: list[dict],
        chunk_size: int = 30,
        strategy: str = "region"
    ) -> list[list[dict]]:
        """Chunking semantico che preserva cluster significativi.

        Fase 3.1: Invece di spezzare i casi numericamente, li raggruppa
        prima per regione (o altro criterio) per mantenere la coerenza
        territoriale nell'analisi.

        Args:
            cases: Lista di casi da raggruppare
            chunk_size: Dimensione massima di ogni chunk
            strategy: Strategia di raggruppamento ("region", "tipo_scuola", "mixed")

        Returns:
            Lista di chunk, ognuno contenente casi semanticamente correlati
        """
        if strategy == "region":
            # Raggruppa per regione
            by_region = defaultdict(list)
            for case in cases:
                region = case.get("scuola", {}).get("regione", "Altro") or "Altro"
                by_region[region].append(case)

            chunks = []
            current_chunk = []
            current_chunk_regions = []

            # Ordina le regioni per numero di casi (decrescente) per bilanciare
            sorted_regions = sorted(by_region.keys(), key=lambda r: len(by_region[r]), reverse=True)

            for region in sorted_regions:
                region_cases = by_region[region]

                # Se la regione intera sta nel chunk corrente, aggiungila
                if len(current_chunk) + len(region_cases) <= chunk_size:
                    current_chunk.extend(region_cases)
                    current_chunk_regions.append(region)
                else:
                    # Chiudi chunk corrente se non vuoto
                    if current_chunk:
                        chunks.append(current_chunk)

                    # Se la regione è troppo grande, spezzala
                    if len(region_cases) > chunk_size:
                        for i in range(0, len(region_cases), chunk_size):
                            chunks.append(region_cases[i:i + chunk_size])
                        current_chunk = []
                        current_chunk_regions = []
                    else:
                        current_chunk = region_cases
                        current_chunk_regions = [region]

            # Aggiungi l'ultimo chunk se non vuoto
            if current_chunk:
                chunks.append(current_chunk)

            return chunks

        elif strategy == "tipo_scuola":
            # Raggruppa per tipo scuola
            by_type = defaultdict(list)
            for case in cases:
                tipo = case.get("scuola", {}).get("tipo_scuola", "Altro") or "Altro"
                by_type[tipo].append(case)

            chunks = []
            for tipo in sorted(by_type.keys()):
                type_cases = by_type[tipo]
                # Spezza se necessario
                for i in range(0, len(type_cases), chunk_size):
                    chunks.append(type_cases[i:i + chunk_size])

            return chunks

        elif strategy == "mixed":
            # Strategia mista: prima per regione, poi bilancia
            by_region = defaultdict(list)
            for case in cases:
                region = case.get("scuola", {}).get("regione", "Altro") or "Altro"
                by_region[region].append(case)

            # Crea chunk bilanciati alternando regioni
            all_cases_sorted = []
            max_len = max(len(cases) for cases in by_region.values()) if by_region else 0

            for i in range(max_len):
                for region in sorted(by_region.keys()):
                    if i < len(by_region[region]):
                        all_cases_sorted.append(by_region[region][i])

            # Chunking standard sulla lista ordinata
            return self._chunk_cases(all_cases_sorted, chunk_size)

        # Fallback a chunking numerico
        return self._chunk_cases(cases, chunk_size)

    def _render_inventory(self, inventory_groups: dict) -> str:
        """Render full inventory in markdown."""
        if not inventory_groups:
            return ""

        lines = [
            "---",
            "## Inventario completo",
            "Elenco completo dei casi raggruppati per regione.",
        ]
        for region in sorted(inventory_groups.keys()):
            cases = sorted(inventory_groups[region])
            lines.append(f"### {region} ({len(cases)})")
            for item in cases:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _normalize_report_headings(self, content: str) -> str:
        """Normalize headings so only the intended hierarchy is preserved."""
        if not content:
            return ""
        allowed_h2 = {
            "Panoramica temi",
            "Analisi per tematiche",
            "Sintesi delle analisi tematiche",
            "Analisi per regione",
            "Altri temi emergenti",
        }
        lines = []
        seen_h1 = False
        prev_heading = None

        for line in content.splitlines():
            stripped = line.strip()

            # Rimuovi righe che sembrano titoli duplicati (testo in grassetto che ripete il tema)
            if stripped.startswith("**") and stripped.endswith("**"):
                # Potrebbe essere un titolo in grassetto generato dal modello
                inner = stripped[2:-2].strip()
                # Se il titolo precedente era simile, salta
                if prev_heading and inner.lower() in prev_heading.lower():
                    continue
                # Altrimenti converti in testo normale
                lines.append(inner)
                continue

            match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if not match:
                lines.append(line)
                continue

            level = len(match.group(1))
            text = match.group(2).strip()

            # Rimuovi prefissi come "Sintesi Analitica:" o "Sintesi narrativa:"
            text = re.sub(r"^(Sintesi\s+(Analitica|narrativa|Narrativa)\s*:\s*)", "", text).strip()

            # Salta heading vuoti
            if not text:
                continue

            # Evita duplicati consecutivi
            if prev_heading and text.lower() == prev_heading.lower():
                continue

            if level == 1:
                if not seen_h1:
                    seen_h1 = True
                    lines.append(f"# {text}")
                    prev_heading = text
                else:
                    # H1 duplicato: converti in paragrafo
                    lines.append(f"\n{text}\n")
                continue

            if level == 2:
                if text in allowed_h2:
                    lines.append(f"## {text}")
                    prev_heading = text
                else:
                    # H2 non consentito: converti in paragrafo o H3
                    lines.append(f"### {text}")
                    prev_heading = text
                continue

            # Keep theme headings, demote overly deep levels
            level = min(level, 4)
            lines.append(f"{'#' * level} {text}")
            prev_heading = text

        # Post-process: rimuovi linee vuote multiple consecutive
        result = "\n".join(lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _sample_case_labels(
        self,
        cases: list[dict],
        per_region: int = 5,
        max_total: int = 50
    ) -> list[str]:
        """Pick a sample of case labels using systematic sampling (1 in 5)."""
        if not cases:
            return []

        # Ordina per regione e codice scuola per garantire distribuzione uniforme
        sorted_cases = sorted(cases, key=lambda x: (
            x.get("scuola", {}).get("regione", ""),
            x.get("scuola", {}).get("codice", "")
        ))

        n = len(cases)
        if n < 10:
            # Se pochi casi, prendili tutti
            samples = sorted_cases
        else:
            # Campionamento sistematico 1 su 5 (20%)
            samples = sorted_cases[::5]

        return [self._format_case_label(c, include_description=True) for c in samples]

    # =========================================================================
    # Fase 3.3: Sampling Stratificato
    # =========================================================================

    def _stratified_sample(
        self,
        cases: list[dict],
        min_per_stratum: int = 2,
        max_total: int = 80,
        stratify_by: str = "regione"
    ) -> list[dict]:
        """Campionamento stratificato con minimo garantito per strato.

        Fase 3.3: Garantisce che ogni regione/strato sia rappresentata
        nel campione, evitando di perdere informazioni su territori
        con pochi casi.

        Args:
            cases: Lista completa di casi
            min_per_stratum: Numero minimo di casi per strato
            max_total: Numero massimo totale di casi nel campione
            stratify_by: Campo per la stratificazione ("regione", "tipo_scuola", "provincia")

        Returns:
            Lista di casi campionati con rappresentatività garantita
        """
        if not cases:
            return []

        if len(cases) <= max_total:
            return cases

        # Raggruppa per strato
        strata = defaultdict(list)
        for case in cases:
            if stratify_by == "regione":
                key = case.get("scuola", {}).get("regione", "Altro") or "Altro"
            elif stratify_by == "tipo_scuola":
                key = case.get("scuola", {}).get("tipo_scuola", "Altro") or "Altro"
            elif stratify_by == "provincia":
                key = case.get("scuola", {}).get("provincia", "Altro") or "Altro"
            else:
                key = "Altro"
            strata[key].append(case)

        sampled = []
        remaining_quota = max_total

        # Prima passata: minimo garantito per strato
        for stratum_name in sorted(strata.keys()):
            stratum_cases = strata[stratum_name]
            take = min(min_per_stratum, len(stratum_cases), remaining_quota)
            sampled.extend(stratum_cases[:take])
            remaining_quota -= take
            if remaining_quota <= 0:
                break

        # Seconda passata: proporzionale con quota rimanente
        if remaining_quota > 0:
            # Raccogli tutti i casi non ancora selezionati
            all_remaining = []
            for stratum_name, stratum_cases in strata.items():
                # Prendi i casi oltre il minimo già selezionato
                all_remaining.extend(stratum_cases[min_per_stratum:])

            if all_remaining:
                # Campionamento sistematico sul resto
                step = max(1, len(all_remaining) // remaining_quota)
                additional = all_remaining[::step][:remaining_quota]
                sampled.extend(additional)

        return sampled

    def _get_sample_with_coverage(
        self,
        cases: list[dict],
        max_total: int = 80
    ) -> tuple[list[dict], dict]:
        """Get stratified sample with coverage statistics.

        Args:
            cases: Lista completa di casi
            max_total: Numero massimo di casi

        Returns:
            Tuple di (casi campionati, statistiche di copertura)
        """
        # Prima prova stratificato per regione
        sampled = self._stratified_sample(cases, min_per_stratum=2, max_total=max_total)

        # Calcola copertura
        original_regions = set(c.get("scuola", {}).get("regione", "Altro") for c in cases)
        sampled_regions = set(c.get("scuola", {}).get("regione", "Altro") for c in sampled)

        coverage = {
            "total_cases": len(cases),
            "sampled_cases": len(sampled),
            "sample_rate": round(len(sampled) / len(cases) * 100, 1) if cases else 0,
            "total_regions": len(original_regions),
            "covered_regions": len(sampled_regions),
            "region_coverage": round(len(sampled_regions) / len(original_regions) * 100, 1) if original_regions else 0,
            "missing_regions": sorted(original_regions - sampled_regions)
        }

        return sampled, coverage

    def _summarize_cases(self, cases: list[dict], disable_sampling: bool = False) -> dict:
        region_counts = defaultdict(int)
        province_counts = defaultdict(int)
        category_counts = defaultdict(int)
        schools = set()

        for case in cases:
            scuola = case.get("scuola", {})
            pratica = case.get("pratica", {})
            region = scuola.get("regione") or "Non specificata"
            province = scuola.get("provincia") or "Non specificata"
            category = pratica.get("categoria") or "Altre attivita"
            region_counts[region] += 1
            province_counts[province] += 1
            category_counts[category] += 1
            code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
            if code:
                schools.add(code)

        n_cases = len(cases)
        
        if disable_sampling:
            # Analisi chunk: usa formato compresso per ridurre token
            # Ottimizzazione per modelli locali 27B
            max_chars = int(os.getenv("META_REPORT_MAX_CHUNK_CHARS", "6000"))
            sample_cases = self._compress_cases_for_prompt(cases, max_chars=max_chars)
            detail_level = "chunk_compresso (formato ottimizzato per modelli locali)"
        else:
            # Logica dinamica per il sampling e livello dettaglio
            if n_cases < 10:
                per_region = 3
                max_total = 10
                detail_level = "sintetico (pochi casi)"
            elif n_cases < 50:
                per_region = 5
                max_total = 25
                detail_level = "medio (alcuni esempi rappresentativi)"
            elif n_cases < 100:
                per_region = 10
                max_total = 50
                detail_level = "approfondito (molti esempi e cluster)"
            else:
                per_region = 20
                max_total = 80
                detail_level = "molto dettagliato (ampia varieta di esempi e cluster)"

            sample_cases = self._sample_case_labels(cases, per_region=per_region, max_total=max_total)
        top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_provinces = sorted(province_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "cases_count": n_cases,
            "schools_count": len(schools),
            "region_counts": dict(region_counts),
            "province_counts": dict(province_counts),
            "category_counts": dict(category_counts),
            "top_regions": top_regions,
            "top_provinces": top_provinces,
            "sample_cases": sample_cases,
            "detail_level": detail_level,
        }

    def _compress_cases_for_prompt(self, cases: list[dict], max_chars: int = 6000) -> str:
        """Crea sommario compatto dei casi per il prompt (riduce token).

        Ottimizzazione per modelli locali 27B: invece di passare JSON completo,
        crea un elenco lineare compatto che preserva le info essenziali.

        Args:
            cases: Lista di casi da comprimere
            max_chars: Limite massimo caratteri output

        Returns:
            Stringa compressa con un caso per riga
        """
        lines = []
        for c in cases:
            scuola = c.get("scuola", {})
            pratica = c.get("pratica", {})
            # Una riga compatta per caso: Nome (Codice): Titolo [Categoria]
            nome = scuola.get("nome", "ND")[:40]
            codice = scuola.get("codice") or scuola.get("codice_meccanografico") or "ND"
            titolo = (pratica.get("titolo") or "")[:80]
            categoria = (pratica.get("categoria") or "")[:30]
            regione = scuola.get("regione") or ""
            provincia = scuola.get("provincia") or ""

            line = f"• {nome} ({codice}): {titolo}"
            if categoria:
                line += f" [{categoria}]"
            if provincia:
                line += f" - {provincia}"
            elif regione:
                line += f" - {regione}"

            lines.append(line[:180])

        compressed = "\n".join(lines)
        if len(compressed) > max_chars:
            # Tronca e indica quanti casi totali
            truncated = compressed[:max_chars].rsplit("\n", 1)[0]
            compressed = truncated + f"\n[...{len(cases)} casi totali, alcuni omessi per brevità]"
        return compressed

    def _build_activity_rows(self, cases: list[dict]) -> list[dict]:
        rows = []
        for case in cases:
            scuola = case.get("scuola", {})
            pratica = case.get("pratica", {})
            themes = self._extract_themes(case)
            rows.append({
                "tema": "; ".join(themes),
                "regione": scuola.get("regione") or "Non specificata",
                "provincia": scuola.get("provincia") or "",
                "scuola": scuola.get("nome") or "Scuola",
                "codice_meccanografico": scuola.get("codice") or scuola.get("codice_meccanografico") or "",
                "ordine_grado": scuola.get("ordine_grado") or "",
                "tipo_scuola": scuola.get("tipo_scuola") or "",
                "categoria": pratica.get("categoria") or "",
                "titolo": pratica.get("titolo") or "",
                "ambiti_attivita": " | ".join(pratica.get("ambiti_attivita", [])),
            })
        return rows

    def _write_activity_table(self, output_path: Path, rows: list[dict]) -> None:
        if not rows:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        table_path = output_path.with_suffix(".activities.csv")
        fieldnames = list(rows[0].keys())
        with table_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _build_summary_table(
        self,
        theme_counts: dict,
        theme_groups: dict,
        min_cases: int
    ) -> str:
        """Build markdown summary table for themes."""
        lines = [
            "| Tema | Casi | Scuole | Regioni principali |",
            "|------|------|--------|-------------------|",
        ]
        for theme in sorted(theme_counts.keys(), key=lambda t: theme_counts[t], reverse=True):
            count = theme_counts[theme]
            cases = theme_groups.get(theme, [])
            schools = set()
            region_counts = defaultdict(int)
            for case in cases:
                scuola = case.get("scuola", {})
                code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
                if code:
                    schools.add(code)
                region = scuola.get("regione") or "N/D"
                region_counts[region] += 1
            top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            regions_str = ", ".join(f"{r} ({c})" for r, c in top_regions)
            # Marca temi sotto soglia
            marker = "" if count >= min_cases else " *"
            lines.append(f"| {theme}{marker} | {count} | {len(schools)} | {regions_str} |")
        lines.append("")
        lines.append(f"*Temi con meno di {min_cases} casi sono aggregati in 'Altri temi emergenti'*")
        return "\n".join(lines)

    def _build_minor_themes_section(
        self,
        minor_themes: dict[str, list],
        theme_counts: dict
    ) -> str:
        """Build a compact section for themes with few cases."""
        if not minor_themes:
            return ""

        lines = ["I seguenti temi emergenti presentano un numero limitato di casi ma meritano menzione:\n"]

        for theme in sorted(minor_themes.keys(), key=lambda t: theme_counts.get(t, 0), reverse=True):
            cases = minor_themes[theme]
            count = len(cases)
            # Estrai info sintetiche
            schools = set()
            regions = set()
            examples = []
            for case in cases[:3]:  # Max 3 esempi
                scuola = case.get("scuola", {})
                pratica = case.get("pratica", {})
                code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
                nome = scuola.get("nome") or "Scuola"
                if code:
                    schools.add(code)
                    examples.append(f"{nome} ({code})")
                region = scuola.get("regione")
                if region:
                    regions.add(region)

            regions_str = ", ".join(sorted(regions)[:3])
            examples_str = "; ".join(examples[:2])
            lines.append(f"- **{theme}** ({count} casi, {len(schools)} scuole): {regions_str}. Es: {examples_str}")

        return "\n".join(lines)

    # =========================================================================
    # Fase 1.2: Caching dei risultati intermedi
    # =========================================================================

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for chunk results."""
        cache_dir = self.base_dir / ".cache" / "meta_report_chunks"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _get_cache_key(
        self,
        dimension: str,
        theme: str,
        chunk_index: int,
        chunk_data: dict,
        prompt_profile: str
    ) -> str:
        """Generate a unique cache key for a chunk.

        The key is based on the content hash to ensure cache invalidation
        when data changes.
        """
        # Crea un hash basato sui dati rilevanti
        key_data = {
            "dimension": dimension,
            "theme": theme,
            "chunk_index": chunk_index,
            "prompt_profile": prompt_profile,
            "cases_count": chunk_data.get("cases_count", 0),
            "sample_cases": chunk_data.get("sample_cases", [])[:3],  # Prime 3 per variazione
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode()).hexdigest()[:12]

    def _get_chunk_cache_path(
        self,
        dimension: str,
        theme: str,
        prompt_profile: str
    ) -> Path:
        """Get the cache file path for a dimension/theme combination."""
        safe_theme = re.sub(r"[^a-zA-Z0-9_-]", "_", theme)[:50]
        return self._get_cache_dir() / f"{dimension}_{safe_theme}_{prompt_profile}_chunks.json"

    def _load_chunk_cache(self, cache_path: Path) -> dict:
        """Load cached chunk notes from file."""
        if not cache_path.exists():
            return {}
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[cache] Warning: Could not load cache {cache_path}: {e}")
            return {}

    def _save_chunk_cache(self, cache_path: Path, cache_data: dict) -> None:
        """Save chunk notes to cache file."""
        try:
            cache_path.write_text(
                json.dumps(cache_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except OSError as e:
            print(f"[cache] Warning: Could not save cache {cache_path}: {e}")

    def _clear_chunk_cache(self, cache_path: Path) -> None:
        """Clear the cache file after successful generation."""
        try:
            if cache_path.exists():
                cache_path.unlink()
        except OSError:
            pass

    # =========================================================================
    # Fase 3.2: Estrazione pattern per contesto cumulativo
    # =========================================================================

    def _extract_patterns_from_chunk(self, chunk_content: str) -> list[str]:
        """Extract key patterns from chunk content for cumulative context.

        Fase 3.2: Analizza il contenuto del chunk per identificare pattern
        chiave da passare ai chunk successivi.

        Args:
            chunk_content: Contenuto testuale del chunk generato

        Returns:
            Lista di pattern identificati (max 3)
        """
        patterns = []

        # Pattern 1: Cerca frasi che iniziano con pattern indicator
        pattern_indicators = [
            "emerge", "si nota", "pattern", "tendenza",
            "approccio", "modello", "pratica comune",
            "frequente", "diffuso", "ricorrente"
        ]

        sentences = chunk_content.replace("\n", " ").split(".")
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(ind in sentence_lower for ind in pattern_indicators):
                # Estrai una versione breve della frase
                if len(sentence.strip()) > 20:
                    # Prendi le prime parole significative
                    words = sentence.strip().split()[:15]
                    pattern = " ".join(words)
                    if pattern and pattern not in patterns:
                        patterns.append(pattern.strip())
                        if len(patterns) >= 3:
                            break

        # Pattern 2: Se non abbiamo trovato abbastanza, cerca scuole menzionate
        if len(patterns) < 2:
            # Cerca nomi di scuole con codice
            school_pattern = r'([A-Z][a-zA-Z\s]+)\s*\([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7}\)'
            matches = re.findall(school_pattern, chunk_content)
            for match in matches[:2]:
                school_name = match.strip()
                if school_name and len(school_name) > 5:
                    patterns.append(f"Esempio: {school_name}")
                    if len(patterns) >= 3:
                        break

        return patterns[:3]

    # =========================================================================

    def _generate_theme_summary(
        self,
        dimension: str,
        dimension_name: str,
        theme: str,
        cases: list[dict],
        prompt_profile: str,
        filters: Optional[dict] = None,
        region: Optional[str] = None
    ) -> str:
        theme_summary = self._summarize_cases(cases)
        theme_summary.update({
            "dimension": dimension,
            "dimension_name": dimension_name,
            "theme": theme,
            "scope": "region" if region else "national",
            "region": region,
        })

        # Chunk size dinamico ottimizzato per modelli locali
        default_base_chunk_size = int(os.getenv("META_REPORT_THEME_CHUNK_SIZE", "30"))
        base_chunk = getattr(self.provider, "recommended_chunk_size", default_base_chunk_size)

        # Rilevamento modello locale per chunk size adattivo
        model_name = getattr(self.provider, 'model', '').lower()
        is_local_small = any(x in model_name for x in ['27b', '14b', '8b', '7b', 'gemma', 'llama', 'qwen'])

        if is_local_small:
            # Modelli locali: chunk più piccoli per migliore qualità
            local_chunk_size = int(os.getenv("META_REPORT_LOCAL_CHUNK_SIZE", "12"))
            chunk_size = max(8, min(local_chunk_size, int(base_chunk * 0.5)))
            print(f"[thematic] Local model detected ({model_name}): using smaller chunks ({chunk_size})")
        else:
            # Modelli cloud: chunk più grandi per efficienza
            chunk_size = max(20, int(base_chunk * 1.2))
            print(f"[thematic] Cloud model: using larger chunks ({chunk_size})")
        # Abbassiamo la soglia a 35 per forzare il chunking anche su temi medi
        chunk_threshold = int(os.getenv("META_REPORT_THEME_CHUNK_THRESHOLD", "35"))
        use_chunking = len(cases) >= chunk_threshold

        if use_chunking:
            # Fase 3.1: Usa chunking semantico se abilitato
            if ENABLE_SEMANTIC_CHUNKING:
                chunks = self._semantic_chunk_cases(cases, chunk_size, SEMANTIC_CHUNKING_STRATEGY)
                print(f"[thematic] Using semantic chunking (strategy: {SEMANTIC_CHUNKING_STRATEGY})")
            else:
                chunks = self._chunk_cases(cases, chunk_size)

            chunk_notes = []

            # Fase 1.2: Setup caching
            cache_path = self._get_chunk_cache_path(dimension, theme, prompt_profile)
            cached_notes = self._load_chunk_cache(cache_path) if ENABLE_CHUNK_CACHE else {}
            cache_hits = 0
            cache_misses = 0

            # Fase 3.2: Pattern cumulativi per contesto tra chunk
            cumulative_patterns = []

            for idx, chunk in enumerate(chunks, 1):
                # Per i chunk, disabilitiamo il sampling: vogliamo che l'LLM veda tutto
                chunk_summary = self._summarize_cases(chunk, disable_sampling=True)
                chunk_data = {
                    "dimension": dimension,
                    "dimension_name": dimension_name,
                    "theme": theme,
                    "scope": "region" if region else "national",
                    "region": region,
                    "chunk_index": idx,
                    "chunk_total": len(chunks),
                    **chunk_summary,
                }
                if filters:
                    chunk_data["filters"] = filters

                # Fase 3.2: Aggiungi contesto dei chunk precedenti
                if ENABLE_CUMULATIVE_CONTEXT and cumulative_patterns:
                    # Passa gli ultimi 3 pattern identificati per evitare ridondanze
                    chunk_data["previous_patterns"] = cumulative_patterns[-3:]
                    chunk_data["context_instruction"] = (
                        "NOTA: I seguenti pattern sono già stati identificati nei chunk precedenti. "
                        "Evita di ripeterli e cerca elementi NUOVI o COMPLEMENTARI:\n" +
                        "\n".join(f"- {p}" for p in cumulative_patterns[-3:])
                    )

                # Fase 1.2: Check cache
                cache_key = self._get_cache_key(dimension, theme, idx, chunk_data, prompt_profile)

                if ENABLE_CHUNK_CACHE and cache_key in cached_notes:
                    # Cache hit - riusa il risultato precedente
                    chunk_notes.append(cached_notes[cache_key])
                    cache_hits += 1
                    print(f"[cache] Chunk {idx}/{len(chunks)} loaded from cache")
                else:
                    # Cache miss - genera e salva
                    chunk_response = self.provider.generate_best_practices(
                        chunk_data,
                        "thematic_group_chunk",
                        prompt_profile=prompt_profile
                    )
                    chunk_notes.append(chunk_response.content)
                    cache_misses += 1

                    # Salva in cache dopo ogni chunk (checkpoint)
                    if ENABLE_CHUNK_CACHE:
                        cached_notes[cache_key] = chunk_response.content
                        self._save_chunk_cache(cache_path, cached_notes)
                        print(f"[cache] Chunk {idx}/{len(chunks)} saved to cache")

                # Fase 3.2: Estrai pattern dal chunk corrente per il contesto cumulativo
                if ENABLE_CUMULATIVE_CONTEXT:
                    new_patterns = self._extract_patterns_from_chunk(chunk_notes[-1])
                    cumulative_patterns.extend(new_patterns)

            if ENABLE_CHUNK_CACHE and (cache_hits > 0 or cache_misses > 0):
                print(f"[cache] Summary: {cache_hits} hits, {cache_misses} misses")

            merge_data = dict(theme_summary)
            merge_data["chunk_count"] = len(chunks)
            merge_data["chunk_notes"] = chunk_notes
            if filters:
                merge_data["filters"] = filters
            response = self.provider.generate_best_practices(
                merge_data,
                "thematic_group_merge",
                prompt_profile=prompt_profile
            )

            # Fase 1.2: Clear cache after successful merge
            if ENABLE_CHUNK_CACHE:
                self._clear_chunk_cache(cache_path)

            return response.content

        if filters:
            theme_summary["filters"] = filters
        response = self.provider.generate_best_practices(
            theme_summary,
            "thematic_group_merge",
            prompt_profile=prompt_profile
        )
        return response.content

    def _build_methodology_section(self, is_single_theme: bool, is_regional: bool) -> str:
        """Build dynamic methodology section based on report context."""
        
        intro = "Il presente report offre un'analisi monografica" if is_single_theme else "Il presente report offre un'analisi tematica comparata"
        scope_text = "analizzando le specificità territoriali a livello provinciale." if is_regional else "confrontando i diversi approcci a livello regionale e nazionale."
        
        return f"""### Nota Metodologica

{intro} delle attività di orientamento estratte dai PTOF (Piani Triennali dell'Offerta Formativa) degli istituti scolastici, catalogate nel dataset `attivita.csv`. L'elaborazione si basa su un'analisi qualitativa automatizzata supportata da modelli linguistici avanzati (LLM), che hanno classificato ogni iniziativa secondo una tassonomia standardizzata in **sei categorie chiave**:

| Categoria | Descrizione e Obiettivi |
|-----------|-------------------------|
| 🎯 **Progetti e Attività Esemplari** | Iniziative di eccellenza, innovative e ad alto impatto, potenzialmente replicabili in altri contesti. |
| 📚 **Metodologie Didattiche Innovative** | Adozione di nuovi approcci pedagogici (es. debate, peer tutoring, gamification) per rendere l'orientamento attivo e coinvolgente. |
| 🤝 **Partnership e Collaborazioni** | Reti strategiche con Università, ITS, aziende ed enti territoriali per connettere scuola e mondo del lavoro. |
| ⚙️ **Azioni di Sistema** | Interventi strutturali di governance, coordinamento dei dipartimenti e formazione dedicata ai docenti referenti. |
| 🌈 **Inclusione e BES** | Strategie specifiche per garantire l'accessibilità dei percorsi orientativi a studenti con BES, DSA e disabilità. |
| 🗺️ **Esperienze Territoriali** | Progetti radicati nel tessuto socio-economico locale, {scope_text} |

L'obiettivo è restituire una narrazione coerente che non si limiti a un elenco di attività, ma evidenzi le **direttrici strategiche**, le **interconnessioni multidisciplinari** e le **specificità territoriali**.

### Come leggere questo report

- **Panoramica Territoriale**: Distribuzione delle attività per area (Regioni o Province).
- **Analisi Monografica**: Approfondimento strutturato sulle direttrici strategiche e operative.
- **Sintesi Executive**: Visione d'insieme per i decisori con raccomandazioni finali.
"""

    def _build_territorial_table(self, cases: list[dict], is_regional: bool, filters: dict, prompt_profile: str = "") -> str:
        """Build a territorial distribution table with categories and schools."""
        
        # 1. Define Categories (fixed order)
        categories = [
            "Progetti e Attività Esemplari",
            "Metodologie Didattiche Innovative",
            "Partnership e Collaborazioni",
            "Azioni di Sistema",
            "Inclusione e BES",
            "Esperienze Territoriali"
        ]
        
        # 2. Aggregations
        # Structure: territory -> { "schools": set(codes), "categories": { cat: count } }
        territory_data = defaultdict(lambda: {"schools": set(), "categories": defaultdict(int), "school_names": set()})
        
        current_region = filters.get("regione") if filters else None
        target_key = "provincia" if (is_regional and current_region) else "regione"
        header_name = "Provincia" if (is_regional and current_region) else "Regione"

        for case in cases:
            # Handle both dict and object access
            if isinstance(case, dict):
                scuola = case.get("school", {}) or case.get("scuola", {})
                code = scuola.get("codice_meccanografico") or scuola.get("codice")
                name = scuola.get("nome_scuola") or scuola.get("nome")
                terr_val = scuola.get(target_key)
            else:
                scuola = getattr(case, "school", None) or getattr(case, "scuola", None)
                if not scuola: continue
                code = getattr(scuola, "codice_meccanografico", None) or getattr(scuola, "codice", None)
                name = getattr(scuola, "nome_scuola", None) or getattr(scuola, "nome", None)
                terr_val = getattr(scuola, target_key, None)

            if not terr_val: 
                terr_val = "ND"
            
            # Normalize territory name (capitalization)
            terr_val = terr_val.title()
            
            # Determine category
            # _assign_primary_category returns (primary, secondary_list)
            # It only takes (practice), not prompt_profile
            cat, _ = self._assign_primary_category(case)
            if not cat: continue # Skip generic/blocked
            
            # Update stats
            territory_data[terr_val]["categories"][cat] += 1
            if code:
                territory_data[terr_val]["schools"].add(code)
            if name:
                # Store "Name (Code)" for listing
                school_str = f"{name}"
                if code: school_str += f" ({code})"
                territory_data[terr_val]["school_names"].add(school_str)

        lines = []
        
        # Table Title
        title_suffix = f": {current_region}" if (is_regional and current_region) else ""
        lines.append(f"### Dettaglio Territoriale{title_suffix}")
        lines.append("")
        
        # Table Header
        # | Territorio | Scuole | Cat 1 | Cat 2 | ... | Tot Attività |
        headers = [header_name, "Scuole"] + [c[:4]+"." for c in categories] + ["Tot"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Sort territories by total activities desc
        sorted_territories = sorted(
            territory_data.items(), 
            key=lambda x: sum(x[1]["categories"].values()), 
            reverse=True
        )
        
        for terr, data in sorted_territories:
            row = [f"{terr}"]
            row.append(str(len(data["schools"])))
            
            total_acts = 0
            for cat in categories:
                count = data["categories"].get(cat, 0)
                row.append(str(count) if count > 0 else "-")
                total_acts += count
            
            row.append(f"{total_acts}")
            lines.append("| " + " | ".join(row) + " |")
            
        lines.append("")
        lines.append("_Legenda: Prog.=Progetti Esemplari, Meto.=Metodologie, Part.=Partnership, Azio.=Azioni Sistema, Incl.=Inclusione, Espe.=Esperienze Territoriali_")
        lines.append("")
        
        # List of Schools per Territory
        lines.append("#### Scuole Coinvolte per Territorio")
        for terr, data in sorted_territories:
            if not data["school_names"]: continue
            sorted_schools = sorted(list(data["school_names"]))
            lines.append(f"- **{terr}** ({len(sorted_schools)}): {', '.join(sorted_schools)}.")
            
        return "\n".join(lines)
    def _parse_school_analysis(self, content: str) -> dict[str, list[str]]:
        """Parse LLM output into categories."""
        sections = defaultdict(list)
        current_category = None
        buffer = []
        
        for line in content.splitlines():
            stripped = line.strip()
            # Match headings like # Category or ## Category or **Category**
            match = re.search(r"^[#\*]+\s*(.*?)(?:[\*#]+)?$", stripped)
            
            if stripped.startswith("#") or (stripped.startswith("**") and stripped.endswith("**")):
                # New category
                if current_category and buffer:
                    sections[current_category].append("\n".join(buffer).strip())
                
                heading = stripped.replace("#", "").replace("*", "").strip()
                current_category = heading
                buffer = []
            else:
                if current_category:
                    buffer.append(line)
        
        # Flush last
        if current_category and buffer:
            sections[current_category].append("\n".join(buffer).strip())
            
        return sections

    def _generate_by_school_loop(
        self,
        cases: list[dict],
        filters: dict,
        prompt_profile: str
    ) -> dict[str, dict[str, list[str]]]:
        """Process cases school by school and accumulate results by category and territory."""
        
        # Group by school
        schools_map = defaultdict(list)
        for c in cases:
            school = c.get("school", {}) or c.get("scuola", {})
            code = school.get("codice_meccanografico") or school.get("codice") or "ND"
            schools_map[code].append(c)
            
        print(f"[thematic] Processing {len(schools_map)} schools...")
        
        # Structure: category -> territory -> list of entries
        category_accumulator = defaultdict(lambda: defaultdict(list))
        
        categories_map = {
            "Progetti e Attività Esemplari": ["progetti", "esemplari", "eccellenza"],
            "Metodologie Didattiche Innovative": ["metodologie", "didattiche", "innovative"],
            "Partnership e Collaborazioni": ["partnership", "collaborazioni", "reti"],
            "Azioni di Sistema": ["azioni di sistema", "governance", "sistema"],
            "Inclusione e BES": ["inclusione", "bes", "bisogni", "speciali"],
            "Esperienze Territoriali": ["territoriali", "territorio", "locali"]
        }

        # Determine territorial key based on filters
        is_regional_analysis = bool(filters and filters.get("regione"))
        
        for i, (code, school_cases) in enumerate(schools_map.items(), 1):
            school_data = school_cases[0].get("school", {}) or school_cases[0].get("scuola", {})
            school_name = school_data.get("nome") or school_data.get("nome_scuola") or "Scuola"
            
            # Determine territory for this school
            if is_regional_analysis:
                territory = school_data.get("provincia") or "Provincia ND"
            else:
                territory = school_data.get("regione") or "Regione ND"

            print(f"[thematic] ({i}/{len(schools_map)}) Analyzing {school_name} ({code}) [{territory}]...")
            
            # Simple retry mechanism if needed, but for now single pass
            try:
                analysis_data = {
                    "school_name": school_name,
                    "school_code": code,
                    "practices": [self._build_case_record(c) for c in school_cases],
                    "filters": filters
                }
                
                response = self.provider.generate_best_practices(
                    analysis_data,
                    "thematic_school_analysis",
                    prompt_profile=prompt_profile
                )
                
                parsed_sections = self._parse_school_analysis(response.content)
                
                # Check for empty parse result
                if not parsed_sections:
                    print(f"[thematic] Warning: No sections extracted for {code}")
                    # Could dump raw content for debug?
                    # continue
                
                found_categories = 0
                for cat, contents in parsed_sections.items():
                    # Normalize category key
                    norm_cat = None
                    cat_lower = cat.lower()
                    
                    for std_cat, keywords in categories_map.items():
                        if any(kw in cat_lower for kw in keywords):
                            norm_cat = std_cat
                            break
                    
                    if not norm_cat:
                         # Fallback for unexpected categories
                         norm_cat = "Altri Temi e Spunti"

                    for content in contents:
                        if content and len(content.strip()) > 10: # Min length check
                            # Add to specific territory bucket within category
                            # FIX: Name normal, Code BOLD
                            entry = f"{school_name} (**{code}**)\n\n{content}"
                            category_accumulator[norm_cat][territory].append(entry)
                            found_categories += 1
                
                if found_categories == 0:
                     print(f"[thematic] Warning: No valid content found for {code}")

            except Exception as e:
                print(f"[thematic] Error analyzing school {code}: {e}")
                
        return category_accumulator

    def generate(
        self,
        dimension: str,
        force: bool = False,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate thematic report for a dimension using the new CATEGORY-FIRST pipeline."""
        
        output_path = self.get_output_path(dimension, filters=filters, prompt_profile=prompt_profile)
        # Make unique path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")

        # Load best practices
        all_practices = self.load_best_practices()
        if not all_practices:
            print("[thematic] No best practices found")
            return None

        # Apply Filters
        filters = self._normalize_filters(filters)
        if filters:
            all_practices = [p for p in all_practices if self._matches_filters(p.get("school", {}), filters)]

        if not all_practices:
            print("[thematic] No best practices found after filters")
            return None

        print(f"[thematic] Loaded {len(all_practices)} practices. Starting Category-First Analysis...")

        # 1. Initialize Report Skeleton
        self._initialize_report_skeleton(output_path, dimension, all_practices, filters)
        print(f"[thematic] Skeleton initialized at {output_path}")

        # 2. Category Loop
        priority_categories = [
            "Progetti e Attività Esemplari",
            "Metodologie Didattiche Innovative",
            "Partnership e Collaborazioni",
            "Azioni di Sistema",
            "Inclusione e BES",
            "Esperienze Territoriali"
        ]

        # PRE-PROCESS: Filter generic activities and assign primary categories
        preprocessed = self._preprocess_activities(all_practices)
        
        # Group preprocessed activities by school AND primary category
        # Structure: {category: {school_code: [activities]}}
        activities_by_category_school = {cat: defaultdict(list) for cat in priority_categories}
        school_data = {}  # Cache school info
        
        for activity_id, data in preprocessed.items():
            practice = data["practice"]
            primary_cat = data["primary_category"]
            secondary_cats = data["secondary_categories"]
            
            code = practice.get("school", {}).get("codice_meccanografico")
            if not code:
                continue
                
            # Store school info once
            if code not in school_data:
                school_data[code] = practice.get("school", {})
            
            # Add activity to its PRIMARY category only
            if primary_cat in activities_by_category_school:
                # Include secondary categories info for display
                practice["_secondary_categories"] = secondary_cats
                activities_by_category_school[primary_cat][code].append(practice)
        
        # Debug stats
        for cat, schools in activities_by_category_school.items():
            total_activities = sum(len(acts) for acts in schools.values())
            print(f"[thematic]   Category '{cat}': {len(schools)} schools, {total_activities} activities")

        for category in priority_categories:
            print(f"[thematic] >>> Processing Category: {category}...")
            
            # Start Category Chapter in file
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(f"\n## {category}\n\n")
                f.write(f"<!-- INTRO_PLACEHOLDER_{category.replace(' ', '_')} -->\n\n")
            
            category_content_buffer = []

            # Get schools that have activities for THIS category only
            schools_for_category = activities_by_category_school.get(category, {})
            
            if not schools_for_category:
                print(f"[thematic]   No schools with activities for this category")
                # Remove the chapter header since it's empty
                current_text = output_path.read_text(encoding="utf-8")
                placeholder = f"<!-- INTRO_PLACEHOLDER_{category.replace(' ', '_')} -->"
                to_remove = f"\n## {category}\n\n{placeholder}\n\n"
                updated_text = current_text.replace(to_remove, "")
                output_path.write_text(updated_text, encoding="utf-8")
                continue

            # 2a. Loop Schools (Grouped by Territory)
            is_regional_report = bool(filters and filters.get("regione"))
            
            def get_school_territory(code):
                school = school_data.get(code, {})
                return school.get("provincia", "ND") if is_regional_report else school.get("regione", "ND")

            # Sort schools by Territory then Name
            sorted_schools_grouped = sorted(
                schools_for_category.keys(), 
                key=lambda k: (get_school_territory(k), school_data.get(k, {}).get("nome", ""))
            )

            current_territory = None

            for code in sorted_schools_grouped:
                school_territory = get_school_territory(code)
                
                # Identify if territory changed
                if school_territory != current_territory:
                    current_territory = school_territory
                    # Add Territory Header
                    header_text = f"\n#### {current_territory}\n\n"
                    category_content_buffer.append(header_text)
                    with open(output_path, "a", encoding="utf-8") as f:
                        f.write(header_text)

                school_practices = schools_for_category[code]  # Only activities for THIS category
                school_name = school_data.get(code, {}).get("nome", code)
                
                # Build secondary categories note
                secondary_cats = set()
                for p in school_practices:
                    secondary_cats.update(p.get("_secondary_categories", []))
                secondary_note = f" (si collega anche a: {', '.join(secondary_cats)})" if secondary_cats else ""
                
                analysis_data = {
                    "school_name": school_name,
                    "school_code": code,
                    "practices": [self._build_case_record(p) for p in school_practices],
                    "category": category,
                    "secondary_categories": list(secondary_cats),
                    "dimension": DIMENSIONS.get(dimension, dimension),
                    "school_level": filters.get("ordine_grado", "Tutti") if filters else "Tutti",
                    "filters": filters
                }

                # LLM Call for School Category Analysis
                try:
                    response = self.provider.generate_best_practices(
                        analysis_data, 
                        "thematic_category_school_analysis",
                        prompt_profile=prompt_profile
                    )
                    content = response.content.strip()
                    
                    if content: # Only append if not empty
                        # Format as school entry with secondary category note
                        entry_text = f"{school_name} ({code}){secondary_note}\n\n{content}\n\n"
                        category_content_buffer.append(entry_text)
                        
                        # Append immediately to file (streaming feel)
                        with open(output_path, "a", encoding="utf-8") as f:
                            f.write(entry_text)
                        
                        print(f"[thematic]   + Added {school_name} ({school_territory}) to {category}")
                except Exception as e:
                    print(f"[thematic]   ! Error analyzing {school_name} for {category}: {e}")

            # 2b. Generate Synthesis for Category
            if category_content_buffer:
                print(f"[thematic] Generating synthesis for {category}...")
                synthesis_data = {
                    "dimension_name": category,
                    "report_context": "\n".join(category_content_buffer),
                    "filters": filters
                }
                
                # We reuse 'thematic_intro' prompt but now it receives context
                synth_resp = self.provider.generate_best_practices(
                    synthesis_data,
                    "thematic_intro", 
                    prompt_profile=prompt_profile
                )
                
                # Replace placeholder in file
                current_text = output_path.read_text(encoding="utf-8")
                # Fix: Use explicit placeholder string matching
                placeholder = f"<!-- INTRO_PLACEHOLDER_{category.replace(' ', '_')} -->"
                if placeholder in current_text:
                    updated_text = current_text.replace(placeholder, synth_resp.content)
                    output_path.write_text(updated_text, encoding="utf-8")
                
                # 2c. Generate School-Type Synthesis (only for II Grado)
                is_ii_grado = filters and ("ii grado" in str(filters.get("ordine_grado", "")).lower() or 
                                           "ii-grado" in str(filters.get("ordine_grado", "")).lower() or
                                           "ii grado" in str(filters.get("ordine-grado", "")).lower())
                
                if is_ii_grado:
                    print(f"[thematic]   Generating school-type syntheses for {category}...")
                    
                    # Group content by school type
                    school_types_content = {
                        "Licei": [],
                        "Istituti Tecnici": [],
                        "Istituti Professionali": []
                    }
                    
                    # Track school counts by type
                    school_types_codes = {
                        "Licei": set(),
                        "Istituti Tecnici": set(),
                        "Istituti Professionali": set()
                    }
                    
                    for code in schools_for_category.keys():
                        school_info = school_data.get(code, {})
                        tipo = school_info.get("tipo_scuola", "").lower()
                        
                        # Classify school
                        if "liceo" in tipo:
                            school_types_codes["Licei"].add(code)
                        elif "tecnico" in tipo:
                            school_types_codes["Istituti Tecnici"].add(code)
                        elif "professionale" in tipo:
                            school_types_codes["Istituti Professionali"].add(code)
                    
                    # Match content to school types based on school codes in entries
                    for entry in category_content_buffer:
                        if "####" in entry:  # Skip territory headers
                            continue
                        for code in school_types_codes["Licei"]:
                            if code in entry:
                                school_types_content["Licei"].append(entry)
                                break
                        for code in school_types_codes["Istituti Tecnici"]:
                            if code in entry:
                                school_types_content["Istituti Tecnici"].append(entry)
                                break
                        for code in school_types_codes["Istituti Professionali"]:
                            if code in entry:
                                school_types_content["Istituti Professionali"].append(entry)
                                break
                    
                    # Generate synthesis for each school type that has content
                    type_syntheses = []
                    for school_type, content_list in school_types_content.items():
                        if content_list:
                            synth_data = {
                                "category": category,
                                "school_type": school_type,
                                "content": "\n\n".join(content_list),
                                "school_count": len(school_types_codes[school_type])
                            }
                            try:
                                type_resp = self.provider.generate_best_practices(
                                    synth_data,
                                    "thematic_category_type_synthesis",
                                    prompt_profile=prompt_profile
                                )
                                if type_resp.content.strip():
                                    type_syntheses.append(f"### Sintesi {school_type}\n\n{type_resp.content.strip()}\n")
                                    print(f"[thematic]     + {school_type} synthesis generated")
                            except Exception as e:
                                print(f"[thematic]     ! Error generating {school_type} synthesis: {e}")
                    
                    # Append type syntheses to report
                    if type_syntheses:
                        with open(output_path, "a", encoding="utf-8") as f:
                            f.write("\n---\n\n")  # Separator before type syntheses
                            f.write("\n".join(type_syntheses))
                
                # 2d. Generate Similar Schools Section (always, not just II Grado)
                if len(schools_for_category) >= 3:  # Need at least 3 schools to find similarities
                    print(f"[thematic]   Generating similar schools analysis for {category}...")
                    
                    # Use the already-generated content from the report, not raw activities
                    similar_data = {
                        "category": category,
                        "schools_data": "\n\n".join(category_content_buffer)  # Text già scritto nel report
                    }
                    
                    try:
                        similar_resp = self.provider.generate_best_practices(
                            similar_data,
                            "thematic_similar_schools",
                            prompt_profile=prompt_profile
                        )
                        if similar_resp.content.strip():
                            with open(output_path, "a", encoding="utf-8") as f:
                                f.write("\n### Scuole con Attività Simili\n\n")
                                f.write(similar_resp.content.strip())
                                f.write("\n\n")
                            print(f"[thematic]     + Similar schools analysis generated")
                    except Exception as e:
                        print(f"[thematic]     ! Error generating similar schools: {e}")
                        
            else:
                 # No content for this category
                 print(f"[thematic] No content for {category}. Removing header.")
                 current_text = output_path.read_text(encoding="utf-8")
                 placeholder = f"<!-- INTRO_PLACEHOLDER_{category.replace(' ', '_')} -->"
                 # Removes section header and placeholder
                 to_remove = f"\n## {category}\n\n{placeholder}\n\n"
                 updated_text = current_text.replace(to_remove, "")
                 output_path.write_text(updated_text, encoding="utf-8")

        # 3. Global Sections (Territorial, Intro, Conclusion)
        print("[thematic] Generating Global Sections...")
        full_report_text = output_path.read_text(encoding="utf-8")
        
        # 3a. Territorial Analysis
        print("[thematic] > Generating Territorial Analysis...")
        terr_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "report_context": full_report_text,
            "territorial_stats": self._calculate_territorial_stats(all_practices, filters),
            "scope": "region" if filters and filters.get("regione") else "national"
        }
        terr_resp = self.provider.generate_best_practices(terr_data, "thematic_territorial_analysis", prompt_profile)
        
        # 3b. Introduction (Global)
        print("[thematic] > Generating Global Introduction...")
        intro_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "report_context": full_report_text 
        }
        intro_resp = self.provider.generate_best_practices(intro_data, "thematic_intro", prompt_profile)
        
        # 3c. Conclusion
        print("[thematic] > Generating Conclusion...")
        concl_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "report_context": full_report_text
        }
        concl_resp = self.provider.generate_best_practices(concl_data, "thematic_conclusion", prompt_profile)

        # 4. Final Injection
        final_text = output_path.read_text(encoding="utf-8")
        
        # Inject Introduction
        if "<!-- GLOBAL_INTRO_PLACEHOLDER -->" in final_text:
            final_text = final_text.replace("<!-- GLOBAL_INTRO_PLACEHOLDER -->", intro_resp.content)
        
        # Append Territorial/Conclusion
        # We need to rewrite just in case replacing Intro changed length
        with open(output_path, "w", encoding="utf-8") as f: 
            f.write(final_text)
        
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n\n## Differenze Territoriali\n\n")
            f.write(terr_resp.content)
            f.write("\n\n")
            f.write(self._build_territorial_table(all_practices, bool(filters and filters.get("regione")), filters))
            f.write("\n\n## Conclusioni e Sintesi\n\n")
            f.write(concl_resp.content)
            
            f.write("\n\n## Appendice\n\n")
            f.write(f"Analisi basata su {len(all_practices)} attività di {len(school_data)} scuole.\n")
        
        print(f"[thematic] Report generated: {output_path}")
        
        try:
            from src.agents.meta_report.postprocess import postprocess_report
            print("[thematic] Applying postprocessor...")
            postprocess_report(output_path)
        except Exception as e:
            print(f"[thematic] Postprocessor warning: {e}")

        return output_path

    def _initialize_report_skeleton(self, path: Path, dimension: str, practices: list[dict], filters: dict):
        """Initialize the report file with headers, methodology and placeholders."""
        is_regional = bool(filters and filters.get("regione"))
        
        content = [
            f"# {DIMENSIONS.get(dimension, dimension)}",
            self._build_methodology_section(True, is_regional),
            "## Introduzione",
            "<!-- GLOBAL_INTRO_PLACEHOLDER -->", 
            "\n"
        ]
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(content), encoding="utf-8")

    def _calculate_territorial_stats(self, practices: list[dict], filters: dict) -> dict:
        """Calculate territorial stats for context."""
        stats = defaultdict(int)
        for p in practices:
             scuola = p.get("school", {}) or p.get("scuola", {})
             if filters and filters.get("regione"):
                 key = scuola.get("provincia", "ND")
             else:
                 key = scuola.get("regione", "ND")
             stats[key] += 1
        return dict(stats)

        output_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")

        # Load best practices
        all_practices = self.load_best_practices()
        if not all_practices:
            print("[thematic] No best practices found")
            return None

        if filters:
            all_practices = [p for p in all_practices if self._matches_filters(p.get("school", {}), filters)]

        if not all_practices:
            print("[thematic] No best practices found after filters")
            return None

        print(f"[thematic] Loaded {len(all_practices)} practices. Starting School-by-School Analysis...")
        
        # Calculate stats for territorial analysis
        territorial_stats = defaultdict(int) 
        for p in all_practices:
            scuola = p.get("school", {}) or p.get("scuola", {})
            if filters and filters.get("regione"):
                 # Regional scope -> count per province
                 key = scuola.get("provincia", "ND")
            else:
                 # National scope -> count per region
                 key = scuola.get("regione", "ND")
            territorial_stats[key] += 1

        # 1. School Loop Analysis (Execution Phase)
        # Returns: category -> territory -> list of entries
        category_accumulator = self._generate_by_school_loop(all_practices, filters, prompt_profile)

        # 2. Phase: Category Summaries (for context to Intro/Conclusion)
        # We flatten the structure just for synthesis context
        category_flat_notes = {}
        for cat, territories in category_accumulator.items():
            all_entries = []
            for terr, entries in territories.items():
                all_entries.extend(entries)
            category_flat_notes[cat] = all_entries
            
        category_intros = {}
        # We perform a synthesis of each category to guide the intro/conclusion
        for cat, entries in category_flat_notes.items():
            print(f"[thematic] Synthesizing summary for category: {cat}...")
            summary_data = {
                "dimension_name": cat,
                "chunk_notes": entries[:30], # Limit context window if needed, or take sample
                "cases_count": len(entries),
                "scope": "region" if filters and filters.get("regione") else "national"
            }
            resp = self.provider.generate_best_practices(summary_data, "thematic_group_merge", prompt_profile)
            category_intros[cat] = resp.content

        # 3. Phase: High Level Synthesis (Separate Calls)
        print("[thematic] Generating High Level Synthesis Sections...")
        
        # 3a. Introduction
        print("[thematic] > Generating Introduction...")
        intro_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "category_summaries": category_intros
        }
        if filters: intro_data["filters"] = filters
        intro_resp = self.provider.generate_best_practices(intro_data, "thematic_intro", prompt_profile)
        
        # 3b. Territorial Analysis
        print("[thematic] > Generating Territorial Analysis...")
        terr_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "territorial_stats": territorial_stats,
            "scope": "region" if filters and filters.get("regione") else "national"
        }
        if filters: terr_data["filters"] = filters
        terr_resp = self.provider.generate_best_practices(terr_data, "thematic_territorial_analysis", prompt_profile)
        
        # 3c. Conclusion
        print("[thematic] > Generating Conclusion...")
        concl_data = {
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "category_summaries": category_intros
        }
        if filters: concl_data["filters"] = filters
        concl_resp = self.provider.generate_best_practices(concl_data, "thematic_conclusion", prompt_profile)

        # 4. Assemble Report
        content_parts = [
            f"# {DIMENSIONS.get(dimension, dimension)}",
            self._build_methodology_section(True, bool(filters and filters.get("regione"))),
            "## Introduzione",
            intro_resp.content
        ]
        
        priority_order = [
            "Progetti e Attività Esemplari",
            "Metodologie Didattiche Innovative",
            "Partnership e Collaborazioni",
            "Azioni di Sistema",
            "Inclusione e BES",
            "Esperienze Territoriali"
        ]
        
        # Merge discovered categories
        sorted_cats = [c for c in priority_order if c in category_accumulator]
        other_cats = [c for c in category_accumulator if c not in priority_order]
        sorted_cats.extend(other_cats)
        
        for cat in sorted_cats:
            content_parts.append(f"## {cat}")
            # Add the category synthesis
            content_parts.append(category_intros.get(cat, ""))
            
            # Add the school-by-school details, grouped by territory
            content_parts.append("### Dettaglio Scuole\n")
            territories = category_accumulator[cat]
            for territory in sorted(territories.keys()):
                entries = territories[territory]
                if entries:
                    content_parts.append(f"#### {territory}")
                    content_parts.append("\n\n".join(entries))
        
        # Territorial Differences
        content_parts.append("## Differenze Territoriali")
        content_parts.append(terr_resp.content)
        
        # Insert table AFTER text
        content_parts.append(self._build_territorial_table(
            all_practices, 
            bool(filters and filters.get("regione")), 
            filters,
            prompt_profile=prompt_profile
        ))
        
        # Conclusions
        content_parts.append("## Conclusioni e Sintesi")
        content_parts.append(concl_resp.content)

        # Appendice
        appendix_lines = [
            "## Appendice: Note",
            "",
            f"Analisi basata su {len(all_practices)} attività.",
            "Il report è stato generato aggregando le analisi delle singole scuole.",
        ]
        content_parts.append("\n".join(appendix_lines))
        
        final_text = "\n\n".join(content_parts)
        
        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(final_text, encoding="utf-8")
        
        print(f"[thematic] Report generated: {output_path}")
        
        # Metadata
        metadata = {
            "dimension": dimension,
            "dimension_name": DIMENSIONS.get(dimension, dimension),
            "practices_analyzed": len(all_practices),
            "schools_involved": len(set(p.get("school", {}).get("codice_meccanografico") for p in all_practices if p.get("school", {}).get("codice_meccanografico"))),
        }
        if filters:
            metadata["filters"] = self._format_filters(filters)
        metadata["prompt_profile"] = prompt_profile

        # The original code had self.write_report and _write_activity_table here.
        # Since the new code writes directly to output_path, we need to adapt.
        # Assuming _write_activity_table is still desired, but it needs 'activities_rows'.
        # The new strategy doesn't explicitly build 'activities_rows' in the same way.
        # For now, I'll comment out _write_activity_table if 'activities_rows' is not available.
        # If the user wants to keep it, they need to ensure 'activities_rows' is populated.
        # For this change, I'll assume it's not directly needed or will be handled elsewhere.
        # The instruction only provided the new generate method body.

        # If self.write_report is meant to add metadata, we can add it here.
        # However, the new code already writes the content.
        # Let's just return the path as the new code does.
        
        # Postprocessing automatico per correggere codici e formattazione
        try:
            from src.agents.meta_report.postprocess import postprocess_report
            print("[thematic] Applying postprocessor...")
            postprocess_report(output_path)
        except Exception as e:
            print(f"[thematic] Postprocessor warning: {e}")

        # Raffinamento automatico con LLM (opzionale, controllato da env var)
        if os.environ.get("META_REPORT_REFINE", "0") == "1":
            try:
                from src.agents.meta_report.refine import refine_report
                print("[thematic] Applying refinement agent...")
                refine_report(output_path, provider_name=self.provider.__class__.__name__.lower().replace("provider", ""))
            except Exception as e:
                print(f"[thematic] Refinement warning: {e}")
        else:
            print(f"[thematic] Refinement skipped (set META_REPORT_REFINE=1 to enable)")
            print(f"[thematic] Or run: make meta-refine REPORT={output_path}")

        return output_path

    def _prepare_data(self, dimension: str, practices: list[dict]) -> dict:
        """Extract dimension-specific data from best practices."""
        dimension_name = DIMENSIONS[dimension]

        # Filter practices by dimension using keyword matching
        # NOTE: The CSV categories (e.g., "Progetti e Attività Esemplari") differ from
        # the dimension names, so we always use keyword-based matching for all dimensions.
        filtered_practices = []
        keywords = ACTIVITY_KEYWORDS.get(dimension, [])
        
        if not keywords:
            print(f"[thematic] Warning: No keywords defined for dimension: {dimension}")
            return {
                "dimension": dimension,
                "dimension_name": dimension_name,
                "practices_count": 0,
                "schools_count": 0,
                "regional_distribution": {},
                "top_regions": [],
                "practices": [],
                "case_groups": {},
                "inventory_groups": {},
            }
        
        for p in practices:
            # Search in ambiti/attivita correlate
            ambiti = (
                p.get("pratica", {}).get("ambiti_attivita", [])
                or p.get("contesto", {}).get("attivita_correlate", [])
            )
            ambiti_text = " ".join(ambiti).lower()

            # Also search in title and description
            titolo = p.get("pratica", {}).get("titolo", "").lower()
            descrizione = p.get("pratica", {}).get("descrizione", "").lower()
            metodologia = p.get("pratica", {}).get("metodologia", "").lower()
            categoria = p.get("pratica", {}).get("categoria", "").lower()

            search_text = f"{ambiti_text} {titolo} {descrizione} {metodologia} {categoria}"

            if any(kw in search_text for kw in keywords):
                filtered_practices.append(p)

        # Deduplicate by school + title
        seen = set()
        unique_practices = []
        for p in filtered_practices:
            key = (
                p.get("school", {}).get("codice_meccanografico", ""),
                p.get("pratica", {}).get("titolo", "")
            )
            if key not in seen:
                seen.add(key)
                unique_practices.append(p)

        # Aggregate by region
        by_region = defaultdict(list)
        for p in unique_practices:
            region = p.get("school", {}).get("regione", "Non specificata")
            by_region[region].append(p)

        # Get schools involved
        schools = set()
        for p in unique_practices:
            code = p.get("school", {}).get("codice_meccanografico", "")
            if code:
                schools.add(code)

        case_records = [self._build_case_record(p) for p in unique_practices]
        case_groups = self._group_labels_by_category(case_records)
        inventory_groups = self._group_labels_by_region(case_records)

        # Regional summary
        regional_summary = {}
        for region, pracs in by_region.items():
            regional_summary[region] = {
                "count": len(pracs),
                "schools": len(set(p.get("school", {}).get("codice_meccanografico", "") for p in pracs)),
                "examples": [p.get("pratica", {}).get("titolo", "") for p in pracs[:3]]
            }

        return {
            "dimension": dimension,
            "dimension_name": dimension_name,
            "practices_count": len(unique_practices),
            "schools_count": len(schools),
            "regional_distribution": regional_summary,
            "top_regions": sorted(regional_summary.items(), key=lambda x: x[1]["count"], reverse=True)[:5],
            "practices": case_records,
            "case_groups": case_groups,
            "inventory_groups": inventory_groups,
        }
