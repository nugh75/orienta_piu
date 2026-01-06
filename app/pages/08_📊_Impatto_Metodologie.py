# 📊 Impatto Metodologie - Analisi statistica dell'effetto sull'Indice RO

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
from scipy import stats
try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
from data_utils import (
    render_footer,
    load_summary_data,
    scale_to_pct,
    format_pct
)
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Impatto Metodologie", page_icon="🧭", layout="wide")
setup_page("pages/08_📊_Impatto_Metodologie.py")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'

# Glossario metodologie
METHODOLOGY_GLOSSARY = {
    'PBL': 'Project Based Learning',
    'STEM': 'Science, Technology, Engineering, Mathematics',
    'STEAM': 'STEM + Arts',
    'Debate': 'Dibattito argomentativo',
    'Flipped Classroom': 'Classe capovolta',
    'Cooperative Learning': 'Apprendimento cooperativo',
    'PCTO': 'Percorsi Competenze Trasversali e Orientamento',
    'Alternanza': 'Alternanza Scuola-Lavoro',
    'Stage': 'Stage aziendale',
    'Tirocinio': 'Tirocinio formativo',
    'Orientamento Narrativo': 'Orientamento Narrativo',
    'Portfolio': 'Portfolio competenze',
    'Inclusione': 'Didattica inclusiva',
    'BES': 'Bisogni Educativi Speciali',
    'DSA': 'Disturbi Specifici Apprendimento',
    'Peer Education': 'Educazione tra pari',
    'Peer Tutoring': 'Tutoraggio tra pari',
    'Mentoring': 'Mentoring',
    'Cittadinanza': 'Educazione civica',
    'Legalità': 'Educazione legalità',
    'Volontariato': 'Volontariato',
    'Service Learning': 'Service Learning',
    'Digitale': 'Competenze digitali',
    'Coding': 'Coding',
    'Robotica': 'Robotica educativa',
    'E-Portfolio': 'E-Portfolio',
    'Laboratorio': 'Didattica laboratoriale',
    'Learning by Doing': 'Learning by Doing',
    'Outdoor': 'Outdoor education',
    'Maker': 'Cultura Maker'
}

ALL_METHODOLOGIES = list(METHODOLOGY_GLOSSARY.keys())


@st.cache_data(ttl=60)
def load_data():
    df = load_summary_data()
    if 'ptof_orientamento_maturity_index' in df.columns:
        df['ptof_orientamento_maturity_index'] = pd.to_numeric(
            df['ptof_orientamento_maturity_index'], errors='coerce'
        )
    return df


