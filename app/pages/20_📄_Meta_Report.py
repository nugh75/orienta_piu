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
REPORTS_DIR = Path("reports")
META_REPORTS_DIR = REPORTS_DIR / "meta"
REPORT_SUFFIXES = ("_best_practices", "_attivita")

# Titoli comprensibili per le dimensioni (basati su attivita.json)
DIM_TITLES = {
    # Categorie principali
    "metodologie": "Metodologie Didattiche Innovative",
    "progetti": "Progetti e Attivita Esemplari",
    "inclusione": "Inclusione e Supporto",
    "orientamento": "Orientamento e Accompagnamento",
    "partnership": "Partnership e Collaborazioni",
    # Attivita specifiche
    "pcto": "Percorsi per le Competenze (PCTO)",
    "openday": "Giornate di Orientamento (Open Day)",
    "universita": "Orientamento Universitario",
    "visite": "Visite Guidate e Viaggi di Istruzione",
    "exalunni": "La Rete degli Ex-Studenti",
    "certificazioni": "Certificazioni e Competenze"
}

# Descrizioni per ogni dimensione
DIM_DESCRIPTIONS = {
    "metodologie": "Le metodologie innovative usate per orientare e formare gli studenti",
    "progetti": "I progetti e le attivita esemplari che distinguono le scuole",
    "inclusione": "Come le scuole supportano tutti gli studenti nel loro percorso",
    "orientamento": "Le pratiche di accompagnamento verso le scelte future",
    "partnership": "Le collaborazioni con aziende, universita e territorio",
    "pcto": "I percorsi di alternanza scuola-lavoro e competenze trasversali",
    "openday": "Le iniziative per far conoscere la scuola a studenti e famiglie",
    "universita": "L'orientamento verso il mondo universitario",
    "visite": "Le uscite didattiche presso aziende e atenei",
    "exalunni": "Il coinvolgimento degli ex-studenti come mentori",
    "certificazioni": "Le certificazioni linguistiche, digitali e professionali"
}

