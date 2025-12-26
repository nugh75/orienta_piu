# 🗺️ Analisi Territoriale - Mappa Italia + Confronti Gruppi + Report Regionali
# Accorpa: 01_Confronti_Gruppi + 02_Mappa_Italia + 15_Report_Regionali

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from io import BytesIO
from scipy import stats
from app.data_utils import normalize_statale_paritaria

st.set_page_config(page_title="ORIENTA+ | Analisi Territoriale", page_icon="🧭", layout="wide")

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
    'ptof_orientamento_maturity_index': 'Indice RO'
}

TIPI_SCUOLA = [
    "Infanzia",
    "Primaria",
    "I Grado",
    "Liceo",
    "Tecnico",
    "Professionale"
]

GESTIONE_SCUOLA = [
    "Statale",
    "Paritaria"
]

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

def get_primary_type(tipo):
    if pd.isna(tipo):
        return None
    for part in str(tipo).split(','):
        t = part.strip()
        if t in TIPI_SCUOLA:
            return t
    return None

def add_type_normalized_score(df, score_col='ptof_orientamento_maturity_index'):
    if score_col not in df.columns or 'tipo_scuola' not in df.columns:
        return df.copy()
    df_norm = df.copy()
    df_norm['tipo_primario'] = df_norm['tipo_scuola'].apply(get_primary_type)
    df_norm = df_norm[df_norm['tipo_primario'].isin(TIPI_SCUOLA)]
    if df_norm.empty:
        return df_norm
    overall_mean = df_norm[score_col].mean()
    type_means = df_norm.groupby('tipo_primario')[score_col].mean()
    df_norm['score_norm'] = df_norm[score_col] - df_norm['tipo_primario'].map(type_means) + overall_mean
    return df_norm

# Region to ISO codes for choropleth
REGION_ISO = {
    'Piemonte': 'IT-21', 'Valle d\'Aosta': 'IT-23', 'Lombardia': 'IT-25',
    'Trentino-Alto Adige': 'IT-32', 'Veneto': 'IT-34', 'Friuli Venezia Giulia': 'IT-36',
    'Liguria': 'IT-42', 'Emilia-Romagna': 'IT-45', 'Toscana': 'IT-52',
    'Umbria': 'IT-55', 'Marche': 'IT-57', 'Lazio': 'IT-62',
    'Abruzzo': 'IT-65', 'Molise': 'IT-67', 'Campania': 'IT-72',
    'Puglia': 'IT-75', 'Basilicata': 'IT-77', 'Calabria': 'IT-78',
    'Sicilia': 'IT-82', 'Sardegna': 'IT-88'
}

REGION_NORMALIZATION = {
    'Emilia Romagna': 'Emilia-Romagna',
    'Friuli-Venezia Giulia': 'Friuli Venezia Giulia',
    'Trentino Alto Adige': 'Trentino-Alto Adige',
    'Valle D\'Aosta': 'Valle d\'Aosta',
    'Valle d Aosta': 'Valle d\'Aosta',
}

MACRO_AREA = {
    'Piemonte': 'Nord', 'Valle d\'Aosta': 'Nord', 'Lombardia': 'Nord',
    'Trentino-Alto Adige': 'Nord', 'Veneto': 'Nord', 'Friuli Venezia Giulia': 'Nord',
    'Liguria': 'Nord', 'Emilia-Romagna': 'Nord',
    'Toscana': 'Nord', 'Umbria': 'Nord', 'Marche': 'Nord',
    'Abruzzo': 'Nord', 'Lazio': 'Sud',
    'Molise': 'Sud', 'Campania': 'Sud', 'Puglia': 'Sud',
    'Basilicata': 'Sud', 'Calabria': 'Sud', 'Sicilia': 'Sud', 'Sardegna': 'Sud'
}

REGION_COORDS = {
    'Piemonte': (45.0703, 7.6869), 'Valle d\'Aosta': (45.7388, 7.4262),
    'Lombardia': (45.4668, 9.1905), 'Trentino-Alto Adige': (46.4993, 11.3548),
    'Veneto': (45.4414, 12.3155), 'Friuli Venezia Giulia': (45.6495, 13.7768),
    'Liguria': (44.4056, 8.9463), 'Emilia-Romagna': (44.4949, 11.3426),
    'Toscana': (43.7711, 11.2486), 'Umbria': (42.9384, 12.6217),
    'Marche': (43.6169, 13.5188), 'Lazio': (41.9028, 12.4964),
    'Abruzzo': (42.3498, 13.3995), 'Molise': (41.5603, 14.6684),
    'Campania': (40.8518, 14.2681), 'Puglia': (41.1258, 16.8666),
    'Basilicata': (40.6395, 15.8053), 'Calabria': (38.9059, 16.5941),
    'Sicilia': (37.6000, 14.0154), 'Sardegna': (40.1209, 9.0129)
}

# === UTILITY FUNCTIONS ===
def split_multi_value(value):
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]

