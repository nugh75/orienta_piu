import glob
import logging
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd

# New Import for Hybrid Logic
from .db_manager import DatabaseManager
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

CLUSTER_PROFILE_SECTION = {
    "key": "profili_cluster",
    "title": "Profili dei Cluster e Differenze",
}

# ── Thematic Sections Configuration ──────────────────────────────────────

THEMATIC_SECTIONS = [
    {
        "key": "sintesi_generale",
        "title": "Commento di Sintesi Generale",
        "description": "Panoramica trasversale sull'orientamento nei PTOF analizzati",
        "score_keys": [
            "mean_finalita",
            "mean_obiettivi",
            "mean_governance",
            "mean_didattica_orientativa",
            "mean_opportunita",
        ],
        "retrieval_query": "sintesi generale orientamento punti di forza debolezza",
    },
    {
        "key": "allineamento_normativo",
        "title": "Allineamento Normativo e Approccio Innovativo",
        "description": "Recepimento delle Linee Guida MIM, D.M. 328/2022, ruolo tutor e orientatore",
        "score_keys": ["2_1_score", "2_5_azione_coordinamento_servizi_score"],
        "retrieval_query": "linee guida orientamento DM 328 2022 tutor orientatore PNRR moduli 30 ore",
    },
    {
        "key": "rapporto_territorio",
        "title": "Rapporto con il Territorio",
        "description": "Partnership, reti, collaborazioni con università, enti, aziende",
        "score_keys": [
            "2_4_obiettivo_continuita_territorio_score",
            "2_5_azione_coordinamento_servizi_score",
        ],
        "extra_csv_keys": ["partnership_count"],
        "retrieval_query": "partnership territorio aziende università enti locali terzo settore PCTO stage tirocini",
    },
    {
        "key": "metodologie_didattiche",
        "title": "Metodologie Didattiche",
        "description": "Analisi delle metodologie didattiche adottate per l'orientamento.",
        "score_keys": ["2_6_didattica_laboratoriale_score", "2_6_didattica_da_esperienza_studenti_score"],
        "retrieval_query": "metodologie didattiche orientative laboratori learning by doing gamification storytelling",
    },
    {
        "key": "strumenti_supporto",
        "title": "Strumenti di Supporto",
        "description": "Analisi degli strumenti specifici (portfolio, questionari, piattaforme) utilizzati per l'orientamento.",
        "score_keys": [],
        "retrieval_query": "e-portfolio portfolio digitale questionari interessi test attitudinali piattaforma unica consiglio orientativo",
    },
    {
        "key": "formazione_personale",
        "title": "Formazione del Personale",
        "description": "Analisi delle attività di formazione per docenti e tutor sui temi dell'orientamento.",
        "score_keys": ["2_5_azione_dialogo_docenti_studenti_score"],
        "retrieval_query": "formazione docenti orientamento tutoraggio psicologia dell'orientamento aggiornamento professionale",
    },
    {
        "key": "figure_professionali",
        "title": "Figure Professionali e Governance",
        "description": "Ruoli, funzioni strumentali e organizzazione interna.",
        "score_keys": ["2_5_azione_coordinamento_servizi_score"],
        "retrieval_query": "funzione strumentale orientamento commissione team referente orientatore tutor scolastico",
    },
    {
        "key": "principali_lacune",
        "title": "Principali Lacune",
        "description": "Gap strutturali: monitoraggio, accessibilità, quadro teorico, continuità",
        "score_keys": [
            "2_5_azione_monitoraggio_azioni_score",
            "2_5_azione_sistema_integrato_inclusione_fragilita_score",
            "2_4_obiettivo_ridurre_abbandono_score",
            "2_4_obiettivo_contrastare_neet_score",
        ],
        "retrieval_query": "criticità orientamento mancanza fondi spazi personale assenza monitoraggio gap",
    },
    {
        "key": "temi_globali_e_scelte_consapevoli",
        "title": "Temi Globali e Scelte Consapevoli",
        "description": "L'orientamento come supporto alle decisioni e alla cittadinanza globale (sostenibilità, giustizia, diritti)",
        "score_keys": [
            "2_3_finalita_progetto_vita_score",
            "2_3_finalita_attitudini_score",
            "2_7_opzionali_volontariato_score",
            "2_4_obiettivo_lifelong_learning_score",
        ],
        "retrieval_query": "scelte consapevoli progetto di vita sostenibilità agenda 2030 cittadinanza globale disuguaglianze",
    },
    {
        "key": "bilancio_complessivo",
        "title": "Bilancio Complessivo",
        "description": "Punti di forza, criticità, prospettive di sviluppo",
        "score_keys": [
            "mean_finalita",
            "mean_obiettivi",
            "mean_governance",
            "mean_didattica_orientativa",
            "mean_opportunita",
        ],
        "retrieval_query": "bilancio finale orientamento conclusioni prospettive future miglioramenti",
    },
    {
        "key": "conclusioni_e_limiti",
        "title": "Conclusioni e Limiti del Report",
        "description": "Sintesi dei risultati principali, limiti metodologici e avvertenze per il lettore",
        "score_keys": [],
        "retrieval_query": "conclusioni limiti metodologia campione rappresentatività orientamento",
    },
]

# ── Methodology keywords for frequency analysis ─────────────────────────
# Same categories used in the Streamlit "Metodologie" page (app/pages/13_Metodologie.py)

METHODOLOGY_KEYWORDS = {
    'Didattica Innovativa': ['PBL', 'STEM', 'STEAM', 'Debate', 'Flipped Classroom', 'Cooperative Learning'],
    'Orientamento': ['PCTO', 'Alternanza', 'Stage', 'Tirocinio', 'Orientamento Narrativo', 'Portfolio'],
    'Inclusione': ['Inclusione', 'BES', 'DSA', 'Peer Education', 'Peer Tutoring', 'Mentoring'],
    'Competenze Trasversali': ['Cittadinanza', 'Legalità', 'Volontariato', 'Service Learning'],
    'Tecnologia': ['Digitale', 'Coding', 'Robotica', 'E-Portfolio'],
    'Laboratori': ['Laboratorio', 'Learning by Doing', 'Outdoor', 'Maker'],
}

ALL_METHODOLOGY_NAMES = [m for methods in METHODOLOGY_KEYWORDS.values() for m in methods]

# ── Territory partner categories for frequency analysis ──────────────────
# Used to classify raw partner names from JSON analysis files into macro-categories

TERRITORY_PARTNER_CATEGORIES = {
    'Università/Ricerca': ['università', 'ateneo', 'politecnico', 'facoltà', 'cnr', 'ricerca', 'accademia'],
    'ITS/Formazione Prof.': ['its', 'istituto tecnico superiore', 'formazione professionale', 'cpia'],
    'Enti Locali': ['comune', 'provincia', 'regione', 'prefettura', 'municipio', 'città metropolitana'],
    'ASL/Sanità': ['asl', 'ausl', 'ospedale', 'consultorio', 'sert', 'neuropsichiatria', 'servizi socio-sanitari'],
    'Aziende/Imprese': ['aziend', 'impres', 'confcommercio', 'confindustria', 'cna', 'confartigianato', 'camera di commercio', 'ordine professionale'],
    'Terzo Settore': ['associazion', 'onlus', 'volontariato', 'cooperativ', 'fondazione', 'terzo settore', 'caritas', 'croce rossa'],
    'Forze dell\'Ordine': ['polizia', 'carabinieri', 'guardia di finanza', 'questura', 'capitaneria'],
    'Cultura/Patrimonio': ['museo', 'biblioteca', 'teatro', 'fai', 'archivio', 'soprintendenza', 'conservatorio'],
    'Sport': ['coni', 'asd', 'federazione sportiva', 'polisportiva'],
    'Scuole/Reti': ['rete', 'scuol', 'istituto comprensivo', 'liceo', 'ambito territoriale'],
    'Famiglie': ['famigli', 'genitor', 'comitato genitori'],
    'Servizi Sociali': ['servizi sociali', 'tribunale minori', 'garante', 'comunità'],
}


