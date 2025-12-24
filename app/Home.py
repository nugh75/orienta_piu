# 🏠 Home - Dashboard Analisi PTOF

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Dashboard PTOF", page_icon="📊", layout="wide")

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

# Constants
SUMMARY_FILE = 'data/analysis_summary.csv'

# Label Mapping
LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice RO',
    'partnership_count': 'N. Partnership',
    'activities_count': 'N. Attività',
    '2_1_score': 'Sezione Dedicata'
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

# Load Data
@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        return df
    return pd.DataFrame()

df = load_data()

# Auto-Update Check (Lightweight)
try:
    if 'index_updated' not in st.session_state:
        from src.data.data_manager import update_index_safe
        # Only auto-run if CSV missing or explicit refresh needed?
        # For now, let's just do it once per session to be safe
        update_index_safe()
        st.session_state['index_updated'] = True
except Exception as e:
    st.error(f"Auto-update failed: {e}")

# Sidebar explicit refresh
if st.sidebar.button("🔄 Aggiorna Dati"):
    from src.data.data_manager import update_index_safe
    with st.spinner("Aggiornamento indice in corso..."):
        success, count = update_index_safe()
    if success:
        st.success(f"Indice aggiornato: {count} scuole.")
        st.cache_data.clear()
        st.rerun()

