# 🏫 Dettaglio Scuola - Analisi singola scuola con Gap Analysis e Peer Comparison
# Accorpa: 07_Dettaglio_Scuola + 12_Gap_Analysis + 13_Confronto_Peer

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import glob
import numpy as np
import csv
from data_utils import (
    render_footer,
    scale_to_pct,
    format_pct,
    recalculate_weighted_index,
    load_summary_data,
    get_index_column
)
from page_control import setup_page, switch_page

st.set_page_config(page_title="ORIENTA+ | Dettaglio Scuola", page_icon="🧭", layout="wide")
setup_page("pages/09_Scuola.py")

# CSS
st.markdown("""
<style>
    div[data-baseweb="select"] > div { font-size: 0.85rem !important; }
    div[data-baseweb="popover"] li { font-size: 0.8rem !important; white-space: normal !important; }
    div[data-testid="stMetric"] { padding: 8px !important; }
    div[data-testid="stMetric"] label { font-size: 0.75rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 0.95rem !important; }
</style>
""", unsafe_allow_html=True)

SUMMARY_FILE = 'data/analysis_summary.csv'
ACTIVITIES_META_FILE = 'data/attivita.json'
ACTIVITIES_CSV = 'data/attivita.csv'

DIMENSIONS = {
    'mean_finalita': 'Finalita',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunita'
}

LABEL_MAP = {
    'mean_finalita': 'Media Finalita',
    'mean_obiettivi': 'Media Obiettivi',
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunita',
}

# Sotto-indicatori per Gap Analysis
SUB_INDICATORS = {
    'Finalita': {
        '2_3_finalita_attitudini_score': 'Attitudini',
        '2_3_finalita_interessi_score': 'Interessi',
        '2_3_finalita_progetto_vita_score': 'Progetto di Vita',
        '2_3_finalita_transizioni_formative_score': 'Transizioni Formative',
        '2_3_finalita_capacita_orientative_opportunita_score': 'Capacita Orientative'
    },
    'Obiettivi': {
        '2_4_obiettivo_ridurre_abbandono_score': 'Ridurre Abbandono',
        '2_4_obiettivo_continuita_territorio_score': 'Continuita Territorio',
        '2_4_obiettivo_contrastare_neet_score': 'Contrastare NEET',
        '2_4_obiettivo_lifelong_learning_score': 'Lifelong Learning'
    },
    'Governance': {
        '2_5_azione_coordinamento_servizi_score': 'Coordinamento Servizi',
        '2_5_azione_dialogo_docenti_studenti_score': 'Dialogo Docenti-Studenti',
        '2_5_azione_rapporto_scuola_genitori_score': 'Rapporto Scuola-Genitori',
        '2_5_azione_monitoraggio_azioni_score': 'Monitoraggio Azioni',
        '2_5_azione_sistema_integrato_inclusione_fragilita_score': 'Inclusione Fragilita'
    },
    'Didattica': {
        '2_6_didattica_da_esperienza_studenti_score': 'Esperienza Studenti',
        '2_6_didattica_laboratoriale_score': 'Laboratoriale',
        '2_6_didattica_flessibilita_spazi_tempi_score': 'Flessibilita Spazi/Tempi',
        '2_6_didattica_interdisciplinare_score': 'Interdisciplinare'
    },
    'Opportunita': {
        '2_7_opzionali_culturali_score': 'Culturali',
        '2_7_opzionali_laboratoriali_espressive_score': 'Laboratoriali Espressive',
        '2_7_opzionali_ludiche_ricreative_score': 'Ludiche Ricreative',
        '2_7_opzionali_volontariato_score': 'Volontariato',
        '2_7_opzionali_sportive_score': 'Sportive'
    }
}

