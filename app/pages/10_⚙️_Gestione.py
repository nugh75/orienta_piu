# ⚙️ Gestione - Revisione Metadati Scuole

import streamlit as st
import pandas as pd
import os
import json
import glob

st.set_page_config(page_title="Gestione", page_icon="⚙️", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'
PTOF_PROCESSED_DIR = 'ptof_processed'
PTOF_INBOX_DIR = 'ptof_inbox'
PTOF_SEARCH_DIRS = [PTOF_PROCESSED_DIR, PTOF_INBOX_DIR]
PTOF_MD_DIR = 'ptof_md'

@st.cache_data(ttl=30)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

def display_pdf(school_id, height=600):
    """Display PDF for a given school_id"""
    import base64

    try:
        from app.data_utils import find_pdf_for_school
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
            return True
        except Exception as e:
            st.warning(f"Impossibile visualizzare PDF: {e}")
            return False
    else:
        st.info(f"PDF non trovato per {school_id}")
        st.caption("Cartelle cercate: ptof_processed/, ptof_inbox/")
        return False

df = load_data()

st.title("⚙️ Gestione Metadati Scuole")
st.markdown("Visualizza e modifica i metadati delle scuole analizzate")

st.markdown("---")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()
    
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
    
    # Nuovi metadati: Regione, Provincia, Stato
    regione = school_row.get('regione', 'N/D')
    provincia = school_row.get('provincia', 'N/D')
    statale = school_row.get('statale_paritaria', 'N/D')
    st.write(f"**Regione:** {regione if regione and regione != 'ND' else 'N/D'} | **Provincia:** {provincia if provincia and provincia != 'ND' else 'N/D'} | **Stato:** {statale if statale and statale != 'ND' else 'N/D'}")
    
    st.write(f"**Indice:** {school_row.get('ptof_orientamento_maturity_index', 'N/D'):.2f}/7" if pd.notna(school_row.get('ptof_orientamento_maturity_index')) else "**Indice:** N/D")
    
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
    if tipo_infanzia: selected_types.append('Infanzia')
    if tipo_primaria: selected_types.append('Primaria')
    if tipo_igrado: selected_types.append('I Grado')
    if tipo_liceo: selected_types.append('Liceo')
    if tipo_tecnico: selected_types.append('Tecnico')
    if tipo_prof: selected_types.append('Professionale')
    new_tipo = ', '.join(selected_types) if selected_types else ''
    
    # Build ordine_grado from checkboxes
    selected_ordini = []
    if ordine_infanzia: selected_ordini.append('Infanzia')
    if ordine_primaria: selected_ordini.append('Primaria')
    if ordine_igrado: selected_ordini.append('I Grado')
    if ordine_iigrado: selected_ordini.append('II Grado')
    if ordine_comprensivo: selected_ordini.append('Comprensivo')
    new_ordine = ', '.join(selected_ordini) if selected_ordini else ''

    
    if st.button("💾 Salva Modifiche", key="save_edit", type="primary"):
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
df_mgmt = load_data()

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
                load_data.clear()
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
                            except: pass
                    st.success(f"Record eliminato: {anom_row['school_id']}")
                    load_data.clear()
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
                    load_data.clear()
                    st.rerun()
    else:
        st.success("✅ Nessun record anomalo")

st.markdown("---")
st.caption("⚙️ Gestione Metadati - Modifiche salvate in data/analysis_summary.csv e file JSON corrispondenti")
