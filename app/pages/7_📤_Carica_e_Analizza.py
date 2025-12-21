import streamlit as st
import os
import glob
import pandas as pd
import sys
import shutil

# Add project root to path
sys.path.insert(0, '.')

try:
    from src.processing.convert_pdfs_to_md import pdf_to_markdown
    from src.processing.cloud_review import (
        load_api_config, 
        fetch_gemini_models, fetch_openai_models, fetch_openrouter_models_free,
        review_ptof_with_cloud
    )
    from app.agentic_pipeline import (
        AnalystAgent, ReviewerAgent, RefinerAgent, process_single_ptof
    )
except ImportError as e:
    st.error(f"Errore importazione moduli: {e}")
    st.stop()

st.set_page_config(page_title="Carica e Analizza", page_icon="📤", layout="wide")

# Config paths
PTOF_DIR = 'ptof'
PTOF_MD_DIR = 'ptof_md'
ANALYSIS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'

# Ensure directories exist
os.makedirs(PTOF_DIR, exist_ok=True)
os.makedirs(PTOF_MD_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

st.title("📤 Carica Nuovi PTOF e Analizza")
st.markdown("Carica i file PDF dei PTOF per convertirli e analizzarli **direttamente con il modello Cloud** (nessuna pipeline locale).")

# --- Configurazione Analisi ---
st.sidebar.header("Configurazione Analisi")
api_config = load_api_config()
provider = st.sidebar.selectbox("Provider", ['gemini', 'openai', 'openrouter'], key="up_prov")

models = []
api_key = ""
if provider == 'gemini':
    api_key = api_config.get('gemini_api_key', '')
    if api_key: models = fetch_gemini_models(api_key)
elif provider == 'openai':
    api_key = api_config.get('openai_api_key', '')
    if api_key: models = fetch_openai_models(api_key)
elif provider == 'openrouter':
    api_key = api_config.get('openrouter_api_key', '')
    models = fetch_openrouter_models_free(api_key)

model = st.sidebar.selectbox("Modello", models, key="up_model") if models else None

if not api_key or not model:
    st.sidebar.warning("⚠️ Configura API Key per Cloud")

st.sidebar.markdown("---")
analysis_mode = st.sidebar.radio(
    "Modalità Analisi", 
    ["Cloud API (Veloce)", "Locale Ollama (Multi-Agent)"],
    index=1,
    help="Cloud: Singolo passaggio. Locale: Architettura a 3 Agenti (Analyst, Reviewer, Refiner) su Ollama."
)

# --- Validatore ---
def update_csv_with_metadata(school_id, meta):
    """Update CSV with new metadata"""
    if not os.path.exists(SUMMARY_FILE):
        return # Should create? For now assume it exists
        
    try:
        df = pd.read_csv(SUMMARY_FILE)
        # Check if school exists by ID or Denominazione
        # If new school, we might not have a row.
        # Check by school_id first
        mask_id = df['school_id'] == school_id
        if mask_id.any():
            idx = df[mask_id].index[0]
        else:
            # Check by denominazione
            denominazione = meta.get('denominazione', '')
            if denominazione:
                mask_denom = df['denominazione'] == denominazione
                if mask_denom.any():
                    idx = df[mask_denom].index[0]
                else:
                    # New Row
                    new_row = {'school_id': school_id, 'denominazione': denominazione or f"School {school_id}"}
                    # Add missing cols
                    for c in df.columns:
                        if c not in new_row: new_row[c] = 'ND'
                    
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    idx = df.index[-1]
            else:
                 # Create completely new row
                new_row = {'school_id': school_id, 'denominazione': f"School {school_id}"}
                for c in df.columns:
                    if c not in new_row: new_row[c] = 'ND'
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                idx = df.index[-1]
        
        # Update fields
        if 'denominazione' in meta: df.at[idx, 'denominazione'] = meta['denominazione']
        if 'tipo_scuola' in meta: df.at[idx, 'tipo_scuola'] = meta['tipo_scuola']
        if 'ordine_grado' in meta: df.at[idx, 'ordine_grado'] = meta['ordine_grado']
        if 'area_geografica' in meta: df.at[idx, 'area_geografica'] = meta['area_geografica']
        if 'territorio' in meta: df.at[idx, 'territorio'] = meta['territorio']
        if 'comune' in meta: df.at[idx, 'comune'] = meta['comune']
        
        df.to_csv(SUMMARY_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Errore aggiornamento CSV: {e}")
        return False

# --- Uploader ---
uploaded_files = st.file_uploader("Trascina qui i PDF", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} file pronti.**")
    
    # Determine if disabled
    disable_btn = False
    if analysis_mode.startswith("Cloud") and (not model):
        disable_btn = True
        
    if st.button("🚀 Avvia Processo (Converti + Analizza)", type="primary", disabled=disable_btn):
        
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        results_log = []
        
        for i, up_file in enumerate(uploaded_files):
            fname = up_file.name
            status_area.write(f"Elaborazione {i+1}/{len(uploaded_files)}: `{fname}`...")
            
            # 1. Save PDF
            try:
                # Sanitize filename?
                safe_name = fname.replace(" ", "_")
                pdf_path = os.path.join(PTOF_DIR, safe_name)
                
                with open(pdf_path, "wb") as f:
                    f.write(up_file.getbuffer())
                
                file_size = os.path.getsize(pdf_path)
                results_log.append(f"✅ Salvato: `{safe_name}` ({file_size} bytes)")
                
                # Extract simple school_id from filename (basic heuristic)
                # Assumes filename contains ID. If not, use generic.
                # Heuristic: Find pattern like MIIS...
                import re
                id_match = re.search(r'([A-Z]{2}[A-Z0-9]{8})', safe_name.upper())
                school_id = id_match.group(1) if id_match else safe_name.replace('.pdf', '')
                
                # 2. Convert to MD
                md_name = safe_name.replace('.pdf', '.md')
                md_path = os.path.join(PTOF_MD_DIR, md_name)
                
                status_area.write(f"Conversione PDF -> MD: `{safe_name}`...")
                if pdf_to_markdown(pdf_path, md_path):
                    results_log.append(f"✅ Convertito MD: `{md_name}`")
                    
                    # 3. Analyze
                    # 3. Analyze
                    if analysis_mode.startswith("Cloud"):
                        if model and api_key:
                            status_area.write(f"Analisi LLM ({provider}): `{md_name}`...")
                            
                            with open(md_path, 'r', encoding='utf-8') as f:
                                md_content = f.read()
                                
                            # Run Analysis
                            import json
                            result = review_ptof_with_cloud(md_content, provider, api_key, model)
                            
                            if result:
                                # Save JSON
                                json_path = os.path.join(ANALYSIS_DIR, f"{school_id}_cloud_analysis.json")
                                with open(json_path, 'w') as f:
                                    json.dump(result, f, indent=2, ensure_ascii=False)
                                results_log.append(f"✅ Analisi Completa: `{os.path.basename(json_path)}`")
                                
                                # Update CSV
                                if 'metadata' in result:
                                    if update_csv_with_metadata(school_id, result['metadata']):
                                        results_log.append("✅ CSV Aggiornato")
                            else:
                                 results_log.append(f"❌ Errore Analisi LLM per {safe_name}")
                        else:
                             results_log.append(f"⚠️ Configurazione Cloud mancante per {safe_name}")

                    elif analysis_mode.startswith("Locale"):
                        status_area.write(f"Avvio Pipeline Locale (Ollama Agentic)...")
                        
                        try:
                            # Initialize Agents
                            analyst = AnalystAgent()
                            reviewer = ReviewerAgent()
                            refiner = RefinerAgent()
                            
                            def update_status(msg):
                                status_area.write(f"🤖 [{school_id}] {msg}")
                                
                            result = process_single_ptof(md_path, analyst, reviewer, refiner, results_dir=ANALYSIS_DIR, status_callback=update_status)
                            
                            if result:
                                results_log.append(f"✅ Analisi Agentic Completa: `{school_id}`")
                                # Update CSV
                                if 'metadata' in result:
                                    update_csv_with_metadata(school_id, result['metadata'])
                            else:
                                results_log.append(f"❌ Pipeline locale fallita per {safe_name}")
                        except Exception as e:
                             results_log.append(f"❌ Errore Ollama: {e}")
                    else:
                        results_log.append("⚠️ Modalità Analisi non riconosciuta")
                else:
                    results_log.append(f"❌ Errore Conversione per {safe_name}")
                    
            except Exception as e:
                results_log.append(f"❌ Errore critico su {fname}: {e}")
            
            progress_bar.progress((i+1)/len(uploaded_files))
            
        status_area.success("Tutte le operazioni completate!")
        
        with st.expander("📝 Log Operazioni", expanded=True):
            for log in results_log:
                st.write(log)
                
        # Cache clearing
        st.cache_data.clear()
