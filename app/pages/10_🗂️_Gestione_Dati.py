# 🗂️ Gestione Dati - Esplora, Modifica e Backup
import streamlit as st
import pandas as pd
import os
import glob
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.backup_system import (
    create_backup, list_backups, restore_backup,
    create_backup_zip, restore_from_zip, delete_backup
)
from data_utils import render_footer
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Gestione Dati", page_icon="🧭", layout="wide")
setup_page("pages/10_🗂️_Gestione_Dati.py")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'
PTOF_PROCESSED_DIR = 'ptof_processed'
PTOF_INBOX_DIR = 'ptof_inbox'
PTOF_INVIATI_DIR = 'ptof_inviati'
PTOF_DISCARDED_DIR = 'ptof_discarded'
PTOF_SEARCH_DIRS = [PTOF_PROCESSED_DIR, PTOF_INBOX_DIR, PTOF_INVIATI_DIR]
PTOF_MD_DIR = 'ptof_md'


# Removed cache to ensure fresh data
def load_data_no_cache():
    df = pd.DataFrame()
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)

    # Analysis summary è la fonte di verità per la regione.
    if not df.empty and 'regione' in df.columns:
        df['regione'] = df['regione'].fillna('DA VERIFICARE')

    return df


@st.cache_data(ttl=30)
def load_data_cached():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()


def display_pdf(school_id, height=600):
    """Display PDF for a given school_id. Returns (path, bytes) when available."""
    import base64

    try:
        from data_utils import find_pdf_for_school
        pdf_path = find_pdf_for_school(school_id, base_dirs=PTOF_SEARCH_DIRS)
    except Exception:
        pdf_path = None
        pdf_patterns = []
        for base_dir in PTOF_SEARCH_DIRS:
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
            for base_dir in PTOF_SEARCH_DIRS:
                all_pdfs = glob.glob(os.path.join(base_dir, "**", "*.pdf"), recursive=True)
                for pdf in all_pdfs:
                    if school_id.upper() in os.path.basename(pdf).upper():
                        pdf_files.append(pdf)
                        break
                if pdf_files:
                    break
        if pdf_files:
            pdf_path = sorted(set(pdf_files))[0]

    if pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f"**📄 PDF:** `{os.path.basename(pdf_path)}`")
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf"></iframe>', unsafe_allow_html=True)
            return pdf_path, pdf_bytes
        except Exception as e:
            st.warning(f"Impossibile visualizzare PDF: {e}")
            return None, None
    else:
        st.info(f"PDF non trovato per {school_id}")
        st.caption("Cartelle cercate: ptof_processed/, ptof_inbox/, ptof_inviati/")
        return None, None


def discard_pdf(pdf_path: str) -> Optional[str]:
    """Move a PTOF PDF to the discarded folder. Returns new path or None."""
    try:
        target = Path(pdf_path)
        discard_dir = Path(PTOF_DISCARDED_DIR)
        discard_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dest = discard_dir / f"{target.stem}_{stamp}{target.suffix}"
        target.replace(dest)
        return str(dest)
    except Exception as e:
        st.error(f"Impossibile eliminare il PDF: {e}")
        return None


st.title("🗂️ Gestione Dati")

tab_explore, tab_edit, tab_backup = st.tabs(["📋 Esplora Dati", "✏️ Modifica Metadati", "🛡️ Backup & Ripristino"])