def explode_multi_value(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return df
    if not df[col].astype(str).str.contains(',').any():
        return df
    df_temp = df.copy()
    df_temp[col] = df_temp[col].apply(split_multi_value)
    return df_temp.explode(col)

def normalize_region(value):
    if pd.isna(value):
        return 'Non Specificato'
    value_str = str(value).strip()
    if value_str in ('', 'ND', 'N/A', 'nan'):
        return 'Non Specificato'
    if value_str in REGION_NORMALIZATION:
        return REGION_NORMALIZATION[value_str]
    return value_str

# === STATISTICAL FUNCTIONS ===
def cohens_d(group1, group2):
    """Calcola Cohen's d per due gruppi"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return np.nan
    var1, var2 = group1.var(), group2.var()
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    if pooled_std == 0:
        return np.nan
    return (group1.mean() - group2.mean()) / pooled_std

def interpret_cohens_d(d):
    """Interpreta il valore di Cohen's d"""
    if pd.isna(d):
        return "N/D", "⚪"
    d_abs = abs(d)
    if d_abs < 0.2:
        return "Trascurabile", "⚪"
    elif d_abs < 0.5:
        return "Piccolo", "🟡"
    elif d_abs < 0.8:
        return "Medio", "🟠"
    else:
        return "Grande", "🔴"

def interpret_pvalue(p):
    """Interpreta il p-value"""
    if pd.isna(p):
        return "N/D", "⚪"
    if p < 0.001:
        return "***", "🟢"
    elif p < 0.01:
        return "**", "🟢"
    elif p < 0.05:
        return "*", "🟡"
    else:
        return "n.s.", "⚪"

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

def dunn_posthoc(df, group_col, score_col):
    """Test post-hoc di Dunn con correzione Bonferroni."""
    from itertools import combinations
    try:
        groups_data = {}
        for name, group in df.groupby(group_col):
            values = group[score_col].dropna().values
            if len(values) >= 2:
                groups_data[name] = values
        if len(groups_data) < 2:
            return None
        group_names = list(groups_data.keys())
        n_comparisons = len(list(combinations(group_names, 2)))
        results = []
        for g1, g2 in combinations(group_names, 2):
            stat, p_val = stats.mannwhitneyu(
                groups_data[g1], groups_data[g2], alternative='two-sided'
            )
            p_adj = min(p_val * n_comparisons, 1.0)
            n1, n2 = len(groups_data[g1]), len(groups_data[g2])
            z = stats.norm.ppf(1 - p_val / 2) if p_val > 0 else 0
            r = abs(z) / np.sqrt(n1 + n2)
            mean1 = np.mean(groups_data[g1])
            mean2 = np.mean(groups_data[g2])
            results.append({
                'Gruppo 1': g1,
                'Gruppo 2': g2,
                'Media 1': round(mean1, 2),
                'Media 2': round(mean2, 2),
                'Diff': round(mean1 - mean2, 2),
                'p-value': round(p_val, 4),
                'p-adj (Bonf.)': round(p_adj, 4),
                'Effect (r)': round(r, 3),
                'Significativo': '✓' if p_adj < 0.05 else ''
            })
        return pd.DataFrame(results)
    except Exception:
        return None

def interpret_effect_size(value):
    """Interpreta l'effect size (eta-squared)."""
    if value is None:
        return "N/D", "gray"
    if value < 0.01:
        return "Trascurabile", "gray"
    elif value < 0.06:
        return "Piccolo", "orange"
    elif value < 0.14:
        return "Medio", "blue"
    else:
        return "Grande", "green"

def interpret_r_effect(r):
    """Interpreta l'effect size r."""
    if r is None:
        return "N/D"
    if r < 0.1:
        return "Trascurabile"
    elif r < 0.3:
        return "Piccolo"
    elif r < 0.5:
        return "Medio"
    else:
        return "Grande"

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
        numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi',
                        'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()

df = load_data()

# === PAGE HEADER ===
st.title("🗺️ Analisi Territoriale")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina integra **analisi geografiche e confronti statistici** per comprendere come varia
    la robustezza dell’orientamento tra territori, tipologie e regioni.

    ### 📊 Sezioni Disponibili
    **🗺️ Mappa Italia**
    - Distribuzione geografica dei punteggi
    - Hotspot di eccellenza e cluster territoriali
    - Analisi per regione e macro-area

    **📊 Confronti Gruppi**
    - Confronti tra area geografica, tipologia e territorio
    - Heatmap, radar comparativi, box plot
    - Significatività statistica ed effect size

    **📋 Report Regionali**
    - Report sintetici per USR
    - Statistiche chiave e confronto nazionale
    - Export in Excel/CSV
    """)
st.markdown("Confronti geografici, mappe e report regionali")

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Normalize regions
if 'regione' in df.columns:
    df['regione'] = df['regione'].apply(normalize_region)
else:
    df['regione'] = 'Non Specificato'

df['macro_area'] = df['regione'].map(MACRO_AREA).fillna('Non Specificato')
df_valid = df[df['ptof_orientamento_maturity_index'].notna()].copy()

# === TABS ===
tab_mappa, tab_confronti, tab_report = st.tabs(["🗺️ Mappa Italia", "📊 Confronti Gruppi", "📋 Report Regionali"])

# ============================================================================
# TAB 1: MAPPA ITALIA
# ============================================================================
with tab_mappa:
    st.header("🗺️ Mappa Italia - Analisi Geografica")

    with st.expander("📖 Come leggere questa sezione", expanded=False):
        st.markdown("""
        ### 🎯 Scopo
        Analizza la **distribuzione geografica** della qualità dell'orientamento nei PTOF italiani.

        ### 📊 Sezioni
        - **Confronto Regionale**: Media dell'Indice RO normalizzata per tipologia
        - **Test ANOVA**: Verifica statistica se le differenze tra regioni sono significative
        - **Mappa Coropletica**: Visualizzazione geografica dell'Indice RO
        - **Mappa Scuole Virtuose**: Localizza le scuole con i punteggi più alti
        - **Confronto Nord vs Sud**: Analisi delle macro-aree
        """)

    # Check for missing regions
    missing_region_rows = df[df['regione'] == 'Non Specificato']
    if not missing_region_rows.empty:
        st.error(f"⚠️ **Attenzione: {len(missing_region_rows)} scuole senza regione**")

        if 'comune' in df.columns:
            missing_comuni = sorted({
                str(comune).upper().strip()
                for comune in missing_region_rows['comune'].dropna().tolist()
                if str(comune).strip()
            })

            if missing_comuni:
                with st.expander(f"📋 Visualizza {len(missing_comuni)} comuni senza regione", expanded=True):
                    cols = st.columns(3)
                    for i, comune in enumerate(missing_comuni[:15]):
                        with cols[i % 3]:
                            st.code(comune)
                    if len(missing_comuni) > 15:
                        st.caption(f"... e altri {len(missing_comuni) - 15} comuni")

        st.info("Aggiorna i metadati rigenerando `data/analysis_summary.csv` dal workflow.")
        st.markdown("---")

    st.markdown("---")

    # === 1. REGIONAL COMPARISON (NORMALIZED) ===
    st.subheader("📊 Confronto Regionale (normalizzato)")
    st.caption("Indice RO normalizzato per tipologia: ogni tipo pesa allo stesso modo")

    df_region_norm = add_type_normalized_score(df_valid)
    regional_stats = pd.DataFrame()

    if not df_region_norm.empty:
        regional_stats = df_region_norm.groupby('regione').agg({
            'score_norm': ['mean', 'count'],
            'tipo_primario': 'nunique'
        }).round(2)
        regional_stats.columns = ['Media Normalizzata', 'N. Scuole', 'Tipi Coperti']
        regional_stats = regional_stats.reset_index()
        regional_stats.columns = ['Regione', 'Media Normalizzata', 'N. Scuole', 'Tipi Coperti']
        regional_stats = regional_stats[regional_stats['Regione'] != 'Non Specificato']
        regional_stats = regional_stats.sort_values('Media Normalizzata', ascending=False)

        col1, col2 = st.columns([2, 1])

        with col1:
            fig_ranking = px.bar(
                regional_stats.sort_values('Media Normalizzata', ascending=True),
                x='Media Normalizzata', y='Regione', orientation='h',
                color='Media Normalizzata', color_continuous_scale='RdYlGn',
                range_x=[0, 7], range_color=[1, 7],
                title="Indice RO Normalizzato per Regione",
                text='N. Scuole'
            )
            fig_ranking.update_traces(texttemplate='n=%{text}', textposition='outside')
            fig_ranking.update_layout(height=500)
            st.plotly_chart(fig_ranking, use_container_width=True)

        with col2:
            st.markdown("### 📊 Statistiche Regionali (normalizzate)")
            st.dataframe(regional_stats.reset_index(drop=True), use_container_width=True, hide_index=True, height=450)

        st.info("""
💡 **A cosa serve**: Confronta le regioni usando un indice normalizzato per tipologia, riducendo l'effetto della composizione delle scuole.

🔍 **Cosa rileva**: Le barre mostrano la media normalizzata. La colonna "Tipi Coperti" indica quante tipologie canoniche sono presenti per regione.

🎯 **Implicazioni**: Interpreta i risultati insieme a "N. Scuole" e "Tipi Coperti". Non vengono indicati migliori/peggiori per evitare bias da copertura disomogenea.
""")
    else:
        st.info("Dati insufficienti per il confronto regionale normalizzato.")

    # === 1b. STATALE vs PARITARIA PER REGIONE ===
    st.markdown("---")
    st.subheader("🏛️ Statale vs Paritaria per Regione")
    st.caption("Confronto per gestione con opzione normalizzata per tipologia")

    if 'statale_paritaria' in df_valid.columns:
        mode = st.radio(
            "Indice utilizzato",
            ["Normalizzato per tipologia", "Grezzo"],
            horizontal=True,
            key="reg_sp_mode"
        )
        min_n = st.slider(
            "Soglia minima per gruppo (per regione)",
            min_value=2,
            max_value=10,
            value=3,
            key="reg_sp_min_n"
        )

        df_sp_base = df_valid.copy()
        df_sp_base['gestione'] = df_sp_base['statale_paritaria'].apply(normalize_statale_paritaria)
        extra = int((df_sp_base['gestione'] == 'ND').sum() + (df_sp_base['gestione'] == 'Altro').sum())
        if extra > 0:
            st.warning(f"{extra} record non classificati in 'Statale/Paritaria' (ND o Altro).")
        df_sp_base = df_sp_base[df_sp_base['gestione'].isin(GESTIONE_SCUOLA)]

        if mode == "Normalizzato per tipologia":
            df_sp = add_type_normalized_score(df_sp_base)
            score_col = 'score_norm'
        else:
            df_sp = df_sp_base
            score_col = 'ptof_orientamento_maturity_index'

        if not df_sp.empty:
            grouped = df_sp.groupby(['regione', 'gestione'])[score_col].agg(['mean', 'count']).reset_index()
            grouped.columns = ['Regione', 'Gestione', 'Media', 'N. Scuole']

            counts_pivot = grouped.pivot(index='Regione', columns='Gestione', values='N. Scuole').fillna(0)
            valid_regions = counts_pivot[
                (counts_pivot.get('Statale', 0) >= min_n) &
                (counts_pivot.get('Paritaria', 0) >= min_n)
            ].index
            grouped = grouped[grouped['Regione'].isin(valid_regions)]

            if not grouped.empty:
                fig_sp = px.bar(
                    grouped,
                    x='Regione',
                    y='Media',
                    color='Gestione',
                    barmode='group',
                    text='N. Scuole',
                    labels={'Media': 'Indice RO', 'Gestione': 'Gestione'}
                )
                fig_sp.update_traces(texttemplate='n=%{text}', textposition='outside')
                fig_sp.update_layout(height=450, yaxis_range=[0, 7])
                st.plotly_chart(fig_sp, use_container_width=True)

                st.dataframe(
                    grouped.sort_values(['Regione', 'Gestione']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nessuna regione soddisfa la soglia minima per entrambi i gruppi.")
        else:
            st.info("Dati insufficienti per il confronto statale/paritaria.")
    else:
        st.info("Colonna 'statale_paritaria' non disponibile nel dataset.")

    # === ANOVA Test ===
    st.markdown("### 🔬 Test ANOVA: Differenze tra Regioni")
    st.caption("Verifica statistica se esistono differenze significative nell'Indice RO normalizzato tra le regioni")

    try:
        region_groups = []
        region_names = []
        for region, group in df_region_norm.groupby('regione'):
            vals = group['score_norm'].dropna().values
            if len(vals) >= 2 and region != 'Non Specificato':
                region_groups.append(vals)
                region_names.append(region)

        if len(region_groups) >= 2:
            f_stat, p_value = stats.f_oneway(*region_groups)

            all_values = np.concatenate(region_groups)
            grand_mean = np.mean(all_values)
            ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in region_groups)
            ss_total = sum((x - grand_mean)**2 for x in all_values)
            eta_squared = ss_between / ss_total if ss_total > 0 else 0

            if p_value < 0.001:
                sig_stars = "***"
                sig_text = "Altamente significativo (p < 0.001)"
            elif p_value < 0.01:
                sig_stars = "**"
                sig_text = "Molto significativo (p < 0.01)"
            elif p_value < 0.05:
                sig_stars = "*"
                sig_text = "Significativo (p < 0.05)"
            else:
                sig_stars = ""
                sig_text = "Non significativo (p ≥ 0.05)"

            if eta_squared >= 0.14:
                effect_text = "Grande"
                effect_stars = "***"
            elif eta_squared >= 0.06:
                effect_text = "Medio"
                effect_stars = "**"
            elif eta_squared >= 0.01:
                effect_text = "Piccolo"
                effect_stars = "*"
            else:
                effect_text = "Trascurabile"
                effect_stars = ""

            anova_results = pd.DataFrame({
                'Statistica': ['F-statistic', 'p-value', 'Significatività', 'η² (Eta-squared)', 'Effect Size'],
                'Valore': [
                    f"{f_stat:.3f}",
                    f"{p_value:.4f}",
                    f"{sig_stars} {sig_text}",
                    f"{eta_squared:.3f}",
                    f"{effect_stars} {effect_text}"
                ]
            })

            col_anova1, col_anova2 = st.columns([1, 1])
            with col_anova1:
                st.dataframe(anova_results, use_container_width=True, hide_index=True)
            with col_anova2:
                st.markdown("""
                **Legenda Significatività:**
                - \\* p < 0.05
                - \\*\\* p < 0.01  
                - \\*\\*\\* p < 0.001

                **Legenda Effect Size (η²):**
                - \\* Piccolo (0.01 - 0.06)
                - \\*\\* Medio (0.06 - 0.14)
                - \\*\\*\\* Grande (> 0.14)
                """)

            if p_value < 0.05:
                st.success(f"✅ Le differenze tra le {len(region_groups)} regioni sono **statisticamente significative** con un effect size **{effect_text.lower()}**.")

                st.markdown("#### 🎯 Analisi Post-Hoc: Quali regioni differiscono?")

                try:
                    from scipy.stats import tukey_hsd

                    tukey_result = tukey_hsd(*region_groups)
                    significant_pairs = []
                    all_pairs = []

                    for i in range(len(region_names)):
                        for j in range(i + 1, len(region_names)):
                            mean_i = np.mean(region_groups[i])
                            mean_j = np.mean(region_groups[j])
                            diff = mean_i - mean_j
                            p_adj = tukey_result.pvalue[i, j]

                            if diff > 0:
                                favored = region_names[i]
                                unfavored = region_names[j]
                            else:
                                favored = region_names[j]
                                unfavored = region_names[i]

                            pair_info = {
                                'Regione 1': region_names[i],
                                'Media 1': f"{mean_i:.2f}",
                                'Regione 2': region_names[j],
                                'Media 2': f"{mean_j:.2f}",
                                'Differenza': f"{abs(diff):.2f}",
                                'p-value adj.': f"{p_adj:.4f}",
                                'Significativo': '✅' if p_adj < 0.05 else '❌',
                                'A favore di': favored if p_adj < 0.05 else '-'
                            }
                            all_pairs.append(pair_info)

                            if p_adj < 0.05:
                                significant_pairs.append({
                                    'Confronto': f"{favored} vs {unfavored}",
                                    'Media superiore': f"{favored} ({max(mean_i, mean_j):.2f})",
                                    'Media inferiore': f"{unfavored} ({min(mean_i, mean_j):.2f})",
                                    'Differenza': f"{abs(diff):.2f}",
                                    'p-value': f"{p_adj:.4f}"
                                })

                    if significant_pairs:
                        st.markdown("##### 🏆 Confronti Significativi (p < 0.05)")
                        st.caption("Coppie di regioni con differenze statisticamente significative (media normalizzata)")

                        sig_df = pd.DataFrame(significant_pairs)
                        st.dataframe(sig_df, use_container_width=True, hide_index=True)

                        st.info(
                            f"📌 **Interpretazione**: Sono stati identificati **{len(significant_pairs)} confronti significativi** "
                            f"su {len(all_pairs)} possibili. Le medie sono normalizzate per tipologia."
                        )
                    else:
                        st.info("ℹ️ Nessun confronto tra coppie di regioni raggiunge la significatività statistica (p < 0.05) nel test post-hoc Tukey HSD.")

                    with st.expander("📋 Visualizza tutti i confronti a coppie"):
                        all_pairs_df = pd.DataFrame(all_pairs)
                        all_pairs_df = all_pairs_df.sort_values('p-value adj.')
                        st.dataframe(all_pairs_df, use_container_width=True, hide_index=True)
                        st.caption("La tabella mostra tutti i confronti possibili tra coppie di regioni, ordinati per significatività.")
                except ImportError:
                    st.warning("⚠️ Test Tukey HSD non disponibile. Aggiorna scipy: `pip install --upgrade scipy`")
                except Exception as e:
                    st.warning(f"⚠️ Impossibile eseguire test post-hoc: {e}")

                    region_means = {region_names[i]: np.mean(region_groups[i]) for i in range(len(region_names))}
                    sorted_regions = sorted(region_means.items(), key=lambda x: x[1], reverse=True)

                    st.markdown("##### 📊 Medie Regionali (normalizzate)")
                    ranking_df = pd.DataFrame([
                        {'Regione': reg, 'Media Normalizzata': f"{mean:.2f}"}
                        for reg, mean in sorted_regions
                    ])
                    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"ℹ️ Non ci sono differenze statisticamente significative tra le {len(region_groups)} regioni analizzate.")
        else:
            st.warning("Dati insufficienti per il test ANOVA (servono almeno 2 regioni con 2+ scuole ciascuna)")
    except Exception as e:
        st.error(f"Errore nel calcolo ANOVA: {e}")

    st.markdown("---")

    # === 2. CHOROPLETH MAP ===
    st.subheader("🗺️ Mappa Coropletica")
    st.caption("Visualizzazione geografica dell'Indice RO normalizzato per regione")

    map_data = regional_stats.copy()
    if map_data.empty:
        st.info("Dati insufficienti per generare la mappa")
    else:
        map_data['iso_code'] = map_data['Regione'].map(REGION_ISO)
        map_data = map_data[map_data['iso_code'].notna()]
        map_data['lat'] = map_data['Regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0])
        map_data['lon'] = map_data['Regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1])

        if len(map_data) > 0:
            fig_map = px.scatter_geo(
                map_data,
                lat='lat', lon='lon',
                size='N. Scuole',
                color='Media Normalizzata',
                hover_name='Regione',
                hover_data={'Media Normalizzata': ':.2f', 'N. Scuole': True, 'lat': False, 'lon': False},
                color_continuous_scale='RdYlGn',
                range_color=[1, 7],
                size_max=50,
                title="Distribuzione Geografica Indice RO Normalizzato"
            )
            fig_map.update_geos(
                scope='europe',
                center=dict(lat=42.5, lon=12.5),
                projection_scale=5,
                showland=True, landcolor='rgb(243, 243, 243)',
                showocean=True, oceancolor='rgb(204, 229, 255)',
                showcountries=True, countrycolor='rgb(204, 204, 204)',
                showsubunits=True, subunitcolor='rgb(255, 255, 255)'
            )
            fig_map.update_layout(height=600, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_map, use_container_width=True)
            st.info("""
💡 **A cosa serve**: Visualizza geograficamente la distribuzione della qualità dell'orientamento sul territorio italiano.

🔍 **Cosa rileva**: I cerchi rappresentano le regioni. Il colore (rosso → verde) indica il punteggio medio normalizzato, la dimensione è proporzionale al numero di scuole analizzate. Passa il mouse per i dettagli.

🎯 **Implicazioni**: Permette di identificare rapidamente aree critiche o virtuose con un indicatore comparabile tra regioni. Utile per pianificare interventi territoriali mirati.
""")
        else:
            st.info("Dati insufficienti per generare la mappa")

    st.markdown("---")

    # === 3. TOP PERFORMERS MAP ===
    st.subheader("🏆 Mappa Scuole più Virtuose")
    st.caption("Le scuole con gli indici di robustezza più alti, colorate per tipologia")

    if len(df_valid) > 0:
        n_top = st.slider("Numero di scuole da visualizzare", min_value=5, max_value=min(30, len(df_valid)), value=10, step=5)
        top_schools = df_valid.nlargest(n_top, 'ptof_orientamento_maturity_index').copy()

        # Assign coordinates
        if 'lat' in top_schools.columns and 'lon' in top_schools.columns:
            top_schools['lat'] = pd.to_numeric(top_schools['lat'], errors='coerce')
            top_schools['lon'] = pd.to_numeric(top_schools['lon'], errors='coerce')
            for idx, row in top_schools.iterrows():
                if pd.isna(row['lat']) or pd.isna(row['lon']):
                    coords = REGION_COORDS.get(row.get('regione', ''), (42.0, 12.5))
                    top_schools.at[idx, 'lat'] = coords[0] + np.random.uniform(-0.05, 0.05)
                    top_schools.at[idx, 'lon'] = coords[1] + np.random.uniform(-0.05, 0.05)
        else:
            top_schools['lat'] = top_schools['regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0])
            top_schools['lon'] = top_schools['regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1])
            np.random.seed(42)
            top_schools['lat'] = top_schools['lat'] + np.random.uniform(-0.1, 0.1, len(top_schools))
            top_schools['lon'] = top_schools['lon'] + np.random.uniform(-0.1, 0.1, len(top_schools))

        if 'tipo_scuola' in top_schools.columns:
            def get_primary_type(tipo):
                if pd.isna(tipo):
                    return None
                for part in str(tipo).split(','):
                    t = part.strip()
                    if t in TIPI_SCUOLA:
                        return t
                return None

            top_schools['tipo_primario'] = top_schools['tipo_scuola'].apply(get_primary_type)
            top_schools = top_schools[top_schools['tipo_primario'].isin(TIPI_SCUOLA)]
        else:
            top_schools['tipo_primario'] = None

        if top_schools.empty:
            st.info("Nessuna scuola con tipologia canonica disponibile")
        else:
            fig_top = px.scatter_geo(
                top_schools,
                lat='lat', lon='lon',
                color='tipo_primario',
                hover_name='denominazione',
                hover_data={
                    'ptof_orientamento_maturity_index': ':.2f',
                    'comune': True,
                    'regione': True,
                    'tipo_primario': True,
                    'lat': False, 'lon': False
                },
                title=f"🏆 Top {n_top} Scuole per Indice RO",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_top.update_traces(marker=dict(size=12, line=dict(width=1, color='white')))
            fig_top.update_geos(
                scope='europe',
                center=dict(lat=42.5, lon=12.5),
                projection_scale=5,
                showland=True, landcolor='rgb(243, 243, 243)',
                showocean=True, oceancolor='rgb(204, 229, 255)',
                showcountries=True, countrycolor='rgb(204, 204, 204)'
            )
            fig_top.update_layout(
                height=650,
                margin=dict(l=0, r=0, t=50, b=0),
                legend=dict(
                    title="Tipologia Scuola",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig_top, use_container_width=True)

        # Table
        st.markdown("### 📋 Dettaglio Scuole Top Performers")
        display_cols = ['denominazione', 'comune', 'regione', 'tipo_primario', 'ptof_orientamento_maturity_index']
        display_cols = [c for c in display_cols if c in top_schools.columns]
        top_display = top_schools[display_cols].copy()
        top_display.columns = ['Scuola', 'Comune', 'Regione', 'Tipo', 'Indice'][:len(display_cols)]
        top_display = top_display.reset_index(drop=True)
        top_display.index = top_display.index + 1
        st.dataframe(top_display, use_container_width=True)

        st.info("""
💡 **A cosa serve**: Localizza geograficamente le scuole con i migliori punteggi di orientamento in Italia.

🔍 **Cosa rileva**: Ogni punto sulla mappa è una scuola "eccellente". Il colore indica la tipologia (Liceo, Tecnico, ecc.). La tabella sotto mostra i dettagli completi.

🎯 **Implicazioni**: Usa questa mappa per trovare modelli di riferimento vicini alla tua zona. Puoi contattare queste scuole per scambi di buone pratiche o visite di studio.
""")

    # === 2b. MAP BY SCHOOL TYPE ===
    st.subheader("🏫 Mappa per Tipo di Istituto")
    st.caption("Distribuzione geografica per tipologia scolastica")

    if 'tipo_scuola' in df_valid.columns and len(map_data) > 0:
        def get_primary_type(tipo):
            if pd.isna(tipo):
                return None
            for part in str(tipo).split(','):
                t = part.strip()
                if t in TIPI_SCUOLA:
                    return t
            return None

        df_tipo_base = df_valid.copy()
        df_tipo_base['tipo_primario'] = df_tipo_base['tipo_scuola'].apply(get_primary_type)

        df_tipo_base = df_tipo_base[df_tipo_base['tipo_primario'].isin(TIPI_SCUOLA)]
        tipo_options = [t for t in TIPI_SCUOLA if t in df_tipo_base['tipo_primario'].unique()]

        if tipo_options:
            col_sel1, col_sel2 = st.columns([1, 2])

            with col_sel1:
                view_mode = st.radio(
                    "Visualizzazione",
                    ["Tutti i tipi", "Singolo tipo"],
                    horizontal=True
                )

            with col_sel2:
                if view_mode == "Singolo tipo":
                    selected_tipo = st.selectbox("Seleziona Tipologia", tipo_options)
                else:
                    selected_tipo = None

            if selected_tipo:
                df_tipo_map = df_tipo_base[df_tipo_base['tipo_primario'] == selected_tipo].copy()
            else:
                df_tipo_map = df_tipo_base.copy()

            if view_mode == "Tutti i tipi":
                tipo_region_stats = df_tipo_map.groupby(['regione', 'tipo_primario']).agg({
                    'ptof_orientamento_maturity_index': 'mean',
                    'school_id': 'count'
                }).reset_index()
                tipo_region_stats.columns = ['Regione', 'Tipo', 'Media', 'N. Scuole']
                tipo_region_stats = tipo_region_stats[tipo_region_stats['Regione'] != 'Non Specificato']

                if len(tipo_region_stats) > 0:
                    tipo_region_stats['lat'] = tipo_region_stats['Regione'].map(
                        lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0]
                    )
                    tipo_region_stats['lon'] = tipo_region_stats['Regione'].map(
                        lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1]
                    )

                    tipo_values = tipo_region_stats['Tipo'].unique()
                    tipo_offsets = {t: ((i - len(tipo_values) / 2) * 0.08, (i - len(tipo_values) / 2) * 0.08)
                                    for i, t in enumerate(tipo_values)}
                    tipo_region_stats['lat'] = tipo_region_stats.apply(
                        lambda r: r['lat'] + tipo_offsets.get(r['Tipo'], (0, 0))[0], axis=1
                    )
                    tipo_region_stats['lon'] = tipo_region_stats.apply(
                        lambda r: r['lon'] + tipo_offsets.get(r['Tipo'], (0, 0))[1], axis=1
                    )

                    fig_tipo_map = px.scatter_geo(
                        tipo_region_stats,
                        lat='lat', lon='lon',
                        size='N. Scuole',
                        color='Tipo',
                        hover_name='Regione',
                        hover_data={'Media': ':.2f', 'N. Scuole': True, 'Tipo': True, 'lat': False, 'lon': False},
                        size_max=20,
                        title="Distribuzione Tipologie per Regione"
                    )

                    fig_tipo_map.update_geos(
                        scope='europe',
                        center=dict(lat=42.5, lon=12.5),
                        projection_scale=5,
                        showland=True, landcolor='rgb(243, 243, 243)',
                        showocean=True, oceancolor='rgb(204, 229, 255)',
                        showcountries=True, countrycolor='rgb(204, 204, 204)'
                    )

                    fig_tipo_map.update_layout(height=550, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig_tipo_map, use_container_width=True)
            else:
                tipo_stats = df_tipo_map.groupby('regione').agg({
                    'ptof_orientamento_maturity_index': ['mean', 'count']
                }).round(2)
                tipo_stats.columns = ['Media', 'N. Scuole']
                tipo_stats = tipo_stats.reset_index()
                tipo_stats.columns = ['Regione', 'Media', 'N. Scuole']
                tipo_stats = tipo_stats[tipo_stats['Regione'] != 'Non Specificato']

                if len(tipo_stats) > 0:
                    tipo_stats['lat'] = tipo_stats['Regione'].map(
                        lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0]
                    )
                    tipo_stats['lon'] = tipo_stats['Regione'].map(
                        lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1]
                    )

                    fig_tipo_single = px.scatter_geo(
                        tipo_stats,
                        lat='lat', lon='lon',
                        size='N. Scuole',
                        color='Media',
                        hover_name='Regione',
                        hover_data={'Media': ':.2f', 'N. Scuole': True, 'lat': False, 'lon': False},
                        color_continuous_scale='RdYlGn',
                        range_color=[1, 7],
                        size_max=50,
                        title=f"Distribuzione {selected_tipo} per Regione"
                    )

                    fig_tipo_single.update_geos(
                        scope='europe',
                        center=dict(lat=42.5, lon=12.5),
                        projection_scale=5,
                        showland=True, landcolor='rgb(243, 243, 243)',
                        showocean=True, oceancolor='rgb(204, 229, 255)',
                        showcountries=True, countrycolor='rgb(204, 204, 204)'
                    )

                    fig_tipo_single.update_layout(height=550, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig_tipo_single, use_container_width=True)

                    st.markdown(
                        f"**{selected_tipo}**: {df_tipo_map['school_id'].nunique()} scuole in {len(tipo_stats)} regioni | "
                        f"Media: {df_tipo_map['ptof_orientamento_maturity_index'].mean():.2f}"
                    )
                else:
                    st.info(f"Nessun dato disponibile per {selected_tipo}")

            st.markdown("### 📊 Confronto Indice per Tipologia")
            tipo_comparison = df_tipo_base.groupby('tipo_primario').agg({
                'ptof_orientamento_maturity_index': ['mean', 'std', 'count']
            }).round(2)
            tipo_comparison.columns = ['Media', 'Dev.Std', 'N. Scuole']
            tipo_comparison = tipo_comparison.reset_index()
            tipo_comparison.columns = ['Tipologia', 'Media', 'Dev.Std', 'N. Scuole']
            tipo_comparison = tipo_comparison[tipo_comparison['Tipologia'] != 'Non Specificato']
            tipo_comparison = tipo_comparison.sort_values('Media', ascending=True)

            fig_tipo_bar = px.bar(
                tipo_comparison,
                x='Media', y='Tipologia', orientation='h',
                color='Media', color_continuous_scale='RdYlGn',
                range_x=[0, 7], range_color=[1, 7],
                text='N. Scuole',
                title="Indice RO Medio per Tipologia Scolastica"
            )
            fig_tipo_bar.update_traces(texttemplate='n=%{text}', textposition='outside')
            fig_tipo_bar.update_layout(height=350)
            st.plotly_chart(fig_tipo_bar, use_container_width=True)
        else:
            st.info("Nessuna tipologia scolastica disponibile")
    else:
        st.info("Dati tipo scuola non disponibili")

    st.info("""
💡 **A cosa serve**: Visualizza la distribuzione geografica delle scuole per tipologia (Licei, Tecnici, Professionali, ecc.).

🔍 **Cosa rileva**: La mappa mostra dove si concentrano le diverse tipologie. La dimensione dei cerchi indica il numero di scuole, il colore indica la media dell'Indice RO. Il grafico a barre sottostante ordina le tipologie per punteggio medio.

🎯 **Implicazioni**: Alcune tipologie potrebbero essere più diffuse o performanti in certe aree. Questi pattern aiutano a comprendere le specificità territoriali e tipologiche del sistema scolastico.
""")

    st.markdown("---")

    # === 4. NORD VS SUD ===
    st.subheader("⚖️ Confronto Nord vs Sud")
    st.caption("Analisi statistica delle differenze tra le due macro-aree geografiche")

    df_macro = df_valid[df_valid['macro_area'] != 'Non Specificato'].copy()

    if len(df_macro) > 5:
        col1, col2 = st.columns([2, 1])

        with col1:
            fig_box = px.box(
                df_macro, x='macro_area', y='ptof_orientamento_maturity_index',
                color='macro_area',
                color_discrete_map={'Nord': '#3498db', 'Sud': '#e74c3c'},
                title="Distribuzione Indice RO per Macro-Area",
                labels={'macro_area': 'Macro-Area', 'ptof_orientamento_maturity_index': 'Indice RO'},
                points='all'
            )
            fig_box.update_layout(showlegend=False, height=450)
            st.plotly_chart(fig_box, use_container_width=True)

        with col2:
            macro_stats = df_macro.groupby('macro_area')['ptof_orientamento_maturity_index'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).round(2)
            macro_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
            macro_stats = macro_stats.reset_index()
            macro_stats.columns = ['Area', 'N', 'Media', 'Dev.Std', 'Min', 'Max']

            st.markdown("### 📊 Statistiche per Area")
            st.dataframe(macro_stats, use_container_width=True, hide_index=True)

            try:
                valid_groups = []
                excluded_groups = []
                for name, group in df_macro.groupby('macro_area'):
                    values = group['ptof_orientamento_maturity_index'].dropna().values
                    if len(values) >= 3:
                        valid_groups.append(values)
                    else:
                        excluded_groups.append(name)

                if len(valid_groups) >= 2:
                    stat, p_val = stats.kruskal(*valid_groups)
                    st.markdown("### 🔬 Test Kruskal-Wallis")
                    if excluded_groups:
                        st.caption(f"⚠️ Esclusi per dati insufficienti (<3): {', '.join(excluded_groups)}")

                    st.metric("H-statistic", f"{stat:.2f}")
                    st.metric("p-value", f"{p_val:.4f}")
                    if p_val < 0.05:
                        st.success("✅ Differenza significativa (p < 0.05)")

                        group_names = []
                        group_values = []
                        for name, group in df_macro.groupby('macro_area'):
                            values = group['ptof_orientamento_maturity_index'].dropna().values
                            if len(values) >= 3:
                                group_names.append(name)
                                group_values.append(values)

                        group_means = {group_names[i]: np.mean(group_values[i]) for i in range(len(group_names))}
                        sorted_groups = sorted(group_means.items(), key=lambda x: x[1], reverse=True)

                        best_group = sorted_groups[0][0]
                        worst_group = sorted_groups[-1][0]
                        diff = sorted_groups[0][1] - sorted_groups[-1][1]

                        st.info(f"📌 **A favore di {best_group}** (media: {sorted_groups[0][1]:.2f}) vs {worst_group} (media: {sorted_groups[-1][1]:.2f}). Differenza: {diff:.2f}")
                    else:
                        st.info("❌ Nessuna differenza significativa")
                else:
                    st.info("Dati insufficienti per il test statistico (richiesti almeno 2 gruppi con n>=3)")
            except ImportError:
                st.info("Installa scipy per il test statistico")
    else:
        st.info("Dati insufficienti per il confronto macro-aree")

    st.info("""
💡 **A cosa serve**: Confronta le scuole del Nord con quelle del Sud per verificare se esistono differenze significative nella qualità dell'orientamento.

🔍 **Cosa rileva**: Il box plot mostra la distribuzione dei punteggi per ciascuna macro-area. La tabella riporta statistiche descrittive (N, media, dev.std). Il test Kruskal-Wallis verifica se le differenze sono statisticamente significative.

🎯 **Implicazioni**: Una differenza significativa suggerisce disparità territoriali da affrontare con politiche mirate. Se non significativa, l'orientamento è omogeneo a livello nazionale.
""")

    st.markdown("---")

    # === 5. AREA GEOGRAFICA (5 AREE) ===
    st.subheader("🌍 Confronto per Area Geografica (5 Aree)")
    st.caption("Analisi statistica per Nord Ovest, Nord Est, Centro, Sud, Isole")

    if 'area_geografica' in df_valid.columns:
        df_area = df_valid[df_valid['area_geografica'].notna() & (df_valid['area_geografica'] != 'ND')].copy()

        if len(df_area) > 5:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig_box_area = px.box(
                    df_area, x='area_geografica', y='ptof_orientamento_maturity_index',
                    color='area_geografica',
                    title="Distribuzione Indice RO per Area Geografica",
                    labels={'area_geografica': 'Area', 'ptof_orientamento_maturity_index': 'Indice RO'},
                    points='all',
                    category_orders={"area_geografica": ["Nord Ovest", "Nord Est", "Centro", "Sud", "Isole"]}
                )
                fig_box_area.update_layout(showlegend=False, height=450)
                st.plotly_chart(fig_box_area, use_container_width=True)

            with col2:
                area_stats = df_area.groupby('area_geografica')['ptof_orientamento_maturity_index'].agg([
                    'count', 'mean', 'std', 'min', 'max'
                ]).round(2)
                area_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
                area_stats = area_stats.reset_index()

                st.markdown("### 📊 Statistiche per Area")
                st.dataframe(area_stats, use_container_width=True, hide_index=True)

                try:
                    valid_groups = []
                    excluded_groups = []
                    for name, group in df_area.groupby('area_geografica'):
                        values = group['ptof_orientamento_maturity_index'].dropna().values
                        if len(values) >= 3:
                            valid_groups.append(values)
                        else:
                            excluded_groups.append(name)

                    if len(valid_groups) >= 2:
                        stat, p_val = stats.kruskal(*valid_groups)
                        st.markdown("### 🔬 Test Kruskal-Wallis")
                        if excluded_groups:
                            st.caption(f"⚠️ Esclusi per dati insufficienti (<3): {', '.join(excluded_groups)}")

                        st.metric("H-statistic", f"{stat:.2f}")
                        st.metric("p-value", f"{p_val:.4f}")
                        if p_val < 0.05:
                            st.success("✅ Differenza significativa")

                            group_names_area = []
                            group_values_area = []
                            for name, group in df_area.groupby('area_geografica'):
                                values = group['ptof_orientamento_maturity_index'].dropna().values
                                if len(values) >= 3:
                                    group_names_area.append(name)
                                    group_values_area.append(values)

                            group_means_area = {group_names_area[i]: np.mean(group_values_area[i]) for i in range(len(group_names_area))}
                            sorted_groups_area = sorted(group_means_area.items(), key=lambda x: x[1], reverse=True)

                            st.markdown("#### 🎯 A favore di chi?")

                            col_rank1, col_rank2 = st.columns(2)
                            with col_rank1:
                                st.markdown("**🏆 Ranking:**")
                                for i, (grp, mean) in enumerate(sorted_groups_area, 1):
                                    medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
                                    st.markdown(f"{medal} **{grp}**: {mean:.2f}")

                            with col_rank2:
                                best = sorted_groups_area[0]
                                worst = sorted_groups_area[-1]
                                st.info(
                                    f"📌 **{best[0]}** ha l'indice più alto ({best[1]:.2f}), "
                                    f"**{worst[0]}** il più basso ({worst[1]:.2f}). Differenza: {best[1]-worst[1]:.2f}"
                                )

                            try:
                                from scipy.stats import mannwhitneyu
                                from itertools import combinations

                                significant_pairs_area = []
                                for (i, name1), (j, name2) in combinations(enumerate(group_names_area), 2):
                                    _, p_pairwise = mannwhitneyu(group_values_area[i], group_values_area[j], alternative='two-sided')
                                    n_comparisons = len(group_names_area) * (len(group_names_area) - 1) // 2
                                    p_adjusted = min(p_pairwise * n_comparisons, 1.0)

                                    if p_adjusted < 0.05:
                                        mean1, mean2 = np.mean(group_values_area[i]), np.mean(group_values_area[j])
                                        favored = name1 if mean1 > mean2 else name2
                                        significant_pairs_area.append({
                                            'Confronto': f"{name1} vs {name2}",
                                            'A favore di': favored,
                                            'Media sup.': f"{max(mean1, mean2):.2f}",
                                            'Media inf.': f"{min(mean1, mean2):.2f}",
                                            'p-value adj.': f"{p_adjusted:.4f}"
                                        })

                                if significant_pairs_area:
                                    with st.expander(f"📋 {len(significant_pairs_area)} confronti significativi (Bonferroni-corretti)"):
                                        st.dataframe(pd.DataFrame(significant_pairs_area), use_container_width=True, hide_index=True)
                            except Exception:
                                pass
                        else:
                            st.info("❌ Nessuna differenza significativa")
                    else:
                        st.info("Dati insufficienti per il test statistico (richiesti almeno 2 gruppi con n>=3)")
                except ImportError:
                    st.info("Installa scipy per il test statistico")
        else:
            st.info("Dati insufficienti per il confronto per aree geografiche")
    else:
        st.warning("Colonna 'area_geografica' non trovata nel dataset")

    st.info("""
💡 **A cosa serve**: Analizza le differenze tra le 5 aree geografiche italiane (Nord Ovest, Nord Est, Centro, Sud, Isole).

🔍 **Cosa rileva**: Il box plot confronta le distribuzioni dei punteggi per area. Il test Kruskal-Wallis verifica se esistono differenze significative. I confronti post-hoc (Bonferroni) identificano quali coppie di aree differiscono.

🎯 **Implicazioni**: Permette di individuare le aree più performanti e quelle che necessitano maggiore supporto. Il ranking mostra chiaramente la graduatoria.
""")

    st.markdown("---")

    # === 3b. METROPOLITANO vs NON METROPOLITANO COMPARISON ===
    st.subheader("🏙️ Confronto Metropolitano vs Non Metropolitano")
    st.caption("Analisi statistica delle differenze tra scuole in aree metropolitane e non metropolitane")

    if 'territorio' in df_valid.columns:
        df_territorio = df_valid[df_valid['territorio'].isin(['Metropolitano', 'Non Metropolitano'])].copy()

        if len(df_territorio) > 5:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig_box_terr = px.box(
                    df_territorio, x='territorio', y='ptof_orientamento_maturity_index',
                    color='territorio',
                    color_discrete_map={'Metropolitano': '#9b59b6', 'Non Metropolitano': '#27ae60'},
                    title="Distribuzione Indice RO per Territorio",
                    labels={'territorio': 'Territorio', 'ptof_orientamento_maturity_index': 'Indice RO'},
                    points='all'
                )
                fig_box_terr.update_layout(showlegend=False, height=450)
                st.plotly_chart(fig_box_terr, use_container_width=True)

            with col2:
                terr_stats = df_territorio.groupby('territorio')['ptof_orientamento_maturity_index'].agg([
                    'count', 'mean', 'std', 'min', 'max'
                ]).round(2)
                terr_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
                terr_stats = terr_stats.reset_index()
                terr_stats.columns = ['Territorio', 'N', 'Media', 'Dev.Std', 'Min', 'Max']

                st.markdown("### 📊 Statistiche per Territorio")
                st.dataframe(terr_stats, use_container_width=True, hide_index=True)

                try:
                    metro = df_territorio[df_territorio['territorio'] == 'Metropolitano']['ptof_orientamento_maturity_index'].dropna().values
                    non_metro = df_territorio[df_territorio['territorio'] == 'Non Metropolitano']['ptof_orientamento_maturity_index'].dropna().values

                    if len(metro) >= 3 and len(non_metro) >= 3:
                        stat_mw, p_val_mw = stats.mannwhitneyu(metro, non_metro, alternative='two-sided')

                        n1, n2 = len(metro), len(non_metro)
                        mean1, mean2 = np.mean(metro), np.mean(non_metro)
                        std1, std2 = np.std(metro, ddof=1), np.std(non_metro, ddof=1)

                        pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1 + n2 - 2))
                        cohens_d_val = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0

                        abs_d = abs(cohens_d_val)
                        if abs_d >= 0.8:
                            effect_text = "Grande"
                            effect_stars = "***"
                        elif abs_d >= 0.5:
                            effect_text = "Medio"
                            effect_stars = "**"
                        elif abs_d >= 0.2:
                            effect_text = "Piccolo"
                            effect_stars = "*"
                        else:
                            effect_text = "Trascurabile"
                            effect_stars = ""

                        if cohens_d_val > 0:
                            direction = "a favore di Metropolitano"
                        elif cohens_d_val < 0:
                            direction = "a favore di Non Metropolitano"
                        else:
                            direction = ""

                        st.markdown("### 🔬 Test Mann-Whitney U")

                        test_results = pd.DataFrame({
                            'Statistica': ['U-statistic', 'p-value', 'Significatività', "Cohen's d", 'Effect Size', 'Direzione'],
                            'Valore': [
                                f"{stat_mw:.1f}",
                                f"{p_val_mw:.4f}",
                                "✅ Significativo" if p_val_mw < 0.05 else "❌ Non significativo",
                                f"{cohens_d_val:.3f}",
                                f"{effect_stars} {effect_text}",
                                direction if abs_d >= 0.2 else "-"
                            ]
                        })
                        st.dataframe(test_results, use_container_width=True, hide_index=True)

                        if p_val_mw < 0.05 and abs_d >= 0.2:
                            st.success(
                                f"✅ Differenza **statisticamente significativa** (p={p_val_mw:.4f}) con effect size "
                                f"**{effect_text.lower()}** ({cohens_d_val:.2f}) {direction}."
                            )
                        elif p_val_mw < 0.05:
                            st.info(f"ℹ️ Differenza statisticamente significativa (p={p_val_mw:.4f}) ma effect size trascurabile.")
                        else:
                            st.info("ℹ️ Nessuna differenza statisticamente significativa tra aree metropolitane e non metropolitane.")
                    else:
                        st.warning("Dati insufficienti per il test statistico (servono almeno 3 scuole per gruppo)")
                except ImportError:
                    st.info("Installa scipy per il test statistico: `pip install scipy`")
                except Exception as e:
                    st.error(f"Errore nel calcolo: {e}")
        else:
            st.info("Dati insufficienti per il confronto territori")
    else:
        st.warning("Colonna 'territorio' non presente nei dati")

    st.info("""
💡 **A cosa serve**: Confronta le scuole situate in aree metropolitane con quelle non metropolitane.

🔍 **Cosa rileva**: Il box plot visualizza le distribuzioni. Il test Mann-Whitney U verifica se le differenze sono significative. Il Cohen's d misura la dimensione dell'effetto (piccolo, medio, grande).

🎯 **Implicazioni**: Se esiste differenza significativa, potrebbe indicare che le scuole urbane e rurali hanno esigenze diverse o risorse differenti per l'orientamento. Aiuta a orientare interventi specifici.
""")

    st.markdown("---")

    # === 3c. ANALISI PER REGIONE E TERRITORIO ===
    st.subheader("📊 Analisi per Regione e Territorio")
    st.caption("Confronto dell'Indice RO per regione, suddiviso per area metropolitana e non metropolitana")

    if 'territorio' in df_valid.columns:
        df_reg_terr = df_valid[
            (df_valid['regione'] != 'Non Specificato') &
            (df_valid['territorio'].isin(['Metropolitano', 'Non Metropolitano']))
        ].copy()

        if len(df_reg_terr) > 0:
            reg_terr_stats = df_reg_terr.groupby(['regione', 'territorio']).agg({
                'ptof_orientamento_maturity_index': ['mean', 'count', 'std']
            }).round(2)
            reg_terr_stats.columns = ['Media', 'N', 'Dev.Std']
            reg_terr_stats = reg_terr_stats.reset_index()

            regions_both = reg_terr_stats.groupby('regione').filter(
                lambda x: len(x['territorio'].unique()) == 2
            )['regione'].unique()

            if len(regions_both) > 0:
                st.markdown(f"**{len(regions_both)} regioni** hanno scuole sia metropolitane che non metropolitane:")

                fig_grouped = px.bar(
                    reg_terr_stats[reg_terr_stats['regione'].isin(regions_both)].sort_values(['regione', 'territorio']),
                    x='regione', y='Media', color='territorio',
                    barmode='group',
                    color_discrete_map={'Metropolitano': '#9b59b6', 'Non Metropolitano': '#27ae60'},
                    title="Indice RO Medio per Regione e Territorio",
                    labels={'regione': 'Regione', 'Media': 'Indice RO Medio', 'territorio': 'Territorio'},
                    text='N'
                )
                fig_grouped.update_traces(texttemplate='n=%{text}', textposition='outside')
                fig_grouped.update_layout(height=500, xaxis_tickangle=-45)
                st.plotly_chart(fig_grouped, use_container_width=True)

                st.markdown("### 🔬 Effect Size per Regione")
                st.caption("Cohen's d calcolato per ogni regione con almeno 2 scuole per territorio")

                try:
                    effect_data = []
                    for region in regions_both:
                        metro_vals = df_reg_terr[
                            (df_reg_terr['regione'] == region) &
                            (df_reg_terr['territorio'] == 'Metropolitano')
                        ]['ptof_orientamento_maturity_index'].dropna().values
                        non_metro_vals = df_reg_terr[
                            (df_reg_terr['regione'] == region) &
                            (df_reg_terr['territorio'] == 'Non Metropolitano')
                        ]['ptof_orientamento_maturity_index'].dropna().values

                        if len(metro_vals) >= 2 and len(non_metro_vals) >= 2:
                            n1, n2 = len(metro_vals), len(non_metro_vals)
                            mean1, mean2 = np.mean(metro_vals), np.mean(non_metro_vals)
                            std1, std2 = np.std(metro_vals, ddof=1), np.std(non_metro_vals, ddof=1)

                            pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1 + n2 - 2))
                            d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0

                            try:
                                _, p_val = stats.mannwhitneyu(metro_vals, non_metro_vals, alternative='two-sided')
                            except Exception:
                                p_val = 1.0

                            abs_d = abs(d)
                            if abs_d >= 0.8:
                                effect_text = "Grande ***"
                            elif abs_d >= 0.5:
                                effect_text = "Medio **"
                            elif abs_d >= 0.2:
                                effect_text = "Piccolo *"
                            else:
                                effect_text = "Trascurabile"

                            direction = "→ Metropolitano" if d > 0 else "→ Non Metropolitano" if d < 0 else "-"

                            effect_data.append({
                                'Regione': region,
                                'Metro (n)': n1,
                                'Non Metro (n)': n2,
                                'Media Metro': f"{mean1:.2f}",
                                'Media Non Metro': f"{mean2:.2f}",
                                "Cohen's d": f"{d:.2f}",
                                'Effect Size': effect_text,
                                'Direzione': direction,
                                'p-value': f"{p_val:.3f}" if p_val >= 0.001 else "<0.001"
                            })

                    if effect_data:
                        effect_df = pd.DataFrame(effect_data)
                        effect_df['abs_d'] = effect_df["Cohen's d"].astype(float).abs()
                        effect_df = effect_df.sort_values('abs_d', ascending=False).drop('abs_d', axis=1)

                        st.dataframe(effect_df, use_container_width=True, hide_index=True)

                        significant_regions = [row for row in effect_data if float(row['p-value'].replace('<', '')) < 0.05]
                        if significant_regions:
                            st.success(f"✅ {len(significant_regions)} regioni mostrano differenze significative (p<0.05) tra aree metropolitane e non metropolitane.")
                        else:
                            st.info("ℹ️ Nessuna regione mostra differenze statisticamente significative.")
                    else:
                        st.info("Dati insufficienti per calcolare effect size per regione")
                except Exception as e:
                    st.error(f"Errore nel calcolo effect size: {e}")
            else:
                st.info("Nessuna regione ha sia scuole metropolitane che non metropolitane")

            with st.expander("📋 Tabella completa per Regione e Territorio"):
                st.dataframe(reg_terr_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Dati insufficienti per l'analisi per regione e territorio")
    else:
        st.warning("Colonna 'territorio' non presente nei dati")

    st.info("""
💡 **A cosa serve**: Analizza per ogni regione le differenze tra scuole in area metropolitana e non metropolitana.

🔍 **Cosa rileva**: L'heatmap mostra la media dell'indice RO per ogni combinazione regione-territorio. La tabella calcola Cohen's d e p-value per ogni regione che ha entrambi i tipi di territorio.

🎯 **Implicazioni**: Identifica regioni dove la differenza metropolitano/non-metropolitano è più marcata. Alcune regioni potrebbero non mostrare disparità, altre sì. Utile per interventi territoriali mirati.
""")

    st.markdown("---")

    # === 4. GAP ANALYSIS ===
    st.subheader("📉 Gap Analysis per Dimensione")
    st.caption("Differenza tra punteggio massimo e minimo per ciascuna dimensione, diviso per area geografica")

    dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

    if all(c in df_valid.columns for c in dim_cols) and 'area_geografica' in df_valid.columns:
        gap_data = []

        for area in df_valid['area_geografica'].dropna().unique():
            df_area_gap = df_valid[df_valid['area_geografica'] == area]
            for dim in dim_cols:
                vals = df_area_gap[dim].dropna()
                if len(vals) > 0:
                    gap_data.append({
                        'Area': area,
                        'Dimensione': get_label(dim),
                        'Min': vals.min(),
                        'Max': vals.max(),
                        'Gap': vals.max() - vals.min(),
                        'Media': vals.mean()
                    })

        if gap_data:
            gap_df = pd.DataFrame(gap_data)

            fig_gap = px.bar(
                gap_df, x='Dimensione', y='Gap', color='Area',
                barmode='group',
                title="Gap (Max - Min) per Dimensione e Area Geografica",
                labels={'Gap': 'Ampiezza Gap'},
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_gap.update_layout(height=450)
            st.plotly_chart(fig_gap, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📊 Gap Maggiori")
                top_gaps = gap_df.nlargest(5, 'Gap')[['Area', 'Dimensione', 'Gap', 'Min', 'Max']]
                st.dataframe(top_gaps, use_container_width=True, hide_index=True)

            with col2:
                st.markdown("### 📊 Gap Minori")
                bottom_gaps = gap_df.nsmallest(5, 'Gap')[['Area', 'Dimensione', 'Gap', 'Min', 'Max']]
                st.dataframe(bottom_gaps, use_container_width=True, hide_index=True)
    else:
        st.info("Dati insufficienti per l'analisi dei gap")

    st.info("""
💡 **A cosa serve**: Analizza l'ampiezza del gap (differenza tra punteggio massimo e minimo) per ogni dimensione e area geografica.

🔍 **Cosa rileva**: Gap ampi indicano forte eterogeneità: alcune scuole eccellono mentre altre sono molto indietro. Gap stretti indicano omogeneità. Le tabelle mostrano le combinazioni con gap maggiori e minori.

🎯 **Implicazioni**: Dove i gap sono ampi, esistono modelli di eccellenza da diffondere. Dimensioni con gap stretti potrebbero essere più "standard" o difficili da differenziare.
""")

    st.markdown("---")

    # === 5. AREA GEOGRAFICA RADAR ===
    st.subheader("🎯 Profilo per Area Geografica")
    st.caption("Confronto del profilo medio delle 5 dimensioni per area geografica")

    if all(c in df_valid.columns for c in dim_cols) and 'area_geografica' in df_valid.columns:
        area_profiles = df_valid.groupby('area_geografica')[dim_cols].mean().reset_index()

        if len(area_profiles) > 0:
            fig_radar = go.Figure()

            colors = {'Nord': '#3498db', 'Sud': '#e74c3c'}

            for _, row in area_profiles.iterrows():
                area = row['area_geografica']
                values = [row[c] for c in dim_cols]
                values.append(values[0])

                labels = [get_label(c) for c in dim_cols]
                labels.append(labels[0])

                fig_radar.add_trace(go.Scatterpolar(
                    r=values,
                    theta=labels,
                    fill='toself',
                    name=area,
                    line_color=colors.get(area, '#95a5a6'),
                    opacity=0.7
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                showlegend=True,
                title="Confronto Dimensioni per Area Geografica",
                height=500
            )

            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info("Dati insufficienti per il radar chart")
    else:
        st.info("Dati insufficienti per il radar chart")

    st.info("""
💡 **A cosa serve**: Confronta il "profilo" delle 5 dimensioni dell'orientamento tra le diverse aree geografiche.

🔍 **Cosa rileva**: Ogni area ha un poligono colorato. Un poligono più ampio indica punteggi più alti. La forma rivela quali dimensioni sono più sviluppate in ogni area.

🎯 **Implicazioni**: Le aree geografiche potrebbero avere "specializzazioni" diverse. Ad esempio, il Nord potrebbe eccellere in Governance mentre il Sud in Didattica. Questa visualizzazione aiuta a identificare buone pratiche regionali da diffondere.
""")

    st.markdown("---")

    # === 6. HOTSPOT GEOGRAFICI ===
    st.subheader("🔥 Hotspot Geografici di Eccellenza")
    st.caption("Identificazione di cluster territoriali con concentrazione di scuole eccellenti")

    if 'lat' in df_valid.columns and 'lon' in df_valid.columns:
        df_geo = df_valid[['lat', 'lon', 'ptof_orientamento_maturity_index', 'denominazione', 'comune', 'regione']].copy()
        df_geo['lat'] = pd.to_numeric(df_geo['lat'], errors='coerce')
        df_geo['lon'] = pd.to_numeric(df_geo['lon'], errors='coerce')
        df_geo = df_geo.dropna(subset=['lat', 'lon', 'ptof_orientamento_maturity_index'])

        if len(df_geo) >= 10:
            try:
                from sklearn.cluster import DBSCAN

                threshold = df_geo['ptof_orientamento_maturity_index'].quantile(0.70)
                top_performers = df_geo[df_geo['ptof_orientamento_maturity_index'] >= threshold].copy()

                if len(top_performers) >= 5:
                    col_h1, col_h2 = st.columns([1, 3])

                    with col_h1:
                        eps_km = st.slider(
                            "Raggio cluster (km)", 10, 100, 50, 10,
                            help="Distanza massima tra punti dello stesso cluster"
                        )
                        min_samples = st.slider(
                            "Minimo scuole per hotspot", 2, 10, 3,
                            help="Numero minimo di scuole per formare un hotspot"
                        )

                    eps_deg = eps_km / 111.0
                    coords = top_performers[['lat', 'lon']].values
                    clustering = DBSCAN(eps=eps_deg, min_samples=min_samples).fit(coords)
                    top_performers['cluster'] = clustering.labels_

                    n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
                    n_in_clusters = len(top_performers[top_performers['cluster'] != -1])

                    with col_h2:
                        met_cols = st.columns(3)
                        with met_cols[0]:
                            st.metric("🔥 Hotspot Identificati", n_clusters)
                        with met_cols[1]:
                            st.metric("🏫 Scuole in Hotspot", n_in_clusters)
                        with met_cols[2]:
                            st.metric("📊 Scuole Top 30%", len(top_performers))

                    if n_clusters > 0:
                        cluster_colors = px.colors.qualitative.Set1
                        top_performers['cluster_label'] = top_performers['cluster'].apply(
                            lambda x: f"Hotspot {x+1}" if x >= 0 else "Scuola isolata"
                        )

                        fig_hotspot = px.scatter_geo(
                            top_performers,
                            lat='lat', lon='lon',
                            color='cluster_label',
                            hover_name='denominazione',
                            hover_data={'ptof_orientamento_maturity_index': ':.2f', 'comune': True, 'regione': True, 'lat': False, 'lon': False},
                            title="Hotspot di Eccellenza (Scuole Top 30%)"
                        )
                        fig_hotspot.update_traces(marker=dict(size=10, line=dict(width=1, color='white')))
                        fig_hotspot.update_geos(
                            scope='europe',
                            center=dict(lat=42.5, lon=12.5),
                            projection_scale=5,
                            showland=True, landcolor='rgb(243, 243, 243)',
                            showocean=True, oceancolor='rgb(204, 229, 255)',
                            showcountries=True, countrycolor='rgb(204, 204, 204)'
                        )
                        fig_hotspot.update_layout(height=600, margin=dict(l=0, r=0, t=50, b=0))
                        st.plotly_chart(fig_hotspot, use_container_width=True)

                        st.markdown("#### 📋 Dettaglio Hotspot")
                        for cluster_id in sorted(set(top_performers['cluster'])):
                            if cluster_id == -1:
                                continue

                            cluster_schools = top_performers[top_performers['cluster'] == cluster_id]
                            center_lat = cluster_schools['lat'].mean()
                            center_lon = cluster_schools['lon'].mean()
                            mean_score = cluster_schools['ptof_orientamento_maturity_index'].mean()

                            main_region = cluster_schools['regione'].mode().iloc[0] if len(cluster_schools) > 0 else "N/D"

                            with st.expander(
                                f"🔥 Hotspot {cluster_id + 1}: {main_region} ({len(cluster_schools)} scuole, media: {mean_score:.2f})"
                            ):
                                cols_info = st.columns(3)
                                with cols_info[0]:
                                    st.metric("📍 Centro", f"{center_lat:.2f}, {center_lon:.2f}")
                                with cols_info[1]:
                                    st.metric("📊 Media Indice", f"{mean_score:.2f}")
                                with cols_info[2]:
                                    st.metric("🏫 N. Scuole", len(cluster_schools))

                                st.markdown("**Scuole nel cluster:**")
                                for _, school in cluster_schools.iterrows():
                                    st.write(
                                        f"- {school['denominazione']} ({school['comune']}) - "
                                        f"Indice: {school['ptof_orientamento_maturity_index']:.2f}"
                                    )
                    else:
                        st.info("ℹ️ Nessun hotspot identificato con questi parametri. Prova ad aumentare il raggio o diminuire il minimo scuole.")
            except ImportError:
                st.warning("Installa scikit-learn per l'analisi hotspot: `pip install scikit-learn`")
    else:
        st.info("Coordinate geografiche (lat/lon) non disponibili nei dati.")

    st.info("""
💡 **A cosa serve**: Identifica "hotspot" territoriali dove si concentrano scuole eccellenti.

🔍 **Cosa rileva**: Usa il clustering per trovare aree geografiche con alta densità di scuole nel top 30%. I parametri permettono di regolare il raggio e il numero minimo di scuole per definire un hotspot.

🎯 **Implicazioni**: Gli hotspot indicano aree territoriali dove si concentrano buone pratiche. Queste zone possono essere usate come poli di formazione e diffusione di modelli efficaci.
""")

    st.markdown("---")
    st.caption("🗺️ Mappa Italia - Dashboard PTOF | Analisi geografica della robustezza dell'orientamento PTOF delle scuole italiane")


# ============================================================================
# TAB 2: CONFRONTI GRUPPI
# ============================================================================
with tab_confronti:
    st.header("📊 Confronti tra Gruppi")

    with st.expander("📖 Come leggere questa sezione", expanded=False):
        st.markdown("""
        ### 🎯 Scopo della Pagina
        Questa pagina permette di **confrontare le performance** tra diversi gruppi di scuole, evidenziando pattern e differenze significative.

        ### 📊 Sezioni Disponibili

        **🔥 Matrice Performance (Heatmap)**
        - Incrocio tra **Area geografica** (Nord, Centro, Sud) e **Tipo scuola** (Liceo, Tecnico, ecc.)
        - I colori indicano il punteggio medio:
          - 🟢 **Verde scuro**: Punteggio alto (> 5)
          - 🟡 **Giallo**: Punteggio medio (3-5)
          - 🔴 **Rosso**: Punteggio basso (< 3)
        - Le celle vuote indicano assenza di dati per quella combinazione

        **📊 Box Plot Comparativi**
        - Mostrano la **distribuzione** dei punteggi per ogni gruppo
        - La **linea centrale** indica la mediana
        - La **scatola** contiene il 50% centrale dei dati (dal 25° al 75° percentile)
        - I **baffi** mostrano il range dei valori tipici
        - I **punti isolati** sono valori anomali (outlier)

        **📊 Grafico a Barre per Tipologia**
        - Confronto diretto delle medie per tipo di scuola
        - Più la barra è alta, migliore è la performance media

        ### 🔢 Come Interpretare le Heatmap
        - **Righe**: Tipi di scuola
        - **Colonne**: Aree geografiche o altre categorie
        - **Intensità colore**: Livello del punteggio
        - **Valori numerici**: Valore esatto della cella
        """)

    st.markdown("---")

    # === 1. HEATMAP AREA x TIPO ===
    st.subheader("🔥 Matrice Performance: Area x Tipo Scuola")
    st.caption("Confronto del punteggio medio per area geografica e tipo di scuola.")

    if 'tipo_scuola' in df.columns and 'area_geografica' in df.columns:
        try:
            from app.data_utils import explode_school_types
            df_pivot = explode_school_types(df)
        except Exception:
            df_pivot = df.copy()
        df_pivot = explode_multi_value(df_pivot, 'tipo_scuola')
        df_pivot = df_pivot[df_pivot['tipo_scuola'].isin(TIPI_SCUOLA)]

        pivot = df_pivot.pivot_table(
            index='tipo_scuola',
            columns='area_geografica',
            values='ptof_orientamento_maturity_index',
            aggfunc='mean'
        )

        if not pivot.empty:
            fig = px.imshow(
                pivot, text_auto='.2f', color_continuous_scale='RdBu',
                zmin=1, zmax=7, title="Indice RO Medio per Tipo e Area"
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📘 Guida alla lettura: Heatmap"):
                st.markdown("""
                **Cosa mostra?**
                Incrocia il **Tipo di Scuola** con l'**Area Geografica** per vedere chi performa meglio.
                - **Blu/Rosso scuro:** Punteggi alti/bassi (a seconda della scala).
                - **Numeri:** Il punteggio medio del gruppo (1-7).
                """)

            st.info("""
💡 **A cosa serve**: Incrocia tipologia scolastica e area geografica per identificare le combinazioni migliori e peggiori.

🔍 **Cosa rileva**: Ogni cella mostra il punteggio medio di quel gruppo. Colori scuri = punteggi estremi (alti o bassi). Celle vuote = nessun dato per quella combinazione.

🎯 **Implicazioni**: Se i Licei del Nord hanno punteggi alti ma quelli del Sud bassi, potrebbe indicare disparità territoriali da affrontare. Utile per politiche educative mirate.
""")

            # ANOVA effects
            with st.expander("📈 Analisi Statistica: Effetti Tipo Scuola e Area Geografica"):
                st.markdown("""
                Analisi degli effetti principali e dell'interazione tra **Tipo Scuola** e **Area Geografica** 
                sull'Indice RO.
                """)

                tipo_groups = df_pivot.groupby('tipo_scuola')['ptof_orientamento_maturity_index'].apply(list).to_dict()
                valid_tipo = {k: pd.Series(v).dropna() for k, v in tipo_groups.items() if len(pd.Series(v).dropna()) >= 3}

                col_stat1, col_stat2 = st.columns(2)

                with col_stat1:
                    st.markdown("#### 📚 Effetto Tipo Scuola")
                    if len(valid_tipo) >= 2:
                        f_tipo, p_tipo = stats.f_oneway(*[v for v in valid_tipo.values()])
                        p_interp, p_emoji = interpret_pvalue(p_tipo)
                        st.markdown(f"- F = {f_tipo:.2f}, p = {p_tipo:.4f} {p_emoji} {p_interp}")
                        if p_tipo < 0.05:
                            st.success("✅ Il tipo di scuola ha un effetto significativo")
                        else:
                            st.info("Il tipo di scuola non ha un effetto significativo")
                    else:
                        st.info("Dati insufficienti")

                with col_stat2:
                    st.markdown("#### 🗺️ Effetto Area Geografica")
                    if 'area_geografica' in df_pivot.columns:
                        area_groups = df_pivot.groupby('area_geografica')['ptof_orientamento_maturity_index'].apply(list).to_dict()
                        valid_area = {k: pd.Series(v).dropna() for k, v in area_groups.items() if len(pd.Series(v).dropna()) >= 3}
                        if len(valid_area) >= 2:
                            f_area, p_area = stats.f_oneway(*[v for v in valid_area.values()])
                            p_interp, p_emoji = interpret_pvalue(p_area)
                            st.markdown(f"- F = {f_area:.2f}, p = {p_area:.4f} {p_emoji} {p_interp}")
                            if p_area < 0.05:
                                st.success("✅ L'area geografica ha un effetto significativo")
                            else:
                                st.info("L'area geografica non ha un effetto significativo")
                        else:
                            st.info("Dati insufficienti")
                    else:
                        st.info("Dati area non disponibili")

                st.markdown("---")
                st.markdown("#### 🏆 Migliori e Peggiori Combinazioni")

                if not pivot.empty:
                    flat_data = []
                    for tipo in pivot.index:
                        for area in pivot.columns:
                            val = pivot.loc[tipo, area]
                            if pd.notna(val):
                                flat_data.append({'Tipo': tipo, 'Area': area, 'Media': val})

                    if flat_data:
                        flat_df = pd.DataFrame(flat_data).sort_values('Media', ascending=False)

                        col_best, col_worst = st.columns(2)
                        with col_best:
                            st.markdown("**🥇 Top 3:**")
                            for _, row in flat_df.head(3).iterrows():
                                st.markdown(f"- {row['Tipo']} ({row['Area']}): **{row['Media']:.2f}**")

                        with col_worst:
                            st.markdown("**⚠️ Bottom 3:**")
                            for _, row in flat_df.tail(3).iterrows():
                                st.markdown(f"- {row['Tipo']} ({row['Area']}): **{row['Media']:.2f}**")
        else:
            st.info("Dati insufficienti per la Heatmap")
    else:
        st.warning("Colonne 'tipo_scuola' o 'area_geografica' mancanti.")

    st.markdown("---")

    # === 2. RADAR CHART ===
    st.subheader("🕸️ Radar Chart: Profili a Confronto")
    st.caption("Confronto delle 5 dimensioni di robustezza tra diversi gruppi.")

    radar_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in radar_cols):
        radar_group = st.selectbox("Raggruppa per:", ["tipo_scuola", "area_geografica", "ordine_grado"], index=0, key="radar_group_select")

        if radar_group in df.columns:
            df_radar = df.copy()
            if radar_group == 'tipo_scuola':
                try:
                    from app.data_utils import explode_school_types
                    df_radar = explode_school_types(df)
                except Exception:
                    pass
                df_radar = explode_multi_value(df_radar, 'tipo_scuola')
                df_radar = df_radar[df_radar['tipo_scuola'].isin(TIPI_SCUOLA)]
            elif radar_group == 'ordine_grado':
                try:
                    from app.data_utils import explode_school_grades
                    df_radar = explode_school_grades(df)
                except Exception:
                    pass
                df_radar = explode_multi_value(df_radar, 'ordine_grado')

            radar_df = df_radar.groupby(radar_group)[radar_cols].mean().reset_index()

            fig = go.Figure()
            for i, row in radar_df.iterrows():
                group_name = str(row[radar_group])
                values = row[radar_cols].values.tolist()
                values += values[:1]
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=[get_label(c) for c in radar_cols] + [get_label(radar_cols[0])],
                    fill='toself',
                    name=group_name
                ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                showlegend=True,
                title=f"Confronto Profili per {radar_group.replace('_', ' ').title()}",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)

            st.info("""
💡 **A cosa serve**: Confronta il "profilo" di diversi gruppi (es. Licei vs Tecnici) sulle 5 dimensioni dell'orientamento.

🔍 **Cosa rileva**: Ogni "petalo" del radar è una dimensione. Più un gruppo si espande verso l'esterno, migliore è in quella area. Gruppi con profili sovrapposti hanno performance simili.

🎯 **Implicazioni**: Se un tipo di scuola ha un profilo "schiacciato" su una dimensione, quella è un'area critica su cui lavorare a livello di sistema per quel tipo di istituto.
""")
        else:
            st.info("Dati insufficienti per il Radar Chart")
    else:
        st.info("Dati insufficienti per il Radar Chart")

    st.markdown("---")

    # === 3. BOX PLOTS ===
    st.subheader("🏙️ Confronti: Territorio e Grado Scolastico")
    col1, col2 = st.columns(2)

    with col1:
        if 'territorio' in df.columns:
            fig = px.box(df, x='territorio', y='ptof_orientamento_maturity_index',
                         points="all", color='territorio',
                         title="Distribuzione per Territorio")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if 'ordine_grado' in df.columns:
            try:
                from app.data_utils import explode_school_grades
                df_box = explode_school_grades(df)
            except Exception:
                df_box = df.copy()
            df_box = explode_multi_value(df_box, 'ordine_grado')

            fig = px.box(df_box, x='ordine_grado', y='ptof_orientamento_maturity_index',
                         points="all", color='ordine_grado',
                         title="Distribuzione per Grado")
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("📘 Guida alla lettura: Box Plot"):
        st.markdown("""
        **Come si legge?**
        Confronta la distribuzione dei punteggi tra gruppi.
        - **Linea centrale:** Mediana (il valore che divide a metà il gruppo).
        - **Scatola (Box):** Contiene il 50% centrale delle scuole.
        - **Baffi (Linee):** Indicano il range dei valori (esclusi gli outlier).
        """)

    st.info("""
💡 **A cosa serve**: Mostra come si distribuiscono i punteggi all'interno di ogni gruppo, non solo la media.

🔍 **Cosa rileva**: La linea centrale è la mediana (metà delle scuole sta sopra, metà sotto). La "scatola" contiene il 50% centrale. I punti isolati sono scuole eccezionali (positive o negative).

🎯 **Implicazioni**: Scatole "alte" indicano gruppi migliori. Scatole "lunghe" indicano alta variabilità (alcune scuole eccellenti, altre no). I punti isolati meritano attenzione speciale.
""")

    st.markdown("---")

    # === 4. SIGNIFICATIVITÀ ED EFFECT SIZE ===
    st.subheader("📈 Significatività Statistica ed Effect Size")
    st.caption("Analisi della significatività delle differenze tra gruppi e della dimensione dell'effetto.")

    stat_tab1, stat_tab2, stat_tab3 = st.tabs(["🏙️ Territorio", "📚 Grado Scolastico", "🗺️ Area Geografica"])

    with stat_tab1:
        st.markdown("#### Confronto Metropolitano vs Non Metropolitano")
        if 'territorio' in df.columns:
            terr_groups = df.groupby('territorio')['ptof_orientamento_maturity_index'].apply(list).to_dict()
            if len(terr_groups) >= 2:
                terr_names = list(terr_groups.keys())
                results_terr = []
                for i, t1 in enumerate(terr_names):
                    for t2 in terr_names[i+1:]:
                        g1 = pd.Series(terr_groups[t1]).dropna()
                        g2 = pd.Series(terr_groups[t2]).dropna()
                        if len(g1) >= 3 and len(g2) >= 3:
                            t_stat, p_value = stats.ttest_ind(g1, g2)
                            d = cohens_d(g1, g2)
                            d_interp, d_emoji = interpret_cohens_d(d)
                            p_interp, p_emoji = interpret_pvalue(p_value)
                            results_terr.append({
                                'Confronto': f"{t1} vs {t2}",
                                'N₁': len(g1),
                                'Media₁': f"{g1.mean():.2f}",
                                'N₂': len(g2),
                                'Media₂': f"{g2.mean():.2f}",
                                'Differenza': f"{g1.mean() - g2.mean():.2f}",
                                't': f"{t_stat:.2f}",
                                'p-value': f"{p_value:.4f}",
                                'Sig.': f"{p_emoji} {p_interp}",
                                "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                                'Effetto': f"{d_emoji} {d_interp}"
                            })
                if results_terr:
                    st.dataframe(pd.DataFrame(results_terr), use_container_width=True, hide_index=True)

    with stat_tab2:
        st.markdown("#### Confronto I Grado vs II Grado")
        if 'ordine_grado' in df.columns:
            try:
                from app.data_utils import explode_school_grades
                df_stat = explode_school_grades(df)
            except Exception:
                df_stat = df.copy()
            df_stat = explode_multi_value(df_stat, 'ordine_grado')

            grado_groups = df_stat.groupby('ordine_grado')['ptof_orientamento_maturity_index'].apply(list).to_dict()
            if len(grado_groups) >= 2:
                grado_names = list(grado_groups.keys())
                results_grado = []
                for i, g1_name in enumerate(grado_names):
                    for g2_name in grado_names[i+1:]:
                        g1 = pd.Series(grado_groups[g1_name]).dropna()
                        g2 = pd.Series(grado_groups[g2_name]).dropna()
                        if len(g1) >= 3 and len(g2) >= 3:
                            t_stat, p_value = stats.ttest_ind(g1, g2)
                            d = cohens_d(g1, g2)
                            d_interp, d_emoji = interpret_cohens_d(d)
                            p_interp, p_emoji = interpret_pvalue(p_value)
                            results_grado.append({
                                'Confronto': f"{g1_name} vs {g2_name}",
                                'N₁': len(g1),
                                'Media₁': f"{g1.mean():.2f}",
                                'N₂': len(g2),
                                'Media₂': f"{g2.mean():.2f}",
                                'p-value': f"{p_value:.4f}",
                                'Sig.': f"{p_emoji} {p_interp}",
                                "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                                'Effetto': f"{d_emoji} {d_interp}"
                            })
                if results_grado:
                    st.dataframe(pd.DataFrame(results_grado), use_container_width=True, hide_index=True)

    with stat_tab3:
        st.markdown("#### Confronto tra Aree Geografiche")
        if 'area_geografica' in df.columns:
            area_groups = df.groupby('area_geografica')['ptof_orientamento_maturity_index'].apply(list).to_dict()
            if len(area_groups) >= 2:
                area_names = list(area_groups.keys())
                results_area = []
                for i, a1 in enumerate(area_names):
                    for a2 in area_names[i+1:]:
                        g1 = pd.Series(area_groups[a1]).dropna()
                        g2 = pd.Series(area_groups[a2]).dropna()
                        if len(g1) >= 3 and len(g2) >= 3:
                            t_stat, p_value = stats.ttest_ind(g1, g2)
                            d = cohens_d(g1, g2)
                            d_interp, d_emoji = interpret_cohens_d(d)
                            p_interp, p_emoji = interpret_pvalue(p_value)
                            results_area.append({
                                'Confronto': f"{a1} vs {a2}",
                                'N₁': len(g1),
                                'Media₁': f"{g1.mean():.2f}",
                                'N₂': len(g2),
                                'Media₂': f"{g2.mean():.2f}",
                                'p-value': f"{p_value:.4f}",
                                'Sig.': f"{p_emoji} {p_interp}",
                                "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                                'Effetto': f"{d_emoji} {d_interp}"
                            })
                if results_area:
                    st.dataframe(pd.DataFrame(results_area), use_container_width=True, hide_index=True)

                    # ANOVA if 3+ groups
                    if len(area_groups) >= 3:
                        valid_groups = [pd.Series(v).dropna() for v in area_groups.values() if len(pd.Series(v).dropna()) >= 3]
                        if len(valid_groups) >= 3:
                            f_stat, p_anova = stats.f_oneway(*valid_groups)
                            p_interp, p_emoji = interpret_pvalue(p_anova)
                            st.markdown(f"**ANOVA (confronto globale)**: F = {f_stat:.2f}, p = {p_anova:.4f} {p_emoji} {p_interp}")

    with st.expander("📘 Guida alla lettura: Significatività e Effect Size"):
        st.markdown("""
        ### 📊 Come interpretare i risultati

        **P-value (Significatività statistica)**
        - `*** (p < 0.001)`: Differenza altamente significativa
        - `** (p < 0.01)`: Differenza molto significativa
        - `* (p < 0.05)`: Differenza significativa
        - `n.s.`: Non significativa (la differenza potrebbe essere casuale)

        **Cohen's d (Dimensione dell'effetto)**
        - `< 0.2` ⚪ **Trascurabile**: Differenza praticamente inesistente
        - `0.2-0.5` 🟡 **Piccolo**: Differenza reale ma modesta
        - `0.5-0.8` 🟠 **Medio**: Differenza sostanziale e rilevante
        - `> 0.8` 🔴 **Grande**: Differenza molto marcata

        ### ⚠️ Nota importante
        Un p-value significativo indica che la differenza è *reale* (non casuale), ma non dice quanto sia *importante*.
        Il Cohen's d invece quantifica l'*entità* della differenza. Una differenza può essere statisticamente significativa ma praticamente irrilevante (d piccolo), o viceversa.

        **Per decisioni pratiche, guarda il Cohen's d!**
        """)

    st.info("""
