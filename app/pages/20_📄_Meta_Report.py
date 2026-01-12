#!/usr/bin/env python3
"""
Meta Report - Sintesi delle Attivita dalle scuole italiane
"""
import streamlit as st
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from data_utils import render_footer
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Sintesi Attivita", page_icon="🧭", layout="wide")
setup_page("pages/20_📄_Meta_Report.py")

# Custom CSS
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
# Fix path resolution: resolve relative to this file's position (app/pages/20_...)
# __file__ -> app/pages/20_...py
# parents[0] -> app/pages
# parents[1] -> app
# parents[2] -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
META_REPORTS_DIR = REPORTS_DIR / "meta"
REPORT_SUFFIXES = ("_best_practices", "_attivita", "_skeleton")

# Titoli comprensibili per le dimensioni (basati su attivita.json)
# Titoli ufficiali delle 6 Dimensioni (basati su skeleton.py)
DIM_TITLES = {
    "azioni": "Azioni di Sistema e Governance",
    "inclusione": "Buone Pratiche per l'Inclusione",
    "esperienze": "Esperienze Territoriali Significative",
    "metodologie": "Metodologie Didattiche Innovative",
    "partnership": "Partnership e Collaborazioni Strategiche",
    "progetti": "Progetti e Attività Esemplari",
}

# Descrizioni per ogni dimensione
DIM_DESCRIPTIONS = {
    "azioni": "Strategie organizzative, reti di scuole, formazione docenti e coordinamento.",
    "inclusione": "Supporto a BES/DSA, integrazione studenti stranieri e contrasto alla dispersione.",
    "esperienze": "Attività di PCTO, uscite didattiche, Service Learning e legame col territorio.",
    "metodologie": "Didattica laboratoriale, digitale, CLIL, Debate e spazi innovativi.",
    "partnership": "Accordi e collaborazioni con Università, ITS, Aziende ed Enti del Terzo Settore.",
    "progetti": "Iniziative di eccellenza, premi, gare e percorsi distintivi.",
}

DIM_ICONS = {
    "azioni": "⚙️",
    "inclusione": "🤗",
    "esperienze": "🌍",
    "metodologie": "💡",
    "partnership": "🤝",
    "progetti": "🏆",
}


# === DATA LOADING ===
@st.cache_data(ttl=60)
def load_meta_registry():
    """Carica lo stato dei meta report dal registry."""
    registry_path = META_REPORTS_DIR / "meta_registry.json"
    if registry_path.exists():
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def strip_report_suffix(stem: str) -> str:
    for suffix in REPORT_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def humanize_report_stem(stem: str) -> str:
    label = stem.replace("best_practices", "attivita").replace("best_practice", "attivita")
    label = label.replace("_", " ").strip()
    return label.title() if label else "Report"


