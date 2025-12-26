# 🔍 Ricerca Metodologie - Cerca scuole per metodologia/progetto

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
from collections import Counter
from data_utils import render_footer
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Ricerca Metodologie", page_icon="🧭", layout="wide")
setup_page("pages/07_🔍_Ricerca_Metodologie.py")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'

DIMENSIONS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica Orientativa',
    'mean_opportunita': 'Opportunità'
}

# Glossario metodologie con descrizioni
METHODOLOGY_GLOSSARY = {
    # Didattica Innovativa
    'PBL': 'Project Based Learning: apprendimento basato su progetti reali che sviluppa competenze trasversali',
    'STEM': 'Science, Technology, Engineering, Mathematics: approccio integrato alle discipline scientifiche',
    'STEAM': 'STEM + Arts: integra creatività e discipline artistiche nell\'approccio scientifico-tecnologico',
    'Debate': 'Metodologia del dibattito argomentativo strutturato per sviluppare pensiero critico e public speaking',
    'Flipped Classroom': 'Classe capovolta: gli studenti studiano a casa e applicano in classe con il docente',
    'Cooperative Learning': 'Apprendimento cooperativo in piccoli gruppi con interdipendenza positiva',
    # Orientamento
    'PCTO': 'Percorsi per le Competenze Trasversali e l\'Orientamento (ex Alternanza Scuola-Lavoro)',
    'Alternanza': 'Alternanza Scuola-Lavoro: esperienze formative in contesti lavorativi',
    'Stage': 'Periodo di formazione pratica presso aziende o enti esterni alla scuola',
    'Tirocinio': 'Esperienza formativa guidata in contesto professionale reale',
    'Orientamento Narrativo': 'Metodologia che usa la narrazione per la costruzione dell\'identità e delle scelte',
    'Portfolio': 'Raccolta documentata delle competenze e dei lavori dello studente',
    # Inclusione
    'Inclusione': 'Strategie didattiche per garantire partecipazione e apprendimento di tutti gli studenti',
    'BES': 'Bisogni Educativi Speciali: interventi personalizzati per studenti con difficoltà',
    'DSA': 'Disturbi Specifici dell\'Apprendimento: dislessia, disgrafia, discalculia, disortografia',
    'Peer Education': 'Educazione tra pari: studenti formati che educano altri studenti',
    'Peer Tutoring': 'Tutoraggio tra pari: studenti che supportano compagni nell\'apprendimento',
    'Mentoring': 'Accompagnamento personalizzato da parte di figure esperte o senior',
    # Competenze Trasversali
    'Cittadinanza': 'Educazione civica e alla cittadinanza attiva e responsabile',
    'Legalità': 'Educazione alla legalità e al rispetto delle regole',
    'Volontariato': 'Attività di volontariato come esperienza educativa e formativa',
    'Service Learning': 'Apprendimento attraverso il servizio alla comunità',
    # Tecnologia
    'Digitale': 'Competenze digitali e uso delle tecnologie nella didattica',
    'Coding': 'Programmazione e pensiero computazionale',
    'Robotica': 'Robotica educativa per sviluppare competenze STEM e problem solving',
    'E-Portfolio': 'Portfolio digitale delle competenze dello studente',
    # Laboratori
    'Laboratorio': 'Didattica laboratoriale: apprendere facendo in spazi attrezzati',
    'Learning by Doing': 'Imparare facendo: apprendimento esperienziale e pratico',
    'Outdoor': 'Educazione all\'aperto: attività didattiche in ambienti naturali',
    'Maker': 'Cultura maker: fabbricazione digitale, creatività e innovazione'
}

# Metodologie organizzate per categoria
METHODOLOGIES_BY_CATEGORY = {
    'Didattica Innovativa': ['PBL', 'STEM', 'STEAM', 'Debate', 'Flipped Classroom', 'Cooperative Learning'],
    'Orientamento': ['PCTO', 'Alternanza', 'Stage', 'Tirocinio', 'Orientamento Narrativo', 'Portfolio'],
    'Inclusione': ['Inclusione', 'BES', 'DSA', 'Peer Education', 'Peer Tutoring', 'Mentoring'],
    'Competenze Trasversali': ['Cittadinanza', 'Legalità', 'Volontariato', 'Service Learning'],
    'Tecnologia': ['Digitale', 'Coding', 'Robotica', 'E-Portfolio'],
    'Laboratori': ['Laboratorio', 'Learning by Doing', 'Outdoor', 'Maker']
}