with tab_explore:
    st.title("📋 Dati Grezzi e Verifica")

    df = load_data_no_cache()

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
    else:
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

        # === FILTRI E EXPORT AVANZATO ===
        st.subheader("🔍 Filtra e Esporta Dati")

        with st.expander("⚙️ Configura Filtri", expanded=True):
            filter_cols = st.columns(4)
            
            # Initialize filtered dataframe
            df_filtered = df.copy()
            active_filters = []
            
            with filter_cols[0]:
                # Regione filter
                if 'regione' in df.columns:
                    regions = ['Tutte'] + sorted(df['regione'].dropna().unique().tolist())
                    selected_region = st.selectbox("Regione", regions, key="filter_region")
                    if selected_region != 'Tutte':
                        df_filtered = df_filtered[df_filtered['regione'] == selected_region]
                        active_filters.append(f"Regione: {selected_region}")
            
            with filter_cols[1]:
                # Tipo scuola filter
                if 'tipo_scuola' in df.columns:
                    types = ['Tutti'] + sorted(df['tipo_scuola'].dropna().unique().tolist())
                    selected_type = st.selectbox("Tipo Scuola", types, key="filter_type")
                    if selected_type != 'Tutti':
                        df_filtered = df_filtered[df_filtered['tipo_scuola'] == selected_type]
                        active_filters.append(f"Tipo: {selected_type}")
            
            with filter_cols[2]:
                # Statale/Paritaria filter
                if 'statale_paritaria' in df.columns:
                    stato = ['Tutti'] + sorted(df['statale_paritaria'].dropna().unique().tolist())
                    selected_stato = st.selectbox("Stato", stato, key="filter_stato")
                    if selected_stato != 'Tutti':
                        df_filtered = df_filtered[df_filtered['statale_paritaria'] == selected_stato]
                        active_filters.append(f"Stato: {selected_stato}")
            
            with filter_cols[3]:
                # Indice RO range filter
                if 'ptof_orientamento_maturity_index' in df.columns:
                    # Convert to pct for display/filtering logic if needed, but here we filter on raw values
                    # If we want to filter by %, we should convert limits.
                    # Let's keep filter on raw values but maybe label it better or convert?
                    # The filter is on the raw column. Let's just update label to "Indice Compl"
                    # But wait, raw values are 1-7. If user sees "Indice Compl" they expect %.
                    # It's better to show % range slider and convert to 1-7 for filtering.
                    min_val = float(df['ptof_orientamento_maturity_index'].min())
                    max_val = float(df['ptof_orientamento_maturity_index'].max())
                    
                    # Convert min/max to pct for slider
                    from data_utils import scale_to_pct
                    min_pct = int(scale_to_pct(min_val))
                    max_pct = int(scale_to_pct(max_val))

                    ro_range_pct = st.slider("Indice Completezza (%)", 0, 100, (min_pct, max_pct), 5, key="filter_ro")
                    
                    # Convert back to 1-7
                    min_ro = 1 + (ro_range_pct[0] * 6 / 100)
                    max_ro = 1 + (ro_range_pct[1] * 6 / 100)

                    if ro_range_pct != (min_pct, max_pct):
                        df_filtered = df_filtered[
                            (df_filtered['ptof_orientamento_maturity_index'] >= min_ro) &
                            (df_filtered['ptof_orientamento_maturity_index'] <= max_ro)
                        ]
                        active_filters.append(f"Indice: {ro_range_pct[0]}%-{ro_range_pct[1]}%")

        # Show filter results
        if active_filters:
            st.info(f"🔍 **Filtri attivi:** {' | '.join(active_filters)} → **{len(df_filtered)} scuole**")
        else:
            st.caption(f"Nessun filtro attivo. Totale: {len(df_filtered)} scuole")

        # Preview filtered data
        if selected_cols and len(df_filtered) > 0:
            st.markdown("**Anteprima dati filtrati:**")
            st.dataframe(df_filtered[selected_cols].head(20), use_container_width=True, height=300)
            if len(df_filtered) > 20:
                st.caption(f"Mostrate prime 20 righe su {len(df_filtered)} totali")

        # Export buttons for filtered data
        st.markdown("**📥 Esporta dati filtrati:**")
        exp_cols = st.columns(3)

        with exp_cols[0]:
            if len(df_filtered) > 0:
                csv_filtered = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 CSV Filtrato",
                    data=csv_filtered,
                    file_name=f"dati_filtrati_{len(df_filtered)}_scuole.csv",
                    mime="text/csv",
                    help=f"Scarica {len(df_filtered)} scuole in formato CSV"
                )

        with exp_cols[1]:
            if len(df_filtered) > 0:
                try:
                    from io import BytesIO
                    excel_buffer = BytesIO()
                    df_filtered.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="📥 Excel Filtrato",
                        data=excel_buffer,
                        file_name=f"dati_filtrati_{len(df_filtered)}_scuole.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help=f"Scarica {len(df_filtered)} scuole in formato Excel"
                    )
                except ImportError:
                    st.warning("Installa openpyxl per export Excel")

        with exp_cols[2]:
            if len(df_filtered) > 0 and selected_cols:
                # Export only selected columns
                csv_selected = df_filtered[selected_cols].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Solo Colonne Selezionate",
                    data=csv_selected,
                    file_name=f"dati_selezionati_{len(df_filtered)}_scuole.csv",
                    mime="text/csv",
                    help=f"Scarica solo le {len(selected_cols)} colonne selezionate"
                )

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

        json_data = None
        if selected_label:
            # Estrai school_id dalla riga selezionata (già filtrata sopra)
            school_id = school_row['school_id']
            json_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.json')
            
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
            if selected_label and json_data:
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