# Raccomandazioni per Gap Analysis
RECOMMENDATIONS = {
    '2_3_finalita_attitudini_score': ["Introdurre test attitudinali standardizzati", "Creare portfolio delle competenze individuali", "Implementare colloqui orientativi personalizzati"],
    '2_3_finalita_interessi_score': ["Organizzare giornate di esplorazione professionale", "Creare laboratori di scoperta interessi", "Attivare questionari di auto-valutazione"],
    '2_3_finalita_progetto_vita_score': ["Sviluppare percorsi di life design", "Integrare educazione alla scelta nel curriculum", "Coinvolgere famiglie nel progetto orientativo"],
    '2_3_finalita_transizioni_formative_score': ["Potenziare raccordo con ordini scolastici successivi", "Creare momenti di continuita verticale", "Organizzare visite presso scuole/universita"],
    '2_3_finalita_capacita_orientative_opportunita_score': ["Sviluppare competenze di decision making", "Formare all'analisi delle opportunita formative", "Creare mappe delle opportunita territoriali"],
    '2_4_obiettivo_ridurre_abbandono_score': ["Attivare sistema di early warning", "Creare percorsi di ri-motivazione", "Potenziare tutoring individuale"],
    '2_4_obiettivo_continuita_territorio_score': ["Stringere accordi con enti locali", "Creare rete con associazioni territoriali", "Mappare risorse del territorio"],
    '2_4_obiettivo_contrastare_neet_score': ["Attivare percorsi di alternanza scuola-lavoro", "Creare connessioni con centri per l'impiego", "Organizzare incontri con mondo del lavoro"],
    '2_4_obiettivo_lifelong_learning_score': ["Promuovere competenze di apprendimento permanente", "Sviluppare metacognizione negli studenti", "Creare portfolio competenze trasferibili"],
    '2_5_azione_coordinamento_servizi_score': ["Nominare referente orientamento dedicato", "Creare cabina di regia per l'orientamento", "Definire protocolli di coordinamento"],
    '2_5_azione_dialogo_docenti_studenti_score': ["Istituzionalizzare momenti di dialogo", "Formare docenti all'ascolto attivo", "Creare spazi di confronto informale"],
    '2_5_azione_rapporto_scuola_genitori_score': ["Organizzare incontri orientativi con famiglie", "Creare canali di comunicazione dedicati", "Coinvolgere genitori come testimonial professionali"],
    '2_5_azione_monitoraggio_azioni_score': ["Definire indicatori di monitoraggio", "Creare sistema di raccolta feedback", "Implementare cicli di miglioramento continuo"],
    '2_5_azione_sistema_integrato_inclusione_fragilita_score': ["Attivare percorsi personalizzati per fragili", "Creare rete con servizi sociali", "Formare docenti su bisogni speciali orientativi"],
    '2_6_didattica_da_esperienza_studenti_score': ["Implementare project-based learning", "Valorizzare esperienze extra-scolastiche", "Creare portfolio esperienziale"],
    '2_6_didattica_laboratoriale_score': ["Aumentare ore di laboratorio", "Creare laboratori interdisciplinari", "Attivare learning by doing"],
    '2_6_didattica_flessibilita_spazi_tempi_score': ["Ripensare organizzazione oraria", "Creare spazi flessibili di apprendimento", "Sperimentare moduli intensivi"],
    '2_6_didattica_interdisciplinare_score': ["Progettare UDA interdisciplinari", "Creare team di docenti per aree", "Sviluppare competenze trasversali"],
    '2_7_opzionali_culturali_score': ["Ampliare offerta culturale pomeridiana", "Creare partnership con musei/teatri", "Organizzare eventi culturali interni"],
    '2_7_opzionali_laboratoriali_espressive_score': ["Attivare laboratori artistici/creativi", "Creare spazi maker", "Promuovere espressione artistica"],
    '2_7_opzionali_ludiche_ricreative_score': ["Valorizzare momento ricreativo", "Creare spazi di socializzazione", "Organizzare eventi ludici strutturati"],
    '2_7_opzionali_volontariato_score': ["Attivare progetti di service learning", "Creare partnership con associazioni", "Valorizzare esperienze di volontariato"],
    '2_7_opzionali_sportive_score': ["Ampliare offerta sportiva", "Creare gruppi sportivi scolastici", "Partnership con associazioni sportive"]
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    df = load_summary_data(apply_weights=True)
    if df.empty:
        return pd.DataFrame()
    
    idx_col = get_index_column(df)
    num_cols = list(DIMENSIONS.keys()) + [idx_col, 'partnership_count', 'activities_count']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calcolo IDPO (Logica: >= 5/7 = Robusto, >= 4/7 = Parziale)
    if idx_col in df.columns:
        df['completeness_status'] = df[idx_col].apply(
            lambda x: 'Robusto' if x >= 5.0 else ('Parziale' if x >= 4.0 else 'Da rafforzare')
        )
    return df

@st.cache_data(ttl=60)
def load_activities():
    # Prova JSON (solo se contiene ancora l'array pratiche)
    if os.path.exists(ACTIVITIES_META_FILE):
        try:
            with open(ACTIVITIES_META_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            practices = data.get('practices', [])
            if isinstance(practices, list) and practices:
                return practices
        except Exception:
            pass

    # Fallback CSV (formato attuale)
    if os.path.exists(ACTIVITIES_CSV):
        try:
            def pipe_to_list(val):
                if not val:
                    return []
                return [v.strip() for v in str(val).split('|') if v.strip()]

            practices = []
            with open(ACTIVITIES_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    maturity = row.get('maturity_index')
                    try:
                        maturity = float(maturity) if maturity else None
                    except (ValueError, TypeError):
                        maturity = None

                    practices.append({
                        'id': row.get('id', ''),
                        'school': {
                            'codice_meccanografico': row.get('codice_meccanografico', ''),
                            'nome': row.get('nome_scuola', ''),
                            'tipo_scuola': row.get('tipo_scuola', ''),
                            'ordine_grado': row.get('ordine_grado', ''),
                            'regione': row.get('regione', ''),
                            'provincia': row.get('provincia', ''),
                            'comune': row.get('comune', ''),
                            'area_geografica': row.get('area_geografica', ''),
                            'territorio': row.get('territorio', ''),
                            'statale_paritaria': row.get('statale_paritaria', ''),
                        },
                        'pratica': {
                            'categoria': row.get('categoria', ''),
                            'titolo': row.get('titolo', ''),
                            'descrizione': row.get('descrizione', ''),
                            'metodologia': row.get('metodologia', ''),
                            'tipologie_metodologia': pipe_to_list(row.get('tipologie_metodologia', '')),
                            'ambiti_attivita': pipe_to_list(row.get('ambiti_attivita', '')),
                            'target': row.get('target', ''),
                            'citazione_ptof': row.get('citazione_ptof', ''),
                            'pagina_evidenza': row.get('pagina_evidenza', ''),
                        },
                        'contesto': {
                            'maturity_index': maturity,
                            'partnership_coinvolte': pipe_to_list(row.get('partnership_coinvolte', '')),
                        },
                        'metadata': {
                            'extracted_at': row.get('extracted_at', ''),
                            'model_used': row.get('model_used', ''),
                            'source_file': row.get('source_file', ''),
                        },
                    })
            return practices
        except Exception:
            pass
    return []

# === FUNZIONI HELPER ===

def get_radar_benchmark(df, school_data, comparison_mode):
    if comparison_mode == "Media per Tipologia":
        tipo = str(school_data.get('tipo_scuola', '')).split(',')[0].strip()
        if tipo:
            filtered = df[df['tipo_scuola'].str.contains(tipo, na=False, case=False)]
            label = f"Media Tipologia: {tipo}"
        else:
            filtered = df
            label = "Media Nazionale"
    elif comparison_mode == "Media per Area Geografica":
        area = str(school_data.get('area_geografica', '')).strip()
        if area and area.lower() not in ['nd', 'nan', 'none']:
            filtered = df[df['area_geografica'] == area]
            label = f"Media Area: {area}"
        else:
            filtered = df
            label = "Media Nazionale"
    else:
        filtered = df
        label = "Media Nazionale"

    if filtered.empty:
        return df, "Media Nazionale", True
    return filtered, label, False


def get_school_practices(practices, school_id):
    return [
        p for p in practices
        if p.get('school', {}).get('codice_meccanografico') == school_id
    ]


def _normalize_text(value):
    return str(value or "").strip().lower()


def _practice_similarity_score(practice, school_data):
    score = 0
    school_tipo = _normalize_text(school_data.get('tipo_scuola'))
    school_area = _normalize_text(school_data.get('area_geografica'))
    school_regione = _normalize_text(school_data.get('regione'))

    practice_school = practice.get('school', {})
    practice_tipo = _normalize_text(practice_school.get('tipo_scuola'))
    practice_area = _normalize_text(practice_school.get('area_geografica'))
    practice_regione = _normalize_text(practice_school.get('regione'))

    if school_tipo:
        school_types = [t.strip() for t in school_tipo.split(',') if t.strip()]
        if any(t in practice_tipo for t in school_types):
            score += 2
    if school_area and school_area == practice_area:
        score += 1
    if school_regione and school_regione == practice_regione:
        score += 1
    return score


def get_similar_practices(practices, school_data, max_items=5):
    ranked = []
    for practice in practices:
        score = _practice_similarity_score(practice, school_data)
        if score > 0:
            ranked.append((score, practice))
    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].get('contesto', {}).get('maturity_index') or 0
        ),
        reverse=True
    )
    return [item[1] for item in ranked[:max_items]]


def get_best_in_class(df, tipo_scuola=None, ordine_grado=None):
    filtered = df.copy()
    if tipo_scuola and tipo_scuola != "Tutti":
        filtered = filtered[filtered['tipo_scuola'].str.contains(tipo_scuola, na=False, case=False)]
    if ordine_grado and ordine_grado != "Tutti":
        filtered = filtered[filtered['ordine_grado'].str.contains(ordine_grado, na=False, case=False)]
    if filtered.empty:
        return None
    return filtered.loc[filtered[INDEX_COL].idxmax()]

def calculate_gap(school, benchmark):
    gaps = {}
    for col, name in DIMENSIONS.items():
        school_val = float(school.get(col, 0) or 0)
        bench_val = float(benchmark.get(col, 0) or 0)
        gaps[name] = {
            'school': school_val,
            'benchmark': bench_val,
            'gap': bench_val - school_val,
            'gap_pct': 0 # not needed as gap is already in punti
        }
    return gaps

def get_priority_areas(school, df, top_n=3):
    priorities = []
    for dim_col, dim_name in DIMENSIONS.items():
        if dim_name in SUB_INDICATORS:
            for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                sub_val = float(school.get(sub_col, 0) or 0)
                sub_mean = float(df[sub_col].mean() if sub_col in df.columns else 4)
                if sub_val < sub_mean:
                    priorities.append({
                        'dimension': dim_name,
                        'indicator': sub_name,
                        'column': sub_col,
                        'score': sub_val,
                        'mean': sub_mean,
                        'gap': sub_mean - sub_val,
                        'priority_score': (sub_mean - sub_val) * (100 - sub_val)
                    })
    return sorted(priorities, key=lambda x: x['priority_score'], reverse=True)[:top_n]


# === CARICAMENTO DATI ===
df = load_data()
INDEX_COL = get_index_column(df) if not df.empty else 'weighted_index'

