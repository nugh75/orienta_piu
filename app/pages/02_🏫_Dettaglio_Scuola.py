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

st.set_page_config(page_title="ORIENTA+ | Dettaglio Scuola", page_icon="🧭", layout="wide")

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
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index', 'partnership_count', 'activities_count']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()

# === FUNZIONI HELPER ===

def get_best_in_class(df, tipo_scuola=None, ordine_grado=None):
    filtered = df.copy()
    if tipo_scuola and tipo_scuola != "Tutti":
        filtered = filtered[filtered['tipo_scuola'].str.contains(tipo_scuola, na=False, case=False)]
    if ordine_grado and ordine_grado != "Tutti":
        filtered = filtered[filtered['ordine_grado'].str.contains(ordine_grado, na=False, case=False)]
    if filtered.empty:
        return None
    return filtered.loc[filtered['ptof_orientamento_maturity_index'].idxmax()]

def calculate_gap(school, benchmark):
    gaps = {}
    for col, name in DIMENSIONS.items():
        school_val = school.get(col, 0) or 0
        bench_val = benchmark.get(col, 0) or 0
        gaps[name] = {
            'school': school_val,
            'benchmark': bench_val,
            'gap': bench_val - school_val,
            'gap_pct': ((bench_val - school_val) / bench_val * 100) if bench_val > 0 else 0
        }
    return gaps

def get_priority_areas(school, df, top_n=3):
    priorities = []
    for dim_col, dim_name in DIMENSIONS.items():
        if dim_name in SUB_INDICATORS:
            for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                sub_val = school.get(sub_col, 0) or 0
                sub_mean = df[sub_col].mean() if sub_col in df.columns else 4
                if sub_val < sub_mean:
                    priorities.append({
                        'dimension': dim_name,
                        'indicator': sub_name,
                        'column': sub_col,
                        'score': sub_val,
                        'mean': sub_mean,
                        'gap': sub_mean - sub_val,
                        'priority_score': (sub_mean - sub_val) * (7 - sub_val)
                    })
    return sorted(priorities, key=lambda x: x['priority_score'], reverse=True)[:top_n]

def calculate_similarity_score(school1, school2):
    weights = {'tipo_match': 30, 'grado_match': 25, 'territorio_match': 15, 'regione_match': 10, 'statale_match': 10, 'size_similarity': 10}
    score = 0
    tipo1 = set(str(school1.get('tipo_scuola', '')).split(','))
    tipo2 = set(str(school2.get('tipo_scuola', '')).split(','))
    if tipo1 & tipo2:
        score += weights['tipo_match']
    grado1 = set(str(school1.get('ordine_grado', '')).split(','))
    grado2 = set(str(school2.get('ordine_grado', '')).split(','))
    if grado1 & grado2:
        score += weights['grado_match']
    if school1.get('territorio') == school2.get('territorio'):
        score += weights['territorio_match']
    if school1.get('regione') == school2.get('regione'):
        score += weights['regione_match']
    if school1.get('statale_paritaria') == school2.get('statale_paritaria'):
        score += weights['statale_match']
    p1 = school1.get('partnership_count', 0) or 0
    p2 = school2.get('partnership_count', 0) or 0
    if p1 + p2 > 0:
        size_sim = 1 - abs(p1 - p2) / max(p1 + p2, 1)
        score += weights['size_similarity'] * size_sim
    return score

def find_peer_schools(target_school, df, top_n=10):
    peers = []
    for idx, school in df.iterrows():
        if school['school_id'] == target_school['school_id']:
            continue
        similarity = calculate_similarity_score(target_school, school)
        peers.append({
            'school_id': school['school_id'],
            'denominazione': school['denominazione'],
            'comune': school.get('comune', ''),
            'regione': school.get('regione', ''),
            'tipo_scuola': school.get('tipo_scuola', ''),
            'indice_ro': school.get('ptof_orientamento_maturity_index', 0),
            'similarity_score': similarity,
            **{col: school.get(col, 0) for col in DIMENSIONS.keys()}
        })
    return sorted(peers, key=lambda x: x['similarity_score'], reverse=True)[:top_n]

