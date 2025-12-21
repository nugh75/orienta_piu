# ⚙️ Gestione - Amministrazione dati e analisi

import streamlit as st
import pandas as pd
import os
import json
import glob
import subprocess

st.set_page_config(page_title="Gestione", page_icon="⚙️", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'
PTOF_DIR = 'ptof'
PTOF_MD_DIR = 'ptof_md'

@st.cache_data(ttl=30)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

def display_pdf(school_id, height=600):
    """Display PDF for a given school_id"""
    import base64
    
    pdf_patterns = [f'{PTOF_DIR}/*{school_id}*.pdf', f'{PTOF_DIR}/{school_id}*.pdf']
    pdf_files = []
    for pattern in pdf_patterns:
        pdf_files.extend(glob.glob(pattern))
    
    if not pdf_files:
        all_pdfs = glob.glob(f'{PTOF_DIR}/*.pdf')
        for pdf in all_pdfs:
            if school_id.upper() in os.path.basename(pdf).upper():
                pdf_files.append(pdf)
                break
    
    if pdf_files:
        pdf_path = pdf_files[0]
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f"**📄 PDF:** `{os.path.basename(pdf_path)}`")
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf"></iframe>', unsafe_allow_html=True)
            return True
        except Exception as e:
            st.warning(f"Impossibile visualizzare PDF: {e}")
            return False
    else:
        st.info(f"PDF non trovato per {school_id}")
        return False

df = load_data()

st.title("⚙️ Gestione Scuole")
st.markdown("Seleziona una scuola per visualizzare, modificare, eliminare o ri-analizzare")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()
    
# Global Sidebar Filters
try:
    from app.data_utils import apply_sidebar_filters
    # Keep original DF for saving operations
    df_original = df.copy()
    # Apply filters to view DF
    df = apply_sidebar_filters(df, extra_clear_keys=['search_box', 'filter_missing_chk'])
except ImportError:
    pass

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

# Update options

# Create unique display label
filtered_df['display_label'] = filtered_df['denominazione'].astype(str) + " [" + filtered_df['school_id'].astype(str) + "]"

# Update options to use unique labels
school_options = filtered_df['display_label'].sort_values().unique().tolist()

if filter_missing or search_query:
    st.caption(f"Trovate: {len(school_options)} scuole")
else:
    # If no filters, use full list 
    pass

if not school_options:
    st.warning("Nessuna scuola trovata con questo filtro")
    st.stop()

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
selected_school = school_row.get('denominazione', '') # Backwards compat variable
school_id = school_row.get('school_id', '')

st.markdown("---")

# Two main columns: Actions left, PDF right
actions_col, pdf_col = st.columns([1, 1])

with pdf_col:
    st.subheader("📄 PDF PTOF")
    display_pdf(school_id, height=800)