💡 **A cosa serve**: Quantifica se le differenze osservate tra i gruppi sono statisticamente significative e quanto sono rilevanti nella pratica.

🔍 **Cosa rileva**: Il **p-value** indica se la differenza è reale o casuale. Il **Cohen's d** misura l'entità della differenza: valori > 0.5 indicano differenze sostanziali meritevoli di attenzione.

🎯 **Implicazioni**: Differenze con p < 0.05 E Cohen's d > 0.5 sono quelle su cui vale la pena intervenire. Evita di basare decisioni su differenze statisticamente significative ma con effetto trascurabile.
""")

    st.markdown("---")

    # 4. Grouped Bar I Grado vs II Grado
    st.subheader("📊 Confronto I Grado vs II Grado")

    if 'ordine_grado' in df.columns:
        dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
        if all(c in df.columns for c in dim_cols):
            try:
                from app.data_utils import explode_school_grades
                df_bar = explode_school_grades(df)
            except Exception:
                df_bar = df.copy()
            df_bar = explode_multi_value(df_bar, 'ordine_grado')

            grado_df = df_bar.groupby('ordine_grado')[dim_cols].mean().reset_index()
            grado_melted = grado_df.melt(id_vars='ordine_grado', var_name='Dimensione', value_name='Media')
            grado_melted['Dimensione'] = grado_melted['Dimensione'].apply(get_label)

            fig = px.bar(
                grado_melted, x='Dimensione', y='Media', color='ordine_grado',
                barmode='group', title="Media per Dimensione: I Grado vs II Grado"
            )
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📈 Analisi Statistica per Dimensione (I Grado vs II Grado)", expanded=False):
                grado_groups = df_bar.groupby('ordine_grado')
                grado_names = list(grado_groups.groups.keys())

                if len(grado_names) >= 2:
                    results_dim = []
                    for dim_col in dim_cols:
                        g1_name, g2_name = grado_names[0], grado_names[1]
                        g1 = grado_groups.get_group(g1_name)[dim_col].dropna()
                        g2 = grado_groups.get_group(g2_name)[dim_col].dropna()

                        if len(g1) >= 3 and len(g2) >= 3:
                            t_stat, p_value = stats.ttest_ind(g1, g2)
                            d = cohens_d(g1, g2)
                            d_interp, d_emoji = interpret_cohens_d(d)
                            p_interp, p_emoji = interpret_pvalue(p_value)

                            results_dim.append({
                                'Dimensione': get_label(dim_col),
                                f'Media {g1_name}': f"{g1.mean():.2f}",
                                f'Media {g2_name}': f"{g2.mean():.2f}",
                                'Diff.': f"{g1.mean() - g2.mean():.2f}",
                                'p-value': f"{p_value:.4f}",
                                'Sig.': f"{p_emoji} {p_interp}",
                                "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                                'Effetto': f"{d_emoji} {d_interp}"
                            })

                    if results_dim:
                        st.dataframe(pd.DataFrame(results_dim), use_container_width=True, hide_index=True)

                        sig_dims = [r for r in results_dim if '🟢' in r['Sig.'] or '🟡' in r['Sig.']]
                        if sig_dims:
                            st.markdown("**🔍 Differenze significative trovate in:**")
                            for r in sig_dims:
                                effect = r['Effetto'].split()[1] if len(r['Effetto'].split()) > 1 else r['Effetto']
                                st.markdown(
                                    f"- **{r['Dimensione']}**: differenza di {r['Diff.']} punti (effetto {effect.lower()})"
                                )

            st.info("""