DIM_ICONS = {
    "metodologie": "📚",
    "progetti": "🌟",
    "inclusione": "🤗",
    "orientamento": "🧭",
    "partnership": "🤝",
    "pcto": "🏭",
    "openday": "🚪",
    "universita": "🎓",
    "visite": "🏢",
    "exalunni": "👥",
    "certificazioni": "📜"
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
    regional_dir = META_REPORTS_DIR / "regional"
    if regional_dir.exists():
        for f in regional_dir.rglob("*.md"):
            report_id = f.stem
            region, filters, profile = split_report_filters(report_id)
            reports["regional"].append({
                "region": region,
                "id": report_id,
                "filters": filters,
                "profile": profile,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    # National reports
    national_dir = META_REPORTS_DIR / "national"
    if national_dir.exists():
        for f in national_dir.rglob("*.md"):
            report_id = f.stem
            _, filters, profile = split_report_filters(report_id)
            reports["national"].append({
                "path": str(f),
                "id": report_id,
                "filters": filters,
                "profile": profile,
                "mtime": f.stat().st_mtime
            })

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


def split_report_filters(identifier: str) -> tuple[str, dict, str]:
    clean_id = strip_report_suffix(identifier)
    parts = clean_id.split("__")
    base = parts[0]
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
    return base, filters, profile


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
st.title("📄 Sintesi delle Attivita")

st.markdown("""
Questa sezione raccoglie le **sintesi delle attivita di orientamento**
emerse dall'analisi dei PTOF delle scuole italiane. I report sono organizzati
per tema, territorio e singola scuola, offrendo una panoramica completa delle
esperienze piu significative nel campo dell'orientamento scolastico.
""")

# Carica dati
available_reports = get_available_reports()

# === METRICHE ===
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

with col_m1:
    school_count = len(available_reports["schools"])
    st.metric("Scuole Analizzate", school_count)

with col_m2:
    regional_count = len(available_reports["regional"])
    st.metric("Report Regionali", regional_count)

with col_m3:
    national_status = "Disponibile" if available_reports["national"] else "—"
    st.metric("Report Italia", national_status)

with col_m4:
    thematic_count = len(available_reports["thematic"])
    st.metric("Approfondimenti", thematic_count)

with col_m5:
    if st.button("🔄 Aggiorna"):
        refresh_data()

st.markdown("---")

# === TABS ===
tab_tematici, tab_regionali, tab_scuole, tab_nazionale, tab_generali, tab_info = st.tabs([
    "🎯 Per Tema", "🗺️ Per Regione", "🏫 Per Scuola", "🇮🇹 Italia", "📚 Tutti i Report", "ℹ️ Info"
])

# === TAB TEMATICI ===
with tab_tematici:
    st.subheader("🎯 Approfondimenti Tematici")

    st.markdown("""
    Esplora le attivita organizzate per **area tematica**. Ogni report analizza
    come le scuole italiane affrontano uno specifico aspetto dell'orientamento,
    evidenziando le esperienze piu innovative e replicabili.
    """)

    if available_reports["thematic"]:
        search_thematic = st.text_input(
            "🔎 Cerca temi",
            key="search_thematic",
            placeholder="Es. orientamento, didattica, inclusione"
        )
        dim_options = sorted({r["dimension"] for r in available_reports["thematic"]})
        dim_label_map = {DIM_TITLES.get(d, d.title()): d for d in dim_options}
        dim_labels = list(dim_label_map.keys())
        selected_dim_labels = st.multiselect(
            "Filtra dimensioni",
            options=dim_labels,
            default=dim_labels,
            key="filter_thematic_dims"
        )
        selected_dims = {dim_label_map[label] for label in selected_dim_labels}
        profile_options = sorted({r.get("profile") for r in available_reports["thematic"] if r.get("profile")})
        selected_profiles = set()
        if profile_options:
            profile_label_map = {PROFILE_LABELS.get(p, p): p for p in profile_options}
            profile_labels = list(profile_label_map.keys())
            selected_profile_labels = st.multiselect(
                "Filtra profilo",
                options=profile_labels,
                default=profile_labels,
                key="filter_thematic_profiles"
            )
            selected_profiles = {profile_label_map[label] for label in selected_profile_labels}

        filtered_reports = []
        for r in available_reports["thematic"]:
            dim = r["dimension"]
            if selected_dims and dim not in selected_dims:
                continue
            if selected_profiles and r.get("profile") not in selected_profiles:
                continue
            title = DIM_TITLES.get(dim, dim.title())
            desc = DIM_DESCRIPTIONS.get(dim, "")
            filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))
            text_blob = f"{dim} {title} {desc} {filters_label}".lower()
            if search_thematic and search_thematic.lower() not in text_blob:
                continue
            filtered_reports.append(r)

        st.caption(f"{len(filtered_reports)} risultati su {len(available_reports['thematic'])}")

        if not filtered_reports:
            st.info("Nessun report corrisponde ai filtri selezionati.")
        else:
            # Organizza per categoria
            structural = []
            opportunity = []
            other = []

            structural_dims = [
                "finalita", "obiettivi", "governance", "didattica", "partnership",
                "metodologie", "progetti", "inclusione"
            ]
            opportunity_dims = ["orientamento", "pcto", "stage", "openday", "visite", "laboratori", "testimonianze", "counseling", "alumni"]

            for r in filtered_reports:
                dim = r["dimension"]
                if dim in structural_dims:
                    structural.append(r)
                elif dim in opportunity_dims:
                    opportunity.append(r)
                else:
                    other.append(r)

            st.markdown("---")

            # Dimensioni Strutturali
            if structural:
                st.markdown("### 📋 Aspetti Organizzativi e Strategici")
                st.caption("Come le scuole pianificano e gestiscono l'orientamento")

                for r in structural:
                    dim = r["dimension"]
                    icon = DIM_ICONS.get(dim, "📄")
                    title = DIM_TITLES.get(dim, dim.title())
                    desc = DIM_DESCRIPTIONS.get(dim, "") + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                    mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(f"{icon} {title}", key=f"btn_struct_{r['id']}", use_container_width=True):
                            st.session_state["selected_report"] = r["path"]
                            st.session_state["selected_report_title"] = title + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                            st.session_state["selected_report_type"] = "thematic"
                            st.session_state["selected_report_id"] = r["id"]
                        st.caption(desc)
                    with col2:
                        st.caption(f"Agg. {mtime}")

                    render_report_inline("thematic", expected_id=r["id"], key_suffix=f"struct_{r['id']}")

            st.markdown("---")

            # Dimensioni Opportunita
            if opportunity:
                st.markdown("### 🚀 Attivita e Opportunita per gli Studenti")
                st.caption("Le esperienze concrete offerte agli studenti")

                for r in opportunity:
                    dim = r["dimension"]
                    icon = DIM_ICONS.get(dim, "📄")
                    title = DIM_TITLES.get(dim, dim.title())
                    desc = DIM_DESCRIPTIONS.get(dim, "") + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                    mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(f"{icon} {title}", key=f"btn_opp_{r['id']}", use_container_width=True):
                            st.session_state["selected_report"] = r["path"]
                            st.session_state["selected_report_title"] = title + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                            st.session_state["selected_report_type"] = "thematic"
                            st.session_state["selected_report_id"] = r["id"]
                        st.caption(desc)
                    with col2:
                        st.caption(f"Agg. {mtime}")

                    render_report_inline("thematic", expected_id=r["id"], key_suffix=f"opp_{r['id']}")

            # Altre dimensioni
            if other:
                st.markdown("---")
                st.markdown("### 📎 Altri Temi")
                st.caption("Report tematici non ancora classificati nelle sezioni principali")

                for r in other:
                    dim = r["dimension"]
                    icon = DIM_ICONS.get(dim, "📄")
                    title = DIM_TITLES.get(dim, dim.title())
                    desc = DIM_DESCRIPTIONS.get(dim, "") + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                    mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(f"{icon} {title}", key=f"btn_other_{r['id']}", use_container_width=True):
                            st.session_state["selected_report"] = r["path"]
                            st.session_state["selected_report_title"] = title + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                            st.session_state["selected_report_type"] = "thematic"
                            st.session_state["selected_report_id"] = r["id"]
                        st.caption(desc)
                    with col2:
                        st.caption(f"Agg. {mtime}")

                    render_report_inline("thematic", expected_id=r["id"], key_suffix=f"other_{r['id']}")

    else:
        st.info("I report tematici saranno disponibili a breve. Stiamo elaborando le analisi delle scuole.")

# === TAB REGIONALI ===
with tab_regionali:
    st.subheader("🗺️ Attivita per Regione")

    st.markdown("""
    Scopri le **attivita di orientamento** suddivise per territorio.
    Ogni report regionale presenta una sintesi delle esperienze piu significative
    delle scuole di quella regione.
    """)

    if available_reports["regional"]:
        search_regional = st.text_input(
            "🔎 Cerca regione",
            key="search_regional",
            placeholder="Es. Lazio, Lombardia"
        )
        region_options = sorted({r["region"] for r in available_reports["regional"]})
        region_label_map = {r.title(): r for r in region_options}
        region_labels = list(region_label_map.keys())
        selected_region_labels = st.multiselect(
            "Filtra regioni",
            options=region_labels,
            default=region_labels,
            key="filter_regional_regions"
        )
        selected_regions = {region_label_map[label] for label in selected_region_labels}
        profile_options = sorted({r.get("profile") for r in available_reports["regional"] if r.get("profile")})
        selected_profiles = set()
        if profile_options:
            profile_label_map = {PROFILE_LABELS.get(p, p): p for p in profile_options}
            profile_labels = list(profile_label_map.keys())
            selected_profile_labels = st.multiselect(
                "Filtra profilo",
                options=profile_labels,
                default=profile_labels,
                key="filter_regional_profiles"
            )
            selected_profiles = {profile_label_map[label] for label in selected_profile_labels}

        filtered_reports = []
        for r in available_reports["regional"]:
            region = r["region"]
            if selected_regions and region not in selected_regions:
                continue
            if selected_profiles and r.get("profile") not in selected_profiles:
                continue
            region_label = region.title()
            filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))
            if search_regional and search_regional.lower() not in f"{region_label} {filters_label}".lower():
                continue
            filtered_reports.append(r)

        st.caption(f"{len(filtered_reports)} risultati su {len(available_reports['regional'])}")

        st.markdown("---")

        # Ordina per regione
        sorted_reports = sorted(filtered_reports, key=lambda x: x["region"])

        if not sorted_reports:
            st.info("Nessun report corrisponde ai filtri selezionati.")
        else:
            for r in sorted_reports:
                region = r["region"].title()
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                col1, col2 = st.columns([4, 1])
                with col1:
                    label = f"🗺️ {region}{format_filters_label(r.get('filters', {}), r.get('profile', ''))}"
                    if st.button(label, key=f"btn_reg_{r['id']}", use_container_width=True):
                        st.session_state["selected_report"] = r["path"]
                        st.session_state["selected_report_title"] = f"Le Attivita in {region}{format_filters_label(r.get('filters', {}), r.get('profile', ''))}"
                        st.session_state["selected_report_type"] = "regional"
                        st.session_state["selected_report_id"] = r["id"]
                with col2:
                    st.caption(f"Aggiornato: {mtime}")

                render_report_inline("regional", expected_id=r["id"], key_suffix=r["id"])
    else:
        st.info("I report regionali saranno disponibili a breve.")

