
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Page Config
st.set_page_config(page_title="Dashboard Analisi PTOF", layout="wide")
st.title("📊 Dashboard Analisi Orientamento PTOF")

# Constants
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'

# Label Mapping: Technical Column Names -> Italian Human-Readable Labels
LABEL_MAP = {
    # Finalità (2.3)
    '2_3_finalita_attitudini_score': 'Finalità: Attitudini Personali',
    '2_3_finalita_interessi_score': 'Finalità: Interessi',
    '2_3_finalita_progetto_vita_score': 'Finalità: Progetto di Vita',
    '2_3_finalita_transizioni_formative_score': 'Finalità: Transizioni Formative',
    '2_3_finalita_capacita_orientative_opportunita_score': 'Finalità: Capacità Orientative',
    # Obiettivi (2.4)
    '2_4_obiettivo_ridurre_abbandono_score': 'Obiettivo: Riduzione Abbandono',
    '2_4_obiettivo_continuita_territorio_score': 'Obiettivo: Continuità Territoriale',
    '2_4_obiettivo_contrastare_neet_score': 'Obiettivo: Contrasto NEET',
    '2_4_obiettivo_lifelong_learning_score': 'Obiettivo: Apprendimento Permanente',
    # Indices
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi',
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica Orientativa',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice di Maturità',
    'partnership_count': 'N. Partnership',
    'activities_count': 'N. Attività',
    '2_1_score': 'Sezione Orientamento Dedicata'
}

def get_label(col):
    """Returns Italian label for a column, or cleaned version of column name."""
    return LABEL_MAP.get(col, col.replace('_', ' ').replace('score', '').title().strip())

# Data Loading
@st.cache_data
def load_data():
    if not os.path.exists(SUMMARY_FILE):
        return pd.DataFrame()
    
    df = pd.read_csv(SUMMARY_FILE)
    
    # Enrich with metadata if available
    if os.path.exists(METADATA_FILE):
        meta = pd.read_csv(METADATA_FILE, sep=';', on_bad_lines='skip')
        meta.columns = [c.lower() for c in meta.columns]
        
        merge_cols = ['istituto']
        if 'ordine_grado' in meta.columns:
            merge_cols.append('ordine_grado')
            
        df = pd.merge(df, meta[merge_cols], 
                      left_on='school_id', right_on='istituto', how='left')
                      
        if 'ordine_grado' not in df.columns:
            def infer_level(name):
                if not isinstance(name, str): return 'ND'
                name = name.upper()
                if any(x in name for x in ['LICEO', 'IIS', 'ISIS', 'TECNICO', 'PROFESSIONALE', 'IT', 'IPS']):
                    return 'II Grado'
                if any(x in name for x in ['IC', 'COMPRENSIVO', 'DIDATTICA', 'MEDIA', 'ELEMENTARE']):
                    return 'I Grado'
                return 'Altro'
            df['ordine_grado'] = df['denominazione'].apply(infer_level)
    
    # Ensure numeric columns
    cols_to_numeric = [c for c in df.columns if '_score' in c or 'mean_' in c or 'index' in c or 'count' in c]
    for c in cols_to_numeric:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    return df

df = load_data()

if df.empty:
    st.warning(f"Nessun dato trovato in {SUMMARY_FILE}. Esegui prima l'analisi.")
    st.stop()

# Sidebar Filters
st.sidebar.header("🔍 Filtri")
if 'ordine_grado' in df.columns:
    school_levels = df['ordine_grado'].unique()
    selected_level = st.sidebar.multiselect("Grado Scolastico", school_levels, default=list(school_levels))
    df = df[df['ordine_grado'].isin(selected_level)]

st.sidebar.markdown("---")
with st.sidebar.expander("📘 Glossario Completo", expanded=False):
    st.markdown("""
    ### 📊 Indice di Maturità Orientamento
    Punteggio complessivo (1-7) che misura quanto il PTOF integra l'orientamento in modo sistemico.
    
    **Formula:** Media di (Finalità + Obiettivi + Governance + Didattica + Opportunità) / 5
    
    ---
    ### 📐 MEDIE PER AREA TEMATICA
    
    **Media Finalità** *(perché fare orientamento)*
    - Attitudini, Interessi, Progetto di Vita, Transizioni, Capacità Orientative
    
    **Media Obiettivi** *(cosa raggiungere)*
    - Riduzione Abbandono, Continuità Territorio, Contrasto NEET, Lifelong Learning
    
    **Media Governance** *(come organizzare)*
    - Coordinamento servizi, Dialogo docenti-studenti, Rapporto scuola-genitori, Monitoraggio, Sistema inclusione
    
    **Media Didattica** *(come insegnare)*
    - Apprendimento esperienziale, Laboratori, Flessibilità spazi/tempi, Interdisciplinarità
    
    **Media Opportunità** *(cosa offrire)*
    - Attività culturali, Laboratori espressivi, Attività ludiche, Volontariato, Sport
    
    ---
    ### 🔢 CONTEGGI
    
    **N. Partnership**: Quante tipologie di partner (0-11): interni, primarie, licei, tecnici, professionali, IeFP, università, aziende, enti pubblici, terzo settore, altro.
    
    **N. Attività**: Quante attività specifiche di orientamento sono censite nel documento.
    
    ---
    ### SCALA DI PUNTEGGIO (Likert 1-7)
    | Punteggio | Significato |
    |:---------:|:------------|
    | **1** | Assente: nessun riferimento nel documento |
    | **2-3** | Minimo: accenni generici o indiretti |
    | **4** | Sufficiente: azioni presenti ma basilari |
    | **5-6** | Buono: azioni strutturate e descritte |
    | **7** | Eccellente: sistema integrato e monitorato |
    """)