💡 **A cosa serve**: Confronta direttamente le scuole di I grado (medie) con quelle di II grado (superiori) su ogni dimensione.

🔍 **Cosa rileva**: Le barre affiancate mostrano le medie per grado. Differenze evidenti tra i colori indicano che un grado performa sistematicamente meglio dell'altro in quella dimensione.

🎯 **Implicazioni**: Se il II grado eccelle in "Opportunità" ma il I grado no, potrebbe indicare che i collegamenti con il mondo del lavoro sono più sviluppati alle superiori. Utile per interventi specifici per fascia d'età.
""")

    st.markdown("---")

    # === 5. GAP ANALYSIS ===
    st.subheader("🎯 Gap Analysis: Distanza dal Ottimo (7)")

    gap_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in gap_cols):
        gap_means = df[gap_cols].mean()
        gap_values = 7 - gap_means

        gap_df = pd.DataFrame({
            'Dimensione': [get_label(c) for c in gap_cols],
            'Punteggio Attuale': gap_means.values,
            'Gap da 7': gap_values.values
        })

        fig = go.Figure()
        fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Punteggio Attuale'],
                             name='Attuale', marker_color='#00CC96'))
        fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Gap da 7'],
                             name='Gap', marker_color='#EF553B'))
        fig.update_layout(barmode='stack', yaxis=dict(range=[0, 7]))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📘 Guida alla lettura: Gap Analysis"):
            st.markdown("""
            **Cosa significa?**
            Visualizza quanto manca per raggiungere l'eccellenza (punteggio 7).
            - **Verde/Blu:** Il punteggio attuale raggiunto.
            - **Rosso/Grigio:** Il gap (distanza) mancante per arrivare a 7.
            """)

        with st.expander("📈 Analisi Statistica: Quanto siamo lontani dall'eccellenza?", expanded=False):
            st.markdown("""
            Verifica se i punteggi medi sono significativamente diversi dal valore teorico ottimo (7).
            Utilizziamo un **t-test one-sample** per ogni dimensione.
            """)

            results_gap = []
            for gap_col in gap_cols:
                values = df[gap_col].dropna()
                if len(values) >= 3:
                    t_stat, p_value = stats.ttest_1samp(values, 7)
                    mean_val = values.mean()
                    std_val = values.std()
                    gap = 7 - mean_val

                    d_one = (mean_val - 7) / std_val if std_val > 0 else np.nan
                    d_interp, d_emoji = interpret_cohens_d(d_one)
                    p_interp, p_emoji = interpret_pvalue(p_value)

                    results_gap.append({
                        'Dimensione': get_label(gap_col),
                        'Media': f"{mean_val:.2f}",
                        'Gap da 7': f"{gap:.2f}",
                        'DS': f"{std_val:.2f}",
                        't': f"{t_stat:.2f}",
                        'p-value': f"{p_value:.4f}",
                        'Sig.': f"{p_emoji} {p_interp}",
                        'Distanza (d)': f"{abs(d_one):.2f}" if not pd.isna(d_one) else "N/D",
                        'Entità Gap': f"{d_emoji} {d_interp}"
                    })

            if results_gap:
                st.dataframe(pd.DataFrame(results_gap), use_container_width=True, hide_index=True)

                st.markdown("### 🎯 Priorità di Intervento")
                sorted_gaps = sorted(results_gap, key=lambda x: float(x['Gap da 7']), reverse=True)
                for i, r in enumerate(sorted_gaps, 1):
                    emoji = "🔴" if float(r['Gap da 7']) > 2 else "🟠" if float(r['Gap da 7']) > 1 else "🟡"
                    entita = r['Entità Gap'].split()[1] if len(r['Entità Gap'].split()) > 1 else 'N/D'
                    st.markdown(f"{i}. {emoji} **{r['Dimensione']}**: gap di {r['Gap da 7']} punti ({entita})")

    st.info("""