class SynthesisSkeleton:
    """Manages the structure and data retrieval for the synthesis report using Hybrid Engine."""

    def __init__(
        self,
        base_dir: Path,
        filters: Optional[dict] = None,
        max_narrative_samples: int = 30,  # Keeping for backward compatibility but unused in DB mode
    ):
        self.base_dir = Path(base_dir)
        self.filters = filters or {}
        
        # Load stats from CSV anyway to provide quantitative context
        self.stats = {}
        self._load_csv_stats()
        
        self.db = DatabaseManager()
        
        # Lazy-load embeddings model (only needed for RAG retrieval)
        self._model = None
            
        self.narratives = [] # To satisfy interface
        
        # Load Cluster Summaries (Map-Reduce)
        self.cluster_summaries = self._load_cluster_summaries()
        self.cluster_assignments, self.cluster_stats = self._load_cluster_data()
        self.filtered_school_ids = self._load_filtered_school_ids()
        self.filtered_cluster_counts = self._compute_filtered_cluster_counts()

        # Populated during _build_dynamic_sampling_note(), used by get_slot_contexts()
        self.sampling_bias: Dict = {}
        self.quantitative_summary: Dict = {}
        self.filtered_df = None  # Set by _build_dynamic_sampling_note()
        self.methodology_frequencies: list = []  # Set by _build_methodology_frequency_analysis()
        self.territory_frequencies: list = []  # Set by _build_territory_frequency_analysis()
        self.territory_category_frequencies: list = []  # Set by _build_territory_frequency_analysis()

    @property
    def model(self):
        """Lazy-load SentenceTransformer only when needed for RAG retrieval."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading SentenceTransformer model...")
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("SentenceTransformer loaded.")
            except ImportError:
                logger.error("sentence-transformers not installed.")
        return self._model

    def _load_cluster_summaries(self) -> Dict:
        """Loads pre-computed cluster summaries."""
        path = self.base_dir / "data" / "cluster_summaries.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cluster summaries: {e}")
        else:
            logger.warning("Cluster summaries not found. Skipping Map-Reduce context.")
        return {}

    def _load_cluster_data(self) -> Tuple[Dict[str, str], Dict[str, dict]]:
        """Loads assignments and stats from data/clusters.json."""
        path = self.base_dir / "data" / "clusters.json"
        if not path.exists():
            return {}, {}

        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning("Failed to load clusters metadata: %s", e)
            return {}, {}

        raw_assignments = data.get("assignments", {})
        assignments: Dict[str, str] = {}
        for school_code, cluster_id in raw_assignments.items():
            assignments[str(school_code).strip().upper()] = str(cluster_id)

        raw_stats = data.get("metadata", {}).get("stats", {})
        cluster_stats: Dict[str, dict] = {}
        for key, value in raw_stats.items():
            skey = str(key)
            if isinstance(value, dict):
                cluster_stats[skey] = {
                    "count": value.get("count"),
                }
            else:
                cluster_stats[skey] = {"count": None}
        return assignments, cluster_stats

    def _load_filtered_school_ids(self) -> Set[str]:
        """Loads school IDs filtered exactly like the report scope."""
        path = self.base_dir / "data" / "analysis_summary.csv"
        if not path.exists():
            return set()

        try:
            df = pd.read_csv(path, usecols=[
                "school_id",
                "ordine_grado",
                "regione",
                "area_geografica",
                "tipo_scuola",
            ])
        except Exception:
            try:
                df = pd.read_csv(path)
            except Exception as e:
                logger.warning("Failed to load analysis_summary for cluster filtering: %s", e)
                return set()

        # Align filters with report scope
        if "ordine_grado" in self.filters and "ordine_grado" in df.columns:
            target = self.filters["ordine_grado"]
            if isinstance(target, list):
                df = df[df["ordine_grado"].isin(target)]
            else:
                df = df[df["ordine_grado"] == target]

        if "regione" in self.filters and "regione" in df.columns:
            df = df[df["regione"] == self.filters["regione"]]

        if "area_geografica" in self.filters and "area_geografica" in df.columns:
            df = df[df["area_geografica"] == self.filters["area_geografica"]]

        if "tipo_scuola" in self.filters and "tipo_scuola" in df.columns:
            df = df[df["tipo_scuola"] == self.filters["tipo_scuola"]]

        if "school_id" not in df.columns:
            return set()

        return set(
            df["school_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

    def _compute_filtered_cluster_counts(self) -> Dict[str, int]:
        """Computes cluster distribution within the current report filter scope."""
        if not self.cluster_assignments:
            return {}

        counts: Dict[str, int] = {}

        # If filters are active and no school IDs are available, keep distribution empty.
        if self.filters and not self.filtered_school_ids:
            return counts

        for school_code, cluster_id in self.cluster_assignments.items():
            if self.filtered_school_ids and school_code not in self.filtered_school_ids:
                continue
            counts[cluster_id] = counts.get(cluster_id, 0) + 1

        return counts

    def _active_cluster_keys(self) -> List[str]:
        """Returns cluster IDs relevant to the current report scope."""
        if self.filtered_cluster_counts:
            return sorted(self.filtered_cluster_counts.keys(), key=lambda x: int(x))
        if self.filters:
            return []
        if self.cluster_summaries:
            return sorted(self.cluster_summaries.keys(), key=lambda x: int(x))
        return sorted(self.cluster_stats.keys(), key=lambda x: int(x))

    @staticmethod
    def _compact_cluster_text(text: str, max_chars: int = 650) -> str:
        """Normalizes cluster summary text and truncates it for prompt efficiency."""
        if not text:
            return ""

        cleaned_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            cleaned_lines.append(stripped)

        compact = " ".join(cleaned_lines)
        if len(compact) > max_chars:
            return compact[: max_chars - 1].rstrip() + "…"
        return compact

    def _build_cluster_profiles_text(self) -> str:
        """Builds a cross-cluster profile text for the dedicated slot."""
        if not self.cluster_summaries:
            return "Nessuna sintesi per cluster disponibile."

        cluster_keys = self._active_cluster_keys()
        if not cluster_keys:
            return "Nessun cluster disponibile per i filtri correnti."

        lines = []
        for cluster_key in cluster_keys:
            summaries = self.cluster_summaries.get(cluster_key, {})
            cluster_count = self.filtered_cluster_counts.get(cluster_key)
            if cluster_count is None:
                cluster_count = self.cluster_stats.get(cluster_key, {}).get("count")
            cluster_name = summaries.get("_cluster_name", "")
            if cluster_name:
                label = f"{cluster_name} (Cluster {cluster_key})"
            else:
                label = f"CLUSTER {cluster_key}"
            if cluster_count:
                label += f" (n={cluster_count})"

            sintesi = self._compact_cluster_text(summaries.get("sintesi_generale", ""))
            lacune = self._compact_cluster_text(summaries.get("principali_lacune", ""))
            bilancio = self._compact_cluster_text(summaries.get("bilancio_complessivo", ""))

            parts = []
            if sintesi:
                parts.append(f"Profilo dominante: {sintesi}")
            if lacune:
                parts.append(f"Lacune ricorrenti: {lacune}")
            if bilancio:
                parts.append(f"Bilancio sintetico: {bilancio}")

            if parts:
                lines.append(f"{label}:\n" + "\n".join(parts))

        if not lines:
            return "Nessuna caratterizzazione cluster disponibile nei dati correnti."

        return "PROFILI CLUSTER (ANALISI PRELIMINARE):\n" + "\n\n".join(lines)

    def load_data(self):
        """Placeholder to satisfy interface. Stats are loaded in init."""
        pass

    def _load_csv_stats(self):
        """Loads aggregate stats from CSV to support the report."""
        csv_path = self.base_dir / "data" / "analysis_summary.csv"
        if not csv_path.exists():
            return
            
        try:
            df = pd.read_csv(csv_path)
             # Apply filters
            if "ordine_grado" in self.filters:
                target = self.filters["ordine_grado"]
                if isinstance(target, list):
                     df = df[df["ordine_grado"].isin(target)]
                else:
                     df = df[df["ordine_grado"] == target]

            if "regione" in self.filters:
                df = df[df["regione"] == self.filters["regione"]]
                
            self.stats["n_schools"] = len(df)
            
            # Helper for means
            score_stats = {}
            for col in df.columns:
                if "score" in col or "mean" in col:
                     try:
                        score_stats[col] = {
                            "mean": round(df[col].mean(), 2),
                            "std": round(df[col].std(), 2)
                        }
                     except: pass
            self.stats["score_stats"] = score_stats
            
        except Exception as e:
            logger.error(f"Error loading CSV stats: {e}")

    def generate_skeleton(self) -> str:
        """Generates the Markdown skeleton with [SLOT:xxx] placeholders."""
        
        # 1. Build Header & Methodology
        report = []
        target_degree = self.filters.get("ordine_grado", "Tutti i gradi")
        if isinstance(target_degree, list):
            target_degree = ", ".join(target_degree)

        title = f"Report di Sintesi sull'Orientamento nei PTOF — {target_degree}"
        report.append(f"# {title}\n")
             
        report.append(f"*Target Analisi: {target_degree}*\n")
        report.append(self._build_methodology_note())

        # Sezione dedicata ai profili cluster (esplicita le differenze tra gruppi)
        report.append(f"## {CLUSTER_PROFILE_SECTION['title']}\n")
        report.append(f"[SLOT:{CLUSTER_PROFILE_SECTION['key']}]\n")

        # 2. Build Sections
        for section in THEMATIC_SECTIONS:
            report.append(f"## {section['title']}\n")

            # Insert methodology frequency analysis before the narrative slot
            if section['key'] == 'metodologie_didattiche' and self.filtered_df is not None:
                freq_analysis = self._build_methodology_frequency_analysis(self.filtered_df)
                if freq_analysis:
                    report.append(freq_analysis)

            # Insert territory partner frequency analysis before the narrative slot
            if section['key'] == 'rapporto_territorio' and self.filtered_df is not None:
                territory_analysis = self._build_territory_frequency_analysis(self.filtered_df)
                if territory_analysis:
                    report.append(territory_analysis)

            report.append(f"[SLOT:{section['key']}]\n")

        return "\n".join(report)

    def _build_methodology_note(self) -> str:
        """Constructs the detailed methodology note with coherent logical flow.

        Structure:
        1. Premessa — what we measure (copertura informativa) and why
        2. Come funziona — the two analysis levels
        3. Framework — the 6 dimensions (all at uniform depth)
        4. Dal qualitativo al quantitativo — the scoring scale
        5. IIPO — the aggregate index
        6. Raggruppamento per Affinità — clustering approach
        7. Analisi del Campione — dynamic sampling stats
        """

        # ── 1. Premessa ──────────────────────────────────────────────────────
        premessa = (
            "## Premessa: Cosa Misuriamo e Perché\n\n"
            "Questo report analizza i **PTOF** (Piani Triennali dell'Offerta Formativa) delle scuole italiane "
            "per misurarne la **copertura informativa** in tema di orientamento: quanto e come il documento "
            "descrive le pratiche, i progetti e le strategie che la scuola adotta per orientare gli studenti.\n\n"
            "È importante chiarire fin da subito un principio fondamentale: **i punteggi che seguono non "
            "esprimono un giudizio sulla qualità della scuola**, ma sulla ricchezza e completezza della "
            "documentazione contenuta nel PTOF. Una scuola con un punteggio basso potrebbe svolgere "
            "ottime attività di orientamento senza averle descritte nel proprio piano; viceversa, un "
            "punteggio alto indica che il PTOF documenta in modo dettagliato e strutturato le proprie "
            "pratiche orientative.\n\n"
        )

        # ── 2. Come funziona l'analisi ───────────────────────────────────────
        come_funziona = (
            "## Come Funziona l'Analisi\n\n"
            "L'analisi automatizzata legge e interpreta il testo del PTOF su due livelli complementari.\n\n"
            "1. **Analisi Strutturale (Compliance)**: Il sistema verifica la conformità formale rispetto "
            "alle Linee Guida per l'orientamento scolastico stabilite dal D.M. 328/2022, il decreto "
            "ministeriale che ha introdotto l'obbligo per ogni scuola di dedicare almeno 30 ore annuali "
            "a moduli di orientamento formativo e di individuare figure dedicate (tutor e docente "
            "orientatore). In concreto, si verifica se il PTOF contiene una sezione esplicitamente "
            "dedicata all'orientamento, valutandone la visibilità e la struttura nel documento.\n\n"
            "2. **Analisi Semantica e di Contenuto**: Attraverso modelli di linguaggio avanzati (LLM), "
            "l'analisi \"legge\" l'intero documento per estrarre informazioni sulla copertura delle "
            "6 dimensioni del framework di valutazione (descritte nella sezione successiva). "
            "In questa fase, vengono distinte le semplici dichiarazioni di intenti dalle azioni concrete, "
            "mappando la presenza di progetti, risorse, tempi e responsabilità. L'algoritmo rileva "
            "il contesto in cui appaiono i termini: ad esempio, distingue se l'orientamento è citato "
            "in una lista generica oppure se è descritto attraverso laboratori con obiettivi specifici "
            "e modalità di verifica.\n\n"
        )

        # ── 3. Framework: le 6 Dimensioni ────────────────────────────────────
        framework = (
            "## Le 6 Dimensioni del Framework di Valutazione\n\n"
            "L'analisi semantica valuta la copertura del PTOF attraverso **6 dimensioni**. "
            "Ognuna rappresenta un aspetto fondamentale dell'orientamento scolastico: dalla struttura "
            "organizzativa alle finalità educative, dalle metodologie didattiche alle opportunità offerte "
            "agli studenti. Di seguito, ciascuna dimensione è descritta con i propri sotto-indicatori.\n\n"

            "### Dimensione Strutturale e di Contesto\n"
            "Valuta se l'orientamento ha una collocazione riconoscibile all'interno del PTOF e se la scuola "
            "è inserita in un tessuto di relazioni territoriali.\n"
            "- **Sezione dedicata**: Presenza di un capitolo o paragrafo esplicitamente intitolato all'orientamento, non frammentato tra diverse parti del documento.\n"
            "- **Partnership e reti territoriali**: Qualità del coinvolgimento di soggetti esterni (Università, ITS, imprese, Terzo Settore), con attenzione ad attività congiunte e accordi formali.\n\n"

            "### Finalità dell'Orientamento\n"
            "Analizza gli obiettivi formativi che la scuola si pone attraverso le attività di orientamento.\n"
            "- **Attitudini e Talenti**: Azioni per aiutare gli studenti a scoprire i propri punti di forza e inclinazioni personali.\n"
            "- **Interessi Professionali**: Percorsi di esplorazione degli ambiti disciplinari e del mondo del lavoro.\n"
            "- **Progetto di Vita**: Supporto alla costruzione di una traiettoria personale di lungo termine.\n"
            "- **Transizioni Formative**: Accompagnamento nei passaggi critici tra cicli scolastici (primaria-secondaria, secondaria-università/lavoro).\n"
            "- **Capacità Orientativa (Empowerment)**: Sviluppo di competenze trasversali che rendano lo studente autonomo nelle proprie scelte.\n\n"

            "### Obiettivi di Incidenza\n"
            "Misura l'attenzione del PTOF verso gli impatti sociali dell'orientamento.\n"
            "- **Contrasto alla Dispersione**: Strategie di prevenzione dell'abbandono scolastico e iniziative di rimotivazione.\n"
            "- **Riduzione dei NEET**: Azioni di collegamento scuola-lavoro per favorire l'occupabilità e contrastare il fenomeno dei giovani che non studiano né lavorano.\n"
            "- **Continuità Territoriale**: Costruzione di ponti tra i diversi gradi di istruzione presenti sul territorio.\n"
            "- **Lifelong Learning**: Concezione dell'orientamento come competenza permanente, utile per tutta la vita.\n\n"

            "### Governance e Organizzazione\n"
            "Esamina il modello organizzativo interno: chi fa cosa e come si coordina l'azione orientativa.\n"
            "- **Coordinamento**: Presenza di figure dedicate come Funzioni Strumentali, referenti o commissioni per l'orientamento.\n"
            "- **Dialogo Interno**: Coinvolgimento dei Consigli di Classe e dei docenti nella progettazione orientativa.\n"
            "- **Alleanza con le Famiglie**: Iniziative strutturate di comunicazione e collaborazione con i genitori.\n"
            "- **Monitoraggio**: Utilizzo di strumenti di feedback, questionari e dati per valutare l'efficacia delle azioni.\n"
            "- **Inclusione**: Attenzione specifica a studenti con BES/DSA, studenti stranieri e situazioni di fragilità.\n\n"

            "### Didattica Orientativa\n"
            "Valuta il passaggio dalle dichiarazioni di principio alle pratiche concrete in aula.\n"
            "- **Didattica Laboratoriale ed Esperienziale**: Attività basate sul *learning by doing* e sull'apprendimento attivo.\n"
            "- **Centralità dello Studente**: Ruolo attivo degli studenti nella co-progettazione dei percorsi orientativi.\n"
            "- **Interdisciplinarità**: Integrazione dell'orientamento nelle diverse discipline curricolari, non solo come attività aggiuntiva.\n"
            "- **Flessibilità Organizzativa**: Adattamento di spazi, tempi e gruppi per favorire esperienze orientative efficaci.\n\n"

            "### Opportunità Formative\n"
            "Mappa l'ecosistema delle proposte extracurricolari e integrative offerte dalla scuola.\n"
            "- **Attività Culturali e Artistiche**: Progetti di teatro, musica, scrittura creativa, visite a musei.\n"
            "- **Laboratori Espressivi**: Percorsi manuali, artigianali o digitali che favoriscono la scoperta di talenti.\n"
            "- **Sport e Attività Ricreative**: Offerta sportiva e ludica come strumento di socializzazione e benessere.\n"
            "- **Volontariato e Service Learning**: Esperienze di impegno civico che collegano apprendimento e comunità.\n\n"
        )

        # ── 4. Dal qualitativo al quantitativo: la Scala ─────────────────────
        scala = (
            "## Dal Qualitativo al Quantitativo: la Scala di Punteggio\n\n"
            "Ciascuna delle 6 dimensioni appena descritte viene valutata attraverso una **scala numerica "
            "da 1 a 7**, detta scala di copertura informativa. Si tratta di una scala ordinale di tipo "
            "Likert — uno strumento consolidato nella ricerca sociale che consente di tradurre "
            "valutazioni qualitative in punteggi confrontabili.\n\n"
            "Il punteggio riflette il livello di dettaglio con cui il PTOF documenta le pratiche "
            "orientative per quella dimensione: da 1 (nessun riferimento) a 7 (documentazione "
            "sistematica con evidenze di miglioramento continuo). La tabella seguente descrive "
            "ogni livello.\n\n"
            r"\begin{tabularx}{\textwidth}{@{} c l X @{}}" + "\n"
            r"\toprule" + "\n"
            r"\textbf{Punti} & \textbf{Livello} & \textbf{Cosa significa} \\" + "\n"
            r"\midrule" + "\n"
            r"1 & Assente & Nessun riferimento all'orientamento nel documento. \\" + "\n"
            r"2 & Traccia minima & Menzione vaga o copia-incolla di testo normativo, senza personalizzazione. \\" + "\n"
            r"3 & Parziale & Intenzione dichiarata, ma senza dettagli su come viene attuata. \\" + "\n"
            r"4 & Di base & Azioni descritte in modo chiaro ma essenziale, senza approfondimento. \\" + "\n"
            r"5 & Strutturata & Azioni dettagliate con metodologie esplicitate e risorse indicate. \\" + "\n"
            r"6 & Approfondita & Azioni integrate nel curricolo, con indicatori di monitoraggio documentati. \\" + "\n"
            r"7 & Esaustiva & Documentazione sistematica e ciclica, con evidenze di revisione e miglioramento. \\" + "\n"
            r"\bottomrule" + "\n"
            r"\end{tabularx}" + "\n\n"
        )

        # ── 5. IIPO ──────────────────────────────────────────────────────────
        iipo = (
            "## L'Indice Sintetico: IIPO\n\n"
            "Per avere una visione d'insieme della copertura documentale di ciascuna scuola, i punteggi "
            "delle 6 dimensioni vengono riassunti in un unico indicatore: l'**IIPO** (Indice di "
            "Documentazione delle Pratiche di Orientamento).\n\n"
            "L'IIPO è calcolato come **media aritmetica semplice** dei punteggi delle 6 dimensioni "
            "(Strutturale, Finalità, Obiettivi, Governance, Didattica, Opportunità). "
            "Si è scelta una media non pesata per evitare di privilegiare a priori una dimensione "
            "rispetto alle altre, trattandole tutte come ugualmente rilevanti.\n\n"
            "**Come leggere l'IIPO:**\n"
            "- Un IIPO di **5.0** indica che, in media, il PTOF documenta le pratiche orientative "
            "a un livello \"Strutturato\" su tutte le dimensioni.\n"
            "- Un IIPO di **3.0** segnala una documentazione complessivamente \"Parziale\".\n\n"
            "**Limiti da tenere presenti:**\n"
            "- *Effetto compensazione*: Essendo una media, l'IIPO può mascherare squilibri tra le dimensioni. "
            "Ad esempio, una scuola con punteggio 7 su Didattica e 1 su Governance otterrebbe un IIPO "
            "apparentemente nella norma. Per questo motivo, l'IIPO va sempre letto insieme ai "
            "punteggi delle singole dimensioni.\n"
            "- *Sensibilità incrementale*: La scala a 7 livelli consente di cogliere differenze graduali "
            "tra scuole, evitando la polarizzazione tipica delle scale più strette (es. 1-3).\n\n"
        )

        # ── 6. Raggruppamento per Affinità ───────────────────────────────────
        n_clusters = len(self.cluster_summaries) if self.cluster_summaries else 0
        clustering_note = (
            "## Approccio Analitico: Raggruppamento per Affinità\n\n"
            "Oltre all'analisi dimensionale, il report utilizza una tecnica di **raggruppamento "
            "automatico** (clustering) per evitare di appiattire i risultati su una semplice media "
            "nazionale.\n\n"
            "Il funzionamento è il seguente: il sistema analizza i profili di punteggio di tutte "
            "le scuole e individua **gruppi di istituti** che presentano caratteristiche documentali "
            f"simili. Nel campione corrente sono stati identificati **{n_clusters} gruppi omogenei** — "
            "ad esempio, un gruppo potrebbe riunire scuole con forte attenzione ai PCTO e alle "
            "partnership territoriali, mentre un altro potrebbe raccogliere istituti che privilegiano "
            "la didattica laboratoriale.\n\n"
            "Per ciascun gruppo viene generata una **sintesi tematica** che descrive l'approccio "
            "dominante su ogni dimensione. A ogni cluster viene inoltre assegnato un **nome rappresentativo** "
            "(ad esempio *\"Orientamento frammentario e implicito\"* o *\"Forte integrazione territoriale\"*), "
            "generato automaticamente a partire dalla sintesi del profilo dominante, per facilitare "
            "la lettura e il riferimento nel testo. Queste sintesi intermedie vengono poi integrate nel "
            "report finale, permettendo di confrontare i diversi \"profili di orientamento\" e di "
            "evidenziare sia le tendenze comuni sia le eccezioni virtuose.\n\n"
        )

        # ── 7. Strategia di Generazione del Report ────────────────────────────
        prompting_note = (
            "## Strategia di Generazione del Report\n\n"
            "La redazione di questo report è affidata a un sistema di intelligenza artificiale "
            "che opera attraverso un processo strutturato in **tre fasi**, progettato per garantire "
            "coerenza, accuratezza e aderenza ai dati.\n\n"

            "### Fase 1: Costruzione dello Scheletro\n"
            "Il sistema genera automaticamente la struttura del report — titolo, sezioni tematiche, "
            "nota metodologica, grafici e tabelle — senza coinvolgere il modello linguistico. "
            "Questa fase è puramente deterministica: calcola statistiche aggregate, produce "
            "visualizzazioni e predispone i segnaposto (*slot*) che verranno riempiti nella fase "
            "successiva.\n\n"

            "### Fase 2: Compilazione Narrativa (Slot Filling)\n"
            "Per ogni sezione tematica, il modello linguistico riceve un **prompt specifico** che include:\n\n"
            "- **Istruzioni di ruolo**: il sistema si presenta come analista esperto del sistema scolastico "
            "italiano, con conoscenza approfondita della normativa sull'orientamento (D.M. 328/2022, "
            "Linee Guida MIM).\n"
            "- **Contesto normativo per grado**: informazioni specifiche sulla fascia d'età, sugli obblighi "
            "normativi e sulle pratiche appropriate per il grado scolastico oggetto del report "
            "(I Grado o II Grado), per evitare contaminazioni tra gradi.\n"
            "- **Dati aggregati**: statistiche calcolate dal campione (medie, deviazioni standard, "
            "distribuzione dei punteggi per dimensione).\n"
            "- **Sintesi per cluster**: i profili tematici pre-generati per ciascun gruppo omogeneo.\n"
            "- **Evidenze testuali (RAG ibrido)**: estratti reali dai PTOF recuperati attraverso un sistema "
            "di *Retrieval-Augmented Generation* a doppio livello — sintesi analitiche per il quadro "
            "d'insieme e citazioni dirette dai documenti originali per ancorare le affermazioni.\n\n"
            "Ogni prompt tematico è stato progettato con una **struttura analitica vincolante** "
            "(punti da trattare, domande guida, vincoli stilistici e contenuti da evitare) per "
            "ottenere testi omogenei, comparabili tra sezioni e privi di generalizzazioni non "
            "supportate dai dati.\n\n"

            "### Contenuto dei Prompt Tematici\n\n"
            "Di seguito si descrive *cosa* viene richiesto al modello in ciascuna sezione e *perché* "
            "quella prospettiva analitica è stata scelta.\n\n"
            "- **Profili dei Cluster**: il modello deve descrivere ciascun gruppo di scuole evidenziandone "
            "il tratto dominante, le dimensioni forti e deboli e le differenze rispetto agli altri gruppi. "
            "L'obiettivo è offrire al lettore una mappa tipologica, non una classifica.\n"
            "- **Sintesi Generale**: viene richiesta una panoramica trasversale guidata da domande chiave — "
            "l'orientamento è scelta strategica o adempimento burocratico? È integrato nella didattica "
            "o confinato in attività separate? Lo studente è soggetto attivo o destinatario passivo? — "
            "per evitare descrizioni superficiali e stimolare un'analisi critica.\n"
            "- **Allineamento Normativo**: il prompt vincola il modello a distinguere tra recepimento "
            "formale (la norma è citata) e sostanziale (i principi sono tradotti in azioni), con "
            "attenzione ai moduli obbligatori da 30 ore e alle figure di tutor e orientatore.\n"
            "- **Rapporto con il Territorio**: si chiede di analizzare le reti di partnership usando i dati "
            "di frequenza dei partner (grafici e tabelle), classificandole per tipologia e verificando "
            "se le collaborazioni sono operative o solo formali.\n"
            "- **Metodologie Didattiche**: il prompt è costruito attorno al principio che l'orientamento "
            "è di per sé un atto didattico. La domanda centrale è se le scuole lo integrano nel "
            "curricolo quotidiano o lo confinano in progetti separati. Si chiede anche di verificare "
            "se la didattica attiva documentata è autentica (con prodotti e valutazione) o solo dichiarata.\n"
            "- **Strumenti di Supporto**: il modello deve distinguere tra test psicodiagnostici "
            "(che fotografano attitudini) e questionari riflessivi (che stimolano autoesplorazione), "
            "verificando se gli strumenti promuovono l'auto-direzione dello studente o lo relegano "
            "a destinatario passivo di profili.\n"
            "- **Formazione del Personale**: si chiede esplicitamente di verificare se nei PTOF compare "
            "formazione *specifica* sull'orientamento — non solo su altri temi — e se la preparazione "
            "dei tutor è documentata o la funzione è assegnata senza training.\n"
            "- **Figure Professionali e Governance**: il focus è sull'organigramma orientativo — se esiste "
            "un team dedicato, come si raccorda con i Consigli di Classe, e se il piano annuale "
            "dell'orientamento ha tempi, azioni e responsabilità concrete.\n"
            "- **Principali Lacune**: il prompt richiede un'analisi diretta e senza diplomazia dei gap, "
            "con attenzione allo scarto tra dichiarazioni e azioni, all'assenza di monitoraggio "
            "dell'efficacia, e a temi sistematicamente ignorati (bias di genere, stereotipi, "
            "empowerment studentesco).\n"
            "- **Temi Globali e Scelte Consapevoli**: il modello è guidato dal principio che le scelte "
            "orientative non sono mai solo individuali. Si chiede di verificare se i PTOF integrano "
            "responsabilità sociale, sostenibilità ambientale e dignità della persona nelle scelte "
            "formative, o se l'orientamento si riduce alla scelta del percorso successivo.\n"
            "- **Bilancio Complessivo**: il prompt vincola a una selezione — massimo 3 punti di forza "
            "e 3 criticità, con direzioni di sviluppo basate su ciò che le scuole migliori già fanno, "
            "non su desideri astratti.\n"
            "- **Conclusioni e Limiti**: il capitolo finale richiede una sintesi dei risultati principali "
            "seguita da una discussione trasparente dei limiti metodologici — dalla distanza tra "
            "documento e pratica reale, ai limiti dell'analisi automatizzata, alla rappresentatività "
            "campionaria — con avvertenze concrete per il lettore su come utilizzare il report.\n\n"
            "Questa architettura di prompt è stata progettata per garantire che ogni sezione adotti "
            "una **lente analitica specifica** e coerente con il framework pedagogico di riferimento, "
            "evitando sia le generalizzazioni sia le descrizioni puramente quantitative.\n\n"

            "### Fase 3: Revisione di Coerenza\n"
            "Un passaggio finale di revisione automatica verifica ogni sezione del report per "
            "individuare e correggere: ripetizioni tra sezioni, incongruenze numeriche, errori "
            "nelle etichette della scala, refusi grammaticali e contaminazioni tra gradi scolastici.\n\n"

            "### Perché questa strategia\n"
            "La scelta di un processo a tre fasi separate risponde a tre esigenze:\n\n"
            "1. **Grounding sui dati**: il modello linguistico non inventa contenuti, ma elabora "
            "narrazioni a partire da dati quantitativi ed evidenze testuali reali.\n"
            "2. **Specificità tematica**: ogni sezione riceve un prompt dedicato con istruzioni "
            "e dati pertinenti, evitando che il modello perda il focus su un documento troppo lungo.\n"
            "3. **Controllo qualità**: la revisione finale agisce come filtro automatico per "
            "garantire coerenza interna e accuratezza.\n\n"
        )

        # ── 8. Analisi del Campione (dinamica) ───────────────────────────────
        sampling_note = self._build_dynamic_sampling_note()

        return premessa + come_funziona + framework + scala + iipo + clustering_note + prompting_note + sampling_note

    def _build_dynamic_sampling_note(self) -> str:
        """Generates the Sampling Analysis section using real data and benchmarks."""
        try:
            import pandas as pd
            # Load analysis summary safely within the method to avoid init overhead
            path = self.base_dir / "data" / "analysis_summary.csv"
            if not path.exists():
                logger.warning(f"Analysis summary not found at {path}")
                return "\n\n## Analisi del Campione\nDati non disponibili (file sorgente mancante)."
                
            df = pd.read_csv(path)

            # Filtra per il grado corrente
            grade_filter = self.filters.get("ordine_grado")
            if grade_filter:
                if isinstance(grade_filter, list):
                    df = df[df['ordine_grado'].isin(grade_filter)]
                else:
                    df = df[df['ordine_grado'] == grade_filter]

            # Store filtered df for reuse in generate_skeleton
            self.filtered_df = df

            n_obs = len(df)
            provinces = df['provincia'].nunique() if 'provincia' in df.columns else "N/D"
            regions = df['regione'].nunique() if 'regione' in df.columns else "N/D"
            
            # BENCHMARKS (Hardcoded from user provided data for II Grado)
            # Default to generic if not II Grado
            benchmarks_geo = {
                "Nord Ovest": 26.6,
                "Nord Est": 19.3,
                "Centro": 19.9,
                "Sud": 23.3,
                "Isole": 10.9
            }
            # Benchmark Gestione Statale (II Grado specific: 92%)
            benchmark_statale = 92.0 
            
            # 1. Statale vs Paritaria
            note_gest = "Dati gestione non disponibili"
            if 'statale_paritaria' in df.columns:
                counts_gest = df['statale_paritaria'].value_counts()
                p_paritaria = (counts_gest.get('Paritaria', 0) / n_obs * 100) if n_obs > 0 else 0
                p_statale = 100 - p_paritaria
                
                diff_statale = p_statale - benchmark_statale
                dev_sign = "+" if diff_statale > 0 else ""
                
                note_gest = (
                    r"\begin{tabularx}{\textwidth}{@{} p{3cm} c c c @{}}" + "\n"
                    r"\toprule" + "\n"
                    r"\textbf{Tipo} & \textbf{Osservato \%} & \textbf{Atteso \% (MIUR)} & \textbf{Deviazione} \\" + "\n"
                    r"\midrule" + "\n"
                    f"Statale & {p_statale:.1f}\\% & {benchmark_statale}\\% & {dev_sign}{diff_statale:.1f} pp \\\\\n"
                    f"Paritaria & {p_paritaria:.1f}\\% & {100-benchmark_statale}\\% & {('-' if diff_statale > 0 else '+')}{abs(diff_statale):.1f} pp \\\\\n"
                    r"\bottomrule" + "\n"
                    r"\end{tabularx}"
                )

            # Store gestione bias
            if 'statale_paritaria' in df.columns:
                self.sampling_bias['dev_statale_pp'] = round(diff_statale, 1)
                self.sampling_bias['pct_paritaria_obs'] = round(p_paritaria, 1)
                self.sampling_bias['pct_paritaria_exp'] = round(100 - benchmark_statale, 1)

            # 2. Macro Aree
            geo_table = ""
            commentary = ""
            if 'area_geografica' in df.columns:
                counts_geo = df['area_geografica'].value_counts(normalize=True) * 100
                
                geo_rows = ""
                max_dev = 0
                
                for area, expected in benchmarks_geo.items():
                    observed = counts_geo.get(area, 0.0)
                    diff = observed - expected
                    dev_sign = "+" if diff > 0 else ""
                    geo_rows += f"{area} & {observed:.1f}\\% & {expected}\\% & {dev_sign}{diff:.1f} pp \\\\\n"
                    if abs(diff) > max_dev:
                        max_dev = abs(diff)
                
                geo_table = (
                    r"\begin{tabularx}{\textwidth}{@{} X c c c @{}}" + "\n"
                    r"\toprule" + "\n"
                    r"\textbf{Area} & \textbf{Osservato \%} & \textbf{Atteso \% (MIUR)} & \textbf{Deviazione} \\" + "\n"
                    r"\midrule" + "\n"
                    f"{geo_rows}"
                    r"\bottomrule" + "\n"
                    r"\end{tabularx}"
                )
                
                if max_dev < 5:
                    commentary = "\n✅ **Campione Rappresentativo**: Le deviazioni rispetto all'atteso sono minime (< 5 pp), garantendo un'ottima affidabilità statistica."
                elif max_dev < 15:
                    commentary = "\n⚠️ **Campione con Lievi Disallineamenti**: Si notano alcune sovra/sottorappresentazioni geografiche, che tuttavia non invalidano l'analisi complessiva (deviazione max < 15 pp)."
                else:
                    commentary = "\n⚠️ **Nota sulla Rappresentatività**: Il campione presenta significative deviazioni rispetto alla distribuzione attesa, in particolare per alcune macro-aree (es. Sud/Nord)."

                # Store geo deviations for bias tracking
                geo_deviations = {}
                for area, expected in benchmarks_geo.items():
                    observed = counts_geo.get(area, 0.0)
                    geo_deviations[area] = round(observed - expected, 1)
                self.sampling_bias['geo_deviations'] = geo_deviations
                self.sampling_bias['geo_max_dev'] = round(max_dev, 1)

            # 3. Metro vs Non Metro
            METRO_PROVINCES = [
                'Roma', 'Milano', 'Napoli', 'Torino', 'Palermo', 
                'Bari', 'Catania', 'Firenze', 'Bologna', 'Genova', 
                'Venezia', 'Messina', 'Reggio Calabria', 'Cagliari'
            ]
            
            note_metro = "Dati territoriali non disponibili"
            if 'provincia' in df.columns:
                df['is_metro'] = df['provincia'].isin(METRO_PROVINCES)
                counts_metro = df['is_metro'].value_counts(normalize=True) * 100
                
                obs_metro = counts_metro.get(True, 0)
                obs_non_metro = counts_metro.get(False, 0)
                
                # Benchmark: ~33% Metro, 67% Non Metro (Stima popolazione/scuole)
                exp_metro = 33.0
                diff_metro = obs_metro - exp_metro
                dev_sign = "+" if diff_metro > 0 else ""
                
                note_metro = (
                    r"\begin{tabularx}{\textwidth}{@{} X c c c @{}}" + "\n"
                    r"\toprule" + "\n"
                    r"\textbf{Area} & \textbf{Osservato \%} & \textbf{Atteso \% (Stima)} & \textbf{Deviazione} \\" + "\n"
                    r"\midrule" + "\n"
                    f"Metropolitana & {obs_metro:.1f}\\% & {exp_metro:.1f}\\% & {dev_sign}{diff_metro:.1f} pp \\\\\n"
                    f"Non Metropolitana & {obs_non_metro:.1f}\\% & {100-exp_metro:.1f}\\% & {('-' if diff_metro > 0 else '+')}{abs(diff_metro):.1f} pp \\\\\n"
                    r"\bottomrule" + "\n"
                    r"\end{tabularx}"
                )

                # Store metro bias
                self.sampling_bias['dev_metro_pp'] = round(diff_metro, 1)
                self.sampling_bias['pct_metro_obs'] = round(obs_metro, 1)

            # Store general stats for bias tracking
            self.sampling_bias['n_obs'] = n_obs
            self.sampling_bias['n_provinces'] = provinces
            self.sampling_bias['n_regions'] = regions
            self.sampling_bias['grade_filter'] = grade_filter

            # ── Build representativeness assessment ──────────────────────
            # Coverage ratio for regions
            region_coverage_pct = (regions / 20 * 100) if isinstance(regions, (int, float)) else 0
            if region_coverage_pct >= 90:
                region_assessment = "Il campione copre la quasi totalità delle regioni italiane, garantendo una visione nazionale."
            elif region_coverage_pct >= 75:
                region_assessment = "Il campione copre la maggior parte delle regioni italiane, con alcune lacune marginali."
            else:
                region_assessment = "Il campione presenta lacune nella copertura regionale che possono limitare la generalizzabilità dei risultati."

            return (
                f"## Analisi e Copertura del Campione ({grade_filter})\n\n"
                "Questa sezione descrive la composizione del campione analizzato e ne valuta la **rappresentatività** "
                "rispetto all'universo delle scuole italiane. Comprendere la struttura del campione è essenziale "
                "per interpretare correttamente i risultati: un campione ben bilanciato consente di generalizzare "
                "le osservazioni; un campione sbilanciato richiede cautela nell'estendere le conclusioni a tutto "
                "il sistema scolastico.\n\n"
                "Per ogni dimensione di confronto (gestione, area geografica, contesto territoriale) la tabella "
                "riporta tre valori:\n"
                "- **Osservato %**: la percentuale nel nostro campione.\n"
                "- **Atteso % (MIUR)**: la percentuale nell'universo reale delle scuole italiane, ricavata dai dati ministeriali.\n"
                "- **Deviazione (pp)**: la differenza tra osservato e atteso, espressa in *punti percentuali*. "
                "Deviazioni entro ±5 pp sono trascurabili; tra 5 e 15 pp segnalano un lieve squilibrio; "
                "oltre 15 pp indicano una sovra- o sotto-rappresentazione significativa.\n\n"

                f"### Statistiche Generali\n\n"
                f"- **Scuole Analizzate**: **{n_obs}** PTOF di scuole {grade_filter}\n"
                f"- **Province Coperte**: {provinces} (su 107 totali)\n"
                f"- **Regioni Coperte**: {regions}/20\n\n"
                f"{region_assessment}\n\n"

                f"### Bilanciamento Gestione (Statale vs Paritaria)\n\n"
                "In Italia, le scuole statali rappresentano la grande maggioranza degli istituti. "
                "Un campione rappresentativo dovrebbe riflettere questa proporzione. "
                "Una sovra-rappresentazione delle paritarie, ad esempio, potrebbe influenzare i risultati "
                "perché i PTOF delle scuole paritarie tendono ad avere strutture e contenuti diversi "
                "da quelli delle statali.\n\n"
                f"{note_gest}\n\n"

                f"### Distribuzione Geografica per Macro-Area\n\n"
                "L'Italia presenta significative differenze territoriali nell'offerta formativa. "
                "Per valutare se il campione rispecchia la distribuzione reale delle scuole, "
                "confrontiamo le cinque macro-aree geografiche (Nord Ovest, Nord Est, Centro, Sud, Isole) "
                "con i dati MIUR. Una buona rappresentatività geografica è fondamentale perché "
                "le pratiche di orientamento possono variare sensibilmente tra Nord e Sud, "
                "tra aree urbane e rurali.\n\n"
                f"{geo_table}\n\n"
                f"{commentary}\n\n"

                f"### Distribuzione Territoriale (Aree Metropolitane vs Non Metropolitane)\n\n"
                "Le scuole situate nelle 14 città metropolitane italiane operano in contesti diversi "
                "rispetto a quelle di provincia: maggiore offerta formativa esterna, più partnership "
                "con università e imprese, ma anche maggiore competizione tra istituti. "
                "Questa distinzione aiuta a capire se i risultati del report sono influenzati "
                "da una prevalenza di scuole urbane o rurali nel campione.\n\n"
                f"{note_metro}\n\n"

                f"### Implicazioni per la Lettura del Report\n\n"
                "[SLOT:implicazioni_campionamento]\n\n"
                "\\newpage\n\n"
                f"{self._build_quantitative_dimensions_summary(df)}"
            )

        except Exception as e:
            logger.error(f"Error building dynamic sampling note: {e}")
            return f"\n\n## 6. Analisi del Campione\nErrore durante la generazione: {str(e)}"


    def _generate_dimension_bar_chart(self, dimension_name, sub_data, compact=False) -> str:
        """Generates a colored horizontal bar chart for sub-indicators.

        Args:
            dimension_name: Label for the dimension.
            sub_data: List of (label, value) tuples.
            compact: If True, generates a smaller chart suitable for grid layout.
        """
        if not sub_data:
            return None

        try:
            labels = [x[0] for x in sub_data]
            values = [x[1] for x in sub_data]

            if compact:
                fig, ax = plt.subplots(figsize=(5.5, 0.35 * len(labels) + 1.0))
                label_fontsize = 8
                value_fontsize = 7
                title_fontsize = 9
                bar_height = 0.38
                xlabel_fontsize = 8
            else:
                fig, ax = plt.subplots(figsize=(7, 0.45 * len(labels) + 1.2))
                label_fontsize = 10
                value_fontsize = 9
                title_fontsize = 12
                bar_height = 0.45
                xlabel_fontsize = 10

            y_pos = np.arange(len(labels))

            # Colors: Red (<3.5), Yellow (3.5-5), Green (>=5)
            colors = []
            for v in values:
                if v >= 5.0: colors.append('#2ecc71') # Green
                elif v >= 3.5: colors.append('#f1c40f') # Yellow
                else: colors.append('#e74c3c') # Red

            ax.barh(y_pos, values, align='center', color=colors, height=bar_height)

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=label_fontsize)
            ax.invert_yaxis()  # labels read top-to-bottom
            ax.set_xlabel('Punteggio Medio (1-7)', fontsize=xlabel_fontsize)
            ax.set_xlim(0, 7.5)
            ax.set_title(f"{dimension_name}", loc='left', pad=6, fontsize=title_fontsize, fontweight='bold')

            # Remove spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Add value labels
            for i, v in enumerate(values):
                ax.text(v + 0.1, i, f"{v:.2f}", color='black', va='center', fontweight='bold', fontsize=value_fontsize)

            # Save
            output_dir = self.base_dir / "reports" / "synthesis" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_name = dimension_name.replace(" ", "_").replace("'", "").lower()
            # Remove accented/special chars that break LaTeX file paths
            import unicodedata
            safe_name = unicodedata.normalize('NFKD', safe_name).encode('ascii', 'ignore').decode('ascii')
            safe_name = re.sub(r'[^a-z0-9_]', '', safe_name)
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            suffix = "_compact" if compact else ""
            filename = f"bar_{safe_name}{suffix}_{timestamp}.png"
            output_path = output_dir / filename

            plt.tight_layout()
            plt.savefig(output_path, dpi=180 if compact else 150)
            plt.close()

            return f"images/{filename}"

        except Exception as e:
            logger.error(f"Error generating bar chart for {dimension_name}: {e}")
            return None

        """Generates a radar chart for the 6 dimensions and returns the image path."""
        try:
            # 1. Prepare Data
            categories = [
                'Strutturale', 'Finalità', 'Obiettivi', 
                'Governance', 'Didattica', 'Opportunità'
            ]
            keys = [
                '2_1_score', 'mean_finalita', 'mean_obiettivi', 
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita'
            ]
            
            # Calculate means, default to 0 if missing
            values = []
            for k in keys:
                if k in df.columns:
                    values.append(df[k].mean())
                else:
                    values.append(0.0)
            
            # Close the loop for radar chart
            values += values[:1]
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]
            
            # 2. Setup Plot
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
            
            # Draw one axe per variable + add labels
            plt.xticks(angles[:-1], categories, color='grey', size=10)
            
            # Draw ylabels
            ax.set_rlabel_position(0)
            plt.yticks([1, 2, 3, 4, 5, 6, 7], ["1", "2", "3", "4", "5", "6", "7"], color="grey", size=7)
            plt.ylim(0, 7)
            
            # Plot data
            ax.plot(angles, values, linewidth=2, linestyle='solid', color='#1f77b4')
            ax.fill(angles, values, '#1f77b4', alpha=0.25)
            
            # Add Title
            grade = self.filters.get("ordine_grado", "Generale")
            if isinstance(grade, list): grade = "Generale"
            plt.title(f'Profilo Dimensionale Orientamento - {grade}', size=14, color='#1f77b4', y=1.1)
            
            # 3. Save Image
            output_dir = self.base_dir / "reports" / "synthesis" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"radar_chart_{timestamp}.png"
            output_path = output_dir / filename
            
            plt.savefig(output_path, bbox_inches='tight', dpi=100)
            plt.close()
            
            # Return relative path for Markdown
            return f"images/{filename}"
            
        except Exception as e:
            logger.error(f"Error generating radar chart: {e}")
            return None

    def _build_quantitative_dimensions_summary(self, df) -> str:
        """Generates detailed summary tables and charts for each dimension.

        Layout: all tables first, then all 5 bar charts on a single page
        arranged in a 3+2 grid using LaTeX minipage.
        """
        try:

            # === MAPPING DIMENSIONI (Ordine Logico) ===
            DIMENSIONS_ORDER = [
                ('Finalita', 'Finalità dell\'Orientamento', 'mean_finalita'),
                ('Obiettivi', 'Obiettivi di Incidenza', 'mean_obiettivi'),
                ('Governance', 'Governance e Organizzazione', 'mean_governance'),
                ('Didattica', 'Didattica Orientativa', 'mean_didattica_orientativa'),
                ('Opportunita', 'Opportunità Formative', 'mean_opportunita')
            ]

            # === MAPPING SOTTO-INDICATORI ===
            SUB_INDICATORS = {
                'Finalita': [
                    ('2_3_finalita_attitudini_score', 'Attitudini e Talenti'),
                    ('2_3_finalita_interessi_score', 'Interessi Professionali'),
                    ('2_3_finalita_progetto_vita_score', 'Progetto di Vita'),
                    ('2_3_finalita_transizioni_formative_score', 'Transizioni Formative'),
                    ('2_3_finalita_capacita_orientative_opportunita_score', 'Capacità Orientative')
                ],
                'Obiettivi': [
                    ('2_4_obiettivo_ridurre_abbandono_score', 'Contrasto Dispersione'),
                    ('2_4_obiettivo_continuita_territorio_score', 'Continuità Territorio'),
                    ('2_4_obiettivo_contrastare_neet_score', 'Riduzione NEET'),
                    ('2_4_obiettivo_lifelong_learning_score', 'Lifelong Learning')
                ],
                'Governance': [
                    ('2_5_azione_coordinamento_servizi_score', 'Coordinamento'),
                    ('2_5_azione_dialogo_docenti_studenti_score', 'Dialogo Interno'),
                    ('2_5_azione_rapporto_scuola_genitori_score', 'Alleanza Famiglie'),
                    ('2_5_azione_monitoraggio_azioni_score', 'Monitoraggio'),
                    ('2_5_azione_sistema_integrato_inclusione_fragilita_score', 'Inclusione')
                ],
                'Didattica': [
                    ('2_6_didattica_da_esperienza_studenti_score', 'Centralità Studente'),
                    ('2_6_didattica_laboratoriale_score', 'Didattica Laboratoriale'),
                    ('2_6_didattica_flessibilita_spazi_tempi_score', 'Flessibilità'),
                    ('2_6_didattica_interdisciplinare_score', 'Interdisciplinarità')
                ],
                'Opportunita': [
                    ('2_7_opzionali_culturali_score', 'Attività Culturali'),
                    ('2_7_opzionali_laboratoriali_espressive_score', 'Laboratori Espressivi'),
                    ('2_7_opzionali_ludiche_ricreative_score', 'Attività Ricreative'),
                    ('2_7_opzionali_volontariato_score', 'Volontariato'),
                    ('2_7_opzionali_sportive_score', 'Sport')
                ]
            }

            summary_text = "\\newpage\n\n## Sintesi Quantitativa: Le Dimensioni dell'Orientamento\n\n"
            summary_text += "Di seguito il dettaglio dei punteggi medi rilevati per le dimensioni e i relativi sotto-indicatori.\n"

            # ── PARTE 1: Tutte le tabelle ──────────────────────────────────

            # 1. Dimensione Strutturale
            if '2_1_score' in df.columns:
                val = df['2_1_score'].mean()
                std = df['2_1_score'].std()
                summary_text += f"### Dimensione Strutturale (Compliance)\n"
                summary_text += f"**Media: {val:.2f}** (dev.std: {std:.2f})\n\n"

            # 2. Tabelle per le 5 dimensioni
            for key, label, col_main in DIMENSIONS_ORDER:
                summary_text += f"### {label}\n\n"

                # Start LaTeX table
                summary_text += r"\begin{tabularx}{\textwidth}{@{} X c c @{}}" + "\n"
                summary_text += r"\toprule" + "\n"
                summary_text += r"\textbf{Indicatore} & \textbf{Media} & \textbf{Dev. Std.} \\" + "\n"
                summary_text += r"\midrule" + "\n"

                # Riga Totale Dimensione (Bold)
                if col_main in df.columns:
                    val = df[col_main].mean()
                    std = df[col_main].std()
                    summary_text += f"\\textbf{{Totale Dimensione}} & \\textbf{{{val:.2f}}} & \\textbf{{{std:.2f}}} \\\\\n"

                # Righe Sotto-indicatori
                if key in SUB_INDICATORS:
                    for sub_col, sub_label in SUB_INDICATORS[key]:
                        if sub_col in df.columns:
                            sub_val = df[sub_col].mean()
                            sub_std = df[sub_col].std()
                            summary_text += f"{sub_label} & {sub_val:.2f} & {sub_std:.2f} \\\\\n"

                summary_text += r"\bottomrule" + "\n"
                summary_text += r"\end{tabularx}" + "\n\n"

            summary_text += "\n*Legenda Copertura Informativa: Copertura esaustiva (6-7), Copertura approfondita (5-5.9), Copertura strutturata (4-4.9), Copertura di base (3-3.9), Copertura parziale (2-2.9), Traccia minima (1-1.9), Assente (0)*\n\n"

            # ── PARTE 2: Pagina grafici (griglia 3+2) ─────────────────────

            summary_text += "\\newpage\n\n"
            summary_text += "### Panoramica Grafica dei Sotto-Indicatori\n\n"

            # Generate all bar charts and collect paths
            chart_paths = []
            for key, label, col_main in DIMENSIONS_ORDER:
                sub_data = []
                if key in SUB_INDICATORS:
                    for sub_col, sub_label in SUB_INDICATORS[key]:
                        if sub_col in df.columns:
                            val = df[sub_col].mean()
                            sub_data.append((sub_label, val))

                bar_chart_path = self._generate_dimension_bar_chart(label, sub_data, compact=True)
                if bar_chart_path:
                    chart_paths.append((label, bar_chart_path))

            # Build LaTeX minipage grid: 2 per row for better readability
            if chart_paths:
                all_charts = list(chart_paths)
                rows = [all_charts[i:i+2] for i in range(0, len(all_charts), 2)]

                for row_idx, row in enumerate(rows):
                    summary_text += r"\noindent" + "\n"
                    if len(row) == 1:
                        # Single chart centered
                        summary_text += r"\hfill" + "\n"
                    for i, (label, path) in enumerate(row):
                        summary_text += r"\begin{minipage}[t]{0.47\textwidth}" + "\n"
                        summary_text += r"\centering" + "\n"
                        summary_text += f"\\includegraphics[width=\\textwidth]{{{path}}}\n"
                        summary_text += r"\end{minipage}" + "\n"
                        if i < len(row) - 1:
                            summary_text += r"\hfill" + "\n"
                    if len(row) == 1:
                        summary_text += r"\hfill" + "\n"
                    if row_idx < len(rows) - 1:
                        summary_text += "\n\\vspace{0.5cm}\n\n"

                summary_text += "\n"

            # ── PARTE 3: Commento narrativo ────────────────────────────────

            summary_text += "\n### Panoramica dei Risultati Quantitativi\n\n"
            summary_text += "[SLOT:panoramica_quantitativa]\n\n"
            summary_text += "\\newpage\n"

            # Store quantitative summary for slot context
            self.quantitative_summary = {
                'dimensions': {},
            }
            for key, label, col_main in DIMENSIONS_ORDER:
                if col_main in df.columns:
                    dim_data = {'mean': round(df[col_main].mean(), 2), 'std': round(df[col_main].std(), 2)}
                    if key in SUB_INDICATORS:
                        dim_data['sub'] = {}
                        for sub_col, sub_label in SUB_INDICATORS[key]:
                            if sub_col in df.columns:
                                dim_data['sub'][sub_label] = round(df[sub_col].mean(), 2)
                    self.quantitative_summary['dimensions'][label] = dim_data
            if '2_1_score' in df.columns:
                self.quantitative_summary['dimensions']['Dimensione Strutturale'] = {
                    'mean': round(df['2_1_score'].mean(), 2),
                    'std': round(df['2_1_score'].std(), 2),
                }

            return summary_text

        except Exception as e:
            logger.error(f"Error building detailed dimensions summary: {e}")
            return ""

    def _build_territory_frequency_analysis(self, df) -> str:
        """Scans PTOF analysis JSON files for named partners and builds
        frequency charts + table for the filtered schools.

        Returns markdown text with bar charts (top partners + categories) and LaTeX table.
        """
        try:
            analysis_dir = self.base_dir / "analysis_results"
            if not analysis_dir.exists():
                logger.warning("analysis_results directory not found for territory analysis")
                return ""

            school_ids = set(df['school_id'].dropna().astype(str).str.strip().str.upper())
            n_total = len(school_ids)
            if n_total == 0:
                return ""

            # Collect all partner names from JSON files
            from collections import Counter
            partner_counter = Counter()  # normalized_name -> n_schools

            for school_id in school_ids:
                json_files = glob.glob(str(analysis_dir / f"*{school_id}*_analysis.json"))
                if not json_files:
                    continue
                try:
                    with open(json_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    partners = (
                        data.get('ptof_section2', {})
                        .get('2_2_partnership', {})
                        .get('partner_nominati', [])
                    )
                    # Deduplicate per school (case-insensitive)
                    seen = set()
                    for p in partners:
                        p_clean = p.strip()
                        p_lower = p_clean.lower()
                        if p_lower and p_lower not in seen:
                            seen.add(p_lower)
                            # Normalize to title case so "musei" and "Musei" merge
                            p_normalized = p_clean.title()
                            partner_counter[p_normalized] += 1
                except Exception:
                    continue

            if not partner_counter:
                return ""

            # ── Classify partners into categories ──
            category_counter = Counter()
            for partner_name, count in partner_counter.items():
                p_lower = partner_name.lower()
                classified = False
                for cat, keywords in TERRITORY_PARTNER_CATEGORIES.items():
                    for kw in keywords:
                        if kw in p_lower:
                            category_counter[cat] += count
                            classified = True
                            break
                    if classified:
                        break
                if not classified:
                    category_counter['Altro'] += count

            # Top 15 individual partners
            top_partners = partner_counter.most_common(15)
            # Category ranking
            top_categories = category_counter.most_common()

            # Store for slot context
            self.territory_frequencies = top_partners
            self.territory_category_frequencies = top_categories

            # ── Generate partner bar chart ──
            labels_p = [p for p, _ in reversed(top_partners)]
            values_p = [c for _, c in reversed(top_partners)]

            fig, ax = plt.subplots(figsize=(9, 0.45 * len(labels_p) + 1.5))
            colors_p = ['#27ae60' if v >= n_total * 0.3
                        else '#82e0aa' if v >= n_total * 0.1
                        else '#d5f5e3'
                        for v in values_p]
            ax.barh(range(len(labels_p)), values_p, color=colors_p, height=0.5)
            ax.set_yticks(range(len(labels_p)))
            ax.set_yticklabels(labels_p, fontsize=9)
            ax.set_xlabel('Numero di scuole', fontsize=10)
            ax.set_title('Partner più citati nei PTOF', loc='left', fontsize=12, fontweight='bold', pad=10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for i, v in enumerate(values_p):
                pct = v / n_total * 100
                ax.text(v + 0.3, i, f"{v} ({pct:.0f}%)", va='center', fontsize=9)

            output_dir = self.base_dir / "reports" / "synthesis" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

            fname_partners = f"territory_partners_{timestamp}.png"
            plt.tight_layout()
            plt.savefig(output_dir / fname_partners, dpi=150)
            plt.close()

            # ── Generate category bar chart ──
            labels_c = [c for c, _ in reversed(top_categories)]
            values_c = [v for _, v in reversed(top_categories)]

            fig2, ax2 = plt.subplots(figsize=(9, 0.45 * len(labels_c) + 1.5))
            colors_c = ['#2980b9' if v >= n_total * 0.5
                        else '#7fb3d8' if v >= n_total * 0.2
                        else '#d6eaf8'
                        for v in values_c]
            ax2.barh(range(len(labels_c)), values_c, color=colors_c, height=0.5)
            ax2.set_yticks(range(len(labels_c)))
            ax2.set_yticklabels(labels_c, fontsize=10)
            ax2.set_xlabel('N. menzioni aggregate', fontsize=10)
            ax2.set_title('Categorie di partner territoriali', loc='left', fontsize=12, fontweight='bold', pad=10)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            for i, v in enumerate(values_c):
                ax2.text(v + 0.3, i, str(v), va='center', fontsize=8)

            fname_categories = f"territory_categories_{timestamp}.png"
            plt.tight_layout()
            plt.savefig(output_dir / fname_categories, dpi=150)
            plt.close()

            # ── Build markdown ──
            text = "### Partner territoriali più diffusi nel campione\n\n"
            text += f"![Partner più citati](images/{fname_partners})\n\n"

            # LaTeX table — top partners
            text += r"\begin{tabularx}{\textwidth}{@{} X l c c @{}}" + "\n"
            text += r"\toprule" + "\n"
            text += r"\textbf{Partner} & \textbf{Categoria} & \textbf{N. Scuole} & \textbf{\% Campione} \\" + "\n"
            text += r"\midrule" + "\n"

            for partner, count in top_partners:
                pct = count / n_total * 100
                # Find category
                p_lower = partner.lower()
                cat = 'Altro'
                for cat_name, keywords in TERRITORY_PARTNER_CATEGORIES.items():
                    if any(kw in p_lower for kw in keywords):
                        cat = cat_name
                        break
                text += f"{partner} & {cat} & {count} & {pct:.1f}\\% \\\\\n"

            text += r"\bottomrule" + "\n"
            text += r"\end{tabularx}" + "\n\n"

            # Category chart
            text += "### Distribuzione per categoria di partner\n\n"
            text += f"![Categorie partner](images/{fname_categories})\n\n"

            return text

        except Exception as e:
            logger.error(f"Error building territory frequency analysis: {e}")
            return ""

    def _build_methodology_frequency_analysis(self, df) -> str:
        """Scans PTOF analysis markdown files for methodology keywords and builds
        a frequency chart + table for the filtered schools.

        Returns markdown text with bar chart image and LaTeX table.
        """
        try:
            analysis_dir = self.base_dir / "analysis_results"
            if not analysis_dir.exists():
                logger.warning("analysis_results directory not found")
                return ""

            school_ids = set(df['school_id'].dropna().astype(str).str.strip().str.upper())
            n_total = len(school_ids)
            if n_total == 0:
                return ""

            # Count how many schools mention each methodology
            method_school_count = {m: 0 for m in ALL_METHODOLOGY_NAMES}

            for school_id in school_ids:
                md_files = glob.glob(str(analysis_dir / f"*{school_id}*_analysis.md"))
                if not md_files:
                    continue
                try:
                    with open(md_files[0], 'r', encoding='utf-8') as f:
                        content = f.read().upper()
                    for method in ALL_METHODOLOGY_NAMES:
                        if method.upper() in content:
                            method_school_count[method] += 1
                except Exception:
                    continue

            # Sort by count, take top 12
            sorted_methods = sorted(method_school_count.items(), key=lambda x: x[1], reverse=True)
            top_methods = [(m, c) for m, c in sorted_methods if c > 0][:12]

            if not top_methods:
                return ""

            # Store for slot context (list of (method, count) tuples)
            self.methodology_frequencies = top_methods

            # ── Generate bar chart ──
            labels = [m for m, _ in reversed(top_methods)]
            values = [c for _, c in reversed(top_methods)]

            fig, ax = plt.subplots(figsize=(9, 0.45 * len(labels) + 1.5))

            colors = ['#3498db' if v >= n_total * 0.5
                      else '#85c1e9' if v >= n_total * 0.25
                      else '#d5e8f0'
                      for v in values]

            ax.barh(range(len(labels)), values, color=colors, height=0.5)
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=10)
            ax.set_xlabel('Numero di scuole', fontsize=10)
            ax.set_title('Metodologie più citate nei PTOF', loc='left', fontsize=12, fontweight='bold', pad=10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            for i, v in enumerate(values):
                pct = v / n_total * 100
                ax.text(v + 0.3, i, f"{v} ({pct:.0f}%)", va='center', fontsize=9)

            output_dir = self.base_dir / "reports" / "synthesis" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"methodology_freq_{timestamp}.png"
            output_path = output_dir / filename

            plt.tight_layout()
            plt.savefig(output_path, dpi=150)
            plt.close()

            # ── Build markdown ──
            text = "### Metodologie più diffuse nel campione\n\n"
            text += f"![Metodologie più diffuse](images/{filename})\n\n"

            # LaTeX table
            text += r"\begin{tabularx}{\textwidth}{@{} X c c @{}}" + "\n"
            text += r"\toprule" + "\n"
            text += r"\textbf{Metodologia} & \textbf{N. Scuole} & \textbf{\% Campione} \\" + "\n"
            text += r"\midrule" + "\n"

            for method, count in top_methods:
                pct = count / n_total * 100
                text += f"{method} & {count} & {pct:.1f}\\% \\\\\n"

            text += r"\bottomrule" + "\n"
            text += r"\end{tabularx}" + "\n\n"

            return text

        except Exception as e:
            logger.error(f"Error building methodology frequency analysis: {e}")
            return ""

    def get_slot_contexts(self) -> Dict[str, dict]:
        """Retrieves data context for each slot using Hybrid Dual-Index Retrieval.

        Two RAG layers per slot:
          1. QUADRO (summary): analysis_md + analysis_note chunks → structured overview
          2. EVIDENZA (booster): raw_ptof chunks → direct textual evidence from PTOF
        Plus: activities and cluster summaries as before.
        """
        contexts = {}

        # Determine grade filter for DB query
        grade_filter = self.filters.get("ordine_grado")
        db_grade_filter = None
        if grade_filter:
            if isinstance(grade_filter, list):
                db_grade_filter = grade_filter[0] if len(grade_filter) == 1 else None
            else:
                db_grade_filter = grade_filter

        logger.info(f"Starting Hybrid Dual-Index Retrieval with filter: {db_grade_filter}...")

        cluster_distribution = {
            k: self.filtered_cluster_counts.get(k, self.cluster_stats.get(k, {}).get("count"))
            for k in self._active_cluster_keys()
        }
        clustered_schools = sum(
            int(v) for v in cluster_distribution.values() if isinstance(v, int)
        )
        total_schools = int(self.stats.get("n_schools", 0) or 0)

        contexts[CLUSTER_PROFILE_SECTION["key"]] = {
            "narrative_excerpts": [],
            "raw_evidence": [],
            "representative_activities": [],
            "score_stats": {},
            "n_schools": clustered_schools,
            "n_schools_total": total_schools,
            "n_schools_clustered": clustered_schools,
            "n_schools_unassigned": max(total_schools - clustered_schools, 0),
            "n_clusters": len(self._active_cluster_keys()),
            "cluster_distribution": cluster_distribution,
            "cluster_summaries_text": self._build_cluster_profiles_text(),
        }

        for section in THEMATIC_SECTIONS:
            key = section["key"]
            query = section.get("retrieval_query", "")

            logger.info(f"Retrieving context for slot: {key}")

            query_emb = None
            if self.model and query:
                query_emb = self.model.encode(query).tolist()

            # ── 1. Layer QUADRO: summary chunks (analysis_md + analysis_note) ──
            summary_chunks = []
            if self.db and query_emb:
                try:
                    summary_chunks = self.db.search_similar_chunks(
                        query_embedding=query_emb,
                        source_types=["analysis_md", "analysis_note"],
                        grade_level=db_grade_filter,
                        limit=30,
                    )
                except Exception as e:
                    logger.error(f"Summary retrieval failed for {key}: {e}")

            formatted_summary = []
            for c in summary_chunks:
                formatted_summary.append({
                    "denominazione": f"Scuola {c.get('school_code')}",
                    "code": c.get("school_code"),
                    "regione": c.get("region"),
                    "tipo_scuola": c.get("school_type"),
                    "excerpt": c.get("content"),
                })

            # ── 2. Layer EVIDENZA: raw PTOF chunks (booster) ──
            raw_chunks = []
            if self.db and query_emb:
                try:
                    raw_chunks = self.db.search_similar_chunks(
                        query_embedding=query_emb,
                        source_types=["raw_ptof"],
                        grade_level=db_grade_filter,
                        limit=20,
                    )
                except Exception as e:
                    logger.error(f"Raw PTOF retrieval failed for {key}: {e}")

            formatted_raw = []
            for c in raw_chunks:
                formatted_raw.append({
                    "code": c.get("school_code"),
                    "regione": c.get("region"),
                    "tipo_scuola": c.get("school_type"),
                    "excerpt": c.get("content"),
                })

            # ── 3. Score Stats ──
            relevant_scores = {}
            for sk in section.get("score_keys", []):
                if sk in self.stats.get("score_stats", {}):
                    relevant_scores[sk] = self.stats["score_stats"][sk]

            # ── 4. Cluster Summaries (Map-Reduce) ──
            cluster_summary_text = ""
            if self.cluster_summaries:
                lines = []
                for cluster_key in self._active_cluster_keys():
                    summaries = self.cluster_summaries.get(cluster_key, {})
                    if key in summaries:
                        cluster_count = self.filtered_cluster_counts.get(cluster_key)
                        cluster_label = f"CLUSTER {cluster_key}"
                        if cluster_count:
                            cluster_label += f" (n={cluster_count})"
                        lines.append(f"{cluster_label}: {summaries[key]}")
                if lines:
                    cluster_summary_text = "SINTESI PER CLUSTER (ANALISI PRELIMINARE):\n" + "\n\n".join(lines)

            # ── 5. Activities Retrieval ──
            activity_chunks = []
            if self.db and query_emb:
                try:
                    activity_chunks = self.db.search_similar_chunks(
                        query_embedding=query_emb,
                        topic="activity",
                        grade_level=db_grade_filter,
                        limit=15,
                    )
                except Exception as e:
                    logger.error(f"Activity retrieval failed for {key}: {e}")

            formatted_activities = []
            for ac in activity_chunks:
                content = ac.get("content", "")
                act_dict = {
                    "school_code": ac.get("school_code", "?"),
                    "school_region": ac.get("region", "?"),
                }
                for line in content.split("\n"):
                    if line.startswith("TITOLO: "):
                        act_dict["titolo_attivita"] = line[8:]
                    elif line.startswith("DESCRIZIONE: "):
                        act_dict["descrizione_e_metodologia"] = line[13:]
                    elif line.startswith("TARGET: "):
                        act_dict["target"] = line[8:]
                formatted_activities.append(act_dict)

            contexts[key] = {
                "narrative_excerpts": formatted_summary,
                "raw_evidence": formatted_raw,
                "representative_activities": formatted_activities,
                "score_stats": relevant_scores,
                "n_schools": self.stats.get("n_schools", 0),
                "cluster_summaries_text": cluster_summary_text,
                "sampling_bias_note": self._build_sampling_bias_note(),
            }

        # ── Enrich metodologie_didattiche with frequency data ──
        if "metodologie_didattiche" in contexts and self.methodology_frequencies:
            top12 = self.methodology_frequencies[:12]
            n_schools = int(self.stats.get("n_schools", 0) or 0)
            freq_lines = []
            for m, cnt in top12:
                pct = (cnt / n_schools * 100) if n_schools else 0
                freq_lines.append(f"- {m}: {cnt} scuole ({pct:.1f}%)")
            contexts["metodologie_didattiche"]["methodology_frequencies"] = self.methodology_frequencies[:12]
            contexts["metodologie_didattiche"]["methodology_frequencies_text"] = (
                "FREQUENZA METODOLOGIE NEL CAMPIONE (top 12):\n" + "\n".join(freq_lines)
            )

        # ── Enrich rapporto_territorio with partner frequency data ──
        if "rapporto_territorio" in contexts and self.territory_frequencies:
            n_schools = int(self.stats.get("n_schools", 0) or 0)
            partner_lines = []
            for p, cnt in self.territory_frequencies[:15]:
                pct = (cnt / n_schools * 100) if n_schools else 0
                partner_lines.append(f"- {p}: {cnt} scuole ({pct:.1f}%)")
            cat_lines = []
            for cat, cnt in self.territory_category_frequencies:
                cat_lines.append(f"- {cat}: {cnt} menzioni")
            contexts["rapporto_territorio"]["territory_frequencies"] = self.territory_frequencies[:15]
            contexts["rapporto_territorio"]["territory_category_frequencies"] = self.territory_category_frequencies
            contexts["rapporto_territorio"]["territory_frequencies_text"] = (
                "PARTNER PIÙ CITATI NEI PTOF (top 15):\n" + "\n".join(partner_lines)
                + "\n\nCATEGORIE DI PARTNER (per n. menzioni aggregate):\n" + "\n".join(cat_lines)
            )

        # ── Context for implicazioni_campionamento ──
        contexts["implicazioni_campionamento"] = {
            "narrative_excerpts": [],
            "raw_evidence": [],
            "representative_activities": [],
            "score_stats": {},
            "n_schools": total_schools,
            "cluster_summaries_text": "",
            "sampling_bias": self.sampling_bias,
        }

        # ── Context for panoramica_quantitativa ──
        contexts["panoramica_quantitativa"] = {
            "narrative_excerpts": [],
            "raw_evidence": [],
            "representative_activities": [],
            "score_stats": self.stats.get("score_stats", {}),
            "n_schools": total_schools,
            "cluster_summaries_text": "",
            "quantitative_summary": getattr(self, "quantitative_summary", {}),
            "sampling_bias_note": self._build_sampling_bias_note(),
        }

        return contexts

    def _build_sampling_bias_note(self) -> str:
        """Build a compact text note summarizing sampling biases for injection into thematic prompts."""
        if not self.sampling_bias:
            return "Nessun dato di bias campionario disponibile."

        parts = []
        bias = self.sampling_bias
        n = bias.get('n_obs', '?')
        grade = bias.get('grade_filter', '?')
        parts.append(f"Campione: {n} scuole {grade}, {bias.get('n_regions', '?')}/20 regioni.")

        # Gestione bias
        dev_stat = bias.get('dev_statale_pp')
        if dev_stat is not None and abs(dev_stat) > 5:
            pct_par = bias.get('pct_paritaria_obs', '?')
            pct_par_exp = bias.get('pct_paritaria_exp', '?')
            parts.append(
                f"BIAS GESTIONE: Paritarie {pct_par}% vs {pct_par_exp}% atteso "
                f"(deviazione {'+' if dev_stat < 0 else ''}{-dev_stat:.0f} pp). "
                "I punteggi di governance e struttura possono risentirne."
            )

        # Geo bias
        geo_devs = bias.get('geo_deviations', {})
        significant_geo = {area: dev for area, dev in geo_devs.items() if abs(dev) > 5}
        if significant_geo:
            geo_parts = [f"{area} {'+' if d > 0 else ''}{d:.0f}pp" for area, d in significant_geo.items()]
            parts.append(f"BIAS GEOGRAFICO: {', '.join(geo_parts)}. "
                        "Le sezioni su territorio e partnership vanno interpretate con cautela.")

        # Metro bias
        dev_metro = bias.get('dev_metro_pp')
        if dev_metro is not None and abs(dev_metro) > 5:
            parts.append(
                f"BIAS METRO/NON-METRO: Deviazione {'+' if dev_metro > 0 else ''}{dev_metro:.0f} pp. "
                "I risultati su partnership e PCTO possono riflettere il contesto prevalente."
            )

        return " ".join(parts)