with actions_col:
    # School info
    st.subheader(f"📋 {selected_school}")
    st.write(f"**Codice:** {school_id}")
    st.write(f"**Tipo:** {school_row.get('tipo_scuola', 'N/D')} | **Area:** {school_row.get('area_geografica', 'N/D')}")
    st.write(f"**Indice:** {school_row.get('ptof_orientamento_maturity_index', 'N/D'):.2f}/7" if pd.notna(school_row.get('ptof_orientamento_maturity_index')) else "**Indice:** N/D")
    
    # Tabs for different actions
    tab_edit, tab_upload, tab_delete = st.tabs(["✏️ Modifica", "📤 Carica PDF", "🗑️ Elimina"])
    
    # TAB 1: Edit metadata
    with tab_edit:
        # Show persistent success message if present
        if 'last_save_msg' in st.session_state:
            st.success(st.session_state.last_save_msg)
            # Clear it so it doesn't show up on next unrelated action, but it stays for this render
            del st.session_state.last_save_msg
            
        st.markdown("#### Modifica Caratteristiche Scuola")
        
        col_cloud, _ = st.columns([1, 2])
        with col_cloud:
            if st.button("✨ Estrai dati da PTOF (Cloud)", help="Usa l'AI per leggere Nome, Città e Tipo dal documento caricato"):
                try:
                    from src.processing.cloud_review import extract_metadata_from_header, load_api_config
                    
                    # 1. Find MD Document
                    md_files = glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md')
                    if not md_files:
                        st.error("⚠️ Nessun file Markdown trovato. Carica prima il PDF.")
                    else:
                        with st.spinner("⏳ Analisi intestazione documento in corso..."):
                            # 2. Config & Key
                            api_cfg = load_api_config()
                            prov = 'gemini' if api_cfg.get('gemini_api_key') else 'openrouter'
                            key = api_cfg.get(f'{prov}_api_key')
                            
                            if not key:
                                st.error("❌ Configura le API Key in basso (Sezione Cloud).")
                            else:
                                with open(md_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                
                                # 3. Extract
                                meta = extract_metadata_from_header(content, prov, key, "gemini-2.0-flash-exp" if prov=='gemini' else "google/gemini-2.0-flash-exp:free")
                                
                                if meta:
                                    # 4. Update Session State
                                    if meta.get('denominazione'):
                                        st.session_state[f"edit_denom_{school_id}"] = meta['denominazione']
                                    if meta.get('comune'):
                                        st.session_state[f"edit_comune_{school_id}"] = meta['comune']
                                    if meta.get('school_id'):
                                        st.session_state[f"edit_id_{school_id}"] = meta['school_id']
                                        
                                    # Handle Checkboxes from Type text
                                    found_type = str(meta.get('tipo_scuola', ''))
                                    st.session_state[f"tipo_liceo_{school_id}"] = 'Liceo' in found_type
                                    st.session_state[f"tipo_tecnico_{school_id}"] = 'Tecnico' in found_type
                                    st.session_state[f"tipo_prof_{school_id}"] = 'Professionale' in found_type
                                    st.session_state[f"tipo_igrado_{school_id}"] = 'I Grado' in found_type or 'Medie' in found_type
                                    st.session_state[f"tipo_primaria_{school_id}"] = 'Primaria' in found_type
                                    st.session_state[f"tipo_infanzia_{school_id}"] = 'Infanzia' in found_type

                                    # Handle Selectboxes
                                    if meta.get('area_geografica') in ['Nord', 'Centro', 'Sud']:
                                        st.session_state[f"edit_area_{school_id}"] = meta['area_geografica']
                                    if meta.get('ordine_grado') in ['Infanzia', 'Primaria', 'I Grado', 'II Grado', 'Comprensivo']:
                                        st.session_state[f"edit_ordine_{school_id}"] = meta['ordine_grado']

                                    st.success(f"✅ Dati estratti: {meta.get('denominazione')}")
                                    st.rerun()
                                else:
                                    st.warning("⚠️ L'AI non ha trovato dati certi.")
                except ImportError:
                    st.error("Modulo cloud non trovato.")
                except Exception as e:
                    st.error(f"Errore: {e}")
        
        st.write("") # Spacer
        
        col1, col2 = st.columns(2)
        with col1:
            new_school_id = st.text_input("Codice Meccanografico", value=str(school_id), key=f"edit_id_{school_id}")
            new_denominazione = st.text_input("Denominazione", value=str(school_row.get('denominazione', '')), key=f"edit_denom_{school_id}")
            new_comune = st.text_input("Comune", value=str(school_row.get('comune', '') if pd.notna(school_row.get('comune')) else ''), key=f"edit_comune_{school_id}")
        
        with col2:
            # Multi-tipo checkboxes
            st.markdown("**Tipo Scuola:**")
            current_types = str(school_row.get('tipo_scuola', '')).split(', ') if pd.notna(school_row.get('tipo_scuola')) else []
            tipo_liceo = st.checkbox("Liceo", value='Liceo' in current_types, key=f"tipo_liceo_{school_id}")
            tipo_tecnico = st.checkbox("Tecnico", value='Tecnico' in current_types, key=f"tipo_tecnico_{school_id}")
            tipo_prof = st.checkbox("Professionale", value='Professionale' in current_types, key=f"tipo_prof_{school_id}")
            tipo_igrado = st.checkbox("Medie (Sec. I Grado)", value='I Grado' in current_types or 'Medie' in current_types, key=f"tipo_igrado_{school_id}")
            tipo_primaria = st.checkbox("Primaria", value='Primaria' in current_types, key=f"tipo_primaria_{school_id}")
            tipo_infanzia = st.checkbox("Infanzia", value='Infanzia' in current_types, key=f"tipo_infanzia_{school_id}")
            st.caption("ℹ️ Per Ist. Comprensivi: seleziona Infanzia + Primaria + Medie")
            
            new_ordine = st.selectbox("Ordine Grado", ['', 'Infanzia', 'Primaria', 'I Grado', 'II Grado', 'Comprensivo'],
                index=['', 'Infanzia', 'Primaria', 'I Grado', 'II Grado', 'Comprensivo'].index(str(school_row.get('ordine_grado', '')))
                if str(school_row.get('ordine_grado', '')) in ['Infanzia', 'Primaria', 'I Grado', 'II Grado', 'Comprensivo'] else 0, key=f"edit_ordine_{school_id}")
            new_area = st.selectbox("Area Geografica", ['', 'Nord', 'Centro', 'Sud'],
                index=['', 'Nord', 'Centro', 'Sud'].index(str(school_row.get('area_geografica', '')))\
                if str(school_row.get('area_geografica', '')) in ['Nord', 'Centro', 'Sud'] else 0, key=f"edit_area_{school_id}")
            new_territorio = st.selectbox("Territorio", ['', 'Metropolitano', 'Non Metropolitano'],
                index=['', 'Metropolitano', 'Non Metropolitano'].index(str(school_row.get('territorio', '')))\
                if str(school_row.get('territorio', '')) in ['Metropolitano', 'Non Metropolitano'] else 0, key=f"edit_terr_{school_id}")
        
        # Build tipo_scuola from checkboxes
        selected_types = []
        if tipo_infanzia: selected_types.append('Infanzia')
        if tipo_primaria: selected_types.append('Primaria')
        if tipo_igrado: selected_types.append('I Grado')
        if tipo_liceo: selected_types.append('Liceo')
        if tipo_tecnico: selected_types.append('Tecnico')
        if tipo_prof: selected_types.append('Professionale')
        new_tipo = ', '.join(selected_types) if selected_types else ''
        
        if st.button("💾 Salva Modifiche", key="save_edit"):
             # RELOAD original data to be safe against concurrency/stale state
            df_full = load_data()
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
                    if new_tipo: df_full.at[idx, 'tipo_scuola'] = new_tipo
                    if new_area: df_full.at[idx, 'area_geografica'] = new_area
                    if new_ordine: df_full.at[idx, 'ordine_grado'] = new_ordine
                    if new_territorio: df_full.at[idx, 'territorio'] = new_territorio
                    if new_comune: df_full.at[idx, 'comune'] = new_comune
                    
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
                    if 'metadata' not in jd: jd['metadata'] = {}
                    jd['metadata']['school_id'] = new_school_id
                    jd['metadata']['denominazione'] = new_denominazione
                    if new_tipo: jd['metadata']['tipo_scuola'] = new_tipo
                    if new_area: jd['metadata']['area_geografica'] = new_area
                    if new_ordine: jd['metadata']['ordine_grado'] = new_ordine
                    if new_territorio: jd['metadata']['territorio'] = new_territorio
                    if new_comune: jd['metadata']['comune'] = new_comune
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
                for f in glob.glob(f'{PTOF_DIR}/*{school_id}*.pdf'):
                    try:
                        new_name = os.path.basename(f).replace(school_id, new_school_id)
                        os.rename(f, os.path.join(PTOF_DIR, new_name))
                        renamed_count += 1
                    except Exception: pass
                
                # MD
                for f in glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md'):
                    try:
                        new_name = os.path.basename(f).replace(school_id, new_school_id)
                        os.rename(f, os.path.join(PTOF_MD_DIR, new_name))
                        renamed_count += 1
                    except Exception: pass
                
                # JSON
                for f in glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.json'):
                    try:
                        new_name = os.path.basename(f).replace(school_id, new_school_id)
                        os.rename(f, os.path.join(ANALYSIS_DIR, new_name))
                        renamed_count += 1
                    except Exception: pass
                
                if renamed_count > 0:
                    rename_status = f"\n3. 🔄 File rinominati ({renamed_count}) con nuovo codice"
            
            # Save consolidated message to session state for persistence after rerun
            st.session_state.last_save_msg = f"**Salvataggio completato!**\n\n1. {csv_status}\n2. {json_status}{rename_status}"
            
            load_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("#### 🔄 Riavvia Analisi LLM")
        
        md_files = glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md')
        if md_files:
            st.write(f"📄 MD: `{os.path.basename(md_files[0])}`")
            if st.button("🔄 Riavvia Analisi", key="rerun_btn"):
                # Delete existing
                for p in [f'{ANALYSIS_DIR}/*{school_id}*_analysis.json', f'{ANALYSIS_DIR}/*{school_id}*_analysis.md']:
                    for f in glob.glob(p):
                        try: os.remove(f)
                        except: pass
                
                md_file = md_files[0]
                script = f'''import sys; sys.path.insert(0, '.'); from app.agentic_pipeline import analyze_single_school; analyze_single_school("{md_file}")'''
                subprocess.Popen(f"cd /Users/danieledragoni/git/LIste && source .venv/bin/activate && python -c '{script}' >> logs/single_analysis.log 2>&1 &", shell=True)
                st.success("✅ Analisi avviata! Ricarica tra 2-3 min.")
        else:
            st.warning("⚠️ Nessun file MD. Carica un PDF.")
    
    # TAB 2: Upload PDF
    with tab_upload:
        st.markdown("#### Carica nuovo PDF PTOF")
        
        uploaded = st.file_uploader("Seleziona PDF", type=['pdf'], key=f"upload_{school_id}")
        
        if uploaded:
            st.success(f"📎 {uploaded.name}")
            
            if st.button("💾 Salva e Analizza", key="upload_btn"):
                new_path = f"{PTOF_DIR}/{school_id}_{uploaded.name}"
                with open(new_path, 'wb') as f:
                    f.write(uploaded.getvalue())
                st.write(f"✓ Salvato: {os.path.basename(new_path)}")
                
                # Delete old files
                for p in [f'{PTOF_DIR}/*{school_id}*.pdf', f'{ANALYSIS_DIR}/*{school_id}*', f'{PTOF_MD_DIR}/*{school_id}*.md']:
                    for f in glob.glob(p):
                        if f != new_path:
                            try: os.remove(f)
                            except: pass
                
                # Convert to MD
                st.write("📝 Conversione PDF → MD...")
                try:
                    subprocess.run(['marker_single', new_path, PTOF_MD_DIR, '--batch_multiplier', '2'],
                        capture_output=True, timeout=120, cwd='/Users/danieledragoni/git/LIste')
                    st.write("✓ Conversione OK")
                except: st.warning("Conversione con warning")
                
                # Find MD and start analysis
                new_md = glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md') or glob.glob(f'{PTOF_MD_DIR}/*{os.path.splitext(uploaded.name)[0]}*.md')
                if new_md:
                    md_file = new_md[0]
                    st.write(f"✓ MD: {os.path.basename(md_file)}")
                    st.write("🤖 Avvio analisi...")
                    script = f'''import sys; sys.path.insert(0, '.'); from app.agentic_pipeline import analyze_single_school; analyze_single_school("{md_file}")'''
                    subprocess.Popen(f"cd /Users/danieledragoni/git/LIste && source .venv/bin/activate && python -c '{script}' >> logs/single_analysis.log 2>&1 &", shell=True)
                    st.success("✅ Analisi avviata!")
                else:
                    st.error("❌ MD non generato")
    
    # TAB 3: Delete
    with tab_delete:
        st.markdown("#### Elimina questa scuola")
        
        with st.form(key=f"delete_form_{school_id}"):
            st.warning("⚠️ L'eliminazione è irreversibile!")
            
            del_pdf = st.checkbox("Elimina anche PDF")
            del_md = st.checkbox("Elimina anche MD source")
            
            if st.form_submit_button("🗑️ Elimina Scuola", type="primary"):
                # Delete analysis files
                files_deleted = []
                for f in glob.glob(f'{ANALYSIS_DIR}/*{school_id}*'):
                    try: 
                        os.remove(f)
                        files_deleted.append(os.path.basename(f))
                    except: pass
                
                if del_pdf:
                    for f in glob.glob(f'{PTOF_DIR}/*{school_id}*.pdf'):
                        try: 
                            os.remove(f)
                            files_deleted.append(os.path.basename(f))
                        except: pass
                
                if del_md:
                    for f in glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md'):
                        try: 
                            os.remove(f)
                            files_deleted.append(os.path.basename(f))
                        except: pass
                
                # Update CSV (Delete from FULL dataframe)
                df_full = load_data()
                df_new = df_full[df_full['denominazione'] != selected_school]
                df_new.to_csv(SUMMARY_FILE, index=False)
                
                st.success(f"✅ Elimina '{selected_school}' completata")
                if files_deleted:
                    st.caption(f"File rimossi: {', '.join(files_deleted)}")
                import time
                time.sleep(1) # Give time to read message
                load_data.clear()
                st.rerun()

st.markdown("---")

# Batch operations
with st.expander("📦 Operazioni Batch"):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Rigenera CSV"):
            try:
                r = subprocess.run(['python', 'src/processing/align_metadata.py'], capture_output=True, text=True, cwd='/Users/danieledragoni/git/LIste')
                st.success("✅ CSV rigenerato") if r.returncode == 0 else st.error(r.stderr[:200])
            except Exception as e:
                st.error(str(e))
    with col2:
        st.metric("JSON", len(glob.glob(f'{ANALYSIS_DIR}/*_analysis.json')))
        st.metric("MD", len(glob.glob(f'{PTOF_MD_DIR}/*.md')))

st.markdown("---")

# ============================================================================
# Cloud LLM Review & API Configuration
# ============================================================================
st.header("⚡ Revisione Cloud LLM")

try:
    import sys
    sys.path.insert(0, '.')
    from src.processing.cloud_review import (
        load_api_config, save_api_config, 
        fetch_gemini_models, fetch_openai_models, fetch_openrouter_models_free,
        review_ptof_with_cloud, validate_ptof_header
    )
    
    api_config = load_api_config()
    
    with st.expander("🔑 Configurazione API Keys", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            gemini_key = st.text_input("Gemini API Key", value=api_config.get('gemini_api_key', ''), type="password", key="gemini_key")
            openai_key = st.text_input("OpenAI API Key", value=api_config.get('openai_api_key', ''), type="password", key="openai_key")
        with col2:
            openrouter_key = st.text_input("OpenRouter API Key", value=api_config.get('openrouter_api_key', ''), type="password", key="openrouter_key")
            default_provider = st.selectbox("Provider Default", ['gemini', 'openai', 'openrouter'],
                index=['gemini', 'openai', 'openrouter'].index(api_config.get('default_provider', 'gemini')), key="default_prov")
        
        if st.button("💾 Salva Configurazione API"):
            new_config = {
                'gemini_api_key': gemini_key,
                'openai_api_key': openai_key,
                'openrouter_api_key': openrouter_key,
                'default_provider': default_provider,
                'default_model': api_config.get('default_model', '')
            }
            if save_api_config(new_config):
                st.success("✅ Configurazione salvata!")
            else:
                st.error("❌ Errore salvataggio")
    
    # Cloud review for current school
    if selected_school and school_id:
        st.markdown("#### 🔄 Revisione Cloud per la Scuola Corrente")
        
        rev_col1, rev_col2 = st.columns(2)
        
        with rev_col1:
            rev_provider = st.selectbox("Provider", ['gemini', 'openai', 'openrouter'], key="rev_provider")
        
        with rev_col2:
            # Fetch models dynamically
            models = []
            provider_key = ""
            if rev_provider == 'gemini':
                provider_key = api_config.get('gemini_api_key', '')
                if provider_key:
                    models = fetch_gemini_models(provider_key)
            elif rev_provider == 'openai':
                provider_key = api_config.get('openai_api_key', '')
                if provider_key:
                    models = fetch_openai_models(provider_key)
            elif rev_provider == 'openrouter':
                provider_key = api_config.get('openrouter_api_key', '')
                models = fetch_openrouter_models_free(provider_key)
            
            if models:
                rev_model = st.selectbox(f"Modello ({len(models)} disponibili)", models, key="rev_model")
            else:
                st.warning("⚠️ Nessun modello trovato. Verifica la API key.")
                rev_model = None
        
        if rev_model and provider_key:
            if st.button("🚀 Avvia Revisione Cloud", type="primary"):
                # Find MD file
                md_files = glob.glob(f'{PTOF_MD_DIR}/*{school_id}*.md')
                if md_files:
                    md_file = md_files[0]
                    with open(md_file, 'r') as f:
                        md_content = f.read()
                    
                    with st.spinner(f"⏳ Analisi con {rev_provider}/{rev_model}..."):
                        result = review_ptof_with_cloud(md_content, rev_provider, provider_key, rev_model)
                    
                    if result:
                        # Overwrite existing JSON
                        json_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.json')
                        if json_files:
                            with open(json_files[0], 'w') as f:
                                json.dump(result, f, indent=2, ensure_ascii=False)
                            st.success(f"✅ Revisione completata! JSON aggiornato: `{os.path.basename(json_files[0])}`")
                        else:
                            # Create new file
                            new_json = f'{ANALYSIS_DIR}/{school_id}_cloud_analysis.json'
                            with open(new_json, 'w') as f:
                                json.dump(result, f, indent=2, ensure_ascii=False)
                            st.success(f"✅ Revisione completata! Nuovo file: `{os.path.basename(new_json)}`")
                        
                        # Update CSV
                        if 'metadata' in result:
                            meta = result['metadata']
                            try:
                                idx = df[df['denominazione'] == selected_school].index
                                if not idx.empty:
                                    i = idx[0]
                                    # Update fields if present in new metadata
                                    if 'tipo_scuola' in meta: df.at[i, 'tipo_scuola'] = meta['tipo_scuola']
                                    if 'ordine_grado' in meta: df.at[i, 'ordine_grado'] = meta['ordine_grado']
                                    if 'area_geografica' in meta: df.at[i, 'area_geografica'] = meta['area_geografica']
                                    if 'territorio' in meta: df.at[i, 'territorio'] = meta['territorio']
                                    if 'comune' in meta: df.at[i, 'comune'] = meta['comune']
                                    
                                    df.to_csv(SUMMARY_FILE, index=False)
                                    load_data.clear()
                                    st.info("ℹ️ Caratteristiche scuola aggiornate nel CSV")
                                    
                                    # Update session state widgets to reflect changes immediately
                                    try:
                                        curr_id = school_id
                                        ss = st.session_state
                                        if 'denominazione' in meta: ss[f"edit_denom_{curr_id}"] = meta['denominazione']
                                        if 'comune' in meta: ss[f"edit_comune_{curr_id}"] = meta['comune']
                                        
                                        if 'ordine_grado' in meta and meta['ordine_grado'] in ['Infanzia', 'Primaria', 'I Grado', 'II Grado', 'Comprensivo']: 
                                             ss[f"edit_ordine_{curr_id}"] = meta['ordine_grado']
                                        if 'area_geografica' in meta and meta['area_geografica'] in ['Nord', 'Centro', 'Sud']: 
                                             ss[f"edit_area_{curr_id}"] = meta['area_geografica']
                                        if 'territorio' in meta and meta['territorio'] in ['Metropolitano', 'Non Metropolitano']: 
                                             ss[f"edit_terr_{curr_id}"] = meta['territorio']

                                        if 'tipo_scuola' in meta:
                                            ts = str(meta['tipo_scuola'])
                                            ss[f"tipo_liceo_{curr_id}"] = 'Liceo' in ts
                                            ss[f"tipo_tecnico_{curr_id}"] = 'Tecnico' in ts
                                            ss[f"tipo_prof_{curr_id}"] = 'Professionale' in ts
                                            ss[f"tipo_igrado_{curr_id}"] = 'I Grado' in ts or 'Medie' in ts
                                            ss[f"tipo_primaria_{curr_id}"] = 'Primaria' in ts
                                            ss[f"tipo_infanzia_{curr_id}"] = 'Infanzia' in ts
                                    except Exception as e:
                                        print(f"Error updating session state: {e}")
                            except Exception as e:
                                st.warning(f"Errore aggiornamento CSV: {e}")
                        
                        # Show result preview
                        with st.expander("📄 Anteprima Risultato"):
                            st.json(result)
                    else:
                        st.error("❌ Errore durante la revisione - nessuna risposta dal modello")
                        st.info(f"Provider: {rev_provider}, Model: {rev_model}")
                else:
                    st.error(f"❌ File MD non trovato per {school_id}")
        elif not provider_key:
            st.info("ℹ️ Inserisci la API key nella sezione Configurazione")

    st.markdown("---")
    st.markdown("### 🔍 Validazione Massiva PTOF")
    
    with st.expander("🛠️ Strumenti di Analisi (Batch)", expanded=False):
        st.info("Scansiona i file MD per identificare documenti troppo brevi o non conformi (es. Regolamenti, Verbali, etc) analizzando le prime 2 pagine.")
        
        col_scan1, col_scan2 = st.columns(2)
        with col_scan1:
            scan_provider = st.selectbox("Provider Validazione", ['gemini', 'openai', 'openrouter'], key="scan_prov")
        with col_scan2:
            val_models = []
            val_key = ""
            if scan_provider == 'gemini':
                val_key = api_config.get('gemini_api_key', '')
                if val_key: val_models = fetch_gemini_models(val_key)
            elif scan_provider == 'openai':
                val_key = api_config.get('openai_api_key', '')
                if val_key: val_models = fetch_openai_models(val_key)
            elif scan_provider == 'openrouter':
                val_key = api_config.get('openrouter_api_key', '')
                val_models = fetch_openrouter_models_free(val_key)
            
            scan_model = st.selectbox("Modello Validazione", val_models, key="scan_model") if val_models else None

        limit_scan = st.number_input("Numero di file da analizzare (ordinati per dimensione crescente)", min_value=1, max_value=200, value=10)
        
        if st.button("🚀 Avvia Scansione Batch", type="primary"):
            if not scan_model or not val_key:
                st.error("Configura API e Modello prima di procedere.")
            else:
                results = []
                files = glob.glob(f'{PTOF_MD_DIR}/*.md')
                # Sort by size ascending (Suspicious first)
                files_with_size = [(f, os.path.getsize(f)) for f in files]
                files_with_size.sort(key=lambda x: x[1])
                
                target_files = files_with_size[:limit_scan]
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, (fpath, size) in enumerate(target_files):
                    fname = os.path.basename(fpath)
                    status_text.write(f"Analisi {i+1}/{len(target_files)}: `{fname}` ({size} bytes)...")
                    
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Heuristic 1: Length < 1000 chars is suspicious
                        if size < 1000:
                            status = "⚠️ Molto Corto"
                            is_ptof = False
                            type_doc = "Sconosciuto (Corto)"
                            reason = f"Lunghezza: {size} caratteri"
                        else:
                            # LLM Check on first 4000 chars
                            res = validate_ptof_header(content, scan_provider, val_key, scan_model)
                            if res:
                                is_ptof = res.get('is_ptof', False)
                                type_doc = res.get('document_type', 'N/D')
                                reason = res.get('reasoning', '')
                                status = "✅ PTOF Valido" if is_ptof else f"❌ {type_doc}"
                            else:
                                status = "❓ Errore API"
                                type_doc = "Errore"
                                reason = "Nessuna risposta"
                        
                        results.append({
                            "File": fname,
                            "Size": size,
                            "Status": status,
                            "Tipo Rilevato": type_doc,
                            "Dettagli": reason
                        })
                    except Exception as e:
                        results.append({"File": fname, "Status": "Error", "Dettagli": str(e)})

                    progress_bar.progress((i+1)/len(target_files))
                
                st.success("Scansione completata!")
                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True)

except ImportError as e:
    st.warning(f"⚠️ Modulo cloud_review non disponibile: {e}")
except Exception as e:
    st.error(f"❌ Errore: {e}")




st.markdown("---")
st.info("🛡️ Per gestire i Backup e Ripristinare i dati, vai alla pagina **Backup e Ripristino**.")

st.caption("⚙️ Gestione - Le eliminazioni sono irreversibili | API keys salvate in data/api_config.json (gitignored)")
