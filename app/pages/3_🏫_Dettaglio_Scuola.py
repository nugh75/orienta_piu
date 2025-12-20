# 🏫 Dettaglio Scuola - Analisi singola scuola

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import glob

st.set_page_config(page_title="Dettaglio Scuola", page_icon="🏫", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("🏫 Dettaglio Scuola")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# School selector
school_options = df['denominazione'].dropna().unique().tolist()
selected_school = st.selectbox("Seleziona Scuola", school_options)

if selected_school:
    school_data = df[df['denominazione'] == selected_school].iloc[0]
    
    # Metadata
    st.subheader("📋 Informazioni Generali")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Codice", school_data.get('school_id', 'N/D'))
    with col2:
        st.metric("Tipo", school_data.get('tipo_scuola', 'N/D'))
    with col3:
        st.metric("Area", school_data.get('area_geografica', 'N/D'))
    with col4:
        idx = school_data.get('ptof_orientamento_maturity_index', 0)
        st.metric("Indice Robustezza", f"{idx:.2f}/7" if pd.notna(idx) else "N/D")
    
    st.markdown("---")
    
    # Radar Chart
    st.subheader("🕸️ Profilo Radar")
    radar_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in radar_cols):
        school_vals = [school_data.get(c, 0) if pd.notna(school_data.get(c)) else 0 for c in radar_cols]
        avg_vals = [df[c].mean() for c in radar_cols]
        labels = ['Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=school_vals + [school_vals[0]], theta=labels + [labels[0]],
                                       fill='toself', name=selected_school[:25]))
        fig.add_trace(go.Scatterpolar(r=avg_vals + [avg_vals[0]], theta=labels + [labels[0]],
                                       fill='toself', name='Media Campione', opacity=0.5))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Detailed scores bar chart
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
    
    st.markdown("---")
    
    # Load JSON for detailed data
    st.subheader("📄 Dettaglio dal Report")
    school_id = school_data.get('school_id', '')
    json_files = glob.glob(f'analysis_results/*{school_id}*_analysis.json')
    
    if json_files:
        try:
            with open(json_files[0], 'r') as f:
                json_data = json.load(f)
            
            sec2 = json_data.get('ptof_section2', {})
            
            # Partnership
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
            
            # Section 2.1
            with col2:
                st.markdown("### 📋 Sezione Orientamento")
                s21 = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
                has_sez = "✅ Sì" if s21.get('has_sezione_dedicata') else "❌ No"
                st.write(f"**Sezione dedicata:** {has_sez}")
                st.write(f"**Punteggio:** {s21.get('score', 'N/D')}/7")
                if s21.get('note'):
                    st.caption(s21.get('note'))
            
            st.markdown("---")
            
            # Finalità detail
            st.markdown("### 🎯 Finalità (dettaglio)")
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
    
    # Position in ranking
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