# === TAB SCUOLE ===
with tab_scuole:
    st.subheader("🏫 Analisi per Singola Scuola")

    st.markdown("""
    Consulta l'**analisi dettagliata** delle pratiche di orientamento
    di una specifica scuola. Inserisci il codice meccanografico per trovare il report.
    """)

    if available_reports["schools"]:
        # Cerca scuola
        search_school = st.text_input(
            "🔎 Cerca per codice scuola",
            placeholder="Inserisci il codice meccanografico (es: RMIS09400V)",
            help="Il codice meccanografico e l'identificativo unico della scuola"
        )
        profile_options = sorted({r.get("profile") for r in available_reports["schools"] if r.get("profile")})
        selected_profiles = set()
        if profile_options:
            profile_label_map = {PROFILE_LABELS.get(p, p): p for p in profile_options}
            profile_labels = list(profile_label_map.keys())
            selected_profile_labels = st.multiselect(
                "Filtra profilo",
                options=profile_labels,
                default=profile_labels,
                key="filter_school_profiles"
            )
            selected_profiles = {profile_label_map[label] for label in selected_profile_labels}
        max_results = st.slider(
            "Numero massimo risultati",
            min_value=10,
            max_value=200,
            value=30,
            step=10,
            key="filter_school_limit"
        )

        # Filtra
        filtered_schools = available_reports["schools"]
        if search_school:
            filtered_schools = [r for r in filtered_schools if search_school.upper() in r["code"].upper()]
        if selected_profiles:
            filtered_schools = [r for r in filtered_schools if r.get("profile") in selected_profiles]

        # Ordina per codice
        sorted_reports = sorted(filtered_schools, key=lambda x: x["code"])

        st.markdown(f"**{len(sorted_reports)} scuole** con report disponibile")

        st.markdown("---")

        # Mostra lista
        for r in sorted_reports[:max_results]:
            code = r["code"]
            mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{code}**")
                filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))
                if filters_label:
                    st.caption(filters_label.strip())
            with col2:
                st.caption(f"Agg. {mtime}")
            with col3:
                if st.button("📄 Leggi", key=f"btn_school_{r['id']}"):
                    st.session_state["selected_report"] = r["path"]
                    st.session_state["selected_report_title"] = f"Analisi Scuola {code}{format_filters_label(r.get('filters', {}), r.get('profile', ''))}"
                    st.session_state["selected_report_type"] = "school"
                    st.session_state["selected_report_id"] = r["id"]
            render_report_inline("school", expected_id=r["id"], key_suffix=r["id"])

        if len(sorted_reports) > max_results:
            st.info(f"Mostrate le prime {max_results} scuole. Usa la ricerca per trovare una scuola specifica.")

    else:
        st.info("I report delle singole scuole saranno disponibili a breve.")