💡 **A cosa serve**: Visualizza quanto manca a ciascuna dimensione per raggiungere l'eccellenza (punteggio massimo 7).

🔍 **Cosa rileva**: La parte verde è il punteggio medio attuale, quella rossa è il "gap" da colmare. Dimensioni con più rosso sono quelle dove c'è maggior margine di miglioramento.

🎯 **Implicazioni**: Concentra gli sforzi sulle dimensioni con gap maggiori. Queste sono le priorità di intervento per migliorare la qualità complessiva dell'orientamento nel sistema.
""")

    st.markdown("---")

    # === 6. REGIONAL COMPARISON ===
    st.subheader("🗺️ Confronto Regionale")

    if 'regione' in df.columns:
        df_region = df.copy()
        df_region['regione'] = df_region['regione'].apply(normalize_region)
        df_region = df_region[df_region['regione'] != 'Non Specificato']
        df_region_norm = add_type_normalized_score(df_region)
        region_counts = df_region_norm['regione'].dropna().value_counts()

        if df_region_norm.empty:
            st.info("Dati regionali insufficienti per la normalizzazione.")
        elif len(region_counts) >= 3:
            region_avg = df_region_norm[df_region_norm['regione'].notna()].groupby('regione')[
                'score_norm'
            ].agg(['mean', 'count']).reset_index()
            region_avg.columns = ['Regione', 'Indice RO Normalizzato', 'N. Scuole']

            if len(region_avg) >= 3:
                fig = px.bar(
                    region_avg.sort_values('Indice RO Normalizzato'),
                    x='Indice RO Normalizzato',
                    y='Regione',
                    orientation='h',
                    color='Indice RO Normalizzato',
                    color_continuous_scale='RdYlGn',
                    range_color=[1, 7],
                    text='N. Scuole',
                    title="Indice RO Normalizzato per Regione"
                )
                fig.update_traces(texttemplate='n=%{text}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("📈 Analisi Statistica Regionale (ANOVA + Confronti)", expanded=False):
                    region_groups = df_region_norm[df_region_norm['regione'].notna()].groupby('regione')[
                        'score_norm'
                    ].apply(list).to_dict()
                    valid_regions = {k: pd.Series(v).dropna() for k, v in region_groups.items() if len(pd.Series(v).dropna()) >= 3}

                    if len(valid_regions) >= 3:
                        f_stat, p_anova = stats.f_oneway(*[v for v in valid_regions.values()])
                        p_interp, p_emoji = interpret_pvalue(p_anova)

                        st.markdown(f"""
                        ### ANOVA (Confronto Globale tra Regioni)
                        - **F-statistic**: {f_stat:.2f}
                        - **p-value**: {p_anova:.4f} {p_emoji} {p_interp}
                        """)

                        if p_anova < 0.05:
                            st.success("✅ Esistono differenze significative tra le regioni!")
                            st.caption("Le medie sono normalizzate per tipologia; non vengono indicati migliori/peggiori.")
                        else:
                            st.info("Le differenze tra regioni non sono statisticamente significative (p > 0.05)")
                    else:
                        st.info("Servono almeno 3 regioni con dati sufficienti per l'ANOVA")

                st.info("""