# Lista piatta per ricerca
ALL_METHODOLOGIES = [m for methods in METHODOLOGIES_BY_CATEGORY.values() for m in methods]


@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()


@st.cache_data(ttl=300)
def search_methodology(keyword: str, df: pd.DataFrame) -> pd.DataFrame:
    """Cerca una keyword in tutti i report markdown."""
    results = []
    keyword_lower = keyword.lower()

    for idx, row in df.iterrows():
        school_id = row.get('school_id', '')
        md_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.md')

        if md_files:
            try:
                with open(md_files[0], 'r', encoding='utf-8') as f:
                    content = f.read()

                # Conta occorrenze (case insensitive)
                match_count = len(re.findall(re.escape(keyword_lower), content.lower()))

                if match_count > 0:
                    results.append({
                        'school_id': school_id,
                        'denominazione': row.get('denominazione'),
                        'regione': row.get('regione'),
                        'provincia': row.get('provincia'),
                        'tipo_scuola': row.get('tipo_scuola'),
                        'ptof_orientamento_maturity_index': row.get('ptof_orientamento_maturity_index'),
                        'match_count': match_count,
                        **{col: row.get(col) for col in DIMENSIONS.keys()}
                    })
            except Exception:
                pass

    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(
            ['match_count', 'ptof_orientamento_maturity_index'],
            ascending=[False, False]
        )

    return results_df


# === CARICAMENTO DATI ===
df = load_data()

st.title("🔍 Ricerca Metodologie e Progetti")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

st.markdown("""
Cerca scuole che utilizzano specifiche metodologie didattiche, progetti o approcci.
Seleziona una metodologia dalla lista oppure inserisci una parola chiave personalizzata.
""")

st.markdown("---")

# === STEP 1: SELEZIONE METODOLOGIA ===
st.subheader("1️⃣ Scegli cosa cercare")

# Tabs per categoria
tab_names = list(METHODOLOGIES_BY_CATEGORY.keys()) + ["🔤 Ricerca Libera"]
tabs = st.tabs(tab_names)

selected_keyword = None

# Tab per ogni categoria
for i, (category, methods) in enumerate(METHODOLOGIES_BY_CATEGORY.items()):
    with tabs[i]:
        st.markdown(f"**Seleziona una metodologia di {category}:**")

        cols = st.columns(3)
        for j, method in enumerate(methods):
            with cols[j % 3]:
                tooltip = METHODOLOGY_GLOSSARY.get(method, '')
                if st.button(f"🔍 {method}", key=f"btn_{category}_{method}", use_container_width=True, help=tooltip):
                    st.session_state['selected_methodology'] = method

# Tab ricerca libera
with tabs[-1]:
    st.markdown("**Inserisci una parola chiave personalizzata:**")
    custom_keyword = st.text_input(
        "Parola chiave",
        placeholder="es: musica, teatro, ambiente, sostenibilità...",
        key="custom_search"
    )
    if st.button("🔍 Cerca", key="btn_custom_search", type="primary"):
        if custom_keyword and len(custom_keyword) >= 2:
            st.session_state['selected_methodology'] = custom_keyword

# Mostra selezione corrente
selected_keyword = st.session_state.get('selected_methodology', None)

if selected_keyword:
    st.success(f"**Metodologia selezionata:** {selected_keyword}")

    if st.button("❌ Cancella selezione"):
        del st.session_state['selected_methodology']
        st.rerun()

st.markdown("---")

