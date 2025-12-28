#!/usr/bin/env python3
"""
Meta Report - Sintesi delle Best Practice dalle scuole italiane
"""
import streamlit as st
import json
import re
from pathlib import Path
from datetime import datetime
from data_utils import render_footer
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Sintesi Best Practice", page_icon="🧭", layout="wide")
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
META_REPORTS_DIR = Path("reports/meta")

# Titoli comprensibili per le dimensioni (basati su best_practices.json)
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


def get_available_reports():
    """Trova tutti i report disponibili."""
    reports = {
        "schools": [],
        "regional": [],
        "national": [],
        "thematic": []
    }

    # School reports
    schools_dir = META_REPORTS_DIR / "schools"
    if schools_dir.exists():
        for f in schools_dir.glob("*.md"):
            code = f.stem.replace("_best_practices", "")
            reports["schools"].append({
                "code": code,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    # Regional reports
    regional_dir = META_REPORTS_DIR / "regional"
    if regional_dir.exists():
        for f in regional_dir.glob("*.md"):
            region = f.stem.replace("_best_practices", "")
            reports["regional"].append({
                "region": region,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    # National report
    national_path = META_REPORTS_DIR / "national" / "italia_best_practices.md"
    if national_path.exists():
        reports["national"].append({
            "path": str(national_path),
            "mtime": national_path.stat().st_mtime
        })

    # Thematic reports
    thematic_dir = META_REPORTS_DIR / "thematic"
    if thematic_dir.exists():
        for f in thematic_dir.glob("*.md"):
            dim = f.stem.replace("_best_practices", "")
            reports["thematic"].append({
                "dimension": dim,
                "path": str(f),
                "mtime": f.stat().st_mtime
            })

    return reports


def get_report_title(report_type: str, identifier: str = None) -> str:
    """Genera un titolo leggibile per il report."""
    if report_type == "thematic":
        return DIM_TITLES.get(identifier, identifier.title() if identifier else "Report Tematico")
    elif report_type == "regional":
        return f"Le Migliori Pratiche in {identifier.title()}" if identifier else "Report Regionale"
    elif report_type == "national":
        return "Panorama Nazionale delle Best Practice"
    elif report_type == "school":
        return f"Analisi della Scuola {identifier}" if identifier else "Report Scuola"
    return "Report"


def refresh_data():
    """Forza il refresh dei dati."""
    load_meta_registry.clear()
    st.rerun()


# === MAIN PAGE ===
st.title("📄 Sintesi delle Best Practice")

st.markdown("""
Questa sezione raccoglie le **sintesi delle migliori pratiche di orientamento**
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
tab_tematici, tab_regionali, tab_scuole, tab_nazionale, tab_info = st.tabs([
    "🎯 Per Tema", "🗺️ Per Regione", "🏫 Per Scuola", "🇮🇹 Italia", "ℹ️ Info"
])

# === TAB TEMATICI ===
with tab_tematici:
    st.subheader("🎯 Approfondimenti Tematici")

    st.markdown("""
    Esplora le best practice organizzate per **area tematica**. Ogni report analizza
    come le scuole italiane affrontano uno specifico aspetto dell'orientamento,
    evidenziando le esperienze piu innovative e replicabili.
    """)

    if available_reports["thematic"]:
        # Organizza per categoria
        structural = []
        opportunity = []

        structural_dims = ["finalita", "obiettivi", "governance", "didattica", "partnership"]
        opportunity_dims = ["pcto", "stage", "openday", "visite", "laboratori", "testimonianze", "counseling", "alumni"]

        for r in available_reports["thematic"]:
            dim = r["dimension"]
            if dim in structural_dims:
                structural.append(r)
            elif dim in opportunity_dims:
                opportunity.append(r)

        st.markdown("---")

        # Dimensioni Strutturali
        if structural:
            st.markdown("### 📋 Aspetti Organizzativi e Strategici")
            st.caption("Come le scuole pianificano e gestiscono l'orientamento")

            for r in structural:
                dim = r["dimension"]
                icon = DIM_ICONS.get(dim, "📄")
                title = DIM_TITLES.get(dim, dim.title())
                desc = DIM_DESCRIPTIONS.get(dim, "")
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"{icon} {title}", key=f"btn_struct_{dim}", use_container_width=True):
                        st.session_state["selected_report"] = r["path"]
                        st.session_state["selected_report_title"] = title
                        st.session_state["selected_report_type"] = "thematic"
                        st.session_state["selected_report_id"] = dim
                    st.caption(desc)
                with col2:
                    st.caption(f"Agg. {mtime}")

        st.markdown("---")

        # Dimensioni Opportunita
        if opportunity:
            st.markdown("### 🚀 Attivita e Opportunita per gli Studenti")
            st.caption("Le esperienze concrete offerte agli studenti")

            for r in opportunity:
                dim = r["dimension"]
                icon = DIM_ICONS.get(dim, "📄")
                title = DIM_TITLES.get(dim, dim.title())
                desc = DIM_DESCRIPTIONS.get(dim, "")
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"{icon} {title}", key=f"btn_opp_{dim}", use_container_width=True):
                        st.session_state["selected_report"] = r["path"]
                        st.session_state["selected_report_title"] = title
                        st.session_state["selected_report_type"] = "thematic"
                        st.session_state["selected_report_id"] = dim
                    st.caption(desc)
                with col2:
                    st.caption(f"Agg. {mtime}")

    else:
        st.info("I report tematici saranno disponibili a breve. Stiamo elaborando le analisi delle scuole.")

# === TAB REGIONALI ===
with tab_regionali:
    st.subheader("🗺️ Best Practice per Regione")

    st.markdown("""
    Scopri le **migliori pratiche di orientamento** suddivise per territorio.
    Ogni report regionale presenta una sintesi delle esperienze piu significative
    delle scuole di quella regione.
    """)

    if available_reports["regional"]:
        st.markdown("---")

        # Ordina per regione
        sorted_reports = sorted(available_reports["regional"], key=lambda x: x["region"])

        cols = st.columns(3)
        for i, r in enumerate(sorted_reports):
            with cols[i % 3]:
                region = r["region"].title()
                mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

                if st.button(f"🗺️ {region}", key=f"btn_reg_{r['region']}", use_container_width=True):
                    st.session_state["selected_report"] = r["path"]
                    st.session_state["selected_report_title"] = f"Le Migliori Pratiche in {region}"
                    st.session_state["selected_report_type"] = "regional"
                    st.session_state["selected_report_id"] = r["region"]

                st.caption(f"Aggiornato: {mtime}")
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

        # Filtra
        filtered_schools = available_reports["schools"]
        if search_school:
            filtered_schools = [r for r in filtered_schools if search_school.upper() in r["code"].upper()]

        # Ordina per codice
        sorted_reports = sorted(filtered_schools, key=lambda x: x["code"])

        st.markdown(f"**{len(sorted_reports)} scuole** con report disponibile")

        st.markdown("---")

        # Mostra lista
        for r in sorted_reports[:30]:
            code = r["code"]
            mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y")

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{code}**")
            with col2:
                st.caption(f"Agg. {mtime}")
            with col3:
                if st.button("📄 Leggi", key=f"btn_school_{code}"):
                    st.session_state["selected_report"] = r["path"]
                    st.session_state["selected_report_title"] = f"Analisi Scuola {code}"
                    st.session_state["selected_report_type"] = "school"
                    st.session_state["selected_report_id"] = code

        if len(sorted_reports) > 30:
            st.info(f"Mostrate le prime 30 scuole. Usa la ricerca per trovare una scuola specifica.")

    else:
        st.info("I report delle singole scuole saranno disponibili a breve.")

# === TAB NAZIONALE ===
with tab_nazionale:
    st.subheader("🇮🇹 Panorama Nazionale")

    st.markdown("""
    Una **visione d'insieme** delle migliori pratiche di orientamento
    a livello nazionale. Questo report sintetizza le tendenze, i punti di forza
    e le aree di miglioramento emerse dall'analisi di tutte le scuole italiane.
    """)

    if available_reports["national"]:
        r = available_reports["national"][0]
        mtime = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y alle %H:%M")

        st.success(f"Report nazionale disponibile - Ultimo aggiornamento: {mtime}")

        if st.button("📄 Leggi il Report Nazionale", use_container_width=True):
            st.session_state["selected_report"] = r["path"]
            st.session_state["selected_report_title"] = "Panorama Nazionale delle Best Practice"
            st.session_state["selected_report_type"] = "national"
            st.session_state["selected_report_id"] = "italia"
    else:
        st.info("Il report nazionale sara disponibile a breve, una volta completata l'analisi delle scuole.")

# === TAB INFO ===
with tab_info:
    st.subheader("ℹ️ Informazioni sui Report")

    st.markdown("""
    ### Cosa sono questi report?

    I report di sintesi sono **documenti generati automaticamente** che raccolgono e
    analizzano le migliori pratiche di orientamento emerse dai PTOF (Piano Triennale
    dell'Offerta Formativa) delle scuole italiane.

    ### Come vengono generati?

    Un sistema di intelligenza artificiale analizza i dati strutturati estratti dai PTOF
    e produce sintesi ragionate che evidenziano:

    - **Pratiche innovative** adottate dalle scuole
    - **Pattern comuni** nelle strategie di orientamento
    - **Punti di forza** da valorizzare
    - **Suggerimenti** per il miglioramento

    ### Tipi di report disponibili

    | Tipo | Contenuto |
    |------|-----------|
    | **Tematici** | Approfondimento su un aspetto specifico dell'orientamento (es. PCTO, stage, counseling) |
    | **Regionali** | Sintesi delle best practice di una regione |
    | **Per Scuola** | Analisi dettagliata di una singola istituzione |
    | **Nazionale** | Panoramica complessiva delle pratiche italiane |

    ### Frequenza di aggiornamento

    I report vengono rigenerati periodicamente per includere le nuove analisi.
    La data di ultimo aggiornamento e indicata accanto a ogni report.

    ### Come utilizzare questi report

    - **Dirigenti scolastici**: per confrontare le proprie pratiche con quelle di altre scuole
    - **Docenti**: per scoprire metodologie innovative da adottare
    - **Famiglie e studenti**: per conoscere le opportunita offerte dalle scuole
    - **Ricercatori**: per analizzare le tendenze nell'orientamento scolastico italiano
    """)

# === VISUALIZZAZIONE REPORT SELEZIONATO ===
if "selected_report" in st.session_state and st.session_state["selected_report"]:
    st.markdown("---")

    report_path = Path(st.session_state["selected_report"])
    report_title = st.session_state.get("selected_report_title", "Report")

    # Pulsante chiudi in alto a destra
    if st.button("❌ Chiudi report"):
        del st.session_state["selected_report"]
        if "selected_report_title" in st.session_state:
            del st.session_state["selected_report_title"]
        if "selected_report_type" in st.session_state:
            del st.session_state["selected_report_type"]
        if "selected_report_id" in st.session_state:
            del st.session_state["selected_report_id"]
        st.rerun()

    if report_path.exists():
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pulisci il contenuto markdown
            # 1. Rimuovi frontmatter YAML (tra ---)
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            # 2. Rimuovi blocchi di codice markdown
            content = re.sub(r'^```markdown\s*\n?', '', content)
            content = re.sub(r'^```\s*\n?', '', content)
            content = re.sub(r'\n?```\s*$', '', content)
            content = content.strip()

            # Mostra il contenuto direttamente
            st.markdown(content)

            # Download button
            st.download_button(
                "📥 Scarica Report",
                data=content.encode('utf-8'),
                file_name=f"{report_title.replace(' ', '_')}.md",
                mime="text/markdown"
            )

        except Exception as e:
            st.error(f"Errore nel caricamento del report.")
    else:
        st.error("Report non disponibile.")
        del st.session_state["selected_report"]

render_footer()