💡 **A cosa serve**: Confronta le regioni con un indice normalizzato per tipologia, riducendo il bias dovuto a composizione e copertura.

🔍 **Cosa rileva**: Il numero "n=" indica quante scuole sono state analizzate. Interpreta i valori insieme alla copertura delle tipologie.

🎯 **Implicazioni**: Le differenze vanno lette come indicatori comparativi, non come classifiche definitive.
""")
            else:
                st.info("Dati regionali insufficienti (servono almeno 3 regioni)")
        else:
            st.info("Dati regionali insufficienti")
    else:
        st.info("Colonna 'regione' non disponibile nel CSV")


# ============================================================================
# TAB 3: REPORT REGIONALI
# ============================================================================
with tab_report:
    st.header("📋 Report Regionali per USR")

    with st.expander("📖 Come usare questa pagina", expanded=False):
        st.markdown("""
        ### 🎯 Scopo
        Genera **report sintetici regionali** per gli Uffici Scolastici Regionali (USR).

        ### 📊 Contenuto
        - Statistiche descrittive regionali
        - Confronto con la media nazionale
        - Distribuzione per tipologia di scuola
        - Scuole eccellenti e scuole da supportare
        - Aree prioritarie di miglioramento

        ### 💾 Export
        - Scarica in Excel, CSV o TXT
        """)

    st.markdown("---")

    # Region selector
    regions = sorted(df['regione'].dropna().unique().tolist())
    regions = [r for r in regions if r and r not in ['', 'ND', 'Non Specificato']]

    if not regions:
        st.warning("Nessuna regione disponibile nei dati.")
    else:
        selected_region = st.selectbox("🗺️ Seleziona Regione", regions, key="region_report_select")

        if selected_region:
            df_region = df[df['regione'] == selected_region].copy()
            df_national = df.copy()

            st.markdown(f"## 📋 Report: {selected_region}")
            st.markdown("---")

            # === METRICHE PRINCIPALI ===
            st.subheader("📈 Statistiche Chiave")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                n_schools = len(df_region)
                st.metric("🏫 N. Scuole Analizzate", n_schools)

            with col2:
                mean_ro = df_region['ptof_orientamento_maturity_index'].mean()
                national_mean = df_national['ptof_orientamento_maturity_index'].mean()
                delta = mean_ro - national_mean
                st.metric("📊 Indice RO Medio", f"{mean_ro:.2f}",
                          delta=f"{delta:+.2f} vs nazionale",
                          delta_color="normal" if delta >= 0 else "inverse")

            with col3:
                std_ro = df_region['ptof_orientamento_maturity_index'].std()
                st.metric("📐 Dev. Standard", f"{std_ro:.2f}")

            with col4:
                threshold_30 = df_national['ptof_orientamento_maturity_index'].quantile(0.70)
                pct_top = (df_region['ptof_orientamento_maturity_index'] >= threshold_30).mean() * 100
                st.metric("🏆 % nel Top 30%", f"{pct_top:.1f}%")

            st.markdown("---")

            # === CONFRONTO CON NAZIONALE ===
            st.subheader("🔄 Confronto con Media Nazionale")

            dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance',
                        'mean_didattica_orientativa', 'mean_opportunita']
            dim_labels = ['Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']

            if all(c in df.columns for c in dim_cols):
                comparison_data = []
                for col, label in zip(dim_cols, dim_labels):
                    regional = df_region[col].mean()
                    national = df_national[col].mean()
                    diff = regional - national
                    comparison_data.append({
                        'Dimensione': label,
                        'Regione': regional,
                        'Nazionale': national,
                        'Differenza': diff
                    })

                comparison_df = pd.DataFrame(comparison_data)

                col_chart, col_table = st.columns([2, 1])

                with col_chart:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name=selected_region,
                        x=comparison_df['Dimensione'],
                        y=comparison_df['Regione'],
                        marker_color='#3498db'
                    ))
                    fig.add_trace(go.Bar(
                        name='Media Nazionale',
                        x=comparison_df['Dimensione'],
                        y=comparison_df['Nazionale'],
                        marker_color='#95a5a6'
                    ))
                    fig.update_layout(
                        barmode='group',
                        title=f"Confronto {selected_region} vs Media Nazionale",
                        yaxis_title="Punteggio",
                        yaxis_range=[0, 7]
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col_table:
                    st.markdown("#### Dettaglio Differenze")
                    display_df = comparison_df.copy()
                    display_df['Regione'] = display_df['Regione'].round(2)
                    display_df['Nazionale'] = display_df['Nazionale'].round(2)
                    display_df['Differenza'] = display_df['Differenza'].apply(lambda x: f"{x:+.2f}")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.markdown("---")

            # === DISTRIBUZIONE PER TIPOLOGIA ===
            st.subheader("🏫 Distribuzione per Tipologia")
            st.caption("Tipologie: Infanzia, Primaria, I Grado, Liceo, Tecnico, Professionale")

            if 'tipo_scuola' in df_region.columns:
                try:
                    from app.data_utils import TIPI_SCUOLA, explode_school_types
                    df_region_exploded = explode_school_types(df_region.copy(), 'tipo_scuola')
                    df_region_exploded = df_region_exploded[df_region_exploded['tipo_scuola'].isin(TIPI_SCUOLA)]

                    if not df_region_exploded.empty:
                        tipo_stats = df_region_exploded.groupby('tipo_scuola').agg({
                            'ptof_orientamento_maturity_index': ['count', 'mean', 'std', 'min', 'max']
                        }).round(2)
                        tipo_stats.columns = ['N. Scuole', 'Media', 'Dev. Std', 'Min', 'Max']
                        tipo_stats = tipo_stats.reset_index()
                        tipo_stats.columns = ['Tipologia'] + list(tipo_stats.columns[1:])

                        tipo_order = {t: i for i, t in enumerate(TIPI_SCUOLA)}
                        tipo_stats['_order'] = tipo_stats['Tipologia'].map(tipo_order)
                        tipo_stats = tipo_stats.sort_values('_order').drop('_order', axis=1)

                        col_pie, col_bar = st.columns([1, 2])

                        with col_pie:
                            fig_pie = px.pie(
                                tipo_stats,
                                values='N. Scuole',
                                names='Tipologia',
                                title="Distribuzione Scuole",
                                category_orders={'Tipologia': TIPI_SCUOLA}
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)

                        with col_bar:
                            fig_tipo = px.bar(
                                tipo_stats.sort_values('Media', ascending=True),
                                x='Media', y='Tipologia', orientation='h',
                                color='Media', color_continuous_scale='RdYlGn',
                                range_x=[0, 7], title="Indice RO per Tipologia"
                            )
                            st.plotly_chart(fig_tipo, use_container_width=True)

                        st.dataframe(tipo_stats, use_container_width=True, hide_index=True)

                        # Test statistici
                        p_val, eta_sq = kruskal_test_scores(
                            df_region_exploded, 'tipo_scuola', 'ptof_orientamento_maturity_index'
                        )
                        sig_text, sig_color = format_significance(p_val)
                        eff_text, eff_color = interpret_effect_size(eta_sq)

                        col_sig, col_eff = st.columns(2)
                        with col_sig:
                            st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                        with col_eff:
                            if eta_sq is not None:
                                st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq:.3f} - {eff_text}]")
                            else:
                                st.markdown(f"**📏 Effect Size (η²):** :gray[N/D]")

                        # Post-hoc
                        if p_val is not None and p_val < 0.05:
                            st.markdown("#### 🔍 Confronti Post-Hoc (Dunn con correzione Bonferroni)")
                            posthoc_df = dunn_posthoc(df_region_exploded, 'tipo_scuola', 'ptof_orientamento_maturity_index')
                            if posthoc_df is not None and not posthoc_df.empty:
                                significant_only = posthoc_df[posthoc_df['Significativo'] == '✓']
                                if not significant_only.empty:
                                    st.markdown("**Confronti significativi (p-adj < 0.05):**")
                                    for _, row in significant_only.iterrows():
                                        diff_sign = ">" if row['Diff'] > 0 else "<"
                                        r_interp = interpret_r_effect(row['Effect (r)'])
                                        st.markdown(f"- **{row['Gruppo 1']}** ({row['Media 1']}) {diff_sign} **{row['Gruppo 2']}** ({row['Media 2']}) — Δ = {row['Diff']:+.2f}, r = {row['Effect (r)']:.2f} ({r_interp})")
                                else:
                                    st.info("Nessun confronto a coppie significativo dopo correzione Bonferroni.")

                                with st.expander("📊 Tabella completa confronti a coppie"):
                                    st.dataframe(posthoc_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("Non è stato possibile calcolare i confronti post-hoc.")

                        with st.expander("ℹ️ Interpretazione test statistici"):
                            st.markdown("""
                            **Test Kruskal-Wallis**: verifica se esistono differenze significative tra le tipologie scolastiche.
                            - `p < 0.05`: differenze statisticamente significative
                            - `p ≥ 0.05 (n.s.)`: differenze non significative

                            **Effect Size (η² - Eta-squared)**: misura la dimensione dell'effetto globale.
                            - < 0.01: Trascurabile
                            - 0.01 - 0.06: Piccolo
                            - 0.06 - 0.14: Medio
                            - > 0.14: Grande

                            **Test Post-Hoc (Dunn)**: se Kruskal-Wallis è significativo, identifica quali coppie di tipologie differiscono.
                            - Usa correzione Bonferroni per controllare l'errore di tipo I
                            - Effect size r (per coppia): < 0.1 Trascurabile, 0.1-0.3 Piccolo, 0.3-0.5 Medio, > 0.5 Grande
                            """)
                    else:
                        st.info("Nessuna scuola con tipologia valida nella regione selezionata.")
                except ImportError:
                    st.info("data_utils non disponibile")

            st.markdown("---")

            # === TOP 10 E BOTTOM 10 ===
            col_top, col_bottom = st.columns(2)

            with col_top:
                st.subheader("🏆 Top 10 Scuole")
                top_10 = df_region.nlargest(10, 'ptof_orientamento_maturity_index')[
                    ['denominazione', 'comune', 'tipo_scuola', 'ptof_orientamento_maturity_index']
                ].copy()
                top_10.columns = ['Denominazione', 'Comune', 'Tipo', 'Indice RO']
                top_10['Indice RO'] = top_10['Indice RO'].round(2)
                st.dataframe(top_10, use_container_width=True, hide_index=True)

            with col_bottom:
                st.subheader("📉 Bottom 10 (da supportare)")
                bottom_10 = df_region.nsmallest(10, 'ptof_orientamento_maturity_index')[
                    ['denominazione', 'comune', 'tipo_scuola', 'ptof_orientamento_maturity_index']
                ].copy()
                bottom_10.columns = ['Denominazione', 'Comune', 'Tipo', 'Indice RO']
                bottom_10['Indice RO'] = bottom_10['Indice RO'].round(2)
                st.dataframe(bottom_10, use_container_width=True, hide_index=True)

            st.markdown("---")

            # === AREE DI MIGLIORAMENTO ===
            st.subheader("🎯 Aree Prioritarie di Miglioramento")

            if all(c in df_region.columns for c in dim_cols):
                dim_means = [(label, df_region[col].mean()) for col, label in zip(dim_cols, dim_labels)]
                dim_means_sorted = sorted(dim_means, key=lambda x: x[1])

                st.markdown("Le dimensioni con i punteggi più bassi a livello regionale:")

                for i, (dim, score) in enumerate(dim_means_sorted[:3], 1):
                    color = "#e74c3c" if score < 3.5 else "#f39c12" if score < 4.5 else "#2ecc71"
                    st.markdown(f"""
                    <div style="padding: 10px; background-color: {color}22; border-left: 4px solid {color}; margin: 5px 0;">
                        <b>{i}. {dim}</b>: Media regionale = {score:.2f}/7
                    </div>
                    """, unsafe_allow_html=True)

                st.info("""