def get_peer_statistics(target_school, peers_df):
    stats = {}
    target_index = target_school.get('ptof_orientamento_maturity_index', 0)
    peer_indices = peers_df['indice_ro'].values

    stats['peer_mean'] = np.mean(peer_indices)
    stats['peer_std'] = np.std(peer_indices)
    stats['peer_min'] = np.min(peer_indices)
    stats['peer_max'] = np.max(peer_indices)
    stats['target_vs_mean'] = target_index - stats['peer_mean']
    stats['rank_in_peers'] = (peer_indices < target_index).sum() + 1
    stats['total_peers'] = len(peer_indices)
    stats['percentile_in_peers'] = stats['rank_in_peers'] / stats['total_peers'] * 100

    for col, name in DIMENSIONS.items():
        target_val = target_school.get(col, 0) or 0
        peer_vals = peers_df[col].values
        stats[f'{name}_target'] = target_val
        stats[f'{name}_peer_mean'] = np.mean(peer_vals)
        stats[f'{name}_diff'] = target_val - np.mean(peer_vals)

    return stats

# === CARICAMENTO DATI ===
df = load_data()

st.title("🏫 Dettaglio Scuola")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina analizza **una singola scuola** con un approccio completo: profilo, gap analysis e confronto con peer.

    ### 📊 Sezioni Disponibili

    **📊 Profilo**
    - Dati generali, radar delle 5 dimensioni e punteggi dettagliati
    - Dettaglio dal report JSON, posizione in classifica, export PDF
    - Documento PTOF originale (se disponibile)

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
    new_index = (current_index - 1) % len(school_options)
    st.session_state.selected_school_name = school_options[new_index]

def next_school():
    new_index = (current_index + 1) % len(school_options)
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

idx = school_data.get('ptof_orientamento_maturity_index', 0)
overall_percentile = (df['ptof_orientamento_maturity_index'] < idx).mean() * 100 if pd.notna(idx) else 0

info_cols = st.columns(4)
with info_cols[0]:
    st.metric("Codice", school_data.get('school_id', 'N/D'))
with info_cols[1]:
    st.metric("Tipo", str(school_data.get('tipo_scuola', 'N/D'))[:20])
with info_cols[2]:
    st.metric("Area", school_data.get('area_geografica', 'N/D'))
with info_cols[3]:
    st.metric("Indice RO", f"{idx:.2f}/7" if pd.notna(idx) else "N/D")

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
    st.metric("Percentile", f"{overall_percentile:.0f}°")
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
💡 **A cosa serve**: Fornisce una panoramica della scuola con i dati identificativi e il punteggio complessivo.

🔍 **Cosa rileva**: L'**Indice RO** (Robustezza Orientamento) è il punteggio principale (scala 1-7). Valori 1-2 = insufficiente, 3-4 = sufficiente, 5-6 = buono, 7 = eccellente.

🎯 **Implicazioni**: Un punteggio alto indica un PTOF con orientamento ben strutturato. I contatti permettono di approfondire direttamente con la scuola.
""")

st.markdown("---")

# === TABS PRINCIPALI ===
tab_profilo, tab_gap, tab_peer, tab_matching, tab_suggestions = st.tabs([
    "📊 Profilo", "🎯 Gap Analysis", "👥 Confronto Peer", "🔍 Matching Avanzato", "💡 Suggerimenti"
])

# === TAB PROFILO ===
with tab_profilo:
    radar_cols = list(DIMENSIONS.keys())
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🕸️ Profilo Radar")
        if all(c in df.columns for c in radar_cols):
            school_vals = [school_data.get(c, 0) if pd.notna(school_data.get(c)) else 0 for c in radar_cols]
            avg_vals = [df[c].mean() for c in radar_cols]
            labels = list(DIMENSIONS.values())

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=school_vals + [school_vals[0]], theta=labels + [labels[0]],
                                           fill='toself', name=selected_school[:25],
                                           line_color='#1f77b4'))
            fig.add_trace(go.Scatterpolar(r=avg_vals + [avg_vals[0]], theta=labels + [labels[0]],
                                           fill='toself', name='Media Campione', opacity=0.5,
                                           line_color='#ff7f0e'))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.info("""