with tab_edit:
    st.title("⚙️ Gestione Metadati Scuole")
    st.markdown("Visualizza e modifica i metadati delle scuole analizzate")

    st.markdown("---")

    df = load_data_cached()

    if df.empty:
        st.warning("Nessun dato disponibile")
    else:
        # Keep original DF for saving operations
        df_original = df.copy()

        # Main school selector with navigation
        school_options_all = df['denominazione'].dropna().unique().tolist()

        # Search and Filter
        col_search, col_filt = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("🔍 Cerca (codice, nome, comune)", placeholder="es: MIIS08900V o Milano", key="search_box")
        with col_filt:
            st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True)
            filter_missing = st.checkbox("⚠️ Solo dati mancanti", help="Mostra solo scuole con Tipo, Ordine o Area = ND", key="filter_missing_chk")

        # Apply filters
        filtered_df = df.copy()

        if filter_missing:
            # Check for ND or NaN in key columns
            mask_missing = (
                filtered_df['tipo_scuola'].isna() | filtered_df['tipo_scuola'].isin(['ND', 'nan', '']) |
                filtered_df['ordine_grado'].isna() | filtered_df['ordine_grado'].isin(['ND', 'nan', '']) |
                filtered_df['area_geografica'].isna() | filtered_df['area_geografica'].isin(['ND', 'nan', ''])
            )
            filtered_df = filtered_df[mask_missing]

        if search_query:
            search_upper = search_query.upper()
            filtered_df = filtered_df[
                filtered_df['school_id'].str.upper().str.contains(search_upper, na=False) |
                filtered_df['denominazione'].str.upper().str.contains(search_upper, na=False) |
                filtered_df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
            ]

        # Create unique display label
        filtered_df['display_label'] = filtered_df['denominazione'].astype(str) + " [" + filtered_df['school_id'].astype(str) + "]"

        # Update options to use unique labels
        school_options = filtered_df['display_label'].sort_values().unique().tolist()

        if filter_missing or search_query:
            st.caption(f"Trovate: {len(school_options)} scuole")

        if not school_options:
            st.warning("Nessuna scuola trovata con questo filtro")
        else:
            # Initialize session state (ensure idx is valid)
            if 'school_idx' not in st.session_state:
                st.session_state.school_idx = 0
            if st.session_state.school_idx >= len(school_options):
                st.session_state.school_idx = 0

            # Callback functions
            def go_prev():
                if st.session_state.school_idx > 0:
                    st.session_state.school_idx -= 1

            def go_next():
                if st.session_state.school_idx < len(school_options) - 1:
                    st.session_state.school_idx += 1

            # Navigation row
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 3, 1, 1])

            with nav_col1:
                st.button("⬅️ Precedente", on_click=go_prev, use_container_width=True)

            with nav_col3:
                st.button("➡️ Successiva", on_click=go_next, use_container_width=True)

            with nav_col4:
                st.markdown(f"**{st.session_state.school_idx + 1}/{len(school_options)}**")

            with nav_col2:
                # Get current school label
                current_label = school_options[st.session_state.school_idx]
                st.info(f"🏫 **{current_label}**")

            # Set selected item
            selected_label = school_options[st.session_state.school_idx]

            # Get school data by unique label
            school_row = filtered_df[filtered_df['display_label'] == selected_label].iloc[0]
            selected_school = school_row.get('denominazione', '')  # Backwards compat variable
            school_id = school_row.get('school_id', '')

            st.markdown("---")

            # Two main columns: Actions left, PDF right
            actions_col, pdf_col = st.columns([1, 1])

            with pdf_col:
                st.subheader("📄 PDF PTOF")
                pdf_path, pdf_bytes = display_pdf(school_id, height=800)

            with actions_col:
                # School info
                st.subheader(f"📋 {selected_school}")
                st.write(f"**Codice:** {school_id}")
                st.write(f"**Tipo:** {school_row.get('tipo_scuola', 'N/D')} | **Area:** {school_row.get('area_geografica', 'N/D')}")
                
                # Nuovi metadati: Regione, Provincia, Stato
                regione = school_row.get('regione', 'N/D')
                provincia = school_row.get('provincia', 'N/D')
                statale = school_row.get('statale_paritaria', 'N/D')
                st.write(f"**Regione:** {regione if regione and regione != 'ND' else 'N/D'} | **Provincia:** {provincia if provincia and provincia != 'ND' else 'N/D'} | **Stato:** {statale if statale and statale != 'ND' else 'N/D'}")
                
                from data_utils import format_pct
                val_ro = school_row.get('ptof_orientamento_maturity_index', 'N/D')
                st.write(f"**Indice:** {format_pct(val_ro)}" if pd.notna(val_ro) and val_ro != 'N/D' else "**Indice:** N/D")
                
                st.markdown("---")
                st.markdown("### 📁 Gestione PTOF")
                if pdf_path and pdf_bytes:
                    st.download_button(
                        "⬇️ Scarica PTOF",
                        data=pdf_bytes,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.caption(f"L'eliminazione sposta il file in `{PTOF_DISCARDED_DIR}`.")
                    confirm_key = f"confirm_delete_ptof_{school_id}"
                    delete_key = f"delete_ptof_{school_id}"
                    confirm_delete = st.checkbox("Confermo di voler eliminare il PTOF", key=confirm_key)
                    if st.button("🗑️ Elimina PTOF", key=delete_key, disabled=not confirm_delete, use_container_width=True):
                        new_path = discard_pdf(pdf_path)
                        if new_path:
                            st.success(f"PTOF spostato in `{new_path}`")
                            st.rerun()
                else:
                    st.info("Nessun PTOF disponibile per questa scuola.")

                # Contatti (se disponibili)
                email = school_row.get('email', '')
                pec = school_row.get('pec', '')
                website = school_row.get('website', '')
                indirizzo = school_row.get('indirizzo', '')
                cap = school_row.get('cap', '')
                comune = school_row.get('comune', '')
                
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
                
                # Metadata edit section
                st.markdown("---")
                
                # Show persistent success message if present
                if 'last_save_msg' in st.session_state:
                    st.success(st.session_state.last_save_msg)
                    # Clear it so it doesn't show up on next unrelated action, but it stays for this render
                    del st.session_state.last_save_msg
                    
                st.markdown("### ✏️ Modifica Metadati")
                
                # Form layout: text inputs on left, checkboxes on right
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.markdown("**Informazioni Generali**")
                    new_school_id = st.text_input("Codice Meccanografico", value=str(school_id), key=f"edit_id_{school_id}")
                    new_denominazione = st.text_input("Denominazione", value=str(school_row.get('denominazione', '')), key=f"edit_denom_{school_id}")
                    new_comune = st.text_input("Comune", value=str(school_row.get('comune', '') if pd.notna(school_row.get('comune')) else ''), key=f"edit_comune_{school_id}")
                    
                    area_options = ['', 'Nord Ovest', 'Nord Est', 'Centro', 'Sud', 'Isole']
                    current_area = str(school_row.get('area_geografica', ''))
                    new_area = st.selectbox(
                        "Area Geografica",
                        area_options,
                        index=area_options.index(current_area) if current_area in area_options else 0,
                        key=f"edit_area_{school_id}"
                    )
                    
                    new_territorio = st.selectbox("Territorio", ['', 'Metropolitano', 'Non Metropolitano'],
                        index=['', 'Metropolitano', 'Non Metropolitano'].index(str(school_row.get('territorio', '')))\
                        if str(school_row.get('territorio', '')) in ['Metropolitano', 'Non Metropolitano'] else 0, key=f"edit_terr_{school_id}")
                
                with col_right:
                    st.markdown("**Tipo Scuola**")
                    # Split by comma and strip whitespace to handle "Liceo, Tecnico" or "Liceo,Tecnico"
                    current_types = [t.strip() for t in str(school_row.get('tipo_scuola', '')).split(',') if t.strip()] if pd.notna(school_row.get('tipo_scuola')) else []
                    
                    tipo_infanzia = st.checkbox("Infanzia", value='Infanzia' in current_types, key=f"tipo_infanzia_{school_id}")
                    tipo_primaria = st.checkbox("Primaria", value='Primaria' in current_types, key=f"tipo_primaria_{school_id}")
                    tipo_igrado = st.checkbox("Medie (Sec. I Grado)", value='I Grado' in current_types or 'Medie' in current_types, key=f"tipo_igrado_{school_id}")
                    tipo_liceo = st.checkbox("Liceo", value='Liceo' in current_types, key=f"tipo_liceo_{school_id}")
                    tipo_tecnico = st.checkbox("Tecnico", value='Tecnico' in current_types, key=f"tipo_tecnico_{school_id}")
                    tipo_prof = st.checkbox("Professionale", value='Professionale' in current_types, key=f"tipo_prof_{school_id}")
                    st.caption("ℹ️ Per Ist. Comprensivi: seleziona Infanzia + Primaria + Medie")
                    
                    st.markdown("")  # Spacer
                    st.markdown("**Ordine Grado**")
                    current_ordini = [t.strip() for t in str(school_row.get('ordine_grado', '')).split(',') if t.strip()] if pd.notna(school_row.get('ordine_grado')) else []
                    
                    ordine_infanzia = st.checkbox("Infanzia", value='Infanzia' in current_ordini, key=f"ordine_infanzia_{school_id}")
                    ordine_primaria = st.checkbox("Primaria", value='Primaria' in current_ordini, key=f"ordine_primaria_{school_id}")
                    ordine_igrado = st.checkbox("I Grado", value='I Grado' in current_ordini, key=f"ordine_igrado_{school_id}")
                    ordine_iigrado = st.checkbox("II Grado", value='II Grado' in current_ordini, key=f"ordine_iigrado_{school_id}")
                    ordine_comprensivo = st.checkbox("Comprensivo", value='Comprensivo' in current_ordini, key=f"ordine_comprensivo_{school_id}")
                
                # Build tipo_scuola from checkboxes
                selected_types = []
                if tipo_infanzia:
                    selected_types.append('Infanzia')
                if tipo_primaria:
                    selected_types.append('Primaria')
                if tipo_igrado:
                    selected_types.append('I Grado')
                if tipo_liceo:
                    selected_types.append('Liceo')
                if tipo_tecnico:
                    selected_types.append('Tecnico')
                if tipo_prof:
                    selected_types.append('Professionale')
                new_tipo = ', '.join(selected_types) if selected_types else ''
                
                # Build ordine_grado from checkboxes
                selected_ordini = []
                if ordine_infanzia:
                    selected_ordini.append('Infanzia')
                if ordine_primaria:
                    selected_ordini.append('Primaria')
                if ordine_igrado:
                    selected_ordini.append('I Grado')
                if ordine_iigrado:
                    selected_ordini.append('II Grado')
                if ordine_comprensivo:
                    selected_ordini.append('Comprensivo')
                new_ordine = ', '.join(selected_ordini) if selected_ordini else ''

                if st.button("💾 Salva Modifiche", key="save_edit", type="primary"):
                    # RELOAD original data to be safe against concurrency/stale state
                    df_full = load_data_cached()
                    try:
                        # Find index in FULL dataframe
                        # Ensure we find the row even if denominazione changed (using school_id if stable, but here user might edit both)
                        # We trust 'selected_school' (original name when selected) to find the row.
                        idx_list = df_full[df_full['denominazione'] == selected_school].index
                        
                        if idx_list.empty:
                            # Fallback: try by ID
                            idx_list = df_full[df_full['school_id'] == school_id].index
                        
                        if not idx_list.empty:
                            idx = idx_list[0]
                            df_full.at[idx, 'school_id'] = new_school_id
                            df_full.at[idx, 'denominazione'] = new_denominazione
                            if new_tipo:
                                df_full.at[idx, 'tipo_scuola'] = new_tipo
                            if new_area:
                                df_full.at[idx, 'area_geografica'] = new_area
                            if new_ordine:
                                df_full.at[idx, 'ordine_grado'] = new_ordine
                            if new_territorio:
                                df_full.at[idx, 'territorio'] = new_territorio
                            if new_comune:
                                df_full.at[idx, 'comune'] = new_comune
                            
                            df_full.to_csv(SUMMARY_FILE, index=False)
                            csv_status = "✅ CSV aggiornato correttamente"
                        else:
                            csv_status = "❌ Errore: Scuola non trovata nel DB originale"
                    except Exception as e:
                        csv_status = f"❌ Errore salvataggio CSV: {e}"

                    # Update JSON too
                    json_status = "ℹ️ Nessun file JSON trovato"
                    json_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.json')
                    if json_files:
                        try:
                            with open(json_files[0], 'r') as f:
                                jd = json.load(f)
                            if 'metadata' not in jd:
                                jd['metadata'] = {}
                            jd['metadata']['school_id'] = new_school_id
                            jd['metadata']['denominazione'] = new_denominazione
                            if new_tipo:
                                jd['metadata']['tipo_scuola'] = new_tipo
                            if new_area:
                                jd['metadata']['area_geografica'] = new_area
                            if new_ordine:
                                jd['metadata']['ordine_grado'] = new_ordine
                            if new_territorio:
                                jd['metadata']['territorio'] = new_territorio
                            if new_comune:
                                jd['metadata']['comune'] = new_comune
                            with open(json_files[0], 'w') as f:
                                json.dump(jd, f, indent=2, ensure_ascii=False)
                            json_status = f"✅ JSON aggiornato ({os.path.basename(json_files[0])})"
                        except Exception as e:
                            json_status = f"⚠️ Errore aggiornamento JSON: {e}"
                    
                    # Rename files if School ID changed
                    rename_status = ""
                    if new_school_id != school_id:
                        renamed_count = 0
                        # PDF
                        for base_dir in PTOF_SEARCH_DIRS:
                            for f in glob.glob(os.path.join(base_dir, "**", f"*{school_id}*.pdf"), recursive=True):
                                try:
                                    new_name = os.path.basename(f).replace(school_id, new_school_id)
                                    os.rename(f, os.path.join(os.path.dirname(f), new_name))
                                    renamed_count += 1
                                except Exception:
                                    pass
                        
                        # MD
                        for f in glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md'):
                            try:
                                new_name = os.path.basename(f).replace(school_id, new_school_id)
                                os.rename(f, os.path.join(PTOF_MD_DIR, new_name))
                                renamed_count += 1
                            except Exception:
                                pass
                        
                        # JSON
                        for f in glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.json'):
                            try:
                                new_name = os.path.basename(f).replace(school_id, new_school_id)
                                os.rename(f, os.path.join(ANALYSIS_DIR, new_name))
                                renamed_count += 1
                            except Exception:
                                pass
                        
                        if renamed_count > 0:
                            rename_status = f"\n3. 🔄 File rinominati ({renamed_count}) con nuovo codice"
                    
                    # Save consolidated message to session state for persistence after rerun
                    st.session_state.last_save_msg = f"**Salvataggio completato!**\n\n1. {csv_status}\n2. {json_status}{rename_status}"
                    
                    load_data_cached.clear()
                    st.rerun()

            st.markdown("---")

            # Quick Stats
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("📊 Totale Scuole", len(df_original))
                st.metric("📄 File JSON", len(glob.glob(f'{ANALYSIS_DIR}/*_analysis.json')))
            with col_stat2:
                st.metric("🔍 Visualizzate (filtri)", len(filtered_df))
                st.metric("📝 File MD", len(glob.glob(f'{PTOF_MD_DIR}/*.md')))

            st.markdown("---")

            # === GESTIONE DUPLICATI E RECORD ANOMALI ===
            st.subheader("🔧 Gestione Duplicati e Record Anomali")

            # Reload fresh data for this section
            df_mgmt = load_data_cached()

            # Find duplicates by school_id
            duplicates = df_mgmt[df_mgmt.duplicated(subset=['school_id'], keep=False)].sort_values('school_id')
            # Find anomalies (school_id contains BIS, DA_VERIFICARE, or doesn't match pattern)
            anomalies = df_mgmt[
                df_mgmt['school_id'].str.contains('BIS|DA_VERIFICARE|PTOF', case=False, na=False) |
                (df_mgmt['school_id'].str.len() < 5) |
                df_mgmt['ptof_orientamento_maturity_index'].isna()
            ]

            col_dup, col_anom = st.columns(2)

            with col_dup:
                st.markdown("**🔄 Scuole Duplicate** (stesso codice)")
                if len(duplicates) > 0:
                    st.warning(f"Trovate {len(duplicates)} righe duplicate")
                    dup_ids = duplicates['school_id'].unique().tolist()
                    selected_dup = st.selectbox("Seleziona codice duplicato", dup_ids, key="dup_select")

                    if selected_dup:
                        dup_rows = df_mgmt[df_mgmt['school_id'] == selected_dup]
                        st.dataframe(dup_rows[['school_id', 'denominazione', 'comune', 'ptof_orientamento_maturity_index']], hide_index=False)

                        # Option to keep one and delete others
                        keep_idx = st.selectbox("Mantieni riga (index)", dup_rows.index.tolist(), key="keep_idx")

                        if st.button("🗑️ Elimina le altre righe duplicate", key="delete_dups"):
                            df_clean = df_mgmt.drop(index=[i for i in dup_rows.index if i != keep_idx])
                            df_clean.to_csv(SUMMARY_FILE, index=False)
                            st.success(f"Eliminate {len(dup_rows) - 1} righe duplicate. Mantenuta riga {keep_idx}.")
                            load_data_cached.clear()
                            st.rerun()
                else:
                    st.success("✅ Nessun duplicato trovato")

            with col_anom:
                st.markdown("**⚠️ Record Anomali** (da verificare)")
                if len(anomalies) > 0:
                    st.warning(f"Trovati {len(anomalies)} record anomali")
                    anom_display = anomalies[['school_id', 'denominazione', 'ptof_orientamento_maturity_index']].copy()
                    st.dataframe(anom_display, hide_index=False)

                    selected_anom_idx = st.selectbox("Seleziona record da gestire (index)", anomalies.index.tolist(), key="anom_select")

                    if selected_anom_idx is not None:
                        anom_row = df_mgmt.loc[selected_anom_idx]
                        st.write(f"**Selezionato:** {anom_row['denominazione']} ({anom_row['school_id']})")

                        col_act1, col_act2 = st.columns(2)
                        with col_act1:
                            if st.button("🗑️ Elimina questo record", key="delete_anom"):
                                df_clean = df_mgmt.drop(index=selected_anom_idx)
                                df_clean.to_csv(SUMMARY_FILE, index=False)
                                # Also try to delete associated files
                                for pattern in [f'{ANALYSIS_DIR}/*{anom_row["school_id"]}*', f'{PTOF_MD_DIR}/*{anom_row["school_id"]}*']:
                                    for f in glob.glob(pattern):
                                        try:
                                            os.remove(f)
                                        except Exception:
                                            pass
                                st.success(f"Record eliminato: {anom_row['school_id']}")
                                load_data_cached.clear()
                                st.rerun()

                        with col_act2:
                            # Option to merge with another school
                            other_schools = df_mgmt[df_mgmt.index != selected_anom_idx]['school_id'].tolist()
                            merge_target = st.selectbox("Unisci con:", ["-- Seleziona --"] + other_schools, key="merge_target")

                            if merge_target != "-- Seleziona --" and st.button("🔗 Unisci record", key="merge_anom"):
                                # Keep the target, delete the anomaly
                                df_clean = df_mgmt.drop(index=selected_anom_idx)
                                df_clean.to_csv(SUMMARY_FILE, index=False)
                                st.success(f"Record {anom_row['school_id']} eliminato. Dati mantenuti in {merge_target}.")
                                load_data_cached.clear()
                                st.rerun()
                else:
                    st.success("✅ Nessun record anomalo")

            st.markdown("---")
            st.caption("🧭 ORIENTA+ | Gestione Dati")

with tab_backup:
    st.title("🛡️ Centro Backup e Ripristino")
    st.markdown("""
    Qui puoi gestire i backup dei dati e delle analisi.
    Puoi creare copie di sicurezza, ripristinare versioni precedenti o scaricare i dati per archivio.
    """)

    # --- Create & Upload Section ---
    col_create, col_upload = st.columns([1, 1])

    with col_create:
        st.subheader("💾 Nuovo Backup")
        st.markdown("Crea una copia istantanea dello stato attuale (CSV + JSON Analysis).")
        if st.button("Crea Backup Ora", type="primary"):
            try:
                path, count = create_backup(description="manual_user")
                st.success(f"✅ Backup creato con successo! ({count} files)")
                st.code(os.path.basename(path))
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la creazione del backup: {e}")

    with col_upload:
        st.subheader("📥 Importa Backup (ZIP)")
        uploaded_file = st.file_uploader("Carica un file ZIP di backup", type="zip")
        if uploaded_file:
            if st.button("Importa Backup"):
                try:
                    backup_name = restore_from_zip(uploaded_file)
                    st.success(f"✅ Backup importato: {backup_name}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore importazione: {e}")

    st.markdown("---")

    # --- Existing Backups List ---
    st.subheader("🗄️ Storico Backup")

    backups = list_backups()

    if not backups:
        st.info("Nessun backup trovato.")
    else:
        for backup_name in backups:
            with st.expander(f"📦 {backup_name}", expanded=False):
                c1, c2, c3 = st.columns([2, 2, 1])
                
                with c1:
                    st.markdown(f"**Cartella:** `{backup_name}`")
                    
                with c2:
                    # Restore
                    if st.button("🔄 Ripristina questo stato", key=f"rest_{backup_name}"):
                        with st.spinner("Ripristino in corso..."):
                            res = restore_backup(backup_name)
                        if res['success']:
                            st.success(f"✅ Ripristino completato! ({res['files_restored']} files)")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Errore ripristino: {res['error']}")
                
                with c3:
                    # Download
                    if st.button("⬇️ ZIP", key=f"zip_{backup_name}"):
                        zip_path = create_backup_zip(backup_name)
                        if zip_path:
                            with open(zip_path, "rb") as f:
                                st.download_button(
                                    label="Scarica Ora",
                                    data=f,
                                    file_name=os.path.basename(zip_path),
                                    mime="application/zip",
                                    key=f"down_{backup_name}"
                                )
                            # Clean up zip after reading?
                            # Streamlit reruns usually handle cleanup or we leave it.
                            # For now we leave the zip file.
                        else:
                            st.error("Errore creazione ZIP")
                    
                    # Delete
                    if st.button("🗑️ Elimina", key=f"del_{backup_name}"):
                        if delete_backup(backup_name):
                            st.success("Cancellato.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Errore cancellazione.")

    st.sidebar.info("ℹ️ Il ripristino sovrascrive i dati attuali. Assicurati di fare prima un backup se necessario.")

render_footer()