💡 **Suggerimenti per USR**:
- Organizzare formazione mirata sulle dimensioni più deboli
- Favorire lo scambio di buone pratiche tra scuole virtuose e scuole in difficoltà
- Creare reti territoriali tematiche (es. rete per la Governance, rete per le Partnership)
""")

            st.markdown("---")

            # === EXPORT ===
            st.subheader("💾 Esporta Report")

            col_exp1, col_exp2, col_exp3 = st.columns(3)

            with col_exp1:
                csv_buffer = df_region.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Dati Regione (CSV)",
                    data=csv_buffer,
                    file_name=f"report_{selected_region.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

            with col_exp2:
                try:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_region.to_excel(writer, sheet_name='Dati', index=False)
                        summary_data = {
                            'Metrica': ['N. Scuole', 'Indice RO Medio', 'Dev. Standard', '% nel Top 30% Nazionale',
                                        'Migliore Scuola', 'Scuola da Supportare'],
                            'Valore': [
                                len(df_region),
                                round(mean_ro, 2),
                                round(std_ro, 2),
                                f"{pct_top:.1f}%",
                                df_region.loc[df_region['ptof_orientamento_maturity_index'].idxmax(), 'denominazione'],
                                df_region.loc[df_region['ptof_orientamento_maturity_index'].idxmin(), 'denominazione']
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Sintesi', index=False)
                        if 'comparison_df' in locals():
                            comparison_df.to_excel(writer, sheet_name='Confronto', index=False)
                    excel_buffer.seek(0)
                    st.download_button(
                        label="📥 Report Excel",
                        data=excel_buffer,
                        file_name=f"report_{selected_region.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    st.warning("Installa openpyxl per export Excel")

            with col_exp3:
                summary_text = f"""