💡 **A cosa serve**: Mostra il "profilo" della scuola sulle 5 dimensioni dell'orientamento, confrontato con la media nazionale.

🔍 **Cosa rileva**: L'area blu è la scuola, quella arancione è la media del campione. Dove il blu "esce" dall'arancione, la scuola eccelle. Dove è "dentro", c'è margine di miglioramento.

🎯 **Implicazioni**: Identifica rapidamente punti di forza (da valorizzare nella comunicazione) e aree critiche (dove investire in formazione o risorse).
""")

    with col2:
        st.subheader("📊 Punteggi Dimensionali")
        for col_key, col_name in DIMENSIONS.items():
            val = school_data.get(col_key, 0) or 0
            mean_val = df[col_key].mean()
            delta = val - mean_val
            st.metric(col_name, f"{val:.2f}/7", f"{delta:+.2f} vs media", delta_color="normal")

    # Report MD
    school_id = school_data.get('school_id')
    if school_id:
        md_files = glob.glob(f'analysis_results/*{school_id}*_analysis.md')
        if md_files:
            with st.expander("📝 Report Analisi Completo", expanded=False):
                with open(md_files[0], 'r') as f:
                    st.markdown(f.read())

    # Punteggi dettagliati
    st.subheader("📊 Punteggi Dettagliati")
    score_cols = [c for c in df.columns if '_score' in c]
    if score_cols:
        scores = {get_label(c): school_data.get(c, 0) for c in score_cols if pd.notna(school_data.get(c))}
        if scores:
            score_df = pd.DataFrame({'Dimensione': list(scores.keys()), 'Punteggio': list(scores.values())})
            score_df = score_df.sort_values('Punteggio', ascending=True)
            fig = px.bar(score_df, x='Punteggio', y='Dimensione', orientation='h',
                        color='Punteggio', color_continuous_scale='RdYlGn',
                        range_x=[0, 7], range_color=[1, 7])
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

            st.info("""
💡 **A cosa serve**: Mostra il punteggio di ogni singolo indicatore valutato nel PTOF.

🔍 **Cosa rileva**: Ogni barra è un indicatore specifico. Verde = punteggio alto (buono), Rosso = punteggio basso (critico). Le barre più corte indicano le aree prioritarie.

🎯 **Implicazioni**: Usa questa vista per identificare esattamente QUALI aspetti migliorare nel PTOF. Gli indicatori in rosso sono le priorità di intervento concrete.
""")

    st.markdown("---")

    # Dettaglio dal report JSON
    st.subheader("📄 Dettaglio dal Report")
    school_id = school_data.get('school_id', '')
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
                has_sez = "✅ Sì" if s21.get('has_sezione_dedicata') else "❌ No"
                st.write(f"**Sezione dedicata:** {has_sez}")
                st.write(f"**Punteggio:** {s21.get('score', 'N/D')}/7")
                if s21.get('note'):
                    st.caption(s21.get('note'))

            st.markdown("---")

            st.markdown("### 🎯 Finalita (dettaglio)")
            finalita = sec2.get('2_3_finalita', {})
            for key, val in finalita.items():
                if isinstance(val, dict):
                    score = val.get('score', 0)
                    st.write(f"**{get_label(key)}:** {score}/7")

        except Exception as e:
            st.error(f"Errore caricamento JSON: {e}")
    else:
        st.info("Report JSON non ancora disponibile per questa scuola")

    st.markdown("---")

    # Posizione in classifica
    st.subheader("📈 Posizione in Classifica")
    if 'ptof_orientamento_maturity_index' in df.columns:
        df_sorted = df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
        df_sorted.index = df_sorted.index + 1
        position = df_sorted[df_sorted['denominazione'] == selected_school].index[0]
        total = len(df_sorted)

        percentile = (total - position) / total * 100

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Posizione", f"#{position}")
        with col2:
            st.metric("Su totale", f"{total} scuole")
        with col3:
            st.metric("Percentile", f"{percentile:.0f}°")

        st.info("""