# Standardize numeric columns (handle 'ND')
numeric_cols = [
    'ptof_orientamento_maturity_index', 
    'mean_finalita', 'mean_obiettivi', 
    'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
    'partnership_count', 'has_sezione_dedicata'
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
# Title
st.title("📊 Dashboard Analisi Orientamento PTOF")
st.markdown("Sistema di analisi automatizzata dei Piani Triennali dell'Offerta Formativa")

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

st.sidebar.markdown(f"**{len(df)} scuole analizzate**")

# KPIs Row
st.subheader("📈 Indicatori Chiave")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("🏫 Scuole Analizzate", len(df))

with c2:
    if 'ptof_orientamento_maturity_index' in df.columns:
        avg_idx = df['ptof_orientamento_maturity_index'].mean()
        st.metric("📊 Indice RO Medio", f"{avg_idx:.2f}/7" if pd.notna(avg_idx) else "N/D", help="Indice di Robustezza dell'Orientamento")
    else:
        st.metric("📊 Indice RO Medio", "N/D")

with c3:
    if 'has_sezione_dedicata' in df.columns:
        pct = (df['has_sezione_dedicata'].sum() / len(df)) * 100 if len(df) > 0 else 0
        st.metric("📋 % Sez. Dedicata", f"{pct:.0f}%")
    else:
        st.metric("📋 % Sez. Dedicata", "N/D")

with c4:
    if 'partnership_count' in df.columns:
        avg_p = df['partnership_count'].mean()
        st.metric("🤝 Partner Medi", f"{avg_p:.1f}" if pd.notna(avg_p) else "N/D")
    else:
        st.metric("🤝 Partner Medi", "N/D")

st.markdown("---")

# Distribution Charts
st.subheader("📊 Distribuzione Scuole")
col1, col2, col3 = st.columns(3)

with col1:
    if 'territorio' in df.columns:
        fig = px.pie(df, names='territorio', title="Per Territorio", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if 'tipo_scuola' in df.columns:
        try:
            from app.data_utils import explode_school_types
            df_exploded = explode_school_types(df)
            # Count occurrences
            type_counts = df_exploded['tipo_scuola'].value_counts().reset_index()
            type_counts.columns = ['tipo_scuola', 'count']
            
            fig = px.pie(type_counts, names='tipo_scuola', values='count', title="Per Tipo Scuola", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            # Fallback if something fails
            if 'ordine_grado' in df.columns:
                fig = px.pie(df, names='ordine_grado', title="Per Grado", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

with col3:
    if 'area_geografica' in df.columns:
        fig = px.pie(df, names='area_geografica', title="Per Area", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Main Chart - Dimension Means
st.subheader("🧩 Medie per Dimensione (1-7)")
dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in dim_cols):
    means = df[dim_cols].mean()
    chart_df = pd.DataFrame({
        'Dimensione': [get_label(c) for c in dim_cols],
        'Punteggio': means.values
    })
    
    fig = px.bar(
        chart_df, x='Punteggio', y='Dimensione', orientation='h',
        color='Punteggio', color_continuous_scale='RdYlGn',
        range_x=[0, 7], range_color=[1, 7],
        title="Media Punteggi per Dimensione"
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Detailed breakdown by dimension tabs
st.subheader("📊 Distribuzione Punteggi Dettagliata")

# Define categories and their columns
CATEGORY_COLS = {
    '🎯 Finalità': [
        ('2_3_finalita_attitudini_score', 'Attitudini Personali'),
        ('2_3_finalita_interessi_score', 'Interessi'),
        ('2_3_finalita_progetto_vita_score', 'Progetto di Vita'),
        ('2_3_finalita_transizioni_formative_score', 'Transizioni Formative'),
        ('2_3_finalita_capacita_orientative_opportunita_score', 'Capacità Orientative'),
    ],
    '🏁 Obiettivi': [
        ('2_4_obiettivo_ridurre_abbandono_score', 'Riduzione Abbandono'),
        ('2_4_obiettivo_continuita_territorio_score', 'Continuità Territoriale'),
        ('2_4_obiettivo_contrastare_neet_score', 'Contrasto NEET'),
        ('2_4_obiettivo_lifelong_learning_score', 'Apprendimento Permanente'),
    ],
    '⚖️ Governance': [
        ('2_5_azione_coordinamento_servizi_score', 'Coordinamento Servizi'),
        ('2_5_azione_dialogo_docenti_studenti_score', 'Dialogo Docenti-Studenti'),
        ('2_5_azione_rapporto_scuola_genitori_score', 'Rapporto Scuola-Genitori'),
        ('2_5_azione_monitoraggio_azioni_score', 'Monitoraggio Azioni'),
        ('2_5_azione_sistema_integrato_inclusione_fragilita_score', 'Inclusione e Fragilità'),
    ],
    '🧠 Didattica': [
        ('2_6_didattica_da_esperienza_studenti_score', 'Esperienza Studenti'),
        ('2_6_didattica_laboratoriale_score', 'Laboratoriale'),
        ('2_6_didattica_flessibilita_spazi_tempi_score', 'Flessibilità Spazi/Tempi'),
        ('2_6_didattica_interdisciplinare_score', 'Interdisciplinare'),
    ],
    '🚀 Opportunità': [
        ('2_7_opzionali_culturali_score', 'Culturali'),
        ('2_7_opzionali_laboratoriali_espressive_score', 'Laboratoriali/Espressive'),
        ('2_7_opzionali_ludiche_ricreative_score', 'Ludico-Ricreative'),
        ('2_7_opzionali_volontariato_score', 'Volontariato'),
        ('2_7_opzionali_sportive_score', 'Sportive'),
    ],
}

# Category colors
CAT_COLORS = {
    '🎯 Finalità': '#636EFA',
    '🏁 Obiettivi': '#EF553B',
    '⚖️ Governance': '#00CC96',
    '🧠 Didattica': '#AB63FA',
    '🚀 Opportunità': '#FFA15A'
}

tabs = st.tabs(["🌈 Visione d'Insieme"] + list(CATEGORY_COLS.keys()))

# Tab 0: Overview
with tabs[0]:
    all_scores = []
    all_labels = []
    all_cats = []
    
    for cat, cols in CATEGORY_COLS.items():
        for col, label in cols:
            if col in df.columns:
                all_scores.append(df[col].mean())
                all_labels.append(label)
                all_cats.append(cat)
    
    if all_scores:
        overview_df = pd.DataFrame({
            'Dimensione': all_labels,
            'Punteggio': all_scores,
            'Categoria': all_cats
        }).sort_values(['Categoria', 'Punteggio'], ascending=[True, True])
        
        fig = px.bar(
            overview_df, x='Punteggio', y='Dimensione', orientation='h',
            color='Categoria', color_discrete_map=CAT_COLORS,
            range_x=[0, 7], title="Tutti i Punteggi per Sottodimensione",
            height=700
        )
        fig.update_layout(yaxis_tickfont_size=10)
        st.plotly_chart(fig, use_container_width=True)

# Individual category tabs
for i, (cat, cols) in enumerate(CATEGORY_COLS.items()):
    with tabs[i + 1]:
        scores = []
        labels = []
        for col, label in cols:
            if col in df.columns:
                scores.append(df[col].mean())
                labels.append(label)
        
        if scores:
            cat_df = pd.DataFrame({
                'Sottodimensione': labels,
                'Punteggio': scores
            }).sort_values('Punteggio', ascending=True)
            
            fig = px.bar(
                cat_df, x='Punteggio', y='Sottodimensione', orientation='h',
                color='Punteggio', color_continuous_scale='RdYlGn',
                range_x=[0, 7], range_color=[1, 7],
                title=f"Dettaglio {cat}",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Stats table
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Media", f"{sum(scores)/len(scores):.2f}")
            with col2:
                st.metric("Min", f"{min(scores):.2f}")
            with col3:
                st.metric("Max", f"{max(scores):.2f}")

st.markdown("---")

# Quick Stats Table - All schools with ranking
st.subheader("📋 Classifica Completa")
if len(df) > 0:
    stats_df = df[['school_id', 'denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']].copy()
    stats_df = stats_df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
    stats_df.insert(0, 'Pos.', range(1, len(stats_df) + 1))
    stats_df.columns = ['#', 'Codice', 'Scuola', 'Tipo', 'Area', 'Indice RO']
    st.dataframe(stats_df, use_container_width=True, hide_index=True, height=500)

# Footer
st.markdown("---")
st.caption("📊 Dashboard PTOF - PRIN 2022 | Navigazione: usa il menu a sinistra per accedere alle altre sezioni")