def get_available_reports():
    """Trova tutti i report disponibili."""
    reports = {
        "schools": [],
        "regional": [],
        "national": [],
        "thematic": [],
        "general": []
    }

    # School reports
    schools_dir = META_REPORTS_DIR / "schools"
    if schools_dir.exists():
        for f in schools_dir.rglob("*.md"):
            report_id = f.stem
            code, filters, profile = split_report_filters(report_id)
            reports["schools"].append({
                "code": code,
                "id": report_id,
                "filters": filters,
                "profile": profile,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    # Regional reports
    # Legacy folders removed (regional/national)
    reports["regional"] = []
    reports["national"] = []

    # Thematic reports
    thematic_dir = META_REPORTS_DIR / "thematic"
    if thematic_dir.exists():
        for f in thematic_dir.rglob("*.md"):
            report_id = f.stem
            dim, filters, profile = split_report_filters(report_id)
            reports["thematic"].append({
                "dimension": dim,
                "id": report_id,
                "filters": filters,
                "profile": profile,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    # General reports (everything outside /reports/meta)
    if REPORTS_DIR.exists():
        for f in REPORTS_DIR.rglob("*.md"):
            try:
                f.relative_to(META_REPORTS_DIR)
                continue
            except ValueError:
                pass
            reports["general"].append({
                "id": f.stem,
                "title": humanize_report_stem(f.stem),
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    return reports


def get_report_title(report_type: str, identifier: str = None) -> str:
    """Genera un titolo leggibile per il report."""
    if report_type == "thematic":
        return DIM_TITLES.get(identifier, identifier.title() if identifier else "Report Tematico")
    elif report_type == "regional":
        return f"Le Attivita in {identifier.title()}" if identifier else "Report Regionale"
    elif report_type == "national":
        return "Panorama Nazionale delle Attivita"
    elif report_type == "school":
        return f"Analisi della Scuola {identifier}" if identifier else "Report Scuola"
    return "Report"


def refresh_data():
    """Forza il refresh dei dati."""
    load_meta_registry.clear()
    st.rerun()

PROFILE_LABELS = {
    "overview": "Quadro complessivo",
    "innovative": "Pratiche interessanti",
    "comparative": "Analisi comparativa",
    "impact": "Impatto e fattibilita",
    "operational": "Sintesi operativa",
}


def strip_report_suffix(stem: str) -> str:
    # Remove common suffixes first
    for suffix in REPORT_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def split_report_filters(identifier: str) -> tuple[str, dict, str]:
    """
    Parse report identifier.
    Supports legacy formats:
      - thematic: orientamento__filter=val
      - school: RMIS01600N__filter=val
    Supports new timestamped format:
      - 20260113_1200__Tema_orientamento__filter=val
      - 20260113_1200__Scuola_RMIS01600N__filter=val
    
    Returns: (base_id, filters, profile)
    """
    clean_id = strip_report_suffix(identifier)
    
    # Check for timestamp prefix (YYYYMMDD_HHMM__)
    # Regex: optional timestamp group, then the rest
    match = re.match(r"^(?P<ts>\d{8}_\d{4}__)?(?P<rest>.*)$", clean_id)
    if not match:
        base = clean_id
    else:
        rest = match.group("rest")
        # Ensure we strip known prefixes if present in new format
        if rest.startswith("Tema_"):
            rest = rest[5:]
        elif rest.startswith("Scuola_"):
            rest = rest[7:]
        base = rest

    # Now parse standard parts
    parts = base.split("__")
    core_id = parts[0]
    
    filters = {}
    profile = ""
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "profile":
            profile = value.replace("-", " ")
            continue
        label = value.replace("+", ", ").replace("-", " ")
        filters[key] = label
        
    return core_id, filters, profile


def format_filters_label(filters: dict, profile: str = "") -> str:
    if not filters:
        return f" | Profilo: {PROFILE_LABELS.get(profile, profile)}" if profile else ""
    pairs = [f"{key}={value}" for key, value in filters.items()]
    label = " | Filtri: " + ", ".join(pairs)
    if profile:
        label = f" | Profilo: {PROFILE_LABELS.get(profile, profile)}" + label
    return label

def clear_selected_report():
    for key in ["selected_report", "selected_report_title", "selected_report_type", "selected_report_id"]:
        if key in st.session_state:
            del st.session_state[key]

def normalize_meta_markdown(content: str) -> str:
    """Normalize markdown so bold-only lines do not render like headings."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if re.search(r"\bSintesi\b", heading, re.IGNORECASE):
                lines.append(heading)
            else:
                lines.append(line)
            continue
        match = re.match(r"^\\*\\*(.+?)\\*\\*$", stripped)
        if match:
            lines.append(match.group(1).strip())
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def render_report_inline(expected_type: str, expected_id: str = None, key_suffix: str = ""):
    if st.session_state.get("selected_report_type") != expected_type:
        return
    if expected_id is not None and st.session_state.get("selected_report_id") != expected_id:
        return

    report_path_value = st.session_state.get("selected_report")
    if not report_path_value:
        return

    st.markdown("---")

    report_title = st.session_state.get("selected_report_title", "Report")
    st.subheader(report_title)

    close_key = f"close_report_{expected_type}"
    if key_suffix:
        close_key = f"{close_key}_{key_suffix}"
    if st.button("❌ Chiudi report", key=close_key):
        clear_selected_report()
        st.rerun()

    report_path = Path(report_path_value)
    if report_path.exists():
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            content = re.sub(r'^```markdown\s*\n?', '', content)
            content = re.sub(r'^```\s*\n?', '', content)
            content = re.sub(r'\n?```\s*$', '', content)
            content = content.strip()
            content = normalize_meta_markdown(content)

            st.markdown(content)
            activities_path = report_path.with_suffix(".activities.csv")
            if activities_path.exists():
                try:
                    with activities_path.open('r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    if rows:
                        st.markdown("### Attivita utilizzate")
                        st.dataframe(rows, use_container_width=True, height=420)
                except Exception:
                    st.info("Tabella attivita non disponibile.")
            st.download_button(
                "📥 Scarica Report",
                data=content.encode('utf-8'),
                file_name=f"{report_title.replace(' ', '_')}.md",
                mime="text/markdown"
            )
        except Exception:
            st.error("Errore nel caricamento del report.")
    else:
        st.error("Report non disponibile.")
        clear_selected_report()


# === MAIN PAGE ===
st.title("📄 Sintesi delle Attività")

st.markdown("""
Questa sezione raccoglie le **sintesi delle attività di orientamento**
emerse dall'analisi dei PTOF delle scuole italiane. 
I report sono organizzati per **Dimensione Tematica** (le 6 categorie del framework) e per **Singola Scuola**.
""")

# Carica dati
available_reports = get_available_reports()

# === METRICHE ===
col1, col2, col4 = st.columns([1, 1, 2])

with col1:
    school_count = len(available_reports["schools"])
    st.metric("Scuole Analizzate", school_count)

with col2:
    thematic_count = len(available_reports["thematic"])
    st.metric("Report Dimensionali", thematic_count)

# Removed Metric as requested

with col4:
    if st.button("🔄 Aggiorna"):
        refresh_data()

st.markdown("---")

# === TABS ===
tab_tematici, tab_scuole, tab_generali, tab_info = st.tabs([
    "📊 Per Dimensione", "🏫 Per Scuola", "📚 Tutti i Report", "ℹ️ Info"
])

# === TAB TEMATICI ===
with tab_tematici:
    st.subheader("📊 Report per Dimensione")

    st.markdown("""
    Esplora le attività organizzate secondo le **6 Dimensioni Fondamentali** dell'orientamento.
    Ogni report aggrega le migliori pratiche riscontrate nelle scuole.
    """)

    if available_reports["thematic"]:
        # Raggruppa report per dimensione (DIM dinamico)
        reports_by_dim = {}
        for r in available_reports["thematic"]:
            dim = r["dimension"]
            if dim not in reports_by_dim:
                reports_by_dim[dim] = []
            reports_by_dim[dim].append(r)

        # Itera su tutte le dimensioni trovate
        found_dims = sorted(reports_by_dim.keys())
        
        for dim_key in found_dims:
            icon = DIM_ICONS.get(dim_key, "📄")
            title = DIM_TITLES.get(dim_key, dim_key.title())
            desc = DIM_DESCRIPTIONS.get(dim_key, "")
            
            st.markdown(f"### {icon} {title}")
            if desc:
                st.caption(desc)
            
            reports = reports_by_dim.get(dim_key, [])
            
            if not reports:
                st.info(f"Nessun report disponibile per {title}")
            else:
                for r in reports:
                    filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))
                    mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        btn_label = f"📄 Report {title} {filters_label}"
                        if st.button(btn_label, key=f"btn_dim_{r['id']}", use_container_width=True):
                            st.session_state["selected_report"] = r["path"]
                            st.session_state["selected_report_title"] = title + filters_label
                            st.session_state["selected_report_type"] = "thematic"
                            st.session_state["selected_report_id"] = r["id"]
                    with col2:
                        st.caption(f"Agg. {mtime}")
                    
                    render_report_inline("thematic", expected_id=r["id"], key_suffix=f"dim_{r['id']}")
            
            st.markdown("---")

    else:
        st.info("I report dimensionali saranno disponibili a breve.")

@st.cache_data(ttl=3600)
def load_school_names():
    """Carica mappa codice -> nome scuola dal CSV."""
    names = {}
    csv_path = PROJECT_ROOT / "data" / "attivita.csv"
    if csv_path.exists():
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("codice_meccanografico") and row.get("nome_scuola"):
                        names[row["codice_meccanografico"]] = row["nome_scuola"]
        except Exception:
            pass
    return names

# === TAB SCUOLE ===
with tab_scuole:
    st.subheader("🏫 Report per Scuola")

    st.markdown("""
    Cerca il report di una scuola specifica inserendo il **Codice Meccanografico** o il **Nome**.
    """)

    if available_reports["schools"]:
        school_names = load_school_names()
        
        search_school = st.text_input(
            "🔎 Cerca Scuola",
            key="search_school",
            placeholder="Es. RMIS01600N o Istruzione Superiore..."
        )
        
        school_reports = available_reports["schools"]
        
        # Arricchisci con nome
        for r in school_reports:
            r["name"] = school_names.get(r["code"], r["code"])

        if search_school:
            q = search_school.lower()
            school_reports = [
                r for r in school_reports
                if q in r['code'].lower() or q in r['name'].lower()
            ]

        # Ordina per nome scuola
        school_reports = sorted(school_reports, key=lambda x: x["name"])

        st.caption(f"{len(school_reports)} scuole trovate")

        if not school_reports:
            st.info("Nessuna scuola corrisponde alla ricerca.")
        else:
            for r in school_reports:
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")
                filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))
                
                school_label = f"{r['name']} ({r['code']})"
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    btn_label = f"🏫 {school_label} {filters_label}"
                    if st.button(btn_label, key=f"btn_school_{r['id']}", use_container_width=True):
                        st.session_state["selected_report"] = r["path"]
                        st.session_state["selected_report_title"] = school_label
                        st.session_state["selected_report_type"] = "school"
                        st.session_state["selected_report_id"] = r["id"]
                with col2:
                    st.caption(f"Agg. {mtime}")

                render_report_inline("school", expected_id=r["id"], key_suffix=r["id"])
    else:
        st.info("Nessun report scolastico disponibile al momento.")


# === TAB GENERALI ===
with tab_generali:
    st.subheader("📚 Tutti i Report")

    st.markdown("""
    Elenco di tutti i report presenti nella cartella `reports/`, inclusi quelli
    storici o non catalogati nei meta report.
    """)

    if available_reports["general"]:
        search_general = st.text_input(
            "🔎 Cerca report",
            key="search_general",
            placeholder="Es. orientamento, sintetico, narrativo"
        )
        sorted_reports = sorted(available_reports["general"], key=lambda x: x["title"])
        if search_general:
            sorted_reports = [
                r for r in sorted_reports
                if search_general.lower() in f"{r['title']} {r['id']}".lower()
            ]

        st.caption(f"{len(sorted_reports)} risultati su {len(available_reports['general'])}")

        if not sorted_reports:
            st.info("Nessun report corrisponde alla ricerca.")
        else:
            for r in sorted_reports:
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"📄 {r['title']}", key=f"btn_general_{r['id']}", use_container_width=True):
                        st.session_state["selected_report"] = r["path"]
                        st.session_state["selected_report_title"] = r["title"]
                        st.session_state["selected_report_type"] = "general"
                        st.session_state["selected_report_id"] = r["id"]
                with col2:
                    st.caption(f"Agg. {mtime}")

                render_report_inline("general", expected_id=r["id"], key_suffix=r["id"])
    else:
        st.info("Nessun report trovato nella cartella `reports/`.")

# === TAB INFO ===
with tab_info:
    st.subheader("ℹ️ Informazioni sui Report")

    st.markdown("""
    ### Cosa sono questi report?

    I report di sintesi sono documenti generati automaticamente che raccolgono e
    analizzano le attività di orientamento emerse dai PTOF (Piano Triennale
    dell'Offerta Formativa) delle scuole italiane.

    ### Come usare questa dashboard

    La dashboard offre due viste principali:

    1.  **📊 Per Dimensione**: Esplora le attività raggruppate per tema (es. Orientamento, Inclusione). Utile per trovare idee e modelli da replicare.
    2.  **🏫 Per Scuola**: Cerca una scuola specifica per vedere l'analisi completa del suo ecosistema di orientamento.

    ### Tipi di Report

    | Tipo | Contenuto |
    |------|-----------|
    | **Report Dimensionale** | Analisi trasversale di un tema specifico (es. "Metodologie Innovative") che aggrega le migliori pratiche di più scuole. |
    | **Report Scuola** | Analisi dettagliata di un singolo istituto che mappa tutte le attività di orientamento nelle 6 categorie del framework. |

    ### Metodologia

    I report sono generati utilizzando un approccio "Skeleton-First" che garantisce una struttura rigorosa e comparabile, arricchita dall'analisi semantica dell'Intelligenza Artificiale sui testi originali dei PTOF.
    """)

render_footer()