# Top Level KPIs
st.subheader("📈 Indicatori Chiave")

# Group 1: Overview
st.markdown("**📊 Panoramica**")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Scuole Analizzate", len(df))
with col2:
    if 'ptof_orientamento_maturity_index' in df.columns:
        st.metric("Indice Maturità Medio", f"{df['ptof_orientamento_maturity_index'].mean():.2f}")
with col3:
    if '2_1_score' in df.columns:
        perc_present = (df['2_1_score'] > 0).mean() * 100
        st.metric("% con Sezione Orientamento", f"{perc_present:.0f}%")

# Group 2: Aree Tematiche (ordinate per logica concettuale)
st.markdown("**📐 Medie per Area Tematica** *(scala 1-7)*")
col4, col5, col6, col7, col8 = st.columns(5)
with col4:
    if 'mean_finalita' in df.columns:
        st.metric("Finalità", f"{df['mean_finalita'].mean():.2f}")
with col5:
    if 'mean_obiettivi' in df.columns:
        st.metric("Obiettivi", f"{df['mean_obiettivi'].mean():.2f}")
with col6:
    if 'mean_governance' in df.columns:
        st.metric("Governance", f"{df['mean_governance'].mean():.2f}")
with col7:
    if 'mean_didattica_orientativa' in df.columns:
        st.metric("Didattica", f"{df['mean_didattica_orientativa'].mean():.2f}")
with col8:
    if 'mean_opportunita' in df.columns:
        st.metric("Opportunità", f"{df['mean_opportunita'].mean():.2f}")

# Group 3: Conteggi
st.markdown("**🔢 Conteggi Medi**")
col9, col10 = st.columns(2)
with col9:
    if 'partnership_count' in df.columns:
        st.metric("N. Partnership", f"{df['partnership_count'].mean():.1f}")
with col10:
    if 'activities_count' in df.columns:
        st.metric("N. Attività", f"{df['activities_count'].mean():.1f}")

# --- Charts ---

# 1. Scores Distribution
st.subheader("📊 Distribuzione Punteggi (Scala 1-7)")

score_columns = [c for c in df.columns if '_score' in c and c != '2_1_score']
if score_columns:
    # Build ordered list with categories
    ordered_cols = []
    categories = []
    
    for c in score_columns:
        ordered_cols.append(c)
        if '2_3_' in c:
            categories.append('Finalità')
        elif '2_4_' in c:
            categories.append('Obiettivi')
        else:
            categories.append('Altro')
    
    scores_mean = df[ordered_cols].mean()
    labels_italian = [get_label(c) for c in ordered_cols]
    
    chart_df = pd.DataFrame({
        'Dimensione': labels_italian,
        'Punteggio': scores_mean.values,
        'Categoria': categories
    })
    # Sort by category then by score
    chart_df = chart_df.sort_values(['Categoria', 'Punteggio'], ascending=[True, True])
    
    fig = px.bar(chart_df, x='Punteggio', y='Dimensione', orientation='h',
                 color='Categoria', 
                 title="Punteggio Medio per Dimensione",
                 labels={'Punteggio': 'Punteggio (1-7)'},
                 color_discrete_map={'Finalità': '#636EFA', 'Obiettivi': '#EF553B', 'Altro': '#00CC96'})
    fig.update_layout(xaxis=dict(range=[0, 7]), yaxis=dict(tickfont=dict(size=10)))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessuna colonna punteggio trovata.")

# 2. Data Table
st.subheader("📋 Dati Analisi")
display_cols = ['school_id', 'denominazione', 'comune', 'ptof_orientamento_maturity_index', 
                'mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 
                'mean_opportunita', 'partnership_count', 'activities_count', 'extraction_status']
display_cols = [c for c in display_cols if c in df.columns]

# Rename columns for display
df_display = df[display_cols].copy() if display_cols else df.copy()
df_display.columns = [get_label(c) if c in LABEL_MAP else c for c in df_display.columns]
st.dataframe(df_display)

with st.expander("🔍 Mostra Dati Grezzi Completi"):
    st.dataframe(df)

# 3. School Detail View
st.subheader("🏫 Dettaglio Singola Scuola")
school_id = st.selectbox("Seleziona Scuola", df['school_id'].unique())
school_data = df[df['school_id'] == school_id].iloc[0]

c1, c2 = st.columns(2)
with c1:
    st.write(f"**Denominazione:** {school_data.get('denominazione', 'ND')}")
    st.write(f"**Grado:** {school_data.get('ordine_grado', 'ND')}")
with c2:
    report_link = school_data.get('analysis_file', '')
    if report_link and os.path.exists(report_link):
        with open(report_link, 'r') as f:
            report_content = f.read()
        st.download_button("📥 Scarica Report (.md)", report_content, file_name=os.path.basename(report_link))
    else:
        st.write("Report non disponibile.")

# Show Report Content
if report_link and os.path.exists(report_link):
    with st.expander("📄 Visualizza Report Completo", expanded=True):
        st.markdown(report_content)

# Spider Chart
if score_columns:
    school_scores = school_data[score_columns]
    avg_scores = df[score_columns].mean()
    
    # Italian labels for radar
    labels_radar = [get_label(c) for c in score_columns]
    
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(r=school_scores.values, theta=labels_radar, fill='toself', name='Questa Scuola'))
    fig_radar.add_trace(go.Scatterpolar(r=avg_scores.values, theta=labels_radar, fill='toself', name='Media Campione'))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 7])), 
        showlegend=True,
        title="Confronto Scuola vs Media"
    )
    st.plotly_chart(fig_radar, use_container_width=True)
