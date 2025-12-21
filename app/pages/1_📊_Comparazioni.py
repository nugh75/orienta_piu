# 📊 Comparazioni - Confronti tra gruppi

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Comparazioni", page_icon="📊", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice Robustezza',
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("📊 Comparazioni tra Gruppi")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# Convert to numeric
numeric_cols = [
    'ptof_orientamento_maturity_index', 
    'mean_finalita', 'mean_obiettivi', 
    'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita'
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

st.markdown("---")

# 1. Heatmap Area x Tipo
st.subheader("🔥 Matrice Performance: Area x Tipo Scuola")
st.caption("Confronto del punteggio medio per area geografica e tipo di scuola.")

if 'tipo_scuola' in df.columns and 'area_geografica' in df.columns:
    try:
        from app.data_utils import explode_school_types
        df_pivot = explode_school_types(df)
    except ImportError:
        df_pivot = df
        
    # Pivot calculation
    pivot = df_pivot.pivot_table(
        index='tipo_scuola', 
        columns='area_geografica', 
        values='ptof_orientamento_maturity_index', 
        aggfunc='mean'
    )
    
    if not pivot.empty:
        fig = px.imshow(
            pivot, text_auto='.2f', color_continuous_scale='RdBu',
            zmin=1, zmax=7, title="Indice Medio per Tipo e Area"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dati insufficienti per la Heatmap")
else:
    st.warning("Colonne 'tipo_scuola' o 'area_geografica' mancanti.")

st.markdown("---")

# 2. Radar Chart (NEW)
st.subheader("🕸️ Radar Chart: Profili a Confronto")
st.caption("Confronto delle 5 dimensioni di maturità tra diversi gruppi.")

radar_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in radar_cols):
    radar_group = st.selectbox("Raggruppa per:", ["tipo_scuola", "area_geografica", "ordine_grado"], index=0) # Index 0 is tipo_scuola
    
    if radar_group in df.columns:
        # Calculate means
        radar_df = df.groupby(radar_group)[radar_cols].mean().reset_index()
        
        fig = go.Figure()
        
        # Add trace for each group
        for i, row in radar_df.iterrows():
            group_name = str(row[radar_group])
            values = row[radar_cols].values.tolist()
            # Close the loop
            values += values[:1]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=[get_label(c) for c in radar_cols] + [get_label(radar_cols[0])],
                fill='toself',
                name=group_name
            ))
            
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 7]
                )
            ),
            showlegend=True,
            title=f"Confronto Profili per {radar_group.replace('_', ' ').title()}",
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dati insufficienti per il Radar Chart")

st.markdown("---")

# 3. Box plots Territorio e Grado
st.subheader("🏙️ Confronti: Territorio e Grado Scolastico")
col1, col2 = st.columns(2)

with col1:
    if 'territorio' in df.columns:
        fig = px.box(df, x='territorio', y='ptof_orientamento_maturity_index',
                     points="all", color='territorio',
                     title="Distribuzione per Territorio")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if 'ordine_grado' in df.columns:
        fig = px.box(df, x='ordine_grado', y='ptof_orientamento_maturity_index',
                     points="all", color='ordine_grado',
                     title="Distribuzione per Grado")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 4. Grouped Bar I Grado vs II Grado
st.subheader("📊 Confronto I Grado vs II Grado")

if 'ordine_grado' in df.columns:
    dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in dim_cols):
        grado_df = df.groupby('ordine_grado')[dim_cols].mean().reset_index()
        grado_melted = grado_df.melt(id_vars='ordine_grado', var_name='Dimensione', value_name='Media')
        grado_melted['Dimensione'] = grado_melted['Dimensione'].apply(get_label)
        
        fig = px.bar(grado_melted, x='Dimensione', y='Media', color='ordine_grado',
                     barmode='group', title="Media per Dimensione: I Grado vs II Grado")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 5. Gap Analysis
st.subheader("🎯 Gap Analysis: Distanza dal Ottimo (7)")
gap_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in gap_cols):
    gap_means = df[gap_cols].mean()
    gap_values = 7 - gap_means
    
    gap_df = pd.DataFrame({
        'Dimensione': [get_label(c) for c in gap_cols],
        'Punteggio Attuale': gap_means.values,
        'Gap da 7': gap_values.values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Punteggio Attuale'], 
                         name='Attuale', marker_color='#00CC96'))
    fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Gap da 7'], 
                         name='Gap', marker_color='#EF553B'))
    fig.update_layout(barmode='stack', yaxis=dict(range=[0, 7]))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 6. Regional comparison
st.subheader("🗺️ Confronto Regionale")
def get_region(code):
    if pd.isna(code) or len(str(code)) < 2:
        return None
    prefix = str(code)[:2].upper()
    regions = {
        'TO': 'Piemonte', 'MI': 'Lombardia', 'VE': 'Veneto', 'BO': 'Emilia-Romagna',
        'FI': 'Toscana', 'RM': 'Lazio', 'NA': 'Campania', 'BA': 'Puglia',
        'PA': 'Sicilia', 'CA': 'Sardegna', 'BG': 'Lombardia', 'BS': 'Lombardia',
        'MO': 'Emilia-Romagna', 'CS': 'Calabria', 'FG': 'Puglia', 'TE': 'Abruzzo',
        'BN': 'Campania', 'CH': 'Abruzzo', 'AG': 'Sicilia', 'SR': 'Sicilia',
        'RG': 'Sicilia', 'CT': 'Sicilia', 'SS': 'Sardegna', 'SA': 'Campania'
    }
    return regions.get(prefix)

if 'school_id' in df.columns:
    df['regione'] = df['school_id'].apply(get_region)
    region_counts = df['regione'].value_counts()
    
    if len(region_counts.dropna()) >= 3:
        region_avg = df.groupby('regione')['ptof_orientamento_maturity_index'].agg(['mean', 'count']).reset_index()
        region_avg.columns = ['Regione', 'Indice Medio', 'N. Scuole']
        region_avg = region_avg.dropna()
        
        if len(region_avg) >= 3:
            fig = px.bar(region_avg.sort_values('Indice Medio'), x='Indice Medio', y='Regione',
                        orientation='h', color='Indice Medio', color_continuous_scale='RdYlGn',
                        range_color=[1, 7], text='N. Scuole', title="Indice per Regione")
            fig.update_traces(texttemplate='n=%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dati regionali insufficienti (servono almeno 3 regioni)")
    else:
        st.info("Dati regionali insufficienti")
