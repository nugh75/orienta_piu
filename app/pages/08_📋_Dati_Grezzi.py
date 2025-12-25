# 📋 Dati Grezzi - Esplorazione e verifica dati

import streamlit as st
import pandas as pd
import os
import glob
import json

st.set_page_config(page_title="Dati Grezzi", page_icon="📋", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

# Removed cache to ensure fresh data
def load_data():
    df = pd.DataFrame()
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
    
    # Analysis summary è la fonte di verità per la regione.
    if not df.empty and 'regione' in df.columns:
        df['regione'] = df['regione'].fillna('DA VERIFICARE')
    
    return df

df = load_data()

st.title("📋 Dati Grezzi e Verifica")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina permette di **esplorare i dati grezzi** e verificare la qualità e completezza del dataset.
    
    ### 📊 Sezioni Disponibili
    
    **📊 Tabella Completa**
    - Visualizza tutti i dati in formato tabellare
    - Puoi selezionare quali colonne mostrare
    - Usa la ricerca integrata per trovare scuole specifiche
    - Le colonne sono ordinabili cliccando sull'intestazione
    
    **📈 Statistiche Descrittive**
    - Per ogni colonna numerica mostra:
      - **N**: Numero di valori non nulli
      - **Media**: Valore medio
      - **Dev.Std**: Dispersione dei dati (valori bassi = dati simili)
      - **Min/Max**: Range dei valori
      - **Q1, Mediana, Q3**: Quartili (25°, 50°, 75° percentile)
    
    **🔍 Analisi Valori Mancanti**
    - Elenca le colonne con dati mancanti
    - La percentuale indica la completezza dei dati
    - Valori mancanti alti possono indicare problemi di qualità dati
    
    **🛠️ Verifica File JSON**
    - Controlla la coerenza tra file di analisi e dati aggregati
    - Evidenzia eventuali discrepanze
    
    ### 🔢 Come Usare Questa Pagina
    - **Per l'esplorazione**: Seleziona le colonne di interesse e ordina i dati
    - **Per il debug**: Verifica valori mancanti e statistiche
    - **Per l'export**: I dati possono essere copiati dalla tabella
    """)

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
# Imposta tutte le colonne come default per mostrare tutto il CSV
selected_cols = st.multiselect("Seleziona colonne da visualizzare", all_cols, default=all_cols)

if selected_cols:
    st.dataframe(df[selected_cols], use_container_width=True, height=400)
else:
    st.warning("Seleziona almeno una colonna")

st.info("""
💡 **A cosa serve**: Esplora tutti i dati grezzi del dataset in formato tabellare.

🔍 **Cosa rileva**: Ogni riga è una scuola, ogni colonna un attributo. Clicca sulle intestazioni per ordinare. Usa la barra di ricerca integrata (in alto a destra) per trovare scuole specifiche.

🎯 **Implicazioni**: Utile per verifiche puntuali, export di dati specifici, e per rispondere a domande specifiche ("Quali scuole di Roma hanno punteggio > 5?").
""")

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
    
    st.info("""
💡 **A cosa serve**: Fornisce un riassunto statistico di tutte le variabili numeriche del dataset.

🔍 **Cosa rileva**: N = valori validi, Media = valore medio, Dev.Std = dispersione (bassa = dati omogenei), Q1/Mediana/Q3 = distribuzione. Min/Max = valori estremi.

🎯 **Implicazioni**: Una deviazione standard alta indica grande variabilità tra scuole. Se Min e Max sono molto distanti, ci sono casi estremi che meritano attenzione.
""")

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
    st.info("""
💡 **A cosa serve**: Identifica quali informazioni mancano nel dataset e in che misura.

🔍 **Cosa rileva**: La tabella mostra le colonne con dati mancanti e la percentuale. Valori alti indicano lacune informative significative.

🎯 **Implicazioni**: Se una colonna importante (es. regione) ha molti mancanti, le analisi per quella dimensione saranno meno affidabili. Potrebbe essere necessario integrare i dati mancanti.
""")
else:
    st.success("✅ Nessun valore mancante!")

st.markdown("---")

# 4. School Detail Explorer
st.subheader("🏫 Esplora Singola Scuola")

# Disambiguate duplicate names by adding ID
df['display_label'] = df['denominazione'].astype(str) + " [" + df['school_id'].astype(str) + "]"
school_options = sorted(df['display_label'].unique().tolist())

selected_label = st.selectbox("Seleziona scuola", school_options)

if selected_label:
    # Filter by unique label
    school_row = df[df['display_label'] == selected_label].iloc[0]
    
    # Show all data as columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Metadati:**")
        for col in ['school_id', 'denominazione', 'regione', 'tipo_scuola', 'area_geografica', 'ordine_grado', 'territorio', 'comune']:
            if col in df.columns:
                val = school_row[col]
                # Handle various empty states
                if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
                    val = "ND (Dato mancante)"
                st.write(f"- **{col}:** {val}")
            else:
                st.write(f"- **{col}:** ⚠️ Colonna assente nel CSV")
    
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

st.info("""
💡 **A cosa serve**: Permette di esaminare nel dettaglio i dati di una singola scuola selezionata.

🔍 **Cosa rileva**: Mostra tutti i metadati (ID, nome, regione, tipo) e tutti gli indici calcolati (Indice RO, medie dimensionali, singoli punteggi). Ogni aspetto valutato nel PTOF è visibile.

🎯 **Implicazioni**: Usa questa sezione per verificare dati specifici, rispondere a domande puntuali su una scuola, o per validare che l'analisi automatica abbia funzionato correttamente.
""")

st.markdown("---")

# 5. JSON Viewer
st.subheader("📄 Visualizza JSON Originale")

if selected_label:
    # Estrai school_id dalla riga selezionata (già filtrata sopra)
    school_id = school_row['school_id']
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

st.info("""
💡 **A cosa serve**: Mostra il file JSON originale prodotto dall'analisi del PTOF di questa scuola.

🔍 **Cosa rileva**: Il JSON contiene tutti i dati estratti: testi analizzati, punteggi assegnati dall'AI, motivazioni delle valutazioni, e metadati. È il documento completo dell'analisi.

🎯 **Implicazioni**: Utile per verificare nel dettaglio come sono stati assegnati i punteggi, controllare le motivazioni dell'AI, o esportare dati per analisi esterne.
""")

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
    if selected_label and 'json_data' in locals() and json_data:
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Scarica JSON Scuola",
            data=json_str,
            file_name=f"{school_id}_analysis.json",
            mime="application/json"
        )

st.info("""
💡 **A cosa serve**: Consente di scaricare i dati in formati riutilizzabili (CSV o JSON).

🔍 **Cosa rileva**: Il CSV contiene il riepilogo di tutte le scuole analizzate in formato tabellare, pronto per Excel o altri software. Il JSON della scuola selezionata contiene l'analisi completa di quella specifica scuola.

🎯 **Implicazioni**: Usa i download per analisi offline, report personalizzati, o integrazione con altri strumenti. Il CSV è ideale per statistiche aggregate, il JSON per approfondimenti su singole scuole.
""")

st.markdown("---")
st.caption("📋 Dati Grezzi - Usa questa pagina per verificare l'affidabilità dei dati")