st.title("🏫 Dettaglio Scuola")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina analizza **una singola scuola** con un approccio completo: profilo, gap analysis e confronto con peer.

    ### 📊 Sezioni Disponibili

    **📊 Profilo**
    - Dati generali, radar delle 5 dimensioni e punteggi dettagliati
    - Posizione in classifica e confronto sintetico

    **📄 Report Scuola**
    - Report MD/JSON, export PDF e documento PTOF originale

    **🌟 Attività**
    - Attività della scuola e suggerimenti da scuole simili

    **🎯 Gap Analysis**
    - Confronto con benchmark (best-in-class, media nazionale, top 10%)
    - Aree prioritarie, raccomandazioni operative
    - Piano di miglioramento e impatto stimato

    **👥 Confronto Peer**
    - Selezione scuole simili per tipo, grado, regione e territorio
    - Posizionamento relativo, confronto dimensionale, distribuzioni
    - Insight e benchmark suggerito
    """)

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# === SELEZIONE SCUOLA ===
search_query = st.text_input("🔍 Cerca (codice, nome, comune)", placeholder="es: MIIS08900V o Milano")

if search_query:
    search_upper = search_query.upper()
    filtered_df = df[
        df['school_id'].str.upper().str.contains(search_upper, na=False) |
        df['denominazione'].str.upper().str.contains(search_upper, na=False) |
        df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
    ]
    school_options = filtered_df['denominazione'].dropna().unique().tolist()
    st.caption(f"Trovate: {len(school_options)} scuole")
else:
    school_options = df['denominazione'].dropna().unique().tolist()

if not school_options:
    st.warning("Nessuna scuola trovata con questo filtro")
    st.stop()

if 'selected_school_name' not in st.session_state or st.session_state.selected_school_name not in school_options:
    st.session_state.selected_school_name = school_options[0]

current_index = school_options.index(st.session_state.selected_school_name)

def prev_school():
    new_index = int((current_index - 1) % len(school_options))
    st.session_state.selected_school_name = school_options[new_index]

def next_school():
    new_index = int((current_index + 1) % len(school_options))
    st.session_state.selected_school_name = school_options[new_index]

col_prev, col_sel, col_next = st.columns([1, 10, 1])

with col_prev:
    st.write("")
    st.write("")
    st.button("⬅️", on_click=prev_school, help="Scuola precedente", use_container_width=True)

with col_sel:
    selected_school = st.selectbox("Seleziona Scuola", school_options, key="selected_school_name")

with col_next:
    st.write("")
    st.write("")
    st.button("➡️", on_click=next_school, help="Scuola successiva", use_container_width=True)

if not selected_school:
    st.stop()

school_data = df[df['denominazione'] == selected_school].iloc[0]



# === INFO GENERALI ===
st.subheader("📋 Informazioni Generali")
st.markdown(f"**{school_data['denominazione']}**")

idx = school_data.get(INDEX_COL, 0)
overall_percentile = (df[INDEX_COL] < idx).mean() * 100 if pd.notna(idx) else 0

info_cols = st.columns(4)
with info_cols[0]:
    st.metric("Codice", school_data.get('school_id', 'N/D'))
with info_cols[1]:
    st.metric("Tipo", str(school_data.get('tipo_scuola', 'N/D'))[:20])
with info_cols[2]:
    st.metric("Area", school_data.get('area_geografica', 'N/D'))
with info_cols[3]:
    st.metric("Indice IDPO", format_pct(idx), help="Indice di informatività delle pratiche di orientamento")

info_cols2 = st.columns(4)
with info_cols2[0]:
    regione = school_data.get('regione', 'N/D')
    st.metric("Regione", regione if regione and regione != 'ND' else 'N/D')
with info_cols2[1]:
    provincia = school_data.get('provincia', 'N/D')
    st.metric("Provincia", provincia if provincia and provincia != 'ND' else 'N/D')
with info_cols2[2]:
    comune = school_data.get('comune', 'N/D')
    st.metric("Comune", comune if comune and comune != 'ND' else 'N/D')
with info_cols2[3]:
    statale = school_data.get('statale_paritaria', 'N/D')
    st.metric("Stato", statale if statale and statale != 'ND' else 'N/D')

info_cols3 = st.columns(2)
with info_cols3[0]:
    # Use percentage instead of text status as requested
    idx_val = school_data.get(INDEX_COL, 0)
    pct_str = format_pct(idx_val)
    st.metric("Stato IDPO", pct_str)
with info_cols3[1]:
    st.metric("Partnership", int(school_data.get('partnership_count', 0) or 0))

email = school_data.get('email', '')
pec = school_data.get('pec', '')
website = school_data.get('website', '')
indirizzo = school_data.get('indirizzo', '')
cap = school_data.get('cap', '')

has_contacts = any(str(v) not in ['', 'ND', 'nan', 'None'] for v in [email, pec, website, indirizzo])
if has_contacts:
    with st.expander("📧 Contatti e Indirizzo", expanded=False):
        if indirizzo and str(indirizzo) not in ['ND', 'nan', 'None', '']:
            addr = f"{indirizzo}"
            if cap and str(cap) not in ['ND', 'nan', 'None', '']:
                addr += f" - {cap}"
            if comune and str(comune) not in ['ND', 'nan', 'None', '']:
                addr += f" {comune}"
            st.write(f"📍 **Indirizzo:** {addr}")
        if email and str(email) not in ['ND', 'nan', 'None', '']:
            st.write(f"📧 **Email:** {email}")
        if pec and str(pec) not in ['ND', 'nan', 'None', '']:
            st.write(f"📨 **PEC:** {pec}")
        if website and str(website) not in ['ND', 'nan', 'None', '']:
            url = website if str(website).startswith('http') else f'https://{website}'
            st.write(f"🌐 **Sito Web:** [{website}]({url})")

st.info("""
💡 **A cosa serve**: Fornisce una panoramica della scuola con i dati identificativi e il livello di completezza del PTOF sull'orientamento.

🔍 **Cosa rileva**: L'**IDPO** (scala 1-7) indica quanto il PTOF sia ricco di informazioni pertinenti. Un valore alto significa che il documento copre in modo esaustivo le dimensioni richieste.

🎯 **Implicazioni**: Un valore vicino a 7 indica un documento ben strutturato. Valori bassi (vicini a 1) suggeriscono che mancano sezioni fondamentali o dettagli sulle attività di orientamento.
""")

st.markdown("---")

# === TABS PRINCIPALI ===
radar_cols = list(DIMENSIONS.keys())

tab_profilo, tab_report, tab_practices, tab_gap, tab_matching, tab_suggestions = st.tabs([
    "📊 Profilo", "📄 Report Scuola", "🌟 Attività", "🎯 Gap Analysis",
    "🔍 Matching Avanzato", "💡 Suggerimenti"
])

# === TAB PROFILO ===
with tab_profilo:
    comparison_options = ["Media per Tipologia", "Media per Area Geografica", "Media Nazionale"]
    comparison_mode = st.selectbox("Confronto Radar", comparison_options, index=0, key="radar_comparison_mode")
    benchmark_df, benchmark_label, fallback_used = get_radar_benchmark(df, school_data, comparison_mode)
    benchmark_means = {col: benchmark_df[col].mean() for col in radar_cols}

    if fallback_used:
        st.info("Confronto specifico non disponibile, mostrata la media nazionale.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🕸️ Profilo Radar")
        if all(c in df.columns for c in radar_cols):
            school_vals = [float(school_data.get(c, 0)) if pd.notna(school_data.get(c)) else 0 for c in radar_cols]
            benchmark_vals = [float(benchmark_means.get(c, 0)) for c in radar_cols]
            labels = list(DIMENSIONS.values())

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=school_vals + [school_vals[0]], theta=labels + [labels[0]],
                                           fill='toself', name=selected_school[:25],
                                           line_color='#1f77b4'))
            fig.add_trace(go.Scatterpolar(r=benchmark_vals + [benchmark_vals[0]], theta=labels + [labels[0]],
                                           fill='toself', name=benchmark_label, opacity=0.5,
                                           line_color='#ff7f0e'))
            fig.update_layout(polar=dict(radialaxis=dict(range=[1, 7])), showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.info(f"""
💡 **A cosa serve**: Mostra il "profilo" della scuola sulle 5 dimensioni dell'orientamento, confrontato con **{benchmark_label}**.