REPORT REGIONALE - {selected_region}
{'='*50}

STATISTICHE CHIAVE
- Scuole analizzate: {len(df_region)}
- Indice RO medio: {mean_ro:.2f}
- Deviazione standard: {std_ro:.2f}
- % scuole nel top 30% nazionale: {pct_top:.1f}%

CONFRONTO CON MEDIA NAZIONALE
- Differenza dall'indice nazionale: {delta:+.2f}
"""
                if 'top_10' in locals():
                    summary_text += "\nTOP 5 SCUOLE\n"
                    for _, row in top_10.head(5).iterrows():
                        summary_text += f"- {row['Denominazione']} ({row['Comune']}): {row['Indice RO']}\n"
                st.download_button(
                    label="📥 Sintesi (TXT)",
                    data=summary_text.encode('utf-8'),
                    file_name=f"sintesi_{selected_region.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            st.markdown("---")

            # === CONFRONTO TRA REGIONI ===
            st.subheader("🔄 Confronto Tra Regioni")

            col_compare = st.multiselect("Seleziona regioni da confrontare", regions, default=[selected_region], key="region_compare_select")

            if len(col_compare) >= 2:
                df_compare = df[df['regione'].isin(col_compare)].copy()

                if all(c in df.columns for c in dim_cols):
                    fig_radar = go.Figure()
                    colors = px.colors.qualitative.Set2

                    for i, region in enumerate(col_compare):
                        region_data = df_compare[df_compare['regione'] == region]
                        values = [region_data[col].mean() for col in dim_cols]
                        values.append(values[0])
                        labels = dim_labels + [dim_labels[0]]

                        fig_radar.add_trace(go.Scatterpolar(
                            r=values,
                            theta=labels,
                            fill='toself',
                            name=region,
                            line_color=colors[i % len(colors)],
                            opacity=0.7
                        ))

                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(range=[0, 7])),
                        title="Confronto Profilo Dimensionale",
                        height=500
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                fig_box = px.box(
                    df_compare,
                    x='regione',
                    y='ptof_orientamento_maturity_index',
                    color='regione',
                    title="Distribuzione Indice RO per Regione"
                )
                fig_box.update_layout(showlegend=False, yaxis_range=[0, 7])
                st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")
    st.caption("📊 Report Regionali - Dashboard PTOF | Generazione report per Uffici Scolastici Regionali")

# Footer
st.markdown("---")
st.caption("🗺️ Analisi Territoriale - Dashboard PTOF | Mappa Italia, Confronti Gruppi e Report Regionali")