# === TAB NAZIONALE ===
with tab_nazionale:
    st.subheader("🇮🇹 Panorama Nazionale")

    st.markdown("""
    Una **visione d'insieme** delle attivita di orientamento
    a livello nazionale. Questo report sintetizza le tendenze, i punti di forza
    e le aree di miglioramento emerse dall'analisi di tutte le scuole italiane.
    """)

    if available_reports["national"]:
        for r in available_reports["national"]:
            mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y alle %H:%M")
            filters_label = format_filters_label(r.get("filters", {}), r.get("profile", ""))

            st.success(f"Report nazionale disponibile - Ultimo aggiornamento: {mtime}{filters_label}")

            if st.button("📄 Leggi il Report Nazionale", key=f"btn_national_{r['id']}", use_container_width=True):
                st.session_state["selected_report"] = r["path"]
                st.session_state["selected_report_title"] = "Panorama Nazionale delle Attivita" + format_filters_label(r.get("filters", {}), r.get("profile", ""))
                st.session_state["selected_report_type"] = "national"
                st.session_state["selected_report_id"] = r["id"]
            render_report_inline("national", expected_id=r["id"], key_suffix=r["id"])
    else:
        st.info("Il report nazionale sara disponibile a breve, una volta completata l'analisi delle scuole.")

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

    I report di sintesi sono **documenti generati automaticamente** che raccolgono e
    analizzano le attivita di orientamento emerse dai PTOF (Piano Triennale
    dell'Offerta Formativa) delle scuole italiane.

    ### Come vengono generati?

    Un sistema di intelligenza artificiale analizza i dati strutturati estratti dai PTOF
    e produce sintesi ragionate che evidenziano:

    - **Attivita innovative** adottate dalle scuole
    - **Pattern comuni** nelle strategie di orientamento
    - **Punti di forza** da valorizzare
    - **Suggerimenti** per il miglioramento

    ### Tipi di report disponibili

    | Tipo | Contenuto |
    |------|-----------|
    | **Tematici** | Approfondimento su un aspetto specifico dell'orientamento (es. PCTO, stage, counseling) |
    | **Regionali** | Sintesi delle attivita di una regione |
    | **Per Scuola** | Analisi dettagliata di una singola istituzione |
    | **Nazionale** | Panoramica complessiva delle attivita italiane |

    ### Frequenza di aggiornamento

    I report vengono rigenerati periodicamente per includere le nuove analisi.
    La data di ultimo aggiornamento e indicata accanto a ogni report.

    ### Come utilizzare questi report

    - **Dirigenti scolastici**: per confrontare le proprie pratiche con quelle di altre scuole
    - **Docenti**: per scoprire metodologie innovative da adottare
    - **Famiglie e studenti**: per conoscere le opportunita offerte dalle scuole
    - **Ricercatori**: per analizzare le tendenze nell'orientamento scolastico italiano
    """)

render_footer()
