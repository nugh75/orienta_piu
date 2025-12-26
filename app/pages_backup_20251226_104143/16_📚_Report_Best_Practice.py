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

        # Genera indice navigabile
        import re

        # Definizione struttura
        TIPOLOGIE = [
            ("💒 Nelle Scuole dell'Infanzia", "Nelle Scuole dell'Infanzia"),
            ("📗 Nelle Scuole Primarie", "Nelle Scuole Primarie"),
            ("📘 Nelle Scuole Secondarie di Primo Grado", "Nelle Scuole Secondarie di Primo Grado"),
            ("📙 Nei Licei", "Nei Licei"),
            ("📕 Negli Istituti Tecnici", "Negli Istituti Tecnici"),
            ("📓 Negli Istituti Professionali", "Negli Istituti Professionali"),
        ]

        CATEGORIE = [
            "Metodologie Didattiche Innovative",
            "Progetti e Attività Esemplari",
            "Partnership e Collaborazioni Strategiche",
            "Azioni di Sistema e Governance",
            "Buone Pratiche per l'Inclusione",
            "Esperienze Territoriali Significative",
        ]

        # Verifica se una sezione ha contenuto reale
        def has_section_content(content, tipologia, categoria):
            """Verifica se tra ### Categoria e il prossimo ### c'è contenuto reale (####)."""
            # Trova la sezione tipologia
            tipo_pattern = rf"## {re.escape(tipologia)}\s*\n"
            tipo_match = re.search(tipo_pattern, content)
            if not tipo_match:
                return False

            # Trova la prossima sezione ## (fine della tipologia)
            next_tipo = re.search(r'\n## ', content[tipo_match.end():])
            tipo_end = tipo_match.end() + next_tipo.start() if next_tipo else len(content)
            tipo_content = content[tipo_match.end():tipo_end]

            # Cerca ### Categoria dentro tipo_content
            cat_pattern = rf"### {re.escape(categoria)}\s*\n"
            cat_match = re.search(cat_pattern, tipo_content)
            if not cat_match:
                return False

            # Trova il prossimo ### (fine della categoria)
            next_cat = re.search(r'\n### ', tipo_content[cat_match.end():])
            cat_end = cat_match.end() + next_cat.start() if next_cat else len(tipo_content)
            cat_content = tipo_content[cat_match.end():cat_end]

            # Cerca se c'è un #### (contenuto reale) o testo significativo
            has_h4 = '####' in cat_content
            clean = re.sub(r'\*[^*]+\*', '', cat_content)
            clean = re.sub(r'---', '', clean)
            clean = clean.strip()

            return has_h4 or len(clean) > 100

        # Funzione per creare anchor ID
        def make_anchor(text):
            """Crea un anchor ID valido da un testo."""
            return text.lower().replace(" ", "-").replace("'", "").replace(".", "")

        # Aggiungi anchor HTML nel report per ogni sezione
        def add_anchors_to_report(content):
            """Inserisce anchor HTML prima di ogni ## e ### per la navigazione."""
            lines = content.split('\n')
            result = []
            for line in lines:
                # Anchor per tipologie (##)
                if line.startswith('## ') and not line.startswith('### '):
                    section_name = line[3:].strip()
                    anchor_id = make_anchor(section_name)
                    result.append(f'<div id="{anchor_id}"></div>\n')
                # Anchor per categorie (###)
                elif line.startswith('### ') and not line.startswith('#### '):
                    section_name = line[4:].strip()
                    anchor_id = make_anchor(section_name)
                    result.append(f'<div id="{anchor_id}"></div>\n')
                result.append(line)
            return '\n'.join(result)

        # Anchor per tornare all'indice
        st.markdown('<div id="indice-report"></div>', unsafe_allow_html=True)

        # Mostra indice in expander
        with st.expander("📚 **INDICE DEL REPORT** - Clicca per navigare", expanded=True):
            # Crea colonne per le tipologie
            cols = st.columns(3)

            for i, (label, tipologia) in enumerate(TIPOLOGIE):
                col_idx = i % 3
                with cols[col_idx]:
                    # Verifica se la tipologia ha contenuto
                    has_content = any(
                        has_section_content(report_content, tipologia, cat)
                        for cat in CATEGORIE
                    )

                    if has_content:
                        tipo_anchor = make_anchor(tipologia)
                        st.markdown(f"**[{label}](#{tipo_anchor})**", unsafe_allow_html=True)
                        for categoria in CATEGORIE:
                            if has_section_content(report_content, tipologia, categoria):
                                cat_anchor = make_anchor(categoria)
                                st.markdown(f"&nbsp;&nbsp;- [{categoria}](#{cat_anchor})", unsafe_allow_html=True)
                    else:
                        st.markdown(f"*{label}* (vuoto)")

        st.markdown("---")

        # Aggiungi anchor e mostra report
        report_with_anchors = add_anchors_to_report(report_content)
        st.markdown(report_with_anchors, unsafe_allow_html=True)

        # Pulsante flottante per tornare all'indice
        st.markdown("""
        <style>
        .floating-button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 1000;
            transition: background-color 0.3s, transform 0.2s;
        }
        .floating-button:hover {
            background-color: #45a049;
            transform: scale(1.05);
            color: white;
            text-decoration: none;
        }
        </style>
        <a href="#indice-report" class="floating-button">📚 Indice</a>
        """, unsafe_allow_html=True)

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