🔍 **Cosa rileva**: L'area blu è la scuola, quella arancione è {benchmark_label}. Dove il blu "esce" dall'arancione, la scuola eccelle. Dove è "dentro", c'è margine di miglioramento.

🎯 **Implicazioni**: Identifica rapidamente punti di forza (da valorizzare nella comunicazione) e aree critiche (dove investire in formazione o risorse).
""")

    with col2:
        st.subheader("📊 Punteggi Dimensionali")
        st.caption(f"Confronto: {benchmark_label}")
        for col_key, col_name in DIMENSIONS.items():
            val = float(school_data.get(col_key, 0) or 0)
            mean_val = float(benchmark_means.get(col_key, 0) or 0)
            delta = val - mean_val
            st.metric(col_name, f"{val:.1f}%", f"{delta:+.1f}%", delta_color="normal")

    # Punteggi dettagliati per dimensione (Cards con Gauge)
    st.subheader("📊 Punteggi Dettagliati per Dimensione")

    # Calcolo indice pesato
    weighted_result = recalculate_weighted_index(school_data)
    original_idx = weighted_result["original_index"]
    weighted_idx = weighted_result["weighted_index"]
    idx_diff = weighted_idx - original_idx

    # Mostra confronto indice originale vs pesato
    if abs(idx_diff) > 0.01:
        idx_cols = st.columns([1, 1, 1])
        with idx_cols[0]:
            st.metric("Indice Originale (CSV)", f"{original_idx:.2f}/7")
        with idx_cols[1]:
            delta_color = "normal" if idx_diff >= 0 else "inverse"
            st.metric("Indice Pesato", f"{weighted_idx:.2f}/7", f"{idx_diff:+.2f}", delta_color=delta_color)
        with idx_cols[2]:
            st.info("⚖️ I pesi sono configurabili dalla pagina **Gestione Pesi** (admin)")
        st.markdown("")

    # Funzione per creare gauge
    def create_gauge(value, title):
        # Colore basato sul valore
        if value >= 5:
            bar_color = "#2ecc71"  # Verde
        elif value >= 3.5:
            bar_color = "#f39c12"  # Giallo/Arancione
        else:
            bar_color = "#e74c3c"  # Rosso

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number={'suffix': '/7', 'font': {'size': 24}},
            gauge={
                'axis': {'range': [1, 7], 'tickwidth': 1},
                'bar': {'color': bar_color},
                'bgcolor': "white",
                'steps': [
                    {'range': [1, 3], 'color': '#fadbd8'},
                    {'range': [3, 5], 'color': '#fef9e7'},
                    {'range': [5, 7], 'color': '#d5f5e3'}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.75,
                    'value': value
                }
            }
        ))
        fig.update_layout(
            height=150,
            margin=dict(l=20, r=20, t=30, b=10),
            font={'size': 12}
        )
        return fig

    # Funzione per colore barra di progresso
    def get_score_color(score):
        if score >= 5:
            return "#2ecc71"
        elif score >= 3.5:
            return "#f39c12"
        else:
            return "#e74c3c"

    # Prima riga: Finalità, Obiettivi, Governance
    row1_cols = st.columns(3)
    dims_row1 = ['Finalita', 'Obiettivi', 'Governance']
    dim_icons = {'Finalita': '🎯', 'Obiettivi': '📌', 'Governance': '🏛️', 'Didattica': '📚', 'Opportunita': '🌟'}

    for col, dim_name in zip(row1_cols, dims_row1):
        with col:
            dim_col = [k for k, v in DIMENSIONS.items() if v == dim_name]
            mean_val = float(school_data.get(dim_col[0], 0) or 0) if dim_col else 0

            st.markdown(f"#### {dim_icons.get(dim_name, '')} {dim_name}")
            st.plotly_chart(create_gauge(mean_val, dim_name), use_container_width=True, key=f"gauge_{dim_name}")

            # Sotto-indicatori
            if dim_name in SUB_INDICATORS:
                for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                    sub_val = float(school_data.get(sub_col, 0) or 0)
                    color = get_score_color(sub_val)
                    pct = (sub_val - 1) / 6 * 100  # Normalizza 1-7 a 0-100%
                    st.markdown(f"""
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                            <span>{sub_name}</span>
                            <span style="font-weight: bold; color: {color};">{sub_val:.1f}</span>
                        </div>
                        <div style="background: #eee; border-radius: 4px; height: 8px; overflow: hidden;">
                            <div style="background: {color}; width: {pct}%; height: 100%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # Seconda riga: Didattica, Opportunità
    row2_cols = st.columns([1, 1, 1])
    dims_row2 = ['Didattica', 'Opportunita']

    for idx, dim_name in enumerate(dims_row2):
        with row2_cols[idx]:
            dim_col = [k for k, v in DIMENSIONS.items() if v == dim_name]
            mean_val = float(school_data.get(dim_col[0], 0) or 0) if dim_col else 0

            st.markdown(f"#### {dim_icons.get(dim_name, '')} {dim_name}")
            st.plotly_chart(create_gauge(mean_val, dim_name), use_container_width=True, key=f"gauge_{dim_name}")

            # Sotto-indicatori
            if dim_name in SUB_INDICATORS:
                for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                    sub_val = float(school_data.get(sub_col, 0) or 0)
                    color = get_score_color(sub_val)
                    pct = (sub_val - 1) / 6 * 100
                    st.markdown(f"""
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                            <span>{sub_name}</span>
                            <span style="font-weight: bold; color: {color};">{sub_val:.1f}</span>
                        </div>
                        <div style="background: #eee; border-radius: 4px; height: 8px; overflow: hidden;">
                            <div style="background: {color}; width: {pct}%; height: 100%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # Legenda
    with row2_cols[2]:
        st.markdown("#### 📖 Legenda")
        st.markdown("""
        <div style="padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 0.85em;">
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #2ecc71; border-radius: 2px; margin-right: 8px;"></span>
                <strong>5-7:</strong> Ampiamente documentato
            </div>
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #f39c12; border-radius: 2px; margin-right: 8px;"></span>
                <strong>3.5-5:</strong> Parzialmente documentato
            </div>
            <div>
                <span style="display: inline-block; width: 12px; height: 12px; background: #e74c3c; border-radius: 2px; margin-right: 8px;"></span>
                <strong>1-3.5:</strong> Poco documentato
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")
        st.info("""
**Cosa mostrano le cards:**
Ogni dimensione ha un gauge con la media e le barre mostrano i singoli indicatori.
Rosso = priorità di intervento.
""")

    st.markdown("---")

    # Posizione in classifica
    # Stato Completezza Dettagliata
    st.subheader("📋 Dettaglio Completezza")
    
    comp_cols = st.columns(3)
    with comp_cols[0]:
        st.write("**Stato Generale**")
        status = school_data.get('completeness_status', 'N/D')
        if status == 'Completo':
            st.success(f"✅ {status}")
        elif status == 'Parziale':
            st.warning(f"⚠️ {status}")
        else:
            st.error(f"❌ {status}")
    
    with comp_cols[1]:
        st.write("**Indice Numerico**")
        st.write(f"**{format_pct(idx)}**")

    with comp_cols[2]:
         missing = []
         if idx < 5.0:
             missing.append("Potenziamento generale richiesto")
         if not missing:
             st.write("Nessuna criticità rilevante.")
         else:
             st.write(f"Note: {', '.join(missing)}")

    st.info("""
💡 **A cosa serve**: Verifica se il PTOF soddisfa i criteri minimi di informazione sull'orientamento.

🔍 **Cosa rileva**: Non è una classifica, ma un check-up della documentazione.

🎯 **Implicazioni**: Utile per capire se la scuola ha formalizzato correttamente le proprie attività o se è necessario integrare il PTOF.
""")


# === TAB REPORT SCUOLA ===
with tab_report:
    st.subheader("📄 Report Scuola")
    school_id = school_data.get('school_id', '')

    md_files = glob.glob(f'analysis_results/*{school_id}*_analysis.md')
    if md_files:
        with st.expander("📝 Report Analisi Completo", expanded=True):
            with open(md_files[0], 'r') as f:
                st.markdown(f.read())
    else:
        st.info("Report MD non disponibile per questa scuola.")

    st.markdown("---")

    st.subheader("🧾 Dettaglio dal Report (JSON)")
    json_files = glob.glob(f'analysis_results/*{school_id}*_analysis.json')

    if json_files:
        try:
            with open(json_files[0], 'r') as f:
                json_data = json.load(f)

            sec2 = json_data.get('ptof_section2', {})

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🤝 Partnership")
                partnerships = sec2.get('2_2_partnership', {})
                partners = partnerships.get('partner_nominati', [])
                if partners:
                    st.write(f"**Numero Partner:** {len(partners)}")
                    for p in partners:
                        st.write(f"- {p}")
                else:
                    st.write("Nessuna partnership nominata")

            with col2:
                st.markdown("### 📋 Sezione Orientamento")
                s21 = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
                has_sez = "✅ Si" if s21.get('has_sezione_dedicata') else "❌ No"
                st.write(f"**Sezione dedicata:** {has_sez}")
                s21_score = float(s21.get('score', 0) or 0)
                st.write(f"**Punteggio:** {s21_score:.1f}%")
                if s21.get('note'):
                    st.caption(s21.get('note'))

            st.markdown("---")

            st.markdown("### 🎯 Finalita (dettaglio)")
            finalita = sec2.get('2_3_finalita', {})
            for key, val in finalita.items():
                if isinstance(val, dict):
                    score = float(val.get('score', 0) or 0)
                    st.write(f"**{get_label(key)}:** {score:.1f}%")

        except Exception as e:
            st.error(f"Errore caricamento JSON: {e}")
    else:
        st.info("Report JSON non ancora disponibile per questa scuola")

    st.markdown("---")

    st.subheader("📥 Report Scuola PDF")

    def generate_school_report_pdf(school_data, radar_cols, df):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from io import BytesIO

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                         fontSize=18, spaceAfter=12, textColor=colors.HexColor('#2c3e50'))
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                           fontSize=14, spaceAfter=8, textColor=colors.HexColor('#34495e'))
            normal_style = styles['Normal']

            story = []

            story.append(Paragraph("📋 Report Scuola", title_style))
            story.append(Paragraph(f"<b>{school_data.get('denominazione', 'N/D')}</b>", heading_style))
            story.append(Spacer(1, 12))

            info_data = [
                ['Codice Meccanografico', str(school_data.get('school_id', 'N/D'))],
                ['Tipo Scuola', str(school_data.get('tipo_scuola', 'N/D'))],
                ['Regione', str(school_data.get('regione', 'N/D'))],
                ['Provincia', str(school_data.get('provincia', 'N/D'))],
                ['Comune', str(school_data.get('comune', 'N/D'))],
                ['Statale/Paritaria', str(school_data.get('statale_paritaria', 'N/D'))],
            ]

            info_table = Table(info_data, colWidths=[6*cm, 10*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))

            # === INDICE SCORES ===
            ro_idx = school_data.get(INDEX_COL, 0)
            ro_pct = format_pct(ro_idx)
            status = school_data.get('completeness_status', 'N/D')
            
            # Colore in base allo status
            status_colors = {
                'Completo': colors.HexColor('#2ecc71'),  # Green
                'Parziale': colors.HexColor('#f1c40f'),  # Yellow
                'Incompleto': colors.HexColor('#e74c3c') # Red
            }
            status_col = status_colors.get(status, colors.black)

            # 1. Indice (Card Like)
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Indice di Completezza: {ro_pct}", 
                ParagraphStyle('ScoreStyle', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#2c3e50'))))
            story.append(Paragraph(f"Stato: <font color='{status_col.hexval()}'>{status}</font>",
                ParagraphStyle('StatusStyle', parent=styles['Normal'], fontSize=14, spaceAfter=12)))
            
            story.append(Spacer(1, 10))

            story.append(Paragraph("Punteggi per Dimensione", heading_style))

            dim_labels = ['Finalita', 'Obiettivi', 'Governance', 'Didattica Orientativa', 'Opportunita']
            dim_data = [['Dimensione', 'Punteggio']]

            for col, label in zip(radar_cols, dim_labels):
                val = school_data.get(col, 0)
                val_str = format_pct(val)
                dim_data.append([label, val_str])

            dim_table = Table(dim_data, colWidths=[8*cm, 4*cm])
            dim_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(dim_table)
            story.append(Spacer(1, 20))

            # Completeness Status in PDF
            story.append(Paragraph("Stato Completezza PTOF", heading_style))
            
            comp_status = "Incompleto"
            idx_val = idx if pd.notna(idx) else 0
            if idx_val >= 5.0: comp_status = "Completo"
            elif idx_val >= 3.0: comp_status = "Parziale"
            
            rank_data = [
                ['Stato', comp_status],
                ['Indice Completezza', format_pct(idx_val)],
            ]
            rank_table = Table(rank_data, colWidths=[6*cm, 10*cm])
            rank_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(rank_table)
            story.append(Spacer(1, 20))

            from datetime import datetime
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"<i>Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", normal_style))
            story.append(Paragraph("<i>Dashboard PTOF - Analisi IDPO</i>", normal_style))

            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()

        except ImportError:
            return None
        except Exception as e:
            st.error(f"Errore generazione PDF: {e}")
            return None

    try:
        pdf_bytes = generate_school_report_pdf(school_data, radar_cols, df)

        if pdf_bytes:
            col_pdf1, col_pdf2 = st.columns([1, 2])
            with col_pdf1:
                st.download_button(
                    label="📥 Scarica Report PDF",
                    data=pdf_bytes,
                    file_name=f"report_scuola_{school_data.get('school_id', 'scuola')}.pdf",
                    mime="application/pdf",
                    help="Scarica il report completo della scuola in formato PDF"
                )
            with col_pdf2:
                st.caption("Il report PDF include: dati anagrafici, punteggi per dimensione, posizione in classifica.")
        else:
            st.warning("⚠️ Per generare il PDF installa reportlab: `pip install reportlab`")

    except Exception as e:
        st.warning(f"Export PDF non disponibile: {e}")
        st.caption("Installa reportlab: `pip install reportlab`")

    st.markdown("---")

    st.subheader("📄 Documento PTOF Originale")

    pdf_path = None
    search_dirs = ["ptof_processed", "ptof_inbox"]
    try:
        from data_utils import find_pdf_for_school
        pdf_path = find_pdf_for_school(school_id, base_dirs=search_dirs)
    except Exception:
        pdf_patterns = []
        for base_dir in search_dirs:
            pdf_patterns.extend([
                os.path.join(base_dir, f"*{school_id}*.pdf"),
                os.path.join(base_dir, f"{school_id}*.pdf"),
                os.path.join(base_dir, f"*_{school_id}_*.pdf"),
                os.path.join(base_dir, "**", f"*{school_id}*.pdf"),
            ])
        pdf_files = []
        for pattern in pdf_patterns:
            pdf_files.extend(glob.glob(pattern, recursive=True))

        if not pdf_files:
            for base_dir in search_dirs:
                all_pdfs = glob.glob(os.path.join(base_dir, "**", "*.pdf"), recursive=True)
                for pdf in all_pdfs:
                    pdf_name = os.path.basename(pdf).upper()
                    if school_id.upper() in pdf_name:
                        pdf_files.append(pdf)
                        break
                if pdf_files:
                    break

        if pdf_files:
            pdf_path = sorted(set(pdf_files))[0]

    if pdf_path:
        st.success(f"📎 PDF trovato: `{os.path.basename(pdf_path)}`")

        try:
            import base64

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

            pdf_display = f"""
                <iframe src="data:application/pdf;base64,{base64_pdf}"
                        width="100%" height="800" type="application/pdf">
                </iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)

            st.download_button(
                label="📥 Scarica PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )

        except Exception as e:
            st.warning(f"Impossibile visualizzare il PDF inline: {e}")
            st.info("Usa il pulsante download per scaricare il file.")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Scarica PDF",
                    data=f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )
    else:
        st.info(f"📂 PDF non trovato per {school_id}. Verifica che il file sia in `ptof/` o `ptof_processed/`.")
        st.caption("Cartelle cercate: ptof/, ptof_processed/, ptof_inbox/")

# === TAB ATTIVITA ===
with tab_practices:
    st.subheader("🌟 Attività della Scuola")

    practices = load_activities()
    school_id = school_data.get('school_id', '')

    if not practices:
        st.info("Catalogo attività non disponibile. Verifica `data/attivita.json`.")
    else:
        school_practices = get_school_practices(practices, school_id)

        if school_practices:
            st.caption(f"Trovate {len(school_practices)} pratiche nel catalogo.")
            for practice in school_practices:
                pratica = practice.get('pratica', {})
                title = pratica.get('titolo', 'Pratica')
                category = pratica.get('categoria', 'Categoria')
                header = f"{category} - {title}"

                with st.expander(header, expanded=False):
                    descrizione = pratica.get('descrizione')
                    if descrizione:
                        st.markdown(f"**Descrizione:** {descrizione}")
                    metodologia = pratica.get('metodologia')
                    if metodologia:
                        st.markdown(f"**Metodologia:** {metodologia}")
                    target = pratica.get('target')
                    if target:
                        st.markdown(f"**Target:** {target}")

                    citazione = pratica.get('citazione_ptof')
                    pagina = pratica.get('pagina_evidenza')
                    if citazione:
                        st.markdown("**Evidenza dal PTOF:**")
                        st.markdown(f"> {citazione}")
                        if pagina:
                            st.caption(f"Evidenza: {pagina}")

                    contesto = practice.get('contesto', {})
                    maturity = contesto.get('maturity_index')
                    if maturity is not None:
                        st.caption(f"Indice maturita contesto: {maturity:.1f}/7")
                    partnerships = contesto.get('partnership_coinvolte', [])
                    if partnerships:
                        st.markdown("**Partnership coinvolte:** " + ", ".join(partnerships[:5]) +
                                    (" ..." if len(partnerships) > 5 else ""))
                    attivita = contesto.get('attivita_correlate', [])
                    if attivita:
                        st.markdown("**Attivita correlate:** " + ", ".join(attivita[:5]) +
                                    (" ..." if len(attivita) > 5 else ""))
        else:
            st.info("Nessuna pratica catalogata per questa scuola.")
            similar_practices = get_similar_practices(practices, school_data, max_items=5)
            if similar_practices:
                st.subheader("🔍 Buone pratiche da scuole simili")
                for practice in similar_practices:
                    pratica = practice.get('pratica', {})
                    school_info = practice.get('school', {})
                    title = pratica.get('titolo', 'Pratica')
                    category = pratica.get('categoria', 'Categoria')
                    school_name = school_info.get('nome', 'Scuola')
                    header = f"{category} - {title} - {school_name}"

                    with st.expander(header, expanded=False):
                        school_tag = " | ".join(filter(None, [
                            school_info.get('tipo_scuola'),
                            school_info.get('area_geografica'),
                            school_info.get('regione')
                        ]))
                        if school_tag:
                            st.caption(school_tag)
                        descrizione = pratica.get('descrizione')
                        if descrizione:
                            st.markdown(f"**Descrizione:** {descrizione}")
                        metodologia = pratica.get('metodologia')
                        if metodologia:
                            st.markdown(f"**Metodologia:** {metodologia}")
                        target = pratica.get('target')
                        if target:
                            st.markdown(f"**Target:** {target}")
            else:
                st.caption("Non ci sono pratiche simili disponibili nel catalogo.")

    if st.button("🌟 Vai al Attività", use_container_width=True):
        switch_page("pages/11_Attivita.py")
# === TAB GAP ANALYSIS ===
with tab_gap:
    st.subheader("🎯 Analisi Gap e Raccomandazioni")

    benchmark_type = st.selectbox("📊 Benchmark di riferimento", ["Best-in-Class Tipo", "Best-in-Class Grado", "Media Nazionale", "Top 10%"])

    # Determina benchmark
    if benchmark_type == "Best-in-Class Tipo":
        tipo = str(school_data.get('tipo_scuola', '')).split(',')[0].strip() if school_data.get('tipo_scuola') else None
        benchmark = get_best_in_class(df, tipo_scuola=tipo)
        bench_label = f"Migliore {tipo}" if tipo else "Migliore assoluta"
    elif benchmark_type == "Best-in-Class Grado":
        grado = str(school_data.get('ordine_grado', '')).split(',')[0].strip() if school_data.get('ordine_grado') else None
        benchmark = get_best_in_class(df, ordine_grado=grado)
        bench_label = f"Migliore {grado}" if grado else "Migliore assoluta"
    elif benchmark_type == "Top 10%":
        top_10 = df.nlargest(max(1, len(df)//10), INDEX_COL)
        benchmark = top_10.mean(numeric_only=True)
        benchmark['denominazione'] = "Media Top 10%"
        bench_label = "Media Top 10%"
    else:
        benchmark = df.mean(numeric_only=True)
        benchmark['denominazione'] = "Media Nazionale"
        bench_label = "Media Nazionale"

    if benchmark is None:
        st.warning("Nessun benchmark disponibile")
    else:
        gaps = calculate_gap(school_data, benchmark)

        st.subheader(f"📏 Gap rispetto a: {bench_label}")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Radar comparison
            categories = list(gaps.keys())
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[gaps[cat]['school'] for cat in categories],
                theta=categories, fill='toself',
                name=school_data['denominazione'][:30], line_color='blue'
            ))
            fig.add_trace(go.Scatterpolar(
                r=[gaps[cat]['benchmark'] for cat in categories],
                theta=categories, fill='toself',
                name=bench_label, line_color='green'
            ))
            fig.update_layout(polar=dict(radialaxis=dict(range=[1, 7])), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### 📊 Dettaglio Gap")
            for dim, vals in gaps.items():
                gap = vals['gap'] # in pct points
                color = "🔴" if gap > 10.0 else "🟡" if gap > 0 else "🟢"
                st.markdown(f"{color} **{dim}**: {vals['school']:.1f}% vs {vals['benchmark']:.1f}% (gap: {gap:+.1f} p.p.)")

        # Aree prioritarie
        st.markdown("---")
        st.subheader("🎯 Aree Prioritarie di Miglioramento")

        priorities = get_priority_areas(school_data, df, top_n=5)

        if priorities:
            prio_cols = st.columns(min(3, len(priorities)))
            for i, prio in enumerate(priorities[:3]):
                with prio_cols[i]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
                                padding: 15px; border-radius: 10px; color: white; text-align: center;">
                        <h4 style="margin:0;">#{i+1} {prio['indicator']}</h4>
                        <p style="margin:5px 0; font-size: 0.9em;">{prio['dimension']}</p>
                        <p style="margin:0; font-size: 1.5em; font-weight: bold;">
                            {prio['score']:.1f}% -> {min(100, prio['score']+30):.1f}%
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

            # Raccomandazioni
            st.markdown("---")
            st.subheader("💡 Raccomandazioni Operative")

            for prio in priorities[:3]:
                col = prio['column']
                if col in RECOMMENDATIONS:
                    target_score = min(100, prio['score'] + 30)
                    with st.expander(
                        f"📌 {prio['dimension']} - {prio['indicator']} (Score: {prio['score']:.1f}% → Target: {target_score:.1f}%)",
                        expanded=True
                    ):
                        for i, r in enumerate(RECOMMENDATIONS[col], 1):
                            st.markdown(f"{i}. {r}")

            st.markdown("---")
            st.subheader("📈 Piano di Miglioramento Suggerito")

            plan_data = []
            for prio in priorities[:5]:
                current = prio['score']
                target = min(100, current + 30)
                plan_data.append({
                    'Area': f"{prio['dimension']} - {prio['indicator']}",
                    'Attuale': f"{current:.1f}%",
                    'Target 6 mesi': f"{min(100, current + 15):.1f}%",
                    'Target 12 mesi': f"{target:.1f}%",
                    'Priorita': '🔴 Alta' if prio['gap'] > 20 else '🟡 Media' if prio['gap'] > 10 else '🟢 Bassa'
                })

            plan_df = pd.DataFrame(plan_data)
            st.dataframe(plan_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🚀 Impatto Stimato")

            current_index_raw = school_data.get(INDEX_COL, 0) or 0
            current_index = float(current_index_raw)
            current_percentile = (df[INDEX_COL] < current_index_raw).mean() * 100 if pd.notna(current_index_raw) else 0
            # gap is already in % points
            potential_gain = sum([min(30, p['gap']) for p in priorities[:3]]) / 5
            projected_index = min(100.0, current_index + potential_gain)
            
            # Estimate projected raw index for percentile calc
            projected_index_raw = 1 + (projected_index * 6 / 100)
            new_percentile = (df[INDEX_COL] < projected_index_raw).mean() * 100

            impact_cols = st.columns(3)
            with impact_cols[0]:
                st.metric("Indice Attuale", f"{current_index:.1f}%")
            with impact_cols[1]:
                st.metric("Indice Proiettato (12 mesi)", f"{projected_index:.1f}%", f"+{potential_gain:.1f}%")
            with impact_cols[2]:
                st.metric("Percentile Proiettato", f"{new_percentile:.0f}°", f"+{new_percentile - current_percentile:.0f}")
        else:
            st.success("✅ Questa scuola non presenta aree critiche evidenti!")

    st.markdown("---")
    st.caption("🎯 Gap Analysis - Sistema di analisi per il miglioramento continuo")



# === TAB MATCHING AVANZATO ===
with tab_matching:
    st.subheader("🔍 Matching Avanzato tra Scuole")

    st.markdown("""
    Questo strumento utilizza algoritmi avanzati per trovare scuole con cui confrontarti in modo più mirato.
    Puoi scegliere tra diverse strategie di matching a seconda dei tuoi obiettivi.
    """)

    # Import del match engine
    try:
        from match_engine import (
            advanced_peer_matching,
            DIMENSION_LABELS,
            compare_two_schools
        )
        match_engine_available = True
    except ImportError:
        match_engine_available = False
        st.warning("Modulo match_engine non disponibile. Assicurati che sia presente in app/match_engine.py")

    if match_engine_available:
        st.markdown("---")

        # Selezione strategia
        col_strat1, col_strat2 = st.columns([1, 2])

        with col_strat1:
            strategy = st.radio(
                "🎯 Strategia di Matching",
                ["similar", "complementary", "adjacent", "balanced"],
                format_func=lambda x: {
                    "similar": "🔵 Scuole Simili",
                    "complementary": "🟢 Scuole Complementari",
                    "adjacent": "🟡 Modelli Raggiungibili",
                    "balanced": "⚖️ Matching Bilanciato"
                }[x],
                help="Scegli la strategia di matching più adatta ai tuoi obiettivi"
            )

        with col_strat2:
            strategy_descriptions = {
                "similar": """
                **Scuole Simili**: Trova scuole con profilo molto simile al tuo.
                Utile per: creare reti, condividere esperienze, collaborare su progetti comuni.
                """,
                "complementary": """
                **Scuole Complementari**: Trova scuole forti nelle aree dove tu sei debole.
                Utile per: imparare dalle attività, trovare mentor, colmare gap specifici.
                """,
                "adjacent": """
                **Modelli Raggiungibili**: Trova scuole leggermente migliori di te.
                Utile per: fissare obiettivi realistici, trovare modelli imitabili a breve termine.
                """,
                "balanced": """
                **Matching Bilanciato**: Combinazione equilibrata di tutti i criteri.
                Utile per: esplorare senza un obiettivo specifico, scoprire opportunità varie.
                """
            }
            st.info(strategy_descriptions[strategy])

        # Configurazione
        with st.expander("⚙️ Opzioni avanzate", expanded=False):
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                n_results = st.slider("Numero di risultati", 5, 20, 10)
            with col_opt2:
                filter_region = st.checkbox("Limita alla stessa regione", False)

        # Applica filtri
        search_df = df.copy()
        if filter_region:
            search_df = search_df[search_df['regione'] == school_data.get('regione')]

        # Esegui matching
        if st.button("🔍 Trova Scuole", type="primary", use_container_width=True):
            with st.spinner("Analisi in corso..."):
                matches = advanced_peer_matching(
                    target_school=school_data,
                    df=search_df,
                    strategy=strategy,
                    top_n=n_results
                )

            if matches.empty:
                st.warning("Nessuna scuola trovata con i criteri selezionati.")
            else:
                st.success(f"Trovate {len(matches)} scuole!")

                # Visualizza risultati
                st.subheader("📋 Risultati del Matching")

                for i, (idx, match) in enumerate(matches.iterrows()):
                    with st.expander(
                        f"**{i+1}. {match['denominazione']}** — Score: {match['final_score']:.0f}/100 | Compl: {match[INDEX_COL]:.1f}/7",
                        expanded=(i < 3)
                    ):
                        col_info, col_scores = st.columns([1, 1])

                        with col_info:
                            st.markdown(f"""
                            - **Regione:** {match['regione']}
                            - **Provincia:** {match.get('provincia', 'N/D')}
                            - **Tipo:** {match['tipo_scuola']}
                            - **Indice Compl:** {match[INDEX_COL]:.1f}/7
                            """)
                            st.caption(f"💡 {match['explanation']}")

                        with col_scores:
                            # Mini radar comparativo
                            fig_mini = go.Figure()

                            # Scuola target
                            target_vals = [float(school_data.get(d, 0) or 0) for d in DIMENSION_LABELS.keys()]
                            match_vals = [float(match.get(d, 0) or 0) for d in DIMENSION_LABELS.keys()]
                            labels = list(DIMENSION_LABELS.values())

                            fig_mini.add_trace(go.Scatterpolar(
                                r=target_vals + [target_vals[0]],
                                theta=labels + [labels[0]],
                                fill='toself', name='Tu',
                                line_color='blue', opacity=0.6
                            ))
                            fig_mini.add_trace(go.Scatterpolar(
                                r=match_vals + [match_vals[0]],
                                theta=labels + [labels[0]],
                                fill='toself', name=match['denominazione'][:15],
                                line_color='green', opacity=0.6
                            ))
                            fig_mini.update_layout(
                                polar=dict(radialaxis=dict(range=[1, 7], showticklabels=False)),
                                showlegend=True,
                                height=250,
                                margin=dict(l=20, r=20, t=20, b=20)
                            )
                            st.plotly_chart(fig_mini, use_container_width=True)

                        # Mostra complementi se strategia complementare
                        if strategy == "complementary" and match.get('complements'):
                            st.markdown("**🎯 Aree dove questa scuola può aiutarti:**")
                            for comp in match['complements'][:3]:
                                dim_label = DIMENSION_LABELS.get(comp['dimension'], comp['dimension'])
                                st.markdown(
                                    f"- **{dim_label}**: Tu {comp['school1_score']:.1f}/7 → Lei {comp['school2_score']:.1f}/7 "
                                    f"(+{comp['gap_covered']:.1f})"
                                )

                # Tabella riepilogativa
                st.markdown("---")
                st.markdown("---")
                st.subheader("📊 Tabella Riepilogativa")

                display_matches = matches[['denominazione', 'regione', 'tipo_scuola',
                                          INDEX_COL, 'final_score']].copy()
                display_matches.columns = ['Scuola', 'Regione', 'Tipo', 'Indice Compl', 'Score Match']
                display_matches['Score Match'] = display_matches['Score Match'].round(0).astype(int)
                display_matches['Indice Compl'] = display_matches['Indice Compl'].apply(lambda x: f"{x:.1f}/7")

                st.dataframe(display_matches, use_container_width=True, hide_index=True)

                # Salva in session state per uso in altri tab
                st.session_state['last_matches'] = matches

    st.markdown("---")
    st.caption("🔍 Matching Avanzato - Trova scuole per creare reti e imparare dalle attività")

# === TAB SUGGERIMENTI PERSONALIZZATI ===
with tab_suggestions:
    st.subheader("💡 Suggerimenti Personalizzati di Miglioramento")

    st.markdown("""
    Questa sezione analizza le tue aree di debolezza e cerca scuole simili a te che eccellono
    in quelle aree, estraendo le loro pratiche e metodologie come fonte di ispirazione.
    """)

    try:
        from match_engine import (
            advanced_peer_matching,
            get_improvement_suggestions,
            DIMENSIONS as MATCH_DIMENSIONS,
            DIMENSION_LABELS
        )
        suggestions_available = True
    except ImportError:
        suggestions_available = False
        st.warning("Modulo match_engine non disponibile.")

    if suggestions_available:
        # Identifica le aree deboli
        st.markdown("---")
        st.subheader("🎯 Le tue Aree di Miglioramento")

        weak_areas = []
        for dim_col in MATCH_DIMENSIONS:
            val = school_data.get(dim_col, 0) or 0
            if val < 4:  # Sotto sufficienza
                weak_areas.append({
                    'dimension': dim_col,
                    'label': DIMENSION_LABELS.get(dim_col, dim_col),
                    'score': val,
                    'gap': 7 - val
                })

        if not weak_areas:
            st.success("🎉 Ottimo! Non hai aree critiche evidenti (tutte le dimensioni >= 4)")
            st.info("Puoi comunque cercare ispirazione dalle scuole eccellenti per migliorare ulteriormente.")
        else:
            weak_areas = sorted(weak_areas, key=lambda x: x['gap'], reverse=True)

            cols_weak = st.columns(min(3, len(weak_areas)))
            for i, area in enumerate(weak_areas[:3]):
                with cols_weak[i]:
                    color = "#ff6b6b" if area['gap'] > 4 else "#feca57" if area['gap'] > 2 else "#48dbfb"
                    st.markdown(f"""
                    <div style="background: {color}; padding: 15px; border-radius: 10px;
                                color: white; text-align: center;">
                        <h4 style="margin:0;">{area['label']}</h4>
                        <p style="margin:5px 0; font-size: 2em; font-weight: bold;">{area['score']:.1f}/7</p>
                        <p style="margin:0;">Gap: {area['gap']:.1f}</p>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🏫 Scuole da cui Imparare")

        # Cerca scuole complementari
        if st.button("🔍 Trova Suggerimenti", type="primary", use_container_width=True):
            with st.spinner("Cerco scuole che possono ispirarti..."):
                # Trova peer con strategia complementare
                complementary_matches = advanced_peer_matching(
                    target_school=school_data,
                    df=df,
                    strategy='complementary',
                    top_n=15
                )

                # Genera suggerimenti
                suggestions = get_improvement_suggestions(
                    target_school=school_data,
                    peers_df=complementary_matches,
                    analysis_results_path='analysis_results'
                )

            if not suggestions:
                st.info("Non sono stati trovati suggerimenti specifici. Prova ad ampliare i criteri di ricerca.")
            else:
                # Raggruppa per dimensione
                suggestions_by_dim = {}
                for s in suggestions:
                    dim = s['dimension']
                    if dim not in suggestions_by_dim:
                        suggestions_by_dim[dim] = []
                    suggestions_by_dim[dim].append(s)

                for dim_label, dim_suggestions in suggestions_by_dim.items():
                    st.markdown(f"### 📌 {dim_label}")

                    for i, sugg in enumerate(dim_suggestions[:3]):
                        with st.expander(
                            f"**{sugg['peer_name']}** — {sugg['peer_region']} | Score: {sugg['peer_score']:.1f}%",
                            expanded=(i == 0)
                        ):
                            col_left, col_right = st.columns([2, 1])

                            with col_left:
                                st.markdown(f"""
                                **Perché questa scuola:**
                                - Tipo: {sugg['peer_type']}
                                - Punteggio in {dim_label}: **{sugg['peer_score']:.1f}/7** (tu: {sugg['your_score']:.1f}/7)
                                - Similarità strutturale: {sugg['similarity_score']:.0f}%

                                **Raccomandazione:**
                                {sugg['recommendation']}
                                """)

                                # Mostra evidenze se disponibili
                                if sugg.get('evidence') and sugg['evidence'].get('quotes'):
                                    st.markdown("**📝 Estratti dal loro PTOF:**")
                                    for quote in sugg['evidence']['quotes'][:2]:
                                        st.markdown(f"> _{quote['quote'][:200]}..._")

                            with col_right:
                                # Confronto visivo
                                your_score = sugg['your_score']
                                their_score = sugg['peer_score']

                                fig_compare = go.Figure()
                                fig_compare.add_trace(go.Bar(
                                    x=['Tu', 'Loro'],
                                    y=[your_score, their_score],
                                    marker_color=['#3498db', '#2ecc71'],
                                    text=[f'{your_score:.1f}/7', f'{their_score:.1f}/7'],
                                    textposition='outside'
                                ))
                                fig_compare.update_layout(
                                    height=200,
                                    yaxis_range=[1, 7],
                                    showlegend=False,
                                    margin=dict(l=20, r=20, t=20, b=20)
                                )
                                st.plotly_chart(fig_compare, use_container_width=True)

                    st.markdown("---")

        # Sezione raccomandazioni generali
        st.subheader("📋 Piano d'Azione Suggerito")

        if weak_areas:
            st.markdown("""
            Basandoci sull'analisi del tuo PTOF e sul confronto con scuole simili, ecco un piano d'azione:
            """)

            for i, area in enumerate(weak_areas[:3], 1):
                dim_col = area['dimension']
                dim_label = area['label']

                # Trova raccomandazioni specifiche dal dizionario
                sub_recs = []
                if dim_label in SUB_INDICATORS:
                    for sub_col, sub_name in SUB_INDICATORS[dim_label].items():
                        if sub_col in RECOMMENDATIONS:
                            sub_val = school_data.get(sub_col, 0) or 0
                            if sub_val < 4:
                                sub_recs.extend([(sub_name, r) for r in RECOMMENDATIONS[sub_col][:1]])

                with st.expander(f"**{i}. Migliora {dim_label}** (attuale: {area['score']:.1f}/7)", expanded=(i == 1)):
                    st.markdown(f"""
                    **Obiettivo:** Portare {dim_label} da {area['score']:.1f}/7 a {min(7, area['score'] + 2):.1f}/7

                    **Azioni concrete:**
                    """)

                    if sub_recs:
                        for sub_name, rec in sub_recs[:3]:
                            st.markdown(f"- **{sub_name}:** {rec}")
                    else:
                        st.markdown("- Analizza le pratiche delle scuole eccellenti in questa dimensione")
                        st.markdown("- Confrontati con il benchmark di settore")
                        st.markdown("- Definisci indicatori di monitoraggio specifici")

    st.markdown("---")
    st.caption("💡 Suggerimenti Personalizzati - Impara dalle attività di scuole simili alla tua")

render_footer()
