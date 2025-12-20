# 📋 Dati Grezzi - Esplorazione e verifica dati

import streamlit as st
import pandas as pd
import os
import json
import glob

st.set_page_config(page_title="Dati Grezzi", page_icon="📋", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("📋 Dati Grezzi e Verifica")
st.markdown("Esplora i dati grezzi per verificare affidabilità e completezza")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

st.markdown("---")

# 1. Full Data Table
st.subheader("📊 Tabella Completa")
st.markdown(f"**{len(df)} scuole** | **{len(df.columns)} colonne**")

# Column selector
all_cols = df.columns.tolist()
default_cols = ['school_id', 'denominazione', 'tipo_scuola', 'area_geografica', 'ordine_grado', 
                'ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
default_cols = [c for c in default_cols if c in all_cols]

selected_cols = st.multiselect("Seleziona colonne da visualizzare", all_cols, default=default_cols)

if selected_cols:
    st.dataframe(df[selected_cols], use_container_width=True, height=400)

st.markdown("---")

# 2. Statistics Summary
st.subheader("📈 Statistiche Descrittive")
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
score_cols = [c for c in numeric_cols if '_score' in c or 'mean_' in c or 'index' in c.lower()]

if score_cols:
    stats = df[score_cols].describe().T
    stats = stats[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]
    stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Q1', 'Mediana', 'Q3', 'Max']
    st.dataframe(stats.round(2), use_container_width=True)

st.markdown("---")

# 3. Missing Values Analysis
st.subheader("🔍 Analisi Valori Mancanti")
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(1)
missing_df = pd.DataFrame({
    'Colonna': missing.index,
    'Mancanti': missing.values,
    'Percentuale': missing_pct.values
})
missing_df = missing_df[missing_df['Mancanti'] > 0].sort_values('Mancanti', ascending=False)

if len(missing_df) > 0:
    st.dataframe(missing_df, use_container_width=True, hide_index=True)
else:
    st.success("✅ Nessun valore mancante!")

st.markdown("---")

# 4. School Detail Explorer
st.subheader("🏫 Esplora Singola Scuola")
school_options = df['denominazione'].dropna().unique().tolist()
selected_school = st.selectbox("Seleziona scuola", school_options)

if selected_school:
    school_row = df[df['denominazione'] == selected_school].iloc[0]
    
    # Show all data as columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Metadati:**")
        for col in ['school_id', 'denominazione', 'tipo_scuola', 'area_geografica', 'ordine_grado', 'territorio', 'comune']:
            if col in df.columns:
                val = school_row.get(col, 'N/D')
                st.write(f"- **{col}:** {val}")
    
    with col2:
        st.markdown("**Indici:**")
        for col in ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita', 'partnership_count']:
            if col in df.columns:
                val = school_row.get(col, 'N/D')
                if pd.notna(val) and isinstance(val, (int, float)):
                    st.write(f"- **{col}:** {val:.2f}")
                else:
                    st.write(f"- **{col}:** {val}")
    
    # All score values
    st.markdown("**Tutti i punteggi:**")
    score_cols = [c for c in df.columns if '_score' in c]
    score_data = {c: school_row.get(c, 0) for c in score_cols}
    st.dataframe(pd.DataFrame([score_data]), use_container_width=True)

st.markdown("---")

# 5. JSON Viewer
st.subheader("📄 Visualizza JSON Originale")

if selected_school:
    school_id = df[df['denominazione'] == selected_school]['school_id'].iloc[0]
    json_files = glob.glob(f'analysis_results/*{school_id}*_analysis.json')
    
    if json_files:
        try:
            with open(json_files[0], 'r') as f:
                json_data = json.load(f)
            
            st.json(json_data)
            
        except Exception as e:
            st.error(f"Errore caricamento JSON: {e}")
    else:
        st.info("JSON non ancora disponibile per questa scuola")

st.markdown("---")

# 6. Export Options
st.subheader("📥 Esporta Dati")
col1, col2 = st.columns(2)

with col1:
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Scarica CSV Completo",
        data=csv,
        file_name="analysis_summary_export.csv",
        mime="text/csv"
    )

with col2:
    if selected_school and 'json_data' in dir():
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Scarica JSON Scuola",
            data=json_str,
            file_name=f"{school_id}_analysis.json",
            mime="application/json"
        )

st.markdown("---")
st.caption("📋 Dati Grezzi - Usa questa pagina per verificare l'affidabilità dei dati")
