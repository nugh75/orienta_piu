# 📚 Report Best Practice - Visualizza report generato dall'agente

import streamlit as st
import os
from datetime import datetime

st.set_page_config(page_title="Report Best Practice", page_icon="📚", layout="wide")

REPORT_STATISTICO = 'reports/best_practice_orientamento.md'
REPORT_NARRATIVO = 'reports/best_practice_orientamento_narrativo.md'
REPORT_SINTETICO = 'reports/best_practice_orientamento_sintetico.md'

st.title("📚 Report Best Practice Orientamento")

with st.expander("📖 Come usare questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Visualizza i **report aggregati delle best practice** estratte dall'analisi di tutti i PTOF.

    ### 📊 Tre tipologie di Report
    - **Report Statistico**: Dati aggregati, classifiche, tabelle (generato con algoritmi)
    - **Report Narrativo**: Analisi discorsiva completa (generato con LLM Ollama)
    - **Report Sintetico**: Versione condensata del narrativo, refactoring per sezioni (Gemini)

    ### ♻️ Rigenerazione
    Per aggiornare i report, esegui nel terminale:
    ```bash
    make best-practice            # Report statistico
    make best-practice-llm        # Report narrativo con LLM
    make best-practice-llm-synth  # Report sintetico (da narrativo)
    ```
    """)

st.markdown("---")

# Tab per i tre report
tab1, tab2, tab3 = st.tabs(["📊 Report Statistico", "📝 Report Narrativo (LLM)", "✨ Report Sintetico"])

with tab1:
    st.subheader("📊 Report Statistico")
    st.caption("Dati aggregati e classifiche basate sull'analisi dei PTOF")
    
    if os.path.exists(REPORT_STATISTICO):
        mod_time = os.path.getmtime(REPORT_STATISTICO)
        mod_date = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')
        st.caption(f"📅 Generato il: {mod_date}")
        
        with open(REPORT_STATISTICO, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        st.markdown(report_content)
        
        st.markdown("---")
        st.download_button(
            label="📥 Scarica Report Statistico (MD)",
            data=report_content.encode('utf-8'),
            file_name="best_practice_orientamento.md",
            mime="text/markdown",
            key="download_stat"
        )
    else:
        st.warning("⚠️ Report statistico non ancora generato.")
        st.code("make best-practice", language="bash")

with tab2:
    st.subheader("📝 Report Narrativo")
    st.caption("Analisi discorsiva generata con LLM Ollama (qwen3:32b)")
    
    if os.path.exists(REPORT_NARRATIVO):
        mod_time = os.path.getmtime(REPORT_NARRATIVO)
        mod_date = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')
        st.caption(f"📅 Generato il: {mod_date}")
        
        with open(REPORT_NARRATIVO, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        st.markdown(report_content)
        
        st.markdown("---")
        st.download_button(
            label="📥 Scarica Report Narrativo (MD)",
            data=report_content.encode('utf-8'),
            file_name="best_practice_orientamento_narrativo.md",
            mime="text/markdown",
            key="download_narr"
        )
    else:
        st.warning("⚠️ Report narrativo non ancora generato.")
        st.info("Questo report usa Ollama LLM per generare un'analisi discorsiva professionale.")
        st.code("make best-practice-llm", language="bash")

with tab3:
    st.subheader("✨ Report Sintetico")
    st.caption("Versione condensata del report narrativo, refactoring sezione per sezione con Gemini")

    if os.path.exists(REPORT_SINTETICO):
        mod_time = os.path.getmtime(REPORT_SINTETICO)
        mod_date = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')
        st.caption(f"📅 Generato il: {mod_date}")

        with open(REPORT_SINTETICO, 'r', encoding='utf-8') as f:
            synth_content = f.read()

        # Mostra statistiche confronto
        if os.path.exists(REPORT_NARRATIVO):
            with open(REPORT_NARRATIVO, 'r', encoding='utf-8') as f:
                narr_content = f.read()
            reduction = (1 - len(synth_content) / len(narr_content)) * 100
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Narrativo", f"{len(narr_content):,} car.")
            with col2:
                st.metric("✨ Sintetico", f"{len(synth_content):,} car.")
            with col3:
                st.metric("📉 Riduzione", f"{reduction:.0f}%")
            st.markdown("---")

        st.markdown(synth_content)

        st.markdown("---")
        st.download_button(
            label="📥 Scarica Report Sintetico (MD)",
            data=synth_content.encode('utf-8'),
            file_name="best_practice_orientamento_sintetico.md",
            mime="text/markdown",
            key="download_synth"
        )
    else:
        st.warning("⚠️ Report sintetico non ancora generato.")
        st.info("""
        Il report sintetico è una versione condensata del report narrativo.
        Viene generato processando ogni sezione separatamente con Gemini per:
        - Eliminare ridondanze
        - Unificare contenuti simili
        - Ridurre la lunghezza del 30-50%
        """)
        st.code("make best-practice-llm-synth", language="bash")

st.markdown("---")
st.caption("📚 Report Best Practice - Dashboard PTOF | Analisi aggregata delle best practice sull'orientamento")