💡 **A cosa serve**: Indica la posizione della scuola nella classifica nazionale e il confronto con le altre.

🔍 **Cosa rileva**: Il percentile indica quante scuole questa supera. Es: 75° percentile = supera il 75% degli istituti analizzati. Più è alto, meglio è.

🎯 **Implicazioni**: Un dato utile per la comunicazione esterna ("Siamo nel top 20%"). Permette anche di fissare obiettivi concreti ("Vogliamo passare dal 60° al 75° percentile").
""")

    st.markdown("---")

    # Export scheda scuola PDF
    st.subheader("📥 Esporta Scheda Scuola")

    def generate_school_pdf(school_data, radar_cols, df):
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

            story.append(Paragraph("📋 Scheda Scuola", title_style))
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

            idx = school_data.get('ptof_orientamento_maturity_index', 0)
            idx_str = f"{idx:.2f}/7" if pd.notna(idx) else "N/D"
            story.append(Paragraph(f"<b>Indice Robustezza Orientamento (RO):</b> {idx_str}", heading_style))
            story.append(Spacer(1, 12))

            story.append(Paragraph("Punteggi per Dimensione", heading_style))

            dim_labels = ['Finalita', 'Obiettivi', 'Governance', 'Didattica Orientativa', 'Opportunita']
            dim_data = [['Dimensione', 'Punteggio']]

            for col, label in zip(radar_cols, dim_labels):
                val = school_data.get(col, 0)
                val_str = f"{val:.2f}/7" if pd.notna(val) else "N/D"
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

            df_sorted_pdf = df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
            df_sorted_pdf.index = df_sorted_pdf.index + 1
            pos = df_sorted_pdf[df_sorted_pdf['denominazione'] == school_data.get('denominazione')].index[0]
            tot = len(df_sorted_pdf)
            pct = (tot - pos) / tot * 100

            story.append(Paragraph("Posizione in Classifica Nazionale", heading_style))
            rank_data = [
                ['Posizione', f"#{pos} su {tot} scuole"],
                ['Percentile', f"{pct:.0f}° (supera il {pct:.0f}% delle scuole)"],
            ]
            rank_table = Table(rank_data, colWidths=[6*cm, 10*cm])
            rank_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(rank_table)
            story.append(Spacer(1, 20))

            from datetime import datetime
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"<i>Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", normal_style))
            story.append(Paragraph("<i>Dashboard PTOF - Analisi Robustezza Orientamento</i>", normal_style))

            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()

        except ImportError:
            return None
        except Exception as e:
            st.error(f"Errore generazione PDF: {e}")
            return None

    try:
        pdf_bytes = generate_school_pdf(school_data, radar_cols, df)

        if pdf_bytes:
            col_pdf1, col_pdf2 = st.columns([1, 2])
            with col_pdf1:
                st.download_button(
                    label="📥 Scarica Scheda PDF",
                    data=pdf_bytes,
                    file_name=f"scheda_{school_data.get('school_id', 'scuola')}.pdf",
                    mime="application/pdf",
                    help="Scarica la scheda completa della scuola in formato PDF"
                )
            with col_pdf2:
                st.caption("La scheda PDF include: dati anagrafici, punteggi per dimensione, posizione in classifica.")
        else:
            st.warning("⚠️ Per generare PDF installa reportlab: `pip install reportlab`")

    except Exception as e:
        st.warning(f"Export PDF non disponibile: {e}")
        st.caption("Installa reportlab: `pip install reportlab`")

    st.markdown("---")

    # PDF PTOF originale
    st.subheader("📄 Documento PTOF Originale")
    school_id = school_data.get('school_id', '')

    pdf_path = None
    search_dirs = ["ptof_processed", "ptof_inbox"]
    try:
        from app.data_utils import find_pdf_for_school
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

            pdf_display = f'''
                <iframe src="data:application/pdf;base64,{base64_pdf}"
                        width="100%" height="800" type="application/pdf">
                </iframe>
            '''
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
        top_10 = df.nlargest(max(1, len(df)//10), 'ptof_orientamento_maturity_index')
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
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### 📊 Dettaglio Gap")
            for dim, vals in gaps.items():
                gap = vals['gap']
                color = "🔴" if gap > 0.5 else "🟡" if gap > 0 else "🟢"
                st.markdown(f"{color} **{dim}**: {vals['school']:.1f} vs {vals['benchmark']:.1f} (gap: {gap:+.1f})")

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
                            {prio['score']:.1f} -> {min(7, prio['score']+2):.1f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

            # Raccomandazioni
            st.markdown("---")
            st.subheader("💡 Raccomandazioni Operative")

            for prio in priorities[:3]:
                col = prio['column']
                if col in RECOMMENDATIONS:
                    target_score = min(7, prio['score'] + 2)
                    with st.expander(
                        f"📌 {prio['dimension']} - {prio['indicator']} (Score: {prio['score']:.1f} → Target: {target_score:.1f})",
                        expanded=True
                    ):
                        for i, r in enumerate(RECOMMENDATIONS[col], 1):
                            st.markdown(f"{i}. {r}")

            st.markdown("---")
            st.subheader("📈 Piano di Miglioramento Suggerito")

            plan_data = []
            for prio in priorities[:5]:
                current = prio['score']
                target = min(7, current + 2)
                plan_data.append({
                    'Area': f"{prio['dimension']} - {prio['indicator']}",
                    'Attuale': current,
                    'Target 6 mesi': min(7, current + 1),
                    'Target 12 mesi': target,
                    'Priorita': '🔴 Alta' if prio['gap'] > 1.5 else '🟡 Media' if prio['gap'] > 0.5 else '🟢 Bassa'
                })

            plan_df = pd.DataFrame(plan_data)
            st.dataframe(plan_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🚀 Impatto Stimato")

            current_index = school_data.get('ptof_orientamento_maturity_index', 0) or 0
            current_percentile = (df['ptof_orientamento_maturity_index'] < current_index).mean() * 100 if pd.notna(current_index) else 0
            potential_gain = sum([min(2, p['gap']) for p in priorities[:3]]) / 5
            projected_index = min(7, current_index + potential_gain)
            new_percentile = (df['ptof_orientamento_maturity_index'] < projected_index).mean() * 100

            impact_cols = st.columns(3)
            with impact_cols[0]:
                st.metric("Indice Attuale", f"{current_index:.2f}")
            with impact_cols[1]:
                st.metric("Indice Proiettato (12 mesi)", f"{projected_index:.2f}", f"+{potential_gain:.2f}")
            with impact_cols[2]:
                st.metric("Percentile Proiettato", f"{new_percentile:.0f}°", f"+{new_percentile - current_percentile:.0f}")
        else:
            st.success("✅ Questa scuola non presenta aree critiche evidenti!")

    st.markdown("---")
    st.caption("🎯 Gap Analysis - Sistema di analisi per il miglioramento continuo")

# === TAB CONFRONTO PEER ===
with tab_peer:
    st.subheader("👥 Confronto con Scuole Simili")

    st.subheader(f"📋 {school_data['denominazione']}")
    info_cols = st.columns(5)
    with info_cols[0]:
        st.metric("Indice RO", f"{school_data['ptof_orientamento_maturity_index']:.2f}")
    with info_cols[1]:
        st.metric("Tipo", str(school_data.get('tipo_scuola', 'N/D'))[:20])
    with info_cols[2]:
        st.metric("Regione", school_data.get('regione', 'N/D'))
    with info_cols[3]:
        st.metric("Territorio", school_data.get('territorio', 'N/D'))
    with info_cols[4]:
        st.metric("Gestione", school_data.get('statale_paritaria', 'N/D'))

    st.markdown("---")

    with st.expander("⚙️ Configura Criteri di Matching", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            n_peers = st.slider("Numero di Peer", 5, 20, 10)
        with col2:
            same_region_only = st.checkbox("Solo stessa regione", False)
        with col3:
            same_type_only = st.checkbox("Solo stesso tipo", False)

    filtered_df = df.copy()
    if same_region_only:
        filtered_df = filtered_df[filtered_df['regione'] == school_data.get('regione')]
    if same_type_only:
        tipo = str(school_data.get('tipo_scuola', '')).split(',')[0].strip()
        if tipo:
            filtered_df = filtered_df[filtered_df['tipo_scuola'].str.contains(tipo, na=False, case=False)]

    peers = find_peer_schools(school_data, filtered_df, top_n=n_peers)
    peers_df = pd.DataFrame(peers)

    if peers_df.empty:
        st.warning("Nessuna scuola peer trovata con i criteri selezionati.")
    else:
        stats = get_peer_statistics(school_data, peers_df)

        st.subheader("📊 Posizionamento nel Gruppo Peer")
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Posizione", f"{stats['rank_in_peers']}/{stats['total_peers']}")
        with stat_cols[1]:
            st.metric("Percentile Peer", f"{stats['percentile_in_peers']:.0f}°")
        with stat_cols[2]:
            st.metric("vs Media Peer", f"{school_data['ptof_orientamento_maturity_index']:.2f}", f"{stats['target_vs_mean']:+.2f}")
        with stat_cols[3]:
            st.metric("Range Peer", f"{stats['peer_min']:.1f} - {stats['peer_max']:.1f}")

        st.markdown("---")
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("📈 Confronto Dimensionale")
            categories = list(DIMENSIONS.values())
            target_values = [school_data.get(col, 0) or 0 for col in DIMENSIONS.keys()]
            peer_mean_values = [peers_df[col].mean() for col in DIMENSIONS.keys()]
            peer_max_values = [peers_df[col].max() for col in DIMENSIONS.keys()]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=target_values, theta=categories, fill='toself', name='Scuola Selezionata', line_color='blue'))
            fig.add_trace(go.Scatterpolar(r=peer_mean_values, theta=categories, fill='toself', name='Media Peer', line_color='orange'))
            fig.add_trace(go.Scatterpolar(r=peer_max_values, theta=categories, fill='none', name='Best Peer', line_color='green', line_dash='dash'))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📊 Δ per Dimensione")
            diff_data = []
            for col, name in DIMENSIONS.items():
                target_val = school_data.get(col, 0) or 0
                peer_mean = peers_df[col].mean()
                diff = target_val - peer_mean
                diff_data.append({'Dimensione': name, 'Differenza': diff})

            diff_df = pd.DataFrame(diff_data)
            fig_bar = px.bar(diff_df, x='Differenza', y='Dimensione', orientation='h',
                            color='Differenza', color_continuous_scale=['red', 'yellow', 'green'], range_color=[-2, 2])
            fig_bar.add_vline(x=0, line_dash="dash", line_color="gray")
            fig_bar.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

            strengths = [d['Dimensione'] for d in diff_data if d['Differenza'] > 0.3]
            weaknesses = [d['Dimensione'] for d in diff_data if d['Differenza'] < -0.3]
            if strengths:
                st.success(f"**Punti di forza:** {', '.join(strengths)}")
            if weaknesses:
                st.warning(f"**Aree miglioramento:** {', '.join(weaknesses)}")

        # Tabella peer
        st.markdown("---")
        st.subheader(f"🏫 Le {n_peers} Scuole Peer Più Simili")

        display_df = peers_df[['denominazione', 'comune', 'regione', 'tipo_scuola', 'indice_ro', 'similarity_score']].copy()
        display_df.columns = ['Scuola', 'Comune', 'Regione', 'Tipo', 'Indice RO', 'Similarita %']
        display_df['Similarita %'] = display_df['Similarita %'].round(0).astype(int)
        display_df['Indice RO'] = display_df['Indice RO'].round(2)

        def color_index(val):
            target = school_data['ptof_orientamento_maturity_index']
            if val > target + 0.3:
                return 'background-color: rgba(0, 255, 0, 0.2)'
            if val < target - 0.3:
                return 'background-color: rgba(255, 0, 0, 0.2)'
            return ''

        st.dataframe(
            display_df.style.applymap(color_index, subset=['Indice RO']),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("📊 Distribuzione Indici nel Gruppo Peer")

        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=peers_df['indice_ro'],
            nbinsx=10,
            name='Distribuzione Peer',
            marker_color='lightblue'
        ))
        fig_dist.add_vline(
            x=school_data['ptof_orientamento_maturity_index'],
            line_dash="dash",
            line_color="red",
            annotation_text="Tu",
            annotation_position="top"
        )
        fig_dist.add_vline(
            x=peers_df['indice_ro'].mean(),
            line_dash="dot",
            line_color="orange",
            annotation_text="Media",
            annotation_position="bottom"
        )
        fig_dist.update_layout(
            xaxis_title="Indice RO",
            yaxis_title="N. Scuole",
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("---")
        st.subheader("💡 Insights dal Confronto Peer")

        insights = []
        if stats['percentile_in_peers'] >= 75:
            insights.append("🏆 **Eccellente!** Ti posizioni nel quartile superiore del tuo gruppo peer.")
        elif stats['percentile_in_peers'] >= 50:
            insights.append("✅ **Buono!** Sei sopra la mediana del gruppo peer.")
        elif stats['percentile_in_peers'] >= 25:
            insights.append("⚠️ **Attenzione:** Sei sotto la mediana del gruppo peer.")
        else:
            insights.append("🔴 **Critico:** Sei nel quartile inferiore del gruppo peer.")

        max_strength = max(diff_data, key=lambda x: x['Differenza'])
        max_weakness = min(diff_data, key=lambda x: x['Differenza'])

        if max_strength['Differenza'] > 0.5:
            insights.append(f"💪 **Punto di forza distintivo:** {max_strength['Dimensione']} (+{max_strength['Differenza']:.1f} vs peer)")
        if max_weakness['Differenza'] < -0.5:
            insights.append(f"📉 **Area critica rispetto ai peer:** {max_weakness['Dimensione']} ({max_weakness['Differenza']:.1f} vs peer)")

        best_peer = peers_df.loc[peers_df['indice_ro'].idxmax()]
        if best_peer['indice_ro'] > school_data['ptof_orientamento_maturity_index'] + 0.5:
            insights.append(f"🎯 **Benchmark suggerito:** {best_peer['denominazione']} (Indice: {best_peer['indice_ro']:.2f})")

        for insight in insights:
            st.markdown(insight)

    st.markdown("---")
    st.caption("👥 Confronto Peer - Benchmark equo con scuole simili")

# === TAB MATCHING AVANZATO ===
with tab_matching:
    st.subheader("🔍 Matching Avanzato tra Scuole")

    st.markdown("""
    Questo strumento utilizza algoritmi avanzati per trovare scuole con cui confrontarti in modo più mirato.
    Puoi scegliere tra diverse strategie di matching a seconda dei tuoi obiettivi.
    """)

    # Import del match engine
    try:
        from app.match_engine import (
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
                Utile per: imparare best practice, trovare mentor, colmare gap specifici.
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
                        f"**{i+1}. {match['denominazione']}** — Score: {match['final_score']:.0f}/100 | RO: {match['ptof_orientamento_maturity_index']:.2f}",
                        expanded=(i < 3)
                    ):
                        col_info, col_scores = st.columns([1, 1])

                        with col_info:
                            st.markdown(f"""
                            - **Regione:** {match['regione']}
                            - **Provincia:** {match.get('provincia', 'N/D')}
                            - **Tipo:** {match['tipo_scuola']}
                            - **Indice RO:** {match['ptof_orientamento_maturity_index']:.2f}/7
                            """)
                            st.caption(f"💡 {match['explanation']}")

                        with col_scores:
                            # Mini radar comparativo
                            fig_mini = go.Figure()

                            # Scuola target
                            target_vals = [school_data.get(d, 0) or 0 for d in DIMENSION_LABELS.keys()]
                            match_vals = [match.get(d, 0) or 0 for d in DIMENSION_LABELS.keys()]
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
                                polar=dict(radialaxis=dict(range=[0, 7], showticklabels=False)),
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
                                    f"- **{dim_label}**: Tu {comp['school1_score']:.1f} → Lei {comp['school2_score']:.1f} "
                                    f"(+{comp['gap_covered']:.1f})"
                                )

                # Tabella riepilogativa
                st.markdown("---")
                st.subheader("📊 Tabella Riepilogativa")

                display_matches = matches[['denominazione', 'regione', 'tipo_scuola',
                                          'ptof_orientamento_maturity_index', 'final_score']].copy()
                display_matches.columns = ['Scuola', 'Regione', 'Tipo', 'Indice RO', 'Score Match']
                display_matches['Score Match'] = display_matches['Score Match'].round(0).astype(int)
                display_matches['Indice RO'] = display_matches['Indice RO'].round(2)

                st.dataframe(display_matches, use_container_width=True, hide_index=True)

                # Salva in session state per uso in altri tab
                st.session_state['last_matches'] = matches

    st.markdown("---")
    st.caption("🔍 Matching Avanzato - Trova scuole per creare reti e imparare dalle best practice")

# === TAB SUGGERIMENTI PERSONALIZZATI ===
with tab_suggestions:
    st.subheader("💡 Suggerimenti Personalizzati di Miglioramento")

    st.markdown("""
    Questa sezione analizza le tue aree di debolezza e cerca scuole simili a te che eccellono
    in quelle aree, estraendo le loro pratiche e metodologie come fonte di ispirazione.
    """)

    try:
        from app.match_engine import (
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
                            f"**{sugg['peer_name']}** — {sugg['peer_region']} | Score: {sugg['peer_score']:.1f}/7",
                            expanded=(i == 0)
                        ):
                            col_left, col_right = st.columns([2, 1])

                            with col_left:
                                st.markdown(f"""
                                **Perché questa scuola:**
                                - Tipo: {sugg['peer_type']}
                                - Punteggio in {dim_label}: **{sugg['peer_score']:.1f}** (tu: {sugg['your_score']:.1f})
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
                                    text=[f'{your_score:.1f}', f'{their_score:.1f}'],
                                    textposition='outside'
                                ))
                                fig_compare.update_layout(
                                    height=200,
                                    yaxis_range=[0, 7],
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

                with st.expander(f"**{i}. Migliora {dim_label}** (attuale: {area['score']:.1f})", expanded=(i == 1)):
                    st.markdown(f"""
                    **Obiettivo:** Portare {dim_label} da {area['score']:.1f} a {min(7, area['score'] + 2):.1f}

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
    st.caption("💡 Suggerimenti Personalizzati - Impara dalle best practice di scuole simili alla tua")

st.markdown("---")
st.caption("🏫 Dettaglio Scuola - Analisi completa con Gap Analysis, Confronto Peer e Suggerimenti")
