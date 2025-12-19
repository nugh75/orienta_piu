
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import streamlit as st
import pandas as pd

# Page Config (Must be first)
st.set_page_config(page_title="Dashboard Analisi PTOF", page_icon="📊", layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metrics styling */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label {
        color: #555;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #2c3e50;
        font-weight: 700;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
    }
    
    /* Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Analisi Orientamento PTOF")

# Constants
SUMMARY_FILE_PATTERN = 'data/analysis_summary*.csv'
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
    # Governance (2.5)
    '2_5_azione_coordinamento_servizi_score': 'Governance: Coordinamento Servizi',
    '2_5_azione_dialogo_docenti_studenti_score': 'Governance: Dialogo Docenti-Studenti',
    '2_5_azione_rapporto_scuola_genitori_score': 'Governance: Rapporto Scuola-Genitori',
    '2_5_azione_monitoraggio_azioni_score': 'Governance: Monitoraggio Azioni',
    '2_5_azione_sistema_integrato_inclusione_fragilita_score': 'Governance: Inclusione e Fragilità',
    # Didattica (2.6)
    '2_6_didattica_da_esperienza_studenti_score': 'Didattica: Esperienza Studenti',
    '2_6_didattica_laboratoriale_score': 'Didattica: Laboratoriale',
    '2_6_didattica_flessibilita_spazi_tempi_score': 'Didattica: Flessibilità Spazi/Tempi',
    '2_6_didattica_interdisciplinare_score': 'Didattica: Interdisciplinare',
    # Opportunità (2.7)
    '2_7_opzionali_culturali_score': 'Opportunità: Culturali',
    '2_7_opzionali_laboratoriali_espressive_score': 'Opportunità: Espressive',
    '2_7_opzionali_ludiche_ricreative_score': 'Opportunità: Ludico-Ricreative',
    '2_7_opzionali_volontariato_score': 'Opportunità: Volontariato',
    '2_7_opzionali_sportive_score': 'Opportunità: Sportive',
    # Indices
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi',
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica Orientativa',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice di Robustezza',
    'partnership_count': 'N. Partnership',
    'activities_count': 'N. Attività',
    '2_1_score': 'Sezione Orientamento Dedicata'
}

def get_label(col):
    """Returns Italian label for a column, or cleaned version of column name."""
    return LABEL_MAP.get(col, col.replace('_', ' ').replace('score', '').title().strip())

# Data Loading
# Removed @st.cache_data as it might interfere with dynamic file loading
def load_data():
    all_files = glob.glob(SUMMARY_FILE_PATTERN)
    if not all_files:
        return pd.DataFrame()
    
    dfs = []
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            dfs.append(df)
        except Exception as e:
            st.error(f"Errore caricamento {filename}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Rimuovi duplicati se ci sono (basato su school_id)
    if 'school_id' in df.columns:
        df = df.drop_duplicates(subset=['school_id'], keep='last')
        
    # Estrarre school_id dal nome file quando è "ND"
    def extract_school_id_from_file(row):
        if row['school_id'] == 'ND' or pd.isna(row['school_id']):
            analysis_file = row.get('analysis_file', '')
            if analysis_file:
                filename = os.path.basename(analysis_file)
                return filename.replace('_analysis.md', '').replace('_analysis.json', '')
        return row['school_id']
    
    df['school_id'] = df.apply(extract_school_id_from_file, axis=1)
    
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
                # Normalizzazione
                name = name.upper().strip()
                
                # Keywords chiare per II Grado
                keywords_ii_grado = [
                    'LICEO', 'TECNICO', 'PROFESSIONALE', 'IIS', 'ISIS', 'IT ', 'IPS', 'ISTITUTO SUPERIORE', 
                    'SCIENTIFICO', 'CLASSICO', 'LINGUISTICO', 'ARTISTICO'
                ]
                
                if any(k in name for k in keywords_ii_grado):
                    return 'II Grado'
                
                # Keywords per I Grado (Comprensivi, Medie)
                keywords_i_grado = [
                    'IC ', 'COMPRENSIVO', 'MEDIA', 'ELEMENTARE', 'DIREZIONE DIDATTICA', ' PRIMARIA', 'SEC. I GRADO'
                ]
                
                if any(k in name for k in keywords_i_grado):
                    return 'I Grado'
                    
                # Default fallback (spesso IC omessi o nomi di fantasia sono comprensivi)
                return 'I Grado'
            
            df['ordine_grado'] = df['denominazione'].apply(infer_level)
    
    # Ensure numeric columns
    cols_to_numeric = [c for c in df.columns if '_score' in c or 'mean_' in c or 'index' in c or 'count' in c]
    for c in cols_to_numeric:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    return df

df = load_data()

if df.empty:
    st.warning(f"Nessun dato trovato in {SUMMARY_FILE_PATTERN}. Esegui prima l'analisi.")
    st.stop()

# Sidebar Filters
st.sidebar.header("🔍 Filtri")
st.sidebar.info(f"📚 Scuole Caricate: **{len(df)}**")

# Filter: Area Geografica
if 'area_geografica' in df.columns:
    all_areas = sorted([x for x in df['area_geografica'].unique() if str(x) != 'nan'])
    selected_areas = st.sidebar.multiselect("Area Geografica", all_areas, default=all_areas)
    if selected_areas:
        df = df[df['area_geografica'].isin(selected_areas)]

# Filter: Tipo Scuola
if 'tipo_scuola' in df.columns:
    all_types = sorted([x for x in df['tipo_scuola'].unique() if str(x) != 'nan'])
    selected_types = st.sidebar.multiselect("Tipo Scuola", all_types, default=all_types)
    if selected_types:
        df = df[df['tipo_scuola'].isin(selected_types)]

# Filter: Territorio
if 'territorio' in df.columns:
    all_territories = sorted([x for x in df['territorio'].unique() if str(x) != 'nan'])
    selected_territories = st.sidebar.multiselect("Territorio", all_territories, default=all_territories)
    if selected_territories:
        df = df[df['territorio'].isin(selected_territories)]

# Filter: Grado (Legacy but useful if mixed)
if 'ordine_grado' in df.columns:
    school_levels = sorted([x for x in df['ordine_grado'].unique() if str(x) != 'nan'])
    if len(school_levels) > 1:
        selected_level = st.sidebar.multiselect("Grado Scolastico", school_levels, default=school_levels)
        df = df[df['ordine_grado'].isin(selected_level)]

# Filter: Score Range
score_range = st.sidebar.slider(
    "Indice di Robustezza",
    min_value=1.0, max_value=7.0, value=(1.0, 7.0), step=0.1
)
if 'ptof_orientamento_maturity_index' in df.columns:
    df = df[
        (df['ptof_orientamento_maturity_index'] >= score_range[0]) & 
        (df['ptof_orientamento_maturity_index'] <= score_range[1])
    ]

st.sidebar.markdown(f"**{len(df)} scuole filtrate**")
st.sidebar.markdown("---")
with st.sidebar.expander("📘 Glossario Completo", expanded=False):
    st.markdown("""
    ### 📊 Indice di Robustezza del Sistema
    Punteggio complessivo (1-7) che misura la solidità e la sistemicità delle azioni di orientamento nel PTOF.
    
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
st.subheader("📈 Indicatori Chiave di Sistema")

# 1. Main Overview Row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("🏫 Scuole Analizzate", len(df), delta_color="off")
with c2:
    if 'ptof_orientamento_maturity_index' in df.columns:
        avg_maturity = df['ptof_orientamento_maturity_index'].mean()
        st.metric("💎 Indice Robustezza Medio", f"{avg_maturity:.2f}/7", help="Media dell'Indice di Robustezza del Sistema")
with c3:
    if 'has_sezione_dedicata' in df.columns:
        perc_dedicated = (df['has_sezione_dedicata'].sum() / len(df)) * 100 if len(df) > 0 else 0
        st.metric("📑 % con Sez. Dedicata", f"{perc_dedicated:.0f}%", help="Percentuale di scuole con una sezione PTOF esplicita per l'orientamento")
with c4:
    if 'partnership_count' in df.columns:
        st.metric("🤝 Partner Medi per Scuola", f"{df['partnership_count'].mean():.1f}")

st.markdown("---")

# 2. Detailed Dimension Scores Row
st.subheader("🧩 Medie per Dimensione (1-7)")

# Check if columns exist
dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in dim_cols):
    d1, d2, d3, d4, d5 = st.columns(5)
    
    with d1:
        st.metric("🎯 Finalità", f"{df['mean_finalita'].mean():.2f}", help="Chiarezza su attitudini, interessi e progetto di vita")
    with d2:
        st.metric("🏁 Obiettivi", f"{df['mean_obiettivi'].mean():.2f}", help="Riduzione abbandono, NEET, continuità")
    with d3:
        st.metric("⚖️ Governance", f"{df['mean_governance'].mean():.2f}", help="Coordinamento, monitoraggio, inclusione")
    with d4:
        st.metric("🧠 Didattica", f"{df['mean_didattica_orientativa'].mean():.2f}", help="Laboratori, esperienziale, flessibilità")
    with d5:
        st.metric("🚀 Opportunità", f"{df['mean_opportunita'].mean():.2f}", help="Attività extra, sport, volontariato")

st.markdown("---")

# --- Charts Area ---
c1, c2 = st.columns(2)

# Chart 1: Distribution
with c1:
    st.subheader("📊 Distribuzione Indice Robustezza")
    if 'ptof_orientamento_maturity_index' in df.columns:
        fig_dist = px.histogram(
            df, 
            x='ptof_orientamento_maturity_index',
            nbins=14,
            range_x=[1, 7],
            color='area_geografica' if 'area_geografica' in df.columns else None,
            title="Distribuzione Indice Robustezza",
            labels={'ptof_orientamento_maturity_index': 'Indice Robustezza', 'area_geografica': 'Area Geografica'}
        )
        st.plotly_chart(fig_dist, use_container_width=True)

# Chart 2: Heatmap or Comparison
with c2:
    st.subheader("🌍 Media per Area Geografica")
    if 'area_geografica' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        avg_by_area = df.groupby('area_geografica')['ptof_orientamento_maturity_index'].mean().reset_index()
        fig_area = px.bar(
            avg_by_area,
            x='area_geografica',
            y='ptof_orientamento_maturity_index',
            color='area_geografica',
            range_y=[0, 7],
            title="Confronto Aree Geografiche",
            labels={'ptof_orientamento_maturity_index': 'Indice Robustezza', 'area_geografica': 'Area Geografica'}
        )
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Dati geografici non disponibili")

# Chart 3: Details by Type (Heatmap style if possible or simple bar)
if 'tipo_scuola' in df.columns and 'area_geografica' in df.columns:
    st.subheader("🔥 Matrice Performance: Area x Tipo Scuola")
    pivot = df.pivot_table(
        index='tipo_scuola', 
        columns='area_geografica', 
        values='ptof_orientamento_maturity_index', 
        aggfunc='mean'
    )
    if not pivot.empty:
        fig_heat = px.imshow(
            pivot,
            text_auto='.2f',
            color_continuous_scale='RdBu',
            zmin=1, zmax=7,
            title="Indice Medio per Tipo e Area",
            labels={'color': 'Indice Robustezza', 'x': 'Area Geografica', 'y': 'Tipo Scuola'}
        )
        st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# Chart 4 & 5: Comparisons (Territory & Grade)
st.subheader("🏙️ Confronti: Territorio e Grado Scolastico")
c3, c4 = st.columns(2)

with c3:
    if 'territorio' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        fig_terr = px.box(
            df, 
            x='territorio', 
            y='ptof_orientamento_maturity_index',
            points="all",
            color='territorio',
            title="Distribuzione per Territorio (Metro vs Non-Metro)",
            labels={'ptof_orientamento_maturity_index': 'Indice Robustezza', 'territorio': 'Territorio'}
        )
        st.plotly_chart(fig_terr, use_container_width=True)
    else:
        st.info("Dati territorio non disponibili")

with c4:
    if 'ordine_grado' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        fig_grade = px.box(
            df, 
            x='ordine_grado', 
            y='ptof_orientamento_maturity_index',
            points="all",
            color='ordine_grado',
            title="Distribuzione per Grado Scolastico",
            labels={'ptof_orientamento_maturity_index': 'Indice Robustezza', 'ordine_grado': 'Grado Scolastico'}
        )
        st.plotly_chart(fig_grade, use_container_width=True)
    else:
        st.info("Dati grado scolastico non disponibili")

st.markdown("---")

# 1. Scores Distribution
st.subheader("📊 Distribuzione Punteggi Dettagliata (Scala 1-7)")

# Define Categories and Colors
CATEGORY_COLOR_MAP = {
    'Finalità': '#636EFA',  # Blue
    'Obiettivi': '#EF553B', # Red-Orange
    'Governance': '#00CC96', # Green
    'Didattica': '#AB63FA', # Purple
    'Opportunità': '#FFA15A' # Orange
}

score_columns = [c for c in df.columns if '_score' in c and c != '2_1_score']
if score_columns:
    # Build ordered list with categories
    ordered_cols = []
    categories = []
    
    for c in score_columns:
        if '2_3_' in c:
            ordered_cols.append(c)
            categories.append('Finalità')
        elif '2_4_' in c:
            ordered_cols.append(c)
            categories.append('Obiettivi')
        elif '2_5_' in c:
            ordered_cols.append(c)
            categories.append('Governance')
        elif '2_6_' in c:
            ordered_cols.append(c)
            categories.append('Didattica')
        elif '2_7_' in c:
            ordered_cols.append(c)
            categories.append('Opportunità')
    
    if ordered_cols:  # Only proceed if we found matching columns
        scores_mean = df[ordered_cols].mean()
        labels_italian = [get_label(c) for c in ordered_cols]
        
        chart_df = pd.DataFrame({
            'Dimensione': labels_italian,
            'Punteggio': scores_mean.values,
            'Categoria': categories
        })
        
        # Tabs for cleaner view
        tab_overview, tab_fin, tab_obj, tab_gov, tab_did, tab_opp = st.tabs(
            ["🌈 Visione d'Insieme", "🎯 Finalità", "🏁 Obiettivi", "⚖️ Governance", "🧠 Didattica", "🚀 Opportunità"]
        )
        
        with tab_overview:
            chart_df_sorted = chart_df.sort_values(['Categoria', 'Punteggio'], ascending=[True, True])
            fig = px.bar(chart_df_sorted, x='Punteggio', y='Dimensione', orientation='h',
                         color='Categoria', 
                         title="Tutti gli Indicatori",
                         labels={'Punteggio': 'Punteggio (1-7)'},
                         color_discrete_map=CATEGORY_COLOR_MAP,
                         height=600)
            fig.update_layout(xaxis=dict(range=[0, 7]), yaxis=dict(tickfont=dict(size=11)))
            st.plotly_chart(fig, use_container_width=True)
            
        def show_category_chart(cat_name, color):
            filtered_df = chart_df[chart_df['Categoria'] == cat_name].sort_values('Punteggio', ascending=True)
            if not filtered_df.empty:
                fig_cat = px.bar(filtered_df, x='Punteggio', y='Dimensione', orientation='h',
                                 title=f"Dettaglio: {cat_name}",
                                 labels={'Punteggio': 'Punteggio (1-7)'},
                                 color_discrete_sequence=[color],
                                 height=400)
                fig_cat.update_layout(xaxis=dict(range=[0, 7]))
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info(f"Nessun dato per {cat_name}")

        with tab_fin: show_category_chart("Finalità", "#636EFA")
        with tab_obj: show_category_chart("Obiettivi", "#EF553B")
        with tab_gov: show_category_chart("Governance", "#00CC96")
        with tab_did: show_category_chart("Didattica", "#AB63FA")
        with tab_opp: show_category_chart("Opportunità", "#FFA15A")

    else:
        st.info("Nessuna colonna di dettaglio trovata nello standard atteso (2.3 - 2.7).")
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

# Creare label leggibile usando school_id (già estratto dal nome file) + denominazione
df['_display_key'] = df.apply(lambda row: f"{row['school_id']} - {row.get('denominazione', 'ND')}", axis=1)

school_key = st.selectbox("Seleziona Scuola", df['_display_key'].unique())
school_data = df[df['_display_key'] == school_key].iloc[0]

c1, c2 = st.columns(2)
with c1:
    st.write(f"**Denominazione:** {school_data.get('denominazione', 'ND')}")
    st.write(f"**Grado:** {school_data.get('ordine_grado', 'ND')}")
with c2:
    # Get file paths - CSV has MD path, derive JSON from it
    analysis_file = school_data.get('analysis_file', '')
    if analysis_file.endswith('.md'):
        md_path = analysis_file
        json_path = analysis_file.replace('.md', '.json')
    elif analysis_file.endswith('.json'):
        json_path = analysis_file
        md_path = analysis_file.replace('.json', '.md')
    else:
        md_path = analysis_file
        json_path = analysis_file
    
    if md_path and os.path.exists(md_path):
        with open(md_path, 'r') as f:
            report_content = f.read()
        st.download_button("📥 Scarica Report (.md)", report_content, file_name=os.path.basename(md_path))
    else:
        st.write("Report non disponibile.")
        report_content = None

# Show Report Content
if md_path and os.path.exists(md_path) and report_content:
    with st.expander("📄 Visualizza Report Completo", expanded=True):
        st.markdown(report_content)

# Show Italianized JSON
if json_path and os.path.exists(json_path):
    # Check if file is not empty
    if os.path.getsize(json_path) > 0:
        with st.expander("📊 Visualizza Dati Strutturati (JSON Italianizzato)", expanded=False):
            try:
                import json
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                
                # Create italianized version
                st.subheader("Metadati")
                metadata = json_data.get('metadata', {})
                st.write(f"**Codice Scuola:** {metadata.get('school_id', 'ND')}")
                st.write(f"**Denominazione:** {metadata.get('denominazione', 'ND')}")
                st.write(f"**Grado:** {metadata.get('ordine_grado', 'ND')}")
                st.write(f"**Anno PTOF:** {metadata.get('anno_ptof', 'ND')}")
                
                st.markdown("---")
                st.subheader("Punteggi per Dimensione")
                
                # Sezione Dedicata
                sec2 = json_data.get('ptof_section2', {})
                sez_ded = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
                st.write(f"**Sezione Dedicata:** {'Sì' if sez_ded.get('has_sezione_dedicata', 0) == 1 else 'No'}")
                st.write(f"**Punteggio Sezione:** {sez_ded.get('score', 0)}/7")
                if sez_ded.get('note'):
                    st.caption(f"_{sez_ded.get('note')}_")
                
                # Finalità
                st.markdown("#### 📌 Finalità")
                fin = sec2.get('2_3_finalita', {})
                for key, label in [
                    ('finalita_attitudini', 'Attitudini e Talenti'),
                    ('finalita_interessi', 'Interessi e Passioni'),
                    ('finalita_progetto_vita', 'Progetto di Vita'),
                    ('finalita_transizioni_formative', 'Transizioni Formative'),
                    ('finalita_capacita_orientative_opportunita', 'Capacità Orientative')
                ]:
                    item = fin.get(key, {})
                    score = item.get('score', 0)
                    st.write(f"**{label}:** {score}/7")
                    if item.get('evidence_quote'):
                        st.caption(f"📄 _{item.get('evidence_quote')[:100]}..._ ({item.get('evidence_location', '')})")
                
                # Obiettivi
                st.markdown("#### 🎯 Obiettivi")
                obi = sec2.get('2_4_obiettivi', {})
                for key, label in [
                    ('obiettivo_ridurre_abbandono', 'Ridurre Abbandono'),
                    ('obiettivo_continuita_territorio', 'Continuità Territoriale'),
                    ('obiettivo_contrastare_neet', 'Contrastare NEET'),
                    ('obiettivo_lifelong_learning', 'Lifelong Learning')
                ]:
                    item = obi.get(key, {})
                    score = item.get('score', 0)
                    st.write(f"**{label}:** {score}/7")
                
                # Governance
                st.markdown("#### ⚙️ Governance")
                gov = sec2.get('2_5_azioni_sistema', {})
                for key, label in [
                    ('azione_coordinamento_servizi', 'Coordinamento Servizi'),
                    ('azione_dialogo_docenti_studenti', 'Dialogo Docenti-Studenti'),
                    ('azione_rapporto_scuola_genitori', 'Rapporto Scuola-Genitori'),
                    ('azione_monitoraggio_azioni', 'Monitoraggio Azioni'),
                    ('azione_sistema_integrato_inclusione_fragilita', 'Sistema Integrato Inclusione')
                ]:
                    item = gov.get(key, {})
                    score = item.get('score', 0)
                    st.write(f"**{label}:** {score}/7")
                
                # Didattica
                st.markdown("#### 📚 Didattica Orientativa")
                did = sec2.get('2_6_didattica_orientativa', {})
                for key, label in [
                    ('didattica_da_esperienza_studenti', 'Da Esperienza Studenti'),
                    ('didattica_laboratoriale', 'Laboratoriale'),
                    ('didattica_flessibilita_spazi_tempi', 'Flessibilità Spazi/Tempi'),
                    ('didattica_interdisciplinare', 'Interdisciplinare')
                ]:
                    item = did.get(key, {})
                    score = item.get('score', 0)
                    st.write(f"**{label}:** {score}/7")
                
                # Opportunità
                st.markdown("#### 🌟 Opportunità Opzionali")
                opp = sec2.get('2_7_opzionali_facoltative', {})
                for key, label in [
                    ('opzionali_culturali', 'Culturali'),
                    ('opzionali_laboratoriali_espressive', 'Laboratoriali/Espressive'),
                    ('opzionali_ludiche_ricreative', 'Ludiche/Ricreative'),
                    ('opzionali_volontariato', 'Volontariato'),
                    ('opzionali_sportive', 'Sportive')
                ]:
                    item = opp.get(key, {})
                    score = item.get('score', 0)
                    st.write(f"**{label}:** {score}/7")
                
                # Partnership
                st.markdown("---")
                st.subheader("🤝 Partnership")
                partnerships = sec2.get('2_2_partnership', {})
                partner_names = partnerships.get('partner_nominati', [])
                if partner_names:
                    st.write(f"**Numero Partner:** {len(partner_names)}")
                    st.write("**Partner Nominati:**")
                    for partner in partner_names:
                        st.write(f"- {partner}")
                else:
                    st.write("Nessuna partnership nominata")
                
                # Activities Register
                activities = json_data.get('activities_register', [])
                if activities:
                    st.markdown("---")
                    st.subheader("📋 Registro Attività")
                    st.write(f"**Numero Attività:** {len(activities)}")
                    for idx, act in enumerate(activities[:5]):  # Show first 5
                        st.markdown(f"**Attività {idx+1}: {act.get('titolo_attivita', 'ND')}**")
                        st.write(f"- **Categoria:** {act.get('categoria_principale', 'ND')}")
                        st.write(f"- **Ore:** {act.get('ore_dichiarate', 'ND')}")
                        st.write(f"- **Target:** {act.get('target', 'ND')}")
                        if act.get('evidence_quote'):
                            st.caption(f"📄 _{act.get('evidence_quote', '')}_")
                        st.markdown("")  # Add spacing
                    if len(activities) > 5:
                        st.caption(f"... e altre {len(activities) - 5} attività")

                
            except Exception as e:
                st.error(f"Errore nel caricamento del JSON: {e}")
    else:
        st.info("📝 Il file JSON è in fase di generazione. Ricarica la pagina tra qualche istante.")



# Comparative Bar Chart instead of Radar
if score_columns and ordered_cols:  # Use ordered_cols computed earlier
    # Prepare data for this school
    school_vals = school_data[ordered_cols].values
    labels_italian = [get_label(c) for c in ordered_cols]
    
    # Re-use categories logic from previous block or re-derive
    # We can rebuild the DF for the chart
    school_chart_df = pd.DataFrame({
        'Dimensione': labels_italian,
        'Punteggio': school_vals,
        'Categoria': categories # Assumes 'categories' is still available from main block scope or re-computed
    })
    
    school_chart_df = school_chart_df.sort_values(['Categoria', 'Punteggio'], ascending=[True, True])

    fig_bar_school = px.bar(
        school_chart_df,
        x='Punteggio',
        y='Dimensione',
        orientation='h',
        color='Categoria',
        title=f"Dettaglio Punteggi: {school_data.get('denominazione', 'Scuola Selezionata')}",
        labels={'Punteggio': 'Punteggio (1-7)'},
        color_discrete_map=CATEGORY_COLOR_MAP,
        height=600,
        range_x=[0, 7]
    )
    fig_bar_school.update_layout(yaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig_bar_school, use_container_width=True)
