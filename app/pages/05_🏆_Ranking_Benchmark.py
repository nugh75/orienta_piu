# 🏆 Ranking & Benchmark - Classifiche + Indicatori Statistici
# Accorpa: 03_Benchmark + 04_Indicatori_Statistici

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from scipy import stats
from app.data_utils import GESTIONE_SCUOLA, TIPI_SCUOLA, normalize_statale_paritaria

st.set_page_config(page_title="ORIENTA+ | Ranking & Benchmark", page_icon="🧭", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    .top-performer { background-color: #d4edda !important; border-left-color: #28a745 !important; }
    .bottom-performer { background-color: #f8d7da !important; border-left-color: #dc3545 !important; }
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità',
    'ptof_orientamento_maturity_index': 'Indice RO',
    'partnership_count': 'N. Partnership'
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

# === STATISTICAL FUNCTIONS ===
def chi2_test_presence(df, group_col, presence_col):
    """Test Chi-quadrato per la presenza della sezione dedicata tra gruppi."""
    try:
        contingency = pd.crosstab(df[group_col], df[presence_col])
        if contingency.shape[1] < 2 or contingency.shape[0] < 2:
            return None, None, None
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        n = contingency.sum().sum()
        min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0
        return p_value, cramers_v, chi2
    except:
        return None, None, None

def kruskal_test_scores(df, group_col, score_col):
    """Test Kruskal-Wallis per confrontare i punteggi tra gruppi."""
    try:
        groups = [group[score_col].dropna().values for name, group in df.groupby(group_col)]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            return None, None
        stat, p_value = stats.kruskal(*groups)
        n = sum(len(g) for g in groups)
        eta_sq = (stat - len(groups) + 1) / (n - len(groups)) if n > len(groups) else 0
        eta_sq = max(0, min(1, eta_sq))
        return p_value, eta_sq
    except:
        return None, None

def interpret_effect_size(value, test_type='cramers_v'):
    """Interpreta l'effect size."""
    if value is None:
        return "N/D", "gray"
    if test_type == 'cramers_v':
        if value < 0.1:
            return "Trascurabile", "gray"
        elif value < 0.3:
            return "Piccolo", "orange"
        elif value < 0.5:
            return "Medio", "blue"
        else:
            return "Grande", "green"
    else:
        if value < 0.01:
            return "Trascurabile", "gray"
        elif value < 0.06:
            return "Piccolo", "orange"
        elif value < 0.14:
            return "Medio", "blue"
        else:
            return "Grande", "green"

def format_significance(p_value):
    """Formatta la significatività."""
    if p_value is None:
        return "N/D", "gray"
    if p_value < 0.001:
        return "p < 0.001 ***", "green"
    elif p_value < 0.01:
        return f"p = {p_value:.3f} **", "green"
    elif p_value < 0.05:
        return f"p = {p_value:.3f} *", "orange"
    else:
        return f"p = {p_value:.3f} (n.s.)", "gray"

# === DATA LOADING ===
@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        return df
    return pd.DataFrame()

df = load_data()

# === PAGE HEADER ===
st.title("🏆 Ranking & Benchmark")
st.markdown("Classifiche, confronti e indicatori statistici avanzati")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina ti permette di **confrontare le scuole** tra loro, identificando le migliori pratiche (benchmark)
    e posizionando ogni istituto rispetto al gruppo di riferimento.

    ### 📊 Sezioni Disponibili

    **🥇 Best-in-Class per Tipologia**
    - Mostra la **scuola migliore** per ogni tipo (Liceo, Tecnico, ecc.)
    - Utile per identificare modelli da seguire nel proprio settore

    **🏅 Top 10 vs Bottom 10**
    - Classifica delle 10 scuole con i punteggi più alti e più bassi
    - Permette di capire il divario tra eccellenze e criticità

    **📍 Posizionamento Percentile**
    - Ogni scuola ha un **percentile** che indica la sua posizione relativa
    - Es: \"75° percentile\" = la scuola supera il 75% delle altre

    **🕸️ Radar Chart (Confronto Profili)**
    - Visualizza il **profilo multidimensionale** di più scuole
    - Le aree colorate rappresentano le 5 dimensioni valutate
    - Più l'area è ampia, migliore è la scuola in quella dimensione

    **📐 Quadrante Performance**
    - Divide le scuole in **4 categorie strategiche**:
      - 🌟 **Alto-Alto**: Eccellenza (alte performance, alta robustezza)
      - ⚠️ **Alto-Basso**: Potenziale (alta robustezza, basse performance specifiche)
      - 🔍 **Basso-Alto**: Da monitorare (bassa robustezza, alte performance specifiche)
      - ❌ **Basso-Basso**: Criticità (necessita intervento)

    ### 🔢 Come Interpretare i Numeri
    - **Indice RO (1-7)**: Punteggio complessivo di Robustezza dell'Orientamento
    - **Percentile**: Posizione relativa (più alto = meglio)
    - **Δ dalla media**: Quanto la scuola si discosta dalla media del gruppo
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Standardize numeric columns
numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi',
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
                'partnership_count', 'activities_count']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

# Filter valid data
df_valid = df[df['ptof_orientamento_maturity_index'].notna() & (df['ptof_orientamento_maturity_index'] > 0)].copy()

if len(df_valid) == 0:
    st.warning("⚠️ Nessuna scuola con Indice RO valido.")
    st.stop()

# === TABS ===
tab_classifiche, tab_statistiche = st.tabs(["🏅 Classifiche & Benchmark", "📊 Indicatori Statistici"])

# ============================================================================
# TAB 1: CLASSIFICHE & BENCHMARK
# ============================================================================
with tab_classifiche:
    st.header("🏅 Classifiche e Benchmark")

    with st.expander("📖 Come leggere questa sezione", expanded=False):
        st.markdown("""
        ### 🎯 Scopo della Pagina
        Questa pagina ti permette di **confrontare le scuole** tra loro, identificando le migliori pratiche (benchmark) e posizionando ogni istituto rispetto al gruppo di riferimento.

        ### 📊 Sezioni Disponibili

        **🥇 Best-in-Class per Tipologia**
        - Mostra la **scuola migliore** per ogni tipo (Liceo, Tecnico, ecc.)
        - Utile per identificare modelli da seguire nel proprio settore

        **🏅 Top 10 vs Bottom 10**
        - Classifica delle 10 scuole con i punteggi più alti e più bassi
        - Permette di capire il divario tra eccellenze e criticità

        **📍 Posizionamento Percentile**
        - Ogni scuola ha un **percentile** che indica la sua posizione relativa
        - Es: "75° percentile" = la scuola supera il 75% delle altre

        **🕸️ Radar Chart (Confronto Profili)**
        - Visualizza il **profilo multidimensionale** di più scuole
        - Le aree colorate rappresentano le 5 dimensioni valutate
        - Più l'area è ampia, migliore è la scuola in quella dimensione

        **📐 Quadrante Performance**
        - Divide le scuole in **4 categorie strategiche**:
          - 🌟 **Alto-Alto**: Eccellenza (alte performance, alta robustezza)
          - ⚠️ **Alto-Basso**: Potenziale (alta robustezza, basse performance specifiche)
          - 🔍 **Basso-Alto**: Da monitorare (bassa robustezza, alte performance specifiche)
          - ❌ **Basso-Basso**: Criticità (necessita intervento)

        ### 🔢 Come Interpretare i Numeri
        - **Indice RO (1-7)**: Punteggio complessivo di Robustezza dell'Orientamento
        - **Percentile**: Posizione relativa (più alto = meglio)
        - **Δ dalla media**: Quanto la scuola si discosta dalla media del gruppo
        """)

    st.markdown("---")

    # === 0. SINTESI STATALE/PARITARIA ===
    st.subheader("🏛️ Statali vs Paritarie (sintesi)")
    st.caption("Richiamo rapido; analisi completa nel tab 'Indicatori Statistici'")

    if 'statale_paritaria' in df_valid.columns:
        df_sp_summary = df_valid.copy()
        df_sp_summary['gestione'] = df_sp_summary['statale_paritaria'].apply(normalize_statale_paritaria)
        counts = df_sp_summary['gestione'].value_counts()
        df_sp_summary = df_sp_summary[df_sp_summary['gestione'].isin(GESTIONE_SCUOLA)]

        if not df_sp_summary.empty:
            statali = df_sp_summary[df_sp_summary['gestione'] == 'Statale']
            paritarie = df_sp_summary[df_sp_summary['gestione'] == 'Paritaria']

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                pct_stat = (len(statali) / len(df_sp_summary) * 100) if len(df_sp_summary) > 0 else 0
                st.metric("Statali", f"{len(statali)} ({pct_stat:.1f}%)")
            with col_s2:
                pct_pari = (len(paritarie) / len(df_sp_summary) * 100) if len(df_sp_summary) > 0 else 0
                st.metric("Paritarie", f"{len(paritarie)} ({pct_pari:.1f}%)")
            with col_s3:
                if not statali.empty and not paritarie.empty:
                    diff = statali['ptof_orientamento_maturity_index'].mean() - paritarie['ptof_orientamento_maturity_index'].mean()
                    st.metric("Δ Media RO", f"{diff:+.2f}")
                else:
                    st.metric("Δ Media RO", "N/D")

            fig_sp = px.bar(
                df_sp_summary.groupby('gestione')['ptof_orientamento_maturity_index'].mean().reset_index(),
                x='gestione',
                y='ptof_orientamento_maturity_index',
                color='gestione',
                labels={'gestione': 'Gestione', 'ptof_orientamento_maturity_index': 'Indice RO Medio'},
                title="Indice RO Medio: Statali vs Paritarie"
            )
            fig_sp.update_layout(showlegend=False, height=300, yaxis_range=[0, 7])
            st.plotly_chart(fig_sp, use_container_width=True)

            extra = int(counts.get('ND', 0) + counts.get('Altro', 0))
            if extra > 0:
                st.warning(f"{extra} record non classificati in 'Statale/Paritaria' (ND o Altro).")
        else:
            st.info("Dati insufficienti per la sintesi statale/paritaria.")
    else:
        st.info("Colonna 'statale_paritaria' non disponibile nel dataset.")

    st.markdown("---")

    # === 1. BEST IN CLASS ===
    st.subheader("🥇 Best-in-Class per Tipologia")
    st.caption("Le migliori scuole per ciascuna tipologia scolastica")

    if 'tipo_scuola' in df_valid.columns:
        def get_primary_type(tipo):
            if pd.isna(tipo):
                return None
            for part in str(tipo).split(','):
                t = part.strip()
                if t in TIPI_SCUOLA:
                    return t
            return None

        df_valid['tipo_primario'] = df_valid['tipo_scuola'].apply(get_primary_type)
        tipi = [t for t in TIPI_SCUOLA if t in df_valid['tipo_primario'].dropna().unique()]

        if len(tipi) > 0:
            tabs = st.tabs(tipi)

            for i, tipo in enumerate(tipi):
                with tabs[i]:
                    df_tipo = df_valid[df_valid['tipo_primario'] == tipo].copy()
                    df_tipo = df_tipo.sort_values('ptof_orientamento_maturity_index', ascending=False)
                    top3 = df_tipo.head(3)

                    if len(top3) > 0:
                        cols = st.columns(min(3, len(top3)))
                        medals = ['🥇', '🥈', '🥉']

                        for j, (_, row) in enumerate(top3.iterrows()):
                            with cols[j]:
                                st.markdown(f"### {medals[j]} #{j+1}")
                                st.metric(
                                    label=row.get('denominazione', 'N/D')[:40],
                                    value=f"{row['ptof_orientamento_maturity_index']:.2f}/7"
                                )
                                st.caption(f"📍 {row.get('comune', 'N/D')} | {row.get('area_geografica', 'N/D')}")
                    else:
                        st.info(f"Nessuna scuola di tipo {tipo}")
        else:
            st.info("Nessuna tipologia disponibile")
    else:
        st.info("Colonna 'tipo_scuola' non disponibile")

    st.info("""
💡 **A cosa serve**: Identifica le scuole "campioni" per ogni tipologia (Liceo, Tecnico, ecc.), da usare come modelli di riferimento.

🔍 **Cosa rileva**: Le 3 scuole con l'Indice RO più alto in ciascuna categoria. Se una tipologia non ha medaglie, significa che mancano dati per quel tipo.

🎯 **Implicazioni**: Queste scuole hanno PTOF esemplari per l'orientamento. Puoi contattarle o studiare i loro documenti per replicare le buone pratiche nel tuo istituto.
""")

    st.markdown("---")

    # === 2. TOP vs BOTTOM ===
    st.subheader("📊 Top 10 vs Bottom 10")
    st.caption("Confronto tra le scuole con i punteggi più alti e più bassi")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔝 Top 10 Performers")
        top10 = df_valid.nlargest(10, 'ptof_orientamento_maturity_index')[
            ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
        ].copy()
        top10.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
        top10.insert(0, '#', range(1, len(top10) + 1))
        top10['Indice'] = top10['Indice'].round(2)
        st.dataframe(top10, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("### 🔻 Bottom 10 Performers")
        bottom10 = df_valid.nsmallest(10, 'ptof_orientamento_maturity_index')[
            ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
        ].copy()
        bottom10.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
        bottom10.insert(0, '#', range(1, len(bottom10) + 1))
        bottom10['Indice'] = bottom10['Indice'].round(2)
        st.dataframe(bottom10, use_container_width=True, hide_index=True)

    # Comparison chart
    st.markdown("### 📈 Visualizzazione Comparativa")
    comparison_df = pd.concat([
        top10.assign(Gruppo='Top 10'),
        bottom10.assign(Gruppo='Bottom 10')
    ])

    fig_compare = px.bar(
        comparison_df, x='Scuola', y='Indice', color='Gruppo',
        color_discrete_map={'Top 10': '#28a745', 'Bottom 10': '#dc3545'},
        title="Top 10 vs Bottom 10 - Indice RO",
        barmode='group'
    )
    fig_compare.update_layout(xaxis_tickangle=45, height=400)
    fig_compare.update_xaxes(tickfont_size=8)
    st.plotly_chart(fig_compare, use_container_width=True)

    st.info("""
💡 **A cosa serve**: Mostra il divario tra le scuole migliori e peggiori nel campione analizzato.

🔍 **Cosa rileva**: Le barre verdi sono le 10 scuole con punteggio più alto, quelle rosse le 10 con punteggio più basso. La differenza di altezza indica quanto è ampio il divario.

🎯 **Implicazioni**: Un divario grande suggerisce forti disparità nel sistema scolastico. Le scuole in rosso potrebbero necessitare di supporto o formazione specifica sull'orientamento.
""")

    st.markdown("---")

    # === 3. CLASSIFICA COMPLETA ===
    st.subheader("📋 Classifica Completa")
    st.caption("Tutte le scuole ordinate per Indice RO con le medie per dimensione")

    ranking_cols = ['denominazione', 'tipo_scuola', 'regione', 'area_geografica', 'ptof_orientamento_maturity_index']
    for col in dim_cols:
        if col in df_valid.columns:
            ranking_cols.append(col)

    df_ranking = df_valid[ranking_cols].copy()
    df_ranking = df_ranking.sort_values('ptof_orientamento_maturity_index', ascending=False)
    df_ranking.insert(0, 'Pos.', range(1, len(df_ranking) + 1))

    rename_map = {
        'denominazione': 'Scuola',
        'tipo_scuola': 'Tipo',
        'regione': 'Regione',
        'area_geografica': 'Area',
        'ptof_orientamento_maturity_index': 'Indice',
        'mean_finalita': 'Finalità',
        'mean_obiettivi': 'Obiettivi',
        'mean_governance': 'Governance',
        'mean_didattica_orientativa': 'Didattica',
        'mean_opportunita': 'Opportunità'
    }
    df_ranking = df_ranking.rename(columns=rename_map)

    numeric_display_cols = ['Indice', 'Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
    for col in numeric_display_cols:
        if col in df_ranking.columns:
            df_ranking[col] = df_ranking[col].round(2)

    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        if 'Tipo' in df_ranking.columns:
            tipi_filtro = ['Tutti'] + sorted(df_ranking['Tipo'].dropna().unique().tolist())
            tipo_sel = st.selectbox("Filtra per Tipo", tipi_filtro, key='ranking_tipo')
        else:
            tipo_sel = 'Tutti'

    with col_filter2:
        if 'Regione' in df_ranking.columns:
            regioni_filtro = ['Tutte'] + sorted(df_ranking['Regione'].dropna().unique().tolist())
            regione_sel = st.selectbox("Filtra per Regione", regioni_filtro, key='ranking_regione')
        else:
            regione_sel = 'Tutte'

    with col_filter3:
        if 'Area' in df_ranking.columns:
            aree_filtro = ['Tutte'] + sorted(df_ranking['Area'].dropna().unique().tolist())
            area_sel = st.selectbox("Filtra per Area", aree_filtro, key='ranking_area')
        else:
            area_sel = 'Tutte'

    df_ranking_filtered = df_ranking.copy()
    if tipo_sel != 'Tutti' and 'Tipo' in df_ranking_filtered.columns:
        df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Tipo'].str.contains(tipo_sel, na=False)]
    if regione_sel != 'Tutte' and 'Regione' in df_ranking_filtered.columns:
        df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Regione'] == regione_sel]
    if area_sel != 'Tutte' and 'Area' in df_ranking_filtered.columns:
        df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Area'] == area_sel]

    df_ranking_filtered = df_ranking_filtered.copy()
    df_ranking_filtered['Pos.'] = range(1, len(df_ranking_filtered) + 1)

    st.markdown(f"**{len(df_ranking_filtered)}** scuole nella selezione (su {len(df_ranking)} totali)")

    st.dataframe(
        df_ranking_filtered,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            'Pos.': st.column_config.NumberColumn('Pos.', width='small'),
            'Scuola': st.column_config.TextColumn('Scuola', width='large'),
            'Indice': st.column_config.ProgressColumn('Indice', min_value=0, max_value=7, format='%.2f'),
            'Finalità': st.column_config.ProgressColumn('Finalità', min_value=0, max_value=7, format='%.2f'),
            'Obiettivi': st.column_config.ProgressColumn('Obiettivi', min_value=0, max_value=7, format='%.2f'),
            'Governance': st.column_config.ProgressColumn('Governance', min_value=0, max_value=7, format='%.2f'),
            'Didattica': st.column_config.ProgressColumn('Didattica', min_value=0, max_value=7, format='%.2f'),
            'Opportunità': st.column_config.ProgressColumn('Opportunità', min_value=0, max_value=7, format='%.2f'),
        }
    )

    if len(df_ranking_filtered) > 0:
        with st.expander("📊 Statistiche della selezione"):
            stat_cols = ['Indice', 'Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
            stat_cols = [c for c in stat_cols if c in df_ranking_filtered.columns]

            stats_summary = df_ranking_filtered[stat_cols].describe().round(2)
            st.dataframe(stats_summary, use_container_width=True)

            col_best, col_worst = st.columns(2)
            with col_best:
                best = df_ranking_filtered.iloc[0]
                st.success(f"🥇 **Migliore**: {best['Scuola'][:40]} (Indice: {best['Indice']:.2f})")
            with col_worst:
                worst = df_ranking_filtered.iloc[-1]
                st.warning(f"🔻 **Ultimo**: {worst['Scuola'][:40]} (Indice: {worst['Indice']:.2f})")

    csv_data = df_ranking_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Scarica Classifica (CSV)",
        data=csv_data,
        file_name="classifica_scuole.csv",
        mime="text/csv"
    )

    st.info("""
💡 **A cosa serve**: Mostra la classifica completa di tutte le scuole ordinate per Indice RO, con possibilità di filtraggio.

🔍 **Cosa rileva**: Ogni riga è una scuola con posizione, dati anagrafici, indice complessivo e punteggi per ciascuna delle 5 dimensioni. Le barre di progresso visualizzano i valori. I filtri permettono di restringere la selezione.

🎯 **Implicazioni**: Usa questa classifica per identificare rapidamente le scuole migliori e peggiori nel tuo territorio o tipologia. Puoi esportare i dati in CSV per analisi personalizzate.
""")

    st.markdown("---")

    # === 4. POSIZIONAMENTO PERCENTILE ===
    st.subheader("📍 Posizionamento Percentile")
    st.caption("Scopri dove si posiziona una scuola rispetto alla distribuzione nazionale")

    if 'denominazione' in df_valid.columns:
        school_options = sorted(df_valid['denominazione'].dropna().unique().tolist())
        selected_school = st.selectbox("Seleziona una scuola", school_options, key="percentile_school")

        if selected_school:
            school_row = df_valid[df_valid['denominazione'] == selected_school].iloc[0]
            school_score = school_row['ptof_orientamento_maturity_index']

            all_scores = df_valid['ptof_orientamento_maturity_index'].dropna()
            percentile = (all_scores < school_score).sum() / len(all_scores) * 100

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Indice Robustezza", f"{school_score:.2f}/7")

            with col2:
                st.metric("Percentile", f"{percentile:.0f}°")
                if percentile >= 75:
                    st.success("🌟 Eccellente! Top 25%")
                elif percentile >= 50:
                    st.info("👍 Sopra la media")
                elif percentile >= 25:
                    st.warning("⚠️ Sotto la media")
                else:
                    st.error("❌ Bottom 25%")

            with col3:
                rank = int((all_scores >= school_score).sum())
                st.metric("Posizione in Classifica", f"{rank}/{len(all_scores)}")

            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=all_scores, nbinsx=20,
                name='Distribuzione',
                marker_color='#3498db',
                opacity=0.7
            ))
            fig_dist.add_vline(x=school_score, line_dash="dash", line_color="red", line_width=3)
            fig_dist.add_annotation(
                x=school_score, y=0,
                text=f"{selected_school[:20]}...",
                showarrow=True, arrowhead=2,
                yshift=100, xshift=20
            )
            fig_dist.update_layout(
                title="Posizione nella Distribuzione Nazionale",
                xaxis_title="Indice RO",
                yaxis_title="Frequenza",
                height=400
            )
            st.plotly_chart(fig_dist, use_container_width=True)
            st.info("""
💡 **A cosa serve**: Mostra dove si colloca una scuola rispetto a tutte le altre nel campione nazionale.

🔍 **Cosa rileva**: L'istogramma mostra quante scuole hanno ciascun punteggio. La linea rossa verticale indica la posizione della scuola selezionata. Se è a destra, la scuola è sopra la media.

🎯 **Implicazioni**: Un percentile alto (es. 80°) significa che la scuola supera l'80% degli altri istituti. Questo dato è utile per comunicare ai genitori e stakeholder la qualità dell'orientamento offerto.
""")

    st.markdown("---")

    # === 5. CONFRONTO MULTI-SCUOLA RADAR ===
    st.subheader("🎯 Confronto Multi-Scuola (Radar)")
    st.caption("Confronta fino a 5 scuole su tutte le dimensioni")

    if all(c in df_valid.columns for c in dim_cols):
        selected_schools = st.multiselect(
            "Seleziona fino a 5 scuole da confrontare",
            options=sorted(df_valid['denominazione'].dropna().unique().tolist()),
            max_selections=5,
            key="radar_schools"
        )

        if selected_schools:
            fig_radar = go.Figure()
            colors = px.colors.qualitative.Set1

            avg_values = [df_valid[c].mean() for c in dim_cols]
            avg_values.append(avg_values[0])
            labels = [get_label(c) for c in dim_cols]
            labels.append(labels[0])

            fig_radar.add_trace(go.Scatterpolar(
                r=avg_values,
                theta=labels,
                fill='toself',
                name='Media Nazionale',
                line_color='gray',
                opacity=0.3
            ))

            for i, school in enumerate(selected_schools):
                row = df_valid[df_valid['denominazione'] == school].iloc[0]
                values = [row[c] for c in dim_cols]
                values.append(values[0])

                fig_radar.add_trace(go.Scatterpolar(
                    r=values,
                    theta=labels,
                    fill='toself',
                    name=school[:30],
                    line_color=colors[i % len(colors)],
                    opacity=0.7
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                showlegend=True,
                title="Confronto Profili Scuole",
                height=550
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            comparison_data = []
            for school in selected_schools:
                row = df_valid[df_valid['denominazione'] == school].iloc[0]
                comparison_data.append({
                    'Scuola': school[:40],
                    **{get_label(c): f"{row[c]:.2f}" for c in dim_cols},
                    'Indice': f"{row['ptof_orientamento_maturity_index']:.2f}"
                })
            st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

            st.info("""
💡 **A cosa serve**: Confronta visivamente il "profilo" di più scuole sulle 5 dimensioni dell'orientamento.

🔍 **Cosa rileva**: L'area grigia è la media nazionale. Se il profilo colorato di una scuola "esce" dal grigio in una direzione, quella scuola eccelle in quella dimensione. Un profilo ampio e regolare indica equilibrio.

🎯 **Implicazioni**: Permette di identificare punti di forza e debolezza di ogni scuola. Utile per capire dove concentrare gli sforzi di miglioramento o quali aspetti valorizzare nella comunicazione.
""")
        else:
            st.info("Seleziona almeno una scuola per il confronto")
    else:
        st.warning("Dati delle dimensioni non disponibili")

    st.markdown("---")

    # === 6. QUADRANTE PERFORMANCE ===
    st.subheader("📐 Quadrante Performance")
    st.caption("Visualizzazione bidimensionale per classificare le scuole in 4 categorie strategiche")

    col1, col2 = st.columns(2)

    with col1:
        x_metric = st.selectbox(
            "Asse X",
            options=dim_cols + ['ptof_orientamento_maturity_index', 'partnership_count'],
            format_func=get_label,
            index=0,
            key="quad_x"
        )

    with col2:
        y_metric = st.selectbox(
            "Asse Y",
            options=dim_cols + ['ptof_orientamento_maturity_index', 'partnership_count'],
            format_func=get_label,
            index=2,
            key="quad_y"
        )

    if x_metric in df_valid.columns and y_metric in df_valid.columns:
        df_quad = df_valid[[x_metric, y_metric, 'denominazione', 'tipo_scuola', 'area_geografica']].dropna().copy()

        if len(df_quad) > 0:
            x_median = df_quad[x_metric].median()
            y_median = df_quad[y_metric].median()

            def get_quadrant(row):
                if row[x_metric] >= x_median and row[y_metric] >= y_median:
                    return '⭐ Eccellenti (Alto-Alto)'
                elif row[x_metric] < x_median and row[y_metric] >= y_median:
                    return '🎯 Focalizzati su Y'
                elif row[x_metric] >= x_median and row[y_metric] < y_median:
                    return '📈 Focalizzati su X'
                else:
                    return '⚠️ Da Migliorare'

            df_quad['Quadrante'] = df_quad.apply(get_quadrant, axis=1)

            fig_quad = px.scatter(
                df_quad, x=x_metric, y=y_metric,
                color='Quadrante',
                hover_name='denominazione',
                hover_data={'tipo_scuola': True, 'area_geografica': True},
                color_discrete_map={
                    '⭐ Eccellenti (Alto-Alto)': '#28a745',
                    '🎯 Focalizzati su Y': '#ffc107',
                    '📈 Focalizzati su X': '#17a2b8',
                    '⚠️ Da Migliorare': '#dc3545'
                },
                title=f"Quadrante: {get_label(x_metric)} vs {get_label(y_metric)}"
            )

            fig_quad.add_hline(y=y_median, line_dash="dash", line_color="gray", opacity=0.5)
            fig_quad.add_vline(x=x_median, line_dash="dash", line_color="gray", opacity=0.5)
            fig_quad.add_annotation(
                x=df_quad[x_metric].max(), y=df_quad[y_metric].max(),
                text="⭐ Eccellenti", showarrow=False, font=dict(size=12)
            )
            fig_quad.add_annotation(
                x=df_quad[x_metric].min(), y=df_quad[y_metric].min(),
                text="⚠️ Da Migliorare", showarrow=False, font=dict(size=12)
            )
            fig_quad.update_layout(height=550)
            st.plotly_chart(fig_quad, use_container_width=True)

            quad_counts = df_quad['Quadrante'].value_counts()
            col1, col2, col3, col4 = st.columns(4)
            quadrants = ['⭐ Eccellenti (Alto-Alto)', '🎯 Focalizzati su Y', '📈 Focalizzati su X', '⚠️ Da Migliorare']
            cols = [col1, col2, col3, col4]

            for q, c in zip(quadrants, cols):
                with c:
                    count = quad_counts.get(q, 0)
                    pct = count / len(df_quad) * 100
                    st.metric(q.split(' ')[0], f"{count} ({pct:.0f}%)")
            st.info("""
💡 **A cosa serve**: Classifica le scuole in 4 categorie strategiche incrociando due dimensioni a scelta.

🔍 **Cosa rileva**: Le linee tratteggiate dividono il grafico usando la mediana (valore centrale). ⭐ Eccellenti = sopra la media in entrambe le dimensioni. ⚠️ Da Migliorare = sotto la media in entrambe.

🎯 **Implicazioni**: Le scuole nel quadrante ⭐ sono modelli da seguire. Quelle in ⚠️ necessitano interventi prioritari. I quadranti intermedi indicano scuole con potenziale parziale da sviluppare.
""")
    else:
        st.warning("Metriche selezionate non disponibili")

    st.markdown("---")

    # === 7. BENCHMARK PER TIPOLOGIA ===
    st.subheader("📊 Benchmark per Tipologia")
    st.caption("Confronto delle medie per ciascuna tipologia scolastica")

    if 'tipo_primario' in df_valid.columns:
        tipo_stats = df_valid.groupby('tipo_primario').agg({
            'ptof_orientamento_maturity_index': ['mean', 'std', 'count'],
            **{c: 'mean' for c in dim_cols if c in df_valid.columns}
        }).round(2)

        tipo_stats.columns = ['_'.join(col).strip() for col in tipo_stats.columns.values]
        tipo_stats = tipo_stats.reset_index()

        fig_tipo = px.bar(
            tipo_stats, x='tipo_primario',
            y='ptof_orientamento_maturity_index_mean',
            error_y='ptof_orientamento_maturity_index_std',
            color='ptof_orientamento_maturity_index_mean',
            color_continuous_scale='RdYlGn',
            range_color=[1, 7],
            title="Indice RO Medio per Tipologia Scolastica",
            labels={'tipo_primario': 'Tipologia', 'ptof_orientamento_maturity_index_mean': 'Indice RO Medio'},
            text='ptof_orientamento_maturity_index_mean'
        )
        fig_tipo.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_tipo.update_layout(height=400)
        st.plotly_chart(fig_tipo, use_container_width=True)
        st.info("""
💡 **A cosa serve**: Confronta le performance medie tra le diverse tipologie scolastiche (Licei, Tecnici, Professionali, ecc.).

🔍 **Cosa rileva**: L'altezza delle barre indica il punteggio medio. Le barre di errore (linee verticali) mostrano la variabilità: più sono lunghe, più le scuole di quel tipo hanno risultati diversi tra loro.

🎯 **Implicazioni**: Tipologie con punteggi bassi potrebbero richiedere interventi mirati. Alta variabilità suggerisce che il tipo di scuola non è determinante: ci sono sia eccellenze che criticità.
""")
    else:
        st.info("Colonna 'tipo_primario' non disponibile")


# ============================================================================
# TAB 2: INDICATORI STATISTICI
# ============================================================================
with tab_statistiche:
    st.header("📊 KPI Avanzati e Statistiche")

    with st.expander("ℹ️ Cosa sono i KPI?"):
        st.markdown("""
        **KPI** sta per **Key Performance Indicators** (Indicatori Chiave di Prestazione). 
        In questa dashboard, rappresentano le metriche fondamentali per valutare la qualità dell'orientamento nei PTOF analizzati.

        Utilizziamo questi indicatori per:
        - Monitorare l'andamento generale (es. punteggi medi).
        - Identificare eccellenze o criticità (outliers).
        - Confrontare le performance tra diverse categorie (regioni, tipi di scuola).
        """)

    st.markdown("---")

    # === 1. KPI DASHBOARD ===
    st.subheader("📈 Dashboard KPI Estesa")
    st.caption("Indicatori chiave con statistiche avanzate")

    # Row 1
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("🏫 Totale Scuole", len(df_valid))

    with col2:
        mean_idx = df_valid['ptof_orientamento_maturity_index'].mean()
        st.metric("📊 Media Indice RO", f"{mean_idx:.2f}", help="Indice di Robustezza dell'Orientamento")

    with col3:
        median_idx = df_valid['ptof_orientamento_maturity_index'].median()
        st.metric("📍 Mediana", f"{median_idx:.2f}")

    with col4:
        std_idx = df_valid['ptof_orientamento_maturity_index'].std()
        st.metric("📐 Dev. Standard", f"{std_idx:.2f}")

    with col5:
        cv = (std_idx / mean_idx * 100) if mean_idx > 0 else 0
        st.metric("📉 Coeff. Variazione", f"{cv:.1f}%")

    # Row 2
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        q1 = df_valid['ptof_orientamento_maturity_index'].quantile(0.25)
        st.metric("Q1 (25°)", f"{q1:.2f}")

    with col2:
        q3 = df_valid['ptof_orientamento_maturity_index'].quantile(0.75)
        st.metric("Q3 (75°)", f"{q3:.2f}")

    with col3:
        iqr = q3 - q1
        st.metric("IQR", f"{iqr:.2f}")

    with col4:
        min_val = df_valid['ptof_orientamento_maturity_index'].min()
        st.metric("Min", f"{min_val:.2f}")

    with col5:
        max_val = df_valid['ptof_orientamento_maturity_index'].max()
        st.metric("Max", f"{max_val:.2f}")

    # Row 3: Coverage
    st.markdown("### 📋 Metriche di Copertura")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if 'has_sezione_dedicata' in df_valid.columns:
            sez_pct = df_valid['has_sezione_dedicata'].sum() / len(df_valid) * 100
            st.metric("% Sez. Dedicata", f"{sez_pct:.0f}%")
        else:
            st.metric("% Sez. Dedicata", "N/D")

    with col2:
        if 'partnership_count' in df_valid.columns:
            has_partner = (df_valid['partnership_count'] > 0).sum() / len(df_valid) * 100
            st.metric("% Con Partnership", f"{has_partner:.0f}%")
        else:
            st.metric("% Con Partnership", "N/D")

    with col3:
        above_mid = (df_valid['ptof_orientamento_maturity_index'] > 4).sum() / len(df_valid) * 100
        st.metric("% Sopra Sufficienza", f"{above_mid:.0f}%")

    with col4:
        excellence = (df_valid['ptof_orientamento_maturity_index'] >= 5).sum() / len(df_valid) * 100
        st.metric("% Eccellenza (≥5)", f"{excellence:.0f}%")

    st.info("""
💡 **A cosa serve**: Fornisce una panoramica sintetica delle statistiche principali sull'Indice di Robustezza dell'Orientamento (RO) delle scuole analizzate.

🔍 **Cosa rileva**: Media, mediana, deviazione standard e coefficiente di variazione descrivono la distribuzione centrale e la dispersione dei punteggi. I quartili (Q1, Q3) e l'IQR mostrano come si distribuisce il 50% centrale delle scuole. Le metriche di copertura indicano quante scuole hanno elementi chiave come sezione dedicata o partnership.

🎯 **Implicazioni**: Un coefficiente di variazione alto indica forte eterogeneità tra scuole. Una bassa percentuale di "Eccellenza" suggerisce ampio margine di miglioramento. Usa questi dati per contestualizzare le analisi successive.
""")

    st.markdown("---")

    # === 2. OUTLIER DETECTION ===
    st.subheader("🔍 Rilevamento Outlier")
    st.caption("Identificazione di scuole con punteggi anomali (eccellenti o critici)")

    q1 = df_valid['ptof_orientamento_maturity_index'].quantile(0.25)
    q3 = df_valid['ptof_orientamento_maturity_index'].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    df_valid['outlier_type'] = 'Normale'
    df_valid.loc[df_valid['ptof_orientamento_maturity_index'] > upper_bound, 'outlier_type'] = '🌟 Eccellente'
    df_valid.loc[df_valid['ptof_orientamento_maturity_index'] < lower_bound, 'outlier_type'] = '⚠️ Critico'

    outlier_stats = df_valid['outlier_type'].value_counts()

    col1, col2, col3 = st.columns(3)

    with col1:
        n_excellent = outlier_stats.get('🌟 Eccellente', 0)
        st.metric("🌟 Outlier Eccellenti", n_excellent, help=f"Scuole con indice > {upper_bound:.2f}")

    with col2:
        n_normal = outlier_stats.get('Normale', 0)
        st.metric("✅ Nella Norma", n_normal)

    with col3:
        n_critical = outlier_stats.get('⚠️ Critico', 0)
        st.metric("⚠️ Outlier Critici", n_critical, help=f"Scuole con indice < {lower_bound:.2f}")

    fig_outlier = px.box(
        df_valid, y='ptof_orientamento_maturity_index',
        points='all',
        color='outlier_type',
        color_discrete_map={
            '🌟 Eccellente': '#28a745',
            'Normale': '#3498db',
            '⚠️ Critico': '#dc3545'
        },
        title="Distribuzione con Outlier Evidenziati",
        hover_data=['denominazione', 'tipo_scuola']
    )
    fig_outlier.update_layout(height=400)
    st.plotly_chart(fig_outlier, use_container_width=True)

    # Show outlier details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌟 Scuole Eccellenti (Outlier Positivi)")
        excellent_df = df_valid[df_valid['outlier_type'] == '🌟 Eccellente'][
            ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
        ].copy()
        if len(excellent_df) > 0:
            excellent_df.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
            excellent_df = excellent_df.sort_values('Indice', ascending=False)
            st.dataframe(excellent_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun outlier eccellente rilevato")

    with col2:
        st.markdown("### ⚠️ Scuole Critiche (Outlier Negativi)")
        critical_df = df_valid[df_valid['outlier_type'] == '⚠️ Critico'][
            ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
        ].copy()
        if len(critical_df) > 0:
            critical_df.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
            critical_df = critical_df.sort_values('Indice', ascending=True)
            st.dataframe(critical_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun outlier critico rilevato")

    st.info("""
💡 **A cosa serve**: Identifica le scuole con punteggi "anomali" rispetto alla distribuzione generale, sia in positivo (eccellenti) che in negativo (critici).

🔍 **Cosa rileva**: Usando il metodo IQR (Interquartile Range), classifica come "outlier eccellente" chi supera Q3+1.5×IQR e come "outlier critico" chi scende sotto Q1-1.5×IQR. Il box plot visualizza la distribuzione con i punti colorati per categoria.

🎯 **Implicazioni**: Le scuole eccellenti sono potenziali modelli da studiare e replicare. Le scuole critiche potrebbero necessitare di interventi prioritari. Se non ci sono outlier, la distribuzione è omogenea.
""")

    st.markdown("---")

    # === 3. DISTRIBUTION ANALYSIS ===
    st.subheader("📉 Analisi Distribuzione")
    st.caption("Visualizzazione della distribuzione dei punteggi")

    col1, col2 = st.columns(2)

    with col1:
        fig_hist = px.histogram(
            df_valid, x='ptof_orientamento_maturity_index',
            nbins=20, marginal='box',
            color_discrete_sequence=['#3498db'],
            title="Distribuzione Indice RO"
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        if all(c in df_valid.columns for c in dim_cols):
            dim_data = []
            for c in dim_cols:
                for val in df_valid[c].dropna():
                    dim_data.append({'Dimensione': get_label(c), 'Punteggio': val})

            dim_df = pd.DataFrame(dim_data)

            fig_violin = px.violin(
                dim_df, x='Dimensione', y='Punteggio',
                box=True, points='outliers',
                color='Dimensione',
                title="Distribuzione per Dimensione"
            )
            fig_violin.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_violin, use_container_width=True)

    st.info("""
💡 **A cosa serve**: Mostra la forma della distribuzione dei punteggi, evidenziando concentrazioni e code.

🔍 **Cosa rileva**: L'istogramma a sinistra mostra quante scuole cadono in ogni fascia di punteggio. Il violin plot a destra confronta la distribuzione di ciascuna delle 5 dimensioni: la larghezza indica la densità, il box interno mostra mediana e quartili.

🎯 **Implicazioni**: Una distribuzione bimodale (due picchi) suggerisce gruppi distinti di scuole. Dimensioni con distribuzioni più strette indicano omogeneità; quelle più ampie indicano forte variabilità.
""")

    st.markdown("---")

    # === 4. REGRESSION ANALYSIS ===
    st.subheader("📈 Analisi Regressione")
    st.caption("Identificazione dei migliori predittori dell'Indice RO (Robustezza Orientamento)")

    try:
        from sklearn.linear_model import LinearRegression

        if all(c in df_valid.columns for c in dim_cols):
            X = df_valid[dim_cols].dropna()
            y = df_valid.loc[X.index, 'ptof_orientamento_maturity_index']

            if len(X) >= 10:
                model = LinearRegression()
                model.fit(X, y)

                coef_df = pd.DataFrame({
                    'Dimensione': [get_label(c) for c in dim_cols],
                    'Coefficiente': model.coef_,
                    'Importanza Relativa': np.abs(model.coef_) / np.abs(model.coef_).sum() * 100
                }).sort_values('Importanza Relativa', ascending=False)

                col1, col2 = st.columns([2, 1])

                with col1:
                    fig_coef = px.bar(
                        coef_df.sort_values('Importanza Relativa', ascending=True),
                        x='Importanza Relativa', y='Dimensione',
                        orientation='h',
                        color='Importanza Relativa',
                        color_continuous_scale='Blues',
                        title="Importanza Relativa delle Dimensioni",
                        text='Importanza Relativa'
                    )
                    fig_coef.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_coef.update_layout(height=350)
                    st.plotly_chart(fig_coef, use_container_width=True)

                with col2:
                    st.markdown("### 📊 Coefficienti")
                    st.dataframe(
                        coef_df[['Dimensione', 'Coefficiente']].round(3),
                        use_container_width=True,
                        hide_index=True
                    )
                    r2 = model.score(X, y)
                    st.metric("R² Score", f"{r2:.3f}")
            else:
                st.info("Servono almeno 10 scuole per l'analisi di regressione")
        else:
            st.warning("Colonne dimensioni non disponibili")

    except ImportError:
        st.warning("Installa scikit-learn per l'analisi di regressione: pip install scikit-learn")

    st.info("""
💡 **A cosa serve**: Identifica quali delle 5 dimensioni contribuiscono maggiormente all'Indice RO complessivo.

🔍 **Cosa rileva**: Un modello di regressione lineare calcola l'importanza relativa di ciascuna dimensione. I coefficienti indicano l'impatto: valori alti significano che quella dimensione "pesa" di più. L'R² indica quanto il modello spiega la variabilità totale.

🎯 **Implicazioni**: Se una dimensione ha alta importanza, migliorarla avrà forte impatto sull'indice complessivo. Dimensioni con bassa importanza potrebbero essere meno prioritarie negli interventi di miglioramento.
""")

    st.markdown("---")

    # === 5. SWOT PER TIPOLOGIA ===
    st.subheader("💡 Analisi SWOT per Tipologia")
    st.caption("Punti di forza e debolezza per ciascuna tipologia scolastica")

    if 'tipo_scuola' in df_valid.columns and all(c in df_valid.columns for c in dim_cols):
        def get_primary_type(tipo):
            if pd.isna(tipo):
                return None
            for part in str(tipo).split(','):
                t = part.strip()
                if t in TIPI_SCUOLA:
                    return t
            return None

        df_valid['tipo_primario'] = df_valid['tipo_scuola'].apply(get_primary_type)
        tipo_means = df_valid.groupby('tipo_primario')[dim_cols].mean()
        overall_means = df_valid[dim_cols].mean()

        tipi = [t for t in TIPI_SCUOLA if t in tipo_means.index]

        if len(tipi) > 0:
            selected_tipo = st.selectbox("Seleziona Tipologia", tipi, key="swot_tipo")

            if selected_tipo:
                tipo_vals = tipo_means.loc[selected_tipo]

                strengths = []
                weaknesses = []

                for dim in dim_cols:
                    diff = tipo_vals[dim] - overall_means[dim]
                    label = get_label(dim)

                    if diff > 0.3:
                        strengths.append((label, diff, tipo_vals[dim]))
                    elif diff < -0.3:
                        weaknesses.append((label, diff, tipo_vals[dim]))

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 💪 Punti di Forza")
                    if strengths:
                        for label, diff, val in sorted(strengths, key=lambda x: -x[1]):
                            st.success(f"**{label}**: {val:.2f} (+{diff:.2f} vs media)")
                    else:
                        st.info("Nessun punto di forza significativo rispetto alla media")

                with col2:
                    st.markdown("### ⚠️ Aree di Miglioramento")
                    if weaknesses:
                        for label, diff, val in sorted(weaknesses, key=lambda x: x[1]):
                            st.error(f"**{label}**: {val:.2f} ({diff:.2f} vs media)")
                    else:
                        st.info("Nessuna debolezza significativa rispetto alla media")

                # Radar comparison
                fig_swot = go.Figure()

                avg_vals = [overall_means[c] for c in dim_cols]
                avg_vals.append(avg_vals[0])
                labels = [get_label(c) for c in dim_cols]
                labels.append(labels[0])

                fig_swot.add_trace(go.Scatterpolar(
                    r=avg_vals, theta=labels,
                    fill='toself', name='Media Generale',
                    line_color='gray', opacity=0.5
                ))

                tipo_vls = [tipo_vals[c] for c in dim_cols]
                tipo_vls.append(tipo_vls[0])

                fig_swot.add_trace(go.Scatterpolar(
                    r=tipo_vls, theta=labels,
                    fill='toself', name=selected_tipo,
                    line_color='#3498db', opacity=0.7
                ))

                fig_swot.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                    title=f"Profilo {selected_tipo} vs Media Generale",
                    height=450
                )
                st.plotly_chart(fig_swot, use_container_width=True)
        else:
            st.info("Dati insufficienti per l'analisi SWOT")
    else:
        st.warning("Dati tipologia scuola non disponibili")

    st.info("""
💡 **A cosa serve**: Analizza punti di forza e debolezza di ciascuna tipologia scolastica (Licei, Tecnici, ecc.) rispetto alla media generale.

🔍 **Cosa rileva**: Per la tipologia selezionata, confronta ogni dimensione con la media nazionale. Differenze >+0.3 sono "Punti di Forza", <-0.3 sono "Aree di Miglioramento". Il radar sovrappone il profilo della tipologia (blu) alla media generale (grigio).

🎯 **Implicazioni**: Ogni tipologia ha caratteristiche distintive. I Licei potrebbero eccellere in una dimensione dove i Tecnici sono più deboli, e viceversa. Usa queste informazioni per interventi mirati per tipologia.
""")

    st.markdown("---")

    # === 5.5 SEZIONE DEDICATA ANALYSIS ===
    st.subheader("📑 Analisi Sezione Dedicata")
    st.caption("Approfondimento sulla presenza e qualità della sezione dedicata all'orientamento")

    if 'has_sezione_dedicata' in df_valid.columns and '2_1_score' in df_valid.columns:
        df_valid['has_sezione_dedicata'] = pd.to_numeric(df_valid['has_sezione_dedicata'], errors='coerce').fillna(0)
        df_valid['2_1_score'] = pd.to_numeric(df_valid['2_1_score'], errors='coerce').fillna(0)

        st.markdown("### 🌍 Analisi per Regione")

        if 'regione' in df_valid.columns:
            col_reg1, col_reg2 = st.columns(2)

            with col_reg1:
                st.markdown("#### 📊 Presenza Sezione")
                reg_stats = df_valid.groupby('regione')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
                reg_stats.columns = ['Regione', 'Totale', 'Con Sezione', 'Percentuale']
                reg_stats['Percentuale'] = reg_stats['Percentuale'] * 100
                reg_stats = reg_stats.sort_values('Percentuale', ascending=False)

                fig_reg_pres = px.bar(
                    reg_stats, x='Regione', y='Percentuale',
                    text=reg_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                    title="Percentuale Scuole con Sezione Dedicata per Regione",
                    color='Percentuale', color_continuous_scale='Greens'
                )
                fig_reg_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
                st.plotly_chart(fig_reg_pres, use_container_width=True)

                p_val_reg_pres, cramers_v_reg, _ = chi2_test_presence(df_valid, 'regione', 'has_sezione_dedicata')
                sig_text, sig_color = format_significance(p_val_reg_pres)
                eff_text, eff_color = interpret_effect_size(cramers_v_reg, 'cramers_v')
                st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
                if cramers_v_reg is not None:
                    st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_reg:.3f} - {eff_text}]")

            with col_reg2:
                st.markdown("#### ⭐ Punteggio Medio")
                df_with_sec = df_valid[df_valid['has_sezione_dedicata'] == 1]

                if not df_with_sec.empty:
                    score_reg = df_with_sec.groupby('regione')['2_1_score'].mean().reset_index()
                    score_reg = score_reg.sort_values('2_1_score', ascending=False)

                    fig_score_reg = px.bar(
                        score_reg, x='regione', y='2_1_score',
                        text=score_reg['2_1_score'].apply(lambda x: f'{x:.2f}'),
                        title="Punteggio Medio per Regione (solo scuole con sezione)",
                        color='2_1_score', color_continuous_scale='Viridis',
                        range_y=[0, 7]
                    )
                    fig_score_reg.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                    st.plotly_chart(fig_score_reg, use_container_width=True)

                    p_val_reg_score, eta_sq_reg = kruskal_test_scores(df_with_sec, 'regione', '2_1_score')
                    sig_text, sig_color = format_significance(p_val_reg_score)
                    eff_text, eff_color = interpret_effect_size(eta_sq_reg, 'eta_squared')
                    st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                    if eta_sq_reg is not None:
                        st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_reg:.3f} - {eff_text}]")
                else:
                    st.info("Nessuna scuola con sezione dedicata trovata")
        else:
            st.info("Dati 'regione' non disponibili")

        st.markdown("---")
        st.markdown("### 🏫 Analisi per Tipo Scuola")
        st.caption("Tipologie singole: Infanzia, Primaria, I Grado, Liceo, Tecnico, Professionale")

        if 'tipo_scuola' in df_valid.columns:
            rows = []
            for _, row in df_valid.iterrows():
                tipo = str(row['tipo_scuola'])
                tipi_singoli = [t.strip() for t in tipo.split(',')]
                for t in tipi_singoli:
                    new_row = row.copy()
                    new_row['tipo_singolo'] = t
                    rows.append(new_row)

            df_exploded = pd.DataFrame(rows)
            target_types = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']
            df_target = df_exploded[df_exploded['tipo_singolo'].isin(target_types)].copy()

            if not df_target.empty:
                col_tipo1, col_tipo2 = st.columns(2)

                with col_tipo1:
                    st.markdown("#### 📊 Presenza Sezione")
                    tipo_stats = df_target.groupby('tipo_singolo')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
                    tipo_stats.columns = ['Tipo', 'Totale', 'Con Sezione', 'Percentuale']
                    tipo_stats['Percentuale'] = tipo_stats['Percentuale'] * 100
                    tipo_stats = tipo_stats.sort_values('Percentuale', ascending=False)

                    fig_tipo_pres = px.bar(
                        tipo_stats, x='Tipo', y='Percentuale',
                        text=tipo_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                        title="Percentuale Scuole con Sezione Dedicata per Tipo",
                        color='Percentuale', color_continuous_scale='Blues'
                    )
                    fig_tipo_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
                    st.plotly_chart(fig_tipo_pres, use_container_width=True)

                    p_val_tipo_pres, cramers_v_tipo, _ = chi2_test_presence(df_target, 'tipo_singolo', 'has_sezione_dedicata')
                    sig_text, sig_color = format_significance(p_val_tipo_pres)
                    eff_text, eff_color = interpret_effect_size(cramers_v_tipo, 'cramers_v')
                    st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
                    if cramers_v_tipo is not None:
                        st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_tipo:.3f} - {eff_text}]")

                with col_tipo2:
                    st.markdown("#### ⭐ Punteggio Medio")
                    df_with_sec_tipo = df_target[df_target['has_sezione_dedicata'] == 1]

                    if not df_with_sec_tipo.empty:
                        score_tipo = df_with_sec_tipo.groupby('tipo_singolo')['2_1_score'].mean().reset_index()
                        score_tipo = score_tipo.sort_values('2_1_score', ascending=False)

                        fig_score_tipo = px.bar(
                            score_tipo, x='tipo_singolo', y='2_1_score',
                            text=score_tipo['2_1_score'].apply(lambda x: f'{x:.2f}'),
                            title="Punteggio Medio per Tipo (solo scuole con sezione)",
                            color='2_1_score', color_continuous_scale='Magma',
                            range_y=[0, 7]
                        )
                        fig_score_tipo.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                        st.plotly_chart(fig_score_tipo, use_container_width=True)

                        p_val_tipo_score, eta_sq_tipo = kruskal_test_scores(df_with_sec_tipo, 'tipo_singolo', '2_1_score')
                        sig_text, sig_color = format_significance(p_val_tipo_score)
                        eff_text, eff_color = interpret_effect_size(eta_sq_tipo, 'eta_squared')
                        st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                        if eta_sq_tipo is not None:
                            st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_tipo:.3f} - {eff_text}]")
                    else:
                        st.info("Nessuna scuola con sezione dedicata trovata")
            else:
                st.info("Nessuna scuola trovata per le tipologie specificate")
        else:
            st.info("Dati 'tipo_scuola' non disponibili")

        st.markdown("---")
        st.markdown("### 🎓 Analisi per Ordine e Grado")
        st.caption("Ordini singoli: Infanzia, Primaria, I Grado, II Grado")

        if 'ordine_grado' in df_valid.columns:
            rows_ord = []
            for _, row in df_valid.iterrows():
                ordine = str(row['ordine_grado'])
                ordini_singoli = [o.strip() for o in ordine.split(',')]
                for o in ordini_singoli:
                    new_row = row.copy()
                    new_row['ordine_singolo'] = o
                    rows_ord.append(new_row)

            df_exploded_ord = pd.DataFrame(rows_ord)
            target_ordini = ['Infanzia', 'Primaria', 'I Grado', 'II Grado']
            df_target_ord = df_exploded_ord[df_exploded_ord['ordine_singolo'].isin(target_ordini)].copy()

            if not df_target_ord.empty:
                col_ord1, col_ord2 = st.columns(2)

                with col_ord1:
                    st.markdown("#### 📊 Presenza Sezione")
                    ord_stats = df_target_ord.groupby('ordine_singolo')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
                    ord_stats.columns = ['Ordine', 'Totale', 'Con Sezione', 'Percentuale']
                    ord_stats['Percentuale'] = ord_stats['Percentuale'] * 100
                    ord_stats = ord_stats.sort_values('Percentuale', ascending=False)

                    fig_ord_pres = px.bar(
                        ord_stats, x='Ordine', y='Percentuale',
                        text=ord_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                        title="Percentuale Scuole con Sezione Dedicata per Ordine",
                        color='Percentuale', color_continuous_scale='Purples'
                    )
                    fig_ord_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
                    st.plotly_chart(fig_ord_pres, use_container_width=True)

                    p_val_ord_pres, cramers_v_ord, _ = chi2_test_presence(df_target_ord, 'ordine_singolo', 'has_sezione_dedicata')
                    sig_text, sig_color = format_significance(p_val_ord_pres)
                    eff_text, eff_color = interpret_effect_size(cramers_v_ord, 'cramers_v')
                    st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
                    if cramers_v_ord is not None:
                        st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_ord:.3f} - {eff_text}]")

                with col_ord2:
                    st.markdown("#### ⭐ Punteggio Medio")
                    df_with_sec_ord = df_target_ord[df_target_ord['has_sezione_dedicata'] == 1]

                    if not df_with_sec_ord.empty:
                        score_ord = df_with_sec_ord.groupby('ordine_singolo')['2_1_score'].mean().reset_index()
                        score_ord = score_ord.sort_values('2_1_score', ascending=False)

                        fig_score_ord = px.bar(
                            score_ord, x='ordine_singolo', y='2_1_score',
                            text=score_ord['2_1_score'].apply(lambda x: f'{x:.2f}'),
                            title="Punteggio Medio per Ordine (solo scuole con sezione)",
                            color='2_1_score', color_continuous_scale='Oranges',
                            range_y=[0, 7]
                        )
                        fig_score_ord.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                        st.plotly_chart(fig_score_ord, use_container_width=True)

                        p_val_ord_score, eta_sq_ord = kruskal_test_scores(df_with_sec_ord, 'ordine_singolo', '2_1_score')
                        sig_text, sig_color = format_significance(p_val_ord_score)
                        eff_text, eff_color = interpret_effect_size(eta_sq_ord, 'eta_squared')
                        st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                        if eta_sq_ord is not None:
                            st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_ord:.3f} - {eff_text}]")
                    else:
                        st.info("Nessuna scuola con sezione dedicata trovata")
            else:
                st.info("Nessun ordine trovato tra quelli specificati")
        else:
            st.info("Dati 'ordine_grado' non disponibili")

        st.markdown("---")
        st.markdown("### 📊 Impatto della Sezione Dedicata sull'Indice RO")
        st.caption("Confronto tra scuole con e senza sezione dedicata all'orientamento")

        if 'ptof_orientamento_maturity_index' in df_valid.columns:
            df_valid['has_sezione_label'] = df_valid['has_sezione_dedicata'].apply(
                lambda x: '✅ Con Sezione' if x == 1 else '❌ Senza Sezione'
            )

            col_ro1, col_ro2 = st.columns(2)

            with col_ro1:
                st.markdown("#### 📈 Distribuzione Indice RO")

                fig_ro_box = px.box(
                    df_valid, x='has_sezione_label', y='ptof_orientamento_maturity_index',
                    color='has_sezione_label',
                    color_discrete_map={'✅ Con Sezione': '#28a745', '❌ Senza Sezione': '#dc3545'},
                    title="Distribuzione Indice RO: Con vs Senza Sezione",
                    points='all'
                )
                fig_ro_box.update_layout(
                    yaxis_title="Indice RO",
                    xaxis_title="",
                    showlegend=False
                )
                st.plotly_chart(fig_ro_box, use_container_width=True)

            with col_ro2:
                st.markdown("#### 📊 Confronto Medie")

                mean_with = df_valid[df_valid['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].mean()
                mean_without = df_valid[df_valid['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].mean()
                n_with = (df_valid['has_sezione_dedicata'] == 1).sum()
                n_without = (df_valid['has_sezione_dedicata'] == 0).sum()

                comparison_df = pd.DataFrame({
                    'Gruppo': ['✅ Con Sezione', '❌ Senza Sezione'],
                    'Media RO': [mean_with, mean_without],
                    'N': [n_with, n_without]
                })

                fig_ro_bar = px.bar(
                    comparison_df, x='Gruppo', y='Media RO',
                    text=comparison_df['Media RO'].apply(lambda x: f'{x:.2f}'),
                    color='Gruppo',
                    color_discrete_map={'✅ Con Sezione': '#28a745', '❌ Senza Sezione': '#dc3545'},
                    title="Media Indice RO: Con vs Senza Sezione"
                )
                fig_ro_bar.update_layout(
                    yaxis_title="Media Indice RO",
                    xaxis_title="",
                    showlegend=False,
                    yaxis_range=[0, max(mean_with, mean_without) * 1.2]
                )
                st.plotly_chart(fig_ro_bar, use_container_width=True)

            st.markdown("#### 🔬 Test Statistico")

            group_with = df_valid[df_valid['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
            group_without = df_valid[df_valid['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
            p_value = None

            col_stat1, col_stat2, col_stat3 = st.columns(3)

            with col_stat1:
                diff = mean_with - mean_without
                diff_pct = (diff / mean_without * 100) if mean_without > 0 else 0
                st.metric(
                    "Differenza Media",
                    f"{diff:+.2f}",
                    delta=f"{diff_pct:+.1f}%",
                    delta_color="normal" if diff > 0 else "inverse"
                )

            with col_stat2:
                if len(group_with) >= 2 and len(group_without) >= 2:
                    stat, p_value = stats.mannwhitneyu(group_with, group_without, alternative='two-sided')
                    sig_text, sig_color = format_significance(p_value)
                    st.markdown("**Mann-Whitney U:**")
                    st.markdown(f":{sig_color}[{sig_text}]")
                else:
                    st.info("Dati insufficienti per il test")

            with col_stat3:
                if len(group_with) >= 2 and len(group_without) >= 2:
                    pooled_std = np.sqrt(((len(group_with)-1)*group_with.std()**2 +
                                          (len(group_without)-1)*group_without.std()**2) /
                                         (len(group_with) + len(group_without) - 2))
                    cohens_d = (mean_with - mean_without) / pooled_std if pooled_std > 0 else 0

                    if abs(cohens_d) < 0.2:
                        eff_text, eff_color = "Trascurabile", "gray"
                    elif abs(cohens_d) < 0.5:
                        eff_text, eff_color = "Piccolo", "orange"
                    elif abs(cohens_d) < 0.8:
                        eff_text, eff_color = "Medio", "blue"
                    else:
                        eff_text, eff_color = "Grande", "green"

                    st.markdown("**Cohen's d:**")
                    st.markdown(f":{eff_color}[{cohens_d:.3f} - {eff_text}]")
                else:
                    st.info("Dati insufficienti")

            if mean_with > mean_without and p_value is not None and p_value < 0.05:
                st.success(f"🎯 **Le scuole CON sezione dedicata hanno un Indice RO significativamente più alto** (+{diff:.2f} punti, +{diff_pct:.1f}%)")
            elif mean_with > mean_without:
                st.info(f"📊 Le scuole con sezione dedicata hanno un Indice RO più alto (+{diff:.2f}), ma la differenza non è statisticamente significativa.")
            elif mean_without > mean_with and p_value is not None and p_value < 0.05:
                st.warning(f"⚠️ Le scuole SENZA sezione dedicata hanno un Indice RO più alto ({-diff:.2f} punti)")
            else:
                st.info("📊 Non c'è una differenza significativa tra i due gruppi.")

        st.markdown("---")
        st.markdown("### 🏫 Confronto RO per Tipo Scuola (Con vs Senza Sezione)")

        if 'tipo_scuola' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
            rows_tipo = []
            for _, row in df_valid.iterrows():
                tipo = str(row['tipo_scuola'])
                tipi_singoli = [t.strip() for t in tipo.split(',')]
                for t in tipi_singoli:
                    new_row = row.copy()
                    new_row['tipo_singolo'] = t
                    rows_tipo.append(new_row)

            df_tipo_exp = pd.DataFrame(rows_tipo)
            target_types = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']
            df_tipo_exp = df_tipo_exp[df_tipo_exp['tipo_singolo'].isin(target_types)].copy()

            if not df_tipo_exp.empty:
                tipo_comparison = df_tipo_exp.groupby(['tipo_singolo', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
                tipo_comparison['Sezione'] = tipo_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')

                fig_tipo_comp = px.bar(
                    tipo_comparison, x='tipo_singolo', y='ptof_orientamento_maturity_index',
                    color='Sezione', barmode='group',
                    color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
                    text=tipo_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
                    title="Media Indice RO per Tipo Scuola: Con vs Senza Sezione"
                )
                fig_tipo_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
                st.plotly_chart(fig_tipo_comp, use_container_width=True)

                summary_tipo = []
                for tipo in target_types:
                    df_t = df_tipo_exp[df_tipo_exp['tipo_singolo'] == tipo]
                    group_con = df_t[df_t['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
                    group_senza = df_t[df_t['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
                    mean_con = group_con.mean() if len(group_con) > 0 else None
                    mean_senza = group_senza.mean() if len(group_senza) > 0 else None
                    n_con = len(group_con)
                    n_senza = len(group_senza)
                    diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None

                    p_val, cohens_d = None, None
                    if n_con >= 2 and n_senza >= 2:
                        try:
                            _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                            pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                            cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                        except Exception:
                            pass

                    sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
                    eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"

                    summary_tipo.append({
                        'Tipo': tipo,
                        'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                        'N Con': n_con,
                        'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                        'N Senza': n_senza,
                        'Diff.': f"{diff:+.2f}" if diff else "N/D",
                        'p-value': sig_text,
                        "Cohen's d": eff_text,
                        'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
                    })
                st.dataframe(pd.DataFrame(summary_tipo), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🌍 Confronto RO per Regione (Con vs Senza Sezione)")

        if 'regione' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
            reg_comparison = df_valid.groupby(['regione', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
            reg_comparison['Sezione'] = reg_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')

            fig_reg_comp = px.bar(
                reg_comparison, x='regione', y='ptof_orientamento_maturity_index',
                color='Sezione', barmode='group',
                color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
                text=reg_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
                title="Media Indice RO per Regione: Con vs Senza Sezione"
            )
            fig_reg_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
            st.plotly_chart(fig_reg_comp, use_container_width=True)

            summary_reg = []
            for regione in df_valid['regione'].dropna().unique():
                df_r = df_valid[df_valid['regione'] == regione]
                group_con = df_r[df_r['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
                group_senza = df_r[df_r['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
                mean_con = group_con.mean() if len(group_con) > 0 else None
                mean_senza = group_senza.mean() if len(group_senza) > 0 else None
                n_con = len(group_con)
                n_senza = len(group_senza)
                diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None

                p_val, cohens_d = None, None
                if n_con >= 2 and n_senza >= 2:
                    try:
                        _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                        pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                        cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                    except Exception:
                        pass

                sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
                eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"

                summary_reg.append({
                    'Regione': regione,
                    'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                    'N Con': n_con,
                    'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                    'N Senza': n_senza,
                    'Diff.': f"{diff:+.2f}" if diff else "N/D",
                    'p-value': sig_text,
                    "Cohen's d": eff_text,
                    'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
                })
            summary_reg_df = pd.DataFrame(summary_reg).sort_values('Regione')
            st.dataframe(summary_reg_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🎓 Confronto RO per Ordine e Grado (Con vs Senza Sezione)")

        if 'ordine_grado' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
            rows_ord = []
            for _, row in df_valid.iterrows():
                ordine = str(row['ordine_grado'])
                ordini_singoli = [o.strip() for o in ordine.split(',')]
                for o in ordini_singoli:
                    new_row = row.copy()
                    new_row['ordine_singolo'] = o
                    rows_ord.append(new_row)

            df_ord_exp = pd.DataFrame(rows_ord)
            target_ordini = ['Infanzia', 'Primaria', 'I Grado', 'II Grado']
            df_ord_exp = df_ord_exp[df_ord_exp['ordine_singolo'].isin(target_ordini)].copy()

            if not df_ord_exp.empty:
                ord_comparison = df_ord_exp.groupby(['ordine_singolo', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
                ord_comparison['Sezione'] = ord_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')

                fig_ord_comp = px.bar(
                    ord_comparison, x='ordine_singolo', y='ptof_orientamento_maturity_index',
                    color='Sezione', barmode='group',
                    color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
                    text=ord_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
                    title="Media Indice RO per Ordine: Con vs Senza Sezione"
                )
                fig_ord_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
                st.plotly_chart(fig_ord_comp, use_container_width=True)

                summary_ord = []
                for ordine in target_ordini:
                    df_o = df_ord_exp[df_ord_exp['ordine_singolo'] == ordine]
                    group_con = df_o[df_o['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
                    group_senza = df_o[df_o['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
                    mean_con = group_con.mean() if len(group_con) > 0 else None
                    mean_senza = group_senza.mean() if len(group_senza) > 0 else None
                    n_con = len(group_con)
                    n_senza = len(group_senza)
                    diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None

                    p_val, cohens_d = None, None
                    if n_con >= 2 and n_senza >= 2:
                        try:
                            _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                            pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                            cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                        except Exception:
                            pass

                    sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
                    eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"

                    summary_ord.append({
                        'Ordine': ordine,
                        'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                        'N Con': n_con,
                        'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                        'N Senza': n_senza,
                        'Diff.': f"{diff:+.2f}" if diff else "N/D",
                        'p-value': sig_text,
                        "Cohen's d": eff_text,
                        'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
                    })
                st.dataframe(pd.DataFrame(summary_ord), use_container_width=True, hide_index=True)

        st.markdown("---")
        with st.expander("ℹ️ Come interpretare i test statistici"):
            st.markdown("""
            **Test utilizzati:**
            - **Chi-quadrato (χ²)**: Verifica se la presenza della sezione dedicata varia significativamente tra gruppi (regioni, tipi, ordini).
            - **Kruskal-Wallis**: Verifica se i punteggi medi differiscono significativamente tra gruppi (test non parametrico).

            **Significatività (p-value):**
            - `***` p < 0.001: Differenza molto significativa
            - `**` p < 0.01: Differenza significativa
            - `*` p < 0.05: Differenza marginalmente significativa
            - `n.s.`: Non significativo (p ≥ 0.05)

            **Effect Size (dimensione dell'effetto):**
            - **Cramér's V** (per presenza): Trascurabile (<0.1), Piccolo (0.1-0.3), Medio (0.3-0.5), Grande (>0.5)
            - **η² (Eta-squared)** (per punteggi): Trascurabile (<0.01), Piccolo (0.01-0.06), Medio (0.06-0.14), Grande (>0.14)

            Un risultato significativo con effect size piccolo indica che, pur essendoci una differenza reale, questa ha un impatto pratico limitato.
            """)
    else:
        st.warning("Dati 'has_sezione_dedicata' o '2_1_score' non disponibili nel dataset")

    st.info("""
💡 **A cosa serve**: Analizza in profondità la presenza e qualità della "Sezione Dedicata all'Orientamento" nei PTOF, confrontando regioni, tipologie e ordini scolastici.

🔍 **Cosa rileva**: Per ogni categoria (regione, tipo scuola, ordine) mostra: percentuale di scuole con sezione dedicata, punteggio medio della sezione. I test statistici (Chi-quadrato, Kruskal-Wallis) verificano se le differenze sono significative. L'effect size indica l'impatto pratico.

🎯 **Implicazioni**: Una sezione dedicata all'orientamento è indicatore di attenzione specifica al tema. Regioni o tipologie con bassa presenza potrebbero necessitare di sensibilizzazione. Differenze nei punteggi suggeriscono dove la qualità è migliore.
""")

    st.markdown("---")

    # === 6. CORRELAZIONI ===
    st.subheader("🔗 Correlazioni Chiave")
    st.caption("Relazioni tra dimensioni e metriche")

    if all(c in df_valid.columns for c in dim_cols):
        corr_cols = dim_cols + ['ptof_orientamento_maturity_index']
        if 'partnership_count' in df_valid.columns:
            corr_cols.append('partnership_count')

        corr_matrix = df_valid[corr_cols].corr()

        corr_matrix.index = [get_label(c) for c in corr_matrix.index]
        corr_matrix.columns = [get_label(c) for c in corr_matrix.columns]

        fig_corr = px.imshow(
            corr_matrix,
            text_auto='.2f',
            color_continuous_scale='RdBu_r',
            range_color=[-1, 1],
            title="Matrice di Correlazione"
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)

        # Top correlations
        st.markdown("### 📊 Correlazioni più Forti")
        corr_pairs = []
        for i in range(len(corr_cols)):
            for j in range(i+1, len(corr_cols)):
                corr_pairs.append({
                    'Variabile 1': get_label(corr_cols[i]),
                    'Variabile 2': get_label(corr_cols[j]),
                    'Correlazione': corr_matrix.iloc[i, j]
                })

        corr_pairs_df = pd.DataFrame(corr_pairs)
        corr_pairs_df = corr_pairs_df.reindex(
            corr_pairs_df['Correlazione'].abs().sort_values(ascending=False).index
        ).head(5)
        st.dataframe(corr_pairs_df.round(3), use_container_width=True, hide_index=True)

    st.info("""
💡 **A cosa serve**: Mostra quali dimensioni e metriche sono correlate tra loro, rivelando relazioni sistematiche.

🔍 **Cosa rileva**: La heatmap visualizza le correlazioni: rosso=positiva (crescono insieme), blu=negativa (una cresce, l'altra cala). Valori vicini a ±1 indicano forte correlazione, vicini a 0 indicano indipendenza. La tabella elenca le 5 correlazioni più forti.

🎯 **Implicazioni**: Dimensioni fortemente correlate potrebbero avere cause comuni. Se vuoi migliorare una dimensione, potresti beneficiare anche in quelle correlate. Correlazioni deboli suggeriscono aspetti indipendenti da affrontare separatamente.
""")

    st.markdown("---")

    # === 7. CONFRONTO STATALE VS PARITARIA ===
    st.subheader("🏛️ Confronto Statale vs Paritaria")
    st.caption("Analisi statistica delle differenze tra scuole statali e paritarie")

    if 'statale_paritaria' in df_valid.columns:
        df_sp = df_valid.copy()
        df_sp['gestione'] = df_sp['statale_paritaria'].apply(normalize_statale_paritaria)
        counts = df_sp['gestione'].value_counts()
        df_sp = df_sp[df_sp['gestione'].isin(GESTIONE_SCUOLA)]

        if len(df_sp) > 10:
            statali = df_sp[df_sp['gestione'] == 'Statale']
            paritarie = df_sp[df_sp['gestione'] == 'Paritaria']

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### 🏫 Statali")
                st.metric("N. Scuole", len(statali))
                stat_mean = statali['ptof_orientamento_maturity_index'].mean()
                stat_std = statali['ptof_orientamento_maturity_index'].std()
                st.metric("Media Indice RO", f"{stat_mean:.2f}" if pd.notna(stat_mean) else "N/D")
                st.metric("Dev. Standard", f"{stat_std:.2f}" if pd.notna(stat_std) else "N/D")

            with col2:
                st.markdown("### 🏠 Paritarie")
                st.metric("N. Scuole", len(paritarie))
                pari_mean = paritarie['ptof_orientamento_maturity_index'].mean()
                pari_std = paritarie['ptof_orientamento_maturity_index'].std()
                st.metric("Media Indice RO", f"{pari_mean:.2f}" if pd.notna(pari_mean) else "N/D")
                st.metric("Dev. Standard", f"{pari_std:.2f}" if pd.notna(pari_std) else "N/D")

            with col3:
                st.markdown("### 📊 Test Statistico")
                from scipy.stats import mannwhitneyu, ttest_ind

                stat_vals = statali['ptof_orientamento_maturity_index'].dropna()
                pari_vals = paritarie['ptof_orientamento_maturity_index'].dropna()

                if len(stat_vals) >= 5 and len(pari_vals) >= 5:
                    t_stat, t_pval = ttest_ind(stat_vals, pari_vals)
                    u_stat, u_pval = mannwhitneyu(stat_vals, pari_vals, alternative='two-sided')

                    pooled_std = np.sqrt(((len(stat_vals)-1)*stat_vals.std()**2 + (len(pari_vals)-1)*pari_vals.std()**2) /
                                        (len(stat_vals) + len(pari_vals) - 2))
                    cohens_d = (stat_vals.mean() - pari_vals.mean()) / pooled_std if pooled_std > 0 else 0

                    sig_text, sig_color = format_significance(u_pval)
                    st.metric("Mann-Whitney p-value", sig_text)

                    effect_label = "Grande" if abs(cohens_d) >= 0.8 else "Medio" if abs(cohens_d) >= 0.5 else "Piccolo" if abs(cohens_d) >= 0.2 else "Trascurabile"
                    st.metric("Cohen's d", f"{cohens_d:.2f} ({effect_label})")

                    diff = stat_vals.mean() - pari_vals.mean()
                    st.metric("Δ Media", f"{diff:+.2f}")
                else:
                    st.info("Dati insufficienti per il test (servono almeno 5 scuole per gruppo).")

            fig_box = px.box(
                df_sp,
                x='gestione',
                y='ptof_orientamento_maturity_index',
                color='gestione',
                title="Distribuzione Indice RO: Statali vs Paritarie",
                labels={'gestione': 'Gestione', 'ptof_orientamento_maturity_index': 'Indice RO'}
            )
            fig_box.update_layout(showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)

            st.markdown("#### 📊 Confronto per Dimensione")

            dim_comparison = []
            for col in dim_cols:
                if col in df_sp.columns:
                    stat_mean = statali[col].mean()
                    pari_mean = paritarie[col].mean()
                    diff = stat_mean - pari_mean

                    stat_v = statali[col].dropna()
                    pari_v = paritarie[col].dropna()
                    if len(stat_v) >= 5 and len(pari_v) >= 5:
                        _, p_val = mannwhitneyu(stat_v, pari_v, alternative='two-sided')
                    else:
                        p_val = None

                    dim_comparison.append({
                        'Dimensione': get_label(col),
                        'Media Statali': stat_mean,
                        'Media Paritarie': pari_mean,
                        'Differenza': diff,
                        'p-value': p_val,
                        'Significativo': '✅' if p_val and p_val < 0.05 else '❌' if p_val else 'N/D'
                    })

            dim_df = pd.DataFrame(dim_comparison)

            fig_dim = go.Figure()
            fig_dim.add_trace(go.Bar(
                name='Statali',
                x=[d['Dimensione'] for d in dim_comparison],
                y=[d['Media Statali'] for d in dim_comparison],
                marker_color='steelblue'
            ))
            fig_dim.add_trace(go.Bar(
                name='Paritarie',
                x=[d['Dimensione'] for d in dim_comparison],
                y=[d['Media Paritarie'] for d in dim_comparison],
                marker_color='coral'
            ))
            fig_dim.update_layout(
                barmode='group',
                title="Media per Dimensione: Statali vs Paritarie",
                yaxis_range=[0, 7],
                yaxis_title="Punteggio Medio"
            )
            st.plotly_chart(fig_dim, use_container_width=True)

            st.dataframe(dim_df.round(2), use_container_width=True, hide_index=True)

            st.info("""
            💡 **A cosa serve**: Verifica se esistono differenze sistematiche tra scuole statali e paritarie nella qualità dell'orientamento.

            🔍 **Cosa rileva**: Il test Mann-Whitney confronta le distribuzioni. Cohen's d misura l'entità della differenza (>0.8 = grande, 0.5-0.8 = medio, 0.2-0.5 = piccolo).

            🎯 **Implicazioni**: Differenze significative potrebbero indicare risorse diverse, approcci pedagogici distinti o contesti operativi differenti.
            """)
            extra = int(counts.get('ND', 0) + counts.get('Altro', 0))
            if extra > 0:
                st.warning(f"{extra} record non classificati in 'Statale/Paritaria' (ND o Altro).")
        else:
            st.warning("Dati insufficienti per il confronto statale/paritaria.")
    else:
        st.warning("Colonna 'statale_paritaria' non presente nel dataset.")

# Footer
st.markdown("---")
st.caption("🏆 Benchmark - Dashboard PTOF | Analisi comparativa delle performance scolastiche")
st.caption("📊 KPI Avanzati - Dashboard PTOF | Statistiche approfondite e analisi degli outlier")