# === STEP 2: RISULTATI ===
if selected_keyword:
    st.subheader(f"2️⃣ Risultati per \"{selected_keyword}\"")

    with st.spinner(f"Cercando '{selected_keyword}' nei PTOF..."):
        results = search_methodology(selected_keyword, df)

    if results.empty:
        st.warning(f"Nessuna scuola trovata con '{selected_keyword}' nel proprio PTOF.")
        st.info("Prova con una parola chiave diversa o più generica.")
    else:
        # === STATISTICHE ===
        n_schools = len(results)
        pct = n_schools / len(df) * 100
        mean_ro = results['ptof_orientamento_maturity_index'].mean()
        overall_mean = df['ptof_orientamento_maturity_index'].mean()

        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Scuole trovate", f"{n_schools}")
        with stat_cols[1]:
            st.metric("% del campione", f"{pct:.1f}%")
        with stat_cols[2]:
            st.metric("Indice RO medio", f"{mean_ro:.2f}/7")
        with stat_cols[3]:
            delta = mean_ro - overall_mean
            st.metric("vs Media nazionale", f"{overall_mean:.2f}", f"{delta:+.2f}")

        # Insight
        if delta > 0.3:
            st.success(f"💡 Le scuole che usano '{selected_keyword}' hanno un Indice RO superiore alla media!")
        elif delta < -0.3:
            st.info(f"📊 Le scuole che usano '{selected_keyword}' hanno un Indice RO nella media.")

        st.markdown("---")

        # === FILTRI ===
        with st.expander("⚙️ Filtra i risultati", expanded=False):
            col_f1, col_f2 = st.columns(2)

            with col_f1:
                filter_regions = st.multiselect(
                    "Regione",
                    options=sorted(results['regione'].dropna().unique()),
                    default=[]
                )

            with col_f2:
                filter_types = st.multiselect(
                    "Tipo Scuola",
                    options=sorted(results['tipo_scuola'].dropna().unique()),
                    default=[]
                )

        # Applica filtri
        filtered_results = results.copy()
        if filter_regions:
            filtered_results = filtered_results[filtered_results['regione'].isin(filter_regions)]
        if filter_types:
            filtered_results = filtered_results[filtered_results['tipo_scuola'].isin(filter_types)]

        if len(filtered_results) < len(results):
            st.caption(f"Mostrate {len(filtered_results)} scuole su {len(results)} totali (dopo i filtri)")

        st.markdown("---")

        # === LISTA SCUOLE ===
        st.subheader("🏫 Scuole che usano questa metodologia")

        for i, (idx, row) in enumerate(filtered_results.head(15).iterrows()):
            ro = row['ptof_orientamento_maturity_index']
            ro_color = "🟢" if ro >= 5 else "🟡" if ro >= 3.5 else "🔴"

            with st.expander(
                f"{ro_color} **{row['denominazione']}** — {row['regione']} | RO: {ro:.2f} | {row['match_count']} menzioni",
                expanded=(i < 3)
            ):
                col_info, col_radar = st.columns([3, 2])

                with col_info:
                    st.markdown(f"""
                    **Informazioni:**
                    - **Tipo:** {row['tipo_scuola']}
                    - **Provincia:** {row.get('provincia', 'N/D')}
                    - **Regione:** {row['regione']}
                    - **Indice RO:** {ro:.2f}/7
                    - **Menzioni di "{selected_keyword}":** {row['match_count']}
                    """)


                with col_radar:
                    vals = [row.get(d, 0) or 0 for d in DIMENSIONS.keys()]
                    labels = list(DIMENSIONS.values())

                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=labels + [labels[0]],
                        fill='toself',
                        line_color='#3498db'
                    ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(range=[0, 7], showticklabels=False)),
                        showlegend=False,
                        height=200,
                        margin=dict(l=30, r=30, t=20, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)

        if len(filtered_results) > 15:
            st.info(f"Mostrate le prime 15 scuole su {len(filtered_results)} totali.")

        st.markdown("---")

        # === ANALISI ===
        st.subheader("📊 Analisi")

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("**Distribuzione per Regione**")
            region_counts = filtered_results['regione'].value_counts().head(10)
            fig_region = px.bar(
                x=region_counts.values,
                y=region_counts.index,
                orientation='h',
                labels={'x': 'N. Scuole', 'y': 'Regione'},
                color=region_counts.values,
                color_continuous_scale='Blues'
            )
            fig_region.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_region, use_container_width=True)

        with col_chart2:
            st.markdown("**Distribuzione per Tipo Scuola**")
            type_counts = filtered_results['tipo_scuola'].value_counts().head(8)
            fig_type = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                hole=0.4
            )
            fig_type.update_layout(height=350)
            st.plotly_chart(fig_type, use_container_width=True)

        # Confronto dimensioni
        st.markdown("**Confronto Dimensioni: scuole con questa metodologia vs media nazionale**")

        comparison_data = []
        for dim_col, dim_label in DIMENSIONS.items():
            with_method = filtered_results[dim_col].mean() if dim_col in filtered_results.columns else 0
            overall = df[dim_col].mean() if dim_col in df.columns else 0
            comparison_data.append({
                'Dimensione': dim_label,
                f'Con "{selected_keyword}"': with_method,
                'Media nazionale': overall
            })

        comp_df = pd.DataFrame(comparison_data)

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name=f'Scuole con "{selected_keyword}"',
            x=comp_df['Dimensione'],
            y=comp_df[f'Con "{selected_keyword}"'],
            marker_color='#3498db'
        ))
        fig_comp.add_trace(go.Bar(
            name='Media nazionale',
            x=comp_df['Dimensione'],
            y=comp_df['Media nazionale'],
            marker_color='#bdc3c7'
        ))
        fig_comp.update_layout(barmode='group', yaxis_range=[0, 7], height=350)
        st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("---")

        # === TABELLA EXPORT ===
        st.subheader("📋 Tabella Completa")

        export_df = filtered_results[['denominazione', 'regione', 'provincia', 'tipo_scuola',
                                      'ptof_orientamento_maturity_index', 'match_count']].copy()
        export_df.columns = ['Scuola', 'Regione', 'Provincia', 'Tipo', 'Indice RO', 'Menzioni']
        export_df['Indice RO'] = export_df['Indice RO'].round(2)

        st.dataframe(export_df, use_container_width=True, hide_index=True)

        # Download CSV
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV",
            data=csv,
            file_name=f"scuole_{selected_keyword.replace(' ', '_')}.csv",
            mime="text/csv"
        )

