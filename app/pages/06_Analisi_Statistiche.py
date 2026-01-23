# 📊 Analisi Statistiche Inferenziali - Dimensioni ORIENTA+
# ANOVA, Effect Size, Post-hoc tests per ogni dimensione

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Aggiungi la root del progetto al path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from data_utils import render_footer, load_summary_data
from page_control import setup_page

# Importa librerie statistiche
try:
    from scipy import stats
    from scipy.stats import f_oneway, kruskal, mannwhitneyu, ttest_ind
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import scikit_posthocs as sp
    POSTHOC_AVAILABLE = True
except ImportError:
    POSTHOC_AVAILABLE = False

try:
    import pingouin as pg
    PINGOUIN_AVAILABLE = True
except ImportError:
    PINGOUIN_AVAILABLE = False

st.set_page_config(page_title="ORIENTA+ | Analisi Statistiche", page_icon="📊", layout="wide")
setup_page("pages/06_Analisi_Statistiche.py")

# Custom CSS
st.markdown("""
<style>
    .stat-significant { background-color: #d4edda; padding: 10px; border-radius: 5px; border-left: 4px solid #28a745; }
    .stat-not-significant { background-color: #f8d7da; padding: 10px; border-radius: 5px; border-left: 4px solid #dc3545; }
    .stat-marginal { background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107; }
    .effect-large { color: #28a745; font-weight: bold; }
    .effect-medium { color: #ffc107; font-weight: bold; }
    .effect-small { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# === COSTANTI ===
DIMENSIONS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi', 
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica Orientativa',
    'mean_opportunita': 'Opportunità'
}

DIM_COLORS = {
    'Finalità': '#e74c3c',
    'Obiettivi': '#3498db',
    'Governance': '#2ecc71',
    'Didattica Orientativa': '#9b59b6',
    'Opportunità': '#f39c12'
}

GROUPING_VARS = {
    'area_geografica': 'Area Geografica',
    'regione': 'Regione',
    'provincia': 'Provincia',
    'ordine_grado': 'Ordine/Grado',
    'statale_paritaria': 'Gestione (Statale/Paritaria)',
    'territorio': 'Territorio (Metro/Non Metro)'
}

# === FUNZIONI STATISTICHE ===

def calculate_eta_squared(groups: List[np.ndarray]) -> float:
    """Calcola eta-squared (effect size per ANOVA)."""
    all_data = np.concatenate(groups)
    grand_mean = np.mean(all_data)
    
    ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
    ss_total = sum((x - grand_mean)**2 for x in all_data)
    
    if ss_total == 0:
        return 0.0
    return ss_between / ss_total


def calculate_omega_squared(groups: List[np.ndarray], f_stat: float) -> float:
    """Calcola omega-squared (effect size meno biased di eta-squared)."""
    k = len(groups)
    n_total = sum(len(g) for g in groups)
    
    all_data = np.concatenate(groups)
    grand_mean = np.mean(all_data)
    
    ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
    ss_total = sum((x - grand_mean)**2 for x in all_data)
    ms_within = (ss_total - ss_between) / (n_total - k)
    
    numerator = ss_between - (k - 1) * ms_within
    denominator = ss_total + ms_within
    
    if denominator == 0:
        return 0.0
    return max(0, numerator / denominator)


def calculate_cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Calcola Cohen's d per confronto tra due gruppi."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def interpret_effect_size(effect: float, metric: str = 'eta') -> Tuple[str, str]:
    """Interpreta la dimensione dell'effetto."""
    if metric == 'eta' or metric == 'omega':
        # Cohen's guidelines per eta-squared
        if abs(effect) >= 0.14:
            return "Grande", "effect-large"
        elif abs(effect) >= 0.06:
            return "Medio", "effect-medium"
        elif abs(effect) >= 0.01:
            return "Piccolo", "effect-small"
        else:
            return "Trascurabile", "effect-small"
    else:  # Cohen's d
        if abs(effect) >= 0.8:
            return "Grande", "effect-large"
        elif abs(effect) >= 0.5:
            return "Medio", "effect-medium"
        elif abs(effect) >= 0.2:
            return "Piccolo", "effect-small"
        else:
            return "Trascurabile", "effect-small"


def run_anova(df: pd.DataFrame, dv: str, group_var: str) -> Dict:
    """Esegue ANOVA one-way con diagnostiche."""
    # Rimuovi NA
    df_clean = df[[dv, group_var]].dropna()
    
    if df_clean.empty or df_clean[group_var].nunique() < 2:
        return None
    
    groups = [g[dv].values for name, g in df_clean.groupby(group_var) if len(g) >= 2]
    group_names = [name for name, g in df_clean.groupby(group_var) if len(g) >= 2]
    
    if len(groups) < 2:
        return None
    
    # Test di normalità (Shapiro-Wilk per gruppi piccoli)
    normality_ok = True
    normality_tests = {}
    for i, (name, g) in enumerate(zip(group_names, groups)):
        if len(g) >= 3 and len(g) <= 5000:
            stat, p = stats.shapiro(g)
            normality_tests[name] = {'statistic': stat, 'p_value': p}
            if p < 0.05:
                normality_ok = False
    
    # Test di omoschedasticità (Levene)
    levene_stat, levene_p = stats.levene(*groups)
    homoscedasticity_ok = levene_p >= 0.05
    
    # ANOVA parametrica o Kruskal-Wallis non parametrica
    if normality_ok and homoscedasticity_ok:
        f_stat, p_value = f_oneway(*groups)
        test_type = "ANOVA (parametrica)"
    else:
        f_stat, p_value = kruskal(*groups)
        test_type = "Kruskal-Wallis (non parametrica)"
    
    # Effect sizes
    eta_sq = calculate_eta_squared(groups)
    omega_sq = calculate_omega_squared(groups, f_stat) if normality_ok else eta_sq
    
    # Statistiche descrittive per gruppo
    descriptives = {}
    for name, g in zip(group_names, groups):
        descriptives[name] = {
            'n': len(g),
            'mean': np.mean(g),
            'std': np.std(g, ddof=1),
            'median': np.median(g),
            'min': np.min(g),
            'max': np.max(g)
        }
    
    return {
        'test_type': test_type,
        'statistic': f_stat,
        'p_value': p_value,
        'eta_squared': eta_sq,
        'omega_squared': omega_sq,
        'normality_ok': normality_ok,
        'homoscedasticity_ok': homoscedasticity_ok,
        'levene_p': levene_p,
        'n_groups': len(groups),
        'n_total': sum(len(g) for g in groups),
        'descriptives': descriptives,
        'group_names': group_names,
        'groups': groups
    }


def run_posthoc(df: pd.DataFrame, dv: str, group_var: str, parametric: bool = True) -> Optional[pd.DataFrame]:
    """Esegue test post-hoc per confronti multipli."""
    df_clean = df[[dv, group_var]].dropna()
    
    if not PINGOUIN_AVAILABLE:
        return None
    
    try:
        if parametric:
            # Tukey HSD
            posthoc = pg.pairwise_tukey(data=df_clean, dv=dv, between=group_var)
        else:
            # Dunn's test (non parametrico)
            posthoc = pg.pairwise_tests(data=df_clean, dv=dv, between=group_var, 
                                         parametric=False, padjust='bonf')
        return posthoc
    except Exception as e:
        return None


def find_best_worst_groups(descriptives: Dict) -> Tuple[str, str, float]:
    """Trova il gruppo migliore e peggiore."""
    sorted_groups = sorted(descriptives.items(), key=lambda x: x[1]['mean'], reverse=True)
    best = sorted_groups[0]
    worst = sorted_groups[-1]
    diff = best[1]['mean'] - worst[1]['mean']
    return best[0], worst[0], diff


# === PAGINA PRINCIPALE ===

st.title("📊 Analisi Statistiche Inferenziali")
st.markdown("Confronti tra gruppi sulle dimensioni dell'orientamento con ANOVA, effect size e test post-hoc")

# Verifica dipendenze
if not SCIPY_AVAILABLE:
    st.error("❌ Libreria scipy non disponibile. Installa con: pip install scipy")
    st.stop()

# Carica dati
df = load_summary_data()

if df.empty:
    st.error("Nessun dato disponibile per l'analisi.")
    st.stop()

st.info(f"📊 **Dataset:** {len(df)} scuole analizzate")

# === SIDEBAR: CONFIGURAZIONE ===
st.sidebar.header("⚙️ Configurazione Analisi")

# Selezione dimensioni
selected_dims = st.sidebar.multiselect(
    "Dimensioni da analizzare",
    options=list(DIMENSIONS.keys()),
    default=list(DIMENSIONS.keys()),
    format_func=lambda x: DIMENSIONS[x]
)

# Selezione variabili di raggruppamento
selected_groups = st.sidebar.multiselect(
    "Variabili di confronto",
    options=[k for k in GROUPING_VARS.keys() if k in df.columns],
    default=['area_geografica', 'statale_paritaria', 'ordine_grado'],
    format_func=lambda x: GROUPING_VARS.get(x, x)
)

# Soglia significatività
alpha = st.sidebar.selectbox(
    "Soglia significatività (α)",
    options=[0.05, 0.01, 0.001, 0.10],
    index=0
)

# Mostra post-hoc
show_posthoc = st.sidebar.checkbox("Mostra test post-hoc", value=True)

# Filtro minimo osservazioni per gruppo
min_obs = st.sidebar.slider("Minimo osservazioni per gruppo", 5, 50, 10)

st.sidebar.divider()
st.sidebar.markdown("### 📖 Legenda Effect Size")
st.sidebar.markdown("""
**η² (Eta-squared):**
- η² ≥ 0.14 → Grande
- η² ≥ 0.06 → Medio  
- η² ≥ 0.01 → Piccolo

**Cohen's d:**
- d ≥ 0.8 → Grande
- d ≥ 0.5 → Medio
- d ≥ 0.2 → Piccolo
""")

if not selected_dims or not selected_groups:
    st.warning("Seleziona almeno una dimensione e una variabile di confronto.")
    st.stop()

# === TABS PRINCIPALI ===
tab_overview, tab_details, tab_posthoc, tab_summary = st.tabs([
    "📋 Overview", "🔬 Dettaglio per Dimensione", "📊 Confronti Post-hoc", "📄 Riepilogo"
])

# Calcola tutte le analisi
all_results = {}
for dim_col in selected_dims:
    dim_name = DIMENSIONS[dim_col]
    all_results[dim_name] = {}
    
    for group_var in selected_groups:
        result = run_anova(df, dim_col, group_var)
        if result:
            all_results[dim_name][GROUPING_VARS.get(group_var, group_var)] = {
                'result': result,
                'dim_col': dim_col,
                'group_var': group_var
            }

# === TAB 1: OVERVIEW ===
with tab_overview:
    st.header("📋 Panoramica Risultati ANOVA")
    
    # Tabella riepilogativa
    summary_data = []
    for dim_name, group_results in all_results.items():
        for group_name, data in group_results.items():
            r = data['result']
            effect_interp, effect_class = interpret_effect_size(r['eta_squared'], 'eta')
            
            summary_data.append({
                'Dimensione': dim_name,
                'Confronto': group_name,
                'N Gruppi': r['n_groups'],
                'N Totale': r['n_total'],
                'Test': r['test_type'].split('(')[0].strip(),
                'Statistica': f"{r['statistic']:.2f}",
                'p-value': f"{r['p_value']:.4f}" if r['p_value'] >= 0.0001 else "<0.0001",
                'η²': f"{r['eta_squared']:.3f}",
                'Effetto': effect_interp,
                'Significativo': '✅' if r['p_value'] < alpha else '❌'
            })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        
        # Colora le righe significative
        def highlight_significant(row):
            if row['Significativo'] == '✅':
                return ['background-color: #d4edda'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            df_summary.style.apply(highlight_significant, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Conteggio significativi
        n_sig = sum(1 for d in summary_data if d['Significativo'] == '✅')
        n_total = len(summary_data)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Test Significativi", f"{n_sig}/{n_total}", f"{n_sig/n_total*100:.0f}%")
        with col2:
            large_effects = sum(1 for d in summary_data if d['Effetto'] == 'Grande')
            st.metric("Effetti Grandi", large_effects)
        with col3:
            medium_effects = sum(1 for d in summary_data if d['Effetto'] == 'Medio')
            st.metric("Effetti Medi", medium_effects)
    
    # Heatmap significatività
    st.subheader("🗺️ Mappa Significatività")
    
    # Prepara matrice
    dims = list(all_results.keys())
    groups = list(set(g for d in all_results.values() for g in d.keys()))
    
    sig_matrix = []
    for dim in dims:
        row = []
        for group in groups:
            if group in all_results[dim]:
                p = all_results[dim][group]['result']['p_value']
                row.append(-np.log10(p) if p > 0 else 10)  # -log10(p) per visualizzazione
            else:
                row.append(np.nan)
        sig_matrix.append(row)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=sig_matrix,
        x=groups,
        y=dims,
        colorscale='RdYlGn',
        text=[[f"p={all_results[d].get(g, {}).get('result', {}).get('p_value', np.nan):.4f}" 
               if g in all_results[d] else "" for g in groups] for d in dims],
        texttemplate="%{text}",
        hovertemplate="Dimensione: %{y}<br>Confronto: %{x}<br>%{text}<extra></extra>"
    ))
    
    fig_heatmap.add_hline(y=-0.5, line_dash="dash", line_color="red", 
                          annotation_text=f"α={alpha}", annotation_position="right")
    
    fig_heatmap.update_layout(
        title="Significatività dei confronti (-log10 p-value)",
        xaxis_title="Variabile di Confronto",
        yaxis_title="Dimensione",
        height=400
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.caption("Colori più intensi = p-value più bassi (più significativi). Linea rossa = soglia α.")

# === TAB 2: DETTAGLIO PER DIMENSIONE ===
with tab_details:
    st.header("🔬 Dettaglio per Dimensione")
    
    dim_tabs = st.tabs([DIMENSIONS[d] for d in selected_dims])
    
    for i, dim_col in enumerate(selected_dims):
        dim_name = DIMENSIONS[dim_col]
        
        with dim_tabs[i]:
            st.subheader(f"{dim_name}")
            
            if dim_name not in all_results or not all_results[dim_name]:
                st.warning("Nessun risultato disponibile per questa dimensione.")
                continue
            
            for group_name, data in all_results[dim_name].items():
                r = data['result']
                
                with st.expander(f"📊 {group_name}", expanded=True):
                    # Risultati ANOVA
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Statistica F/H", f"{r['statistic']:.2f}")
                    with col2:
                        p_str = f"{r['p_value']:.4f}" if r['p_value'] >= 0.0001 else "<0.0001"
                        st.metric("p-value", p_str)
                    with col3:
                        st.metric("η² (eta-squared)", f"{r['eta_squared']:.3f}")
                    with col4:
                        effect_interp, _ = interpret_effect_size(r['eta_squared'], 'eta')
                        st.metric("Effetto", effect_interp)
                    
                    # Interpretazione
                    if r['p_value'] < alpha:
                        best, worst, diff = find_best_worst_groups(r['descriptives'])
                        st.markdown(f"""
                        <div class="stat-significant">
                        <strong>✅ Differenza SIGNIFICATIVA</strong> (p = {r['p_value']:.4f})<br>
                        <strong>A favore di:</strong> {best} (M = {r['descriptives'][best]['mean']:.2f})<br>
                        <strong>Più basso:</strong> {worst} (M = {r['descriptives'][worst]['mean']:.2f})<br>
                        <strong>Differenza media:</strong> {diff:.2f} punti
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="stat-not-significant">
                        <strong>❌ Differenza NON significativa</strong> (p = {r['p_value']:.4f})<br>
                        Non ci sono differenze statisticamente rilevanti tra i gruppi.
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Grafico boxplot
                    df_plot = df[[data['dim_col'], data['group_var']]].dropna()
                    df_plot.columns = ['score', 'group']
                    
                    fig_box = px.box(
                        df_plot, x='group', y='score',
                        color='group',
                        title=f"Distribuzione {dim_name} per {group_name}",
                        labels={'score': dim_name, 'group': group_name}
                    )
                    fig_box.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig_box, use_container_width=True)
                    
                    # Tabella descrittive
                    st.markdown("**Statistiche Descrittive:**")
                    desc_data = []
                    for gname, gstats in sorted(r['descriptives'].items(), 
                                                 key=lambda x: x[1]['mean'], reverse=True):
                        desc_data.append({
                            'Gruppo': gname,
                            'N': gstats['n'],
                            'Media': f"{gstats['mean']:.2f}",
                            'DS': f"{gstats['std']:.2f}",
                            'Mediana': f"{gstats['median']:.2f}",
                            'Min': f"{gstats['min']:.2f}",
                            'Max': f"{gstats['max']:.2f}"
                        })
                    st.dataframe(pd.DataFrame(desc_data), use_container_width=True, hide_index=True)
                    
                    # Note metodologiche
                    with st.expander("📝 Note Metodologiche"):
                        st.markdown(f"""
                        - **Test utilizzato:** {r['test_type']}
                        - **Normalità rispettata:** {'Sì' if r['normality_ok'] else 'No (usato test non parametrico)'}
                        - **Omoschedasticità (Levene):** p = {r['levene_p']:.4f} ({'OK' if r['homoscedasticity_ok'] else 'Violata'})
                        - **ω² (omega-squared):** {r['omega_squared']:.3f} (stima meno biased di η²)
                        """)

# === TAB 3: CONFRONTI POST-HOC ===
with tab_posthoc:
    st.header("📊 Confronti Post-hoc (Pairwise)")
    
    if not PINGOUIN_AVAILABLE:
        st.warning("⚠️ Libreria pingouin non disponibile. Installa con: pip install pingouin")
        st.code("pip install pingouin", language="bash")
    else:
        st.info("I test post-hoc mostrano quali specifici gruppi differiscono tra loro dopo un'ANOVA significativa.")
        
        # Selezione dimensione e variabile
        col1, col2 = st.columns(2)
        with col1:
            ph_dim = st.selectbox("Dimensione", selected_dims, format_func=lambda x: DIMENSIONS[x])
        with col2:
            ph_group = st.selectbox("Variabile di confronto", selected_groups, 
                                     format_func=lambda x: GROUPING_VARS.get(x, x))
        
        dim_name = DIMENSIONS[ph_dim]
        group_name = GROUPING_VARS.get(ph_group, ph_group)
        
        if dim_name in all_results and group_name in all_results[dim_name]:
            r = all_results[dim_name][group_name]['result']
            
            if r['p_value'] < alpha:
                st.success(f"✅ ANOVA significativa (p = {r['p_value']:.4f}). Procedo con i confronti post-hoc.")
                
                # Esegui post-hoc
                posthoc_result = run_posthoc(df, ph_dim, ph_group, r['normality_ok'])
                
                if posthoc_result is not None and not posthoc_result.empty:
                    st.subheader("Risultati Tukey HSD / Dunn")
                    
                    # Formatta output
                    if 'A' in posthoc_result.columns and 'B' in posthoc_result.columns:
                        display_cols = ['A', 'B', 'mean(A)', 'mean(B)', 'diff', 'p-tukey']
                        display_cols = [c for c in display_cols if c in posthoc_result.columns]
                        
                        if not display_cols:
                            display_cols = posthoc_result.columns.tolist()
                        
                        ph_display = posthoc_result[display_cols].copy()
                        
                        # Evidenzia significativi
                        p_col = 'p-tukey' if 'p-tukey' in ph_display.columns else 'p-unc'
                        if p_col in ph_display.columns:
                            ph_display['Significativo'] = ph_display[p_col].apply(
                                lambda x: '✅' if x < alpha else '❌'
                            )
                        
                        st.dataframe(ph_display, use_container_width=True, hide_index=True)
                        
                        # Visualizza confronti significativi
                        st.subheader("🎯 Confronti Significativi")
                        
                        if p_col in posthoc_result.columns:
                            sig_pairs = posthoc_result[posthoc_result[p_col] < alpha]
                            
                            if not sig_pairs.empty:
                                for _, row in sig_pairs.iterrows():
                                    a, b = row['A'], row['B']
                                    mean_a = r['descriptives'].get(a, {}).get('mean', 0)
                                    mean_b = r['descriptives'].get(b, {}).get('mean', 0)
                                    
                                    if mean_a > mean_b:
                                        winner, loser = a, b
                                        diff = mean_a - mean_b
                                    else:
                                        winner, loser = b, a
                                        diff = mean_b - mean_a
                                    
                                    # Cohen's d tra i due gruppi
                                    idx_a = r['group_names'].index(a) if a in r['group_names'] else -1
                                    idx_b = r['group_names'].index(b) if b in r['group_names'] else -1
                                    
                                    if idx_a >= 0 and idx_b >= 0:
                                        d = calculate_cohens_d(r['groups'][idx_a], r['groups'][idx_b])
                                        d_interp, _ = interpret_effect_size(abs(d), 'd')
                                    else:
                                        d, d_interp = 0, "N/A"
                                    
                                    st.markdown(f"""
                                    - **{winner}** > **{loser}**: Δ = {diff:.2f} punti (p = {row[p_col]:.4f}, d = {abs(d):.2f} [{d_interp}])
                                    """)
                            else:
                                st.info("Nessun confronto pairwise raggiunge la significatività dopo la correzione per confronti multipli.")
                    else:
                        st.dataframe(posthoc_result, use_container_width=True)
                else:
                    st.warning("Non è stato possibile calcolare i test post-hoc.")
            else:
                st.warning(f"⚠️ ANOVA non significativa (p = {r['p_value']:.4f}). I test post-hoc non sono appropriati.")
        else:
            st.warning("Nessun risultato disponibile per questa combinazione.")

# === TAB 4: RIEPILOGO ===
with tab_summary:
    st.header("📄 Riepilogo Esecutivo")
    
    st.markdown("""
    ### Sintesi dei Risultati
    
    Questa sezione riassume i principali risultati delle analisi statistiche inferenziali
    condotte sulle 5 dimensioni dell'orientamento.
    """)
    
    # Genera riepilogo automatico
    significant_findings = []
    non_significant_findings = []
    
    for dim_name, group_results in all_results.items():
        for group_name, data in group_results.items():
            r = data['result']
            
            if r['p_value'] < alpha:
                best, worst, diff = find_best_worst_groups(r['descriptives'])
                effect_interp, _ = interpret_effect_size(r['eta_squared'], 'eta')
                
                significant_findings.append({
                    'dim': dim_name,
                    'group': group_name,
                    'p': r['p_value'],
                    'eta': r['eta_squared'],
                    'effect': effect_interp,
                    'best': best,
                    'worst': worst,
                    'diff': diff
                })
            else:
                non_significant_findings.append({
                    'dim': dim_name,
                    'group': group_name,
                    'p': r['p_value']
                })
    
    # Risultati significativi
    st.subheader("✅ Differenze Significative Trovate")
    
    if significant_findings:
        for f in sorted(significant_findings, key=lambda x: x['eta'], reverse=True):
            st.markdown(f"""
            **{f['dim']} × {f['group']}** (η² = {f['eta']:.3f}, effetto {f['effect'].lower()})
            - A favore di: **{f['best']}**
            - Più basso: {f['worst']}
            - Differenza: {f['diff']:.2f} punti (p = {f['p']:.4f})
            """)
            st.divider()
    else:
        st.info("Nessuna differenza significativa trovata.")
    
    # Tabella finale
    st.subheader("📊 Tabella Riepilogativa Completa")
    
    if summary_data:
        df_final = pd.DataFrame(summary_data)
        
        # Download CSV
        csv = df_final.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV",
            data=csv,
            file_name="analisi_anova_dimensioni.csv",
            mime="text/csv"
        )
        
        st.dataframe(df_final, use_container_width=True, hide_index=True)
    
    # Note metodologiche finali
    st.subheader("📝 Note Metodologiche")
    st.markdown(f"""
    ### Metodi Utilizzati
    
    1. **Test ANOVA/Kruskal-Wallis**: Confronto tra 3+ gruppi
       - ANOVA parametrica se normalità e omoschedasticità rispettate
       - Kruskal-Wallis non parametrica altrimenti
    
    2. **Effect Size (η²)**: Proporzione di varianza spiegata
       - η² ≥ 0.14 → Effetto grande
       - η² ≥ 0.06 → Effetto medio
       - η² ≥ 0.01 → Effetto piccolo
    
    3. **Test Post-hoc**: Tukey HSD (parametrico) o Dunn (non parametrico)
       - Correzione per confronti multipli
       - Cohen's d per dimensione dell'effetto pairwise
    
    ### Parametri Correnti
    - **Soglia α**: {alpha}
    - **Minimo osservazioni per gruppo**: {min_obs}
    - **Dimensioni analizzate**: {len(selected_dims)}
    - **Variabili di confronto**: {len(selected_groups)}
    - **Totale test eseguiti**: {len(summary_data) if summary_data else 0}
    
    ### Limitazioni
    - I risultati dipendono dalla qualità e completezza dei dati PTOF
    - La numerosità campionaria varia tra i gruppi
    - Possibile violazione di assunzioni in alcuni confronti
    """)

# Footer
st.divider()
render_footer()