@st.cache_data(ttl=600)
def analyze_methodology_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Analizza l'impatto di ogni metodologia sull'Indice RO."""
    results = []

    # Per ogni scuola, verifica quali metodologie usa
    school_methods = {}

    for idx, row in df.iterrows():
        school_id = row.get('school_id', '')
        md_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.md')

        if md_files:
            try:
                with open(md_files[0], 'r', encoding='utf-8') as f:
                    content = f.read().upper()

                methods_used = []
                for method in ALL_METHODOLOGIES:
                    if method.upper() in content:
                        methods_used.append(method)

                school_methods[school_id] = {
                    'methods': methods_used,
                    'ro': scale_to_pct(row.get('ptof_orientamento_maturity_index', np.nan))
                }
            except Exception:
                pass

    # Calcola statistiche per ogni metodologia
    for method in ALL_METHODOLOGIES:
        schools_with = []
        schools_without = []

        for school_id, data in school_methods.items():
            ro = data['ro']
            if pd.notna(ro):
                if method in data['methods']:
                    schools_with.append(ro)
                else:
                    schools_without.append(ro)

        if len(schools_with) >= 5 and len(schools_without) >= 5:
            # Calcola medie
            mean_with = np.mean(schools_with)
            mean_without = np.mean(schools_without)
            diff = mean_with - mean_without

            # T-test indipendente
            t_stat, p_value = stats.ttest_ind(schools_with, schools_without)

            # Effect size (Cohen's d)
            pooled_std = np.sqrt(
                ((len(schools_with) - 1) * np.std(schools_with, ddof=1)**2 +
                 (len(schools_without) - 1) * np.std(schools_without, ddof=1)**2) /
                (len(schools_with) + len(schools_without) - 2)
            )
            cohens_d = diff / pooled_std if pooled_std > 0 else 0

            # Significatività
            if p_value < 0.001:
                sig_level = '***'
                sig_text = 'Altamente significativo'
            elif p_value < 0.01:
                sig_level = '**'
                sig_text = 'Molto significativo'
            elif p_value < 0.05:
                sig_level = '*'
                sig_text = 'Significativo'
            else:
                sig_level = ''
                sig_text = 'Non significativo'

            # Interpretazione effect size
            if abs(cohens_d) >= 0.8:
                effect_text = 'Grande'
            elif abs(cohens_d) >= 0.5:
                effect_text = 'Medio'
            elif abs(cohens_d) >= 0.2:
                effect_text = 'Piccolo'
            else:
                effect_text = 'Trascurabile'

            results.append({
                'Metodologia': method,
                'Descrizione': METHODOLOGY_GLOSSARY.get(method, ''),
                'N_Con': len(schools_with),
                'N_Senza': len(schools_without),
                'Media_Con': mean_with,
                'Media_Senza': mean_without,
                'Differenza': diff,
                'Differenza_Pct': (diff / mean_without * 100) if mean_without > 0 else 0,
                't_statistic': t_stat,
                'p_value': p_value,
                'Cohens_d': cohens_d,
                'Significativita': sig_level,
                'Sig_Text': sig_text,
                'Effect_Size': effect_text
            })

    return pd.DataFrame(results).sort_values('Differenza', ascending=False)


# === MAIN ===
df = load_data()

st.title("📊 Impatto delle Metodologie sull'Indice di Completezza")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

st.markdown("""
Questa pagina analizza **l'impatto statistico** di ciascuna metodologia didattica sull'Indice di Completezza
PTOF. Per ogni metodologia confrontiamo le scuole che la utilizzano con quelle che non la utilizzano.
""")

# Legenda
with st.expander("📖 Come leggere i risultati", expanded=False):
    st.markdown("""
    **Metriche statistiche:**
    - **Differenza**: differenza media dell'Indice di Completezza (%) tra scuole che usano e non usano la metodologia
    - **p-value**: probabilità che la differenza sia dovuta al caso (< 0.05 = significativo)
    - **Cohen's d**: dimensione dell'effetto (quanto è grande la differenza in termini pratici)

    **Livelli di significatività:**
    - ⭐⭐⭐ (***) p < 0.001 - Altamente significativo
    - ⭐⭐ (**) p < 0.01 - Molto significativo
    - ⭐ (*) p < 0.05 - Significativo
    - Nessuna stella: Non significativo statisticamente

    **Dimensione dell'effetto (Cohen's d):**
    - |d| ≥ 0.8: Effetto grande
    - |d| ≥ 0.5: Effetto medio
    - |d| ≥ 0.2: Effetto piccolo
    - |d| < 0.2: Effetto trascurabile
    """)

st.markdown("---")

# Analisi
with st.spinner("Analisi statistica in corso..."):
    impact_df = analyze_methodology_impact(df)

if impact_df.empty:
    st.warning("Dati insufficienti per l'analisi statistica.")
    st.stop()

# === RIEPILOGO ===
st.subheader("🎯 Riepilogo")

sig_positive = impact_df[(impact_df['p_value'] < 0.05) & (impact_df['Differenza'] > 0)]
sig_negative = impact_df[(impact_df['p_value'] < 0.05) & (impact_df['Differenza'] < 0)]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Metodologie analizzate", len(impact_df))
with col2:
    st.metric("Con impatto positivo significativo", len(sig_positive), delta=None)
with col3:
    st.metric("Con impatto negativo significativo", len(sig_negative), delta=None)
with col4:
    best = impact_df.iloc[0] if not impact_df.empty else None
    if best is not None:
        st.metric("Metodologia più efficace", best['Metodologia'], f"+{best['Differenza']:.2f}")

st.markdown("---")

# === GRAFICO PRINCIPALE ===
st.subheader("📈 Impatto delle Metodologie sull'Indice di Completezza")

# Prepara dati per il grafico
chart_df = impact_df.copy()
chart_df['Colore'] = chart_df.apply(
    lambda x: 'Positivo Significativo' if x['p_value'] < 0.05 and x['Differenza'] > 0
    else ('Negativo Significativo' if x['p_value'] < 0.05 and x['Differenza'] < 0
    else 'Non Significativo'), axis=1
)

color_map = {
    'Positivo Significativo': '#27ae60',
    'Negativo Significativo': '#e74c3c',
    'Non Significativo': '#95a5a6'
}

fig = px.bar(
    chart_df,
    x='Differenza',
    y='Metodologia',
    orientation='h',
    color='Colore',
    color_discrete_map=color_map,
    hover_data=['Media_Con', 'Media_Senza', 'p_value', 'Cohens_d', 'N_Con']
)

fig.update_layout(
    height=700,
    yaxis={'categoryorder': 'total ascending'},
    xaxis_title='Differenza Indice Completezza % (Con vs Senza)',
    yaxis_title='',
    legend_title='Significatività',
    showlegend=True
)

# Linea verticale a 0
fig.add_vline(x=0, line_dash="dash", line_color="gray")

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# === TOP METODOLOGIE ===
st.subheader("🏆 Top Metodologie per Impatto Positivo")

top_positive = impact_df[impact_df['Differenza'] > 0].head(10)

if not top_positive.empty:
    for i, (idx, row) in enumerate(top_positive.iterrows()):
        sig_stars = row['Significativita']
        sig_color = "🟢" if row['p_value'] < 0.05 else "⚪"

        with st.expander(
            f"{i+1}. {sig_color} **{row['Metodologia']}** — +{row['Differenza']:.1f}% Completezza {sig_stars}",
            expanded=(i < 3)
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**{row['Descrizione']}**")
                st.markdown(f"""
                | Metrica | Valore |
                |---------|--------|
                | Scuole che la usano | {row['N_Con']} |
                | Scuole che NON la usano | {row['N_Senza']} |
                | Media RO (con) | {row['Media_Con']:.1f}% |
                | Media RO (senza) | {row['Media_Senza']:.1f}% |
                | **Differenza** | **+{row['Differenza']:.1f}%** |
                | p-value | {row['p_value']:.4f} |
                | Cohen's d | {row['Cohens_d']:.3f} |
                | Significatività | {row['Sig_Text']} |
                | Dimensione effetto | {row['Effect_Size']} |
                """)

            with col2:
                # Mini grafico confronto
                fig_mini = go.Figure()
                fig_mini.add_trace(go.Bar(
                    x=['Con', 'Senza'],
                    y=[row['Media_Con'], row['Media_Senza']],
                    marker_color=['#27ae60', '#95a5a6'],
                    text=[f"{row['Media_Con']:.1f}%", f"{row['Media_Senza']:.1f}%"],
                    textposition='outside'
                ))
                fig_mini.update_layout(
                    height=200,
                    margin=dict(l=20, r=20, t=20, b=20),
                    yaxis_range=[0, 100],
                    showlegend=False
                )
                st.plotly_chart(fig_mini, use_container_width=True)

st.markdown("---")

# === TABELLA COMPLETA ===
st.subheader("📋 Tabella Completa")

display_df = impact_df[[
    'Metodologia', 'N_Con', 'N_Senza', 'Media_Con', 'Media_Senza',
    'Differenza', 'p_value', 'Cohens_d', 'Significativita', 'Effect_Size'
]].copy()

display_df.columns = [
    'Metodologia', 'N Con', 'N Senza', 'Media Con', 'Media Senza',
    'Differenza', 'p-value', "Cohen's d", 'Sig.', 'Effetto'
]

# Formatta numeri
display_df['Media Con'] = display_df['Media Con'].map('{:.1f}%'.format)
display_df['Media Senza'] = display_df['Media Senza'].map('{:.1f}%'.format)
display_df['Differenza'] = display_df['Differenza'].map('{:+.1f}%'.format)
display_df['p-value'] = display_df['p-value'].apply(lambda x: f"{x:.4f}" if x >= 0.0001 else "<0.0001")
display_df["Cohen's d"] = display_df["Cohen's d"].round(3)

st.dataframe(display_df, use_container_width=True, hide_index=True)

# Download
csv = display_df.to_csv(index=False)
st.download_button(
    label="📥 Scarica CSV",
    data=csv,
    file_name="impatto_metodologie.csv",
    mime="text/csv"
)

st.markdown("---")

# === ANALISI CORRELAZIONI ===
st.subheader("🔗 Correlazione tra Numero di Metodologie e Indice di Completezza")

# Conta metodologie per scuola
method_counts = []
for idx, row in df.iterrows():
    school_id = row.get('school_id', '')
    md_files = glob.glob(f'{ANALYSIS_DIR}/*{school_id}*_analysis.md')

    if md_files:
        try:
            with open(md_files[0], 'r', encoding='utf-8') as f:
                content = f.read().upper()

            count = sum(1 for method in ALL_METHODOLOGIES if method.upper() in content)
            ro = row.get('ptof_orientamento_maturity_index', np.nan)

            if pd.notna(ro):
                method_counts.append({
                    'school_id': school_id,
                    'n_methods': count,
                    'ro': scale_to_pct(ro)
                })
        except Exception:
            pass

if method_counts:
    corr_df = pd.DataFrame(method_counts)

    # Correlazione
    correlation, corr_p = stats.pearsonr(corr_df['n_methods'], corr_df['ro'])

    col1, col2 = st.columns([2, 1])

    with col1:
        plot_args = {
            'data_frame': corr_df,
            'x': 'n_methods',
            'y': 'ro',
            'labels': {'n_methods': 'Numero di Metodologie', 'ro': 'Indice Completezza (%)'},
            'opacity': 0.6
        }
        
        if HAS_STATSMODELS:
            plot_args['trendline'] = 'ols'
            
        fig_corr = px.scatter(**plot_args)
        fig_corr.update_layout(height=400)
        st.plotly_chart(fig_corr, use_container_width=True)

    with col2:
        st.metric("Correlazione (r)", f"{correlation:.3f}")
        st.metric("p-value", f"{corr_p:.4f}" if corr_p >= 0.0001 else "<0.0001")

        if corr_p < 0.05:
            if correlation > 0.5:
                st.success("Correlazione positiva forte e significativa")
            elif correlation > 0.3:
                st.success("Correlazione positiva moderata e significativa")
            elif correlation > 0:
                st.info("Correlazione positiva debole ma significativa")
            else:
                st.warning("Correlazione negativa")
        else:
            st.info("Correlazione non statisticamente significativa")
            
        if not HAS_STATSMODELS:
            st.caption("Nota: Installa 'statsmodels' per vedere la linea di tendenza (trendline).")

render_footer()