else:
    # Nessuna selezione - mostra istruzioni
    st.info("👆 Seleziona una metodologia dalle tab sopra per iniziare la ricerca.")

    st.markdown("---")

    # Panoramica metodologie più diffuse
    st.subheader("📊 Metodologie più diffuse nel campione")

    with st.spinner("Analisi in corso..."):
        freq = Counter()
        for idx, row in df.iterrows():
            school_id = row.get('school_id', '')
            md_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.md')
            if md_files:
                try:
                    with open(md_files[0], 'r', encoding='utf-8') as f:
                        content = f.read().upper()
                    for method in ALL_METHODOLOGIES:
                        if method.upper() in content:
                            freq[method] += 1
                except Exception:
                    pass

    if freq:
        top_methods = freq.most_common(12)

        fig = px.bar(
            x=[m[1] for m in top_methods],
            y=[m[0] for m in top_methods],
            orientation='h',
            labels={'x': 'Numero di scuole', 'y': 'Metodologia'},
            color=[m[1] for m in top_methods],
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=450, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

        st.caption("Clicca su una metodologia nelle tab sopra per vedere i dettagli.")

st.markdown("---")

# === GLOSSARIO ===
with st.expander("📖 Glossario delle Metodologie", expanded=False):
    st.markdown("Passa il mouse sui bottoni delle metodologie per vedere una breve descrizione, oppure consulta il glossario completo qui sotto.")

    for category, methods in METHODOLOGIES_BY_CATEGORY.items():
        st.markdown(f"**{category}**")
        for method in methods:
            desc = METHODOLOGY_GLOSSARY.get(method, '')
            st.markdown(f"- **{method}**: {desc}")
        st.markdown("")

render_footer()
